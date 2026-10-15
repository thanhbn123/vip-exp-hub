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
# ---------------------------------------------------------------------------
# G19 (AG-03) 16/10/2026 — ĐÓNG LỖ HỔNG `BAN_GIAO.md` §6.1: 13 CON SỐ CÓ NGUỒN ĐÃ VÀO BẢNG.
#
# ĐO LẠI NGUỒN **TRONG CHÍNH REPO NÀY** — không gọi hãng, không ra mạng, không credentials:
#   · `docs/VTP_YEU_CAU_BO_SUNG.md:36` · `docs/G12_VTP_KHAO_SAT.md:86` · `app/adapter_vtp.py:13`
#     → bộ mã chính thức của VTP gồm **21 mã**: 15 mã có ánh xạ + 6 mã CỐ Ý không ánh xạ
#       (102, 202, 503, 505, 508, 550), nguồn trang hãng
#       `partner2.viettelpost.vn/document/webhook` mục «Bảng danh sách trạng thái».
#   · `docs/VTP_YEU_CAU_BO_SUNG.md:80` (câu B1) → `104` = «Lấy hàng điều phối bưu tá»;
#     nhóm trạng thái CUỐI theo đoạn «Lưu ý» = 101/107/201/501/503/504; `200` = «lấy hàng
#     thành công».
#   · `docs/VTP_YEU_CAU_BO_SUNG.md:83` (câu B4) → `505` = «Yêu cầu chuyển hoàn»; `503` =
#     «Tiêu huỷ theo yêu cầu khách hàng».
#   ⇒ Nguồn trong repo NÊU TÊN **13 CON SỐ**: 101 · 102 · 104 · 107 · 200 · 201 · 202 · 501 ·
#     503 · 504 · 505 · 508 · 550.
#
# ĐIỀU QUAN TRỌNG NHẤT, NÓI THẲNG: repo này **KHÔNG chép bảng 21 mã**. Nó chép CON SỐ 21 và
# 13 cái tên. **8 con số còn lại KHÔNG hề xuất hiện ở đâu trong repo** ⇒ không thể liệt kê,
# không thể ánh xạ, và TUYỆT ĐỐI không được bịa. Đếm được, kèm giả định nói rõ:
#   21 = 15 có ánh xạ + 6 cố ý None (nguồn). Sáu mã None đều có tên. Trong 15 mã có ánh xạ,
#   nguồn chỉ nêu tên 7 con số (101, 104, 107, 200, 201, 501, 504) — GIẢ ĐỊNH cả 7 thuộc bộ 21.
#   ⇒ 21 − 13 = **8 con số thiếu**, và cả 8 đều nằm trong nhóm «có ánh xạ» của repo nguồn —
#   đúng nhóm mà bảng của ta cần nhất. Nếu `200` không thuộc bộ 21 thì con số là 9; repo không
#   đủ dữ kiện để phân xử. Dù 8 hay 9, kết luận không đổi.
#
# 13 con số đó KHÔNG cùng một mức tin cậy, nên vào HAI chỗ khác nhau — không gộp:
#   (A) ÁP ĐƯỢC — **1 mã**: `200` «lấy hàng thành công» → `lay_hang`. Nghĩa nói thẳng trong
#       nguồn, và không phải trạng thái hoàn tất nên đoán nhầm cũng không đóng đơn.
#   (B) CHƯA XÁC MINH — **12 mã**: có SỐ THẬT nhưng CHƯA có nghĩa nghiệp vụ đủ để ánh xạ ⇒ sổ
#       `CHUA_XAC_MINH` ⇒ nhãn `NEEDS_REVIEW`, KHÔNG đổi trạng thái đơn. Gồm `104` (tài liệu tự
#       mâu thuẫn về việc nó có phải trạng thái cuối không) và 6 mã mà chính repo nguồn cố ý
#       không ánh xạ.
#
# NGUYÊN VĂN CỦA HÃNG **KHÔNG** CÓ TRONG REPO: mọi mô tả dưới đây là DIỄN GIẢI của bản khảo sát
# trong repo, không phải câu chữ của hãng. Cờ dưới đây nói đúng điều đó, và chỉ được lật khi có
# người thật sự đọc trang hãng rồi đối chiếu từng mã.
VTP_CO_NGUYEN_VAN_HANG = False

NGUON_VTP = ("docs/VTP_YEU_CAU_BO_SUNG.md §1·B1·B4 · docs/G12_VTP_KHAO_SAT.md §2·§4 · "
             "docs/G09_FINAL_REPORT.md §4 — khảo sát GIÁN TIẾP repo thanhbn123/vip-viettelpost, "
             "dẫn trang hãng partner2.viettelpost.vn/document/webhook mục «Bảng danh sách "
             "trạng thái»; CHÍNH DỰ ÁN NÀY CHƯA ĐỌC TRANG HÃNG VÀ CHƯA GỌI HÃNG LẦN NÀO")

# Mã THẬT của hãng (khoá SỐ, đúng kiểu `ORDER_STATUS`). Giá trị `None` = chỉ ghi nhận.
VTP_MA = {
    101: ("Thuộc nhóm TRẠNG THÁI CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói", None),
    102: ("Mã có thật; repo nguồn CỐ Ý không ánh xạ — nghĩa nghiệp vụ KHÔNG có trong repo này", None),
    104: ("Lấy hàng điều phối bưu tá — TÀI LIỆU TỰ MÂU THUẪN: bảng đánh dấu là trạng thái cuối,"
          " đoạn «Lưu ý» thì không", None),
    107: ("Thuộc nhóm TRẠNG THÁI CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói", None),
    200: ("Lấy hàng thành công", "lay_hang"),
    201: ("Thuộc nhóm TRẠNG THÁI CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói", None),
    202: ("Mã có thật; repo nguồn CỐ Ý không ánh xạ — nghĩa nghiệp vụ KHÔNG có trong repo này", None),
    501: ("Thuộc nhóm TRẠNG THÁI CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói", None),
    503: ("Tiêu huỷ theo yêu cầu khách hàng (mã CUỐI) — repo nguồn cố ý không ánh xạ", None),
    504: ("Thuộc nhóm TRẠNG THÁI CUỐI theo đoạn «Lưu ý» — hướng cuối KHÔNG được nói", None),
    505: ("Yêu cầu chuyển hoàn — dùng cho CẢ «khách từ chối» lẫn «người gửi yêu cầu hoàn»,"
          " hai nghĩa này chưa phân biệt được", None),
    508: ("Mã có thật; repo nguồn CỐ Ý không ánh xạ — nghĩa nghiệp vụ KHÔNG có trong repo này", None),
    550: ("Mã có thật; repo nguồn CỐ Ý không ánh xạ — nghĩa nghiệp vụ KHÔNG có trong repo này", None),
}

# Khoá của BỘ MÔ PHỎNG của chính dự án — KHÔNG phải mã hãng, và tên khoá tự khai điều đó.
VTP_MA_MOCK = {
    "cho_lay": ("MOCK chờ lấy", "cho_lay"),
    "lay_hang": ("MOCK đã lấy", "lay_hang"),
    "dang_giao": ("MOCK đang giao", "dang_giao"),
    "giao_thanh_cong": ("MOCK giao thành công", "giao_thanh_cong"),
    "giao_that_bai": ("MOCK giao thất bại", "giao_that_bai"),
    "hoan_hang": ("MOCK hoàn hàng", "hoan_hang"),
}

# Hai bộ khoá KHÔNG đụng nhau (số của hãng vs tên chuẩn của bộ mô phỏng) nên gộp được mà không
# che nhau. Gộp chứ không thay: bỏ `VTP_MA_MOCK` là làm chết đường MOCK của adapter VTP.
BANG = {"jt": JT_MA, "vtp": dict(VTP_MA, **VTP_MA_MOCK)}


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
TIN_CHUA_XAC_MINH = "chua_xac_minh"  # MÃ CÓ THẬT nhưng nghĩa CHƯA xác minh ⇒ cấm đoán
TIN_MA_LA = "ma_la"              # mã không có trong tài liệu đã đọc
MUC_TIN_CAY = (TIN_CAO, TIN_TRUNG_BINH, TIN_NHAP_NHANG, TIN_CHUA_XAC_MINH, TIN_MA_LA)

# TRẦN ĐỘ TIN CẬY THEO HÃNG. `TIN_CAO` chỉ dành cho mã đọc TRỰC TIẾP từ tài liệu của hãng.
# Bảng VTP (G19) dựng từ bản khảo sát GIÁN TIẾP trong repo — chưa ai đọc trang hãng — nên trần
# của nó là `trung_binh`. Đây là chốt BẰNG MÃ, không phải lời dặn: lật `VTP_CO_NGUYEN_VAN_HANG`
# lên True (chỉ khi thật sự đã đọc và đối chiếu từng mã) thì trần mới mở.
TRAN_TIN_CAY = {"jt": TIN_CAO,
                "vtp": TIN_CAO if VTP_CO_NGUYEN_VAN_HANG else TIN_TRUNG_BINH}

# Trạng thái coi là KẾT THÚC hành trình. Mã nhập nhằng tuyệt đối không được rơi vào đây.
TRANG_THAI_HOAN_TAT = ("giao_thanh_cong", "hoan_hang")

NGUON_JT = ("open.jtexpress.vn/apiDoc/logistics/query + /logistics/statusFeedback"
            " · đọc bằng trình duyệt 14/10/2026")
# Nguồn của BẢNG ánh xạ từng hãng. VTP: mã THẬT đầu tiên đã vào bảng (G19) nhưng nguồn là bản
# khảo sát gián tiếp trong repo — KHÔNG phải trang hãng đọc trực tiếp. Nói đúng mức đang có.
NGUON_BANG = {"jt": NGUON_JT, "vtp": NGUON_VTP}
PHIEN_BAN_TAI_LIEU = {"jt": "doc-2026-10-14",
                      "vtp": "khao-sat-gian-tiep-2026-10-15 (tài liệu hãng 29/09/2026 theo khảo sát)"}

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

# ============================================================================
# G19 — SỔ MÃ CÓ THẬT NHƯNG **CHƯA XÁC MINH NGHĨA** (`CHUA_XAC_MINH`)
#
# Khác `NHAP_NHANG` ở chỗ nào, và vì sao phải là sổ RIÊNG:
#   · `NHAP_NHANG` = tài liệu nói HAI nghĩa ngược chiều, và cả hai đều ĐÃ đọc được ⇒ có cái để
#     chốt, chỉ chờ người có thẩm quyền. Nhãn: `AMBIGUOUS`.
#   · `CHUA_XAC_MINH` = biết CHẮC mã đó có thật, nhưng NGHĨA thì repo này KHÔNG có ⇒ không có
#     nghĩa nào để chốt cả. Nhãn: `NEEDS_REVIEW`.
#
# Vì sao không gộp vào `NHAP_NHANG`: gộp là tự nói dối rằng ta đã đọc được hai nghĩa. Và
# `chot_nghia()` chỉ chốt được cái có trong sổ nhập nhằng — nhét mã chưa có nghĩa vào đó là mở
# đường cho người sau "chốt" một nghĩa mà chính họ vừa nghĩ ra.
#
# HỆ QUẢ BẮT BUỘC (cài bằng mã, không bằng lời dặn): mã trong sổ này
#   → `trang_thai_ap` LUÔN `None` (không đổi trạng thái đơn),
#   → `can_soat` LUÔN `True` ⇒ nhãn `NEEDS_REVIEW`,
#   → `do_tin_cay = TIN_CHUA_XAC_MINH`,
#   → và bị CHẶN CỨNG khỏi mọi trạng thái HOÀN TẤT kể cả khi sau này ai đó điền giá trị vào bảng.
# `loai` nói VÌ SAO chưa xác minh được — ba loại khác nhau, không gộp:
#   · `chua_co_nghia`        — repo không có nghĩa nghiệp vụ nào cho mã này.
#   · `huong_cuoi_khong_ro`  — biết là trạng thái CUỐI, nhưng KHÔNG biết cuối theo hướng nào.
#   · `mau_thuan_tai_lieu`   — chính tài liệu mâu thuẫn về mã này.
# ============================================================================
CHUA_XAC_MINH = {}

_CHUA_CO_NGHIA = ("Mã có thật (nằm trong bộ mã chính thức của hãng) nhưng NGHĨA NGHIỆP VỤ "
                  "KHÔNG có trong repo này — repo nguồn CỐ Ý để trống ánh xạ và lý do từng mã "
                  "cũng không được chép sang. Đoán một nghĩa là bịa.")
_HUONG_CUOI = ("Tài liệu xếp mã này vào nhóm TRẠNG THÁI CUỐI, nhưng KHÔNG nói cuối theo hướng "
               "GIAO THÀNH CÔNG hay HOÀN HÀNG. Đoán một trong hai là đúng loại sai đắt nhất: "
               "đơn hoàn bị coi là đã giao (hoặc ngược lại) và không ai soát lại.")

for _ma in (102, 202, 508, 550):
    CHUA_XAC_MINH[("vtp", _ma)] = {"loai": "chua_co_nghia", "ly_do": _CHUA_CO_NGHIA,
                                   "nguon": NGUON_VTP}
for _ma in (101, 107, 201, 501, 504):
    CHUA_XAC_MINH[("vtp", _ma)] = {"loai": "huong_cuoi_khong_ro", "ly_do": _HUONG_CUOI,
                                   "nguon": NGUON_VTP}
# 503 và 505: nghĩa CÓ một phần, nhưng đúng phần cần nhất thì thiếu — và tài liệu tự cảnh báo.
CHUA_XAC_MINH[("vtp", 503)] = {
    "loai": "chua_co_nghia",
    "ly_do": ("«Tiêu huỷ theo yêu cầu khách hàng» — mã CUỐI, và nghĩa này KHÔNG trùng nghĩa với "
              "huỷ đơn hay hoàn hàng. Ánh xạ nó về `hoan_hang` là gán một nghiệp vụ khác vào "
              "đơn; repo nguồn cố ý không ánh xạ. Câu B4 hỏi hãng vẫn chưa có trả lời."),
    "nguon": NGUON_VTP}
CHUA_XAC_MINH[("vtp", 505)] = {
    "loai": "chua_co_nghia",
    "ly_do": ("«Yêu cầu chuyển hoàn» dùng cho CẢ «khách từ chối nhận» lẫn «người gửi yêu cầu "
              "hoàn» (lý do 43) — hai nghiệp vụ khác nhau trên cùng một mã. Ánh xạ bừa về "
              "`hoan_hang` là đẩy đơn sang hoàn khi khách chỉ đổi lịch (đúng cảnh báo của B4)."),
    "nguon": NGUON_VTP}
# 104: ca mâu thuẫn — G09 P4b chỉ định đưa vào `NHAP_NHANG`. KHÔNG làm được trong phạm vi G19:
# `app/thu/thu_webhook_jt.py:1132-1133` khoá sổ đó vào J&T (`assertIn(ma, tth.JT_MA if
# ma_hang == "jt" else {})`), nên thêm một mục `vtp` là làm HỎNG một bộ thử đang xanh mà G19
# KHÔNG được phép sửa. ĐÃ ĐO: `python3 app/thu/thu_webhook_jt.py` → mã thoát 1, 1 ca hỏng.
# Xem `docs/G19_VTP_CODES.md` §5. Hiệu quả an toàn như nhau: không đổi trạng thái đơn + cần soát.
CHUA_XAC_MINH[("vtp", 104)] = {
    "loai": "mau_thuan_tai_lieu",
    "ly_do": ("TÀI LIỆU TỰ MÂU THUẪN: bảng trạng thái đánh dấu 104 là trạng thái CUỐI, đoạn "
              "«Lưu ý» ngay dưới liệt kê trạng thái cuối là 101/107/201/501/503/504 — KHÔNG có "
              "104, mà 104 lại đứng TRƯỚC 200 (lấy hàng thành công) theo nghiệp vụ. Coi 104 là "
              "cuối thì chặn mọi sự kiện sau nó và đơn đứng im trong khi hàng đã đi."),
    "nguon": NGUON_VTP}


class ChuaChotNghia(Exception):
    """Ném khi ai đó cố lấy trạng thái của một mã nhập nhằng chưa được chốt nghĩa."""


class KetQuaAnhXa:
    """Kết quả ánh xạ một mã trạng thái của hãng.

    `trang_thai` giữ nguyên ý nghĩa CŨ (có người đang gọi) = nghĩa theo bảng tham số.
    Với mã NHẬP NHẰNG, nghĩa đó CHƯA được chốt, nên đường cập nhật đơn phải dùng
    `trang_thai_ap` (hoặc tốt hơn: `quyet_dinh()`), KHÔNG dùng `trang_thai`.
    """
    __slots__ = ("biet_ma", "trang_thai", "mo_ta_hang", "ma_goc",
                 "nhap_nhang", "chua_xac_minh", "do_tin_cay", "can_soat", "nguon_tai_lieu",
                 "cac_nghia", "ma_hang")

    def __init__(self, biet_ma, trang_thai, mo_ta_hang, ma_goc,
                 nhap_nhang=False, chua_xac_minh=False, do_tin_cay=None, can_soat=None,
                 nguon_tai_lieu=None, cac_nghia=None, ma_hang=None):
        self.ma_hang = ma_hang
        self.biet_ma = biet_ma          # False = mã lạ, chưa có trong tài liệu đã đọc
        self.trang_thai = trang_thai    # None = chỉ ghi nhận, không đổi trạng thái
        self.mo_ta_hang = mo_ta_hang
        self.ma_goc = ma_goc
        self.nhap_nhang = nhap_nhang
        self.chua_xac_minh = chua_xac_minh   # True = mã có thật nhưng nghĩa CHƯA xác minh
        self.can_soat = ((not biet_ma or nhap_nhang or chua_xac_minh)
                         if can_soat is None else can_soat)
        self.nguon_tai_lieu = nguon_tai_lieu
        self.cac_nghia = cac_nghia or {}
        if do_tin_cay is None:
            do_tin_cay = (TIN_NHAP_NHANG if nhap_nhang else
                          TIN_CHUA_XAC_MINH if chua_xac_minh else
                          TIN_MA_LA if not biet_ma else
                          TIN_CAO if trang_thai else TIN_TRUNG_BINH)
        self.do_tin_cay = do_tin_cay

    @property
    def trang_thai_ap(self):
        """Trạng thái ĐƯỢC PHÉP áp vào đơn.

        Ba đường dẫn tới `None`, và cả ba đều là CHỐT CỨNG chứ không phải hệ quả tình cờ:
        mã CHƯA XÁC MINH nghĩa (G19), mã nhập nhằng chưa ai chốt nghĩa, và mã chỉ ghi nhận.
        """
        if self.chua_xac_minh:
            return None
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
                "nhap_nhang": self.nhap_nhang, "chua_xac_minh": self.chua_xac_minh,
                "do_tin_cay": self.do_tin_cay,
                "can_soat": self.can_soat, "nguon_tai_lieu": self.nguon_tai_lieu}

    def __repr__(self):
        return (f"KetQuaAnhXa(biet_ma={self.biet_ma}, trang_thai={self.trang_thai!r}, "
                f"ma_goc={self.ma_goc!r}, nhap_nhang={self.nhap_nhang}, "
                f"do_tin_cay={self.do_tin_cay!r})")


def _khoa_ma(ma_hang, ma_trang_thai):
    """Khóa tra bảng: J&T và VTP dùng SỐ, hãng khác dùng nguyên chuỗi.

    VÌ SAO VTP CŨNG PHẢI CHUẨN HOÁ (G19): `ORDER_STATUS` của VTP là số, nhưng nó đi qua JSON
    của webhook nên có thể tới dạng số (`200`) hoặc dạng chuỗi (`"200"`). Trước G19 bảng VTP chỉ
    có khoá chuỗi của bộ mô phỏng, nên chuyện này không lộ ra. Nay bảng có mã SỐ THẬT: nếu không
    chuẩn hoá thì một sự kiện thật gửi `"200"` sẽ rơi IM LẶNG vào nhánh «mã lạ» — đúng dạng hỏng
    im lặng mà §12.2 cấm. Chỉ chuỗi TOÀN SỐ bị quy về số, nên khoá của bộ mô phỏng (`"cho_lay"`)
    không bị đụng tới.
    """
    if ma_hang == "jt":
        try:
            return int(ma_trang_thai), None
        except (TypeError, ValueError):
            return None, "scanTypeCode không phải số"
    if ma_hang == "vtp" and isinstance(ma_trang_thai, str):
        _s = ma_trang_thai.strip()
        if _s.isdigit():
            return int(_s), None
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
    cx = CHUA_XAC_MINH.get((ma_hang, khoa))
    do_tin = None
    if chuan and not nn and not cx and TRAN_TIN_CAY.get(ma_hang) == TIN_TRUNG_BINH:
        # Nguồn của bảng hãng này là GIÁN TIẾP ⇒ hạ trần, không được khai 'cao' (xem TRAN_TIN_CAY).
        do_tin = TIN_TRUNG_BINH
    return KetQuaAnhXa(True, chuan, mo_ta, ma_trang_thai,
                       nhap_nhang=nn is not None,
                       chua_xac_minh=cx is not None,
                       do_tin_cay=do_tin,
                       nguon_tai_lieu=(nn or cx or {}).get("nguon") or NGUON_BANG.get(ma_hang),
                       cac_nghia=(nn or {}).get("nghia"), ma_hang=ma_hang)


def ma_da_biet(ma_hang):
    return sorted(BANG.get(ma_hang, {}).keys(), key=str)


def ma_chua_xac_minh(ma_hang):
    """Mã CÓ THẬT nhưng nghĩa CHƯA xác minh của một hãng — nhóm KHÔNG được đoán."""
    return sorted(k for (h, k) in CHUA_XAC_MINH if h == ma_hang)


def ly_do_chua_xac_minh(ma_hang, ma_trang_thai):
    """Vì sao mã này chưa ánh xạ được. None = không nằm trong sổ."""
    khoa, loi = _khoa_ma(ma_hang, ma_trang_thai)
    if loi:
        return None
    return (CHUA_XAC_MINH.get((ma_hang, khoa)) or {}).get("ly_do")


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
                 "phien_ban_tai_lieu", "do_tin_cay", "nhap_nhang", "chua_xac_minh", "can_soat",
                 "trang_thai_ap", "cac_nghia", "nghia_da_chot", "nhan_luc", "ghi_chu", "biet_ma")

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
      - mã CHƯA XÁC MINH nghĩa (G19) → cũng `None`, và nhãn `NEEDS_REVIEW`,
      - luôn mang theo đủ dấu vết để sau này soát lại được,
      - chặn cứng mọi đường rơi vào trạng thái HOÀN TẤT khi mã còn nhập nhằng HOẶC chưa xác minh.
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
    elif ax.chua_xac_minh:
        muc = CHUA_XAC_MINH[(ma_hang, khoa)]
        if ax.trang_thai is not None:
            # Không được xảy ra: bảng đã gán một giá trị cho mã CHƯA XÁC MINH. Vẫn phải NÓI RA
            # chứ không bỏ im lặng — im lặng ở đây là một ánh xạ bừa đi vào đơn mà không ai thấy.
            ghi_chu.append(f"CHẶN: mã CHƯA XÁC MINH bị bảng gán '{ax.trang_thai}'"
                           " — KHÔNG áp, bỏ giá trị đó")
        tt = None
        do_tin = TIN_CHUA_XAC_MINH
        can_soat = True
        ghi_chu.append("mã có thật nhưng CHƯA XÁC MINH nghĩa → KHÔNG đoán, không đổi trạng thái đơn")
        ghi_chu.append(muc["ly_do"])
    else:
        tt = ax.trang_thai
        do_tin = ax.do_tin_cay
        can_soat = not ax.biet_ma
        if not ax.biet_ma:
            ghi_chu.append("mã lạ, không có trong tài liệu đã đọc → chỉ ghi nhận")

    # CHẶN CỨNG (không phụ thuộc nhánh nào ở trên): mã nhập nhằng HOẶC chưa xác minh thì KHÔNG
    # BAO GIỜ được hoàn tất. Đặt ở đây chứ không chỉ dựa vào bảng: bảng có thể bị sửa, còn chốt
    # này thì không — và đây đúng là loại sai đắt nhất (đơn có vấn đề bị coi là đã giao xong).
    if (ax.nhap_nhang or ax.chua_xac_minh) and tt in TRANG_THAI_HOAN_TAT:
        ghi_chu.append(f"CHẶN: mã chưa ngã ngũ không được áp trạng thái hoàn tất '{tt}'")
        tt = None
        can_soat = True
        do_tin = TIN_NHAP_NHANG if ax.nhap_nhang else TIN_CHUA_XAC_MINH

    return QuyetDinhAnhXa(
        ma_hang=ma_hang, ma_goc=ma_trang_thai, mo_ta_goc=ax.mo_ta_hang,
        su_kien_hang_goc=su_kien_goc, nguon_tai_lieu=ax.nguon_tai_lieu,
        phien_ban_tai_lieu=PHIEN_BAN_TAI_LIEU.get(ma_hang, "chua-ro"),
        do_tin_cay=do_tin, nhap_nhang=ax.nhap_nhang, chua_xac_minh=ax.chua_xac_minh,
        can_soat=can_soat,
        trang_thai_ap=tt, cac_nghia=ax.cac_nghia, nghia_da_chot=chot,
        nhan_luc=nhan_luc or _bay_gio(), ghi_chu=" | ".join(ghi_chu), biet_ma=ax.biet_ma)
