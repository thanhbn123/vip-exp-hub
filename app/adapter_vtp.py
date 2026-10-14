# G05 — Adapter Viettel Post.
# TRẠNG THÁI: MOCK hoàn toàn.
#
# ĐÃ ĐỌC repo `vip-viettelpost` ngày 14/10/2026 (Owner cho phép, CHỈ ĐỌC). Khảo sát lại lần hai
# cùng ngày tại commit `4df8ce7`, kết quả đầy đủ ghi ở docs/VIETTELPOST_REUSE_AUDIT.md.
# KẾT QUẢ cho LỚP TÍCH HỢP HÃNG — thứ adapter này cần: KHUNG RỖNG, không tái dùng được gì. Đo được:
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
# ĐÍNH CHÍNH 14/10/2026 (§12.1): câu cũ ở đây viết repo đó "là SCAFFOLD RỖNG" — nói quá phạm vi.
# Đúng là: LỚP TÍCH HỢP HÃNG rỗng (7/9 hạng mục `NotImplementedError`, 2 là vỏ), nhưng LỚP LƯU TRỮ
# của repo đó KHÔNG rỗng — 1.325 dòng mã thật, 8 bảng có ràng buộc, 612 dòng test lưu trữ. Chỉ là
# không chép sang được, vì bên mình dùng sqlite3 + thư viện chuẩn còn bên đó FastAPI + SQLAlchemy.
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
