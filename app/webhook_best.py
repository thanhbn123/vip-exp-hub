# B3 — BEST EXPRESS WEBHOOK (AGENT B3).
#
# PHẠM VI: mô-đun MỚI, dùng CHUNG hub `webhook.py` (không dựng service độc lập, không sửa
# `webhook.py`/`server.py`/`csdl.py` vì đó là tệp của AG-00). Tệp này chỉ:
#   · xác thực callback bằng ĐÚNG sơ đồ mà hub chọn cho tài khoản hãng,
#   · giải tenant từ dòng `carrier_accounts` đã tra được trên URL — KHÔNG BAO GIỜ từ payload,
#   · lưu sự kiện thô vào `wh_su_kien` (cùng bảng, cùng UNIQUE chống trùng của hub),
#   · chuẩn hoá mã BEST → trạng thái chung, cập nhật đơn + lịch sử + audit.
#
# TRẠNG THÁI BẰNG CHỨNG: MOCK. Tài liệu API BEST trong đề bài là Google Docs và KHÔNG đọc được
# trong môi trường này. Vì vậy:
#   · 11 bước, tên trường payload, phản hồi `{"Result": 1, "Message": ""}`, luật tenant và
#     nghĩa "606 mở lại chiều giao" là ĐẶC TẢ ĐÃ XÁC NHẬN trong đề bài; nghĩa 605 là GIẢ THUYẾT;
#   · NGHĨA của từng mã trạng thái và CƠ CHẾ XÁC THỰC của BEST là CHƯA KIỂM CHỨNG. Bảng mã dưới
#     đây là GIẢ THUYẾT PHÂN NHÓM để dựng máy trạng thái, mỗi dòng ghi rõ `muc = CHUA_KIEM_CHUNG`.
#     Không dùng bảng này để đối soát tài chính hay để tuyên bố đã hiểu tài liệu hãng.
#   · Với môi trường sandbox/production, hub KHÔNG có sơ đồ xác thực BEST ⇒ `chon_so_do()` trả
#     None ⇒ mô-đun TỪ CHỐI (BLOCKED), không đoán header/chữ ký. Đường MOCK dùng HMAC của hub
#     (`X-Webhook-Signature`), đúng như callback mô phỏng của chính dự án.
#
# KHÔNG gọi API BEST, KHÔNG tạo đơn thật, KHÔNG dùng credentials thật, KHÔNG ghi secret/token
# vào payload_tho/headers_json/audit/response/sổ.
#
# 11 BƯỚC BẮT BUỘC (thứ tự được canh bằng `TEN_BUOC` và ca thử `test_f05`):
#   1 xac_thuc_webhook          7 luu_raw_event_an_toan
#   2 xac_dinh_tai_khoan_hang   8 chuan_hoa_trang_thai
#   3 xac_dinh_tenant           9 cap_nhat_don
#   4 kiem_tracking_code       10 ghi_lich_su_trang_thai
#   5 kiem_merchant_order_code 11 ghi_audit
#   6 kiem_trung_su_kien
#
# GHI CHÚ VỀ SỐ LƯỢNG MÃ: đề bài nói "24 mã" nhưng danh sách liệt kê chỉ có 23 con số
# (211/203/202/301/302/303/304/309/601/604/666/605/606/701/702/703/704/705/707/708/777/1000/2).
# Mô-đun KHÔNG tự bịa thêm mã thứ 24. `SO_MA_DE_BAI=24`, `SO_MA_LIET_KE=23`,
# `GHI_CHU_SO_LUONG` nói thẳng chênh lệch; bộ thử phủ đủ 23 mã + 1 ca "mã lạ" làm đối chứng
# (tổng 24 lượt kịch bản, không phải 24 mã hãng).
import hashlib
import json
import re
import time
from decimal import Decimal, InvalidOperation

import best_hop_dong
import cau_hinh
import csdl
import don_hang
import webhook as hub
import xac_thuc_best

HANG = "best"
TEN_HANG = "BEST Express"
PHIEN_BAN = "b3-best-webhook-2026-10-19"

# Mức bằng chứng — dùng đúng từ vựng của hub để không nâng mức bằng lời.
MUC_MOCK = "MOCK VERIFIED"
MUC_CHUA_KIEM_CHUNG = "CHUA_KIEM_CHUNG"
MUC_DA_TAI_LIEU = "DA_TAI_LIEU"
MUC_BLOCKED = "BLOCKED"
MUC_TAI_LIEU = MUC_DA_TAI_LIEU

NGUON_DE_BAI = "đề bài AGENT B3 (danh sách mã)"
NGUON_TAI_LIEU = best_hop_dong.NGUON
NGUON_GIA_THUYET = ("mã không có trong tài liệu chính thức — KHÔNG đoán nghĩa")

# 11 bước bắt buộc. Tên là HỢP ĐỒNG: bộ thử canh đúng thứ tự này, không chỉ canh "có chạy".
TEN_BUOC = (
    "xac_thuc_webhook",
    "xac_dinh_tai_khoan_hang",
    "xac_dinh_tenant",
    "kiem_tracking_code",
    "kiem_merchant_order_code",
    "kiem_trung_su_kien",
    "luu_raw_event_an_toan",
    "chuan_hoa_trang_thai",
    "cap_nhat_don",
    "ghi_lich_su_trang_thai",
    "ghi_audit",
)

# Trạng thái chung: 6 trạng thái của hub + `da_huy` chỉ để GHI NHẬN (hủy là quyết định nghiệp vụ
# của Order Service, không phải một hạng trong trục giao vận — xem `_cap_nhat_don`).
TRANG_THAI_CHUNG = tuple(cau_hinh.HANG_TRANG_THAI_GIAO) + ("da_huy",)
TRANG_THAI_HOAN_TAT = ("giao_thanh_cong", "hoan_hang", "da_huy")

# Trần thân yêu cầu. Webhook vô danh không có trần là đường làm kiệt máy; con số này chỉ chặn
# payload phi lý, không phải suy đoán giới hạn của hãng.
GIOI_HAN_BODY = 256 * 1024
GIOI_HAN_MO_TA = 4000
# Cửa sổ hợp lý cho mốc hãng. Đây KHÔNG phải đặc tả BEST (chưa có tài liệu): chỉ là chốt an
# toàn nội bộ để một `modified_at` xa tương lai không đẩy watermark lên năm 5138 rồi đóng băng
# mọi sự kiện sau của đơn. Cho phép lệch đồng hồ 1 ngày về tương lai và tối đa 5 năm về quá khứ.
CUA_SO_TUONG_LAI_MS = 24 * 60 * 60 * 1000
CUA_SO_QUA_KHU_MS = 5 * 365 * 24 * 60 * 60 * 1000

# ============================================================================
# BẢNG MÃ BEST — 23 mã LIỆT KÊ + ghi chú chênh lệch với con số 24 của đề bài
# ============================================================================
SO_MA_DE_BAI = 23          # tài liệu chính thức liệt kê 23 mã
SO_MA_LIET_KE = 23
# Danh sách NGUYÊN VĂN trong đề bài, giữ đúng thứ tự. Bảng `BANG_MA` phải phủ đúng tập này;
# bộ thử so hai tập thay vì tin rằng người viết đã chép đủ.
MA_TRONG_DE_BAI = (211, 203, 202, 301, 302, 303, 304, 309, 601, 604, 666, 605, 606,
                   701, 702, 703, 704, 705, 707, 708, 777, 1000, 2)
GHI_CHU_SO_LUONG = (
    "Tài liệu chính thức của BEST (đọc 2026-10-19) liệt kê ĐÚNG 23 mã trạng thái. "
    "Đề bài cũ ghi '24 mã' nhưng chỉ có 23 con số — KHÔNG bịa mã thứ 24. "
    "Bộ thử phủ 23 mã + 1 mã lạ đối chứng (24 LƯỢT KỊCH BẢN)."
)


def _dong(ma, mo_ta, chung, mo_lai=False, can_soat=False):
    """Một dòng bảng mã ĐỌC TỪ TÀI LIỆU CHÍNH THỨC (mức `DA_TAI_LIEU`)."""
    return {
        "ma": ma,
        "mo_ta": mo_ta,
        "chung": chung,
        "mo_lai": bool(mo_lai),
        "can_soat": bool(can_soat),
        "muc": MUC_DA_TAI_LIEU,
        "nguon": NGUON_TAI_LIEU,
    }


# Thứ tự dòng GIỮ NGUYÊN thứ tự đề bài. `606` mang cờ `mo_lai=True` theo đặc tả đã xác nhận:
# "606 mở lại chiều giao". `605` đứng ngay trước nó để cặp 605→606 đọc được thành một khối.
BANG_MA = {
    ma: _dong(ma, mo_ta, chung, mo_lai=(ma == best_hop_dong.MA_MO_LAI), can_soat=can_soat)
    for ma, (mo_ta, chung, can_soat) in best_hop_dong.BANG_MA.items()
}
assert set(BANG_MA) == set(MA_TRONG_DE_BAI), "BANG_MA phải khớp đúng 23 mã tài liệu"


# Máy trạng thái: chỉ những bước có nghĩa nghiệp vụ mới được đi. Đây KHÔNG phải bảng xếp hạng
# mã; thứ tự đến/đi do `modified_at` quyết định (xem `_cap_nhat_don`). Bảng này chỉ chặn bước
# phi lý (ví dụ từ "đã giao" quay lại "chờ lấy" mà không có 606 mở lại).
CHUYEN_DUOC = {
    None: {"cho_lay", "lay_hang", "dang_giao", "giao_that_bai", "giao_thanh_cong", "hoan_hang"},
    "cho_lay": {"cho_lay", "lay_hang", "dang_giao", "giao_that_bai", "giao_thanh_cong",
                "hoan_hang"},
    "lay_hang": {"lay_hang", "dang_giao", "giao_that_bai", "giao_thanh_cong", "hoan_hang"},
    "dang_giao": {"dang_giao", "giao_that_bai", "giao_thanh_cong", "hoan_hang"},
    # KHÔNG có cạnh `giao_that_bai → dang_giao` thường: đó là hạ hạng, và việc mở lại chiều
    # giao chỉ được phép bằng đúng 606. Giữ cạnh đó sẽ buộc mô-đun tự UPDATE đơn, vượt
    # `don_hang.ap_trang_thai_giao` — đúng thứ chốt cấu trúc G06 cấm.
    "giao_that_bai": {"giao_that_bai", "giao_thanh_cong", "hoan_hang"},
    # Ba trạng thái cuối chỉ mở lại bằng đúng mã 606 (`mo_lai=True`), không bằng bất kỳ mã nào
    # khác — kể cả khi `modified_at` mới hơn.
    "giao_thanh_cong": set(),
    "hoan_hang": set(),
    "da_huy": set(),
}


class LoiDuLieu(Exception):
    """Payload không đúng đặc tả. Có mã HTTP để tầng gọi trả lời được, không phải 500 mù."""

    def __init__(self, ly_do, http=422):
        super().__init__(ly_do)
        self.http = http
        self.ly_do = ly_do


class LoiLuuTru(Exception):
    """Không ghi bền được sự kiện thô. Đây là lý do DUY NHẤT được phép trả Result != 1."""


class KetQua:
    """Kết quả một lượt webhook. `body` là thân phản hồi ĐÚNG đặc tả khi thành công.

    `buoc` là DẤU VẾT 11 bước đã chạy — bộ thử đọc nó thay vì tin lời docstring.
    `event_id` là khóa chống trùng đã dùng; KHÔNG phải mã vận đơn.
    """

    def __init__(self, http, body, su_kien_id=None, trung=False, buoc=(), ket_cuc="",
                 event_id=None, don_id=None, chi_tiet=None):
        self.http = http
        self.body = body
        self.su_kien_id = su_kien_id
        self.trung = trung
        self.buoc = tuple(buoc)
        self.ket_cuc = ket_cuc
        self.event_id = event_id
        self.don_id = don_id
        self.chi_tiet = chi_tiet or {}

    @property
    def thanh_cong(self):
        return self.body.get("Result") == 1 and self.body.get("Message") == ""

    def __repr__(self):
        return (f"KetQua(http={self.http}, ket_cuc={self.ket_cuc!r}, trung={self.trung}, "
                f"su_kien_id={self.su_kien_id})")


def thanh_cong():
    """Thân phản hồi DUY NHẤT được dùng cho ACK thành công — đúng đặc tả, không thêm trường."""
    return {"Result": 1, "Message": ""}


def that_bai(ly_do):
    """Thân phản hồi khi TỪ CHỐI. Hình dạng này CHƯA có trong đặc tả (đề bài chỉ chốt ca
    thành công), nên chỉ giữ đúng hai khóa và ghi rõ lý do — không bịa thêm trường."""
    return {"Result": 0, "Message": str(ly_do)}


def _so_nguyen(v):
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v).strip()
    return int(s) if re.fullmatch(r"[+-]?\d+", s) else None


def _so_khong_am(v, ten):
    """Kiểm một trường tiền/khối lượng/kích thước. Trả Decimal hoặc None.

    Dùng Decimal chứ không float: đây là số tiền, và `0.1 + 0.2` không phải chuyện của kế toán.
    Không tự quy đổi đơn vị (gram/cm/kg) — đơn vị chưa có trong đặc tả đã xác nhận.
    """
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if isinstance(v, bool):
        raise LoiDuLieu(f"{ten} phải là số, không phải boolean")
    s = str(v).strip().replace(",", "")
    try:
        d = Decimal(s)
    except (InvalidOperation, ValueError):
        raise LoiDuLieu(f"{ten} không phải số hợp lệ")
    if not d.is_finite():
        raise LoiDuLieu(f"{ten} không hữu hạn")
    if d < 0:
        raise LoiDuLieu(f"{ten} không được âm")
    return d


def _kiem_ma(v, ten):
    """Mã vận đơn/mã đơn: không rỗng, không khoảng trắng/điều khiển, tối đa 128 ký tự.

    CỐ Ý không ép một định dạng riêng của BEST: định dạng mã CHƯA có trong đặc tả đã xác nhận.
    """
    s = "" if v is None else str(v).strip()
    if not s:
        raise LoiDuLieu(f"thiếu {ten}")
    if len(s) > 128:
        raise LoiDuLieu(f"{ten} dài quá 128 ký tự")
    if re.search(r"[\s\x00-\x1f\x7f]", s):
        raise LoiDuLieu(f"{ten} chứa khoảng trắng/ký tự điều khiển")
    return s


# Toàn bộ trường đề bài đã xác nhận. Bộ thử canh đủ 18 tên này trong payload lưu thô.
TRUONG_PAYLOAD = (
    "code_best", "merchant_order_code", "cod", "product_price", "status", "status_content",
    "freight_fee", "cod_fee", "insurance_fee", "vat_fee", "return_fee", "discount",
    "modified_at", "total_fee", "weight", "length", "width", "height",
)
TRUONG_BAT_BUOC = ("code_best", "merchant_order_code", "status", "modified_at")
TRUONG_SO = ("cod", "product_price", "freight_fee", "cod_fee", "insurance_fee", "vat_fee",
             "return_fee", "discount", "total_fee", "weight", "length", "width", "height")

# Khóa bị che trước khi ghi payload_tho. BEST không khai token trong payload đã xác nhận,
# nhưng để hở nghĩa là lớp sau có thể ghi secret mà không ai thấy.
_KHOA_NHAY_CAM = ("token", "secret", "password", "passwd", "authorization", "cookie",
                  "signature", "chu_ky", "mat_khau", "api_key", "apikey")
_HEADER_DUOC_LUU = ("content-type", "content-length", "user-agent", "host", "x-request-id",
                     "x-best-timestamp", "timestamp")


def _la_khoa_nhay_cam(k):
    return any(x in str(k).lower() for x in _KHOA_NHAY_CAM)


def lam_sach(v, do_sau=0):
    """Che mọi giá trị nằm dưới khóa nhạy cảm, đệ quy có trần độ sâu.

    Không dùng `str(payload)` rồi regex: regex sẽ bỏ sót khóa lồng nhau và có thể cắt nhầm dữ
    liệu nghiệp vụ. Đi theo cấu trúc là cách duy nhất biết chắc "cái gì là token".
    """
    if do_sau > 12:
        return "[QUA_SAU]"
    if isinstance(v, dict):
        return {(k): ("[DA_CHE]" if _la_khoa_nhay_cam(k) else lam_sach(x, do_sau + 1))
                for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [lam_sach(x, do_sau + 1) for x in v]
    return v


def _headers_an_toan(headers):
    """Chỉ lưu header trong danh sách trắng, giá trị đã cắt độ dài.

    KHÔNG lưu `X-Webhook-Signature`, `Authorization`, `Cookie`: chữ ký là MAC của secret
    (phát lại được nếu lộ), token thì tuyệt đối không. Header lạ bị bỏ, không lưu tên.
    """
    hd = _headers_thuong(headers)
    sach = {}
    for k in _HEADER_DUOC_LUU:
        if k in hd and str(hd[k]).strip():
            sach[k] = str(hd[k])[:512]
    return sach


def _headers_thuong(headers):
    if not headers:
        return {}
    return {str(k).lower(): str(v) for k, v in dict(headers).items()}


def _claim_tenant(d):
    """Payload khai tenant — CHỈ để ghi lại là có người cố khai, KHÔNG BAO GIỜ dùng."""
    for t in ("tenant_id", "tenantId", "tenant"):
        if t in d:
            return d[t]
    return None


def doc_payload(body):
    """Đọc + kiểm payload BEST theo ĐÚNG 18 trường đã xác nhận. Trả dict chuẩn hoá.

    Không nhận form-urlencoded, không nhận XML, không đoán tên trường camelCase: đặc tả đã xác
    nhận là JSON với các tên snake_case dưới đây. Thêm trường lạ thì bỏ qua (tiến hoá được),
    nhưng trường lạ KHÔNG được dùng để quyết định tenant hay trạng thái.
    """
    if not isinstance(body, (bytes, bytearray)):
        raise LoiDuLieu("thân yêu cầu phải là bytes")
    if len(body) > GIOI_HAN_BODY:
        raise LoiDuLieu(f"thân yêu cầu quá lớn ({len(body)} > {GIOI_HAN_BODY} byte)", http=413)
    try:
        van_ban = bytes(body).decode("utf-8")
    except UnicodeDecodeError:
        raise LoiDuLieu("thân yêu cầu không phải UTF-8")
    try:
        d = json.loads(van_ban)
    except ValueError:
        raise LoiDuLieu("thân yêu cầu không phải JSON hợp lệ")
    if not isinstance(d, dict):
        raise LoiDuLieu("thân yêu cầu phải là một đối tượng JSON")

    for ten in TRUONG_BAT_BUOC:
        if ten not in d or d[ten] is None or str(d[ten]).strip() == "":
            raise LoiDuLieu(f"thiếu trường bắt buộc '{ten}'")

    code_best = _kiem_ma(d["code_best"], "code_best")
    merchant = _kiem_ma(d["merchant_order_code"], "merchant_order_code")
    # Tài liệu có 22 mã số + nhãn chữ `customer Cancel`. Không được `int()` thẳng rồi vứt sự
    # kiện hủy thật thành "payload sai kiểu". Mã số lạ vẫn được nhận để lưu thô + cần soát.
    status, status_raw, _la_customer_cancel, _biet = \
        best_hop_dong.chuan_hoa_ma_trang_thai(d["status"])
    if status is None or status < 0:
        raise LoiDuLieu("status phải là số nguyên không âm hoặc nhãn 'customer Cancel'")

    try:
        moc = hub._moc_chuan(d["modified_at"])
    except (TypeError, ValueError, OverflowError) as e:
        # `_moc_chuan` là hàm dùng chung của hub. Nó ném với NaN/Infinity hoặc offset múi giờ
        # không hợp lệ (ví dụ +99:99). Payload sai kiểu là lỗi NGƯỜI GỬI (422), không phải 500;
        # không chép giá trị thô vào thông điệp để không biến một trường số thành đường rò dữ liệu.
        raise LoiDuLieu(f"modified_at không đọc được thành mốc thời gian ({type(e).__name__})")
    if not moc:
        raise LoiDuLieu("modified_at không đọc được thành mốc thời gian")
    if len(moc) != 14:
        # Hợp đồng nội bộ dùng chuỗi 14 chữ số (epoch mili giây). Mốc dài hơn là dữ liệu nằm
        # ngoài dải đã chọn, không được để nó âm thầm đi vào so sánh watermark.
        raise LoiDuLieu("modified_at nằm ngoài dải thời gian 14 chữ số đã chọn")
    try:
        moc_ms = int(moc)
    except ValueError:
        raise LoiDuLieu("modified_at không đọc được thành mốc thời gian")
    now_ms = int(time.time() * 1000)
    # 14 chữ số vẫn có thể là năm 5138 (`99999999999999`). Nếu nhận, watermark của đơn bị đẩy
    # lên mốc đó và MỌI sự kiện sau — kể cả 606 — bị coi là "đến muộn", đóng băng trạng thái.
    # Đây là chặn an toàn nội bộ, không phải khẳng định về múi giờ/định dạng của hãng.
    if moc_ms > now_ms + CUA_SO_TUONG_LAI_MS:
        raise LoiDuLieu("modified_at ở tương lai quá xa — không dùng làm mốc")
    if moc_ms < now_ms - CUA_SO_QUA_KHU_MS:
        raise LoiDuLieu("modified_at quá cũ — không dùng làm mốc")

    mo_ta = d.get("status_content")
    if mo_ta is not None:
        mo_ta = str(mo_ta)
        if len(mo_ta) > GIOI_HAN_MO_TA:
            raise LoiDuLieu(f"status_content dài quá {GIOI_HAN_MO_TA} ký tự")
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", mo_ta):
            raise LoiDuLieu("status_content chứa ký tự điều khiển")

    for ten in TRUONG_SO:
        _so_khong_am(d.get(ten), ten)

    return {
        "tho": d,
        "tho_sach": lam_sach(d),
        "code_best": code_best,
        "merchant_order_code": merchant,
        "status": status,
        "status_raw": status_raw,
        "status_content": mo_ta,
        "modified_at_raw": d["modified_at"],
        "moc": moc,
        "claim_tenant": _claim_tenant(d),
    }


def _khoa_su_kien(p):
    """Khóa chống trùng BỀN của một sự kiện BEST.

    Gồm mã vận đơn + MỐC ĐÃ CHUẨN HOÁ + mã trạng thái + mã đơn. Dùng mốc chuẩn hoá (không dùng
    chuỗi thô) để cùng một sự kiện gửi lại với định dạng thời gian khác vẫn trùng. KHÔNG băm
    toàn bộ thân: đây là KHÓA NGHIỆP VỤ. Hai sự kiện cùng bốn trường nhưng khác fees/
    status_content được coi là MỘT sự kiện; bản ghi đầu thắng, bản sau được ACK idempotent.
    """
    # Dùng nhãn gốc (`customer Cancel` khác `2`) để hai sự kiện khác nguồn không bị gộp oan.
    goc = (f"{p['code_best']}\x1f{p['moc']}\x1f{p.get('status_raw', p['status'])}"
           f"\x1f{p['merchant_order_code']}")
    return "best-" + hashlib.sha256(goc.encode("utf-8")).hexdigest()[:40]


def chuan_hoa_trang_thai(ma):
    """Mã BEST → trạng thái chung. Trả dict; mã lạ `biet_ma=False`, `chung=None`.

    KHÔNG ném lỗi với mã lạ: một mã mới của hãng không được làm sập đường nhận. Nó được lưu
    thô, đánh dấu cần soát và KHÔNG đổi trạng thái đơn.
    """
    so, raw, la_customer_cancel, biet_ma = best_hop_dong.chuan_hoa_ma_trang_thai(ma)
    d = BANG_MA.get(so) if biet_ma else None
    if d is None:
        return {"biet_ma": False, "ma": so, "ma_goc": raw, "chung": None, "mo_lai": False,
                "can_soat": True,
                "mo_ta": "mã lạ, chưa có trong danh sách đã xác nhận", "muc": MUC_CHUA_KIEM_CHUNG,
                "nguon": NGUON_GIA_THUYET}
    return {"biet_ma": True, "ma": so, "ma_goc": raw,
            "customer_cancel": bool(la_customer_cancel),
            "chung": d["chung"], "mo_lai": d["mo_lai"],
            "can_soat": d.get("can_soat", False),
            "mo_ta": d["mo_ta"], "muc": d["muc"], "nguon": d["nguon"]}


def quyet_dinh_chuyen(hien_tai, moi, mo_lai=False):
    """Máy trạng thái: `(duoc_ap, ly_do)`. KHÔNG so sánh số mã, KHÔNG dùng thứ hạng.

    `mo_lai=True` chỉ dành cho mã 606 theo đặc tả: nó được phép mở lại chiều giao kể cả khi đơn
    đang ở trạng thái cuối. Đây là lý do tồn tại của máy trạng thái — nếu chỉ so sánh số hoặc
    thứ hạng thì 606 (hạng 3) không bao giờ vượt được `hoan_hang` (hạng 6).
    """
    if moi == "da_huy":
        return 0, "hủy là quyết định nghiệp vụ của Order Service — chỉ ghi nhận, không tự đổi"
    if moi not in TRANG_THAI_CHUNG:
        return 0, f"trạng thái chung lạ: {moi!r}"
    if mo_lai:
        return 1, "mã 606: mở lại chiều giao (đặc tả đã xác nhận)"
    if hien_tai is None:
        return 1, ""
    if hien_tai not in CHUYEN_DUOC:
        return 0, f"trạng thái hiện tại lạ {hien_tai!r} — không đoán bước tiếp theo"
    if hien_tai in TRANG_THAI_HOAN_TAT:
        return 0, (f"đơn đang ở trạng thái cuối {hien_tai!r}; chỉ mã 606 mới được mở lại"
                   " chiều giao")
    if moi not in CHUYEN_DUOC[hien_tai]:
        return 0, f"không có bước hợp lệ {hien_tai!r} → {moi!r}"
    return 1, ""


# ============================================================================
# BƯỚC 1–3: XÁC THỰC · TÀI KHOẢN HÃNG · TENANT
# ============================================================================
def xac_thuc_webhook(tk, headers, body):
    """Xác thực callback theo sơ đồ do HUB chọn cho CHÍNH tài khoản này.

    Trả `(ok, ly_do, ten_so_do, muc)`. Với BEST ở sandbox/production, hub chưa có sơ đồ
    (BLOCKED) nên hàm từ chối — KHÔNG đoán header/chữ ký của hãng.
    """
    mt = str(tk["moi_truong"] if "moi_truong" in tk.keys() else "mock") or "mock"
    if mt != cau_hinh.JT_MOCK:
        # Tài liệu chính thức: webhook dùng JWT Bearer token, không phải HMAC.
        try:
            kq = xac_thuc_best.kiem_bearer_webhook(
                str(tk["tenant_id"]), str(tk["id"]), _headers_thuong(headers).get("authorization"),
                webhook_ma=str(tk["webhook_ma"]) if "webhook_ma" in tk.keys() else None)
        except Exception as e:
            return False, f"lỗi xác thực Bearer: {type(e).__name__} — BLOCKED", "best_bearer", MUC_BLOCKED
        if kq.hop_le:
            return True, "", "best_bearer", MUC_DA_TAI_LIEU
        return False, f"Bearer webhook không hợp lệ ({kq.ma_ly_do}) — BLOCKED", "best_bearer", MUC_BLOCKED
    try:
        ten, ham, muc = hub.chon_so_do(tk)
    except Exception as e:
        return False, f"không chọn được sơ đồ xác thực: {type(e).__name__}", None, MUC_BLOCKED
    if ham is None:
        return (False,
                "chưa có sơ đồ xác thực BEST đã xác minh cho môi trường này — BLOCKED, "
                "không đoán chữ ký", None, MUC_BLOCKED)
    try:
        ok, ly_do = ham(tk, _headers_thuong(headers), bytes(body))
    except Exception as e:
        return False, f"lỗi khi kiểm xác thực: {type(e).__name__}", ten, muc
    return bool(ok), (ly_do or ""), ten, muc


def xac_dinh_tai_khoan_hang(tk):
    """Tài khoản hãng phải tồn tại, đang bật, ĐÚNG là BEST và có môi trường hợp lệ."""
    if tk is None:
        return False, "không có tài khoản hãng"
    try:
        if str(tk["hang"]) != HANG:
            return False, f"tài khoản hãng {tk['hang']!r} không phải BEST"
        if not int(tk["kich_hoat"] or 0):
            return False, "tài khoản hãng đã bị tắt"
        mt = str(tk["moi_truong"] or "")
        if mt not in (cau_hinh.JT_MOCK, cau_hinh.JT_SANDBOX, cau_hinh.JT_PRODUCTION):
            return False, f"môi trường tài khoản lạ: {mt!r}"
    except (KeyError, TypeError, ValueError) as e:
        return False, f"dòng tài khoản hãng không đọc được: {type(e).__name__}"
    return True, ""


def xac_dinh_tenant(tk):
    """Tenant CHỈ đến từ dòng `carrier_accounts` đã tra được trên URL.

    Kiểm thêm tenant có thật và đang hoạt động: một dòng account trỏ tới tenant đã xóa/khóa là
    dữ liệu hỏng, và cập nhật vào đó là cập nhật vào hư không. Không đọc bất kỳ trường tenant
    nào trong payload — payload chỉ được GHI LẠI nếu cố khai (xem `_claim_tenant`).
    """
    tid = tk["tenant_id"] if tk is not None else None
    if tid in (None, ""):
        return None, "tài khoản hãng không gắn tenant — DENY (không xác định tenant)"
    try:
        tid = int(tid)
    except (TypeError, ValueError):
        return None, f"tenant_id không phải số: {tid!r} — DENY"
    r = csdl.mot("SELECT id, trang_thai FROM tenants WHERE id=?", (tid,))
    if r is None:
        return None, f"tenant {tid} không tồn tại — DENY"
    if str(r["trang_thai"]) != "hoat_dong":
        return None, f"tenant {tid} đang ở trạng thái {r['trang_thai']!r} — DENY"
    return tid, ""


def _tenant_cua_tk(tk):
    try:
        return int(tk["tenant_id"])
    except (KeyError, TypeError, ValueError):
        return None


# ============================================================================
# BƯỚC 4–5: MÃ VẬN ĐƠN · MÃ ĐƠN · ĐƠN PHẢI THUỘC ĐÚNG TENANT + ACCOUNT
# ============================================================================
def tim_don(tk, tenant_id, p):
    """Tìm đơn theo tracking code TRONG ĐÚNG tenant + đúng tài khoản hãng.

    Trả `(don, ly_do)`:
      · `don` khác None + `ly_do` rỗng  → cập nhật được;
      · `don` khác None + `ly_do` khác  → tìm thấy nhưng có xung đột (account/mã đơn), KHÔNG áp;
      · `don` None                      → không thấy trong tenant này, KHÔNG áp.
    `merchant_order_code` KHÔNG BAO GIỜ quyết định tenant. Nó chỉ được dùng để đối chiếu sau khi
    đã có tenant từ tài khoản, và để phát hiện trường hợp mã đơn khớp nhưng tracking khác.
    """
    don = csdl.mot(
        "SELECT * FROM don_hang WHERE ma_van_don=? AND tenant_id=? ORDER BY id DESC LIMIT 1",
        (p["code_best"], tenant_id))
    if don is not None:
        try:
            cung_tk = int(don["carrier_account_id"] or 0) == int(tk["id"])
        except (KeyError, TypeError, ValueError):
            cung_tk = False
        if not cung_tk:
            return don, "tracking_thuoc_tai_khoan_khac"
        if str(don["ma_don"]) != p["merchant_order_code"]:
            return don, "merchant_order_lech"
        return don, ""
    # Không thấy theo tracking: thử theo mã đơn TRONG CÙNG TENANT để phát hiện lệch cặp mã.
    # Đây không phải đường cập nhật — nó chỉ để nói đúng lý do không áp.
    don2 = csdl.mot(
        "SELECT * FROM don_hang WHERE ma_don=? AND tenant_id=? ORDER BY id DESC LIMIT 1",
        (p["merchant_order_code"], tenant_id))
    if don2 is not None:
        try:
            cung_tk2 = int(don2["carrier_account_id"] or 0) == int(tk["id"])
        except (KeyError, TypeError, ValueError):
            cung_tk2 = False
        if not cung_tk2:
            return don2, "merchant_thuoc_tai_khoan_khac"
        return don2, "merchant_khop_tracking_khac"
    return None, "khong_co_don"


# ============================================================================
# BƯỚC 6–7: CHỐNG TRÙNG + LƯU THÔ AN TOÀN
# ============================================================================
def _luu_su_kien_tho(tk, tenant_id, event_id, p, headers):
    """Ghi thô BỀN vào `wh_su_kien` của hub. Trả `(sk_id, trung)`.

    Bọc `khoa_ghi` + dựa vào UNIQUE(carrier_account_id, event_id) của hub: hai yêu cầu chồng
    nhau chỉ một dòng. Ghi lỗi ⇒ ném `LoiLuuTru`; người gọi TUYỆT ĐỐI không ACK thành công.
    Mọi câu đọc lại đều JOIN `carrier_accounts` để tenant nằm trong điều kiện, không chỉ trong
    lời cam kết của tầng gọi.
    """
    payload = json.dumps(p["tho_sach"], ensure_ascii=False, sort_keys=True).encode("utf-8")
    headers_json = json.dumps(_headers_an_toan(headers), ensure_ascii=False, sort_keys=True)
    with csdl.khoa_ghi:
        try:
            con = csdl.ghi(
                "INSERT INTO wh_su_kien (carrier_account_id, event_id, payload_tho, headers_json,"
                " nhan_luc) VALUES (?,?,?,?,?)",
                (tk["id"], event_id, payload, headers_json, csdl.bay_gio()))
        except csdl.LoiToanVen:
            cu = csdl.mot(
                "SELECT s.id, s.trang_thai FROM wh_su_kien s JOIN carrier_accounts c"
                " ON c.id=s.carrier_account_id WHERE s.carrier_account_id=? AND c.tenant_id=?"
                " AND s.event_id=?", (tk["id"], tenant_id, event_id))
            if cu is None:
                raise LoiLuuTru("UNIQUE báo trùng nhưng không đọc lại được sự kiện cũ")
            return cu["id"], True
        except csdl.LoiCSDL as e:
            raise LoiLuuTru(f"CSDL từ chối ghi sự kiện thô: {type(e).__name__}: {e}")
        except Exception as e:
            raise LoiLuuTru(f"không ghi được sự kiện thô: {type(e).__name__}: {e}")
    return con.lastrowid, False


def _danh_dau_xong(sk_id):
    csdl.ghi("UPDATE wh_su_kien SET trang_thai='xong', loi_cuoi=NULL, xu_ly_xong_luc=?"
             " WHERE id=?", (csdl.bay_gio(), sk_id))


def _danh_dau_loi(sk_id, e, trang_thai="dlq"):
    try:
        csdl.ghi("UPDATE wh_su_kien SET trang_thai=?, loi_cuoi=? WHERE id=?",
                 (trang_thai, f"{type(e).__name__}: {e}"[:2000], sk_id))
    except Exception:
        pass


# ============================================================================
# BƯỚC 8–10: CHUẨN HOÁ · CẬP NHẬT ĐƠN · LỊCH SỬ
# ============================================================================
def _moc_da_ap(don_id, tenant_id):
    """Mốc `modified_at` LỚN NHẤT đã thật sự ÁP cho đơn này.

    Đọc từ audit do chính đường này ghi (`webhook_best_moc_hang`) — một nguồn duy nhất, không
    suy từ số trạng thái. Sự kiện KHÔNG được áp (đến muộn, mã lạ, trạng thái cuối) không được
    đẩy mốc: nếu đẩy, một sự kiện có thật đến sau nhưng mang mốc cũ hơn sẽ bị chặn oan.
    """
    r = csdl.mot(
        "SELECT MAX(chi_tiet) m FROM audit WHERE hanh_dong='webhook_best_moc_hang'"
        " AND resource_type='don' AND resource_id=? AND tenant_id=?",
        (str(don_id), tenant_id))
    return (r["m"] if r else None) or None


def _ghi_moc(sk_id, don_id, moc, tenant_id):
    """Ghi mốc ĐÃ ÁP. Chỉ gọi bên trong giao dịch của lượt cập nhật thật."""
    if hub.cot_co("wh_su_kien", "hang_moc_thoi_gian"):
        csdl.ghi("UPDATE wh_su_kien SET hang_moc_thoi_gian=? WHERE id=?", (moc, sk_id))
    csdl.audit("webhook_best_moc_hang", f"don:{don_id}", moc, tenant_id=tenant_id)


def _ghi_lich_su(don_id, nguon, noi_dung):
    csdl.ghi("INSERT INTO don_lich_su (don_id, luc, nguon, noi_dung) VALUES (?,?,?,?)",
             (don_id, csdl.bay_gio(), nguon[:200], noi_dung[:4000]))


def _mo_lai_chieu_giao(sk_id, tk, tenant_id, don, p, qd):
    """ĐƯỜNG ĐẶC CÁCH DUY NHẤT của mô-đun: mã 606 mở lại chiều giao.

    `don_hang.ap_trang_thai_giao()` có rank guard `hang_moi > hang_cu`; nó KHÔNG thể hạ đơn từ
    `hoan_hang` (6) hoặc `giao_thanh_cong` (5) xuống `dang_giao` (3). Đó là chốt đúng cho mọi
    sự kiện thường, nhưng 606 là ngoại lệ ĐÃ XÁC NHẬN trong đề bài ("606 mở lại chiều giao").
    Vì vậy — và CHỈ vì vậy — mô-đun tự UPDATE đơn ở đây, trong CÙNG giao dịch với lịch sử + mốc.

    Ca thử `test_f11` canh số câu `UPDATE don_hang` trong tệp đúng bằng 1: mọi đường cập nhật
    khác phải đi qua `don_hang.ap_trang_thai_giao`, không được nới quyền sở hữu của AG-02.
    """
    hang = cau_hinh.HANG_TRANG_THAI_GIAO.get(qd["chung"])
    if hang is None:
        return 0, f"trạng thái chung {qd['chung']!r} không có trong trục giao vận"
    noi_dung = (f"BEST {p['status']} → {qd['chung']} (mở lại chiều giao); status_content="
                f"{(p['status_content'] or '')[:500]!r}; modified_at={p['modified_at_raw']!r}")
    with csdl.giao_dich():
        con = csdl.ghi(
            "UPDATE don_hang SET trang_thai_giao=?, hang_trang_thai_giao=?, cap_nhat_luc=?"
            " WHERE id=? AND tenant_id=? AND carrier_account_id=? AND trang_thai!='huy'",
            (qd["chung"], hang, csdl.bay_gio(), don["id"], tenant_id, tk["id"]))
        if con.rowcount != 1:
            raise RuntimeError(
                f"không mở lại được đơn {don['id']} cho tenant {tenant_id}/account {tk['id']}"
                " — điều kiện tenant/account/trạng thái hủy không khớp")
        _ghi_lich_su(don["id"], f"webhook_best:{sk_id}", noi_dung)
        _ghi_moc(sk_id, don["id"], p["moc"], tenant_id)
    return 1, "mã 606: mở lại chiều giao"


def _cap_nhat_don(sk_id, tk, tenant_id, don, p, qd):
    """Khoá ghi + quyết định + cập nhật là MỘT khối tuần tự.

    Không có khoá này, hai callback chồng nhau cùng đọc mốc cũ, cùng thấy `modified_at` mới hơn
    và cùng áp — đúng khuôn đọc-rồi-ghi mà G17 đã đo được ở cửa replay. `khoa_ghi` là RLock nên
    các lời gọi `csdl.ghi()` bên trong vẫn đi qua được.
    """
    with csdl.khoa_ghi:
        return _cap_nhat_don_trong_khoa(sk_id, tk, tenant_id, don, p, qd)


def _cap_nhat_don_trong_khoa(sk_id, tk, tenant_id, don, p, qd):
    """Mở giao dịch GHI trước khi đọc mốc: đọc-rồi-ghi phải nằm trong CÙNG một giao dịch.

    Nếu chỉ khoá trong tiến trình, một tiến trình khác vẫn có thể ghi giữa lúc đọc mốc và lúc
    áp. `BEGIN IMMEDIATE` của `csdl.giao_dich()` giữ khoá ghi xuyên suốt quyết định; các nhánh
    bên trong dùng SAVEPOINT lồng nhau nên không mở giao dịch thứ hai.
    """
    with csdl.giao_dich():
        return _cap_nhat_don_quyet_dinh(sk_id, tk, tenant_id, don, p, qd)


def _cap_nhat_don_quyet_dinh(sk_id, tk, tenant_id, don, p, qd):
    """Áp trạng thái vào đơn, có máy trạng thái + chống đến muộn. Trả `(ap_dung, ly_do)`.

    Thứ tự quyết định CỐ Ý:
      1. đơn nghiệp vụ đã hủy → không đụng;
      2. mã hủy/lạ/không ánh xạ → không đụng;
      3. `modified_at` so với mốc đã áp → cũ hơn = đến muộn, bằng = trùng mốc/xung đột;
      4. máy trạng thái → bước hợp lệ;
      5. 606 đi đường đặc cách; mọi bước khác đi `don_hang.ap_trang_thai_giao()`.
    KHÔNG dùng thứ hạng trạng thái để quyết định đến muộn; `hang_trang_thai_giao` chỉ là cột
    dẫn xuất để tương thích hub, không phải nguồn quyết định.
    """
    # Đọc LẠI trong giao dịch: `tim_don` đọc ngoài giao dịch, nên đơn có thể bị hủy giữa hai
    # bước. Quyết định trên bản đọc cũ là khe đọc-rồi-ghi; đọc lại dưới khoá ghi đóng khe đó.
    don_moi = csdl.mot(
        "SELECT * FROM don_hang WHERE id=? AND tenant_id=? AND carrier_account_id=?",
        (don["id"], tenant_id, tk["id"]))
    if don_moi is None:
        return 0, "đơn không còn khớp tenant/account tại thời điểm cập nhật — không đổi"
    don = don_moi
    if str(don["trang_thai"]) == "huy":
        return 0, "đơn đã hủy ở trạng thái nghiệp vụ — webhook không tự mở lại"
    if qd["chung"] == "da_huy":
        return 0, "hủy là quyết định nghiệp vụ — chỉ ghi nhận, không tự đổi"
    if qd["chung"] is None:
        return 0, "mã lạ chưa có nghĩa đã xác minh — chỉ ghi nhận, không đổi trạng thái"

    hien_tai = don["trang_thai_giao"] or None
    if hien_tai is not None and str(hien_tai) not in TRANG_THAI_CHUNG:
        return 0, f"trạng thái giao hiện tại lạ {hien_tai!r} — không đoán"

    moc = p["moc"]
    wm = _moc_da_ap(don["id"], tenant_id)
    if wm and moc < wm:
        return 0, f"đến muộn: modified_at {moc} < mốc đã áp {wm}"
    if wm and moc == wm:
        if qd["chung"] == hien_tai:
            return 0, f"trùng mốc đã áp {wm} và cùng trạng thái — không áp lại"
        return 0, (f"xung đột mốc {wm}: cùng modified_at nhưng trạng thái khác"
                   f" ({hien_tai!r} → {qd['chung']!r}) — cần soát, không đoán")

    duoc, ly_do = quyet_dinh_chuyen(hien_tai, qd["chung"], qd["mo_lai"])
    if not duoc:
        return 0, ly_do

    if qd["mo_lai"]:
        return _mo_lai_chieu_giao(sk_id, tk, tenant_id, don, p, qd)

    # Cùng trạng thái nhưng `modified_at` MỚI HƠN: đây là một lần quét lặp hợp lệ. Không có
    # trạng thái nào để đổi, nhưng PHẢI đẩy mốc — nếu không, một sự kiện CŨ hơn (nhưng mới hơn
    # mốc cũ) đến sau sẽ lọt qua và ghi đè một quan sát đã biết là mới hơn.
    if qd["chung"] == hien_tai:
        with csdl.giao_dich():
            _ghi_moc(sk_id, don["id"], moc, tenant_id)
        return 1, "quét lặp cùng trạng thái — chỉ đẩy mốc, không đổi trạng thái"

    # Mọi bước thường đi qua Order Service — không tự UPDATE bảng don_hang. Rank guard của
    # `ap_trang_thai_giao` không mâu thuẫn với máy trạng thái ở trên vì mọi cạnh thường đều
    # không giảm hạng; cạnh giảm hạng duy nhất (mở lại) đã đi đường 606 ở trên.
    # Giao dịch NGOÀI gộp câu cập nhật đơn + lịch sử (Order Service) với mốc đã áp: đơn đổi mà
    # mốc không đổi là đúng khe hở để một webhook cũ ghi đè lần sau.
    with csdl.giao_dich():
        ap_dung, ly_do = don_hang.ap_trang_thai_giao(
            tenant_id, don["id"], qd["chung"], f"webhook_best:{sk_id}")
        if ap_dung:
            _ghi_moc(sk_id, don["id"], moc, tenant_id)
    return ap_dung, ly_do


def _ghi_dau_vet(sk_id, p, qd, don_id, ap_dung):
    """Ghi cột dấu vết của hub NẾU schema đã migrate; payload_tho vẫn là nguồn đầy đủ.

    Không ghi `hang_moc_thoi_gian` ở đây — mốc chỉ do `_ghi_moc()` ghi khi ĐÃ ÁP, đúng bài học
    G14: sự kiện không được áp không được đẩy watermark.
    """
    try:
        dat, ts = [], []
        for cot, gt in (
            ("hang_ma_goc", str(p.get("status_raw", p["status"]))),
            ("hang_mo_ta_goc", p["status_content"]),
            ("hang_su_kien_goc", json.dumps({"status": p.get("status_raw", p["status"]),
                                             "status_content": p["status_content"],
                                             "modified_at": p["modified_at_raw"]},
                                            ensure_ascii=False)),
            ("anh_xa_do_tin_cay", MUC_CHUA_KIEM_CHUNG),
            ("anh_xa_nguon", f"{NGUON_DE_BAI} / {MUC_CHUA_KIEM_CHUNG}"),
            ("can_soat", 0 if ap_dung else 1),
            ("trang_thai_chuan", qd["chung"] if ap_dung else None),
            ("don_id", don_id),
        ):
            if hub.cot_co("wh_su_kien", cot):
                dat.append(f"{cot}=?")
                ts.append(gt)
        if dat:
            ts.append(sk_id)
            csdl.ghi(f"UPDATE wh_su_kien SET {', '.join(dat)} WHERE id=?", ts)
    except Exception as e:
        # Cột dấu vết là phụ; payload_tho + audit vẫn đủ. Không để lỗi cột làm mất ACK đã bền.
        try:
            csdl.audit("webhook_best_loi_dau_vet", f"su_kien:{sk_id}",
                       f"{type(e).__name__}: {e}"[:1000], tenant_id=None, ket_qua="that_bai")
        except Exception:
            pass


# ============================================================================
# AUDIT — KHÔNG BAO GIỜ GHI TOKEN/SECRET/CHỮ KÝ
# ============================================================================
def _audit(hanh_dong, tk, tenant_id, sk_id, p, qd, ket_cuc, ly_do="", ap_dung=0,
           so_do=None, muc_xac_thuc=None, them=None, ket_qua="thanh_cong"):
    """Ghi một dòng audit đủ để điều tra, KHÔNG đủ để phát lại hay lộ secret.

    Cố ý không đưa `payload_tho`, `headers`, `status_content` hay chữ ký vào đây: audit là nơi
    nhiều người đọc nhất, nên nó chỉ nhận mã, mốc, quyết định.
    """
    chi_tiet = {
        "phien_ban": PHIEN_BAN,
        "muc_tai_lieu": MUC_CHUA_KIEM_CHUNG,
        "su_kien_id": sk_id,
        "event_id": None,
        "code_best": None,
        "merchant_order_code": None,
        "status": None,
        "modified_at": None,
        "moc": None,
        "trang_thai_chung": None,
        "biet_ma": None,
        "mo_lai": None,
        "ket_cuc": ket_cuc,
        "ly_do": (ly_do or "")[:1000],
        "ap_dung": bool(ap_dung),
        "so_do_xac_thuc": so_do,
        "muc_xac_thuc": muc_xac_thuc,
        "tai_khoan_hang": (tk["id"] if tk is not None and "id" in tk.keys() else None),
    }
    if p is not None:
        chi_tiet.update({
            "event_id": _khoa_su_kien(p),
            "code_best": p["code_best"],
            "merchant_order_code": p["merchant_order_code"],
            "status": p["status"],
            "modified_at": p["modified_at_raw"],
            "moc": p["moc"],
        })
    if qd is not None:
        chi_tiet.update({"trang_thai_chung": qd["chung"], "biet_ma": qd["biet_ma"],
                         "mo_lai": qd["mo_lai"]})
    if them:
        chi_tiet.update(them)
    doi_tuong = (f"su_kien:{sk_id}" if sk_id is not None
                 else (f"carrier_account:{tk['id']}" if tk is not None and "id" in tk.keys()
                       else "webhook:best"))
    try:
        csdl.audit(hanh_dong, doi_tuong,
                   json.dumps(lam_sach(chi_tiet), ensure_ascii=False, sort_keys=True, default=str),
                   tenant_id=tenant_id, ket_qua=ket_qua)
        return True
    except Exception:
        return False


# ============================================================================
# ĐƯỜNG VÀO CÔNG KHAI
# ============================================================================
def xu_ly_voi_account(tk, body, headers=None):
    """Xử lý một callback BEST khi ĐÃ có dòng `carrier_accounts` (tầng HTTP tra theo URL).

    Tầng gọi KHÔNG được truyền tenant từ payload hay từ tham số rời: tenant được đọc lại từ
    chính dòng account trong bước 3.
    """
    buoc = []
    hd = _headers_thuong(headers)
    p = None
    qd = None
    sk_id = None
    tenant_id = _tenant_cua_tk(tk)

    def dung(http, ly_do, ket_cuc, hanh_dong="webhook_best_tu_choi", ket_qua="tu_choi",
             them=None):
        _audit(hanh_dong, tk, tenant_id, sk_id, p, qd, ket_cuc, ly_do=ly_do, them=them,
               ket_qua=ket_qua)
        buoc.append("ghi_audit")
        return KetQua(http, that_bai(ly_do), su_kien_id=sk_id, buoc=buoc, ket_cuc=ket_cuc,
                      event_id=(_khoa_su_kien(p) if p else None),
                      don_id=(them or {}).get("don_id") if them else None,
                      chi_tiet={"ly_do": ly_do})

    # ---- 1. xác thực webhook ----
    buoc.append("xac_thuc_webhook")
    ok, ly_do, so_do, muc = xac_thuc_webhook(tk, hd, body)
    if not ok:
        return dung(401, f"xác thực webhook thất bại: {ly_do}", "tu_choi_chu_ky",
                    them={"so_do": so_do, "muc": muc})

    # ---- 2. tài khoản hãng ----
    buoc.append("xac_dinh_tai_khoan_hang")
    ok, ly_do = xac_dinh_tai_khoan_hang(tk)
    if not ok:
        return dung(403, ly_do, "tai_khoan_khong_hop_le", them={"so_do": so_do, "muc": muc})

    # ---- 3. tenant (CHỈ từ carrier_accounts) ----
    buoc.append("xac_dinh_tenant")
    tenant_id, ly_do = xac_dinh_tenant(tk)
    if tenant_id is None:
        return dung(403, ly_do, "thieu_tenant", them={"so_do": so_do, "muc": muc})

    # ---- 4. mã vận đơn + payload ----
    buoc.append("kiem_tracking_code")
    try:
        p = doc_payload(body)
    except LoiDuLieu as e:
        return dung(e.http, e.ly_do, "du_lieu_sai", them={"so_do": so_do, "muc": muc})

    # Payload cố khai tenant → GHI LẠI rồi BỎ QUA. Không dùng để xác định tenant.
    if p["claim_tenant"] is not None and str(p["claim_tenant"]) != str(tenant_id):
        _audit("webhook_best_claim_tenant_bi_bo_qua", tk, tenant_id, None, p, None,
               "claim_tenant_bi_bo_qua",
               ly_do=(f"payload khai tenant={p['claim_tenant']!r}, account thuộc tenant"
                      f"={tenant_id} — dùng tenant của account"),
               ket_qua="tu_choi")

    # ---- 5. mã đơn + đối chiếu đơn trong ĐÚNG tenant/account ----
    buoc.append("kiem_merchant_order_code")
    don, ly_do_don = tim_don(tk, tenant_id, p)
    if ly_do_don == "tracking_thuoc_tai_khoan_khac":
        return dung(409, "mã vận đơn thuộc tài khoản hãng khác trong cùng tenant — DENY",
                    "tai_khoan_khong_khop",
                    them={"so_do": so_do, "muc": muc,
                          "don_id": (don["id"] if don is not None else None)})

    # ---- 6. chống trùng sự kiện ----
    buoc.append("kiem_trung_su_kien")
    event_id = _khoa_su_kien(p)
    cu = csdl.mot(
        "SELECT s.id, s.trang_thai FROM wh_su_kien s JOIN carrier_accounts c"
        " ON c.id=s.carrier_account_id WHERE s.carrier_account_id=? AND c.tenant_id=?"
        " AND s.event_id=?", (tk["id"], tenant_id, event_id))
    if cu is not None and str(cu["trang_thai"]) == "xong":
        _audit("webhook_best_trung", tk, tenant_id, cu["id"], p, None, "trung_su_kien",
               ly_do="sự kiện đã được tiếp nhận bền vững trước đó — ACK idempotent",
               them={"so_do": so_do, "muc": muc,
                     "don_id": (don["id"] if don is not None else None)})
        buoc.append("ghi_audit")
        return KetQua(200, thanh_cong(), su_kien_id=cu["id"], trung=True, buoc=buoc,
                      ket_cuc="trung_su_kien", event_id=event_id,
                      don_id=(don["id"] if don is not None else None),
                      chi_tiet={"trung": True})

    # ---- 7. lưu thô an toàn (ACK chỉ sau bước này) ----
    buoc.append("luu_raw_event_an_toan")
    try:
        if cu is not None:
            # Dòng cũ chưa xong (lượt trước lỗi giữa đường): dùng lại, KHÔNG ghi trùng.
            sk_id = cu["id"]
        else:
            sk_id, trung = _luu_su_kien_tho(tk, tenant_id, event_id, p, hd)
            if trung:
                _audit("webhook_best_trung", tk, tenant_id, sk_id, p, None, "trung_su_kien",
                       ly_do="UNIQUE(carrier_account_id,event_id) bắt được lượt chồng nhau",
                       them={"so_do": so_do, "muc": muc})
                buoc.append("ghi_audit")
                return KetQua(200, thanh_cong(), su_kien_id=sk_id, trung=True, buoc=buoc,
                              ket_cuc="trung_su_kien", event_id=event_id,
                              don_id=(don["id"] if don is not None else None))
    except LoiLuuTru as e:
        _audit("webhook_best_loi_luu", tk, tenant_id, None, p, None, "loi_luu",
               ly_do=str(e), ket_qua="that_bai",
               them={"so_do": so_do, "muc": muc})
        buoc.append("ghi_audit")
        # KHÔNG ACK thành công: chưa có gì bền vững để hãng khỏi gửi lại.
        return KetQua(500, that_bai(f"không lưu được sự kiện: {e}"), su_kien_id=None,
                      buoc=buoc, ket_cuc="loi_luu", event_id=event_id)

    try:
        # ---- 8. chuẩn hoá ----
        buoc.append("chuan_hoa_trang_thai")
        qd = chuan_hoa_trang_thai(p["status"])

        # ---- 9. cập nhật đơn ----
        buoc.append("cap_nhat_don")
        ap_dung, ly_do_ap = 0, ly_do_don or ""
        if don is None:
            ly_do_ap = "không có đơn khớp trong tenant/account — đã lưu thô, không cập nhật"
        elif ly_do_don:
            ly_do_ap = f"{ly_do_don} — đã lưu thô, không cập nhật"
        else:
            ap_dung, ly_do_ap = _cap_nhat_don(sk_id, tk, tenant_id, don, p, qd)

        # ---- 10. lịch sử trạng thái ----
        # Bước thường: Order Service ghi lịch sử trong giao dịch của `ap_trang_thai_giao`.
        # Riêng 606: `_mo_lai_chieu_giao` ghi lịch sử trong cùng giao dịch với câu UPDATE.
        # Khi không áp thì KHÔNG bịa dòng lịch sử.
        buoc.append("ghi_lich_su_trang_thai")

        _ghi_dau_vet(sk_id, p, qd, (don["id"] if don is not None else None), ap_dung)
        _danh_dau_xong(sk_id)

        # ---- 11. audit ----
        buoc.append("ghi_audit")
        hanh_dong = "webhook_best_cap_nhat_don" if ap_dung else "webhook_best_bo_qua"
        audit_ok = _audit(
            hanh_dong, tk, tenant_id, sk_id, p, qd,
            ("cap_nhat" if ap_dung else "ghi_nhan"),
            ly_do=ly_do_ap, ap_dung=ap_dung,
            so_do=so_do, muc_xac_thuc=muc,
            them={"so_do": so_do, "muc": muc,
                  "don_id": (don["id"] if don is not None else None),
                  "trang_thai_giao_truoc": (don["trang_thai_giao"] if don is not None else None)},
            ket_qua="thanh_cong")
        if not audit_ok:
            # Sự kiện đã bền nhưng bước 11 hỏng: KHÔNG nói "đã xong". Đánh dấu để lần gửi lại
            # đi tiếp, và trả lỗi để hãng còn gửi lại (thay vì mất dấu audit vĩnh viễn).
            e = RuntimeError("không ghi được audit")
            _danh_dau_loi(sk_id, e, trang_thai="cho_thu_lai")
            return KetQua(500, that_bai("không ghi được audit — sự kiện đã lưu, chưa xác nhận"),
                          su_kien_id=sk_id, buoc=buoc, ket_cuc="loi_audit", event_id=event_id,
                          don_id=(don["id"] if don is not None else None))

        return KetQua(200, thanh_cong(), su_kien_id=sk_id, buoc=buoc,
                      ket_cuc=("cap_nhat" if ap_dung else "ghi_nhan"), event_id=event_id,
                      don_id=(don["id"] if don is not None else None),
                      chi_tiet={"ap_dung": bool(ap_dung), "ly_do": ly_do_ap,
                                "chung": qd["chung"], "mo_lai": qd["mo_lai"]})
    except Exception as e:
        # Từ bước 8 trở đi sự kiện ĐÃ bền. Không ACK "xong" khi chưa xử lý xong, nhưng cũng
        # không nói dối là chưa nhận: đánh dấu DLQ + audit lỗi, trả 500 để hãng gửi lại.
        _danh_dau_loi(sk_id, e, trang_thai="dlq")
        _audit("webhook_best_loi", tk, tenant_id, sk_id, p, qd, "loi_xu_ly",
               ly_do=f"{type(e).__name__}: {e}", ket_qua="that_bai",
               them={"so_do": so_do, "muc": muc})
        if "ghi_audit" not in buoc:
            buoc.append("ghi_audit")
        return KetQua(500, that_bai("sự kiện đã lưu nhưng xử lý lỗi — chưa xác nhận xong"),
                      su_kien_id=sk_id, buoc=buoc, ket_cuc="loi_xu_ly", event_id=event_id,
                      don_id=(don["id"] if don is not None else None))


def xu_ly_theo_dinh_danh(webhook_ma, headers, body):
    """Đường vào cho tầng HTTP cắm vào route hiện có: tra account theo định danh URL.

    Định danh endpoint (`carrier_accounts.webhook_ma`) là thứ DUY NHẤT ánh xạ tenant trước khi
    xử lý. Không nhận tenant từ query string hay payload.
    """
    tk = hub.tim_account_theo_webhook_ma(webhook_ma)
    if tk is None:
        try:
            csdl.audit("webhook_best_khong_ton_tai", f"webhook:{str(webhook_ma)[:64]}",
                       "không có tài khoản hãng BEST đang bật với định danh này",
                       ket_qua="tu_choi")
        except Exception:
            pass
        return KetQua(404, that_bai("webhook không tồn tại"), ket_cuc="khong_ton_tai")
    return xu_ly_voi_account(tk, body, headers)


# ============================================================================
# TỰ KIỂM BẤT BIẾN — chạy được không cần CSDL
# ============================================================================
def kiem_bat_bien():
    """Trả danh sách lỗi cấu trúc. Rỗng = các chốt dưới đây còn đúng.

    Đây là thứ bộ thử gọi để bắt lỗi "sửa bảng mã rồi quên máy trạng thái" — không phải để
    tuyên bố đúng nghiệp vụ (nghiệp vụ còn CHUA_KIEM_CHUNG).
    """
    loi = []
    if tuple(TEN_BUOC) != (
            "xac_thuc_webhook", "xac_dinh_tai_khoan_hang", "xac_dinh_tenant",
            "kiem_tracking_code", "kiem_merchant_order_code", "kiem_trung_su_kien",
            "luu_raw_event_an_toan", "chuan_hoa_trang_thai", "cap_nhat_don",
            "ghi_lich_su_trang_thai", "ghi_audit"):
        loi.append("TEN_BUOC không còn đủ/đúng 11 bước")
    if len(set(TEN_BUOC)) != 11:
        loi.append("TEN_BUOC có tên trùng")
    if len(BANG_MA) != SO_MA_LIET_KE:
        loi.append(f"BANG_MA có {len(BANG_MA)} mã, không khớp {SO_MA_LIET_KE}")
    if set(BANG_MA) != set(MA_TRONG_DE_BAI):
        thieu = sorted(set(MA_TRONG_DE_BAI) - set(BANG_MA))
        thua = sorted(set(BANG_MA) - set(MA_TRONG_DE_BAI))
        loi.append(f"BANG_MA lệch danh sách đề bài: thiếu={thieu} thừa={thua}")
    for ma, d in BANG_MA.items():
        if d["muc"] != MUC_DA_TAI_LIEU:
            loi.append(f"mã {ma}: bị nâng mức bằng chứng lên {d['muc']}")
        if d["chung"] not in TRANG_THAI_CHUNG:
            loi.append(f"mã {ma}: trạng thái chung lạ {d['chung']!r}")
    if not BANG_MA[606]["mo_lai"]:
        loi.append("606 phải có cờ mở lại chiều giao")
    # KHÔNG canh nghĩa của 605: đó là giả thuyết CHUA_KIEM_CHUNG, không phải bất biến. Chỉ canh
    # rằng cặp 605→606 có đủ hai đầu và 606 là mã duy nhất được mở lại.
    if len([d for d in BANG_MA.values() if d["mo_lai"]]) != 1:
        loi.append("chỉ mã 606 được mang cờ mở lại")
    if thanh_cong() != {"Result": 1, "Message": ""}:
        loi.append("thân ACK không đúng đặc tả")
    return loi


def bang_ma_van_ban():
    """Bảng 23 dòng để in bằng chứng — dữ liệu lấy từ chính `BANG_MA`, không chép tay."""
    return [(d["ma"], d["mo_ta"], d["chung"], d["mo_lai"], d["muc"])
            for d in BANG_MA.values()]
