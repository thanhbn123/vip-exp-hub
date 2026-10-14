# G04 — Adapter J&T Express Việt Nam.
# Dựng THEO TÀI LIỆU CÔNG KHAI đọc được ngày 14/10/2026 tại open.jtexpress.vn/apiDoc:
#   - Headers: apiAccount (số), digest (chuỗi ký), timestamp (ms, UTC+7)
#   - digest = base64( md5( bizContent-JSON + privateKey ) )  — md5 ra BYTES rồi base64
#   - Body: application/x-www-form-urlencoded, trường bizContent = chuỗi JSON nghiệp vụ
#   - Tạo đơn: POST .../webopenplatformapi/api/order/addOrder
#     (test: demoopenapi.jtexpress.vn, prod: ylopenapi.jtexpress.vn — chép nguyên văn từ docs)
#   - bizContent tối thiểu: customerCode, password, txlogisticId (mã đơn khách, KHÔNG trùng),
#     orderType, serviceType, payType, productType, goodsType, sender{...}, receiver{...}, packageInfo{weight}
# TRẠNG THÁI: DOCUMENTED — transport dưới đây là MOCK; đường LIVE bị khóa (CHO_PHEP_LIVE=False)
# cho tới khi Owner cấp customerCode/password thật và duyệt. KHÔNG tự suy đoán gì ngoài docs.
import base64
import hashlib
import json
import random

import loi_hang
from adapter import CarrierAdapter, KetQuaHang, dang_ky

URL_TAO_DON = {
    "sandbox": "https://demoopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder",
    "production": "https://ylopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder",
}
# Tra cứu hành trình (轨迹查询) — nguồn: open.jtexpress.vn/apiDoc/logistics/query, đọc 14/10/2026.
# Tài liệu nêu rõ: billcodes ngăn cách bằng dấu phẩy, MỘT LƯỢT tối đa 30 vận đơn.
SO_VAN_DON_MOI_LUOT = 30
DUONG_TRA_HANH_TRINH = "/webopenplatformapi/api/logistics/trace"
# SỬA 14/10/2026 (đọc lại trang /apiDoc/logistics/query bằng trình duyệt): tài liệu CÓ cho URL đầy
# đủ của mục tra hành trình, ghi chú cũ "chỉ cho đường dẫn tương đối" là sai.
URL_TRA_HANH_TRINH = {
    "sandbox": "https://demoopenapi.jtexpress.vn" + DUONG_TRA_HANH_TRINH,
    "production": "https://ylopenapi.jtexpress.vn" + DUONG_TRA_HANH_TRINH,
}

CONTENT_TYPE = "application/x-www-form-urlencoded"
BANG_MA = "utf-8"
# Nguồn (trang "极兔API简介", đọc lại bằng trình duyệt 14/10/2026), nguyên văn:
#   "使用http协议表单提交的方式进行信息交互，字符编码默认统一采用UTF-8，
#    数据格式：application/x-www-form-urlencoded"
#   "digest=base64(md5(业务参数的Json+privateKey))，注：先md5得到字节数组，再base64加密"
# → md5 phải ra MẢNG BYTE trước rồi mới base64. Lấy md5 hexdigest rồi base64 là SAI chữ ký.
# Header timestamp: "时间戳，毫秒 / 时区：UTC+7" → mili giây, múi giờ UTC+7.
MUI_GIO_GIO = 7


def ky_digest(biz_content_json: str, private_key: str) -> str:
    """Đúng công thức docs: base64(md5-bytes(bizContent + privateKey))."""
    return base64.b64encode(
        hashlib.md5((biz_content_json + private_key).encode(BANG_MA)).digest()).decode()


def dau_thoi_gian_ms(bay_gio=None) -> int:
    """Mốc thời gian MILI GIÂY theo múi giờ UTC+7 như tài liệu yêu cầu.

    §12.2 ("mọi mốc thời gian phải mang múi giờ"): tính tường minh bằng UTC+7, không mượn múi
    giờ của máy đang chạy — máy chủ đặt UTC thì lệch 7 tiếng mà không báo lỗi gì.
    """
    import datetime as _dt
    tz = _dt.timezone(_dt.timedelta(hours=MUI_GIO_GIO))
    t = bay_gio or _dt.datetime.now(tz)
    return int(t.timestamp() * 1000)


def dung_bizcontent(nghiep_vu: dict) -> str:
    """bizContent là CHUỖI JSON, không phải object lồng — tài liệu ghi
    "业务参数模块内json格式的string类型". Chính chuỗi này là thứ đem đi ký."""
    return json.dumps(nghiep_vu, ensure_ascii=False)


def dung_headers(api_account, biz_content_json, private_key, bay_gio=None) -> dict:
    """Ba header bắt buộc theo tài liệu: apiAccount · digest · timestamp, kèm Content-Type."""
    return {
        "apiAccount": str(api_account),
        "digest": ky_digest(biz_content_json, private_key),
        "timestamp": str(dau_thoi_gian_ms(bay_gio)),
        "Content-Type": CONTENT_TYPE,
    }


def dung_body(biz_content_json: str) -> dict:
    """Thân yêu cầu dạng form: đúng một trường `bizContent` chứa chuỗi JSON."""
    return {"bizContent": biz_content_json}


@dang_ky
class AdapterJT(CarrierAdapter):
    ma_hang = "jt"
    ten_hang = "J&T Express"
    CAPABILITIES = {
        "createOrder": True, "cancelOrder": True, "getOrder": False,   # docs công khai chưa thấy getOrder riêng
        "trackOrder": True, "getShippingFee": True, "getShippingLabel": True,
        # SỬA 14/10/2026: lần đọc đầu em khai webhook=False vì chỉ nhìn menu cấp 1. Đọc kỹ thì
        # mục 物流轨迹 có trang con 轨迹回传 (callback): hãng CHỦ ĐỘNG đẩy hành trình về URL do
        # khách cung cấp. Nguồn: open.jtexpress.vn/apiDoc/logistics/statusFeedback.
        "webhook": True,
    }
    CHO_PHEP_LIVE = False    # BLOCKED: cần credentials thật + Owner duyệt
    # txlogisticId: tài liệu tạo đơn ghi "不支持重复" (không hỗ trợ trùng) → hãng tự chặn đơn trùng,
    # nên createOrder được phép thử lại có kiểm soát (xem transport.py).
    KHOA_CHONG_TRUNG = True

    def _dung_bizcontent_tao_don(self, don):
        """Dựng bizContent đúng theo bảng tham số docs (phần bắt buộc)."""
        return {
            "customerCode": self.credentials.get("customerCode", ""),
            "password": self.credentials.get("password", ""),
            "txlogisticId": don["ma_don"],          # mã đơn nội bộ = chống trùng phía hãng
            "orderType": 1, "serviceType": 1, "payType": "PP_CASH",
            "productType": "EXPRESS", "goodsType": "bm000010", "deliveryType": 1,
            "sender": {"name": don["nguoi_gui_ten"], "mobile": don["nguoi_gui_sdt"],
                       "prov": "", "area": "", "address": don["nguoi_gui_dia_chi"]},
            "receiver": {"name": don["nguoi_nhan_ten"], "mobile": don["nguoi_nhan_sdt"],
                         "prov": "", "area": "", "address": don["nguoi_nhan_dia_chi"]},
            "packageInfo": {"weight": f"{don['khoi_luong_gram'] / 1000:.2f}"},
            "itemsValue": don.get("cod", 0),
        }

    def yeu_cau_tao_don(self, don, bay_gio=None):
        """Dựng TRỌN gói yêu cầu tạo đơn (url · headers · body) mà KHÔNG gửi đi đâu cả.

        Tách ra để bộ thử hợp đồng kiểm được đúng công thức chữ ký, header và Content-Type
        theo tài liệu, không cần mạng và không cần credentials thật (§12.1: thứ dùng để kiểm
        chứng phải độc lập với lớp transport).
        """
        biz = dung_bizcontent(self._dung_bizcontent_tao_don(don))
        return {
            "url": URL_TAO_DON.get(self.moi_truong),   # None ở môi trường mock — cố ý
            "headers": dung_headers(self.credentials.get("apiAccount", ""), biz,
                                    self.credentials.get("privateKey", ""), bay_gio),
            "body": dung_body(biz),
            "bizContent": biz,
        }

    def createOrder(self, don) -> KetQuaHang:
        yc = self.yeu_cau_tao_don(don)
        digest = yc["headers"]["digest"]
        if self.moi_truong == "mock":
            # MOCK: không gửi gì ra ngoài. Hỗ trợ ép ca lỗi/timeout để kiểm thử.
            if don.get("ghi_chu") == "demo_force_fail":
                # Lỗi của hãng đi qua bảng mã lỗi THẬT (loi_hang.JT_MA_LOI), không bịa chuỗi lỗi.
                loi = loi_hang.doc_tra_loi_jt({"code": "145003050", "msg": "参数非法"},
                                              thao_tac="createOrder")
                return KetQuaHang(False, loi=f"MOCK J&T: {loi}", tho={"mock": True,
                                                                      "loi_chuan": loi.nhu_dict()})
            if don.get("ghi_chu") == "demo_force_timeout":
                loi = loi_hang.NormalizedCarrierError(
                    loi_hang.HET_GIO, thong_diep="MOCK J&T: hết giờ — không biết kết quả",
                    hang="jt", thao_tac="createOrder")
                return KetQuaHang(False, timeout=True, loi=str(loi),
                                  tho={"mock": True, "loi_chuan": loi.nhu_dict()})
            return KetQuaHang(True, ma_van_don="JTVN%010d" % random.randint(0, 10**10 - 1),
                              tho={"mock": True, "digest_da_ky": digest[:8] + "…"})
        raise PermissionError("Đường LIVE J&T đang khóa (BLOCKED — chờ Owner)")  # không bao giờ tới vì __init__ chặn

    def cancelOrder(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True})
        raise PermissionError("Đường LIVE J&T đang khóa")

    def trackOrder(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don,
                              tho={"mock": True, "trang_thai": "dang_giao"})
        raise PermissionError("Đường LIVE J&T đang khóa")

    def getShippingFee(self, don) -> KetQuaHang:
        if self.moi_truong == "mock":
            kl = max(1, don["khoi_luong_gram"])
            return KetQuaHang(True, phi=15000 + (kl // 500) * 5200, tho={"mock": True})
        raise PermissionError("Đường LIVE J&T đang khóa")

    def getShippingLabel(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True, "label": "MOCK-PDF"})
        raise PermissionError("Đường LIVE J&T đang khóa")

    # Bảng mã scanTypeCode thật đã đọc từ tài liệu → xem app/trang_thai_hang.py (JT_MA).
    # Lớp nền CarrierAdapter.normalizeTrackingStatus đã dùng bảng đó, không cần ghi đè.
