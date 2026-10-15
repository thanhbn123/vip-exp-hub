# G03 — Khung timeout + retry cho lớp gọi hãng.
#
# LUẬT QUAN TRỌNG NHẤT Ở ĐÂY: không phải thao tác nào cũng thử lại được.
#
#   - Thao tác CHỈ ĐỌC (getOrder, trackOrder, getShippingFee, getShippingLabel): thử lại thoải mái.
#   - createOrder / cancelOrder: thử lại MÙ QUÁNG có thể tạo đơn TRÙNG ở phía hãng. Chỉ được thử lại
#     khi hãng có khóa chống trùng của chính nó (J&T: txlogisticId "không hỗ trợ trùng" — theo tài
#     liệu open.jtexpress.vn/apiDoc/orderserve/create). Không có khóa đó thì KHÔNG thử lại; trả
#     timeout=True để Order Service giữ đơn ở 'dang_gui' + bật cờ phải đối soát bằng getOrder.
#
# Phân biệt ba kết cục, không gộp làm một:
#   ok=True              → hãng xác nhận
#   ok=False, timeout=F  → hãng TỪ CHỐI (biết chắc là hỏng)
#   ok=False, timeout=T  → KHÔNG BIẾT kết quả (mạng/hết giờ) — tuyệt đối không coi là thành công
import time


class LoiTamThoi(Exception):
    """Lỗi có thể khỏi khi thử lại: mạng chập, 5xx, hết giờ.

    `cho_giay`: lớp DƯỚI gợi ý phải CHỜ bao nhiêu giây trước khi thử lại. Có mặt vì HTTP 429
    (và 408) là tín hiệu *"thử lại sau"* của máy chủ, thường kèm header `Retry-After`. Nếu lớp
    trên cứ thử lại theo backoff 0,2 giây thì lượt thử lại vừa vô ích vừa làm hạn mức tệ thêm —
    tức là "thử lại được" trên giấy mà hỏng trong thực tế. `None` = dùng backoff của chính sách.
    """

    def __init__(self, *a, cho_giay=None):
        super().__init__(*a)
        self.cho_giay = cho_giay


# TRẦN thời gian chờ do lớp dưới gợi ý. Không có trần thì một `Retry-After: 86400` biến
# "thử lại được" thành "treo tiến trình một ngày" — hãng không được phép quyết định điều đó.
CHO_TOI_DA = 60.0


class LoiVinhVien(Exception):
    """Lỗi thử lại vô ích: sai tham số, sai chữ ký, 4xx."""


class ChinhSach:
    """Chính sách gọi một thao tác của hãng."""
    def __init__(self, so_lan=3, backoff_goc=0.2, he_so=2.0, het_gio=10.0, duoc_thu_lai=True):
        self.so_lan = so_lan
        self.backoff_goc = backoff_goc
        self.he_so = he_so
        self.het_gio = het_gio
        self.duoc_thu_lai = duoc_thu_lai


# Mặc định theo tên thao tác. createOrder/cancelOrder mặc định KHÔNG thử lại.
MAC_DINH = {
    "createOrder": ChinhSach(so_lan=1, duoc_thu_lai=False),
    "cancelOrder": ChinhSach(so_lan=1, duoc_thu_lai=False),
    "getOrder": ChinhSach(so_lan=3),
    "trackOrder": ChinhSach(so_lan=3),
    "getShippingFee": ChinhSach(so_lan=3),
    "getShippingLabel": ChinhSach(so_lan=2),
}


def chinh_sach_cho(thao_tac, co_khoa_chong_trung=False):
    """Trả chính sách; thao tác ghi chỉ được mở thử lại khi hãng có khóa chống trùng riêng."""
    cs = MAC_DINH.get(thao_tac, ChinhSach())
    if thao_tac in ("createOrder", "cancelOrder") and co_khoa_chong_trung:
        return ChinhSach(so_lan=3, duoc_thu_lai=True)
    return cs


def goi(ham, thao_tac="?", chinh_sach=None, co_khoa_chong_trung=False, ngu=time.sleep):
    """Gọi `ham()` theo chính sách. Trả (ket_qua, so_lan_da_goi, nhat_ky).
    Ném LoiVinhVien ra ngoài ngay. Hết số lần mà vẫn LoiTamThoi → ném LoiTamThoi cuối cùng."""
    cs = chinh_sach or chinh_sach_cho(thao_tac, co_khoa_chong_trung)
    nhat_ky = []
    loi_cuoi = None
    for lan in range(1, cs.so_lan + 1):
        try:
            kq = ham()
            nhat_ky.append(f"lần {lan}: ok")
            return kq, lan, nhat_ky
        except LoiVinhVien as e:
            nhat_ky.append(f"lần {lan}: lỗi vĩnh viễn ({e}) — không thử lại")
            raise
        except LoiTamThoi as e:
            loi_cuoi = e
            nhat_ky.append(f"lần {lan}: lỗi tạm thời ({e})")
            if not cs.duoc_thu_lai:
                nhat_ky.append("thao tác KHÔNG được thử lại (nguy cơ trùng) — dừng")
                raise
            if lan < cs.so_lan:
                cho = cs.backoff_goc * (cs.he_so ** (lan - 1))
                # Lớp dưới có thể biết rõ hơn phải chờ bao lâu (HTTP `Retry-After`). Lấy giá trị
                # LỚN HƠN, nhưng LUÔN bị chặn trần: hãng không được quyết định treo tiến trình.
                goi_y = getattr(e, "cho_giay", None)
                if goi_y:
                    try:
                        cho = max(cho, min(float(goi_y), CHO_TOI_DA))
                    except (TypeError, ValueError):
                        pass
                ngu(cho)
    raise loi_cuoi
