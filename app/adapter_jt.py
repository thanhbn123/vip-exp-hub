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

from adapter import CarrierAdapter, KetQuaHang, dang_ky

URL_TAO_DON = {
    "sandbox": "https://demoopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder",
    "production": "https://ylopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder",
}


def ky_digest(biz_content_json: str, private_key: str) -> str:
    """Đúng công thức docs: base64(md5-bytes(bizContent + privateKey))."""
    return base64.b64encode(hashlib.md5((biz_content_json + private_key).encode()).digest()).decode()


@dang_ky
class AdapterJT(CarrierAdapter):
    ma_hang = "jt"
    ten_hang = "J&T Express"
    CAPABILITIES = {
        "createOrder": True, "cancelOrder": True, "getOrder": False,   # docs công khai chưa thấy getOrder riêng
        "trackOrder": True, "getShippingFee": True, "getShippingLabel": True,
        "webhook": False,    # menu docs công khai chưa thấy mục webhook — dùng polling trackOrder (fallback)
    }
    CHO_PHEP_LIVE = False    # BLOCKED: cần credentials thật + Owner duyệt

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

    def createOrder(self, don) -> KetQuaHang:
        biz = json.dumps(self._dung_bizcontent_tao_don(don), ensure_ascii=False)
        digest = ky_digest(biz, self.credentials.get("privateKey", ""))
        if self.moi_truong == "mock":
            # MOCK: không gửi gì ra ngoài. Hỗ trợ ép ca lỗi/timeout để kiểm thử.
            if don.get("ghi_chu") == "demo_force_fail":
                return KetQuaHang(False, loi="MOCK J&T: hãng từ chối (ca ép lỗi)")
            if don.get("ghi_chu") == "demo_force_timeout":
                return KetQuaHang(False, timeout=True, loi="MOCK J&T: timeout — không biết kết quả")
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

    # Bảng mã trạng thái riêng của J&T sẽ bổ sung khi đọc được mục 物流轨迹 chi tiết; tạm ánh xạ tên chuẩn.
    @staticmethod
    def normalizeTrackingStatus(trang_thai_hang):
        return trang_thai_hang
