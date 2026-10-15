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


def tim_account_theo_webhook_ma(webhook_ma):
    return csdl.mot("SELECT * FROM carrier_accounts WHERE webhook_ma=? AND kich_hoat=1", (webhook_ma,))


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
    """
    if cot_co("wh_su_kien", "hang_moc_thoi_gian") and cot_co("wh_su_kien", "don_id"):
        r = csdl.mot("SELECT MAX(hang_moc_thoi_gian) m FROM wh_su_kien"
                     " WHERE don_id=? AND trang_thai='xong' AND hang_moc_thoi_gian IS NOT NULL",
                     (don_id,))
        if r and r["m"]:
            return r["m"]
    r = csdl.mot("SELECT MAX(chi_tiet) m FROM audit WHERE hanh_dong='webhook_moc_hang'"
                 " AND resource_type='don' AND resource_id=?", (str(don_id),))
    return (r["m"] if r else None) or None


def _ghi_watermark(don_id, moc, tenant_id):
    """Ghi mốc hãng vừa áp. `chi_tiet` CHỈ chứa chuỗi 14 chữ số để MAX() so được."""
    if moc:
        csdl.audit("webhook_moc_hang", f"don:{don_id}", moc, tenant_id=tenant_id)


# ============================================================================
# W06 — LƯU DẤU VẾT ÁNH XẠ
# ============================================================================
def luu_dau_vet(sk_id, qd, don_id=None, tenant_id=None):
    """Lưu mã gốc · mô tả gốc · sự kiện hãng gốc · nguồn tài liệu + phiên bản · độ tin cậy ánh xạ
    · nhãn soát · giờ nhận.

    Ghi vào CỘT khi CSDL đã migrate; LUÔN LUÔN ghi thêm một dòng audit, để trên CSDL chưa migrate
    vẫn không mất dấu vết nào. (Cột là nơi truy vấn nhanh; audit là nơi không thể mất.)
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
    moc = qd.su_kien_hang_goc.get("moc_hang") if isinstance(qd.su_kien_hang_goc, dict) else None
    for cot, gt in (("hang_ma_goc", None if qd.ma_goc is None else str(qd.ma_goc)),
                    ("hang_mo_ta_goc", qd.mo_ta_goc),
                    ("hang_su_kien_goc", json.dumps(qd.su_kien_hang_goc, ensure_ascii=False,
                                                    default=str) if qd.su_kien_hang_goc else None),
                    ("anh_xa_do_tin_cay", qd.do_tin_cay),
                    ("anh_xa_nguon", f"{qd.nguon_tai_lieu or ''} [{qd.phien_ban_tai_lieu}]"),
                    ("can_soat", 1 if qd.can_soat else 0),
                    ("hang_moc_thoi_gian", moc),
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
    sv = doc_su_kien_hang(tk, body)
    if sv is None:
        raise LoiVinhVien("payload không đọc được (không phải JSON/form hợp lệ của dạng nào đã biết)")
    if not sv["ma_van_don"] or sv["ma_trang_thai"] in (None, ""):
        raise LoiVinhVien("thiếu mã vận đơn hoặc mã trạng thái")

    # Payload cố khai tenant → GHI LẠI rồi BỎ QUA. tenant chỉ đến từ carrier_account.
    if sv.get("claim_tenant") is not None and str(sv["claim_tenant"]) != str(tk["tenant_id"]):
        csdl.audit("webhook_claim_tenant_bi_bo_qua", f"su_kien:{sk['id']}",
                   f"payload khai tenant={sv['claim_tenant']!r}, account thuộc tenant"
                   f"={tk['tenant_id']} — dùng tenant của account",
                   tenant_id=tk["tenant_id"], ket_qua="tu_choi")

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
    don = csdl.mot(
        "SELECT * FROM don_hang WHERE ma_van_don=? AND tenant_id=? AND carrier_account_id=?",
        (sv["ma_van_don"], tk["tenant_id"], tk["id"]))
    if not don:
        luu_dau_vet(sk["id"], qd, None, tk["tenant_id"])
        csdl.audit("webhook_khong_khop_don", f"su_kien:{sk['id']}",
                   f"mã vận đơn {sv['ma_van_don']} không thuộc tenant {tk['tenant_id']}"
                   f" / account {tk['id']}", tenant_id=tk["tenant_id"], ket_qua="tu_choi")
        return "khong_khop"  # lưu thô, đánh dấu không khớp — không đụng đơn của ai

    luu_dau_vet(sk["id"], qd, don["id"], tk["tenant_id"])

    if qd.trang_thai_ap is None:
        csdl.audit("webhook_can_soat" if qd.can_soat else "webhook_chi_ghi_nhan",
                   f"don:{don['id']}",
                   f"su_kien:{sk['id']} ma_goc={qd.ma_goc!r} nhan={qd.nhan}"
                   f" tin_cay={qd.do_tin_cay} — KHÔNG đổi trạng thái. {qd.ghi_chu}",
                   tenant_id=tk["tenant_id"], ket_qua="that_bai" if qd.can_soat else "thanh_cong")
        return "xong"

    # W05: chặn sự kiện đến muộn bằng MỐC CỦA HÃNG, TRƯỚC cả rank guard.
    # Rank guard một mình không chặn được ca "Delivered cũ đến sau Returning mới": hạng 5 < 6 nên
    # nó bị chặn, nhưng ca "Delivered cũ đến sau dang_giao mới" thì hạng 5 > 3 ⇒ lọt.
    moc = sv.get("moc_hang")
    if moc:
        wm = watermark(don["id"])
        if wm and moc < wm:
            csdl.audit("webhook_den_muon", f"don:{don['id']}",
                       f"su_kien:{sk['id']} moc_hang={moc} < moc đã áp={wm}"
                       f" — KHÔNG áp {qd.trang_thai_ap}",
                       tenant_id=tk["tenant_id"], ket_qua="tu_choi")
            return "xong"

    ap_dung, ly_do = don_hang.ap_trang_thai_giao(
        tk["tenant_id"], don["id"], qd.trang_thai_ap, f"webhook:{sk['id']}")
    if ap_dung and moc:
        _ghi_watermark(don["id"], moc, tk["tenant_id"])
    csdl.audit("webhook_cap_nhat_don", f"don:{don['id']}",
               f"su_kien:{sk['id']} loai={qd.trang_thai_ap} ap_dung={ap_dung} {ly_do}"
               f" ma_goc={qd.ma_goc!r} tin_cay={qd.do_tin_cay}", tenant_id=tk["tenant_id"])
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

    Quyền (`tenant.webhook.replay`) do tầng HTTP kiểm — hàm này KHÔNG tự cấp quyền. Nó thêm hai
    thứ mà tầng HTTP hiện chưa có: chặn chéo tenant một lần nữa, và trần số lần replay.
    Trả (ok, ly_do).
    """
    sk = csdl.mot("SELECT s.*, c.tenant_id t FROM wh_su_kien s JOIN carrier_accounts c"
                  " ON c.id=s.carrier_account_id WHERE s.id=?", (sk_id,))
    if not sk or sk["t"] != tenant_id:
        return False, "không có sự kiện này"
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
