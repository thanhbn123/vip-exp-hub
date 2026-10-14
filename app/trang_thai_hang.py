# G03 — Ánh xạ trạng thái RIÊNG của từng hãng → trạng thái chuẩn của hệ thống.
#
# NGUỒN: chỉ điền mã nào ĐỌC ĐƯỢC từ tài liệu chính thức. Mã nào chưa có tài liệu thì để trống
# và ghi rõ, KHÔNG suy đoán (§12 chống bịa).
#
# Trạng thái chuẩn (xem cau_hinh.HANG_TRANG_THAI_GIAO, có thứ hạng để chặn sự kiện đến muộn):
#   cho_lay(1) → lay_hang(2) → dang_giao(3) → giao_that_bai(4) → giao_thanh_cong(5) → hoan_hang(6)
#
# Giá trị None = sự kiện CHỈ GHI NHẬN, không đổi trạng thái hành trình (thông tin thêm, hoặc
# chưa chắc ánh xạ vào đâu). An toàn hơn là đoán bừa rồi cập nhật sai đơn.

# ---- J&T Express Việt Nam ----
# Nguồn: open.jtexpress.vn/apiDoc/logistics/statusFeedback và /apiDoc/logistics/query
# (đọc bằng trình duyệt ngày 14/10/2026; trang là SPA nên fetch tĩnh không đọc được).
# Danh sách scanTypeCode chép nguyên từ cột mô tả của tài liệu.
JT_MA = {
    103: ("Order Placed / 下单", "cho_lay"),
    104: ("Pickup Failure / 取件失败", None),      # lấy hàng hỏng — chưa có trạng thái chuẩn tương ứng
    105: ("Cancel Order / 取消订单", None),        # hủy là trạng thái NGHIỆP VỤ, do Order Service quyết
    106: ("Picked Up / 快件揽收", "lay_hang"),
    109: ("Departure / 发件扫描", "dang_giao"),
    110: ("Arrival / 到件扫描", "dang_giao"),
    112: ("On Delivery / 出仓扫描", "dang_giao"),
    113: ("Delivered / 快件签收", "giao_thanh_cong"),
    116: ("Returning / 退件确认", "hoan_hang"),
    117: ("Returned Sign / 退件签收", "hoan_hang"),
    118: ("Delivery Problem / 派件问题件", "giao_that_bai"),
    120: ("Return Problem / 退件问题件", None),    # vấn đề trong lúc hoàn — chỉ ghi nhận
    121: ("FINISH / 完结", None),                  # tài liệu không nói rõ kết thúc theo hướng nào
}
# CẦN XÁC MINH khi có tài khoản thật:
#   - Ví dụ request trong tài liệu dùng scanTypeCode = 10, KHÔNG nằm trong danh sách mã nêu trên.
#     Chưa rõ là lỗi tài liệu hay có bộ mã khác. Mã lạ sẽ rơi vào nhánh "không ánh xạ" (an toàn).
#   - Ý nghĩa chính xác của 121 FINISH (sau giao thành công hay sau hoàn hàng).

# ---- Viettel Post ----
# CHƯA CÓ TÀI LIỆU trong tay: adapter VTP hiện là MOCK, và việc đọc mã tích hợp thật nằm ở repo
# `vip-viettelpost` mà Owner chưa cho phép đọc (BLOCKED). Vì vậy chỉ ánh xạ đúng các mã mà
# BỘ MÔ PHỎNG của chính dự án này sinh ra — không bịa mã của hãng thật.
VTP_MA_MOCK = {
    "cho_lay": ("MOCK chờ lấy", "cho_lay"),
    "lay_hang": ("MOCK đã lấy", "lay_hang"),
    "dang_giao": ("MOCK đang giao", "dang_giao"),
    "giao_thanh_cong": ("MOCK giao thành công", "giao_thanh_cong"),
    "giao_that_bai": ("MOCK giao thất bại", "giao_that_bai"),
    "hoan_hang": ("MOCK hoàn hàng", "hoan_hang"),
}

BANG = {"jt": JT_MA, "vtp": VTP_MA_MOCK}


class KetQuaAnhXa:
    """Kết quả ánh xạ: có biết mã không, đổi sang trạng thái nào, mô tả gốc của hãng."""
    __slots__ = ("biet_ma", "trang_thai", "mo_ta_hang", "ma_goc")

    def __init__(self, biet_ma, trang_thai, mo_ta_hang, ma_goc):
        self.biet_ma = biet_ma          # False = mã lạ, chưa có trong tài liệu đã đọc
        self.trang_thai = trang_thai    # None = chỉ ghi nhận, không đổi trạng thái
        self.mo_ta_hang = mo_ta_hang
        self.ma_goc = ma_goc

    def __repr__(self):
        return (f"KetQuaAnhXa(biet_ma={self.biet_ma}, trang_thai={self.trang_thai!r}, "
                f"ma_goc={self.ma_goc!r})")


def anh_xa(ma_hang, ma_trang_thai):
    """Đổi mã trạng thái của hãng → trạng thái chuẩn. Mã lạ KHÔNG ném lỗi và KHÔNG đổi trạng thái."""
    bang = BANG.get(ma_hang)
    if bang is None:
        return KetQuaAnhXa(False, None, f"hãng '{ma_hang}' chưa có bảng ánh xạ", ma_trang_thai)
    khoa = ma_trang_thai
    if ma_hang == "jt":
        try:
            khoa = int(ma_trang_thai)
        except (TypeError, ValueError):
            return KetQuaAnhXa(False, None, "scanTypeCode không phải số", ma_trang_thai)
    if khoa not in bang:
        return KetQuaAnhXa(False, None, "mã không có trong tài liệu đã đọc", ma_trang_thai)
    mo_ta, chuan = bang[khoa]
    return KetQuaAnhXa(True, chuan, mo_ta, ma_trang_thai)


def ma_da_biet(ma_hang):
    return sorted(BANG.get(ma_hang, {}).keys(), key=str)
