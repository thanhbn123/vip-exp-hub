# G05 — Adapter Viettel Post.
# TRẠNG THÁI: MOCK hoàn toàn.
#
# ĐÃ ĐỌC repo `vip-viettelpost` ngày 14/10/2026 (Owner cho phép) — KẾT QUẢ: repo đó là SCAFFOLD RỖNG,
# không có gì để tái dùng. Đo được:
#   - app/providers/viettel_post/status_mapper.py : STATUS_MAP = {} rỗng, kèm
#     "TODO: Fill only after verifying official VTP status codes."
#   - auth.py       : raise NotImplementedError — chưa có contract xác thực
#   - provider.py   : get_services / calculate_fee / create_shipment / get_shipment / cancel_shipment
#                     đều raise NotImplementedError
#   - docs/VIETTEL_POST_INTEGRATION.md : "Scaffold cố ý không điền endpoint/path cụ thể"
#   - docs/STATUS_MAPPING.md           : "Không điền mã trạng thái Viettel Post bằng suy đoán"
# Thứ DUY NHẤT cụ thể lấy được (và vẫn CHƯA XÁC MINH với tài liệu Partner chính thức):
#   - host: https://partner.viettelpost.vn   (app/core/config.py: vtp_base_url, .env.example)
#   - kiểu xác thực dự kiến: Bearer token, cấu hình vtp_username/vtp_password/vtp_token
#     → đây là PHỎNG ĐOÁN CỦA REPO ĐÓ, không phải tài liệu hãng. Không dùng làm căn cứ.
#
# ⇒ Nút thắt thật của VTP là TÀI LIỆU PARTNER API + credentials, KHÔNG phải quyền đọc repo.
VTP_HOST_CHUA_XAC_MINH = "https://partner.viettelpost.vn"
import random

from adapter import CarrierAdapter, KetQuaHang, dang_ky


@dang_ky
class AdapterVTP(CarrierAdapter):
    ma_hang = "vtp"
    ten_hang = "Viettel Post"
    CAPABILITIES = {
        "createOrder": True, "cancelOrder": True, "getOrder": True,
        "trackOrder": True, "getShippingFee": True, "getShippingLabel": True,
        "webhook": True,
    }
    CHO_PHEP_LIVE = False  # BLOCKED: chờ Owner cho đọc vip-viettelpost / cấp credentials
    # Chưa có tài liệu VTP trong tay → coi như KHÔNG có khóa chống trùng (an toàn hơn):
    # createOrder sẽ không được thử lại, timeout thì giữ đơn 'dang_gui' + cờ đối soát.
    KHOA_CHONG_TRUNG = False

    def createOrder(self, don) -> KetQuaHang:
        if self.moi_truong == "mock":
            if don.get("ghi_chu") == "demo_force_fail":
                return KetQuaHang(False, loi="MOCK VTP: hãng từ chối (ca ép lỗi)")
            if don.get("ghi_chu") == "demo_force_timeout":
                return KetQuaHang(False, timeout=True, loi="MOCK VTP: timeout — không biết kết quả")
            return KetQuaHang(True, ma_van_don="VTP%010d" % random.randint(0, 10**10 - 1), tho={"mock": True})
        raise PermissionError("Đường LIVE VTP đang khóa")

    def cancelOrder(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True})
        raise PermissionError("Đường LIVE VTP đang khóa")

    def getOrder(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True, "trang_thai": "da_gui"})
        raise PermissionError("Đường LIVE VTP đang khóa")

    def trackOrder(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True, "trang_thai": "dang_giao"})
        raise PermissionError("Đường LIVE VTP đang khóa")

    def getShippingFee(self, don) -> KetQuaHang:
        if self.moi_truong == "mock":
            kl = max(1, don["khoi_luong_gram"])
            return KetQuaHang(True, phi=16000 + (kl // 500) * 4500, tho={"mock": True})
        raise PermissionError("Đường LIVE VTP đang khóa")

    def getShippingLabel(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True, "label": "MOCK-PDF"})
        raise PermissionError("Đường LIVE VTP đang khóa")
