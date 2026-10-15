# G06 — Central Webhook Gateway tenant-aware (kế thừa thiết kế G01 đã nghiệm thu):
# VERIFY → PERSIST RAW → QUEUE → NORMALIZE → RESOLVE TENANT+ORDER → GUARD → UPDATE → AUDIT.
# Tenant resolve từ carrier_account (định danh trên URL + chữ ký bằng secret của CHÍNH account đó)
# — không bao giờ từ nội dung payload. Chống trùng bằng UNIQUE(account_id, event_id) trong CSDL.
#
# Bổ sung đợt G06 (AG-03):
#   W02/W03 — mỗi hãng một SƠ ĐỒ XÁC THỰC riêng, chọn ở PHÍA MÁY CHỦ theo (hãng, môi trường);
#             người gửi KHÔNG được chọn sơ đồ. Mức xác thực khai rõ: DOCUMENTED / MOCK VERIFIED /
#             SANDBOX VERIFIED / LIVE VERIFIED / BLOCKED.
#   W05     — chặn sự kiện đến muộn bằng MỐC THỜI GIAN CỦA HÃNG (J&T: scanTime), không chỉ bằng
#             thứ hạng trạng thái và không bằng lúc máy chủ nhận.
#   W06     — mã nhập nhằng (J&T 110) đi qua trang_thai_hang.quyet_dinh(): không tự chọn nghĩa,
#             không bao giờ rơi vào trạng thái hoàn tất, đánh dấu AMBIGUOUS/NEEDS_REVIEW.
#   W04/W07 — nhận việc NGUYÊN TỬ (nhiều worker an toàn), retry có trần + backoff có trần, DLQ,
#             replay có phép + có TRẦN SỐ LẦN + audit.
#
# Bổ sung đợt G14 (AG-03):
#   W02 — HỢP ĐỒNG CALLBACK của J&T khai thành BẢNG MÁY ĐỌC ĐƯỢC (`HOP_DONG_CALLBACK`), mỗi
#         trường ghi rõ TÀI LIỆU NÓI GÌ / CHƯA NÓI GÌ. Trường nào tài liệu trong repo chưa trả
#         lời được thì để `CHUA_TAI_LIEU` — KHÔNG suy diễn rồi ghi thành dữ kiện.
#   W03 — `tenant_tu_account()`: tenant chỉ có MỘT nguồn hợp lệ, gọi tên ra để soi được.
#   W04 — mã nhập nhằng KHÔNG được rò ra ngoài chính nó: xem `watermark()` (đã vá G14).
#   W05 — `doi_chieu_hanh_trinh()`: đối chiếu sự kiện ↔ đơn, gồm phép kiểm CHÉO TENANT.
#
# Bổ sung đợt G16 (AG-04):
#   A13 — HỢP ĐỒNG CALLBACK chốt thành dữ liệu MÁY ĐỌC ĐƯỢC, phần biết được và phần BLOCKED:
#         `CHAN_HOP_DONG_CALLBACK` (mười chỗ hở, mỗi chỗ nói CHÍNH XÁC cái còn thiếu + câu hỏi
#         gửi hãng + đường mã đang bị chặn), `HOP_DONG_MUC` / `HOP_DONG_XAC_MINH_VOI_HANG` /
#         `PHAN_HOI_XAC_MINH` (mức THẬT), `bao_cao_hop_dong_callback()` và
#         `kiem_hop_dong_khong_tu_nang_muc()` (canh bất biến trung thực).
#         KHÔNG đổi thuật toán ký và KHÔNG nâng mức nào: mức cao nhất vẫn là DOCUMENTED.
import base64
import hashlib
import hmac
import json
import queue
import re
import threading
import urllib.parse

import bao_mat
import cau_hinh
import csdl
import don_hang
import trang_thai_hang as tth

_hang_doi = queue.Queue()
_worker = None
_dung = threading.Event()
_cho_trong = threading.Condition()
_dang_xu_ly = 0

# Trần cho backoff: 2**n không có trần thì tới lượt thử thứ 20 nó hẹn lại sau 6 ngày — việc coi
# như mất mà không ai thấy lỗi nào (§12.2 hỏng im lặng).
BACKOFF_TRAN_GIAY = float(cau_hinh.WEBHOOK_BACKOFF_GOC) * 64
# Trần số lần replay THỦ CÔNG cho một sự kiện. Replay là cửa người bấm, nhưng bấm 500 lần vào một
# "poison message" thì vẫn là vòng lặp vô hạn, chỉ chậm hơn.
REPLAY_TOI_DA = 5
# Lệch giờ tối đa cho phép ở header timestamp của hãng (chống phát lại bản ghi cũ).
LECH_GIO_TOI_DA_MS = 15 * 60 * 1000


class LoiVinhVien(Exception):
    pass


# ============================================================================
# W02/W03 — XÁC THỰC THEO TỪNG HÃNG
# ============================================================================
# Mức xác thực — nói đúng thứ ĐÃ ĐO được, không nói quá (§12.1).
MUC_DOCUMENTED = "DOCUMENTED"          # viết theo tài liệu hãng, chưa đối chiếu với hãng thật
MUC_MOCK = "MOCK VERIFIED"             # đã chạy đạt với bộ mô phỏng của chính dự án
MUC_SANDBOX = "SANDBOX VERIFIED"       # đã chạy đạt với sandbox của hãng
MUC_LIVE = "LIVE VERIFIED"             # đã chạy đạt với môi trường thật
MUC_BLOCKED = "BLOCKED"                # chưa có tài liệu/credentials → không nhận callback
MUC_HOP_LE = (MUC_DOCUMENTED, MUC_MOCK, MUC_SANDBOX, MUC_LIVE, MUC_BLOCKED)


def _secret_webhook(tk_row):
    return bao_mat.giai_ma_wh(tk_row["webhook_secret_ma_hoa"], tk_row["webhook_ma"])


def xac_thuc_hub_hmac(tk_row, headers, body: bytes):
    """Sơ đồ của CHÍNH hub (dùng cho môi trường mock, và cho hãng nào cho phép tự đặt secret):
    HMAC-SHA256 toàn bộ thân yêu cầu bằng webhook_secret của account, header X-Webhook-Signature."""
    nhan = headers.get("x-webhook-signature", "")
    if not nhan:
        return False, "thiếu header x-webhook-signature"
    dung = hmac.new(_secret_webhook(tk_row).encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(nhan, dung):
        return False, "chữ ký HMAC không khớp"
    return True, ""


def xac_thuc_jt_digest(tk_row, headers, body: bytes):
    """Sơ đồ callback của J&T theo TÀI LIỆU (open.jtexpress.vn/apiDoc/logistics/statusFeedback,
    đọc 14/10/2026): ba header `apiAccount` · `digest` · `timestamp`, thân form có `bizContent`,
    và `digest = base64( md5-BYTES( bizContent + privateKey ) )`.

    KHÔNG phát minh gì: công thức này là công thức của chính tài liệu, trang callback dùng lại
    cùng bộ header. Khóa ký lấy từ `webhook_secret` của account — chỗ tenant lưu khóa mà hãng
    cấp cho chiều callback.
    CẦN XÁC MINH khi có tài khoản thật: hãng ký riêng `bizContent` hay ký cả thân form, và khóa
    callback có đúng là privateKey của tài khoản hay một khóa riêng. ⇒ mức DOCUMENTED, không hơn.
    """
    digest = headers.get("digest", "")
    if not digest:
        return False, "thiếu header digest"
    biz = _bizcontent_tu_than(body)
    if biz is None:
        return False, "thân yêu cầu không có trường bizContent"
    khoa = _secret_webhook(tk_row)
    dung = base64.b64encode(hashlib.md5((biz + khoa).encode("utf-8")).digest()).decode()
    if not hmac.compare_digest(digest, dung):
        return False, "digest J&T không khớp"
    # apiAccount phải khớp credentials đã lưu của CHÍNH account này (khi account có lưu).
    api_account = str(headers.get("apiaccount", "") or "")
    try:
        cred = bao_mat.giai_ma_cred(tk_row["credentials_ma_hoa"], tk_row["tenant_id"], tk_row["hang"])
    except Exception:
        cred = {}   # không giải mã được credentials thì bỏ qua phép kiểm PHỤ này, chữ ký vẫn đã đúng
    cho_doi = str(cred.get("apiAccount", "") or "")
    if cho_doi and api_account and api_account != cho_doi:
        return False, "apiAccount không thuộc tài khoản hãng này"
    # Chống phát lại: timestamp lệch quá xa thì từ chối. Thiếu timestamp cũng từ chối — tài liệu
    # khai nó là header BẮT BUỘC.
    ts = str(headers.get("timestamp", "") or "")
    if not ts.isdigit():
        return False, "thiếu header timestamp (hoặc không phải số mili giây)"
    if abs(_bay_gio_ms() - int(ts)) > LECH_GIO_TOI_DA_MS:
        return False, "timestamp lệch quá xa — nghi phát lại bản ghi cũ"
    return True, ""


def _bay_gio_ms():
    import datetime as _dt
    return int(_dt.datetime.now(_dt.timezone.utc).timestamp() * 1000)


def _bizcontent_tu_than(body: bytes):
    """Lấy chuỗi bizContent từ thân form (hoặc từ JSON có trường bizContent)."""
    try:
        van_ban = body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return None
    try:
        d = json.loads(van_ban)
        if isinstance(d, dict) and isinstance(d.get("bizContent"), str):
            return d["bizContent"]
    except ValueError:
        pass
    truong = urllib.parse.parse_qs(van_ban, keep_blank_values=True)
    gt = truong.get("bizContent")
    return gt[0] if gt else None


# Sơ đồ xác thực: tên → (hàm, mức). Mức là thứ ĐÃ ĐO, không phải thứ mong muốn.
BO_XAC_THUC = {
    "hub_hmac": (xac_thuc_hub_hmac, MUC_MOCK),
    "jt_digest": (xac_thuc_jt_digest, MUC_DOCUMENTED),
}
# Sơ đồ của từng hãng cho môi trường KHÁC mock. None = BLOCKED (chưa có tài liệu callback).
SO_DO_THEO_HANG = {
    "jt": "jt_digest",
    # ĐÍNH CHÍNH 15/10 (AG-03): câu cũ "chưa có tài liệu Partner API" NÓI SAI — tài
    # liệu đã đọc được. Lý do thật để `None`: **Viettel Post KHÔNG KÝ webhook**. Cơ chế
    # chính thức là so sánh hằng thời gian trường `TOKEN` TRONG THÂN với một bí mật
    # chung — khác hẳn sơ đồ ký của J&T, nên cần một sơ đồ riêng chứ không phải chờ
    # tài liệu. Lưu ý khi làm: bí mật đi qua THÂN nên nó lộ trong log của mọi lớp
    # trung gian, không như chữ ký ở header.
    "vtp": None,
}


def chon_so_do(tk_row):
    """Chọn sơ đồ xác thực ở PHÍA MÁY CHỦ theo (hãng, môi trường). Trả (ten, ham, muc).

    Người gửi không có cách nào chọn sơ đồ. Nếu để header/payload chọn thì kẻ tấn công sẽ chọn
    sơ đồ yếu nhất — đúng dạng danh sách trắng bị lách ở §12.2.
    """
    hang = tk_row["hang"]
    khoa = tk_row.keys() if hasattr(tk_row, "keys") else ()
    moi_truong = (tk_row["moi_truong"] if "moi_truong" in khoa else "mock") or "mock"
    if moi_truong == "mock":
        # Callback mock do CHÍNH hub sinh ra → sơ đồ của hub. Đây là sự thật về nguồn gửi,
        # không phải sự nhượng bộ an toàn.
        ham, muc = BO_XAC_THUC["hub_hmac"]
        return "hub_hmac", ham, muc
    ten = SO_DO_THEO_HANG.get(hang)
    if ten is None:
        return None, None, MUC_BLOCKED
    ham, muc = BO_XAC_THUC[ten]
    return ten, ham, muc


def bang_muc_xac_thuc():
    """Bảng mức xác thực từng hãng × môi trường — để báo cáo và để bộ thử đối chiếu."""
    return {hang: {"mock": {"so_do": "hub_hmac", "muc": MUC_MOCK},
                   "sandbox_production": {
                       "so_do": ten,
                       "muc": BO_XAC_THUC[ten][1] if ten else MUC_BLOCKED}}
            for hang, ten in SO_DO_THEO_HANG.items()}


# ============================================================================
# W02 (G14) — HỢP ĐỒNG CALLBACK J&T, KHAI THÀNH BẢNG MÁY ĐỌC ĐƯỢC
# ============================================================================
# Nguồn: trích lục trong repo — `docs/JT_CAU_HOI_CHINH_THUC.md` (câu 2, 3, 5) và
# `docs/G12_JT_DANG_KY.md` mục 5. Cả hai đều chép từ trang
# `open.jtexpress.vn/apiDoc/logistics/statusFeedback` đọc bằng trình duyệt 14–15/10/2026.
# Trang đó là SPA nên `fetch` tĩnh trả về vỏ rỗng — trích lục trong repo LÀ nguồn sự thật.
#
# Ba mức cho mỗi trường:
#   DA_TAI_LIEU   — trích lục nói rõ
#   SUY_RA        — trích lục không nói thẳng, nhưng hệ quả là duy nhất (ghi rõ vì sao)
#   CHUA_TAI_LIEU — trích lục KHÔNG trả lời được. Đây là BLOCKED, không phải chỗ để đoán.
DA_TAI_LIEU = "DA_TAI_LIEU"
SUY_RA = "SUY_RA"
CHUA_TAI_LIEU = "CHUA_TAI_LIEU"

HOP_DONG_CALLBACK = {
    "phuong_thuc_http": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Trích lục chỉ tả THÂN và HEADER, không nói phương thức. Không suy ra POST"
                   " từ chỗ khác rồi ghi thành dữ kiện. Câu hỏi 7 (chuỗi ký) và câu 9 (thử lại)"
                   " là chỗ hỏi kèm.",
    },
    "dinh_danh_url_phia_nhan": {
        "muc": SUY_RA,
        "gia_tri": "/api/v2/webhook/nhan/<webhook_ma>",
        "ghi_chu": "Đây là đường CỦA HUB (server.py), không phải của J&T. J&T gọi vào URL mình"
                   " khai; URL công khai CHƯA ĐƯỢC CẤP (V-G11-01) nên chưa đăng ký được.",
    },
    "than_yeu_cau": {
        "muc": DA_TAI_LIEU,
        "gia_tri": "form (application/x-www-form-urlencoded) với trường `bizContent`",
        "ghi_chu": "Trích lục câu 2: 'thân yêu cầu là form có trường bizContent'.",
    },
    "header_bat_buoc": {
        "muc": DA_TAI_LIEU,
        "gia_tri": ("apiAccount", "digest", "timestamp"),
        "ghi_chu": "Trích lục câu 2: 'callback dùng ĐÚNG BA header như mọi API khác'.",
    },
    "cong_thuc_chu_ky": {
        "muc": DA_TAI_LIEU,
        "gia_tri": "digest = base64( md5-BYTES( <chuỗi JSON của bizContent> + privateKey ) )",
        "ghi_chu": "Trích lục câu 2, chép từ trang 极兔API简介. Đây là CÔNG THỨC, chưa phải"
                   " điều kiện đủ để nghiệm thu: còn hai chỗ chưa biết ở dưới.",
    },
    "khoa_ky_chieu_callback": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 6: tài liệu KHÔNG nói chiều callback ký bằng `privateKey` của tài khoản"
                   " mình hay một khoá riêng J&T cấp. Mã hiện dùng `webhook_secret` của carrier"
                   " account như GIẢ ĐỊNH có ghi chú — mức DOCUMENTED, không hơn.",
    },
    "chuoi_dem_di_ky": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 7: chỉ `bizContent`, hay cả thân form `bizContent=...`? Hiện hiểu là"
                   " CHUỖI JSON của bizContent, lấy nguyên văn từ thân.",
    },
    "vi_du_doi_chieu": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 7 xin một ví dụ đủ ba thứ (chuỗi gốc · khoá che bớt · digest). Không có"
                   " ví dụ thì không chứng minh được cách hiểu nào đúng.",
    },
    "dinh_danh_su_kien": {
        "muc": SUY_RA,
        "gia_tri": "billCode | scanTime | scanTypeCode (băm SHA-256, 24 hex)",
        "ghi_chu": "Câu 10: trong `details` KHÔNG có mã sự kiện duy nhất. Đây là khoá TỔ HỢP do"
                   " mình chọn, hãng chưa xác nhận ⇒ chống trùng đúng trong phạm vi hiểu biết"
                   " hiện tại, không phải bảo đảm của hãng.",
    },
    "moc_thoi_gian_scan": {
        "muc": DA_TAI_LIEU,
        "gia_tri": "`scanTime` trong `details`; hai định dạng đã thấy: 'YYYY-MM-DD HH:MM:SS'"
                   " và 'YYYY-MM-DDTHH:MM:SS'",
        "ghi_chu": "Câu 15: chưa rõ giờ Việt Nam hay UTC, và đâu là định dạng chuẩn. Hiện hiểu"
                   " mốc KHÔNG có nhãn múi giờ là UTC+7 (`_moc_chuan`).",
    },
    "header_timestamp": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": "mili giây; tài liệu ghi '时区：UTC+7'",
        "ghi_chu": "Câu 14 (như câu 12): mốc Unix thật (a) hay giờ treo tường UTC+7 quy đổi (b)?"
                   " Hai cách lệch ĐÚNG 7 TIẾNG mà chữ ký vẫn đúng, nên sai ở đây chỉ hiện ra"
                   " thành 'từ chối sạch' ở lớp chống phát lại. Hiện làm theo (a).",
    },
    "chinh_sach_thu_lai": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 9: số lần J&T thử lại và khoảng cách — tài liệu không nói. Vì vậy phía"
                   " nhận PHẢI tự chống trùng (đã làm, cưỡng chế bằng CSDL).",
    },
    "phan_hoi_xac_nhan": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "CHỖ HỞ THẬT: câu 9 là nơi DUY NHẤT trong trích lục nhắc tới hình dạng phản"
                   " hồi — 'khi chúng tôi trả về mã khác code=1'. Tức phản hồi được hiểu là JSON"
                   " có trường `code`, và `code=1` là được nhận. Nhưng: mã HTTP nào, còn trường"
                   " nào khác, và 200/202 có bị coi là hỏng không — CHƯA có. Xem"
                   " `phan_hoi_xac_nhan()` (có dựng sẵn, chờ AG-00 cắm vào route).",
    },
    "moc_du_lieu_them": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "`codMoney`/`goodsValue`/`itemsValue` (câu 29) và cách ánh xạ `area` (D-9)"
                   " chưa chốt ⇒ TUYỆT ĐỐI không suy ra tiền từ callback (hợp đồng §18).",
    },
    # ---- G16 (AG-04) bổ sung: những chỗ hở CÙNG LOẠI được chỉ đích danh khi rà lại trích lục.
    # Không trường nào ở đây được điền giá trị: chúng là câu hỏi, không phải dữ kiện.
    "y_nghia_apiaccount": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 8: header `apiAccount` trong callback là tài khoản API CỦA MÌNH hay của"
                   " J&T? Mã hiện kiểm nó như tài khoản của mình, và CHỈ khi credentials giải mã"
                   " được + account có lưu trường đó — đây là phép kiểm PHỤ có ghi chú, không"
                   " phải dữ kiện đã xác nhận.",
    },
    "sandbox_co_day_callback": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 24: môi trường THỬ có đẩy callback không, hay chỉ môi trường thật? Chưa"
                   " trả lời thì chặng 'callback sandbox' của harness G16 không thể lên lịch"
                   " được kể cả sau khi có credentials — xem docs/G16_SANDBOX_HARNESS.md §chặng"
                   " BLOCKED.",
    },
    "thu_tu_nhieu_su_kien": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 11: nhiều sự kiện cùng lúc có bảo đảm thứ tự theo thời gian không? Mã"
                   " đang tự sắp theo `scanTime` + thứ hạng trạng thái + watermark; đó là phòng"
                   " thủ của phía nhận, không phải bảo đảm của hãng.",
    },
    "do_lech_gio_chap_nhan": {
        "muc": CHUA_TAI_LIEU,
        "gia_tri": None,
        "ghi_chu": "Câu 13: J&T chấp nhận lệch giờ tối đa bao nhiêu? Chưa biết thì ngưỡng"
                   " `LECH_GIO_TOI_DA_MS` (15 phút) là con số CỦA MÌNH, có ghi chú — không phải"
                   " ngưỡng của hãng.",
    },
}
# Trường nào của hợp đồng còn CHƯA có tài liệu. Bộ thử canh danh sách này để không ai âm thầm
# đổi một dòng `CHUA_TAI_LIEU` thành `DA_TAI_LIEU` mà không kèm căn cứ từ hãng.
CALLBACK_CHUA_TAI_LIEU = tuple(t for t, v in HOP_DONG_CALLBACK.items() if v["muc"] == CHUA_TAI_LIEU)

# ---------------------------------------------------------------------------
# G16 (AG-04) — MỨC CỦA CẢ HỢP ĐỒNG + BẢNG CHẶN MÁY ĐỌC ĐƯỢC
# ---------------------------------------------------------------------------
# Mức cao nhất mà hợp đồng callback đạt được. Đây KHÔNG phải chỗ nâng bằng cách sửa một dòng
# mã: chỉ một lượt đối chiếu với hãng mới nâng được, và lượt đó CHƯA có — `V-G09-01` (gọi API
# hãng, kể cả sandbox) và `V-13906-05` (credentials sandbox J&T) đều CHƯA CẤP.
#
# Vì sao phải có cờ riêng thay vì tin vào docstring: một bản vá làm route chạy được (như B11)
# rất dễ bị đọc thành "hợp đồng đã xác minh". Cờ này là chỗ để bộ thử và harness đối chiếu.
HOP_DONG_MUC = MUC_DOCUMENTED
HOP_DONG_XAC_MINH_VOI_HANG = False
PHAN_HOI_XAC_MINH = False
# Trường được phép GIỮ giá trị dù mức là CHUA_TAI_LIEU: giá trị đó là CÂU CHỮ NGUYÊN VĂN của
# tài liệu, và chính câu đó là chỗ mâu thuẫn — chép nguyên văn thì kiểm được, diễn giải lại thì
# không. Mọi trường khác ở mức CHUA_TAI_LIEU phải để `gia_tri = None`.
GIA_TRI_NGUYEN_VAN_DUOC_PHEP = ("header_timestamp",)

# Mười chỗ hở, mỗi chỗ nói CHÍNH XÁC cái còn thiếu. Năm chỗ đầu là danh sách Owner chỉ đích
# danh (directive 15/10/2026, mục 13); năm chỗ sau là cùng loại, tìm được khi rà lại trích lục.
#   `cau_hoi`      — số câu gốc trong docs/JT_CAU_HOI_CHINH_THUC.md (+ mã B của docs/G14 §8)
#   `thieu`        — cái còn thiếu, nói đủ để gửi hãng nguyên văn
#   `doan_thi_hong`— đoán thì hỏng thế nào (vì sao KHÔNG được đoán)
#   `dang_chan`    — đường mã / hành vi đang bị chặn cho tới khi có câu trả lời
#   `go_khi`       — cần đúng cái gì để gỡ
CHAN_HOP_DONG_CALLBACK = {
    "khoa_ky_chieu_callback": {
        "cau_hoi": "câu 6 · G14 §8 B1",
        "thieu": "Tài liệu KHÔNG nói chiều callback được ký bằng `privateKey` của tài khoản API"
                 " của mình hay bằng một khoá riêng do J&T cấp cho chiều callback.",
        "doan_thi_hong": "Đoán khoá ⇒ chữ ký ĐÚNG của hãng vẫn bị từ chối: mất sạch callback,"
                         " và lỗi hiện ra chỉ là 'digest không khớp' — không chỉ đúng chỗ.",
        "dang_chan": "`webhook.xac_thuc_jt_digest()` giữ mức DOCUMENTED; `chon_so_do()` chọn"
                     " `jt_digest` cho mọi môi trường khác `mock` mà KHÔNG có gì bảo đảm khoá.",
        "go_khi": "hãng trả lời câu 6 kèm một ví dụ đủ ba thứ (chuỗi gốc · khoá che bớt · digest).",
    },
    "chuoi_dem_di_ky": {
        "cau_hoi": "câu 7 · G14 §8 B1",
        "thieu": "Chuỗi đem đi ký: chỉ chuỗi JSON `bizContent`, hay toàn bộ thân form"
                 " (`bizContent=...`), hay một chuỗi khác. Chưa có ví dụ đối chiếu từng byte.",
        "doan_thi_hong": "Đoán chuỗi ký ⇒ TỪ CHỐI SẠCH mọi callback thật, mà không có lỗi nào"
                         " chỉ đúng nguyên nhân.",
        "dang_chan": "`xac_thuc_jt_digest()` lấy `bizContent` nguyên văn từ thân form — cách"
                     " hiểu này là GIẢ ĐỊNH có ghi chú trong mã, không phải dữ kiện.",
        "go_khi": "hãng trả lời câu 7 (chuỗi gốc + digest kết quả để đối chiếu từng byte).",
    },
    "phuong_thuc_http": {
        "cau_hoi": "câu 2 · G14 §8 B2",
        "thieu": "Phương thức HTTP của callback (轨迹回传). Trích lục chỉ tả THÂN và HEADER.",
        "doan_thi_hong": "Ghi `POST` thành dữ kiện là bịa; nếu hãng dùng phương thức khác thì cửa"
                         " ingest hiện tại KHÔNG có route cho nó — callback rơi vào 404/405 và"
                         " không ai thấy sự kiện nào đã mất.",
        "dang_chan": "Route `POST /api/v2/webhook/nhan/<webhook_ma>` (server.py, AG-00) — có"
                     " thật và đã đo qua HTTP, nhưng chưa được đăng ký với hãng.",
        "go_khi": "hãng trả lời câu 2 (và URL công khai được cấp — `V-G11-01`).",
    },
    "phan_hoi_xac_nhan": {
        "cau_hoi": "câu 9 · G14 §8 B3",
        "thieu": "Hình dạng ĐẦY ĐỦ của thân phản hồi: mã HTTP nào là 'đã nhận', còn trường nào"
                 " khác ngoài `code`, và `200`/`202` có bị coi là hỏng không. Biết đúng MỘT mảnh:"
                 " phản hồi có trường `code`, và `code=1` là được nhận.",
        "doan_thi_hong": "Đoán mã HTTP ⇒ hãng coi MỌI callback là hỏng và đẩy lại vô hạn. Chống"
                         " trùng ở tầng CSDL cứu được DỮ LIỆU nhưng không cứu được TẢI.",
        "dang_chan": "`phan_hoi_xac_nhan()` đã dựng và đã được cắm vào route (B11) — nhưng mức"
                     " của trường này VẪN là CHUA_TAI_LIEU; bản vá đó KHÔNG phải nghiệm thu.",
        "go_khi": "hãng trả lời câu 9. Không có câu trả lời thì giữ nguyên mã HTTP cũ.",
    },
    "chinh_sach_thu_lai": {
        "cau_hoi": "câu 9 · G14 §8 B4",
        "thieu": "Số lần J&T thử lại callback, khoảng cách giữa các lần, và J&T có đẩy TRÙNG một"
                 " sự kiện không.",
        "doan_thi_hong": "Không biết thì không chọn được trần thử lại của phía nhận, và không biết"
                         " khoá chống trùng của mình có che đúng ca trùng thật hay không.",
        "dang_chan": "Trần `WEBHOOK_SO_LAN_THU`, `REPLAY_TOI_DA`, `BACKOFF_TRAN_GIAY` — đều là"
                     " con số CỦA MÌNH, có ghi chú, không phải chính sách của hãng.",
        "go_khi": "hãng trả lời câu 9/10.",
    },
    "y_nghia_apiaccount": {
        "cau_hoi": "câu 8",
        "thieu": "`apiAccount` trong header callback là tài khoản API của MÌNH hay của J&T — câu"
                 " này quyết định phép kiểm phụ trong `xac_thuc_jt_digest` có nghĩa hay không.",
        "doan_thi_hong": "Nếu header là tài khoản của J&T thì phép kiểm 'apiAccount phải khớp"
                         " credentials của account này' sẽ TỪ CHỐI OAN mọi callback thật.",
        "dang_chan": "`xac_thuc_jt_digest()` chỉ kiểm khi credentials giải mã được VÀ account có"
                     " lưu `apiAccount` — cố ý bỏ qua được, và có ghi trong mã.",
        "go_khi": "hãng trả lời câu 8 (kèm câu 21: `apiAccount` dùng chung hay mỗi đối tác một bộ).",
    },
    "sandbox_co_day_callback": {
        "cau_hoi": "câu 24",
        "thieu": "Môi trường THỬ của J&T có đẩy callback về URL của mình không, hay chỉ môi"
                 " trường thật mới đẩy.",
        "doan_thi_hong": "Giả định 'sandbox có đẩy' rồi lên lịch nghiệm thu ⇒ chờ một sự kiện"
                         " không bao giờ tới, và gọi đó là 'chưa tới' thay vì 'không thể tới'.",
        "dang_chan": "Chặng callback sandbox của harness G16 (`trien_khai/g16/`) — BLOCKED kèm"
                     " đúng hai lý do: chưa có quyền gọi hãng (`V-G09-01`), chưa có credentials"
                     " (`V-13906-05`), VÀ chưa biết sandbox có đẩy hay không.",
        "go_khi": "hãng trả lời câu 24, cùng lúc với `V-G09-01` + `V-13906-05`.",
    },
    "thu_tu_nhieu_su_kien": {
        "cau_hoi": "câu 11",
        "thieu": "Nhiều sự kiện đẩy cùng lúc có bảo đảm thứ tự theo thời gian không.",
        "doan_thi_hong": "Không biết ⇒ phải tự phòng thủ; nếu phòng thủ bị gỡ vì tin rằng 'hãng"
                         " đã sắp thứ tự' thì sự kiện cũ ghi đè sự kiện mới, và đơn lùi trạng thái.",
        "dang_chan": "Ba lớp phòng thủ của phía nhận: thứ hạng trạng thái, watermark theo `scanTime`"
                     " (chỉ tính sự kiện ĐÃ ÁP), và `UNIQUE(carrier_account_id, event_id)`.",
        "go_khi": "hãng trả lời câu 11.",
    },
    "do_lech_gio_chap_nhan": {
        "cau_hoi": "câu 13",
        "thieu": "J&T chấp nhận lệch giờ tối đa bao nhiêu giữa `timestamp` của họ và giờ máy mình.",
        "doan_thi_hong": "Đặt ngưỡng quá chặt ⇒ từ chối oan callback thật; quá rộng ⇒ lớp chống"
                         " phát lại mất tác dụng. Cả hai đều hỏng im lặng.",
        "dang_chan": "`LECH_GIO_TOI_DA_MS` = 15 phút — con số CỦA MÌNH, có ghi chú trong mã.",
        "go_khi": "hãng trả lời câu 13 (và câu 12: `timestamp` là mốc Unix thật hay giờ UTC+7 quy đổi).",
    },
    "moc_du_lieu_them": {
        "cau_hoi": "câu 29 + quyết định D-9",
        "thieu": "`codMoney`/`goodsValue`/`itemsValue` khác nhau chỗ nào và còn dùng không; cách"
                 " ánh xạ `area`/`city` cho địa chỉ hai cấp Việt Nam.",
        "doan_thi_hong": "Suy ra TIỀN từ callback chưa xác minh ⇒ sổ COD ghi một khoản không có"
                         " thật; đúng loại sai đắt nhất (hợp đồng §18).",
        "dang_chan": "Đường webhook CỐ Ý không chạm sổ COD (ba bảng `tc_` của tài chính); mọi mã"
                     " chưa xác minh đi vào NEEDS_REVIEW với 0 dòng sổ bị đụng.",
        "go_khi": "hãng trả lời câu 29 và chốt D-9.",
    },
}


def bao_cao_hop_dong_callback():
    """Báo cáo MÁY ĐỌC ĐƯỢC về hợp đồng callback: biết gì, chưa biết gì, và mức thật.

    Tồn tại để ba chỗ dùng CHUNG một nguồn: bộ thử (`thu_webhook_jt.py`), harness G16
    (`trien_khai/g16/`), và người đọc tài liệu. Không chỗ nào phải chép lại danh sách —
    chép lại là chỗ để hai bản lệch nhau mà không ai thấy.

    Cố ý KHÔNG có tham số để hạ/nâng mức: mức đọc thẳng từ `HOP_DONG_MUC`, và hàm
    `kiem_hop_dong_khong_tu_nang_muc()` canh nó.
    """
    return {
        "muc": HOP_DONG_MUC,
        "muc_toi_da_duoc_phep_dot_nay": MUC_DOCUMENTED,
        "xac_minh_voi_hang": HOP_DONG_XAC_MINH_VOI_HANG,
        "phan_hoi_xac_minh": PHAN_HOI_XAC_MINH,
        "so_truong": len(HOP_DONG_CALLBACK),
        "da_tai_lieu": sorted(t for t, v in HOP_DONG_CALLBACK.items()
                              if v["muc"] == DA_TAI_LIEU),
        "suy_ra": sorted(t for t, v in HOP_DONG_CALLBACK.items() if v["muc"] == SUY_RA),
        "chua_tai_lieu": sorted(CALLBACK_CHUA_TAI_LIEU),
        "blocked": [dict(ten=t, **CHAN_HOP_DONG_CALLBACK[t]) for t in sorted(CHAN_HOP_DONG_CALLBACK)],
        "canh_bao": ("MỘT BẢN VÁ LÀM ĐƯỜNG MÃ CHẠY ĐƯỢC KHÔNG PHẢI LÀ HỢP ĐỒNG ĐÃ XÁC MINH."
                     " Mức cao nhất đợt này là DOCUMENTED (viết theo tài liệu, chưa đối chiếu với"
                     " hãng). Muốn nâng mức phải có một lượt đối chiếu thật, và lượt đó đang"
                     " BLOCKED bởi V-G09-01 + V-13906-05."),
    }


def kiem_hop_dong_khong_tu_nang_muc():
    """Canh bất biến TRUNG THỰC của hợp đồng. Trả danh sách vi phạm (rỗng = còn trung thực).

    Bốn luật, và luật nào cũng là một cách để một bản vá bị đọc sai:
      1. Mức của cả hợp đồng không được vượt `DOCUMENTED` (không MOCK/SANDBOX/LIVE).
      2. Mọi trường trong bảng chặn phải THẬT SỰ ở mức `CHUA_TAI_LIEU` và có `ghi_chu`.
      3. Trường bị chặn không được khai `gia_tri`, trừ danh sách nguyên-văn có ghi chú.
      4. `phan_hoi_xac_nhan` không được tự nhận đã xác minh.
    """
    loi = []
    if HOP_DONG_MUC != MUC_DOCUMENTED:
        loi.append(f"HOP_DONG_MUC={HOP_DONG_MUC!r} — mức hợp đồng bị đổi khỏi DOCUMENTED")
    if HOP_DONG_MUC in (MUC_MOCK, MUC_SANDBOX, MUC_LIVE):
        loi.append(f"HOP_DONG_MUC={HOP_DONG_MUC!r} — tự nhận mức đã kiểm với hãng")
    if HOP_DONG_XAC_MINH_VOI_HANG:
        loi.append("HOP_DONG_XAC_MINH_VOI_HANG=True — chưa hề có lượt đối chiếu nào với hãng")
    if PHAN_HOI_XAC_MINH:
        loi.append("PHAN_HOI_XAC_MINH=True — hình dạng phản hồi đầy đủ vẫn CHƯA có tài liệu")
    for ten, chan in CHAN_HOP_DONG_CALLBACK.items():
        truong = HOP_DONG_CALLBACK.get(ten)
        if truong is None:
            loi.append(f"{ten}: nằm trong bảng chặn nhưng không có trong HOP_DONG_CALLBACK")
            continue
        if truong["muc"] != CHUA_TAI_LIEU:
            loi.append(f"{ten}: mức {truong['muc']!r} — bảng chặn nói CHƯA có tài liệu")
        if not str(truong.get("ghi_chu") or "").strip():
            loi.append(f"{ten}: không ghi lý do")
        if truong.get("gia_tri") is not None and ten not in GIA_TRI_NGUYEN_VAN_DUOC_PHEP:
            loi.append(f"{ten}: khai giá trị {truong['gia_tri']!r} trong khi tài liệu chưa trả lời")
        for khoa in ("cau_hoi", "thieu", "doan_thi_hong", "dang_chan", "go_khi"):
            if not str(chan.get(khoa) or "").strip():
                loi.append(f"{ten}: bảng chặn thiếu '{khoa}' — phải nói chính xác cái còn thiếu")
    if HOP_DONG_CALLBACK["phan_hoi_xac_nhan"]["muc"] != CHUA_TAI_LIEU:
        loi.append("phan_hoi_xac_nhan: bị nâng mức — bản vá B11 KHÔNG phải nghiệm thu")
    return loi


def phan_hoi_xac_nhan(nhan_duoc: bool, su_kien_id=None, ly_do=None):
    """Dựng phản hồi cho J&T theo chỗ DUY NHẤT trích lục nói tới: `code=1` là được nhận.

    Trả `(ma_http, than_dict)`. CỐ Ý không tự gắn vào route: `server.py` là file của AG-00
    (hợp đồng §22), và hình dạng phản hồi ĐẦY ĐỦ còn nằm trong `CHUA_TAI_LIEU`.

    Vì sao vẫn dựng: hiện route trả `202 {"ket_qua": "da_nhan", ...}` — KHÔNG có trường `code`.
    Nếu J&T thật sự chỉ chấp nhận `code=1` thì mọi callback của họ bị coi là hỏng và bị đẩy lại
    vô hạn; chống trùng ở tầng CSDL cứu được dữ liệu nhưng không cứu được tải. Đây là một việc
    PHẢI hỏi hãng (câu 2/câu 9), không phải chỗ để tự chọn.

    G16 (AG-04) — ĐỌC KÈM `PHAN_HOI_XAC_MINH` (đang `False`) trước khi tin hàm này: nó DỰNG
    được phản hồi theo mảnh duy nhất tài liệu nói tới, nhưng hình dạng ĐẦY ĐỦ vẫn nằm trong
    `CHAN_HOP_DONG_CALLBACK["phan_hoi_xac_nhan"]`. Thân phản hồi CỐ Ý không được thêm trường
    mới: thêm một trường vào thứ mình chưa biết hình dạng là đoán.
    """
    if nhan_duoc:
        than = {"code": 1, "msg": "success"}
        if su_kien_id is not None:
            than["su_kien_id"] = su_kien_id
        return 200, than
    than = {"code": 0, "msg": str(ly_do or "rejected")}
    return 400, than


def tim_account_theo_webhook_ma(webhook_ma):
    return csdl.mot("SELECT * FROM carrier_accounts WHERE webhook_ma=? AND kich_hoat=1", (webhook_ma,))


def tenant_tu_account(tenant_id, account_id=None):
    """W03 (G14) — NGUỒN DUY NHẤT hợp lệ của `tenant_id` trên đường callback.

    `tenant_id` đến từ dòng `carrier_accounts` đã tra được trên URL + chữ ký của CHÍNH account
    đó (hợp đồng §1 và §12). Hàm này tồn tại để chỗ quyết định có TÊN: trước đây việc giải
    tenant nằm rải trong câu truy vấn đơn, nên không có chỗ nào để soi "tenant này từ đâu ra".
    Payload có khai `tenant_id` thì cũng KHÔNG đi qua đây — xem `_claim_tenant()` (chỉ ghi lại).

    Người gọi PHẢI truyền giá trị đọc từ dòng `carrier_accounts` (`tk["tenant_id"]`) — chốt
    chặn cấu trúc `thu_webhook.test_i04` canh đúng chỗ đó, nên chữ ký hàm nhận thẳng giá trị
    thay vì nhận cả dòng: như vậy phép kiểm "tenant từ đâu ra" vẫn nhìn thấy được ở nơi gọi.
    Ném `LoiVinhVien` khi account không gắn tenant — dữ liệu hỏng, thử lại không khỏi.
    """
    if tenant_id in (None, ""):
        raise LoiVinhVien(f"carrier_account {account_id} không gắn tenant nào")
    return tenant_id


def kiem_chu_ky(tk_row, headers, body: bytes):
    """Giữ NGUYÊN chữ ký hàm (server.py đang gọi): trả bool.

    Khác bản trước: sơ đồ xác thực chọn theo hãng + môi trường, và mọi lượt từ chối đều ghi
    audit — chữ ký sai im lặng là chỗ không ai phát hiện được việc dò secret.
    """
    ten, ham, muc = chon_so_do(tk_row)
    if ham is None:
        csdl.audit("webhook_chu_ky_tu_choi", f"carrier_account:{tk_row['id']}",
                   f"hãng {tk_row['hang']} môi trường {tk_row['moi_truong']}: sơ đồ xác thực"
                   f" {muc} — chưa có tài liệu callback",
                   tenant_id=tk_row["tenant_id"], ket_qua="tu_choi")
        return False
    try:
        ok, ly_do = ham(tk_row, headers, body)
    except Exception as e:
        ok, ly_do = False, f"lỗi khi kiểm chữ ký: {type(e).__name__}"
    if not ok:
        csdl.audit("webhook_chu_ky_tu_choi", f"carrier_account:{tk_row['id']}",
                   f"so_do={ten} muc={muc} ly_do={ly_do}",
                   tenant_id=tk_row["tenant_id"], ket_qua="tu_choi")
    return bool(ok)


# ============================================================================
# W04 — ĐỊNH DANH SỰ KIỆN BỀN (chống trùng)
# ============================================================================
def dinh_danh_su_kien(tk_row, body: bytes):
    """Định danh BỀN của một sự kiện, để UNIQUE(carrier_account_id, event_id) chặn trùng được.

    Thứ tự ưu tiên: event_id do bên gửi cấp → khóa tổ hợp của hãng (J&T: billCode|scanTime|
    scanTypeCode) → băm nội dung. Băm nội dung là phương án CUỐI: hai sự kiện khác nhau mà nội
    dung y hệt sẽ bị coi là một, nên hãng nào có khóa riêng thì phải dùng khóa riêng.
    """
    try:
        d = json.loads(body)
    except Exception:
        d = None
    if isinstance(d, dict):
        for t in ("event_id", "eventId"):
            if str(d.get(t) or "").strip():
                return str(d[t]).strip()
    sv = doc_su_kien_hang(tk_row, body)
    if sv and sv.get("khoa_hang"):
        return sv["khoa_hang"]
    return "noid-" + hashlib.sha256(body).hexdigest()[:24]


# ============================================================================
# W05/W06 — ĐỌC SỰ KIỆN HÃNG
# ============================================================================
def doc_su_kien_hang(tk_row, body: bytes):
    """Chuẩn hóa payload về MỘT khung chung, nói rõ mã đến từ đâu. None = không đọc được.

    `nguon_ma`:
      - "hang" → mã riêng của hãng, PHẢI đi qua trang_thai_hang.quyet_dinh()
      - "hub"  → payload dùng tên trạng thái chuẩn của hub (callback mô phỏng của chính dự án)
    """
    try:
        van_ban = body.decode("utf-8")
    except (UnicodeDecodeError, AttributeError):
        return None
    try:
        d = json.loads(van_ban)
    except ValueError:
        d = None

    # --- dạng J&T: bizContent (form hoặc JSON bọc) chứa billCode + details[] ---
    biz = _bizcontent_tu_than(body)
    if biz is not None:
        try:
            nv = json.loads(biz)
        except ValueError:
            return None
        return _doc_jt(nv, tho={"bizContent": nv}) if isinstance(nv, dict) else None
    if isinstance(d, dict) and ("billCode" in d or "details" in d):
        return _doc_jt(d, tho=d)

    # --- dạng hub: event + tracking_number ---
    if isinstance(d, dict) and d.get("event") and d.get("tracking_number"):
        return {"nguon_ma": "hub", "ma_van_don": str(d["tracking_number"]),
                "ma_trang_thai": str(d["event"]), "moc_hang": _moc_chuan(d.get("hang_luc")),
                "thu_tu_hang": _so_nguyen(d.get("sequence")), "mo_ta_hang": None,
                "khoa_hang": None, "tho": d, "claim_tenant": _claim_tenant(d)}
    return None


def _claim_tenant(d):
    """tenant_id/tenantId trong payload — CHỈ để ghi lại là có người cố khai, không bao giờ dùng."""
    for t in ("tenant_id", "tenantId", "tenant"):
        if t in d:
            return d[t]
    return None


def _doc_jt(nv, tho):
    """Đọc một bản tin hành trình J&T. Lấy bản quét MỚI NHẤT theo scanTime trong details[]."""
    ma_van_don = str(nv.get("billCode") or nv.get("txlogisticId") or "")
    chi_tiet = nv.get("details") or nv.get("detail") or []
    if isinstance(chi_tiet, dict):
        chi_tiet = [chi_tiet]
    moi_nhat, moc_moi_nhat = None, None
    for c in chi_tiet:
        if not isinstance(c, dict):
            continue
        moc = _moc_chuan(c.get("scanTime"))
        if moi_nhat is None or (moc or "") >= (moc_moi_nhat or ""):
            moi_nhat, moc_moi_nhat = c, moc
    if moi_nhat is None:
        return None
    ma_tt = moi_nhat.get("scanTypeCode", moi_nhat.get("scanType"))
    khoa = None
    if ma_van_don and moi_nhat.get("scanTime") is not None and ma_tt is not None:
        khoa = "jt-" + hashlib.sha256(
            f"{ma_van_don}|{moi_nhat.get('scanTime')}|{ma_tt}".encode()).hexdigest()[:24]
    return {"nguon_ma": "hang", "ma_van_don": ma_van_don, "ma_trang_thai": ma_tt,
            "moc_hang": moc_moi_nhat, "thu_tu_hang": _so_nguyen(moi_nhat.get("sequence")),
            "mo_ta_hang": moi_nhat.get("desc") or moi_nhat.get("scanTypeName"),
            "khoa_hang": khoa, "tho": tho, "claim_tenant": _claim_tenant(nv)}


def _so_nguyen(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _moc_chuan(v):
    """Đổi mốc thời gian của hãng về chuỗi 14 chữ số (epoch mili giây, zero-pad) để SO SÁNH ĐƯỢC
    bằng cả `<` của chuỗi lẫn MAX() của SQL. None = không đọc được.

    §12.2 "mọi mốc thời gian phải mang múi giờ": J&T khai UTC+7, nên "YYYY-MM-DD HH:MM:SS" không
    có hậu tố múi giờ được hiểu là UTC+7 — hiểu theo giờ máy là chỗ lệch 7 tiếng mà không báo lỗi.
    """
    if v is None:
        return None
    import datetime as _dt
    tz7 = _dt.timezone(_dt.timedelta(hours=7))
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        ms = int(v if v > 10 ** 12 else v * 1000)
        return "%014d" % ms
    s = str(v).strip()
    if not s:
        return None
    if s.isdigit():
        n = int(s)
        return "%014d" % (n if len(s) >= 13 else n * 1000)
    s2 = s.replace("T", " ").replace("/", "-")
    m = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}(:\d{2})?)(\.\d+)?\s*([+-]\d{2}:?\d{2}|Z)?$", s2)
    if not m:
        return None
    goc = m.group(1) if m.group(2) else m.group(1) + ":00"
    try:
        t = _dt.datetime.strptime(goc, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    hau = m.group(4)
    if not hau:
        t = t.replace(tzinfo=tz7)
    elif hau == "Z":
        t = t.replace(tzinfo=_dt.timezone.utc)
    else:
        h = hau.replace(":", "")
        dau = -1 if h[0] == "-" else 1
        t = t.replace(tzinfo=_dt.timezone(
            dau * _dt.timedelta(hours=int(h[1:3]), minutes=int(h[3:5]))))
    return "%014d" % int(t.timestamp() * 1000)


# ============================================================================
# Dò schema: mã phải chạy được trên CSDL CHƯA migrate (AG-00 giữ csdl.py/migrate.py)
# ============================================================================
COT_MO_RONG = ("hang_ma_goc", "hang_mo_ta_goc", "hang_su_kien_goc", "anh_xa_do_tin_cay",
               "anh_xa_nguon", "can_soat", "hang_moc_thoi_gian", "don_id", "trang_thai_chuan")
_cot_cache = {}


def cot_co(bang, cot):
    """Có cột này trong bảng không? Dò bằng PRAGMA table_info, nhớ kết quả theo tiến trình."""
    khoa = (bang, cot)
    if khoa in _cot_cache:
        return _cot_cache[khoa]
    try:
        ten = {r[1] for r in csdl.nhieu(f"PRAGMA table_info({bang})")}
    except Exception:
        ten = set()
    for c in COT_MO_RONG:
        _cot_cache[(bang, c)] = c in ten
    _cot_cache[khoa] = cot in ten
    return _cot_cache[khoa]


def xoa_cache_cot():
    """Gọi sau khi migrate (hoặc trong bộ thử khi đổi CSDL) để dò lại schema."""
    _cot_cache.clear()


# ============================================================================
# NHẬN SỰ KIỆN
# ============================================================================
def nhan_su_kien(tk_row, body: bytes, headers: dict):
    """Lưu bền + xếp hàng. Trả (sk_id, trung)."""
    event_id = dinh_danh_su_kien(tk_row, body)
    with csdl.khoa_ghi:
        try:
            con = csdl.ghi(
                "INSERT INTO wh_su_kien (carrier_account_id, event_id, payload_tho, headers_json, nhan_luc)"
                " VALUES (?,?,?,?,?)",
                (tk_row["id"], event_id, body, json.dumps(headers, ensure_ascii=False), csdl.bay_gio()))
        except csdl.LoiToanVen:
            cu = csdl.mot("SELECT id FROM wh_su_kien WHERE carrier_account_id=? AND event_id=?",
                          (tk_row["id"], event_id))
            return cu["id"], True
    nap(con.lastrowid)
    return con.lastrowid, False


def nap(sk_id):
    _hang_doi.put(sk_id)


# ============================================================================
# W05 — MỐC THỜI GIAN HÃNG: watermark theo từng đơn
# ============================================================================
def watermark(don_id):
    """Mốc hãng mới nhất ĐÃ ÁP cho đơn này (chuỗi 14 chữ số), hoặc None.

    Hai nguồn, theo đúng thứ tự tin cậy:
      1. cột `wh_su_kien.hang_moc_thoi_gian` + `wh_su_kien.don_id` — khi CSDL đã migrate;
      2. audit `webhook_moc_hang` — chạy được NGAY trên CSDL chưa migrate.
    Cả hai đều là dấu vết do CHÍNH đường cập nhật này ghi ra (§12.1 luật 2).

    VÁ G14 (AG-03) — lỗi đo được, xem `docs/G14_JT_WEBHOOK.md` §4:
    cột `hang_moc_thoi_gian` từng được ghi cho MỌI sự kiện đọc được, kể cả sự kiện KHÔNG ĐƯỢC ÁP
    (mã nhập nhằng 110, mã chỉ ghi nhận như 121, mã lạ, và cả sự kiện bị rank guard chặn).
    Nguồn audit thì chỉ ghi khi ĐÃ ÁP — hai nguồn nói khác nhau, và nguồn được ưu tiên lại là
    nguồn sai.

    Hậu quả đo được (CSDL đã migrate): `121 FINISH` lúc 10:00 (không áp) đẩy watermark lên
    10:00, rồi `113 Delivered` lúc 09:00 đến sau bị chặn với lý do "đến muộn" ⇒ đơn KHÔNG BAO
    GIỜ được đánh dấu đã giao. Mã nhập nhằng 110 một mình không đổi trạng thái đơn, nhưng nó
    RÒ RA ngoài chính nó bằng đường này.

    Vá hai tầng, và tầng thứ hai là để cứu DỮ LIỆU CŨ:
      1. `_ghi_watermark()` nay là nơi DUY NHẤT ghi cột, và chỉ ghi khi `ap_dung=1`
         (`luu_dau_vet` không ghi cột này nữa). Sự kiện không được áp không đẩy mốc.
      2. Ở đây vẫn lọc `trang_thai_chuan IS NOT NULL`: những dòng do mã CŨ ghi đã nằm trong
         CSDL thật rồi, và chúng phải tiếp tục bị bỏ qua. Bỏ bộ lọc này là lỗi cũ sống lại
         trên đúng dữ liệu đang có.
    """
    if cot_co("wh_su_kien", "hang_moc_thoi_gian") and cot_co("wh_su_kien", "don_id"):
        dk = ["don_id=?", "trang_thai='xong'", "hang_moc_thoi_gian IS NOT NULL"]
        if cot_co("wh_su_kien", "trang_thai_chuan"):
            # CSDL chưa migrate thì cột này không có — lùi về hành vi cũ thay vì nổ.
            dk.append("trang_thai_chuan IS NOT NULL")
        r = csdl.mot("SELECT MAX(hang_moc_thoi_gian) m FROM wh_su_kien"
                     f" WHERE {' AND '.join(dk)}", (don_id,))
        if r and r["m"]:
            return r["m"]
    r = csdl.mot("SELECT MAX(chi_tiet) m FROM audit WHERE hanh_dong='webhook_moc_hang'"
                 " AND resource_type='don' AND resource_id=?", (str(don_id),))
    return (r["m"] if r else None) or None


def _ghi_watermark(sk_id, don_id, moc, tenant_id):
    """Ghi mốc hãng ĐÃ ÁP. Nơi DUY NHẤT được viết `wh_su_kien.hang_moc_thoi_gian`.

    Chỉ gọi khi `don_hang.ap_trang_thai_giao` trả `ap_dung=1`. Một sự kiện KHÔNG đổi được
    trạng thái (mã nhập nhằng, mã chỉ ghi nhận, mã lạ, hoặc bị rank guard chặn) thì **không**
    được đẩy mốc: nếu nó đẩy, một bản quét CÓ THẬT đến sau nhưng có `scanTime` cũ hơn sẽ bị
    chặn oan và mất hẳn — đó đúng là lỗi G14 đã đo được.

    Ghi HAI nơi, cố ý: cột để truy vấn nhanh, audit để không thể mất (và để CSDL chưa migrate
    vẫn có nguồn). Hai nguồn này phải luôn nói CÙNG một con số — ca `thu_webhook.test_g02` canh.
    """
    if not moc:
        return
    if cot_co("wh_su_kien", "hang_moc_thoi_gian"):
        csdl.ghi("UPDATE wh_su_kien SET hang_moc_thoi_gian=? WHERE id=?", (moc, sk_id))
    csdl.audit("webhook_moc_hang", f"don:{don_id}", moc, tenant_id=tenant_id)


# ============================================================================
# W06 — LƯU DẤU VẾT ÁNH XẠ
# ============================================================================
def luu_dau_vet(sk_id, qd, don_id=None, tenant_id=None):
    """Lưu mã gốc · mô tả gốc · sự kiện hãng gốc · nguồn tài liệu + phiên bản · độ tin cậy ánh xạ
    · nhãn soát · giờ nhận.

    Ghi vào CỘT khi CSDL đã migrate; LUÔN LUÔN ghi thêm một dòng audit, để trên CSDL chưa migrate
    vẫn không mất dấu vết nào. (Cột là nơi truy vấn nhanh; audit là nơi không thể mất.)

    G14: hàm này **KHÔNG** ghi `hang_moc_thoi_gian` nữa. Mốc chỉ được ghi khi sự kiện thật sự
    đổi được trạng thái (`_ghi_watermark`), vì ghi cho mọi sự kiện là cách một mã không được áp
    chặn oan một bản quét có thật đến sau. Mốc gốc của hãng vẫn nằm nguyên trong
    `hang_su_kien_goc` (cột) và trong audit `webhook_anh_xa` (dòng `su_kien_hang_goc`) — không
    mất dấu vết nào, chỉ mất quyền ĐẨY MỐC của sự kiện không được áp.
    """
    chi_tiet = {
        "su_kien": sk_id, "ma_goc": qd.ma_goc, "mo_ta_goc": qd.mo_ta_goc,
        "do_tin_cay": qd.do_tin_cay, "nhan": qd.nhan, "can_soat": bool(qd.can_soat),
        "nguon_tai_lieu": qd.nguon_tai_lieu, "phien_ban_tai_lieu": qd.phien_ban_tai_lieu,
        "trang_thai_ap": qd.trang_thai_ap, "nhan_luc": qd.nhan_luc, "ghi_chu": qd.ghi_chu,
        "cac_nghia": qd.cac_nghia or {}, "nghia_da_chot": qd.nghia_da_chot,
        "su_kien_hang_goc": qd.su_kien_hang_goc,
    }
    csdl.audit("webhook_anh_xa", f"su_kien:{sk_id}",
               json.dumps(chi_tiet, ensure_ascii=False, default=str),
               tenant_id=tenant_id, ket_qua="that_bai" if qd.can_soat else "thanh_cong")
    dat, ts = [], []
    for cot, gt in (("hang_ma_goc", None if qd.ma_goc is None else str(qd.ma_goc)),
                    ("hang_mo_ta_goc", qd.mo_ta_goc),
                    ("hang_su_kien_goc", json.dumps(qd.su_kien_hang_goc, ensure_ascii=False,
                                                    default=str) if qd.su_kien_hang_goc else None),
                    ("anh_xa_do_tin_cay", qd.do_tin_cay),
                    ("anh_xa_nguon", f"{qd.nguon_tai_lieu or ''} [{qd.phien_ban_tai_lieu}]"),
                    ("can_soat", 1 if qd.can_soat else 0),
                    ("trang_thai_chuan", qd.trang_thai_ap),
                    ("don_id", don_id)):
        if cot_co("wh_su_kien", cot):
            dat.append(f"{cot}=?")
            ts.append(gt)
    if dat:
        ts.append(sk_id)
        csdl.ghi(f"UPDATE wh_su_kien SET {', '.join(dat)} WHERE id=?", ts)


# ============================================================================
# XỬ LÝ MỘT SỰ KIỆN
# ============================================================================
def _xu_ly(sk):
    """Normalize + resolve tenant/order + guard + update. Ném LoiVinhVien khi không thể tự khỏi."""
    body = bytes(sk["payload_tho"])
    tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (sk["carrier_account_id"],))
    if tk is None:
        raise LoiVinhVien("carrier_account đã biến mất")
    # W03 (G14): tenant giải từ carrier_account, gọi tên ra — KHÔNG đọc từ payload ở bất kỳ đâu.
    tenant_id = tenant_tu_account(tk["tenant_id"], tk["id"])
    sv = doc_su_kien_hang(tk, body)
    if sv is None:
        raise LoiVinhVien("payload không đọc được (không phải JSON/form hợp lệ của dạng nào đã biết)")
    if not sv["ma_van_don"] or sv["ma_trang_thai"] in (None, ""):
        raise LoiVinhVien("thiếu mã vận đơn hoặc mã trạng thái")

    # Payload cố khai tenant → GHI LẠI rồi BỎ QUA. tenant chỉ đến từ carrier_account.
    if sv.get("claim_tenant") is not None and str(sv["claim_tenant"]) != str(tenant_id):
        csdl.audit("webhook_claim_tenant_bi_bo_qua", f"su_kien:{sk['id']}",
                   f"payload khai tenant={sv['claim_tenant']!r}, account thuộc tenant"
                   f"={tenant_id} — dùng tenant của account",
                   tenant_id=tenant_id, ket_qua="tu_choi")

    if isinstance(sv.get("tho"), dict) and sv["tho"].get("demo_force_fail"):
        raise RuntimeError("demo_force_fail đang bật")  # lỗi TẠM để kiểm retry/DLQ

    # W06: mã của hãng PHẢI đi qua quyet_dinh() — một chỗ duy nhất quyết định nghĩa của mã.
    qd = tth.quyet_dinh(tk["hang"], sv["ma_trang_thai"], su_kien_goc=sv, nhan_luc=sk["nhan_luc"])
    if sv["nguon_ma"] == "hub" and qd.trang_thai_ap is None and not qd.nhap_nhang \
            and sv["ma_trang_thai"] in cau_hinh.HANG_TRANG_THAI_GIAO:
        # Callback của hub nói thẳng tên trạng thái chuẩn (bộ mô phỏng của chính dự án).
        # CỐ Ý không áp cho mã nhập nhằng: mã của hãng không được đi cửa sau này.
        qd.trang_thai_ap = sv["ma_trang_thai"]
        qd.can_soat = False
        qd.do_tin_cay = tth.TIN_CAO
        qd.mo_ta_goc = qd.mo_ta_goc or "trạng thái chuẩn của hub (callback mô phỏng)"
        qd.ghi_chu = "callback hub: tên trạng thái chuẩn, không qua bảng mã hãng"

    # RESOLVE: đơn phải thuộc ĐÚNG tenant của account và đúng account — không bao giờ chéo tenant.
    # `tenant_id` ở đây đã đi qua `tenant_tu_account()`, không phải giá trị nào trong payload.
    don = csdl.mot(
        "SELECT * FROM don_hang WHERE ma_van_don=? AND tenant_id=? AND carrier_account_id=?",
        (sv["ma_van_don"], tenant_id, tk["id"]))
    if not don:
        luu_dau_vet(sk["id"], qd, None, tenant_id)
        csdl.audit("webhook_khong_khop_don", f"su_kien:{sk['id']}",
                   f"mã vận đơn {sv['ma_van_don']} không thuộc tenant {tenant_id}"
                   f" / account {tk['id']}", tenant_id=tenant_id, ket_qua="tu_choi")
        return "khong_khop"  # lưu thô, đánh dấu không khớp — không đụng đơn của ai

    luu_dau_vet(sk["id"], qd, don["id"], tenant_id)

    if qd.trang_thai_ap is None:
        csdl.audit("webhook_can_soat" if qd.can_soat else "webhook_chi_ghi_nhan",
                   f"don:{don['id']}",
                   f"su_kien:{sk['id']} ma_goc={qd.ma_goc!r} nhan={qd.nhan}"
                   f" tin_cay={qd.do_tin_cay} — KHÔNG đổi trạng thái. {qd.ghi_chu}",
                   tenant_id=tenant_id, ket_qua="that_bai" if qd.can_soat else "thanh_cong")
        return "xong"

    # W05: chặn sự kiện đến muộn bằng MỐC CỦA HÃNG, TRƯỚC cả rank guard.
    # Rank guard một mình không chặn được ca "Delivered cũ đến sau Returning mới": hạng 5 < 6 nên
    # nó bị chặn, nhưng ca "Delivered cũ đến sau dang_giao mới" thì hạng 5 > 3 ⇒ lọt.
    # G14: `watermark()` chỉ tính sự kiện ĐÃ ÁP, nên mã nhập nhằng không đầu độc được chỗ này.
    moc = sv.get("moc_hang")
    if moc:
        wm = watermark(don["id"])
        if wm and moc < wm:
            csdl.audit("webhook_den_muon", f"don:{don['id']}",
                       f"su_kien:{sk['id']} moc_hang={moc} < moc đã áp={wm}"
                       f" — KHÔNG áp {qd.trang_thai_ap}",
                       tenant_id=tenant_id, ket_qua="tu_choi")
            return "xong"

    ap_dung, ly_do = don_hang.ap_trang_thai_giao(
        tenant_id, don["id"], qd.trang_thai_ap, f"webhook:{sk['id']}")
    if ap_dung and moc:
        # G14: mốc chỉ được ghi khi trạng thái THẬT SỰ đổi. Sự kiện bị rank guard chặn
        # (`ap_dung=0`) không được đẩy mốc — xem `_ghi_watermark`.
        _ghi_watermark(sk["id"], don["id"], moc, tenant_id)
    csdl.audit("webhook_cap_nhat_don", f"don:{don['id']}",
               f"su_kien:{sk['id']} loai={qd.trang_thai_ap} ap_dung={ap_dung} {ly_do}"
               f" ma_goc={qd.ma_goc!r} tin_cay={qd.do_tin_cay}", tenant_id=tenant_id)
    return "xong"


# ============================================================================
# W04/W07 — HÀNG ĐỢI, RETRY, DLQ, REPLAY
# ============================================================================
def _nhan_viec(sk_id):
    """Nhận việc NGUYÊN TỬ: chỉ một worker lấy được một sự kiện.

    Bản trước là `SELECT` rồi `UPDATE` không điều kiện → hai worker cùng đọc 'moi' rồi cùng xử lý
    MỘT dòng. UNIQUE ở tầng nhận không cứu được chỗ này vì cả hai làm trên cùng một sự kiện.
    """
    with csdl.khoa_ghi:
        con = csdl.ghi("UPDATE wh_su_kien SET trang_thai='dang_xu_ly' WHERE id=?"
                       " AND trang_thai IN ('moi','cho_thu_lai')", (sk_id,))
        if con.rowcount != 1:
            return None
        return csdl.mot("SELECT * FROM wh_su_kien WHERE id=?", (sk_id,))


def _chay_mot(sk_id):
    sk = _nhan_viec(sk_id)
    if sk is None:
        return   # worker khác đã nhận, hoặc sự kiện đã ở trạng thái cuối
    try:
        kq = _xu_ly(sk)
        csdl.ghi("UPDATE wh_su_kien SET trang_thai=?, loi_cuoi=NULL, xu_ly_xong_luc=? WHERE id=?",
                 (kq, csdl.bay_gio(), sk_id))
    except LoiVinhVien as e:
        # "Poison message": không bao giờ tự khỏi → vào DLQ NGAY, không đốt lượt thử nào.
        csdl.ghi("UPDATE wh_su_kien SET trang_thai='dlq', loi_cuoi=? WHERE id=?",
                 (f"vinh vien: {e}", sk_id))
        csdl.audit("webhook_dlq", f"su_kien:{sk_id}", f"lỗi vĩnh viễn: {e}", ket_qua="that_bai")
    except Exception as e:
        so_lan = sk["so_lan_thu"] + 1
        if so_lan >= cau_hinh.WEBHOOK_SO_LAN_THU:
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='dlq', so_lan_thu=?, loi_cuoi=? WHERE id=?",
                     (so_lan, f"qua {so_lan} lan: {e}", sk_id))
            csdl.audit("webhook_dlq", f"su_kien:{sk_id}",
                       f"hết {so_lan} lần thử: {type(e).__name__}: {e}", ket_qua="that_bai")
        else:
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='cho_thu_lai', so_lan_thu=?, loi_cuoi=? WHERE id=?",
                     (so_lan, str(e), sk_id))
            cho = min(cau_hinh.WEBHOOK_BACKOFF_GOC * (2 ** (so_lan - 1)), BACKOFF_TRAN_GIAY)
            threading.Timer(cho, nap, args=(sk_id,)).start()


def so_lan_replay(sk_id):
    """Số lần đã replay THỦ CÔNG sự kiện này — đọc từ audit, là dấu vết do chính cửa replay ghi."""
    r = csdl.mot("SELECT COUNT(*) c FROM audit WHERE hanh_dong='webhook_replay'"
                 " AND resource_type='su_kien' AND resource_id=?", (str(sk_id),))
    return (r["c"] if r else 0) or 0


def co_the_replay(sk_id):
    """(duoc, ly_do). Trần số lần là chốt chặn chống 'replay vô hạn' trên một poison message."""
    n = so_lan_replay(sk_id)
    if n >= REPLAY_TOI_DA:
        return False, (f"đã replay {n} lần (trần {REPLAY_TOI_DA}) — sửa nguyên nhân,"
                       " đừng replay thêm")
    return True, ""


def yeu_cau_replay(sk_id, tenant_id, user_id=None):
    """Replay có kiểm soát: đúng tenant · có TRẦN · ghi audit · rồi mới xếp lại hàng.

    Quyền (`tenant.webhook.replay`) do tầng HTTP kiểm — hàm này KHÔNG tự cấp quyền. Nó thêm ba
    thứ mà tầng HTTP hiện chưa có: chặn chéo tenant một lần nữa, trần số lần replay, và chặn
    replay khi sự kiện ĐANG được xử lý.
    Trả (ok, ly_do).
    """
    sk = csdl.mot("SELECT s.*, c.tenant_id t FROM wh_su_kien s JOIN carrier_accounts c"
                  " ON c.id=s.carrier_account_id WHERE s.id=?", (sk_id,))
    if not sk or sk["t"] != tenant_id:
        return False, "không có sự kiện này"
    # VÁ G14: replay một sự kiện ĐANG xử lý là một lượt replay MẤT IM LẶNG.
    # `yeu_cau_replay` đặt `trang_thai='moi'` rồi xếp hàng; worker đang giữ sự kiện đó chạy xong
    # và đặt lại `trang_thai='xong'`; lượt trong hàng đợi tới `_nhan_viec` thì thấy 'xong' nên
    # bỏ qua. Người bấm thấy HTTP 202 "đã nạp lại" nhưng không có gì chạy lại — đúng kiểu hỏng
    # không báo lỗi mà §12.2 cấm. Từ chối thẳng thì người vận hành biết phải đợi.
    if sk["trang_thai"] == "dang_xu_ly":
        ly_do = "sự kiện đang được xử lý — đợi xong rồi replay"
        csdl.audit("webhook_replay_tu_choi", f"su_kien:{sk_id}", ly_do,
                   tenant_id=tenant_id, user_id=user_id, ket_qua="tu_choi")
        return False, ly_do
    duoc, ly_do = co_the_replay(sk_id)
    if not duoc:
        csdl.audit("webhook_replay_tu_choi", f"su_kien:{sk_id}", ly_do,
                   tenant_id=tenant_id, user_id=user_id, ket_qua="tu_choi")
        return False, ly_do
    csdl.ghi("UPDATE wh_su_kien SET trang_thai='moi', so_lan_thu=0, loi_cuoi=NULL WHERE id=?", (sk_id,))
    csdl.audit("webhook_replay", f"su_kien:{sk_id}", f"trạng thái trước: {sk['trang_thai']}",
               tenant_id=tenant_id, user_id=user_id)
    nap(sk_id)
    return True, ""


def _vong_lap():
    global _dang_xu_ly
    while not _dung.is_set():
        try:
            sk_id = _hang_doi.get(timeout=0.2)
        except queue.Empty:
            continue
        with _cho_trong:
            _dang_xu_ly += 1
        try:
            _chay_mot(sk_id)
        finally:
            _hang_doi.task_done()
            with _cho_trong:
                _dang_xu_ly -= 1
                _cho_trong.notify_all()


def khoi_dong():
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    xoa_cache_cot()
    kn = csdl.mo()
    with csdl.khoa_ghi:
        kn.execute("UPDATE wh_su_kien SET trang_thai='moi' WHERE trang_thai='dang_xu_ly'")
    for d in kn.execute("SELECT id FROM wh_su_kien WHERE trang_thai IN ('moi','cho_thu_lai') ORDER BY id"):
        nap(d["id"])
    _dung.clear()
    _worker = threading.Thread(target=_vong_lap, name="hub-webhook-worker", daemon=True)
    _worker.start()


def dung():
    _dung.set()


def cho_rong(het_gio=10.0):
    import time
    moc = time.time() + het_gio
    while time.time() < moc:
        with _cho_trong:
            if _hang_doi.unfinished_tasks == 0 and _dang_xu_ly == 0:
                return True
            _cho_trong.wait(timeout=0.1)
    return False


# ============================================================================
# W05 (G14) — ĐỐI CHIẾU HÀNH TRÌNH (tracking reconciliation)
# ============================================================================
# Sinh ra từ một câu hỏi rất cụ thể: sau khi webhook chạy một thời gian, LÀM SAO BIẾT nó có
# đang bỏ sót gì không? Không có hàm này thì chỉ có cách mở CSDL bằng tay, và cách đó không
# lặp lại được. Hàm dưới đây CHỈ ĐỌC, chỉ trong MỘT tenant, và trả về đúng những chỗ lệch.
#
# Trạng thái coi là "đang chạy": hạng thấp hơn `giao_thanh_cong` — suy từ cau_hinh để không
# khai một danh sách thứ hai rồi hai danh sách lệch nhau (§12.2).
_HANG_GIAO = cau_hinh.HANG_TRANG_THAI_GIAO
DANG_CHAY = tuple(sorted((k for k, v in _HANG_GIAO.items() if v < _HANG_GIAO["giao_thanh_cong"]),
                         key=_HANG_GIAO.get))


def doi_chieu_hanh_trinh(tenant_id, giay_gan_nhat=3600, gioi_han=200):
    """Đối chiếu sự kiện webhook ↔ đơn hàng của MỘT tenant. Chỉ đọc, không sửa gì.

    Trả dict:
      `lech_tenant`     — BẤT BIẾN: sự kiện của account tenant A lại trỏ vào đơn tenant B.
                          Đúng thiết kế thì LUÔN rỗng; khác rỗng là đã có rò chéo tenant.
      `su_kien_mo_coi`  — `don_id` trỏ vào đơn không còn tồn tại.
      `khong_khop`      — sự kiện không khớp được đơn nào (mã vận đơn lạ / của tenant khác).
      `cho_nguoi_soat`  — sự kiện `can_soat=1` (NEEDS_REVIEW / AMBIGUOUS) chưa ai chốt.
      `ket_dinh`        — DLQ + đang chờ thử lại.
      `don_treo`        — đơn còn đang chạy mà KHÔNG có sự kiện webhook nào trong
                          `giay_gan_nhat` giây ⇒ ứng viên cho polling (W08).
      `don_khong_su_kien` — đơn đã gắn tài khoản hãng mà chưa từng có sự kiện nào.

    CSDL chưa migrate (thiếu cột mở rộng) thì trả phần đọc được và nói rõ phần bỏ qua ở
    `bo_qua` — KHÔNG nổ, và KHÔNG im lặng giả vờ đã đối chiếu đủ.
    """
    import time as _time
    tk = {"tenant_id": tenant_id, "giay_gan_nhat": giay_gan_nhat, "bo_qua": []}
    co = lambda c: cot_co("wh_su_kien", c)          # noqa: E731
    tk["khong_khop"] = [dict(r) for r in csdl.nhieu(
        "SELECT s.id sk_id, s.event_id, s.loi_cuoi FROM wh_su_kien s"
        " JOIN carrier_accounts c ON c.id=s.carrier_account_id"
        " WHERE c.tenant_id=? AND s.trang_thai='khong_khop' ORDER BY s.id DESC LIMIT ?",
        (tenant_id, gioi_han))]
    tk["ket_dinh"] = [dict(r) for r in csdl.nhieu(
        "SELECT s.id sk_id, s.event_id, s.trang_thai, s.so_lan_thu, s.loi_cuoi FROM wh_su_kien s"
        " JOIN carrier_accounts c ON c.id=s.carrier_account_id"
        " WHERE c.tenant_id=? AND s.trang_thai IN ('dlq','cho_thu_lai')"
        " ORDER BY s.id DESC LIMIT ?", (tenant_id, gioi_han))]

    if co("don_id"):
        tk["lech_tenant"] = [dict(r) for r in csdl.nhieu(
            "SELECT s.id sk_id, s.event_id, c.tenant_id tenant_account, d.tenant_id tenant_don"
            " FROM wh_su_kien s JOIN carrier_accounts c ON c.id=s.carrier_account_id"
            " JOIN don_hang d ON d.id=s.don_id"
            " WHERE c.tenant_id=? AND s.don_id IS NOT NULL AND d.tenant_id<>c.tenant_id LIMIT ?",
            (tenant_id, gioi_han))]
        tk["su_kien_mo_coi"] = [dict(r) for r in csdl.nhieu(
            "SELECT s.id sk_id, s.event_id, s.don_id FROM wh_su_kien s"
            " JOIN carrier_accounts c ON c.id=s.carrier_account_id"
            " WHERE c.tenant_id=? AND s.don_id IS NOT NULL"
            "   AND NOT EXISTS (SELECT 1 FROM don_hang d WHERE d.id=s.don_id) LIMIT ?",
            (tenant_id, gioi_han))]
    else:
        # Không có `don_id` thì KHÔNG kiểm được chéo tenant ở tầng sự kiện. Nói thẳng ra thay
        # vì trả danh sách rỗng — danh sách rỗng ở đây trùng với "đã kiểm, không sao".
        tk["lech_tenant"] = None
        tk["su_kien_mo_coi"] = None
        tk["bo_qua"].append("lech_tenant/su_kien_mo_coi: CSDL chưa có cột wh_su_kien.don_id")

    if co("can_soat"):
        tk["cho_nguoi_soat"] = [dict(r) for r in csdl.nhieu(
            "SELECT s.id sk_id, s.event_id, s.hang_ma_goc, s.trang_thai FROM wh_su_kien s"
            " JOIN carrier_accounts c ON c.id=s.carrier_account_id"
            " WHERE c.tenant_id=? AND s.can_soat=1 AND s.trang_thai NOT IN ('dlq','khong_khop')"
            " ORDER BY s.id DESC LIMIT ?", (tenant_id, gioi_han))]
    else:
        tk["cho_nguoi_soat"] = None
        tk["bo_qua"].append("cho_nguoi_soat: CSDL chưa có cột wh_su_kien.can_soat")

    nguong = _time.time() - giay_gan_nhat
    tk["don_treo"] = [dict(r) for r in csdl.nhieu(
        "SELECT d.id don_id, d.ma_van_don, d.trang_thai_giao,"
        "       (SELECT MAX(s.nhan_luc) FROM wh_su_kien s WHERE s.don_id=d.id) sk_gan_nhat"
        " FROM don_hang d WHERE d.tenant_id=? AND d.ma_van_don IS NOT NULL"
        f"   AND COALESCE(d.trang_thai_giao,'cho_lay') IN ({','.join('?' * len(DANG_CHAY))})"
        "   ORDER BY d.id LIMIT ?", (tenant_id, *DANG_CHAY, gioi_han))] \
        if co("don_id") else None
    if tk["don_treo"] is None:
        tk["bo_qua"].append("don_treo: CSDL chưa có cột wh_su_kien.don_id")
    else:
        tk["don_treo"] = [d for d in tk["don_treo"] if _cu_hon(d.get("sk_gan_nhat"), nguong)]

    tk["don_khong_su_kien"] = [dict(r) for r in csdl.nhieu(
        "SELECT d.id don_id, d.ma_van_don, d.carrier_account_id FROM don_hang d"
        " WHERE d.tenant_id=? AND d.carrier_account_id IS NOT NULL AND d.ma_van_don IS NOT NULL"
        + ("   AND NOT EXISTS (SELECT 1 FROM wh_su_kien s WHERE s.don_id=d.id)"
           if co("don_id") else "")
        + " LIMIT ?", (tenant_id, gioi_han))]
    if not co("don_id"):
        tk["bo_qua"].append("don_khong_su_kien: đếm thô, chưa loại được đơn đã có sự kiện")

    tk["bat_bien_tenant_dat"] = None if tk["lech_tenant"] is None else not tk["lech_tenant"]
    tk["can_polling"] = bool(tk["don_treo"] or tk["don_khong_su_kien"])
    return tk


def _cu_hon(moc_chuoi, nguong_epoch):
    """`csdl.bay_gio()` là 'YYYY-MM-DD HH:MM:SS+0700'. Không đọc được thì coi là CŨ (an toàn:
    thà đối chiếu thừa một đơn còn hơn bỏ sót một đơn không ai nhìn tới)."""
    if not moc_chuoi:
        return True
    import datetime as _dt
    try:
        t = _dt.datetime.strptime(str(moc_chuoi)[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return True
    return (t - _dt.datetime(1970, 1, 1)).total_seconds() - 7 * 3600 < nguong_epoch
