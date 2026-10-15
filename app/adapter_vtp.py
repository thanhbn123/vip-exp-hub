# G05 — Adapter Viettel Post.
# TRẠNG THÁI: MOCK hoàn toàn.
#
# ĐÍNH CHÍNH 15/10/2026 (AG-03, G12) — KHỐI CHÚ THÍCH CŨ Ở ĐÂY NÓI SAI.
#
# Khảo sát ngày 14/10 đo trên bản clone `4df8ce7`, mà bản đó đi sau `origin/develop`
# **194 commit**. Bản clone không báo lỗi gì — nó chỉ cũ. Kết luận "KHUNG RỖNG, không tái
# dùng được gì" là kết luận về một bản mã đã lỗi thời, không phải về repo.
#
# Đo lại trên `develop` (`68e9642`, 14/10) — đỉnh thật, KHÔNG phải `main` (`main` và
# `develop` đã rẽ nhánh: ahead 21, behind 1):
#   - lớp tích hợp VTP: **2.391 dòng hoàn chỉnh**, không phải khung rỗng
#   - `status_mapper.py`: **21 mã trạng thái** (15 có ánh xạ, 6 cố ý `None` kèm lý do)
#   - `auth.py`: **141 dòng** — Login → ownerconnect → LoginVTP, có đệm token, `invalidate()`
#   - webhook: **~1.000 dòng** — kiểm cỡ → `TOKEN` qua `hmac.compare_digest` → vân tay
#     SHA-256 → chống trùng → lưu thô → ánh xạ → ACK
#   - đã chạy THẬT trên `partnerdev` ngày 02/10/2026 (tạo đơn thử rồi huỷ)
#
# TÁI DÙNG ĐƯỢC **DỮ KIỆN** (endpoint, bảng mã, khuôn webhook, cách xác thực), KHÔNG tái dùng
# được **MÃ** — repo đó chạy nền async, dự án này là stdlib đồng bộ.
#
# Và một dữ kiện câu cũ nói sai: token VTP đi ở header **`Token`**, không phải `Bearer`.
#
# Chi tiết + 15 câu đính chính: docs/G12_VTP_KHAO_SAT.md §6.
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
