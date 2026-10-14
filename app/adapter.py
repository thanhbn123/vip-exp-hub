# G03 — Carrier Adapter Interface: hợp đồng chung cho mọi hãng.
# Luật: logic đặc thù hãng nằm TRONG adapter, Order Core không biết chi tiết hãng.
# Adapter phải khai báo capabilities; chức năng hãng không hỗ trợ → capability = False.
# KHÔNG giả lập API thật thành "đang hoạt động": transport mock phải tự nhận là mock.


class KetQuaHang:
    """Kết quả chuẩn hóa từ adapter."""
    def __init__(self, ok, ma_van_don=None, phi=None, loi=None, timeout=False, tho=None):
        self.ok = ok
        self.ma_van_don = ma_van_don
        self.phi = phi
        self.loi = loi
        self.timeout = timeout       # True = KHÔNG BIẾT kết quả (phải getOrder kiểm lại), khác với thất bại
        self.tho = tho or {}


class CarrierAdapter:
    """Lớp nền. Mỗi hãng một lớp con. moi_truong: mock | sandbox | production."""
    ma_hang = "?"
    ten_hang = "?"
    CAPABILITIES = {
        "createOrder": False, "cancelOrder": False, "getOrder": False,
        "trackOrder": False, "getShippingFee": False, "getShippingLabel": False,
        "webhook": False,
    }
    # Chặn cứng đường LIVE ở local cho tới khi Owner cấp credentials + duyệt.
    CHO_PHEP_LIVE = False
    # Hãng có khóa chống trùng của CHÍNH NÓ cho createOrder không? Quyết định việc có được
    # thử lại thao tác ghi hay không (xem transport.py). Mặc định: KHÔNG, để an toàn.
    KHOA_CHONG_TRUNG = False

    def __init__(self, credentials: dict, moi_truong: str = "mock"):
        self.credentials = credentials
        self.moi_truong = moi_truong
        if moi_truong != "mock" and not self.CHO_PHEP_LIVE:
            raise PermissionError(
                f"Adapter {self.ma_hang}: môi trường '{moi_truong}' đang bị khóa — "
                "cần Owner cấp credentials thật và duyệt (xem docs/ACCEPTANCE_CHECKLIST.md mục BLOCKED)")

    def capability(self, ten):
        return self.CAPABILITIES.get(ten, False)

    def getCapabilities(self) -> dict:
        """Hàm chuẩn của hợp đồng (docs/SHARED_CONTRACTS.md mục 4): mô tả ĐẦY ĐỦ khả năng của
        MỘT thể hiện adapter, để Order Service không phải biết chi tiết hãng.

        Giữ nguyên `capability(ten)` và `danh_sach_hang()` — hai hàm cũ vẫn có người gọi.
        Khác nhau ở chỗ: `capability` hỏi MỘT khóa; `danh_sach_hang` xem MỌI LỚP đã đăng ký;
        còn `getCapabilities` mô tả CHÍNH thể hiện này, nên biết cả môi trường đang chạy.

        `chuc_nang` là **bản sao**, không phải chính dict của lớp: người gọi lỡ sửa vào đó thì
        chỉ hỏng bản sao, không đổi CAPABILITIES của cả lớp (một chỗ sửa lan ra mọi tenant là
        đúng dạng hỏng im lặng, §12.2).
        """
        return {
            "ma_hang": self.ma_hang,
            "ten_hang": self.ten_hang,
            "chuc_nang": dict(self.CAPABILITIES),
            "moi_truong": self.moi_truong,
            "la_mock": self.moi_truong == "mock",
            "live_mo": bool(self.CHO_PHEP_LIVE),
            "khoa_chong_trung": bool(self.KHOA_CHONG_TRUNG),
            # Thao tác ghi chỉ được thử lại khi hãng tự chặn đơn trùng (xem transport.py).
            "createOrder_duoc_thu_lai": bool(self.KHOA_CHONG_TRUNG),
            "ma_trang_thai_da_biet": self._ma_trang_thai_da_biet(),
            "so_ma_loi_da_biet": self._so_ma_loi_da_biet(),
        }

    @classmethod
    def _ma_trang_thai_da_biet(cls):
        import trang_thai_hang as tth
        return [str(x) for x in tth.ma_da_biet(cls.ma_hang)]

    @classmethod
    def _so_ma_loi_da_biet(cls):
        """Số mã lỗi ĐÃ ĐỌC ĐƯỢC từ tài liệu hãng. 0 nghĩa là chưa có tài liệu — nói thẳng,
        không để người đọc tưởng hãng không có lỗi nào."""
        import loi_hang
        return len(loi_hang.BANG_MA_LOI.get(cls.ma_hang) or {})

    # Các hàm chuẩn — lớp con cài đặt; mặc định báo không hỗ trợ.
    def createOrder(self, don) -> KetQuaHang:
        return KetQuaHang(False, loi=f"{self.ma_hang} không hỗ trợ createOrder")

    def cancelOrder(self, ma_van_don) -> KetQuaHang:
        return KetQuaHang(False, loi=f"{self.ma_hang} không hỗ trợ cancelOrder")

    def getOrder(self, ma_van_don) -> KetQuaHang:
        return KetQuaHang(False, loi=f"{self.ma_hang} không hỗ trợ getOrder")

    def trackOrder(self, ma_van_don) -> KetQuaHang:
        return KetQuaHang(False, loi=f"{self.ma_hang} không hỗ trợ trackOrder")

    def getShippingFee(self, don) -> KetQuaHang:
        return KetQuaHang(False, loi=f"{self.ma_hang} không hỗ trợ getShippingFee")

    def getShippingLabel(self, ma_van_don) -> KetQuaHang:
        return KetQuaHang(False, loi=f"{self.ma_hang} không hỗ trợ getShippingLabel")

    @classmethod
    def normalizeTrackingStatus(cls, trang_thai_hang):
        """Đổi mã trạng thái riêng của hãng → trạng thái chuẩn, qua bảng ánh xạ chung.
        Trả KetQuaAnhXa: mã lạ KHÔNG ném lỗi và KHÔNG đổi trạng thái đơn."""
        import trang_thai_hang as tth
        return tth.anh_xa(cls.ma_hang, trang_thai_hang)


_DANG_KY = {}


def dang_ky(lop):
    _DANG_KY[lop.ma_hang] = lop
    return lop


def tao_adapter(ma_hang, credentials, moi_truong="mock") -> CarrierAdapter:
    if ma_hang not in _DANG_KY:
        raise KeyError(f"Chưa có adapter cho hãng '{ma_hang}'")
    return _DANG_KY[ma_hang](credentials, moi_truong)


def danh_sach_hang():
    return {ma: {"ten": lop.ten_hang, "capabilities": lop.CAPABILITIES,
                 "live_mo": lop.CHO_PHEP_LIVE, "khoa_chong_trung": lop.KHOA_CHONG_TRUNG}
            for ma, lop in _DANG_KY.items()}
