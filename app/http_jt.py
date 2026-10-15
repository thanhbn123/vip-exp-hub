# G16 (§36) — LỚP HTTP THẬT cho J&T: MỘT lượt gửi, đúng một lần, KHÔNG tự thử lại.
#
# Vì sao tệp này tồn tại: `app/transport.py` đã có chính sách (số lần, backoff, hết giờ,
# `duoc_thu_lai`) và bộ chạy `goi()`. Thiếu ĐÚNG MỘT thứ: hàm gửi thật. Chỗ đó là đây.
#
# BA LUẬT CỨNG (§36) — mỗi luật có ca thử riêng trong `app/thu/thu_http_jt.py`:
#
#   1. KHÔNG tự thử lại. `gui_form` gửi MỘT lượt rồi ném ĐÚNG loại lỗi. Thử lại là việc của
#      `transport.goi()`, nơi duy nhất biết thao tác này có được thử lại hay không (createOrder/
#      cancelOrder mặc định KHÔNG — thử lại mù quáng có thể tạo đơn TRÙNG ở phía hãng).
#
#   2. DANH SÁCH TRẮNG máy chủ. Chỉ hai host J&T (sandbox/production — đúng `adapter_jt.HOST_API`)
#      và `127.0.0.1`/`localhost` cho stub cục bộ. Host khác ⇒ TỪ CHỐI **trước khi mở socket**.
#      Đây là chốt chặn để một URL gõ sai không biến thành một lượt gọi ra ngoài.
#
#   3. BA KẾT CỤC KHÔNG GỘP (§4):
#        · hãng TRẢ LỜI (2xx)  → trả `TraLoiHTTP` với thân NGUYÊN VĂN. Lớp này KHÔNG phán ok hay
#          bị từ chối: `code` nằm trong thân, việc đọc nó là của adapter (AG-03). Vì vậy một
#          `TraLoiHTTP` trả về LUÔN có `ma_http` trong 2xx — không có mã HTTP nào khác đi ra được.
#        · hãng TỪ CHỐI / sai cấu hình (3xx, 4xx TRỪ 408/429, URL sai, chữ ký sai) → `LoiVinhVien`
#        · KHÔNG BIẾT (hết giờ, mạng chập, thân đứt giữa chừng, 5xx)   → `LoiTamThoi` + `timeout=True`
#          và HAI mã hãng NÓI THẲNG "thử lại sau" → `LoiTamThoi`:
#            – 429 → `.ket_cuc='qua-han-muc'` (bị giới hạn tần suất, hãng CHƯA xử lý)
#            – 408 → `.ket_cuc='khong-gui-di'` (hãng không nhận kịp, chắc chắn CHƯA xử lý gì)
#          Cả hai đọc `Retry-After` (giây hoặc HTTP-date), KẸP TRẦN `transport.CHO_TOI_DA`, và trả
#          gợi ý qua `cho_giay` — **`gui_form` KHÔNG BAO GIỜ NGỦ**, việc chờ thuộc `transport.goi()`.
#          Quyết định này của AG-00 (15/10/2026) để lớp này ĐỒNG Ý với `loi_hang.tu_http`.
#      Kết cục "không biết" KHÔNG BAO GIỜ được trả về dưới dạng một `TraLoiHTTP`: nó không có mã HTTP
#      nào để trả, và một thân đọc dở TUYỆT ĐỐI không được coi là thành công.
#
# KHÔNG BAO GIỜ ghi log ở tệp này, và không có giá trị bí mật nào đi vào ngoại lệ: thông điệp lỗi
# chỉ nêu TÊN header, không nêu giá trị; thân phản hồi gắn vào NGOẠI LỆ thì đã được CHE; thân trả
# về cho người gọi thì nguyên văn (hợp đồng §36) — xem `che_bi_mat` và `docs/G16_TRANSPORT.md` §5.
#
# ---- NHIỀU TIẾN TRÌNH (G18/AG-02, đo 15/10/2026) ---------------------------------------------
# `docs/G17_TRANSPORT.md` §8.3 ghi "CHƯA ĐO nhiều tiến trình". Nay đã đo, bằng **tiến trình thật**
# (`subprocess`, không phải luồng): `app/thu/thu_g18_multiprocess.py` P3–P4 + `docs/G18_MULTIPROCESS.md`.
#
#   · Lớp này KHÔNG có trạng thái dùng chung nào — quét AST: 20 tên mức mô-đun, 2 trong đó là dict
#     HẰNG số cấu hình (`CHO_PHEP_MOI_TRUONG`, `LY_DO_CHAN_MOI_TRUONG`), **0 dấu hiệu GHI** (không
#     `global`, không ghi chỉ số, không `open(…, "w")`, không `tempfile`, không `shutil`).
#   · Đo hành vi với 4 tiến trình thật: không tiến trình nào nhận thân trả lời của tiến trình khác;
#     4 lượt gọi ⇒ stub nhận ĐÚNG 4 kết nối TCP (một kết nối cho một lượt, tự mở tự đóng — KHÔNG
#     pool, nên không có kết nối nào để dùng chung).
#   ⇒ Vì vậy lớp này **AN TOÀN qua nhiều tiến trình**, và đó là kết luận ĐO ĐƯỢC, không phải suy ra.
#     Cái KHÔNG an toàn nằm ở lớp khác: `gioi_han` PHẦN A giữ bộ đếm trong bộ nhớ MỘT tiến trình
#     (trần thực = khai báo × số bản — B-G11-10), và `csdl.khoa_ghi` là RLock nên không phủ tiến
#     trình. Trần đồng thời của lớp NÀY, khi chạy N bản, là trần file descriptor của TỪNG tiến
#     trình — nhân lên, không phải một trần chung bị chia.
import datetime as _dt
import http.client
import json
import math
import socket
import ssl
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, quote, quote_plus, urlencode, urlsplit

import transport

# ---- §37: ba môi trường, tách rõ, mặc định là MOCK ----------------------------------------------
MOCK = "mock"
SANDBOX = "sandbox"
PRODUCTION = "production"
MOI_TRUONG = (MOCK, SANDBOX, PRODUCTION)

# §37: sandbox cần V-G09-01 **VÀ** V-13906-05; production cần anh Thành duyệt riêng. CẢ HAI CHƯA CẤP.
# Đây là chốt chặn ĐỌC ĐƯỢC, không phải chỗ để mở. Lớp HTTP này ĐỦ KHẢ NĂNG chạy sandbox (host có
# trong danh sách trắng, TLS thật) nhưng TỪ CHỐI cho tới khi Owner cấp — từ chối kèm lý do.
CHO_PHEP_MOI_TRUONG = {MOCK: True, SANDBOX: False, PRODUCTION: False}
LY_DO_CHAN_MOI_TRUONG = {
    SANDBOX: ("mã việc V-G09-01 và V-13906-05 CHƯA ĐƯỢC CẤP (SHARED_CONTRACTS §37) — "
              "chưa ai uỷ quyền gọi sandbox, dù chỉ một lượt"),
    PRODUCTION: ("cần anh Thành duyệt riêng (SHARED_CONTRACTS §37) — "
                 "và chưa từng có lượt gọi hãng thật nào để đối chiếu"),
}


def chan_moi_truong(moi_truong):
    """§37: `mock` mở; `sandbox`/`production` TỪ CHỐI kèm lý do đọc được.

    Ném `PermissionError` (khoá an toàn, không phải `LoiVinhVien`: đây không phải lỗi thử lại
    được hay không — đây là CHƯA ĐƯỢC PHÉP).
    """
    if moi_truong not in CHO_PHEP_MOI_TRUONG:
        raise ValueError(f"môi trường lạ {moi_truong!r}; chỉ có {list(MOI_TRUONG)}")
    if not CHO_PHEP_MOI_TRUONG[moi_truong]:
        raise PermissionError(f"J&T/{moi_truong}: TỪ CHỐI — {LY_DO_CHAN_MOI_TRUONG[moi_truong]}")


# ---- §36 luật 2: DANH SÁCH TRẮNG máy chủ --------------------------------------------------------
# Hai host này chép từ `adapter_jt.HOST_API` (nguồn: open.jtexpress.vn/apiDoc, đọc 14/10/2026).
# Chép chứ KHÔNG import: `adapter_jt` sẽ import chính tệp này để gọi, nhập ngược lại là vòng lặp
# import. Bộ thử có ca canh lệch (đọc `HOST_API` bằng AST) để hai chỗ không trôi khỏi nhau.
HOST_HANG_SANDBOX = "demoopenapi.jtexpress.vn"
HOST_HANG_PRODUCTION = "ylopenapi.jtexpress.vn"
HOST_HANG = (HOST_HANG_SANDBOX, HOST_HANG_PRODUCTION)
CONG_HANG = 443
HOST_CUC_BO = ("127.0.0.1", "localhost")

# Hạn NỐI riêng, tường minh, độc lập với hạn ĐỌC mà người gọi truyền vào. Không có hạn nối thì
# một host nuốt SYN sẽ treo bộ thử/giao dịch tới hạn của hệ điều hành (hàng chục giây).
HET_GIO_KET_NOI_TOI_DA = 5.0

# Ngưỡng để một giá trị KHÔNG thuộc trường credential được coi là "có thể là bí mật" và bị che nếu
# hãng echo lại. Đặt ngưỡng để không che những giá trị ngắn vô hại ("1", "200") làm hỏng thông điệp
# chẩn đoán. Giá trị của TRƯỜNG CREDENTIAL thì KHÔNG có ngưỡng — xem `TRUONG_CREDENTIAL`.
DAI_TOI_THIEU_DE_CHE = 8

# Bốn TÊN trường credentials J&T (§38), chép từ `adapter_jt.TRUONG_CREDENTIAL` (chép chứ không
# import — cùng lý do như HOST_API ở trên; bộ thử canh lệch bằng AST).
#
# VÌ SAO PHẢI CÓ DANH SÁCH NÀY: ngưỡng 8 ký tự ở trên bỏ sót một `customerCode`/`apiAccount` NGẮN —
# mà giá trị ngắn vẫn là credential. Đo được (bộ QA độc lập AG-01, `thu_qa_g16.t18b`): canary 5 ký
# tự đặt ở header `apiAccount` **rò nguyên văn** qua thân/header phản hồi. Giá trị của bốn trường này
# vào tập che BẤT KỂ ĐỘ DÀI. Đánh đổi có ý thức: một credential 1–3 ký tự sẽ làm thông điệp chẩn đoán
# bị che nhiều — thà thông điệp khó đọc còn hơn một credential đi vào log.
TRUONG_CREDENTIAL = ("apiaccount", "privatekey", "customercode", "password")

# Header mà GIÁ TRỊ không phải bí mật (giao thức), không đưa vào tập che — che chúng chỉ làm thông
# điệp chẩn đoán khó đọc mà không thêm an toàn nào.
HEADER_KHONG_CHE = ("content-type", "accept", "accept-encoding", "user-agent", "host", "connection")

# Kết cục CHÍNH XÁC của một lượt hỏng, tách khỏi cờ thô `timeout`:
#   · hang-tu-choi  — biết chắc là hỏng, thử lại vô ích
#   · khong-biet    — KHÔNG BIẾT kết quả (hết giờ, đứt giữa chừng, 5xx, thân đọc dở)
#   · khong-gui-di  — biết chắc hãng CHƯA XỬ LÝ GÌ: yêu cầu chưa ra khỏi máy (bị chặn, DNS hỏng,
#                     bị từ chối kết nối) HOẶC hãng nói chưa nhận được yêu cầu (HTTP 408)
#   · qua-han-muc   — hãng CHƯA xử lý và bảo CHỜ (HTTP 429). Xem chú thích ngay dưới.
# `khong-gui-di` KHÔNG phải "hãng từ chối": hãng chưa hề nói gì. Nó chỉ nói rằng thử lại là AN TOÀN
# (không có nguy cơ trùng đơn). Người gọi đừng gộp nó vào "hãng từ chối" — gộp là làm mất một đơn.
KET_CUC_HANG_TU_CHOI = "hang-tu-choi"
KET_CUC_KHONG_BIET = "khong-biet"
KET_CUC_KHONG_GUI_DI = "khong-gui-di"
# `qua-han-muc` có sau QUYẾT ĐỊNH CỦA AG-00 (15/10/2026): **429 là LỖI TẠM THỜI**, không phải 4xx
# vĩnh viễn. Lý do (nguyên văn tinh thần): 429 là tín hiệu máy chủ NÓI THẲNG "thử lại sau", không
# phải "yêu cầu của bạn sai"; xếp nó vào vĩnh viễn là BỎ IM LẶNG một việc lẽ ra sẽ thành công, và
# làm `http_jt` nói ngược với `loi_hang.tu_http` (429 → `QUA_HAN_MUC`, thử lại được).
# Ba kết cục KHÁC NHAU, không được gộp trong log:
#   · `qua-han-muc`  — hãng CHƯA xử lý, bảo chờ  → thử lại được
#   · `khong-biet`   — hãng CÓ THỂ đã xử lý (5xx, hết giờ, đứt)  → không bao giờ là thành công
#   · `hang-tu-choi` — hãng đã trả lời và từ chối (hoặc URL/tham số sai) → thử lại vô ích
KET_CUC_QUA_HAN_MUC = "qua-han-muc"

# Trần cho `Retry-After`: dùng `transport.CHO_TOI_DA` — NGUỒN DUY NHẤT, không khai lại ở đây (hai
# chỗ khai một trần là hai chỗ trôi khỏi nhau). Hãng là dữ liệu NGOÀI: `Retry-After: 86400` KHÔNG
# được phép treo tiến trình, nên lớp này ĐỌC rồi KẸP TRẦN và trả gợi ý qua `cho_giay`.
#
# ⚠️ `gui_form` **KHÔNG BAO GIỜ NGỦ**. Có ca thử soát bằng AST (`test_b11`) chốt điều đó: nếu nó
# ngủ, `createOrder` (chính sách `so_lan=3`) sẽ treo 3 × trần = 180 giây trong MỘT yêu cầu HTTP của
# hệ này, và phá luôn §36 luật 1 (việc thử lại thuộc `transport.goi()`). Việc chờ do `goi()` làm.

CONTENT_TYPE_FORM = "application/x-www-form-urlencoded"


class TraLoiHTTP:
    """Kết quả MỘT lượt gửi (hợp đồng §36). Chỉ được dựng khi hãng ĐÃ trả lời (2xx).

    `than` là thân THÔ, NGUYÊN VĂN — đó là bằng chứng, không được sửa. `headers` là header phản hồi
    (khoá giữ nguyên chữ hoa/thường như hãng gửi; trùng tên thì bản cuối thắng), GIÁ TRỊ đã được che
    nếu trùng với thứ ta đã gửi đi (xem `che_bi_mat`) — vì đối tượng này rất dễ bị đem đi log.
    """

    __slots__ = ("ma_http", "than", "headers")

    def __init__(self, ma_http, than, headers):
        self.ma_http = int(ma_http)
        self.than = bytes(than)
        self.headers = dict(headers)

    def __repr__(self):
        # KHÔNG in thân và KHÔNG in giá trị header: `repr` là thứ hay bị nhét vào log nhất.
        return (f"TraLoiHTTP(ma_http={self.ma_http}, than=<{len(self.than)} byte>, "
                f"headers=<{len(self.headers)} trường>)")

    def __eq__(self, khac):
        return (isinstance(khac, TraLoiHTTP) and self.ma_http == khac.ma_http
                and self.than == khac.than and self.headers == khac.headers)

    def __hash__(self):
        return hash((self.ma_http, self.than))


# ---- Dựng ngoại lệ: LUÔN qua hai hàm này để mọi lỗi có cùng bộ thuộc tính ------------------------
def _loi_tam_thoi(loai, thong_diep, ket_cuc, ma_http=0, cho_giay=None, **them):
    """Lỗi ĐÁNG thử lại. `timeout=True` = KHÔNG BIẾT kết quả (không bao giờ là thành công).

    `cho_giay` đi vào ĐÚNG tham số của `transport.LoiTamThoi(*a, cho_giay=...)` — đó là hợp đồng
    AG-00 vừa mở (transport.py dòng 27–34), để `transport.goi()` lấy `max(backoff, cho_giay)` rồi
    kẹp trần `CHO_TOI_DA`. Lớp này chỉ GỢI Ý, không tự chờ.
    """
    e = transport.LoiTamThoi(thong_diep, cho_giay=cho_giay)
    e.loai = loai
    e.ket_cuc = ket_cuc
    e.timeout = True
    e.ma_http = int(ma_http)
    for k, v in them.items():
        setattr(e, k, v)
    return e


def _loi_vinh_vien(loai, thong_diep, ket_cuc, ma_http=0, **them):
    """Lỗi thử lại VÔ ÍCH. `timeout=False`: ta BIẾT chắc kết quả (hoặc biết chắc là chưa gửi được)."""
    e = transport.LoiVinhVien(thong_diep)
    e.loai = loai
    e.ket_cuc = ket_cuc
    e.timeout = False
    e.ma_http = int(ma_http)
    for k, v in them.items():
        setattr(e, k, v)
    return e


# ---- Che bí mật trước khi bất cứ thứ gì đi vào ngoại lệ / log ------------------------------------
def _gia_tri_trong_json(chuoi, ra):
    """Gom mọi giá trị CHUỖI trong một JSON — để che cả `customerCode`/`password` nằm trong
    `bizContent` nếu hãng echo nguyên thân yêu cầu trở lại. Chỉ lấy GIÁ TRỊ, không lấy TÊN trường:
    tên trường (`txlogisticId`, `customerCode`…) là thứ cần cho chẩn đoán, không phải bí mật.

    Giá trị nằm dưới một khoá THUỘC `TRUONG_CREDENTIAL` được lấy BẤT KỂ ĐỘ DÀI; giá trị khác chỉ lấy
    khi đủ dài (ngưỡng), để không che những con số ngắn vô hại.
    """
    try:
        cay = json.loads(chuoi)
    except Exception:
        return
    hang_doi = [cay]
    while hang_doi:
        n = hang_doi.pop()
        if isinstance(n, str):
            if len(n) >= DAI_TOI_THIEU_DE_CHE:
                ra.add(n)
        elif isinstance(n, dict):
            for khoa, gt in n.items():
                if isinstance(gt, str) and gt and str(khoa).lower() in TRUONG_CREDENTIAL:
                    ra.add(gt)
                hang_doi.append(gt)
        elif isinstance(n, (list, tuple)):
            hang_doi.extend(n)


def _dang_che(ten, gia_tri):
    """Hai mức: TÊN thuộc credential ⇒ che BẤT KỂ độ dài; tên khác ⇒ chỉ che khi đủ dài.

    Ngưỡng độ dài một mình bỏ sót credential NGẮN — đo được hai lần (`thu_qa_g16.t18b` của AG-01 và
    `thu_http_jt.e3`) — nên mức theo TÊN là mức BẮT BUỘC, không phải mức "thêm cho chắc".
    TÊN không bao giờ bị che: tên là thứ cần cho chẩn đoán, giá trị mới là bí mật.
    """
    if not gia_tri:
        return False
    return len(gia_tri) >= DAI_TOI_THIEU_DE_CHE or ten.lower() in TRUONG_CREDENTIAL


def _escape_json(s):
    """Dạng một chuỗi mang khi nằm trong JSON `ensure_ascii=True` (`ậ` → `\\u1ead`).

    Hãng Trung Quốc hay trả JSON escape ASCII; đo được (`thu_http_jt.j3`) rằng dạng này LỌT qua phép
    che theo chuỗi gốc khi chính người gọi cũng dựng `bizContent` bằng `ensure_ascii=True`.
    """
    try:
        return json.dumps(s, ensure_ascii=True)[1:-1]
    except Exception:
        return s


def _bien_the(s):
    """MỌI dạng mà MỘT giá trị đã gửi đi có thể mang khi hãng echo nó lại.

    Vì sao cần — phép che cũ so khớp ĐÚNG chuỗi đã gửi, nhưng chuỗi ấy còn đi qua các lớp mã hoá
    trước khi lên dây, và hãng echo lại **byte trên dây**, không phải chuỗi Python của ta:

      · `urlencode` percent-encode giá trị form ⇒ `aB?cd&e=f` lên dây là `aB%3Fcd%26e%3Df`
      · `bizContent` là JSON **lồng trong một trường form** ⇒ giá trị bên trong có thể bị mã hoá
        hai lớp (`%253F`), và dạng JSON-escape của nó cũng bị percent-encode
      · JSON `ensure_ascii=True` viết `ậ` thành `\\u1ead`

    ĐO ĐƯỢC trước khi vá (AG-02, 15/10/2026, `thu_http_jt.j3`): bí mật `aB?cd&e=f` ở
    `bizContent.password` RÒ NGUYÊN VĂN dạng `aB%3Fcd%26e%3Df` trong `than_da_che` của ngoại lệ.
    Một đường khác cũng rò: bí mật phi-ASCII gửi bằng `ensure_ascii=True` hiện lại thành
    `m%5Cu1eadt-…`. Vì vậy tập che phải gồm MỌI biến thể, không chỉ chuỗi gốc.

    Bao đóng hai lớp của {percent-encode, JSON-escape} là đủ cho mọi đường đã đo (form phẳng, form
    lồng JSON, JSON escape ASCII). Biến thể KHÔNG bao giờ làm mất an toàn: che thừa chỉ làm thông
    điệp chẩn đoán khó đọc hơn, còn che thiếu là một credential đi vào log.
    """
    ra = {s}
    lop = [s]
    for _ in range(2):
        moi = []
        for v in lop:
            for f in (quote_plus, quote, _escape_json):
                try:
                    w = f(v)
                except Exception:
                    continue
                if w and w not in ra:
                    ra.add(w)
                    moi.append(w)
        lop = moi
    return ra


def _mo_rong_bien_the(can_che):
    """Mở rộng tập giá trị GỐC ra mọi biến thể (`_bien_the`)."""
    ra = set()
    for gt in can_che:
        ra |= _bien_the(gt)
    return ra


def _gia_tri_tu_url(url):
    """Giá trị trong QUERY của URL — cũng là thứ TA GỬI ĐI, nên cũng phải che nếu hãng echo lại.

    ĐO ĐƯỢC (AG-02, `thu_http_jt.j5`): một token đặt ở query (`?tk=…`) đi ra ngoài trong dòng yêu
    cầu và bị máy chủ echo lại, nhưng `_gia_tri_can_che` chỉ nhìn header + thân form, nên bí mật RÒ
    trong `than_da_che`. Hai mức như mọi giá trị khác; TÊN tham số không bao giờ bị che.

    PHẠM VI: chỉ QUERY. ĐƯỜNG DẪN vẫn được in nguyên văn trong mô tả yêu cầu (nó là thứ cho biết
    lượt gọi đi tới endpoint nào) — xem `docs/G17_TRANSPORT.md` §5, mục "NGOÀI PHẠM VI".
    """
    ra = set()
    try:
        for ten, gt in parse_qsl(urlsplit(url).query, keep_blank_values=True):
            if _dang_che(ten, gt):
                ra.add(gt)
    except Exception:
        pass
    return ra


def _che_chuoi(chuoi, can_che):
    """Che một CHUỖI (không phải bytes) — dùng cho mô tả yêu cầu và thông điệp lỗi."""
    return che_bi_mat(chuoi.encode("utf-8", "replace"), can_che).decode("utf-8", "replace")


def _mo_ta_ten(ten):
    """Mô tả một TÊN header/trường form mà KHÔNG in ra giá trị của nó.

    Vì sao không in thẳng tên: hàm này chỉ được gọi khi tên KHÔNG hợp lệ, mà đường duy nhất để một
    tên không hợp lệ là ai đó truyền nhầm GIÁ TRỊ vào vị trí tên (`headers={token: "Bearer …"}`).
    In tên ra là in chính giá trị đó. ĐO ĐƯỢC trước khi vá (AG-02, `thu_http_jt.j6`): bản cũ in
    `str(ten)[:40]`, nên bí mật ở vị trí tên RÒ vào thông điệp lỗi — đúng chỗ mà chú thích cũ khẳng
    định là "giá trị thì không được in ra".

    Tên HỢP LỆ được trả nguyên văn: nó không phải bí mật, và nó là thứ duy nhất chỉ đúng chỗ sai.
    """
    if not isinstance(ten, str):
        return f"<kiểu {type(ten).__name__}>"
    if not ten:
        return "<rỗng>"
    for i, c in enumerate(ten):
        if c in "\r\n: \t" or ord(c) < 0x21 or ord(c) > 0x7E:
            return f"<{len(ten)} ký tự, ký tự không hợp lệ tại vị trí {i}: U+{ord(c):04X}>"
    return ten


def _gia_tri_can_che(headers, than_gui, url=None):
    """Mọi dạng có thể xuất hiện lại của những giá trị TA ĐÃ GỬI ĐI. TÊN trường không bao giờ bị che.

    Hai mức: TÊN thuộc credential thì che BẤT KỂ độ dài; tên khác chỉ che khi đủ dài
    (`DAI_TOI_THIEU_DE_CHE`) — xem `_dang_che`.

    Ba nguồn: header, thân form (kể cả JSON lồng trong `bizContent`), và query của URL. Đầu ra đã
    MỞ RỘNG ra mọi biến thể mã hoá (`_bien_the`) — đó là chỗ vá lỗ hổng đo được ngày 15/10/2026.
    """
    ra = set()
    for ten, gt in headers.items():
        if ten.lower() in HEADER_KHONG_CHE:
            continue
        s = str(gt)
        if _dang_che(ten, s):
            ra.add(s)
    try:
        for ten, gt in parse_qsl(than_gui.decode("utf-8"), keep_blank_values=True):
            if _dang_che(ten, gt):
                ra.add(gt)
            _gia_tri_trong_json(gt, ra)
    except Exception:
        pass
    if url:
        ra |= _gia_tri_tu_url(url)
    return _mo_rong_bien_the(ra)


def che_bi_mat(du_lieu: bytes, can_che) -> bytes:
    """Thay mọi giá trị ĐÃ GỬI ĐI (nếu hãng echo lại) bằng nhãn `[DA-CHE]`.

    Che theo GIÁ TRỊ NGUYÊN VẸN, xếp dài trước để giá trị dài không bị cắt khúc bởi giá trị ngắn
    nằm trong nó. Việc CHỌN giá trị nào đáng che nằm ở `_gia_tri_can_che` — hàm này che đúng những
    gì được đưa vào. Đây là lớp chặn cuối: thân phản hồi của hãng là dữ liệu NGOÀI, không được tin.
    """
    ra = bytes(du_lieu)
    for gt in sorted(can_che, key=len, reverse=True):
        if not gt:
            continue
        try:
            ra = ra.replace(gt.encode("utf-8"), b"[DA-CHE]")
        except UnicodeEncodeError:
            continue
    return ra


def mo_ta_yeu_cau(url, headers, than) -> str:
    """Mô tả một yêu cầu để đưa vào THÔNG ĐIỆP LỖI — chỉ TÊN, không giá trị, không query.

    Hàm này là chỗ DUY NHẤT dựng phần mô tả yêu cầu, nên bộ thử có thể đột biến đúng nó để chứng
    minh bộ dò rò rỉ bí mật thật sự bắt được (xem `thu_http_jt` ca g2).
    """
    phan = urlsplit(url)
    duong = phan.path or "/"
    return (f"POST {phan.scheme}://{phan.hostname}{duong} · header: {sorted(headers)} · "
            f"trường form: {_ten_truong_form(than)} · thân: {len(than)} byte")


def _ten_truong_form(than):
    try:
        return sorted(ten for ten, _ in parse_qsl(than.decode("utf-8"), keep_blank_values=True))
    except Exception:
        return ["<không đọc được>"]


# ---- Kiểm URL và danh sách trắng ------------------------------------------------
def host_duoc_phep(host) -> bool:
    """Chỉ hai host J&T và loopback. So KHỚP CHÍNH XÁC, không so chuỗi con.

    So chuỗi con là bẫy: `demoopenapi.jtexpress.vn.kẻ-tấn-công.example` chứa tên host thật.
    """
    h = (host or "").strip().lower().rstrip(".")
    return h in HOST_HANG or h in HOST_CUC_BO


def tach_url(url):
    """→ (scheme, host, cổng, đích). Ném `LoiVinhVien` nếu URL không dùng được hoặc host bị chặn.

    Chạy TRƯỚC mọi thao tác mạng. Bộ thử chứng minh điều đó bằng cách đếm số lần `connect()`.
    """
    if not isinstance(url, str) or not url.strip():
        raise _loi_vinh_vien("url-sai", f"URL phải là chuỗi khác rỗng, nhận {type(url).__name__}",
                             KET_CUC_KHONG_GUI_DI)
    # Ký tự điều khiển/khoảng trắng: TỪ CHỐI ở đây, TRƯỚC `urlsplit` và trước mọi thao tác mạng.
    # Không chỉ vì URL dán sai: `http.client` cũng từ chối đúng tập ký tự này, nhưng nó ném
    # `InvalidURL` MANG THEO CẢ URL trong thông điệp — mà URL có thể chở bí mật ở query. ĐO ĐƯỢC
    # (AG-02, `thu_http_jt.j5`): bí mật trong query RÒ vào `str(e)` qua đúng đường đó. Chặn ở đây
    # thì không có ngoại lệ nào của thư viện mang dữ liệu của ta đi cả.
    # Thông điệp chỉ nêu VỊ TRÍ + MÃ ký tự, không nêu giá trị (URL có thể chứa bí mật).
    for _i, _c in enumerate(url):
        if ord(_c) < 0x21 or ord(_c) == 0x7F:
            raise _loi_vinh_vien(
                "url-sai",
                f"URL chứa ký tự không hợp lệ tại vị trí {_i} (U+{ord(_c):04X}) — dán sai hoặc bị "
                "chèn. TỪ CHỐI trước khi mở socket",
                KET_CUC_KHONG_GUI_DI)
    try:
        phan = urlsplit(url)
    except ValueError as e:
        # `urlsplit` ném `ValueError` trần cho URL hỏng (ví dụ `http://[abc/`). Để nó đi ra ngoài là
        # phá hợp đồng ba kết cục: `transport.goi()` chỉ bắt `LoiTamThoi`/`LoiVinhVien`, nên một
        # `ValueError` trần sẽ nổi lên tận Order Service như một lỗi 500. ĐO ĐƯỢC (AG-02,
        # `thu_http_jt.j8`). Thông điệp chỉ nêu LOẠI lỗi, không nêu URL.
        raise _loi_vinh_vien(
            "url-sai",
            f"URL không phân tích được ({type(e).__name__}) — dán sai. TỪ CHỐI trước khi mở socket",
            KET_CUC_KHONG_GUI_DI) from None
    if phan.scheme not in ("http", "https"):
        raise _loi_vinh_vien("url-sai", f"scheme {phan.scheme!r} không dùng được (chỉ http/https)",
                             KET_CUC_KHONG_GUI_DI)
    if phan.fragment:
        raise _loi_vinh_vien("url-sai", "URL chứa dấu # — URL bị dán sai, không gửi đi",
                             KET_CUC_KHONG_GUI_DI)
    if "@" in phan.netloc:
        raise _loi_vinh_vien("url-sai",
                             "URL chứa thông tin đăng nhập (user@host) — credentials KHÔNG đi qua URL",
                             KET_CUC_KHONG_GUI_DI)
    host = (phan.hostname or "").lower().rstrip(".")
    if not host:
        raise _loi_vinh_vien("url-sai", "URL không có tên máy chủ", KET_CUC_KHONG_GUI_DI)
    if not host_duoc_phep(host):
        raise _loi_vinh_vien(
            "host-bi-tu-choi",
            f"TỪ CHỐI máy chủ {host!r}: không nằm trong danh sách trắng "
            f"({', '.join(HOST_HANG)} hoặc {'/'.join(HOST_CUC_BO)}). "
            "Lượt gọi này KHÔNG được gửi đi (số lần nối: 0).",
            KET_CUC_KHONG_GUI_DI, host=host)
    try:
        cong = phan.port
    except ValueError:
        raise _loi_vinh_vien("url-sai", f"cổng trong URL không hợp lệ (host {host!r})",
                             KET_CUC_KHONG_GUI_DI, host=host) from None
    if host in HOST_HANG:
        # Host hãng: BẮT BUỘC https và cổng 443. Gõ nhầm `http://` hay cổng lạ là một lượt gửi
        # credentials ra ngoài bằng kênh không mã hoá.
        if phan.scheme != "https" or cong not in (None, CONG_HANG):
            raise _loi_vinh_vien(
                "url-sai",
                f"host hãng {host!r} chỉ nhận https và cổng {CONG_HANG}, "
                f"nhận {phan.scheme}://…:{cong}",
                KET_CUC_KHONG_GUI_DI, host=host)
    duong_dan = phan.path or "/"
    if not duong_dan.startswith("/"):
        raise _loi_vinh_vien("url-sai", f"đường dẫn {duong_dan!r} không bắt đầu bằng '/'",
                             KET_CUC_KHONG_GUI_DI, host=host)
    if phan.query:
        duong_dan = duong_dan + "?" + phan.query
    return phan.scheme, host, cong, duong_dan


# ---- Chuẩn bị yêu cầu ------------------------------------------------------------
def _kiem_tra_het_gio(timeout):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise _loi_vinh_vien("tham-so-sai", f"timeout phải là số giây, nhận {type(timeout).__name__}",
                             KET_CUC_KHONG_GUI_DI)
    t = float(timeout)
    if not math.isfinite(t) or t <= 0:
        raise _loi_vinh_vien("tham-so-sai", f"timeout phải là số hữu hạn > 0, nhận {t!r}",
                             KET_CUC_KHONG_GUI_DI)
    return t


def _chuan_bi_headers(headers):
    """Bản sao header của người gọi, đã kiểm. KHÔNG sửa dict của người gọi."""
    if not hasattr(headers, "items"):
        raise _loi_vinh_vien("tham-so-sai", f"headers phải là dict, nhận {type(headers).__name__}",
                             KET_CUC_KHONG_GUI_DI)
    ra = {}
    for ten, gt in headers.items():
        if not isinstance(ten, str) or not ten or any(c in ten for c in "\r\n: \t") \
                or not ten.isascii():
            # TÊN header không phải bí mật, nhưng một lời gọi sai kiểu có thể đặt GIÁ TRỊ vào vị trí
            # tên — và giá trị thì KHÔNG được in ra. `_mo_ta_ten` mô tả chỗ sai mà không in giá trị.
            raise _loi_vinh_vien("tham-so-sai",
                                 f"tên header không hợp lệ: {_mo_ta_ten(ten)}",
                                 KET_CUC_KHONG_GUI_DI)
        if ten.lower() == "transfer-encoding":
            # Thân là bytes đã mã hoá trọn vẹn; Content-Length do http.client đặt đúng.
            raise _loi_vinh_vien("tham-so-sai", "không nhận Transfer-Encoding",
                                 KET_CUC_KHONG_GUI_DI, header=_mo_ta_ten(ten))
        if ten.lower() == "content-length":
            # Bỏ qua giá trị người gọi đưa: để http.client đặt ĐÚNG độ dài thân thật.
            continue
        if gt is None or isinstance(gt, (bytes, bytearray)):
            # `str(None)` thành "None" và `str(b'x')` thành "b'x'" — đều là dữ liệu SAI gửi đi
            # mà không báo gì. Chặn ở đây.
            raise _loi_vinh_vien("tham-so-sai",
                                 f"header {_mo_ta_ten(ten)!r} nhận giá trị {type(gt).__name__} — "
                                 "không gửi được",
                                 KET_CUC_KHONG_GUI_DI, header=_mo_ta_ten(ten))
        s = gt if isinstance(gt, str) else str(gt)
        if "\r" in s or "\n" in s:
            # Chèn header (CRLF injection): giá trị KHÔNG được in ra, chỉ nêu tên.
            raise _loi_vinh_vien("tham-so-sai",
                                 f"header {_mo_ta_ten(ten)!r} chứa CR/LF — chèn header, TỪ CHỐI",
                                 KET_CUC_KHONG_GUI_DI, header=_mo_ta_ten(ten))
        try:
            s.encode("latin-1")
        except UnicodeEncodeError:
            raise _loi_vinh_vien(
                "tham-so-sai",
                f"header {_mo_ta_ten(ten)!r} có ký tự ngoài latin-1 — chữ có dấu phải nằm trong "
                "THÂN (UTF-8)",
                KET_CUC_KHONG_GUI_DI, header=_mo_ta_ten(ten)) from None
        ra[ten] = s
    if not any(ten.lower() == "content-type" for ten in ra):
        ra["Content-Type"] = CONTENT_TYPE_FORM
    return ra


def _ma_hoa_form(body):
    """→ bytes của thân `application/x-www-form-urlencoded`, UTF-8, percent-encoding chặt."""
    if not hasattr(body, "items"):
        raise _loi_vinh_vien("tham-so-sai", f"body phải là dict, nhận {type(body).__name__}",
                             KET_CUC_KHONG_GUI_DI)
    if not body:
        raise _loi_vinh_vien("tham-so-sai",
                             "thân RỖNG — J&T luôn cần trường `bizContent`; nhiều khả năng ai đó "
                             "quên dựng thân, chặn trước khi gửi",
                             KET_CUC_KHONG_GUI_DI)
    for ten, gt in body.items():
        if not isinstance(ten, str) or not ten:
            raise _loi_vinh_vien("tham-so-sai",
                                 f"tên trường form không hợp lệ: {_mo_ta_ten(ten)}",
                                 KET_CUC_KHONG_GUI_DI)
        if gt is None or isinstance(gt, (bytes, bytearray)):
            raise _loi_vinh_vien("tham-so-sai",
                                 f"trường form {_mo_ta_ten(ten)!r} nhận {type(gt).__name__} — "
                                 "không gửi được",
                                 KET_CUC_KHONG_GUI_DI, truong=_mo_ta_ten(ten))
        if isinstance(gt, float) and not math.isfinite(gt):
            raise _loi_vinh_vien("tham-so-sai", f"trường form {_mo_ta_ten(ten)!r} là NaN/vô cùng",
                                 KET_CUC_KHONG_GUI_DI, truong=_mo_ta_ten(ten))
        if not isinstance(gt, (str, int, float, bool)):
            raise _loi_vinh_vien("tham-so-sai",
                                 f"trường form {_mo_ta_ten(ten)!r} nhận {type(gt).__name__} — "
                                 "chỉ nhận str/int/float/bool",
                                 KET_CUC_KHONG_GUI_DI, truong=_mo_ta_ten(ten))
    try:
        chuoi = urlencode(dict(body), encoding="utf-8", errors="strict")
    except (TypeError, ValueError, UnicodeEncodeError) as e:
        raise _loi_vinh_vien("tham-so-sai", f"thân không mã hoá được thành form: {type(e).__name__}",
                             KET_CUC_KHONG_GUI_DI) from None
    return chuoi.encode("utf-8")


def _mo_ket_noi(scheme, host, cong, het_gio_ket_noi):
    if scheme == "https":
        return http.client.HTTPSConnection(host, cong, timeout=het_gio_ket_noi,
                                           context=ssl.create_default_context())
    return http.client.HTTPConnection(host, cong, timeout=het_gio_ket_noi)


def _dong(ket_noi):
    if ket_noi is None:
        return
    try:
        ket_noi.close()
    except Exception:
        pass


# ---- Biến ngoại lệ của thư viện thành ĐÚNG một trong hai loại lỗi của transport.py ---------------
def _loi_tu_ngoai_le(e, mo_ta, giai_doan, ma_http=0, can_che=None):
    """Ánh xạ NGOẠI LỆ của tầng socket/http.client sang `LoiTamThoi`/`LoiVinhVien`.

    `giai_doan` là thứ quyết định `ket_cuc`: hỏng TRƯỚC khi nối xong thì chắc chắn chưa có gì ra
    khỏi máy (`khong-gui-di`); hỏng sau đó thì KHÔNG BIẾT (`khong-biet`).

    `can_che`: tập giá trị phải che. Ngoại lệ THÔ của thư viện là dữ liệu NGOÀI — nó có thể mang
    theo thứ ta vừa gửi (`InvalidURL` mang URL, `IncompleteRead` mang thân đọc dở…), nên `str(e)`
    đi qua phép che TRƯỚC khi vào thông điệp. Đây là lớp chặn thứ hai; lớp thứ nhất là chặn URL
    chứa ký tự điều khiển ở `tach_url`.
    """
    da_gui = giai_doan != "kết nối"
    ket_cuc = KET_CUC_KHONG_BIET if da_gui else KET_CUC_KHONG_GUI_DI
    giai_doan_tv = {"kết nối": "khi đang nối", "gửi": "khi đang gửi yêu cầu",
                    "chờ phản hồi": "khi đang chờ phản hồi", "đọc thân": "khi đang đọc thân"}.get(
                        giai_doan, giai_doan)
    tho = f"{type(e).__name__}: {e}"
    if can_che:
        tho = _che_chuoi(tho, can_che)
    chung = f"{mo_ta} — hỏng {giai_doan_tv}: {tho}"
    # Hỏng NGAY GIỮA lúc đọc thân (đã có dòng trạng thái, thân chưa trọn) là một kết cục riêng:
    # ta BIẾT hãng đã trả lời, nhưng KHÔNG BIẾT nội dung — và thân đọc dở TUYỆT ĐỐI không được trả về.
    doc_do = giai_doan == "đọc thân"
    loai_het_gio = "than-doc-do" if doc_do else "het-gio"
    them_doc_do = {"than_dut": True} if doc_do else {}

    if isinstance(e, socket.timeout) or isinstance(e, TimeoutError):
        if doc_do:
            return _loi_tam_thoi(
                loai_het_gio,
                f"{chung}. Đã nhận mã HTTP {ma_http} nhưng THÂN ĐỌC DỞ — KHÔNG trả về, KHÔNG coi là "
                "thành công; hãng có thể đã xử lý yêu cầu.", KET_CUC_KHONG_BIET, ma_http, **them_doc_do)
        return _loi_tam_thoi(
            loai_het_gio,
            f"{chung}. KHÔNG BIẾT hãng đã xử lý hay chưa — tuyệt đối không coi là thành công; "
            "hãng CHƯA trả lời.", ket_cuc, ma_http, **them_doc_do)
    if isinstance(e, ssl.SSLCertVerificationError):
        return _loi_vinh_vien("tls-chung-that",
                              f"{chung}. Chứng thư TLS không hợp lệ — thử lại vô ích cho tới khi "
                              "cấu hình đúng.", KET_CUC_KHONG_GUI_DI, 0)
    if isinstance(e, ssl.SSLError):
        return _loi_tam_thoi("tls", f"{chung}. Tay bắt TLS hỏng (mạng/cấu hình) — thử lại được.",
                             ket_cuc, ma_http)
    if isinstance(e, http.client.RemoteDisconnected):
        return _loi_tam_thoi(
            "ket-noi-dut",
            f"{chung}. Hãng đóng kết nối KHÔNG trả lời — KHÔNG BIẾT yêu cầu đã được xử lý chưa.",
            ket_cuc, ma_http)
    if isinstance(e, ConnectionRefusedError):
        return _loi_tam_thoi(
            "tu-choi-ket-noi",
            f"{chung}. Bị TỪ CHỐI KẾT NỐI — yêu cầu CHƯA ra khỏi máy (thử lại an toàn, KHÔNG phải "
            "hãng từ chối: hãng chưa hề nói gì).", KET_CUC_KHONG_GUI_DI, 0)
    if isinstance(e, (ConnectionResetError, ConnectionAbortedError, BrokenPipeError)):
        return _loi_tam_thoi("ket-noi-dut", f"{chung}. Kết nối bị cắt — KHÔNG BIẾT kết quả.",
                             ket_cuc, ma_http)
    if isinstance(e, socket.gaierror):
        return _loi_tam_thoi("phan-giai-ten", f"{chung}. Không phân giải được tên máy chủ.",
                             KET_CUC_KHONG_GUI_DI, 0)
    if isinstance(e, (http.client.InvalidURL, UnicodeEncodeError, ValueError, TypeError)):
        # `InvalidURL` là CON của `HTTPException`, nên phải xét TRƯỚC nhánh HTTPException bên dưới:
        # URL không dựng được là lỗi VĨNH VIỄN, không phải "thử lại được".
        return _loi_vinh_vien("tham-so-sai", f"{chung}. Yêu cầu không dựng được — thử lại vô ích.",
                              KET_CUC_KHONG_GUI_DI, 0)
    if isinstance(e, http.client.HTTPException):
        return _loi_tam_thoi("than-doc-do" if doc_do else "http-khong-hop-le",
                             f"{chung}. Phản hồi không đọc được trọn theo HTTP — KHÔNG BIẾT kết quả.",
                             ket_cuc, ma_http, **them_doc_do)
    if isinstance(e, OSError):
        return _loi_tam_thoi("loi-mang", f"{chung}. Lỗi mạng — KHÔNG BIẾT kết quả.", ket_cuc,
                             ma_http)
    # Ngoại lệ KHÔNG RÕ loại: coi là VĨNH VIỄN. Thà mất một lượt còn hơn gửi lại một đơn đã vào
    # hãng; lỗi lạ mà thử lại mù quáng là cách tạo đơn trùng.
    return _loi_vinh_vien("loi-khong-ro",
                          f"{chung}. Loại lỗi chưa từng gặp — KHÔNG thử lại (an toàn cho thao tác ghi).",
                          KET_CUC_KHONG_BIET if da_gui else KET_CUC_KHONG_GUI_DI, ma_http)


def _doc_retry_after(gia_tri):
    """`Retry-After` → số giây (float), hoặc `None` nếu không đọc được. Nhận CẢ HAI dạng của RFC:
    số giây (`120`, `120.5`) và HTTP-date (`Wed, 21 Oct 2026 07:28:00 GMT`)."""
    s = (gia_tri or "").strip()
    if not s:
        return None
    try:
        giay = float(s)
        if not math.isfinite(giay):        # "inf"/"1e400": hãng không được chọn vô cùng
            return float("inf")
        return giay
    except ValueError:
        pass
    try:
        moc = parsedate_to_datetime(s)
    except (TypeError, ValueError, OverflowError):
        return None
    if moc is None:
        return None
    if moc.tzinfo is None:                 # chuỗi không mang múi giờ ⇒ hiểu là UTC (đúng RFC)
        moc = moc.replace(tzinfo=_dt.timezone.utc)
    return (moc - _dt.datetime.now(_dt.timezone.utc)).total_seconds()


def _cho_theo_retry_after(headers_tra_loi, can_che):
    """→ `(cho_giay | None, bi_cat: bool, gia_tri_da_che: str)`.

    KẸP TRẦN ở `transport.CHO_TOI_DA`. Giá trị thô của header được CHE trước khi vào thông điệp:
    đó là dữ liệu NGOÀI, một máy chủ echo lại có thể nhét bí mật của ta vào chính header này.
    """
    tho = None
    for ten, gt in headers_tra_loi:
        if ten.lower() == "retry-after":
            tho = str(gt)
            break
    if tho is None:
        return None, False, ""
    da_che = che_bi_mat(tho.encode("utf-8", "replace"), can_che).decode("utf-8", "replace")
    giay = _doc_retry_after(tho)
    if giay is None:
        return None, False, da_che
    bi_cat = (not math.isfinite(giay)) or giay > transport.CHO_TOI_DA
    return max(0.0, min(giay, transport.CHO_TOI_DA)), bi_cat, da_che


def _loi_cho_lai(loai, ma_http, mo_ta, than, headers_tra_loi, can_che, them):
    """Dựng `LoiTamThoi` cho 408/429 — hai mã mà hãng NÓI THẲNG 'thử lại sau'.

    429 = bị giới hạn tần suất (`qua-han-muc`); 408 = hãng không nhận kịp yêu cầu (`khong-gui-di`,
    vì chắc chắn CHƯA xử lý gì). Cả hai: `LoiTamThoi`, kèm `cho_giay` ĐÃ KẸP TRẦN để `transport.goi()`
    dùng, và **không ngủ ở đây**.
    """
    cho, bi_cat, tho_ra = _cho_theo_retry_after(headers_tra_loi, can_che)
    if cho is None:
        mo_ta_cho = ("hãng KHÔNG gửi `Retry-After` đọc được ⇒ để `cho_giay=None`, "
                     "`transport.goi()` dùng backoff của chính sách")
    elif bi_cat:
        mo_ta_cho = (f"`Retry-After: {tho_ra!r}` ⇒ chờ {cho:g} giây (ĐÃ KẸP TRẦN "
                     f"{transport.CHO_TOI_DA:g}s — hãng không được quyết định treo tiến trình)")
    else:
        mo_ta_cho = f"`Retry-After: {tho_ra!r}` ⇒ chờ {cho:g} giây"
    if loai == "http-429":
        dau = (f"{mo_ta} — hãng trả HTTP 429: BỊ GIỚI HẠN TẦN SUẤT (KHÁC 5xx, KHÁC 'hãng từ chối'). "
               f"Hãng CHƯA xử lý yêu cầu và bảo chờ")
        ket_cuc = KET_CUC_QUA_HAN_MUC
    else:
        dau = (f"{mo_ta} — hãng trả HTTP 408: hãng KHÔNG NHẬN KỊP yêu cầu (KHÁC 5xx: chắc chắn CHƯA "
               f"xử lý gì). Thử lại được")
        ket_cuc = KET_CUC_KHONG_GUI_DI
    return _loi_tam_thoi(
        loai,
        f"{dau}. {mo_ta_cho}. Lớp này **KHÔNG tự chờ và KHÔNG tự thử lại** — việc thử lại thuộc "
        f"`transport.goi()`; `cho_giay` là gợi ý cho nó. Thân trả lời (đã che, {len(than)} byte): "
        f"{them['than_da_che'][:200].decode('utf-8', 'replace')!r}",
        ket_cuc, ma_http, cho_giay=cho, gioi_han_tan_suat=(loai == "http-429"),
        retry_after_bi_cat=bi_cat, **them)


def _tra_loi_tu_http(ma_http, than, headers_tra_loi, mo_ta, can_che):
    """Phân loại theo mã HTTP. CHỈ 2xx mới trả `TraLoiHTTP`; mọi mã khác NÉM, không bao giờ trả."""
    if 200 <= ma_http <= 299:
        da_che = {ten: che_bi_mat(str(gt).encode("utf-8", "replace"), can_che).decode(
            "utf-8", "replace") for ten, gt in headers_tra_loi}
        return TraLoiHTTP(ma_http, than, da_che)
    than_sach = che_bi_mat(than, can_che) if than else b""
    them = {"than_da_che": than_sach, "so_byte_than": len(than),
            "headers_da_che": {ten: che_bi_mat(str(gt).encode("utf-8", "replace"), can_che).decode(
                "utf-8", "replace") for ten, gt in headers_tra_loi},
            "mo_ta_yeu_cau": mo_ta}
    if 300 <= ma_http <= 399:
        raise _loi_vinh_vien(
            "http-3xx",
            f"{mo_ta} — hãng trả HTTP {ma_http} (chuyển hướng). KHÔNG đi theo chuyển hướng: đi theo "
            "là phá danh sách trắng máy chủ. Thử lại vô ích cho tới khi URL đúng.",
            KET_CUC_HANG_TU_CHOI, ma_http, **them)
    if ma_http in (408, 429):
        # QUYẾT ĐỊNH CỦA AG-00 (15/10/2026): 429 VÀ 408 là LỖI TẠM THỜI, tách khỏi luật
        # "4xx = vĩnh viễn". 429 = hãng bảo chờ; 408 = hãng không nhận kịp ⇒ chưa xử lý gì.
        # `loi_hang.tu_http` cũng đã nói đúng như vậy (429 → `QUA_HAN_MUC`, 408 → `HET_GIO`, cả hai
        # `co_the_thu_lai=True`) — nay HAI LỚP ĐỒNG Ý, và có ca canh chống lệch (`test_b10`).
        # KHÔNG nới bất kỳ mã 4xx nào khác.
        raise _loi_cho_lai("http-429" if ma_http == 429 else "http-408",
                           ma_http, mo_ta, than, headers_tra_loi, can_che, them)
    if 400 <= ma_http <= 499:
        raise _loi_vinh_vien(
            "http-4xx",
            f"{mo_ta} — hãng trả HTTP {ma_http}. Thử lại vô ích (sai tham số/chữ ký/quyền). "
            f"Thân trả lời (đã che bí mật, {len(than)} byte): "
            f"{than_sach[:200].decode('utf-8', 'replace')!r}",
            KET_CUC_HANG_TU_CHOI, ma_http, **them)
    if 500 <= ma_http <= 599:
        raise _loi_tam_thoi(
            "http-5xx",
            f"{mo_ta} — hãng trả HTTP {ma_http}. Lỗi phía hãng: KHÔNG BIẾT yêu cầu đã được xử lý "
            f"chưa — không coi là thành công. Thân trả lời (đã che, {len(than)} byte): "
            f"{than_sach[:200].decode('utf-8', 'replace')!r}",
            KET_CUC_KHONG_BIET, ma_http, **them)
    raise _loi_vinh_vien(
        "http-la",
        f"{mo_ta} — hãng trả mã HTTP {ma_http} không thuộc nhóm nào đã biết. Không đoán, "
        "không thử lại.", KET_CUC_KHONG_BIET, ma_http, **them)


def gui_form(url, headers, body, *, timeout):
    """Gửi MỘT lượt POST `application/x-www-form-urlencoded` tới J&T. Hợp đồng §36.

    Ném `transport.LoiTamThoi`  khi ĐÁNG thử lại (mạng, hết giờ, 5xx).
    Ném `transport.LoiVinhVien` khi thử lại VÔ ÍCH (3xx; 4xx TRỪ 408/429; URL sai; chốt chặn
    danh sách trắng).
    Ném `transport.LoiTamThoi` (kèm `cho_giay` đã kẹp trần `transport.CHO_TOI_DA`) cho 408/429 —
    hai mã hãng NÓI THẲNG "thử lại sau". **Hàm này KHÔNG BAO GIỜ NGỦ**: `cho_giay` chỉ là gợi ý,
    `transport.goi()` mới là chỗ chờ (có ca thử soát bằng AST, `test_b11`).
    KHÔNG tự thử lại — việc thử lại thuộc `transport.goi()`.

    `timeout` là hạn ĐỌC (giây) sau khi đã nối; hạn NỐI là `min(timeout, HET_GIO_KET_NOI_TOI_DA)`.
    Cả hai đều tường minh, không có nhánh "chờ vô hạn".

    ĐO ĐƯỢC (AG-02, `thu_http_jt.k6`): `timeout` là hạn của TỪNG thao tác đọc trên socket, KHÔNG
    phải hạn tổng của lượt gọi. Một máy chủ nhỏ giọt (mỗi byte cách nhau ít hơn `timeout`) giữ được
    lượt gọi lâu hơn `timeout` mà vẫn trả về thân TRỌN VẸN. Đó là giới hạn đã biết, không phải "hạn
    tổng" — xem `docs/G17_TRANSPORT.md` §4.4.

    Hai thuộc tính người gọi nên đọc trên ngoại lệ: `.timeout` (True = KHÔNG BIẾT kết quả) và
    `.ket_cuc` (`khong-biet` / `khong-gui-di` / `hang-tu-choi`) — xem chú thích đầu tệp.
    """
    scheme, host, cong, dich = tach_url(url)                       # §36 luật 2, TRƯỚC mọi thứ
    het_gio_doc = _kiem_tra_het_gio(timeout)
    het_gio_ket_noi = min(het_gio_doc, HET_GIO_KET_NOI_TOI_DA)
    headers_gui = _chuan_bi_headers(headers)
    than_gui = _ma_hoa_form(body)
    can_che = _gia_tri_can_che(headers_gui, than_gui, url)
    # `mo_ta` KHÔNG đi qua phép che, và đó là chủ ý: nó chỉ nêu TÊN (header, trường form) và ĐƯỜNG
    # DẪN, không nêu query. Che nó đi sẽ làm hỏng chính ca tự kiểm `test_g3` — ca đó đột biến hàm
    # dựng mô tả để in giá trị header ra và đòi ca rò rỉ phải ĐỎ. Che `mo_ta` là làm ca đó hết răng.
    mo_ta = mo_ta_yeu_cau(url, headers_gui, than_gui)

    ket_noi = None
    ma_http = 0
    giai_doan = "kết nối"
    loi = None
    try:
        ket_noi = _mo_ket_noi(scheme, host, cong, het_gio_ket_noi)
        ket_noi.connect()                                          # hạn NỐI ở đây
        try:
            ket_noi.sock.settimeout(het_gio_doc)                   # hạn ĐỌC, siết sau khi nối
        except (AttributeError, OSError):
            pass
        giai_doan = "gửi"
        ket_noi.request("POST", dich, body=than_gui, headers=headers_gui)
        giai_doan = "chờ phản hồi"
        phan_hoi = ket_noi.getresponse()
        ma_http = int(phan_hoi.status)
        giai_doan = "đọc thân"
        than = phan_hoi.read()
        headers_tra_loi = phan_hoi.getheaders()
    except Exception as e:
        _dong(ket_noi)
        # Ngoại lệ THÔ có thể mang theo dữ liệu của ta (`IncompleteRead` giữ nguyên thân đọc dở,
        # `InvalidURL` giữ nguyên URL). Dựng ngoại lệ ĐÃ CHE ở đây, nhưng NÉM nó ở NGOÀI khối
        # `except`: ném trong khối thì Python gắn ngoại lệ thô vào `__context__`, và `__context__`
        # là thứ một bộ ghi log đi theo chuỗi cũng đọc tới. Ném ngoài ⇒ `__context__` là `None` —
        # đo được (`thu_http_jt.j7`).
        loi = _loi_tu_ngoai_le(e, mo_ta, giai_doan, ma_http, can_che=can_che)
    _dong(ket_noi)
    if loi is not None:
        raise loi from None
    if giai_doan != "đọc thân":
        # Không thể tới đây: `read()` là bước cuối. Giữ lại như một chốt chặn chống sửa sai về sau.
        raise _loi_vinh_vien("loi-khong-ro", f"{mo_ta} — luồng gửi kết thúc ở giai đoạn lạ",
                             KET_CUC_KHONG_BIET, ma_http)
    return _tra_loi_tu_http(ma_http, than, headers_tra_loi, mo_ta, can_che)
