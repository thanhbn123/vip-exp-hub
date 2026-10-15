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
    # 110: NHẬP NHẰNG — tài liệu tự mâu thuẫn. Nghĩa dưới đây là nghĩa theo BẢNG THAM SỐ,
    # giữ lại để đọc/hiển thị; đường CẬP NHẬT ĐƠN không được dùng nó (xem NHAP_NHANG + quyet_dinh()).
    110: ("Arrival / 到件扫描", "dang_giao"),
    112: ("On Delivery / 出仓扫描", "dang_giao"),
    113: ("Delivered / 快件签收", "giao_thanh_cong"),
    116: ("Returning / 退件确认", "hoan_hang"),
    117: ("Returned Sign / 退件签收", "hoan_hang"),
    118: ("Delivery Problem / 派件问题件", "giao_that_bai"),
    120: ("Return Problem / 退件问题件", None),    # vấn đề trong lúc hoàn — chỉ ghi nhận
    121: ("FINISH / 完结", None),                  # tài liệu không nói rõ kết thúc theo hướng nào
}
# CẦN XÁC MINH khi có tài khoản thật (đọc lại tài liệu bằng trình duyệt 14/10/2026, thấy thêm):
#   - TÀI LIỆU TỰ MÂU THUẪN VỚI VÍ DỤ CỦA CHÍNH NÓ. Bảng tham số liệt kê bộ mã 103…121 ở trên,
#     nhưng VÍ DỤ TRẢ LỜI ngay dưới bảng (cả /apiDoc/logistics/query lẫn /logistics/statusFeedback)
#     dùng một bộ mã KHÁC HẲN: 10 "Nhận hàng / 快件揽收", 50 "Gửi hàng", 92 "Hàng đến",
#     94 "Quét phát hàng", 100 "Ký nhận", 110 "Quét kiện vấn đề".
#     Nguy nhất là **110**: bảng tham số ghi "Arrival / 到件扫描" (đang giao), ví dụ lại ghi
#     "Quét kiện vấn đề". Hai nghĩa ngược chiều nhau trên cùng một con số.
#     HIỆN GIỮ theo BẢNG THAM SỐ — phần chuẩn tắc của tài liệu — vì bộ mã trong ví dụ rõ ràng là
#     một hệ đánh số khác (ví dụ ghi 10 = đã lấy hàng, trong khi bảng ghi 106).
#     Rủi ro còn lại, ghi ra để không ai quên (§12.1 "rủi ro cố ý bỏ qua thì phải ghi ra"): nếu
#     hãng thật đẩy theo bộ mã của ví dụ thì 110 sẽ bị hiểu thành "đang giao" thay vì "kiện vấn
#     đề". Hậu quả có giới hạn — dang_giao hạng 3 < giao_that_bai hạng 4 nên rank guard không bị
#     kéo lùi — nhưng đơn có vấn đề sẽ KHÔNG nổi lên. Phải hỏi hãng ngay khi có người đối tiếp.
#   - Ý nghĩa chính xác của 121 FINISH (sau giao thành công hay sau hoàn hàng).

# ---- Viettel Post ----
# Adapter VTP hiện là MOCK hoàn toàn.
#
# ĐÍNH CHÍNH 15/10/2026 (AG-03, G12) — ghi chú ngày 14/10 ở đây NÓI SAI, và nó nói sai vì
# `docs/VIETTELPOST_REUSE_AUDIT.md` nói sai trước. Cả hai đo trên bản clone `4df8ce7`, mà bản
# đó đi sau `origin/develop` **194 commit**. Bản clone KHÔNG BÁO LỖI GÌ — nó chỉ cũ, nên không
# ai nghĩ phải kiểm nó. Đây đúng là §12.1: thứ dùng để kiểm chứng phải được kiểm TRƯỚC khi tin.
#
# Câu cũ: "lớp tích hợp hãng là khung rỗng, `STATUS_MAP = {}`, không có mã trạng thái nào".
# Đo lại trên `develop` (`68e9642`, 14/10): lớp tích hợp VTP **hoàn chỉnh 2.391 dòng**, có
# **21 mã trạng thái** (15 có ánh xạ, 6 cố ý `None` kèm lý do từng mã), `auth.py` **141 dòng**
# đầy đủ, webhook **~1.000 dòng** có kiểm `TOKEN` bằng `hmac.compare_digest` + vân tay chống
# trùng. Repo đang SỐNG (`pushed_at` 14/10), và đã chạy thật trên `partnerdev` ngày 02/10.
#
# Câu cũ: "nút thắt thật là TÀI LIỆU PARTNER API + credentials".
# Đo lại: **tài liệu KHÔNG còn là nút thắt** — đã đọc được và đối chiếu từng trang. Còn lại
# **chỉ credentials**.
#
# Vì sao mục này vẫn chỉ có mã MOCK: 21 mã kia là dữ kiện của repo khác, mang sang phải qua
# một lượt đối chiếu riêng (và mã `104` của VTP là **ca nhập nhằng thứ hai** — bảng nói là
# trạng thái cuối, đoạn "Lưu ý" nói không). Chưa mang sang thì KHÔNG bịa mã hãng.
# Vì vậy chỉ ánh xạ đúng các mã mà BỘ MÔ PHỎNG của chính dự án này sinh ra — không bịa mã hãng.
VTP_MA_MOCK = {
    "cho_lay": ("MOCK chờ lấy", "cho_lay"),
    "lay_hang": ("MOCK đã lấy", "lay_hang"),
    "dang_giao": ("MOCK đang giao", "dang_giao"),
    "giao_thanh_cong": ("MOCK giao thành công", "giao_thanh_cong"),
    "giao_that_bai": ("MOCK giao thất bại", "giao_that_bai"),
    "hoan_hang": ("MOCK hoàn hàng", "hoan_hang"),
}

BANG = {"jt": JT_MA, "vtp": VTP_MA_MOCK}


# ============================================================================
# G06 — SỔ MÃ NHẬP NHẰNG (ambiguous) và QUYẾT ĐỊNH ÁNH XẠ
#
# Vì sao có mục này: tài liệu hãng có thể TỰ MÂU THUẪN. Khi đó luật của dự án là KHÔNG tự chọn
# một nghĩa (§12 chống bịa) và KHÔNG BAO GIỜ mặc định sang trạng thái HOÀN TẤT — đoán sai về
# phía "đã xong" là loại sai đắt nhất: đơn có vấn đề bị coi là đã giao, không ai soát lại.
#
# Thay vì chọn, hệ thống:
#   1. lưu đủ dấu vết (mã gốc · mô tả gốc · sự kiện hãng gốc · nguồn tài liệu · độ tin cậy · giờ nhận),
#   2. đánh dấu NEEDS_REVIEW / AMBIGUOUS,
#   3. KHÔNG đổi trạng thái đơn cho tới khi có người CHỐT nghĩa kèm căn cứ từ hãng.
# ============================================================================

# Độ tin cậy của một lượt ánh xạ.
TIN_CAO = "cao"                  # tài liệu nói rõ, không có chỗ mâu thuẫn
TIN_TRUNG_BINH = "trung_binh"    # có nghĩa nhưng còn điểm chưa chắc (vd mã chỉ ghi nhận)
TIN_NHAP_NHANG = "nhap_nhang"    # tài liệu tự mâu thuẫn, CHƯA ai chốt nghĩa
TIN_MA_LA = "ma_la"              # mã không có trong tài liệu đã đọc
MUC_TIN_CAY = (TIN_CAO, TIN_TRUNG_BINH, TIN_NHAP_NHANG, TIN_MA_LA)

# Trạng thái coi là KẾT THÚC hành trình. Mã nhập nhằng tuyệt đối không được rơi vào đây.
TRANG_THAI_HOAN_TAT = ("giao_thanh_cong", "hoan_hang")

NGUON_JT = ("open.jtexpress.vn/apiDoc/logistics/query + /logistics/statusFeedback"
            " · đọc bằng trình duyệt 14/10/2026")
# Nguồn của BẢNG ánh xạ từng hãng. VTP nói thẳng là mô phỏng của chính dự án, không phải hãng.
NGUON_BANG = {"jt": NGUON_JT,
              "vtp": "bộ mô phỏng của chính dự án (KHÔNG có tài liệu hãng)"}
PHIEN_BAN_TAI_LIEU = {"jt": "doc-2026-10-14", "vtp": "chua-co-tai-lieu"}

# Sổ mã nhập nhằng: (ma_hang, khóa mã) -> mô tả mâu thuẫn + các nghĩa có thể.
# `trang_thai` trong từng nghĩa là trạng thái chuẩn mà nghĩa ĐÓ dẫn tới (None = chỉ ghi nhận).
NHAP_NHANG = {
    ("jt", 110): {
        "ly_do": ("Tài liệu J&T tự mâu thuẫn với ví dụ của chính nó: BẢNG THAM SỐ ghi"
                  " 110 = Arrival / 到件扫描 (hàng đến kho, đang đi), nhưng VÍ DỤ TRẢ LỜI ở cả"
                  " /logistics/query lẫn /logistics/statusFeedback ghi 110 = quét kiện có vấn đề."
                  " Hai nghĩa ngược chiều nhau trên cùng một con số."),
        "nguon": NGUON_JT,
        "nghia": {
            "bang_tham_so": {
                "mo_ta_hang": "Arrival / 到件扫描",
                "trang_thai": "dang_giao",
                "nguon": "bảng tham số scanTypeCode (phần chuẩn tắc của tài liệu)",
            },
            "vi_du_tra_loi": {
                "mo_ta_hang": "Quét kiện có vấn đề",
                # CỐ Ý None, không phải 'giao_that_bai': ví dụ của tài liệu không nói rõ đây là
                # thất bại giao hay chỉ là một lần quét bất thường trên đường. Đã có mã 118
                # (Delivery Problem) cho thất bại giao thật.
                "trang_thai": None,
                "nguon": "ví dụ trả lời của /logistics/query và /logistics/statusFeedback",
            },
        },
    },
}

# Nghĩa ĐÃ CHỐT cho mã nhập nhằng. Rỗng là đúng hiện trạng: chưa ai đối chiếu được với hãng.
# Chỉ điền qua chot_nghia() — cần căn cứ thật, không điền bằng suy đoán.
NGHIA_DA_CHOT = {}


class ChuaChotNghia(Exception):
    """Ném khi ai đó cố lấy trạng thái của một mã nhập nhằng chưa được chốt nghĩa."""


class KetQuaAnhXa:
    """Kết quả ánh xạ một mã trạng thái của hãng.

    `trang_thai` giữ nguyên ý nghĩa CŨ (có người đang gọi) = nghĩa theo bảng tham số.
    Với mã NHẬP NHẰNG, nghĩa đó CHƯA được chốt, nên đường cập nhật đơn phải dùng
    `trang_thai_ap` (hoặc tốt hơn: `quyet_dinh()`), KHÔNG dùng `trang_thai`.
    """
    __slots__ = ("biet_ma", "trang_thai", "mo_ta_hang", "ma_goc",
                 "nhap_nhang", "do_tin_cay", "can_soat", "nguon_tai_lieu", "cac_nghia", "ma_hang")

    def __init__(self, biet_ma, trang_thai, mo_ta_hang, ma_goc,
                 nhap_nhang=False, do_tin_cay=None, can_soat=None,
                 nguon_tai_lieu=None, cac_nghia=None, ma_hang=None):
        self.ma_hang = ma_hang
        self.biet_ma = biet_ma          # False = mã lạ, chưa có trong tài liệu đã đọc
        self.trang_thai = trang_thai    # None = chỉ ghi nhận, không đổi trạng thái
        self.mo_ta_hang = mo_ta_hang
        self.ma_goc = ma_goc
        self.nhap_nhang = nhap_nhang
        self.can_soat = (not biet_ma or nhap_nhang) if can_soat is None else can_soat
        self.nguon_tai_lieu = nguon_tai_lieu
        self.cac_nghia = cac_nghia or {}
        if do_tin_cay is None:
            do_tin_cay = (TIN_NHAP_NHANG if nhap_nhang else
                          TIN_MA_LA if not biet_ma else
                          TIN_CAO if trang_thai else TIN_TRUNG_BINH)
        self.do_tin_cay = do_tin_cay

    @property
    def trang_thai_ap(self):
        """Trạng thái ĐƯỢC PHÉP áp vào đơn. Mã nhập nhằng chưa chốt nghĩa → None."""
        if self.nhap_nhang and not self.nghia_da_chot:
            return None
        return self.trang_thai

    @property
    def nghia_da_chot(self):
        """Tra sổ chốt THẬT — trả None cứng là tự nói dối về trạng thái hệ thống."""
        if not self.nhap_nhang or self.ma_hang is None:
            return None
        khoa, loi = _khoa_ma(self.ma_hang, self.ma_goc)
        return None if loi else NGHIA_DA_CHOT.get((self.ma_hang, khoa))

    def nhu_dict(self):
        return {"biet_ma": self.biet_ma, "trang_thai": self.trang_thai,
                "mo_ta_hang": self.mo_ta_hang, "ma_goc": self.ma_goc,
                "nhap_nhang": self.nhap_nhang, "do_tin_cay": self.do_tin_cay,
                "can_soat": self.can_soat, "nguon_tai_lieu": self.nguon_tai_lieu}

    def __repr__(self):
        return (f"KetQuaAnhXa(biet_ma={self.biet_ma}, trang_thai={self.trang_thai!r}, "
                f"ma_goc={self.ma_goc!r}, nhap_nhang={self.nhap_nhang}, "
                f"do_tin_cay={self.do_tin_cay!r})")


def _khoa_ma(ma_hang, ma_trang_thai):
    """Khóa tra bảng: J&T dùng số (scanTypeCode), hãng khác dùng nguyên chuỗi."""
    if ma_hang == "jt":
        try:
            return int(ma_trang_thai), None
        except (TypeError, ValueError):
            return None, "scanTypeCode không phải số"
    return ma_trang_thai, None


def anh_xa(ma_hang, ma_trang_thai):
    """Đổi mã trạng thái của hãng → trạng thái chuẩn. Mã lạ KHÔNG ném lỗi và KHÔNG đổi trạng thái."""
    bang = BANG.get(ma_hang)
    if bang is None:
        return KetQuaAnhXa(False, None, f"hãng '{ma_hang}' chưa có bảng ánh xạ", ma_trang_thai)
    khoa, loi = _khoa_ma(ma_hang, ma_trang_thai)
    if loi:
        return KetQuaAnhXa(False, None, loi, ma_trang_thai)
    if khoa not in bang:
        return KetQuaAnhXa(False, None, "mã không có trong tài liệu đã đọc", ma_trang_thai)
    mo_ta, chuan = bang[khoa]
    nn = NHAP_NHANG.get((ma_hang, khoa))
    return KetQuaAnhXa(True, chuan, mo_ta, ma_trang_thai,
                       nhap_nhang=nn is not None,
                       nguon_tai_lieu=(nn or {}).get("nguon") or NGUON_BANG.get(ma_hang),
                       cac_nghia=(nn or {}).get("nghia"), ma_hang=ma_hang)


def ma_da_biet(ma_hang):
    return sorted(BANG.get(ma_hang, {}).keys(), key=str)


def la_nhap_nhang(ma_hang, ma_trang_thai):
    khoa, loi = _khoa_ma(ma_hang, ma_trang_thai)
    return (ma_hang, khoa) in NHAP_NHANG if not loi else False


def chot_nghia(ma_hang, ma_trang_thai, khoa_nghia, nguoi_chot, can_cu):
    """Chốt nghĩa cho một mã nhập nhằng. CHỈ gọi khi có căn cứ THẬT từ hãng.

    Bắt buộc có `nguoi_chot` và `can_cu` — chốt nghĩa mà không ghi ai chốt, căn cứ gì thì lần
    sau không ai dựng lại được vì sao hệ thống hiểu mã đó như vậy (§12.1 luật 4).
    Chặn cứng: nghĩa dẫn tới trạng thái HOÀN TẤT thì KHÔNG được chốt bằng con đường này —
    kết thúc hành trình phải đến từ mã rõ nghĩa (113 Delivered, 116/117 Returned), không từ
    một mã mà tài liệu còn đang tự mâu thuẫn.
    """
    khoa, loi = _khoa_ma(ma_hang, ma_trang_thai)
    if loi:
        raise ValueError(loi)
    muc = NHAP_NHANG.get((ma_hang, khoa))
    if muc is None:
        raise KeyError(f"({ma_hang}, {ma_trang_thai}) không nằm trong sổ mã nhập nhằng")
    if khoa_nghia not in muc["nghia"]:
        raise KeyError(f"nghĩa '{khoa_nghia}' không có trong sổ; có: {sorted(muc['nghia'])}")
    if not str(nguoi_chot or "").strip() or not str(can_cu or "").strip():
        raise ValueError("chốt nghĩa phải ghi rõ ai chốt và căn cứ nào")
    tt = muc["nghia"][khoa_nghia]["trang_thai"]
    if tt in TRANG_THAI_HOAN_TAT:
        raise ValueError(
            f"nghĩa '{khoa_nghia}' dẫn tới trạng thái hoàn tất '{tt}' — cấm chốt qua đường này")
    NGHIA_DA_CHOT[(ma_hang, khoa)] = {"khoa_nghia": khoa_nghia, "trang_thai": tt,
                                      "nguoi_chot": nguoi_chot, "can_cu": can_cu,
                                      "mo_ta_hang": muc["nghia"][khoa_nghia]["mo_ta_hang"]}
    return dict(NGHIA_DA_CHOT[(ma_hang, khoa)])


def bo_chot_nghia(ma_hang=None, ma_trang_thai=None):
    """Gỡ chốt (dùng khi căn cứ bị bác, và trong bộ thử)."""
    if ma_hang is None:
        NGHIA_DA_CHOT.clear()
        return
    khoa, _ = _khoa_ma(ma_hang, ma_trang_thai)
    NGHIA_DA_CHOT.pop((ma_hang, khoa), None)


def _bay_gio():
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S%z")


class QuyetDinhAnhXa:
    """Quyết định dùng cho ĐƯỜNG CẬP NHẬT ĐƠN: giữ trọn dấu vết, nói rõ có được áp hay không."""
    __slots__ = ("ma_hang", "ma_goc", "mo_ta_goc", "su_kien_hang_goc", "nguon_tai_lieu",
                 "phien_ban_tai_lieu", "do_tin_cay", "nhap_nhang", "can_soat", "trang_thai_ap",
                 "cac_nghia", "nghia_da_chot", "nhan_luc", "ghi_chu", "biet_ma")

    def __init__(self, **kw):
        for t in self.__slots__:
            setattr(self, t, kw.get(t))

    @property
    def nhan(self):
        """Nhãn trạng thái soát của sự kiện: AMBIGUOUS / NEEDS_REVIEW / OK."""
        if self.nhap_nhang and not self.nghia_da_chot:
            return "AMBIGUOUS"
        if self.can_soat:
            return "NEEDS_REVIEW"
        return "OK"

    def nhu_dict(self):
        return {t: getattr(self, t) for t in self.__slots__} | {"nhan": self.nhan}

    def __repr__(self):
        return (f"QuyetDinhAnhXa({self.ma_hang}:{self.ma_goc!r} → {self.trang_thai_ap!r} "
                f"[{self.nhan}] tin_cay={self.do_tin_cay!r})")


def quyet_dinh(ma_hang, ma_trang_thai, su_kien_goc=None, nhan_luc=None):
    """Hàm DUY NHẤT mà đường cập nhật đơn được dùng để biến mã hãng thành trạng thái chuẩn.

    Khác `anh_xa()` ở ba chỗ, và đó là lý do nó tồn tại:
      - mã nhập nhằng CHƯA chốt nghĩa → `trang_thai_ap = None` (không đổi trạng thái đơn),
      - luôn mang theo đủ dấu vết để sau này soát lại được,
      - chặn cứng mọi đường rơi vào trạng thái HOÀN TẤT khi mã còn nhập nhằng.
    """
    ax = anh_xa(ma_hang, ma_trang_thai)
    khoa, _ = _khoa_ma(ma_hang, ma_trang_thai)
    chot = NGHIA_DA_CHOT.get((ma_hang, khoa)) if ax.nhap_nhang else None
    ghi_chu = []

    if ax.nhap_nhang:
        muc = NHAP_NHANG[(ma_hang, khoa)]
        if chot:
            tt = chot["trang_thai"]
            do_tin = TIN_TRUNG_BINH      # người chốt, không phải tài liệu → không dám ghi 'cao'
            can_soat = False
            ghi_chu.append(f"nghĩa đã chốt '{chot['khoa_nghia']}' bởi {chot['nguoi_chot']}")
        else:
            tt = None
            do_tin = TIN_NHAP_NHANG
            can_soat = True
            ghi_chu.append("mã nhập nhằng, chưa ai chốt nghĩa → KHÔNG đổi trạng thái đơn")
            ghi_chu.append(muc["ly_do"])
    else:
        tt = ax.trang_thai
        do_tin = ax.do_tin_cay
        can_soat = not ax.biet_ma
        if not ax.biet_ma:
            ghi_chu.append("mã lạ, không có trong tài liệu đã đọc → chỉ ghi nhận")

    # CHẶN CỨNG (không phụ thuộc nhánh nào ở trên): mã nhập nhằng không bao giờ được hoàn tất.
    if ax.nhap_nhang and tt in TRANG_THAI_HOAN_TAT:
        ghi_chu.append(f"CHẶN: mã nhập nhằng không được áp trạng thái hoàn tất '{tt}'")
        tt = None
        can_soat = True
        do_tin = TIN_NHAP_NHANG

    return QuyetDinhAnhXa(
        ma_hang=ma_hang, ma_goc=ma_trang_thai, mo_ta_goc=ax.mo_ta_hang,
        su_kien_hang_goc=su_kien_goc, nguon_tai_lieu=ax.nguon_tai_lieu,
        phien_ban_tai_lieu=PHIEN_BAN_TAI_LIEU.get(ma_hang, "chua-ro"),
        do_tin_cay=do_tin, nhap_nhang=ax.nhap_nhang, can_soat=can_soat,
        trang_thai_ap=tt, cac_nghia=ax.cac_nghia, nghia_da_chot=chot,
        nhan_luc=nhan_luc or _bay_gio(), ghi_chu=" | ".join(ghi_chu), biet_ma=ax.biet_ma)
