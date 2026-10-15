# G04/G13 — Adapter J&T Express Việt Nam.
# Dựng THEO TÀI LIỆU CÔNG KHAI đọc được ngày 14/10/2026 tại open.jtexpress.vn/apiDoc:
#   - Headers: apiAccount (số), digest (chuỗi ký), timestamp (ms, UTC+7)
#   - digest = base64( md5( bizContent-JSON + privateKey ) )  — md5 ra BYTES rồi base64
#   - Body: application/x-www-form-urlencoded, trường bizContent = chuỗi JSON nghiệp vụ
#   - Tạo đơn: POST .../webopenplatformapi/api/order/addOrder
#     (test: demoopenapi.jtexpress.vn, prod: ylopenapi.jtexpress.vn — chép nguyên văn từ docs)
#   - bizContent tối thiểu: customerCode, password, txlogisticId (mã đơn khách, KHÔNG trùng),
#     orderType, serviceType, payType, productType, goodsType, sender{...}, receiver{...},
#     packageInfo{weight}
# TRẠNG THÁI: DOCUMENTED + MOCK_VERIFIED. Đường LIVE bị khóa BA lớp ĐỘC LẬP:
#   (1) `CHO_PHEP_LIVE = False` — chặn ngay trong `__init__`;
#   (2) chốt D-9 — ánh xạ `area` chưa được hãng xác nhận, chặn tại chỗ dựng bizContent;
#   (3) `TRANSPORT_THAT_DA_VIET = False` — lớp HTTP thật CHƯA được viết, và ba thao tác
#       (`cancelOrder`, `getShippingFee`, `getShippingLabel`) còn chưa xác minh được đường dẫn.
# KHÔNG tự suy đoán gì ngoài docs.
#
# ── G13 (15/10/2026) THÊM GÌ SO VỚI G04, VÀ VÌ SAO ──────────────────────────────────────────
# Trước G13 file này chỉ có createOrder là thật sự có "hợp đồng yêu cầu" (url + headers + body);
# năm thao tác còn lại là hàm mock trả về một dòng, KHÔNG dựng yêu cầu, KHÔNG đọc gói trả lời,
# và không nói ra chỗ nào còn thiếu dữ kiện. G13 đóng đúng khoảng đó:
#   · bảng `DUONG_API`: mỗi thao tác ghi rõ đường dẫn ĐÃ ĐỌC ĐƯỢC hay CHƯA, kèm nguồn. Thao tác
#     chưa xác minh đường dẫn thì bị CHẶN ở mọi môi trường khác `mock` — không dựng bừa URL;
#   · `yeu_cau_tra_hanh_trinh` / `yeu_cau_huy_don`: dựng đủ gói yêu cầu (không gửi) để bộ thử
#     kiểm được chữ ký và thân yêu cầu của cả ba thao tác, không chỉ createOrder;
#   · `doc_goi_tra_loi`: đọc gói `{code,msg,data}` → `KetQuaHang`, mã lạ về `KHONG_RO`,
#     KHÔNG đoán nghĩa, KHÔNG bịa mã vận đơn khi hãng không trả về;
#   · `tien_nguyen_vnd`: tiền là INTEGER đồng (§16). Số thập phân bị TỪ CHỐI, không làm tròn im
#     lặng — làm tròn một đồng COD là lệch tiền thật mà không có lỗi nào báo;
#   · kịch bản mock (`MOCK-HONG…`, `MOCK-HETGIO…`, `MOCK-KHONGCO…`, `ghi_chu=demo_force_*`) để
#     đo được CẢ BA kết cục, nhánh đơn-trùng và nhánh không-tìm-thấy trên chính adapter này
#     thay vì phải dựng adapter giả;
#   · `TRANSPORT_THAT_DA_VIET = False` nói THẲNG ra: mở `CHO_PHEP_LIVE` cũng KHÔNG chạy được
#     vì chưa có lớp HTTP. Để im lặng thì người đọc tưởng chỉ còn thiếu credentials.
#
# ── G16-A (15/10/2026) NỐI ADAPTER VÀO LỚP HTTP THẬT ────────────────────────────────────────
# G13 dừng ở "chưa có lớp HTTP". G16-A nối vào lớp đó qua ĐÚNG hợp đồng §36
# (`app/http_jt.py::gui_form`, do AG-02 sở hữu — tệp này CHỈ GỌI, không viết lại):
#   · `_chuan_bi_goi_that()`: ba cửa ĐỘC LẬP của một lượt gọi thật — (1) môi trường đã được
#     Owner cấp quyền chưa, (2) đường dẫn API đã xác minh chưa, (3) lớp HTTP đã có chưa.
#     Cửa thứ tư (chốt D-9 `area`) vẫn nằm ở chỗ dựng bizContent, canh MỌI đường.
#   · `_goi_that()`: gọi `transport.goi()` để việc thử lại do `transport.py` quyết định, rồi
#     đọc `TraLoiHTTP` → `KetQuaHang`. Ba kết cục KHÔNG bị gộp: `ok` / hãng TỪ CHỐI /
#     KHÔNG BIẾT (hết giờ, mạng chập, 5xx ⇒ `timeout=True`).
#   · `UY_QUYEN_MOI_TRUONG` (§37): `mock` MỞ; `sandbox`/`production` TỪ CHỐI kèm lý do đọc
#     được. Đây là cửa RIÊNG, không phải `CHO_PHEP_LIVE`: mở `CHO_PHEP_LIVE` (đang là False và
#     KHÔNG agent nào được mở) vẫn KHÔNG mở được sandbox/production, và viết xong lớp HTTP cũng
#     KHÔNG mở. Ba việc đó là ba việc khác nhau.
#   · `dau_thoi_gian_ms` vá `L2-N2` (docs/QA_G13_G15.md §L2.2): mốc NAIVE nay được gắn UTC+7
#     TƯỜNG MINH thay vì lặng lẽ theo múi giờ máy — docstring cũ hứa đúng điều đó mà mã không ép.
#   · `kiem_chu_ky()`: phép ĐỘC LẬP kiểm lại chữ ký + mốc thời gian của một gói yêu cầu ĐÃ DỰNG,
#     tính từ chính chuỗi `bizContent` NẰM TRONG GÓI — bắt được cả ca "ký một chuỗi, gửi chuỗi
#     khác".
# Mọi phép đo của G16-A dùng **stub cục bộ trên `127.0.0.1`**. KHÔNG có lượt gọi hãng nào, kể cả
# sandbox: `V-G09-01` + `V-13906-05` CHƯA CẤP (`docs/SHARED_CONTRACTS.md` §25, §40).
import base64
import datetime as _dt
import hashlib
import json
import random
import threading

import loi_hang
import transport
from adapter import CarrierAdapter, KetQuaHang, dang_ky

CONTENT_TYPE = "application/x-www-form-urlencoded"
BANG_MA = "utf-8"
# Nguồn (trang "极兔API简介", đọc lại bằng trình duyệt 14/10/2026), nguyên văn:
#   "使用http协议表单提交的方式进行信息交互，字符编码默认统一采用UTF-8，
#    数据格式：application/x-www-form-urlencoded"
#   "digest=base64(md5(业务参数的Json+privateKey))，注：先md5得到字节数组，再base64加密"
# → md5 phải ra MẢNG BYTE trước rồi mới base64. Lấy md5 hexdigest rồi base64 là SAI chữ ký.
# Header timestamp: "时间戳，毫秒 / 时区：UTC+7" → mili giây, múi giờ UTC+7.
MUI_GIO_GIO = 7

# =================================================================================================
# 0. MÔI TRƯỜNG — BA MỨC, HAI MỨC CHƯA ĐƯỢC CẤP QUYỀN (hợp đồng §37)
# =================================================================================================
# NGUỒN CHÂN LÝ DUY NHẤT của cửa này là `app/cau_hinh.py::jt_kiem_moi_truong` (AG-00 sở hữu,
# §39). Ban đầu G16-A tự dựng một bảng quyền trong tệp này; AG-00 chốt 15/10/2026 rằng "đang
# chạy ở môi trường nào" và "được phép gọi tới đâu" là quyết định của NGƯỜI VẬN HÀNH, không phải
# của mã adapter. Hai bảng quyền song song là hai bảng sẽ lệch nhau — nên bảng ở đây đã GỠ, chỉ
# còn hai hàm bọc mỏng gọi sang `cau_hinh`. Giữ hàm bọc để tệp này chỉ có MỘT chỗ trả lời câu
# "môi trường này chạy được chưa", và để bộ thử không phải biết chi tiết của `cau_hinh`.
#
# Điều KHÔNG đổi, và là điều §37 muốn: ba việc sau là BA việc khác nhau, mở một cái không mở
# hai cái kia —
#   1. `adapter.CHO_PHEP_LIVE` (cửa của lớp nền, chặn lúc DỰNG adapter);
#   2. `cau_hinh.JT_CHO_PHEP_SANDBOX` / `JT_CHO_PHEP_PRODUCTION` (cửa MÔI TRƯỜNG, chặn lúc GỬI;
#      cố ý KHÔNG đọc từ biến môi trường nên không bật nhầm được);
#   3. lớp HTTP thật (§36) có trên đĩa hay chưa.
# Cả ba đều đang ĐÓNG. Không agent nào được mở cái nào (§39, §40).
MOCK = "mock"
SANDBOX = "sandbox"
PRODUCTION = "production"
MOI_TRUONG_HOP_LE = (MOCK, SANDBOX, PRODUCTION)


def moi_truong_duoc_chay(moi_truong) -> bool:
    """Môi trường này đã được Owner cấp quyền chạy chưa (hỏi `cau_hinh`, KHÔNG tự phán).

    `None`/chuỗi rỗng được đổi thành `""` TRƯỚC khi hỏi: `cau_hinh.jt_kiem_moi_truong(None)` hiểu
    `None` là "dùng mặc định" và trả về `mock` — tức một giá trị THIẾU lại được đọc thành một môi
    trường ĐƯỢC PHÉP. Ở cửa này, thiếu phải là KHÔNG hợp lệ.
    """
    import cau_hinh
    mt = "" if moi_truong is None else str(moi_truong).strip().lower()
    return bool(cau_hinh.jt_kiem_moi_truong(mt)[0])


def ly_do_moi_truong(moi_truong) -> str:
    """Lý do ĐỌC ĐƯỢC vì sao môi trường này chạy được hoặc không (nguyên văn từ `cau_hinh`)."""
    import cau_hinh
    mt = "" if moi_truong is None else str(moi_truong).strip().lower()
    return str(cau_hinh.jt_kiem_moi_truong(mt)[1])


def chan_moi_truong_chua_duoc_cap(moi_truong):
    """TỪ CHỐI chạy `sandbox`/`production` khi Owner chưa cấp. Kèm lý do, không im lặng (§37).

    Ném `PermissionError` — cùng họ với khoá `CHO_PHEP_LIVE` của lớp nền, để nơi gọi chỉ phải
    hiểu MỘT loại "chưa được phép chạy". Khác `ChuaXacNhanTaiLieu`: đây là **chưa được PHÉP**,
    kia là **chưa biết ĐỦ** — hai việc phải sửa theo hai cách khác nhau.
    """
    mt = str(moi_truong or "").strip().lower()
    if moi_truong_duoc_chay(mt):
        return
    raise PermissionError(
        f"Adapter jt: môi trường '{mt}' bị TỪ CHỐI. {ly_do_moi_truong(mt)} "
        "Mặc định của hệ là 'mock'. Cờ 'đã viết lớp HTTP' và cờ 'cho phép live' KHÔNG mở được "
        "cửa này — xem docs/G16_JT_API.md §BLOCKED.")


# ── ĐIỂM CUỐI THAY THẾ: chỉ để bộ thử dựng stub CỤC BỘ, và chỉ nhận vòng lặp nội bộ ────────────
# Vì sao cần: muốn đo ĐƯỜNG GỬI THẬT (chữ ký, thân form, ba kết cục, chống trùng) mà KHÔNG gọi
# hãng, thì phải trỏ được vào một máy chủ trên `127.0.0.1`. Không có seam này thì bộ thử buộc
# phải giả lập ở tầng hàm — đúng thứ §12.1 cảnh báo: đo bằng bản giả của chính thứ cần đo.
#
# Đây KHÔNG phải cửa mở LIVE, và được canh bằng ba lớp:
#   1. giá trị mặc định là `None`, và đường chạy thật không bao giờ đặt nó;
#   2. `DungDiemCuoiTam` TỪ CHỐI mọi địa chỉ không phải vòng lặp nội bộ ⇒ kể cả dùng sai thì
#      cũng không có lượt gọi nào ra Internet;
#   3. cửa MÔI TRƯỜNG (`chan_moi_truong_chua_duoc_cap`) kiểm TRƯỚC khi gửi, và bộ thử đi vào
#      đường gửi ở DƯỚI cửa đó — nó không mở `sandbox` để tiện cho mình.
DIEM_CUOI_GHI_DE = None
HOST_VONG_LAP = ("127.0.0.1", "localhost", "[::1]")


class DungDiemCuoiTam:
    """CHỈ dùng trong bộ thử: trỏ mọi URL đã xác minh vào một stub cục bộ trong lúc chạy.

    TỪ CHỐI địa chỉ ngoài vòng lặp nội bộ — một seam tiện tay ở đây là một đường gọi hãng thật
    mở toang, đúng thứ `V-G09-01`/`V-13906-05` đang chặn.
    """

    def __init__(self, goc):
        self.goc = str(goc or "").rstrip("/")
        self.cu = None
        self._kiem()

    def _kiem(self):
        """Tự tách host bằng chuỗi, KHÔNG `import urllib` — `adapter*.py` bị bộ dò AST của
        `thu_qa_jt.py` (AG-01) cấm mọi import thuộc họ mạng, và lệnh cấm đó là ĐÚNG: một tệp
        adapter không có việc gì phải biết phân tích URL.
        """
        goc = self.goc
        for scheme in ("http://", "https://"):
            if goc.startswith(scheme):
                con = goc[len(scheme):]
                break
        else:
            raise ValueError(f"điểm cuối thử phải là http/https, nhận {self.goc!r}")
        host = con.split("/")[0].split("@")[-1]
        if host.startswith("["):                      # IPv6: [::1]:8080
            host = host.split("]")[0] + "]"
        else:
            host = host.split(":")[0]
        if host not in HOST_VONG_LAP:
            raise ValueError(
                f"TỪ CHỐI: điểm cuối thử {self.goc!r} không phải vòng lặp nội bộ {HOST_VONG_LAP}"
                " — seam này chỉ để dựng stub cục bộ, không phải để gọi ra ngoài")

    def __enter__(self):
        global DIEM_CUOI_GHI_DE
        self.cu = DIEM_CUOI_GHI_DE
        DIEM_CUOI_GHI_DE = self.goc
        return self.goc

    def __exit__(self, *a):
        global DIEM_CUOI_GHI_DE
        DIEM_CUOI_GHI_DE = self.cu
        return False


# =================================================================================================
# 1. ĐƯỜNG DẪN API — CHỈ GHI CÁI ĐÃ ĐỌC ĐƯỢC, KÈM NGUỒN VÀ MỨC XÁC NHẬN
# =================================================================================================
# Vì sao phải có bảng này thay vì rải URL trong từng hàm: câu hỏi "thao tác này đã đủ dữ kiện để
# gọi thật chưa" phải trả lời được bằng MÁY, không bằng việc đọc lại chú thích. Mỗi dòng ở đây
# là một lời khai: đọc ở đâu, ngày nào, và đã đọc được tới đâu.
MUC_DA_DOC = "da-doc-trong-tai-lieu"
MUC_CHUA_XAC_NHAN = "chua-xac-nhan"

HOST_API = {
    "sandbox": "https://demoopenapi.jtexpress.vn",
    "production": "https://ylopenapi.jtexpress.vn",
}

DUONG_TAO_DON = "/webopenplatformapi/api/order/addOrder"
DUONG_TRA_HANH_TRINH = "/webopenplatformapi/api/logistics/trace"
# Huỷ đơn: câu 27 của docs/JT_CAU_HOI_CHINH_THUC.md chép đường dẫn ở dạng TƯƠNG ĐỐI
# (`/api/order/cancelOrder`). Tiền tố cổng (`/webopenplatformapi`) của riêng API này CHƯA được
# xác minh, nên KHÔNG tự ghép. Xem `DUONG_API["cancelOrder"]`.
DUONG_HUY_DON_TUONG_DOI_DA_DOC = "/api/order/cancelOrder"

NGUON_TAO_DON = ("open.jtexpress.vn/apiDoc/orderserve/create — đọc bằng trình duyệt 14/10/2026;"
                 " URL đầy đủ đã có từ G04")
NGUON_TRA_HANH_TRINH = ("open.jtexpress.vn/apiDoc/logistics/query — đọc lại bằng trình duyệt"
                        " 14/10/2026: tài liệu CÓ cho URL đầy đủ")
NGUON_HUY_DON = ("open.jtexpress.vn/apiDoc/orderserve/cancel — đọc 15/10/2026; đường dẫn chỉ"
                 " chép được ở dạng tương đối (docs/JT_CAU_HOI_CHINH_THUC.md câu 27),"
                 " tiền tố cổng chưa xác minh")
NGUON_TINH_PHI = ("open.jtexpress.vn/apiDoc/fees/calculatingFees — trang CÓ trong trình đơn"
                  " nhưng CHƯA chép được đường dẫn yêu cầu và bảng tham số")
NGUON_IN_NHAN = ("open.jtexpress.vn/apiDoc/vip/printOrder — trang CÓ trong trình đơn nhưng"
                 " CHƯA chép được đường dẫn yêu cầu; trang 批量打印面单 (in hàng loạt) còn chưa"
                 " mở được nội dung")
NGUON_GET_ORDER = ("tài liệu công khai CHƯA nêu API tra đơn theo txlogisticId — câu hỏi 26 của"
                   " docs/JT_CAU_HOI_CHINH_THUC.md đang chờ J&T trả lời")

DUONG_API = {
    "createOrder": {"duong": DUONG_TAO_DON, "muc": MUC_DA_DOC, "nguon": NGUON_TAO_DON},
    "trackOrder": {"duong": DUONG_TRA_HANH_TRINH, "muc": MUC_DA_DOC,
                   "nguon": NGUON_TRA_HANH_TRINH},
    "cancelOrder": {"duong": None, "muc": MUC_CHUA_XAC_NHAN, "nguon": NGUON_HUY_DON,
                    "duong_tuong_doi_da_doc": DUONG_HUY_DON_TUONG_DOI_DA_DOC},
    "getShippingFee": {"duong": None, "muc": MUC_CHUA_XAC_NHAN, "nguon": NGUON_TINH_PHI},
    "getShippingLabel": {"duong": None, "muc": MUC_CHUA_XAC_NHAN, "nguon": NGUON_IN_NHAN},
    "getOrder": {"duong": None, "muc": MUC_CHUA_XAC_NHAN, "nguon": NGUON_GET_ORDER},
}

# URL đầy đủ, giữ nguyên tên cũ (G04) để không phá người gọi đang có.
URL_TAO_DON = {mt: HOST_API[mt] + DUONG_TAO_DON for mt in HOST_API}
URL_TRA_HANH_TRINH = {mt: HOST_API[mt] + DUONG_TRA_HANH_TRINH for mt in HOST_API}

# Tra cứu hành trình: tài liệu nêu rõ billcodes ngăn cách bằng dấu phẩy, MỘT LƯỢT tối đa 30
# vận đơn (mã lỗi 145003502 khi vượt).
SO_VAN_DON_MOI_LUOT = 30

# Bốn trường credentials J&T. Chỉ TÊN trường ở đây — KHÔNG bao giờ có giá trị.
TRUONG_CREDENTIAL = ("apiAccount", "privateKey", "customerCode", "password")

# Lớp HTTP thật (`app/http_jt.py`, AG-02 sở hữu theo §36) — tệp này CHỈ GỌI nó.
#
# G13 để cờ này là hằng `False` viết tay, vì khi đó chưa ai viết lớp HTTP. G16-A đổi thành một
# phép DÒ: cờ chỉ `True` khi tệp của AG-02 có thật trên đĩa **và** có đúng hàm hợp đồng §36.
# Lý do đổi: một hằng viết tay là lời khai không ai kiểm — nó nói "chưa viết" cả khi tệp đã có,
# rồi người đọc kết luận sai về việc còn phải làm.
#
# Cờ này là ẢNH CHỤP lúc nạp module (đúng như mọi hằng cấp module khác). Đường CHẠY không dựa vào
# ảnh chụp: `_chuan_bi_goi_that()` gọi `http_jt_dang_dung()` để hỏi lại mỗi lượt.
def _nap_http_jt():
    """Nạp `app/http_jt.py` nếu nó có trên đĩa VÀ có đúng hàm hợp đồng §36. Không có ⇒ None.

    Nạp MUỘN (trong hàm) chứ không ở đầu tệp: lúc AG-03 viết mã này, tệp của AG-02 chưa tồn tại,
    và `import` ở đầu tệp sẽ làm cả adapter chết vì một tệp của làn khác. Nạp muộn cũng đúng cho
    lúc chạy thật: tệp xuất hiện thì lượt gọi kế tiếp dùng được ngay.

    KHÔNG `except Exception` trần ở đây: nếu tệp có mà lỗi khi nạp thì đó là chuyện phải NHÌN
    THẤY, không phải chuyện im lặng coi như "chưa viết".
    """
    try:
        import http_jt
    except ImportError:
        return None
    if not callable(getattr(http_jt, "gui_form", None)):
        return None
    return http_jt


def _co_http_jt():
    """Có lớp HTTP thật trên đĩa không. (Ảnh chụp; đường chạy hỏi lại từng lượt.)"""
    return _nap_http_jt() is not None


TRANSPORT_THAT_DA_VIET = _co_http_jt()

# Bản TIÊM cho bộ thử: `None` = dùng tệp thật. Chỉ `ThayHttpJtTam` đặt giá trị này, và chỉ bộ
# thử gọi nó. Có bản tiêm vì lúc viết G16-A, `app/http_jt.py` chưa có trên đĩa; nhưng bộ thử
# không được vì thế mà bỏ qua phần nối — nó chạy trên một lớp HTTP ĐÚNG hợp đồng §36 (stub cục
# bộ trên 127.0.0.1), rồi khi tệp thật xuất hiện thì chạy thêm trên chính tệp thật.
_http_jt_tam = None


def http_jt_dang_dung():
    """Module HTTP sẽ dùng cho lượt gọi kế tiếp: bản TIÊM nếu có, ngược lại tệp thật, else None."""
    return _http_jt_tam if _http_jt_tam is not None else _nap_http_jt()


def ten_transport_dang_dung():
    """Tên lớp HTTP đang dùng — để kết quả tự khai nó đo bằng thứ gì, không đoán hộ người đọc."""
    if _http_jt_tam is not None:
        return "tam-thay-the"
    return "app/http_jt.py" if _co_http_jt() else ""


class ThayHttpJtTam:
    """CHỈ dùng trong bộ thử: tiêm một lớp HTTP thay `app/http_jt.py` cho các lượt gọi kế tiếp.

    Không phải cửa mở LIVE: cửa môi trường (`chan_moi_truong_chua_duoc_cap`) vẫn kiểm TRƯỚC, và
    stub chỉ được bind trên `127.0.0.1`. Dùng `with` để không rò sang ca khác.
    """

    def __init__(self, module):
        self.module = module
        self.cu = None

    def __enter__(self):
        global _http_jt_tam
        self.cu = _http_jt_tam
        _http_jt_tam = self.module
        return self.module

    def __exit__(self, *a):
        global _http_jt_tam
        _http_jt_tam = self.cu
        return False


# Tài liệu tạo đơn ghi `city` là trường KHÔNG bắt buộc, để null được với địa chỉ hai cấp.
# Hệ này KHÔNG gửi `city` lượt nào — đo được, ghi lại để không ai tưởng là có gửi.
CITY_CO_GUI = False

# TÊN trường lý do huỷ trong bizContent của `/api/order/cancelOrder`. Rỗng = CHƯA ĐỌC ĐƯỢC.
# Bảng mã lỗi của huỷ đơn có `145003089 — 取消原因不能为空` (thiếu lý do huỷ là bị từ chối), nên
# chắc chắn CÓ trường này; nhưng tên nó thì tài liệu chưa chép được ⇒ để RỖNG và chặn, KHÔNG
# đoán ("reason"? "cancelReason"? "remark"? — đoán sai thì hãng từ chối và mình chẩn đoán nhầm
# hướng, đúng cái đã xảy ra với dạng `password` ở câu hỏi 22).
TRUONG_LY_DO_HUY = ""


class ChuaXacNhanTaiLieu(Exception):
    """DỪNG có chủ ý: thiếu dữ kiện đã xác minh để dựng/gửi yêu cầu ĐÚNG.

    Khác `PermissionError` (khoá an toàn) và khác `NormalizedCarrierError` (lỗi của HÃNG):
    đây là lỗi của CHÍNH MÌNH — ta chưa biết đủ để gọi. Dựng bừa rồi để hãng từ chối là cách
    biến một câu hỏi chưa trả lời thành một lượt gọi hỏng mà không học được gì.
    """

    def __init__(self, thao_tac, thieu, moi_truong=None):
        self.thao_tac = thao_tac
        self.thieu = list(thieu)
        self.moi_truong = moi_truong
        super().__init__(
            f"J&T/{thao_tac}: DỪNG — môi trường {moi_truong!r} chưa chạy được thao tác này. "
            "Còn thiếu: " + "; ".join(self.thieu))


def url_cua(thao_tac, moi_truong):
    """URL ĐÃ XÁC MINH của một thao tác, hoặc None. `mock` luôn None — không có đường ra ngoài."""
    if moi_truong == "mock":
        return None
    if DIEM_CUOI_GHI_DE is not None:
        # Điểm cuối THAY THẾ (chỉ bộ thử đặt được, xem `DungDiemCuoiTam`). Thao tác chưa xác
        # minh đường dẫn vẫn phải trả None: ghi đè điểm cuối KHÔNG được biến một đường dẫn chưa
        # biết thành một đường dẫn có thật.
        duong = (DUONG_API.get(thao_tac) or {}).get("duong")
        return None if duong is None else DIEM_CUOI_GHI_DE.rstrip("/") + duong
    if thao_tac == "createOrder":
        return URL_TAO_DON.get(moi_truong)
    if thao_tac == "trackOrder":
        return URL_TRA_HANH_TRINH.get(moi_truong)
    return None


def chan_duong_chua_xac_nhan(thao_tac, moi_truong):
    """Chặn khi đường dẫn API của thao tác chưa được xác minh (mọi môi trường khác `mock`)."""
    if moi_truong == "mock":
        return
    if url_cua(thao_tac, moi_truong) is None:
        d = DUONG_API.get(thao_tac) or {}
        raise ChuaXacNhanTaiLieu(
            thao_tac,
            ["đường dẫn API đầy đủ CHƯA được xác minh — nguồn đã đọc: "
             + str(d.get("nguon") or "không rõ")],
            moi_truong)


# =================================================================================================
# 2. CHỮ KÝ VÀ GÓI YÊU CẦU (giữ nguyên công thức G04 — đã có ca kiểm)
# =================================================================================================
def ky_digest(biz_content_json: str, private_key: str) -> str:
    """Đúng công thức docs: base64(md5-bytes(bizContent + privateKey))."""
    return base64.b64encode(
        hashlib.md5((biz_content_json + private_key).encode(BANG_MA)).digest()).decode()


def dau_thoi_gian_ms(bay_gio=None) -> int:
    """Mốc thời gian MILI GIÂY theo múi giờ UTC+7 như tài liệu yêu cầu.

    §12.2 ("mọi mốc thời gian phải mang múi giờ"): tính tường minh bằng UTC+7, không mượn múi
    giờ của máy đang chạy — máy chủ đặt UTC thì lệch 7 tiếng mà không báo lỗi gì.

    ── VÁ `L2-N2` (15/10/2026, G16-A) ────────────────────────────────────────────────────────
    `docs/QA_G13_G15.md` §L2.2 đo được: mốc truyền vào KHÔNG mang `tzinfo` thì `t.timestamp()`
    hiểu nó theo **múi giờ của TIẾN TRÌNH**, nên `TZ=UTC` lệch **đúng 7 tiếng** so với
    `TZ=Asia/Ho_Chi_Minh` — trong khi docstring này hứa "không mượn múi giờ của máy". Lời hứa
    đúng cho đường mặc định (`now(tz)`) nhưng KHÔNG được ép cho mốc truyền vào. Docstring nói
    một đằng, mã làm một nẻo: đúng khuôn "thứ dùng để kiểm chứng tự nói sai".

    Nay mốc naive được **gắn UTC+7 tường minh**. Vì sao gắn chứ không ném: mọi lời gọi trong mã
    hiện tại đều truyền mốc CÓ múi giờ (đã soát: `harness_hang.py`, `thu_hop_dong_jt.py`,
    `thu_g03.py`, `thu_qa_jt.py`), nên không có ca nào đang sống bị đổi hành vi; còn ném lỗi chỉ
    đổi "im lặng sai" thành "nổ ở một chỗ khác" mà không nói được mốc ĐÚNG là gì. Gắn UTC+7 là
    điều docstring vẫn luôn hứa.

    Hệ quả ĐÃ BIẾT, ghi để không ai phải đo lại: ca `thu_qa_jt.test_b4` của AG-01 ghim hành vi
    CŨ (naive hiểu theo máy). Nó chỉ đỏ khi tiến trình chạy với `TZ=UTC`/`Etc/UTC`; mặc định
    của bộ chạy không đặt `TZ`, nên vẫn xanh. Xem `docs/G16_JT_API.md` §5.
    """
    tz = _dt.timezone(_dt.timedelta(hours=MUI_GIO_GIO))
    t = bay_gio or _dt.datetime.now(tz)
    if t.tzinfo is None:
        t = t.replace(tzinfo=tz)
    return int(t.timestamp() * 1000)


def kiem_chu_ky(goi_yeu_cau, credentials, luc_goi_ms=None, sai_so_ms=None) -> dict:
    """KIỂM LẠI chữ ký + mốc thời gian của một gói yêu cầu ĐÃ DỰNG. Trả dict, KHÔNG ném.

    Đây là phép kiểm ĐỘC LẬP có chủ ý: nó tính lại digest từ **chính chuỗi `bizContent` nằm
    trong gói** và so với header `digest`. Nhờ vậy nó bắt được cả ca "ký một chuỗi rồi gửi một
    chuỗi khác" — ca mà một hàm ký tự-kiểm-chính-mình không bao giờ thấy, và là ca làm hãng trả
    `145003031` (业务参数签名失败) trong khi mọi ca thử "chữ ký đúng công thức" vẫn xanh.

    Trả:
      `khop`               — digest trong header có bằng digest tính lại từ chuỗi trong gói không
      `digest_tinh_lai`    — giá trị tính lại (KHÔNG phải bí mật: nó là hàm của bizContent + khoá,
                             nhưng bản thân khoá không suy ngược được từ nó; vẫn chỉ nên dùng
                             trong bộ thử, không ghi ra log)
      `co_bizcontent`      — gói có chuỗi bizContent để đối chiếu không
      `thoi_gian_ms`       — mốc trong header, đã đổi thành int; None nếu không đọc được
      `thoi_gian_hop_le`   — mốc là mili giây (13 chữ số) và nằm trong `sai_so_ms` quanh `luc_goi_ms`
                             (bỏ qua phép so khoảng nếu thiếu `luc_goi_ms`/`sai_so_ms`)
    """
    headers = (goi_yeu_cau or {}).get("headers") or {}
    biz = (goi_yeu_cau or {}).get("bizContent")
    co_biz = isinstance(biz, str)
    tinh_lai = ky_digest(biz, str((credentials or {}).get("privateKey") or "")) if co_biz else None
    ra = {
        "co_bizcontent": co_biz,
        "digest_tinh_lai": tinh_lai,
        "thoi_gian_ms": None,
        "thoi_gian_hop_le": False,
    }
    ra["khop"] = bool(co_biz and headers.get("digest") == tinh_lai)
    chuoi_ts = str(headers.get("timestamp") or "").strip()
    if chuoi_ts.isdigit():
        ra["thoi_gian_ms"] = int(chuoi_ts)
        du_moc = len(chuoi_ts) == 13
        if luc_goi_ms is None or sai_so_ms is None:
            ra["thoi_gian_hop_le"] = du_moc
        else:
            ra["thoi_gian_hop_le"] = du_moc and abs(int(chuoi_ts) - int(luc_goi_ms)) <= int(sai_so_ms)
    return ra


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


# =================================================================================================
# 3. TIỀN — INTEGER ĐỒNG, KHÔNG LÀM TRÒN IM LẶNG (hợp đồng §16)
# =================================================================================================
def _khong_phai_so_that(so) -> bool:
    """NaN / ±vô cùng: `float()` đọc được nhưng KHÔNG `int()` được (ValueError/OverflowError).
    Chặn ở đây để lỗi ra đúng mã chuẩn `THAM_SO_SAI`, không phải một ValueError trần."""
    return so != so or so in (float("inf"), float("-inf"))


def tien_nguyen_vnd(gia_tri, ten_truong):
    """Ép một giá trị tiền về INTEGER đồng. Sai kiểu thì NỔ, không làm tròn, không đoán.

    Vì sao không `int(...)` trần: `int(15000.7)` = 15000 — nuốt 0,7 đồng mà không ai biết;
    `int("15000.5")` thì nổ bằng ValueError khó hiểu. Ở đây số thập phân CÓ phần lẻ bị từ chối
    tường minh, vì hợp đồng §16 nói tiền không có phần thập phân — thấy phần lẻ nghĩa là đơn vị
    đã bị chọn sai ở đâu đó, và chỗ đó phải sửa chứ không phải chỗ này làm tròn.
    """
    if gia_tri is None or gia_tri == "":
        return 0
    if isinstance(gia_tri, bool):     # bool là int trong python — chặn riêng, "True đồng" là vô nghĩa
        raise loi_hang.NormalizedCarrierError(
            loi_hang.THAM_SO_SAI, thong_diep=f"{ten_truong} là kiểu bool, không phải số tiền",
            hang="jt")
    if isinstance(gia_tri, int):
        n = gia_tri
    elif isinstance(gia_tri, float):
        if _khong_phai_so_that(gia_tri):
            raise loi_hang.NormalizedCarrierError(
                loi_hang.THAM_SO_SAI,
                thong_diep=f"{ten_truong}={gia_tri!r} không phải số thật (NaN/vô cùng)",
                hang="jt")
        if gia_tri != int(gia_tri):
            raise loi_hang.NormalizedCarrierError(
                loi_hang.THAM_SO_SAI,
                thong_diep=(f"{ten_truong}={gia_tri!r} có phần thập phân — tiền phải là INTEGER"
                            " đồng (§16). KHÔNG làm tròn: làm tròn ở đây là lệch tiền thật."),
                hang="jt")
        n = int(gia_tri)
    else:
        chuoi = str(gia_tri).strip()
        if not chuoi.isdigit():
            # Thử đọc như số thập phân để nói ĐÚNG lý do: "15000.5" là THẬP PHÂN (lỗi đơn vị),
            # còn "mười nghìn" mới là chuỗi lạ (lỗi dữ liệu vào). Chẩn đoán sai ở đây làm người
            # sửa đi nhầm hướng — đúng cái đã xảy ra với dạng `password` ở câu hỏi 22.
            try:
                so = float(chuoi)
            except ValueError:
                so = None
            # `float("nan")`/`float("inf")` đọc được nhưng KHÔNG so sánh/int được — chặn ở đây,
            # nếu không thì `int(so)` ném ValueError/OverflowError trần, mất mã lỗi chuẩn.
            if so is None or _khong_phai_so_that(so):
                raise loi_hang.NormalizedCarrierError(
                    loi_hang.THAM_SO_SAI,
                    thong_diep=(f"{ten_truong}={chuoi!r} không phải chuỗi số nguyên đồng —"
                                " từ chối, không đoán"),
                    hang="jt")
            if so != int(so):
                raise loi_hang.NormalizedCarrierError(
                    loi_hang.THAM_SO_SAI,
                    thong_diep=(f"{ten_truong}={chuoi!r} có phần thập phân — tiền phải là INTEGER"
                                " đồng (§16). KHÔNG làm tròn: làm tròn ở đây là lệch tiền thật."),
                    hang="jt")
            n = int(so)          # "15000.0": giá trị vẫn là số nguyên đồng
        else:
            n = int(chuoi)
    if n < 0:
        raise loi_hang.NormalizedCarrierError(
            loi_hang.THAM_SO_SAI, thong_diep=f"{ten_truong}={n} là số âm", hang="jt")
    return n


# =================================================================================================
# 4. LỖI VÀ GÓI TRẢ LỜI
# =================================================================================================
# Tên trường mã vận đơn trong `data` của gói trả lời. CHỈ có `billCode` là đã đọc được trong tài
# liệu (nó xuất hiện trong `details` của tra hành trình và trong bảng tham số). Không có tên nào
# khác được suy đoán thêm: đoán sai ở đây nghĩa là bịa ra một mã vận đơn không tồn tại.
TRUONG_MA_VAN_DON = ("billCode",)

# ── HAI MÃ HTTP MÀ HAI LỚP BẮT BUỘC PHẢI ĐỒNG Ý (AG-00 chốt 15/10/2026) ───────────────────────
# `loi_hang.tu_http` nói `408 → HET_GIO` và `429 → QUA_HAN_MUC`, **cả hai `co_the_thu_lai=True`**.
# `http_jt` từng xếp **mọi** 4xx là `LoiVinhVien` (vĩnh viễn) — kể cả hai mã này. Hai lớp phát
# hai câu trả lời khác nhau cho cùng một lượt là đúng khuôn "lệch im lặng".
#
# AG-00 đã chốt: **cả 408 và 429 là TẠM THỜI.** Lý do: 408 = máy chủ không nhận kịp yêu cầu,
# 429 = vượt hạn mức — cả hai là "thử lại sau", KHÔNG phải "yêu cầu sai". Xếp chúng vĩnh viễn là
# **bỏ im lặng một việc lẽ ra thành công**; còn lý do ban đầu ("backoff 0,2 s quá ngắn để có nghĩa
# với hạn mức") là lập luận để đổi CÁCH CHỜ, không phải để đổi PHÂN LOẠI. AG-02 đã tách hai mã
# này ra (`LoiTamThoi` + gợi ý `cho_giay` lấy từ `Retry-After`, `transport.goi()` lấy max với
# backoff rồi kẹp trần `transport.CHO_TOI_DA`), và **không** nới bất kỳ 4xx nào khác.
#
# Vì sao adapter VẪN cần hằng này dù `http_jt` đã đổi: chỗ ép `co_the_thu_lai=False` bên dưới khoá
# theo LOẠI NGOẠI LỆ, mà loại ngoại lệ là chuyện nội bộ của lớp dưới. Một ngày nào đó một nhánh
# 408/429 trả `LoiVinhVien` (ví dụ `Retry-After` dị dạng) thì adapter sẽ lặng lẽ hạ `QUA_HAN_MUC`
# xuống "không thử lại" — đúng chiều lệch mà AG-00 đã bác. Hằng này khoá theo **MÃ HTTP**, tức
# khoá theo SỰ THẬT GIAO THỨC, nên nó đứng vững bất kể lớp dưới cài đặt thế nào.
# Ca canh chống lệch: `thu_adapter_jt.H_NoiTransportThat_TrenStubCucBo.test_h5b…` — đo CẢ HAI mã,
# trên CẢ HAI lớp, và đo cả kết quả adapter phát ra.
MA_HTTP_HAI_LOP_PHAI_DONG_Y = (408, 429)


def goi_y_loi_chuan(loi) -> dict:
    """Dict lỗi chuẩn cho `KetQuaHang.tho['loi_chuan']` — ĐÚNG hình dạng hợp đồng §5.

    Một chỗ duy nhất dựng dict này để mọi kết quả lỗi của adapter có cùng hình dạng.

    LỊCH SỬ, ghi lại để không ai phải đoán: G13 từng phát CẢ HAI khoá `ma_chuan` **và** `ma`,
    vì khi đó `don_hang._la_khong_tim_thay()` đọc `ma` còn `NormalizedCarrierError.nhu_dict()`
    phát `ma_chuan` — lệch nhau mà KHÔNG có lỗi nào báo. AG-00 chốt 15/10/2026: **`ma_chuan` là
    tên CHUẨN**, `don_hang.py` là bên sai và đã được vá (đọc `ma_chuan` trước, giữ `ma` làm lớp
    lùi TẠM cho adapter ngoài làn này). Nên bí danh `ma` ở đây đã được GỠ: adapter chỉ phát hình
    dạng hợp đồng. Bí danh là thứ sống mãi nếu không ai gỡ, và mỗi bí danh là thêm một tên nữa
    để hai bên lệch nhau.
    """
    return dict(loi.nhu_dict())


def ket_qua_tu_loi(loi, mock=False) -> KetQuaHang:
    """NormalizedCarrierError → KetQuaHang, GIỮ phân biệt 'hãng từ chối' và 'không biết'.

    `HET_GIO` (mạng đứt, hết giờ, 5xx) là "KHÔNG BIẾT kết quả" ⇒ `timeout=True`. Gộp nó vào
    "hãng từ chối" là cách nhanh nhất để một đơn đã vào hãng bị coi là chưa vào rồi gửi lại.
    """
    return KetQuaHang(False, timeout=(loi.ma_chuan == loi_hang.HET_GIO),
                      loi=("MOCK J&T: " if mock else "") + str(loi),
                      tho={"mock": bool(mock), "hang": "jt", "thao_tac": loi.thao_tac,
                           "loi_chuan": goi_y_loi_chuan(loi)})


def ket_qua_het_gio(thao_tac, thong_diep, mock=False) -> KetQuaHang:
    """Kết cục thứ ba: KHÔNG BIẾT kết quả. Tuyệt đối không được coi là thành công."""
    return ket_qua_tu_loi(loi_hang.NormalizedCarrierError(
        loi_hang.HET_GIO, thong_diep=thong_diep, hang="jt", thao_tac=thao_tac), mock=mock)


def lay_ma_van_don(data):
    """Lấy mã vận đơn từ `data` của gói trả lời, chỉ theo tên trường ĐÃ ĐỌC ĐƯỢC.
    Không thấy ⇒ None (nói thẳng là không thấy), KHÔNG bịa."""
    if isinstance(data, list):
        for phan in data:
            ma = lay_ma_van_don(phan)
            if ma:
                return ma
        return None
    if not isinstance(data, dict):
        return None
    for ten in TRUONG_MA_VAN_DON:
        gt = str(data.get(ten) or "").strip()
        if gt:
            return gt
    return None


def doc_than_tra_loi(than):
    """Thân thô (`bytes` từ lớp HTTP, §36) → `(goi, ghi_chu)`.

    Trả `(None, lý_do)` khi KHÔNG đọc được, và **không đoán**: thân rỗng, không giải mã được
    UTF-8, hay không phải JSON (trang HTML của proxy chẳng hạn) đều là "không đọc được", không
    phải "thất bại của hãng". `doc_goi_tra_loi(None, …, http_status=…)` sẽ phân loại tiếp — và
    nếu mã HTTP là 5xx thì kết cục đúng là KHÔNG BIẾT kết quả, không phải "hãng từ chối".
    """
    if isinstance(than, (bytes, bytearray)):
        try:
            chuoi = bytes(than).decode(BANG_MA)
        except UnicodeDecodeError:
            return None, f"thân trả lời không giải mã được bằng {BANG_MA}"
    elif than is None:
        return None, "không có thân trả lời"
    else:
        chuoi = str(than)
    chuoi = chuoi.strip()
    if not chuoi:
        return None, "thân trả lời RỖNG"
    try:
        return json.loads(chuoi), ""
    except ValueError:
        return None, "thân trả lời không phải JSON (có thể là trang HTML của proxy/máy chủ trung gian)"


def doc_goi_tra_loi(goi, thao_tac=None, http_status=None) -> KetQuaHang:
    """Đọc gói trả lời J&T `{code, msg, data}` → `KetQuaHang`.

    Quy ước thành/bại của hãng (mọi trang tài liệu ghi giống nhau): `code == "1"` là THÀNH CÔNG,
    khác "1" là thất bại và lý do nằm ở `msg`. Mã lạ ⇒ `KHONG_RO` + KHÔNG thử lại.

    `http_status` khác 2xx thì phân loại theo HTTP TRƯỚC (thân trả lời của một lượt 502 thường
    không phải JSON của hãng), và 429/408/5xx mới là loại thử lại được.
    """
    if http_status is not None and not (200 <= int(http_status) < 300):
        return ket_qua_tu_loi(loi_hang.tu_http(
            http_status, hang="jt", thao_tac=thao_tac,
            thong_diep=f"J&T trả HTTP {int(http_status)} — thân trả lời không dùng để đoán mã"))
    loi = loi_hang.doc_tra_loi_jt(goi, thao_tac=thao_tac, http_status=http_status)
    if loi is not None:
        return ket_qua_tu_loi(loi)
    data = goi.get("data") if isinstance(goi, dict) else None
    ma_van_don = lay_ma_van_don(data)
    tho = {"mock": False, "hang": "jt", "thao_tac": thao_tac, "ma_van_don_da_doc": ma_van_don}
    if ma_van_don is None:
        # Thành công mà không đọc được mã vận đơn: KHÔNG bịa mã, và KHÔNG gọi là thất bại —
        # hãng đã xác nhận đơn. Gắn cờ để nơi gọi biết còn thiếu số vận đơn.
        tho["thieu_ma_van_don"] = True
        tho["canh_bao"] = ("hãng xác nhận thành công nhưng gói trả lời không có trường mã vận"
                           f" đơn nào trong {list(TRUONG_MA_VAN_DON)} — cần bổ sung tên trường"
                           " đã đọc được từ tài liệu, KHÔNG bịa mã")
    return KetQuaHang(True, ma_van_don=ma_van_don, tho=tho)


# =================================================================================================
# 5. CHỐT CHẶN D-9: ánh xạ `area` CHƯA ĐƯỢC HÃNG XÁC NHẬN
# =================================================================================================
# Anh Thành chốt 15/10/2026: "Chưa chốt cách ánh xạ `area` cho đến khi hãng xác nhận."
#
# AG-03 đo 15/10 trên `open.jtexpress.vn/apiDoc/orderserve/create` (bảng tham số và ví dụ
# nằm CÙNG MỘT TRANG): ví dụ của CHÍNH HÃNG đặt **quận vào `city`** và **phường vào `area`**
# — NGƯỢC với ánh xạ đang dùng trong `TRUONG_HANH_CHINH`. Và hệ này hiện **không gửi `city`**
# lượt nào. Đọc theo cách khác (địa chỉ hai cấp từ 2025) cũng ra `area` = phường/xã.
# **Cả hai cách đọc đều không ra "quận".**
#
# KHÔNG đổi ánh xạ ở đây — đổi lúc này là thay một giả định bằng một giả định khác. Chỉ
# CHẶN, để giả định không lặng lẽ đi ra đường LIVE. Chi tiết: docs/G12_VTP_KHAO_SAT.md §5.
ANH_XA_AREA_DA_XAC_NHAN = False
NGUON_XAC_NHAN_AREA = ""          # ai nói · ngày nào · kênh nào. Rỗng = chưa xác nhận.
CAP_HANH_CHINH_CHO_AREA = "quan-huyen"

CAP_HOP_LE = ("quan-huyen", "phuong-xa")
DAI_NGUON_TOI_THIEU = 20
TU_GIU_CHO = ("todo", "tbd", "n/a", "na", "?", "chua biet", "chưa biết", "xxx", "...",
              "sau", "updating", "fixme")


def chot_chan_anh_xa_area(moi_truong, da_xac_nhan=None, nguon=None, cap=None):
    """Chặn đường LIVE khi ánh xạ `area` chưa được J&T xác nhận (D-9).

    MOCK luôn đi qua. Mọi môi trường khác phải qua đủ BA cửa:
      1. cờ `ANH_XA_AREA_DA_XAC_NHAN` còn False ⇒ chặn. Mặc định là CHẶN, không phải cho
         qua kèm cảnh báo — cảnh báo là thứ người ta học cách bỏ qua.
      2. cờ True nhưng nguồn rỗng / là chuỗi giữ chỗ / quá ngắn ⇒ chặn.
      3. cấp hành chính không thuộc danh sách hợp lệ ⇒ chặn.

    Cửa 2 dùng danh sách ĐEN, cửa 3 dùng danh sách TRẮNG — theo câu hỏi phân biệt của §12.2:
    quên một từ giữ chỗ thì chỉ cho qua một chuỗi vô hại; quên một cấp khỏi danh sách trắng
    thì kết quả là BỊ CHẶN, tức là an toàn.

    Tham số để `None` ⇒ đọc hằng của module (đường chạy thật). Truyền tường minh ⇒ dùng giá
    trị truyền vào (đường bộ thử), nhờ vậy ca thử không phải vá hằng toàn cục.
    """
    if moi_truong == "mock":
        return

    da = ANH_XA_AREA_DA_XAC_NHAN if da_xac_nhan is None else da_xac_nhan
    ng = NGUON_XAC_NHAN_AREA if nguon is None else nguon
    cp = CAP_HANH_CHINH_CHO_AREA if cap is None else cap

    def _chan(ly_do):
        raise loi_hang.NormalizedCarrierError(
            loi_hang.THAM_SO_SAI,
            thong_diep=(
                "CHỐT CHẶN D-9 — ánh xạ trường `area` của J&T CHƯA ĐƯỢC HÃNG XÁC NHẬN, "
                "nên không được gửi đơn thật. " + ly_do + " "
                "Cần J&T trả lời câu hỏi 28 (docs/JT_CAU_HOI_CHINH_THUC.md): với địa chỉ "
                "hành chính HAI CẤP của Việt Nam từ 2025, `prov` và `area` phải điền chính "
                "xác chuỗi nào, và có danh mục địa danh chuẩn tải về được không. "
                "Lưu ý: ví dụ trong chính tài liệu tạo đơn đặt QUẬN vào `city` và PHƯỜNG "
                "vào `area` — ngược với ánh xạ đang dùng. "
                "Có trả lời rồi thì đặt ANH_XA_AREA_DA_XAC_NHAN=True, điền "
                "NGUON_XAC_NHAN_AREA (ai nói · ngày nào · ở đâu) và CAP_HANH_CHINH_CHO_AREA."),
            hang="jt", thao_tac="createOrder")

    if not da:
        _chan("Cờ ANH_XA_AREA_DA_XAC_NHAN đang là False.")
    chuoi = str(ng or "").strip()
    if not chuoi:
        _chan("Cờ đã đặt True nhưng NGUON_XAC_NHAN_AREA còn RỖNG — "
              "không có nguồn thì không có xác nhận.")
    thap = chuoi.lower()
    if len(chuoi) < DAI_NGUON_TOI_THIEU or any(t == thap for t in TU_GIU_CHO):
        _chan("NGUON_XAC_NHAN_AREA đang là chuỗi giữ chỗ hoặc quá ngắn "
              f"({len(chuoi)} ký tự, cần tối thiểu {DAI_NGUON_TOI_THIEU}) — "
              "phải ghi rõ ai xác nhận, ngày nào, bằng kênh nào.")
    if cp not in CAP_HOP_LE:
        _chan(f"CAP_HANH_CHINH_CHO_AREA = {cp!r} không thuộc danh sách hợp lệ {CAP_HOP_LE}.")


# =================================================================================================
# 6. KỊCH BẢN MOCK — ép ba kết cục và hai nhánh lỗi đã đọc được từ tài liệu
# =================================================================================================
# Vì sao cần: nhánh `chua_vao` của đối soát và nhánh đơn-trùng chỉ chạy được nếu mock TẠO RA
# ĐƯỢC chúng. Trước G13 hai nhánh đó chỉ kiểm được bằng adapter GIẢ, nghĩa là mã thật của
# adapter không hề đi qua chúng (§12.1: đo bằng chính thứ sẽ chạy thật).
MA_MOCK_HONG = "MOCK-HONG"          # tiền tố mã vận đơn → ép hãng TỪ CHỐI
MA_MOCK_HET_GIO = "MOCK-HETGIO"     # tiền tố → ép HẾT GIỜ (không biết kết quả)
MA_MOCK_KHONG_THAY = "MOCK-KHONGCO"  # tiền tố → mã 999002000 (未找到数据 → KHONG_TIM_THAY)
GHI_CHU_EP_HONG = "demo_force_fail"
GHI_CHU_EP_HET_GIO = "demo_force_timeout"
GHI_CHU_EP_TRUNG = "demo_force_trung"


def kich_ban_mock(*chuoi):
    """Đọc kịch bản ép từ các chuỗi (mã vận đơn / ghi chú). Trả None nếu không ép gì."""
    for x in chuoi:
        s = str(x or "").strip()
        if not s:
            continue
        if s == GHI_CHU_EP_HONG or s.startswith(MA_MOCK_HONG):
            return "hong"
        if s == GHI_CHU_EP_HET_GIO or s.startswith(MA_MOCK_HET_GIO):
            return "het_gio"
        if s == GHI_CHU_EP_TRUNG:
            return "trung"
        if s.startswith(MA_MOCK_KHONG_THAY):
            return "khong_thay"
    return None


class SoDonMock:
    """Sổ mô phỏng khoá chống trùng phía hãng (`txlogisticId`: tài liệu ghi "不支持重复").

    CHỈ dùng ở mock, và chỉ khi được BẬT TƯỜNG MINH (`mo_phong_chong_trung=True`). Mặc định
    TẮT để không đổi hành vi của mọi đường đang chạy. Khoá gồm cả `apiAccount` + `customerCode`
    nên hai tenant khác nhau KHÔNG dùng chung một ô — đó là cách ly tenant ở tầng mô phỏng.
    """

    def __init__(self):
        self._o = {}
        self._khoa = threading.Lock()

    def dat(self, khoa, ma_van_don_moi):
        """Trả (đã_có, mã_vận_đơn). Lượt đầu ghi vào sổ; lượt sau trả lại mã CŨ, không tạo mới."""
        with self._khoa:
            if khoa in self._o:
                return True, self._o[khoa]
            self._o[khoa] = ma_van_don_moi
            return False, ma_van_don_moi

    def xoa(self):
        with self._khoa:
            self._o.clear()

    def so_o(self):
        with self._khoa:
            return len(self._o)


SO_DON_MOCK = SoDonMock()


def xoa_so_mock():
    """Xoá sổ mô phỏng — bộ thử gọi ở setUp để ca này không ăn sang ca khác."""
    SO_DON_MOCK.xoa()


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
    TRANSPORT_THAT_DA_VIET = TRANSPORT_THAT_DA_VIET

    # Trường hành chính BẮT BUỘC theo bảng tham số J&T. Thiếu là hãng trả `1450033315`.
    TRUONG_HANH_CHINH = (("sender", "prov", "nguoi_gui_tinh"),
                         ("sender", "area", "nguoi_gui_quan"),
                         ("receiver", "prov", "nguoi_nhan_tinh"),
                         ("receiver", "area", "nguoi_nhan_quan"))

    def __init__(self, credentials: dict, moi_truong: str = "mock", mo_phong_chong_trung=False):
        super().__init__(credentials, moi_truong)
        # Mô phỏng khoá chống trùng của hãng. Mặc định TẮT (xem SoDonMock).
        self.mo_phong_chong_trung = bool(mo_phong_chong_trung)

    # ── đường gọi THẬT: ba cửa ĐỘC LẬP, rồi một chỗ gửi duy nhất ───────────────────────────────
    def _chuan_bi_goi_that(self, thao_tac):
        """Chuẩn bị MỘT lượt gọi thật. Trả module HTTP nếu đủ điều kiện, `None` nếu đang ở `mock`.

        Bốn ổ khoá độc lập canh đường ra hãng; hàm này kiểm BA, ổ thứ tư nằm ở chỗ dựng
        `bizContent` (`chot_chan_anh_xa_area`) nên nó canh được cả những đường chưa đi qua đây:

          1. **Môi trường đã được Owner cấp quyền chưa** (§37) — `PermissionError`. Cửa này hỏi
             TRƯỚC TIÊN vì khi môi trường chưa được phép thì mọi câu hỏi sau đều vô nghĩa. Nguồn
             chân lý là `cau_hinh.jt_kiem_moi_truong` (AG-00 sở hữu), KHÔNG phải một bảng quyền
             riêng trong tệp này.
          2. **Đường dẫn API đã xác minh chưa** — `ChuaXacNhanTaiLieu`, nêu đúng thao tác nào và
             nguồn đã đọc tới đâu.
          3. **Lớp HTTP thật (§36) đã có chưa** — `ChuaXacNhanTaiLieu`. `TRANSPORT_THAT_DA_VIET`
             là ảnh chụp lúc nạp module; ở đây hỏi LẠI từng lượt.

        Không cửa nào trong ba cửa này "đi tiếp kèm cảnh báo": cảnh báo là thứ người ta học cách
        bỏ qua (cùng lý do đã ghi ở `chot_chan_anh_xa_area`).
        """
        if self.moi_truong == MOCK:
            return None
        chan_moi_truong_chua_duoc_cap(self.moi_truong)
        chan_duong_chua_xac_nhan(thao_tac, self.moi_truong)
        http = http_jt_dang_dung()
        if http is None:
            raise ChuaXacNhanTaiLieu(
                thao_tac,
                ["lớp HTTP thật CHƯA có trên đĩa — hợp đồng §36 đặt nó ở `app/http_jt.py`"
                 " (làn AG-02). Adapter chỉ GỌI, không tự viết lớp đó"],
                self.moi_truong)
        return http

    @staticmethod
    def _ket_qua_tu_ngoai_le_transport(e, thao_tac):
        """Ngoại lệ của `transport.py`/`http_jt.py` → `KetQuaHang`, GIỮ phân biệt ba kết cục.

        `LoiTamThoi` (mạng đứt, hết giờ, 5xx) ⇒ `HET_GIO` ⇒ `timeout=True`: KHÔNG BIẾT kết quả.
        `LoiVinhVien` (4xx, URL sai, chữ ký sai) ⇒ thử lại vô ích, biết chắc là hỏng.

        Nếu ngoại lệ có mang `ma_http` (hợp đồng §36 KHÔNG bắt buộc trường này, nên chỉ đọc khi
        có) thì phân loại theo HTTP TRƯỚC — 401/403 ra `XAC_THUC_HONG`, 400 ra `THAM_SO_SAI`,
        thay vì gộp hết vào `THAM_SO_SAI`. Không có thì rơi về `loi_hang.tu_ngoai_le`.

        ÉP CHẶT (chỉ khi lớp HTTP kết luận VĨNH VIỄN): `NormalizedCarrierError` cho ép
        `co_the_thu_lai` True→False, KHÔNG cho nới (hợp đồng §5). Khi `http_jt` ném
        `LoiVinhVien` (4xx, URL sai, chữ ký sai) mà `loi_hang.tu_http` lại xếp mã đó là thử lại
        được, ta giữ **mã chuẩn** theo `loi_hang` nhưng hạ cờ thử lại — nếu không thì adapter
        khuyên thử lại một việc mà lớp dưới đã bỏ.

        **NGOẠI LỆ ĐÃ ĐƯỢC AG-00 CHỐT 15/10/2026:** `408` và `429` **KHÔNG** bị ép. Hai mã đó là
        TẠM THỜI (xem `MA_HTTP_HAI_LOP_PHAI_DONG_Y`), nên `HET_GIO` / `QUA_HAN_MUC` phải đi thẳng
        với `co_the_thu_lai=True`. Adapter **không được** ghi đè chúng.
        """
        ma_http = getattr(e, "ma_http", None)
        if isinstance(ma_http, int) and ma_http:
            loi = loi_hang.tu_http(
                ma_http, hang="jt", thao_tac=thao_tac,
                thong_diep=f"J&T trả HTTP {ma_http} (qua lớp HTTP thật)")
        else:
            loi = loi_hang.tu_ngoai_le(e, hang="jt", thao_tac=thao_tac)
        if (isinstance(e, transport.LoiVinhVien) and loi.co_the_thu_lai
                and ma_http not in MA_HTTP_HAI_LOP_PHAI_DONG_Y):
            loi = loi_hang.NormalizedCarrierError(
                loi.ma_chuan, ma_goc_hang=loi.ma_goc_hang, thong_diep=loi.thong_diep,
                co_the_thu_lai=False, hang="jt", thao_tac=thao_tac,
                http_status=loi.http_status)
        return ket_qua_tu_loi(loi)

    def _goi_that(self, http, thao_tac, yc):
        """GỬI một yêu cầu ĐÃ DỰNG qua lớp HTTP thật, rồi đọc gói trả lời.

        Việc thử lại do `transport.goi()` quyết định theo `chinh_sach_cho` — lớp HTTP **không**
        tự thử lại (§36 luật 1). Với `createOrder`/`cancelOrder` điều đó có nghĩa: chỉ thử lại khi
        hãng có khoá chống trùng của chính nó (`txlogisticId`, `KHOA_CHONG_TRUNG = True`).
        """
        url = (yc or {}).get("url")
        if not url:
            raise ChuaXacNhanTaiLieu(
                thao_tac, ["URL đầy đủ chưa xác minh — KHÔNG ghép bừa một URL"],
                self.moi_truong)
        cs = transport.chinh_sach_cho(thao_tac, co_khoa_chong_trung=bool(self.KHOA_CHONG_TRUNG))
        dem = {"so_lan": 0}

        def _mot_lan():
            dem["so_lan"] += 1
            return http.gui_form(url, dict(yc["headers"]), dict(yc["body"]), timeout=cs.het_gio)

        try:
            tra_loi, so_lan, nhat_ky = transport.goi(_mot_lan, thao_tac, chinh_sach=cs)
        except (transport.LoiTamThoi, transport.LoiVinhVien) as e:
            kq = self._ket_qua_tu_ngoai_le_transport(e, thao_tac)
            kq.tho["so_lan_goi"] = dem["so_lan"]
            kq.tho["transport"] = ten_transport_dang_dung()
            return kq

        goi, ghi_chu_doc = doc_than_tra_loi(getattr(tra_loi, "than", None))
        kq = doc_goi_tra_loi(goi, thao_tac, http_status=getattr(tra_loi, "ma_http", None))
        kq.tho["transport"] = ten_transport_dang_dung()
        kq.tho["so_lan_goi"] = so_lan
        kq.tho["nhat_ky_goi"] = list(nhat_ky)
        if ghi_chu_doc:
            kq.tho["ghi_chu_doc_than"] = ghi_chu_doc
        # Đơn trùng: hãng báo mã đơn ĐÃ TỒN TẠI ⇒ lượt TRƯỚC ĐÃ VÀO. Cờ này để Order Service
        # (`don_hang._la_don_trung`) xử đúng nhánh, không trả đơn về `da_duyet` rồi gửi lại mù.
        if kq.tho.get("loi_chuan", {}).get("ma_chuan") == loi_hang.DON_TRUNG:
            kq.tho["don_da_ton_tai_tai_hang"] = True
        return kq

    # ── dựng gói yêu cầu ───────────────────────────────────────────────────────────────────────
    def _biz_chung(self):
        """Hai trường hợp đồng khách có mặt trong bizContent của MỌI API nghiệp vụ."""
        return {"customerCode": self.credentials.get("customerCode", ""),
                "password": self.credentials.get("password", "")}

    def _khoa_mock(self, txlogistic_id):
        """Khoá sổ mô phỏng: có cả apiAccount + customerCode ⇒ hai tenant không chung một ô."""
        return (str(self.credentials.get("apiAccount") or ""),
                str(self.credentials.get("customerCode") or ""),
                str(txlogistic_id))

    def _chan_chua_chay_duoc(self, thao_tac):
        """Chặn ĐƯỜNG THẬT — nêu ĐỦ lý do còn thiếu, không chỉ lý do đầu tiên.

        Giữ lại làm MỘT chỗ trả lời câu hỏi "vì sao thao tác này chưa gọi ra hãng được" cho
        người đọc và cho `kiem_ket_noi()`. Từ G16-A, đường chạy không dùng hàm này nữa: nó đi
        qua `_chuan_bi_goi_that()`, nơi ba cửa được kiểm theo thứ tự và mỗi cửa ném đúng loại
        lỗi của nó (`PermissionError` = chưa được phép, `ChuaXacNhanTaiLieu` = chưa biết đủ).
        """
        thieu = []
        d = DUONG_API.get(thao_tac) or {}
        if not moi_truong_duoc_chay(self.moi_truong):
            thieu.append(f"môi trường {self.moi_truong!r} CHƯA được Owner cấp quyền — "
                         + ly_do_moi_truong(self.moi_truong))
        if url_cua(thao_tac, self.moi_truong) is None:
            thieu.append("đường dẫn API đầy đủ chưa xác minh — nguồn đã đọc: "
                         + str(d.get("nguon") or "không rõ"))
        if http_jt_dang_dung() is None:
            thieu.append("lớp HTTP thật CHƯA có trên đĩa — hợp đồng §36 đặt nó ở `app/http_jt.py`"
                         f" (TRANSPORT_THAT_DA_VIET={bool(TRANSPORT_THAT_DA_VIET)})")
        if not thieu:
            thieu.append("không rõ còn thiếu gì — soi lại `_chuan_bi_goi_that`")
        raise ChuaXacNhanTaiLieu(thao_tac, thieu, self.moi_truong)

    def truong_hanh_chinh_thieu(self, don):
        """Trường hành chính bắt buộc nào đang rỗng. Trả danh sách tên cột của hệ.

        Tách thành hàm riêng để cả adapter, bộ thử và giao diện dùng CHUNG một định nghĩa
        "đủ dữ liệu để gửi J&T" — ba định nghĩa rời là ba định nghĩa sẽ lệch nhau.
        """
        thieu = []
        for _, _, cot in self.TRUONG_HANH_CHINH:
            gt = don.get(cot) if hasattr(don, "get") else None
            if not str(gt or "").strip():
                thieu.append(cot)
        return thieu

    @staticmethod
    def _ghi_chu_thieu(yc, danh_sach):
        """Gắn danh sách trường còn thiếu vào GÓI YÊU CẦU (không vào bizContent).

        Sửa lỗi chú thích cũ nói "gắn danh sách thiếu vào payload" nhưng mã không gắn gì: thông
        tin đó biến mất im lặng ở mock. Gắn vào gói yêu cầu (không phải bizContent) để nó tới
        được bộ thử mà KHÔNG bị gửi lên hãng như một trường lạ.
        """
        if danh_sach:
            yc["thieu_truong"] = list(danh_sach)
        return yc

    def _dung_bizcontent_tao_don(self, don):
        """Dựng bizContent theo bảng tham số docs.

        AG-03 phát hiện ở đợt 3, AG-00 đo lại trên mã: bản cũ có BA lỗi sẽ làm mọi đơn bị
        hãng từ chối, hoặc tệ hơn là lọt mà KHÔNG THU ĐƯỢC TIỀN:

        1. `prov` và `area` là **bắt buộc** nhưng gửi **chuỗi rỗng** ⇒ hãng trả `1450033315`.
           Bốn cột dữ liệu đã có sẵn từ migration v7 (`nguoi_gui_tinh/quan`, `nguoi_nhan_*`),
           chỉ là chưa ai nối vào.
        2. **COD gán vào `itemsValue`** trong khi tài liệu dùng **`codMoney`**; `itemsValue`
           KHÔNG có trong bảng tham số. Nếu đơn lọt qua thì hãng **không biết phải thu COD** —
           hàng đi, tiền không về, và không có lỗi nào báo.
        3. Thiếu hai trường bắt buộc `isInsured` và `goodsValue`.

        CHƯA CHẮC, đã ghi vào `docs/JT_CAU_HOI_CHINH_THUC.md` (câu về cấp hành chính): hệ này
        có BA cấp (tỉnh/quận/xã), J&T có HAI (`prov`/`area`). Em map `area` ← **quận/huyện**,
        vì đó là cấp J&T dùng để chia tuyến ở Việt Nam. Đây là **giả định**, không phải dữ kiện
        — hãng xác nhận khác thì đổi đúng một dòng ở `TRUONG_HANH_CHINH`. Giả định này bị chốt
        chặn D-9 canh: mọi môi trường khác `mock` đều DỪNG ở đây cho tới khi hãng xác nhận.
        """
        # Chốt D-9 đặt Ở ĐÂY chứ không ở `__init__`: `__init__` chỉ chặn lúc dựng
        # adapter, còn chốt ở chỗ DÙNG thì mọi đường mới dẫn tới `bizContent` sau này
        # đều tự bị canh — kể cả khi ai đó mở LIVE cho riêng thao tác chỉ-đọc.
        chot_chan_anh_xa_area(self.moi_truong)
        g = lambda k: str(don.get(k) or "").strip()      # noqa: E731
        khoi_luong = tien_nguyen_vnd(don.get("khoi_luong_gram"), "khoi_luong_gram")
        if khoi_luong <= 0:
            raise loi_hang.NormalizedCarrierError(
                loi_hang.THAM_SO_SAI,
                thong_diep="khoi_luong_gram phải > 0 — J&T không nhận kiện 0 gram",
                hang="jt", thao_tac="createOrder")
        cod = tien_nguyen_vnd(don.get("cod"), "cod")
        gia_tri_khai = tien_nguyen_vnd(don.get("gia_tri_khai"), "gia_tri_khai")
        biz = {
            **self._biz_chung(),
            "txlogisticId": don["ma_don"],          # mã đơn nội bộ = chống trùng phía hãng
            "orderType": 1, "serviceType": 1, "payType": "PP_CASH",
            "productType": "EXPRESS", "goodsType": "bm000010", "deliveryType": 1,
            "sender": {"name": don["nguoi_gui_ten"], "mobile": don["nguoi_gui_sdt"],
                       "prov": g("nguoi_gui_tinh"), "area": g("nguoi_gui_quan"),
                       "address": don["nguoi_gui_dia_chi"]},
            "receiver": {"name": don["nguoi_nhan_ten"], "mobile": don["nguoi_nhan_sdt"],
                         "prov": g("nguoi_nhan_tinh"), "area": g("nguoi_nhan_quan"),
                         "address": don["nguoi_nhan_dia_chi"]},
            "packageInfo": {"weight": f"{khoi_luong / 1000:.2f}"},
            # COD vào ĐÚNG cột `codMoney`. Số nguyên đồng (§16) — J&T nhận chuỗi số.
            # KHÔNG bao giờ dùng `itemsValue` cho COD: trường đó không có trong bảng tham số,
            # và đơn lọt qua sẽ đi mà không ai thu tiền.
            "codMoney": str(cod),
            # `isInsured` 0/1 và `goodsValue` bắt buộc. Chưa bán bảo hiểm nên 0, và giá trị
            # khai lấy từ `gia_tri_khai`; không có thì dùng COD (giá trị người nhận trả).
            "isInsured": 0,
            "goodsValue": str(gia_tri_khai or cod),
        }
        return biz

    def yeu_cau_tao_don(self, don, bay_gio=None):
        # Thiếu trường hành chính bắt buộc thì DỪNG Ở ĐÂY, đừng để hãng từ chối rồi mới biết:
        # lỗi của hãng là một mã số khó tra, còn lỗi ở đây nói rõ thiếu cột nào của hệ.
        # Ở MOCK vẫn cho đi (bộ thử và dữ liệu demo chưa có địa chỉ hành chính), nhưng gắn
        # danh sách thiếu vào gói yêu cầu để nó không biến mất im lặng.
        thieu = self.truong_hanh_chinh_thieu(don)
        if thieu and self.moi_truong != "mock":
            raise loi_hang.NormalizedCarrierError(
                loi_hang.THAM_SO_SAI,
                thong_diep=("thiếu trường hành chính bắt buộc của J&T: "
                            + ", ".join(thieu)
                            + " — hãng sẽ từ chối đơn (mã 1450033315)"),
                hang="jt", thao_tac="createOrder")
        """Dựng TRỌN gói yêu cầu tạo đơn (url · headers · body) mà KHÔNG gửi đi đâu cả.

        Tách ra để bộ thử hợp đồng kiểm được đúng công thức chữ ký, header và Content-Type
        theo tài liệu, không cần mạng và không cần credentials thật (§12.1: thứ dùng để kiểm
        chứng phải độc lập với lớp transport).
        """
        biz = dung_bizcontent(self._dung_bizcontent_tao_don(don))
        return self._ghi_chu_thieu({
            "url": url_cua("createOrder", self.moi_truong),   # None ở môi trường mock — cố ý
            "headers": dung_headers(self.credentials.get("apiAccount", ""), biz,
                                    self.credentials.get("privateKey", ""), bay_gio),
            "body": dung_body(biz),
            "bizContent": biz,
        }, thieu)

    def yeu_cau_tra_hanh_trinh(self, danh_sach_van_don, bay_gio=None):
        """Gói yêu cầu tra hành trình. Tài liệu: `billcodes` ngăn cách bằng dấu phẩy, tối đa 30.

        Nhận một mã (chuỗi) hoặc nhiều mã. Quá 30 mã thì DỪNG Ở ĐÂY kèm mã lỗi 145003502 mà
        hãng sẽ trả — chẻ lô là việc của `polling.py`, không phải của adapter.
        """
        if isinstance(danh_sach_van_don, str):
            ds = [danh_sach_van_don]
        else:
            ds = list(danh_sach_van_don or [])
        ds = [str(x).strip() for x in ds if str(x or "").strip()]
        if not ds:
            raise loi_hang.NormalizedCarrierError(
                loi_hang.THAM_SO_SAI, thong_diep="tra hành trình cần ít nhất một mã vận đơn",
                hang="jt", thao_tac="trackOrder")
        if len(ds) > SO_VAN_DON_MOI_LUOT:
            raise loi_hang.NormalizedCarrierError(
                loi_hang.THAM_SO_SAI, ma_goc_hang="145003502",
                thong_diep=(f"{len(ds)} mã vận đơn một lượt — tài liệu cho tối đa"
                            f" {SO_VAN_DON_MOI_LUOT} (mã lỗi 145003502)"),
                hang="jt", thao_tac="trackOrder")
        biz = dung_bizcontent({**self._biz_chung(), "billcodes": ",".join(ds)})
        return {"url": url_cua("trackOrder", self.moi_truong),
                "headers": dung_headers(self.credentials.get("apiAccount", ""), biz,
                                        self.credentials.get("privateKey", ""), bay_gio),
                "body": dung_body(biz), "bizContent": biz, "billcodes": ds}

    def yeu_cau_huy_don(self, ma_van_don, ly_do="", bay_gio=None):
        """Gói yêu cầu huỷ đơn. ĐƯỜNG DẪN CHƯA XÁC MINH ⇒ mọi môi trường khác `mock` DỪNG.

        Hai dữ kiện đọc được, và một chỗ còn thiếu:
          · bảng mã lỗi riêng của huỷ đơn có `145003082` (txlogisticId rỗng/quá dài) và
            `145003089` (取消原因不能为空 — THIẾU LÝ DO HUỶ) ⇒ yêu cầu huỷ CÓ trường lý do;
          · **TÊN** trường lý do chưa chép được từ tài liệu ⇒ KHÔNG bịa tên trường. Ở mock,
            tên còn thiếu được ghi vào `thieu_truong` của gói yêu cầu; ngoài mock thì DỪNG.
        """
        chan_duong_chua_xac_nhan("cancelOrder", self.moi_truong)
        ma = str(ma_van_don or "").strip()
        if not ma:
            raise loi_hang.NormalizedCarrierError(
                loi_hang.THAM_SO_SAI, ma_goc_hang="145003082",
                thong_diep="thiếu mã đơn/mã vận đơn để huỷ (hãng trả 145003082)",
                hang="jt", thao_tac="cancelOrder")
        thieu = []
        if "cancelOrder" in DUONG_API and DUONG_API["cancelOrder"]["muc"] != MUC_DA_DOC:
            thieu.append("đường dẫn API đầy đủ của huỷ đơn")
        if not TRUONG_LY_DO_HUY:
            thieu.append("TÊN trường lý do huỷ (hãng bắt buộc có lý do — mã lỗi 145003089 —"
                         " nhưng tài liệu chưa chép được tên trường)")
        if thieu and self.moi_truong != "mock":
            raise ChuaXacNhanTaiLieu("cancelOrder", thieu, self.moi_truong)
        biz = dung_bizcontent({**self._biz_chung(), "txlogisticId": ma})
        yc = {"url": url_cua("cancelOrder", self.moi_truong),
              "headers": dung_headers(self.credentials.get("apiAccount", ""), biz,
                                      self.credentials.get("privateKey", ""), bay_gio),
              "body": dung_body(biz), "bizContent": biz, "ly_do": str(ly_do or "")}
        return self._ghi_chu_thieu(yc, thieu)

    # ── sáu thao tác của hợp đồng ──────────────────────────────────────────────────────────────
    def createOrder(self, don) -> KetQuaHang:
        # Thứ tự có chủ ý: DỰNG gói yêu cầu TRƯỚC (chốt D-9 nằm trong đường này, nên nó chặn
        # ngay cả khi ba cửa sau đã mở), rồi mới hỏi ba cửa của đường gửi thật.
        yc = self.yeu_cau_tao_don(don)     # dựng + ký; chốt D-9 nằm trong đường này
        http = self._chuan_bi_goi_that("createOrder")
        if http is not None:
            return self._goi_that(http, "createOrder", yc)
        digest = yc["headers"]["digest"]
        kb = kich_ban_mock(don.get("ghi_chu"), don.get("ma_don"))
        if kb == "hong":
            # Lỗi của hãng đi qua bảng mã lỗi THẬT (loi_hang.JT_MA_LOI), không bịa chuỗi lỗi.
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt({"code": "145003050", "msg": "参数非法"},
                                                         thao_tac="createOrder"), mock=True)
        if kb == "het_gio":
            return ket_qua_het_gio("createOrder", "hết giờ — không biết kết quả", mock=True)
        if kb == "trung":
            return self._ket_qua_don_trung(None)
        ma_van_don = "JTVN%010d" % random.randint(0, 10**10 - 1)
        if self.mo_phong_chong_trung:
            da_co, ma_cu = SO_DON_MOCK.dat(self._khoa_mock(don.get("ma_don")), ma_van_don)
            if da_co:
                return self._ket_qua_don_trung(ma_cu)
            ma_van_don = ma_cu
        # KHÔNG đưa byte nào của chữ ký/khoá ra kết quả: `digest` là hàm của (bizContent +
        # privateKey), nên một tiền tố của nó vẫn là dữ liệu suy ra từ khoá. Chỉ nói ĐÃ KÝ.
        return KetQuaHang(True, ma_van_don=ma_van_don,
                          tho={"mock": True, "hang": "jt", "thao_tac": "createOrder",
                               "da_ky": True, "do_dai_digest": len(digest),
                               "url_mock": yc["url"],
                               "thieu_truong": yc.get("thieu_truong", [])})

    def _ket_qua_don_trung(self, ma_van_don_cu=None):
        """Đơn trùng: lượt TRƯỚC đã vào hãng. Không thử lại, và không được coi là 'chưa vào'."""
        loi = loi_hang.doc_tra_loi_jt({"code": "145003204", "msg": "订单重复"},
                                      thao_tac="createOrder")
        kq = ket_qua_tu_loi(loi, mock=True)
        kq.tho["don_da_ton_tai_tai_hang"] = True
        kq.tho["khong_tim_thay"] = False
        if ma_van_don_cu:
            kq.tho["ma_van_don_luot_truoc"] = str(ma_van_don_cu)
        return kq

    def cancelOrder(self, ma_van_don, ly_do="") -> KetQuaHang:
        yc = self.yeu_cau_huy_don(ma_van_don, ly_do)   # ngoài mock: tự DỪNG ở đây
        http = self._chuan_bi_goi_that("cancelOrder")
        if http is not None:
            return self._goi_that(http, "cancelOrder", yc)
        kb = kich_ban_mock(ma_van_don, ly_do)
        if kb == "hong":
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt(
                {"code": "999010010", "msg": "当前订单状态无法取消"},
                thao_tac="cancelOrder"), mock=True)
        if kb == "het_gio":
            return ket_qua_het_gio("cancelOrder", "hết giờ — không biết đơn đã huỷ chưa",
                                   mock=True)
        if kb == "khong_thay":
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt(
                {"code": "999002000", "msg": "未找到数据"}, thao_tac="cancelOrder"), mock=True)
        return KetQuaHang(True, ma_van_don=str(ma_van_don),
                          tho={"mock": True, "hang": "jt", "thao_tac": "cancelOrder",
                               "da_ky": True, "url_mock": yc["url"],
                               "thieu_truong": yc.get("thieu_truong", [])})

    def trackOrder(self, ma_van_don) -> KetQuaHang:
        """Tra hành trình. Nhận MỘT mã hoặc một danh sách (tài liệu: tối đa 30 mã một lượt)."""
        yc = self.yeu_cau_tra_hanh_trinh(ma_van_don)   # dựng + ký + chặn lô quá 30
        http = self._chuan_bi_goi_that("trackOrder")
        if http is not None:
            return self._goi_that(http, "trackOrder", yc)
        ma_dau = yc["billcodes"][0]
        kb = kich_ban_mock(ma_dau)
        if kb == "hong":
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt({"code": "145003100", "msg": "运单号不合法"},
                                                         thao_tac="trackOrder"), mock=True)
        if kb == "het_gio":
            return ket_qua_het_gio("trackOrder", "hết giờ — không biết hành trình", mock=True)
        if kb == "khong_thay":
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt({"code": "999002000", "msg": "未找到数据"},
                                                         thao_tac="trackOrder"), mock=True)
        # `trang_thai` là MÃ CỦA HÃNG (scanTypeCode), không phải trạng thái chuẩn: `polling.py`
        # đưa thẳng giá trị này vào `trang_thai_hang.quyet_dinh(hang, ma)`. Trả về tên chuẩn
        # ("dang_giao") ở đây là đưa một mã LẠ vào bảng ánh xạ ⇒ mọi vòng polling thành "mã lạ".
        # 112 = 出仓扫描 (On Delivery) — mã ĐÃ ĐỌC ĐƯỢC, ánh xạ `dang_giao`.
        return KetQuaHang(True, ma_van_don=ma_dau,
                          tho={"mock": True, "hang": "jt", "thao_tac": "trackOrder",
                               "trang_thai": 112, "trang_thai_chuan": "dang_giao",
                               "ma_da_tra": list(yc["billcodes"]),
                               "so_van_don": len(yc["billcodes"]),
                               "da_ky": True, "url_mock": yc["url"]})

    def getShippingFee(self, don) -> KetQuaHang:
        """Báo giá cước. Ở MOCK trả công thức NỘI BỘ, tự khai KHÔNG phải bảng giá J&T.

        Chưa đọc được đường dẫn và bảng tham số của API算费 (`apiDoc/fees/calculatingFees`),
        nên mọi môi trường khác `mock` DỪNG — không dựng một yêu cầu báo giá bằng cách đoán
        tên trường. Con số ở mock KHÔNG được dùng để chào giá cho khách.

        DỪNG ở đâu: `_chuan_bi_goi_that` ném ở cửa môi trường (chưa được cấp quyền), rồi cửa
        đường dẫn (chưa xác minh). Cả hai đều TRƯỚC khi có gói yêu cầu nào được dựng — nên
        KHÔNG có nhánh "đoán tên trường rồi gửi".
        """
        http = self._chuan_bi_goi_that("getShippingFee")
        if http is not None:
            # Đường tới đây chỉ mở khi CẢ HAI đã xong: đường dẫn `calculatingFees` được xác minh
            # VÀ có hàm dựng gói yêu cầu. Chưa ai viết hàm đó, nên nói thẳng thay vì gửi rỗng.
            raise ChuaXacNhanTaiLieu(
                "getShippingFee",
                ["có lớp HTTP và đường dẫn, nhưng CHƯA có hàm dựng bizContent báo giá"
                 " (bảng tham số `apiDoc/fees/calculatingFees` chưa chép được)"],
                self.moi_truong)
        kb = kich_ban_mock(don.get("ghi_chu"), don.get("ma_don"))
        if kb == "hong":
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt({"code": "145005004", "msg": "该收货地址暂时停用"},
                                                         thao_tac="getShippingFee"), mock=True)
        if kb == "het_gio":
            return ket_qua_het_gio("getShippingFee", "hết giờ — chưa có giá", mock=True)
        kl = max(1, tien_nguyen_vnd(don.get("khoi_luong_gram"), "khoi_luong_gram"))
        return KetQuaHang(True, phi=15000 + (kl // 500) * 5200,
                          tho={"mock": True, "hang": "jt", "thao_tac": "getShippingFee",
                               "la_gia_hang": False,
                               "nguon_gia": ("MOCK — công thức nội bộ của dự án, KHÔNG phải bảng"
                                             " giá J&T; không dùng để chào giá cho khách")})

    def getShippingLabel(self, ma_van_don) -> KetQuaHang:
        """Nhãn in. MOCK trả chuỗi giữ chỗ; ngoài mock DỪNG (chưa có đường dẫn đã xác minh)."""
        http = self._chuan_bi_goi_that("getShippingLabel")
        if http is not None:
            raise ChuaXacNhanTaiLieu(
                "getShippingLabel",
                ["có lớp HTTP và đường dẫn, nhưng CHƯA có hàm dựng bizContent in nhãn"
                 " (`apiDoc/vip/printOrder` chưa chép được đường dẫn và tham số)"],
                self.moi_truong)
        kb = kich_ban_mock(ma_van_don)
        if kb == "hong":
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt({"code": "145005005", "msg": "获取运单号失败"},
                                                         thao_tac="getShippingLabel"), mock=True)
        if kb == "het_gio":
            return ket_qua_het_gio("getShippingLabel", "hết giờ — chưa có nhãn", mock=True)
        if kb == "khong_thay":
            return ket_qua_tu_loi(loi_hang.doc_tra_loi_jt({"code": "999002000", "msg": "未找到数据"},
                                                         thao_tac="getShippingLabel"), mock=True)
        return KetQuaHang(True, ma_van_don=str(ma_van_don),
                          tho={"mock": True, "hang": "jt", "thao_tac": "getShippingLabel",
                               "label": "MOCK-PDF", "la_nhan_hang": False,
                               "nguon_nhan": "MOCK — chuỗi giữ chỗ, KHÔNG phải nhãn của J&T"})

    # getOrder: tài liệu công khai CHƯA nêu API tra đơn theo txlogisticId (câu hỏi 26) ⇒
    # `CAPABILITIES["getOrder"]=False` và lớp nền trả "không hỗ trợ". Đối soát bằng trackOrder.

    # ── tự kiểm cấu hình (KHÔNG phải kiểm kết nối) ─────────────────────────────────────────────
    def kiem_ket_noi(self) -> dict:
        """Kiểm TRA CẤU HÌNH cục bộ cho J&T. KHÔNG gọi hãng, và KHÔNG chứng minh kết nối.

        Tên hàm dễ bị đọc thành "đã kiểm tra kết nối" — nên kết quả trả về nói thẳng
        `chung_minh_ket_noi: False` kèm việc còn phải làm. Một hàm tự nhận đã kiểm kết nối
        trong khi nó chỉ đọc biến cục bộ là đúng dạng §12.1: thứ dùng để kiểm chứng tự nói sai.
        """
        thieu = [t for t in TRUONG_CREDENTIAL
                 if not str(self.credentials.get(t) or "").strip()]
        chua_xac_nhan = sorted(op for op, d in DUONG_API.items() if d["muc"] != MUC_DA_DOC)
        da_xac_nhan = sorted(op for op, d in DUONG_API.items() if d["muc"] == MUC_DA_DOC)
        http = http_jt_dang_dung()
        duoc_chay = moi_truong_duoc_chay(self.moi_truong)
        return {
            "hang": "jt", "ten_hang": self.ten_hang, "moi_truong": self.moi_truong,
            "la_mock": self.moi_truong == "mock",
            "du_credential": not thieu,
            "thieu_credential": thieu,          # TÊN trường, KHÔNG bao giờ là giá trị
            "cho_phep_live": bool(type(self).CHO_PHEP_LIVE),
            # HAI cửa KHÁC NHAU, khai riêng để không ai đọc một cửa rồi tưởng cửa kia đã mở:
            #   `moi_truong_duoc_chay` — Owner đã cấp quyền cho MÔI TRƯỜNG này chưa (§37)
            #   `transport_that_da_viet` — lớp HTTP thật (§36) đã có trên đĩa chưa
            "moi_truong_duoc_chay": duoc_chay,
            "ly_do_moi_truong": ly_do_moi_truong(self.moi_truong),
            "transport_that_da_viet": bool(TRANSPORT_THAT_DA_VIET),
            "transport_dang_dung": (ten_transport_dang_dung() if http is not None else ""),
            "chot_chan_D9_dang_bat": not ANH_XA_AREA_DA_XAC_NHAN,
            "city_co_gui": CITY_CO_GUI,
            "duong_api_da_xac_nhan": da_xac_nhan,
            "duong_api_chua_xac_nhan": chua_xac_nhan,
            "chung_minh_ket_noi": False,
            "de_kiem_ket_noi_that": ("chỉ chạy được ở chế độ SANDBOX của app/harness_hang.py,"
                                     " cần V-G09-01 + V-13906-05 + credentials + CHO_PHEP_LIVE"
                                     " + `UY_QUYEN_MOI_TRUONG['sandbox']` + chốt D-9 được gỡ"),
        }
