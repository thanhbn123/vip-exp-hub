# G11 — Lớp QUAN SÁT (observability: khả năng nhìn thấy hệ đang làm gì) của VIP Express Hub.
# AG-05 DEVOPS sở hữu file này. Chỉ stdlib — không thêm thư viện ngoài (ràng buộc kiến trúc dự án).
#
# Bốn việc, cố ý tách rời nhau:
#   1. `che()` + `ghi()`  — log có cấu trúc, ĐÃ che bí mật trước khi ra khỏi tiến trình.
#   2. `suc_khoe()`       — tiến trình còn sống (HEALTH). Rẻ, không chạm CSDL.
#   3. `san_sang()`       — sẵn sàng nhận việc (READINESS). Đo thật: CSDL, schema, khóa, worker.
#   4. `metric()`         — số đếm lỗi / hàng đợi / webhook / worker để nhìn vào lúc có sự cố.
#
# ====== VÌ SAO HEALTH VÀ READINESS KHÔNG ĐƯỢC GỘP ======
# Gộp hai thứ này là một lần báo XANH khi thực ra chưa sẵn sàng. Tiến trình sống mà CSDL ở
# schema cũ hơn mã thì `server.chay()` còn chưa chạy nổi (nó `SystemExit(3)`); tiến trình sống
# mà không đọc được khóa mã hóa thì mọi lượt giải mã credentials sẽ nổ ở lượt dùng đầu tiên —
# tức là nổ trước mặt người dùng, không nổ ở cổng kiểm. Bộ cân tải (load balancer) cần
# READINESS để quyết định có đưa lưu lượng vào hay không; bộ giám sát tiến trình cần HEALTH để
# quyết định có khởi động lại hay không. Hai câu hỏi khác nhau, hai câu trả lời khác nhau.
#
# ====== §12.1 — THỨ DÙNG ĐỂ KIỂM CHỨNG PHẢI ĐỘC LẬP VỚI THỨ ĐƯỢC KIỂM CHỨNG ======
# Ca đã xảy ra thật trong vault chủ dự án: bước nghiệm thu của một bộ cài TỰ CHẠY HỘ bằng shell
# có sẵn quyền, nên LUÔN báo đạt, che mất việc bộ lập lịch không chạy nổi.
# Áp vào đây thành ba luật cứng của file này:
#   (a) `san_sang()` KHÔNG BAO GIỜ đọc giá trị đã nhớ sẵn. Mỗi lượt gọi là một lượt ĐO:
#       `SELECT MAX(phien_ban)` thật, `open().read()` khóa thật, hỏi thread worker thật.
#   (b) `san_sang()` KHÔNG tự mở/sửa cái nó đang kiểm. Không `makedirs`, không `migrate`,
#       không sinh khóa. Thiếu thì BÁO THIẾU. Cổng kiểm mà tự vá cái nó kiểm thì nó luôn xanh.
#   (c) Cổng kiểm của container gọi vào đây QUA HTTP từ MỘT TIẾN TRÌNH KHÁC (xem Dockerfile
#       HEALTHCHECK). Tiến trình tự khẳng định mình sống là lời khai, không phải phép đo.
import base64
import json
import os
import re
import sys
import threading
import time
import uuid

import cau_hinh

# ---------------------------------------------------------------------------
# DDL cho AG-00 cắm vào migration v8. Module này PHẢI chạy được khi bảng CHƯA tồn tại
# (xem `_co_bang`) — nếu không, lớp quan sát sẽ tự thành nguyên nhân sự cố mà nó định quan sát.
# ---------------------------------------------------------------------------
DDL_G11 = """
CREATE TABLE IF NOT EXISTS quan_sat_su_kien (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  luc TEXT NOT NULL,                 -- giờ địa phương VN kèm múi giờ (csdl.bay_gio)
  loai TEXT NOT NULL,                -- khoi_dong | san_sang_that_bai | trien_khai | dung
  muc TEXT NOT NULL DEFAULT 'tin',   -- tin | canh_bao | loi
  request_id TEXT,
  correlation_id TEXT,
  chi_tiet TEXT,                     -- JSON đã qua `che()`; CẤM chứa bí mật
  phien_ban_schema INTEGER,
  tien_trinh INTEGER                 -- PID, để dựng lại trình tự khi đối chiếu log máy chủ
);
CREATE INDEX IF NOT EXISTS ix_quan_sat_luc ON quan_sat_su_kien(luc);
CREATE INDEX IF NOT EXISTS ix_quan_sat_loai ON quan_sat_su_kien(loai, luc);
"""

TEN_BANG = "quan_sat_su_kien"

# ===========================================================================
# 1. CHE BÍ MẬT
# ===========================================================================
# DANH SÁCH TRẮNG, không phải danh sách đen. Câu hỏi phân biệt của §12.2:
# *quên một dòng thì kết quả là AN TOÀN hay HỎNG?*
#   - Danh sách đen (liệt kê thứ phải che): quên một tên ⇒ mật khẩu/token/số điện thoại khách
#     chảy vào log và nằm đó mãi. MẤT IM LẶNG, không ai thấy.
#   - Danh sách trắng (liệt kê thứ được qua): quên một tên ⇒ log hiện `***` ở chỗ đáng ra có
#     giá trị vô hại. HỎNG ỒN ÀO, nhìn log là thấy, thêm một dòng là xong.
# Đây đúng là ngoại lệ chính đáng mà §12.2 đã nêu sẵn: khi đang CHẶN THỨ NGUY HIỂM thì bỏ sót
# phải là AN TOÀN, và lúc đó danh sách trắng mới đúng.
TRUONG_CHO_PHEP = frozenset({
    # định danh kỹ thuật — không phải dữ liệu người
    "request_id", "correlation_id", "tenant_id", "user_id", "don_id", "sk_id", "batch_id",
    "carrier_account_id", "event_id", "key_id", "idem_key", "pid", "thread",
    # phân loại, trạng thái, kết quả
    "loai", "muc", "trang_thai", "trang_thai_giao", "ket_qua", "hanh_dong", "doi_tuong",
    "resource_type", "resource_id", "nguon", "chieu", "ma_chuan", "ma_goc_hang", "role",
    "platform_role", "ma_hang", "phien_ban_schema", "phien_ban", "vai_tro",
    # đo lường
    "ma_http", "method", "duong", "ms", "so_byte", "so_dong", "so_lan_thu", "so_luong",
    "qsize", "dang_xu_ly", "luc", "bat_dau", "ket_thuc", "het_gio", "cho_bao_lau_giay",
    # thông điệp đã do CHÍNH hệ sinh ra (không phải echo dữ liệu người dùng)
    "thong_diep", "loi", "ghi_chu", "ly_do",
})

# Lớp chặn THỨ HAI, đặt sau danh sách trắng chứ không thay nó: ngay cả trường được phép cũng
# bị quét lại theo HÌNH DẠNG giá trị. Vì sao cần hai lớp khi §12.2 nói "lọc một chỗ, không lọc
# hai chỗ": luật đó nói về hai lớp lọc CÙNG LOẠI chồng nhau (bản vá ở lớp này bị lớp kia làm vô
# hiệu). Ở đây hai lớp lọc theo HAI TIÊU CHÍ KHÁC NHAU — một theo TÊN trường, một theo HÌNH DẠNG
# giá trị — nên chúng không che nhau; `thong_diep` do hệ sinh vẫn có thể vô tình nối số điện
# thoại của khách vào, và chỉ lớp hình dạng bắt được ca đó.
MAU_NHAY_CAM = (
    # số điện thoại Việt Nam: 0 hoặc +84 rồi 8–10 số. Dùng lookaround để không ăn vào giữa
    # một chuỗi số dài hơn (mã vận đơn, idem_key) — che sai cũng là làm log mất tác dụng.
    (re.compile(r"(?<!\d)(?:\+?84|0)\d{8,10}(?!\d)"), "<sdt>"),
    # email
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<email>"),
    # bản mã credentials của dự án: v3$<key_id>$<nonce>$<ct>
    (re.compile(r"v\d+\$[A-Za-z0-9._-]+\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+"), "<ban_ma>"),
    # header Authorization
    (re.compile(r"(?i)\b(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), "<auth>"),
)

CHE = "***"
DAI_TOI_DA = 512          # một giá trị dài hơn chừng này bị cắt — log không phải chỗ chứa dữ liệu
SAU_TOI_DA = 6            # chặn JSON lồng vô hạn làm treo lượt ghi log


def _cat(s):
    s = str(s)
    return s if len(s) <= DAI_TOI_DA else s[:DAI_TOI_DA] + "...<cat>"


# Thẻ ngân hàng xử RIÊNG, không nằm trong `MAU_NHAY_CAM`, vì mẫu "13–19 chữ số" một mình là
# mẫu CHE QUÁ TAY: nó ăn luôn mã vận đơn và `idem_key` của chính dự án này (ca `a9` của
# `thu_quan_sat.py` bắt được thật — `VD0987654321234567890` biến thành `VD<the>`). Che sai cũng
# làm log mất tác dụng, nên ở đây dùng HAI chốt trước khi che:
#   1. không đứng liền sau chữ cái (loại `VD…`, `JT…`, `SPX…`),
#   2. qua được phép thử Luhn (mọi số thẻ thật đều qua Luhn).
# RỦI RO CÒN LẠI, ghi ra vì rủi ro không ghi là rủi ro bị bỏ quên: một mã số thuần chữ số 13–19
# ký tự KHÔNG đứng sau chữ cái mà tình cờ qua Luhn thì vẫn bị che — xác suất chừng 1/10. Hệ này
# không lưu số thẻ ở đâu (COD là `INTEGER` đồng, §16), nên đánh đổi nghiêng về CHE.
MAU_THE = re.compile(r"(?<![0-9A-Za-z])(\d[ -]?){12,18}\d(?![0-9A-Za-z])")


def _luhn(so: str) -> bool:
    tong, doi = 0, False
    for ch in reversed(so):
        n = ord(ch) - 48
        if doi:
            n *= 2
            if n > 9:
                n -= 9
        tong += n
        doi = not doi
    return tong % 10 == 0


def _the_hay_khong(m):
    tho = m.group(0)
    so = re.sub(r"[ -]", "", tho)
    if 13 <= len(so) <= 19 and _luhn(so):
        return "<the>"
    return tho


def che_chuoi(s):
    """Che theo HÌNH DẠNG giá trị. Cũng bỏ ký tự điều khiển: `\\n` trong giá trị do client gửi
    là đường CHÈN DÒNG LOG GIẢ (log injection) — một dòng giả trong log là một lần chẩn đoán
    đi sai hướng."""
    s = _cat(s)
    for mau, thay in MAU_NHAY_CAM:
        s = mau.sub(thay, s)
    s = MAU_THE.sub(_the_hay_khong, s)
    return re.sub(r"[\r\n\t\x00-\x08\x0b-\x1f\x7f]", " ", s)


def che(d, sau=0):
    """Trả bản ĐÃ CHE của `d`. Trường ngoài `TRUONG_CHO_PHEP` thành `***` (giữ lại TÊN trường
    để log vẫn nói được 'có trường này' mà không nói nó bằng gì)."""
    if sau > SAU_TOI_DA:
        return "<sau_qua>"
    if isinstance(d, dict):
        ra = {}
        for k, v in d.items():
            ten = str(k)
            if ten not in TRUONG_CHO_PHEP:
                ra[ten] = CHE
            else:
                ra[ten] = che(v, sau + 1)
        return ra
    if isinstance(d, (list, tuple)):
        return [che(v, sau + 1) for v in d[:50]]
    if isinstance(d, bool) or d is None:
        return d
    if isinstance(d, int):
        return d
    if isinstance(d, float):
        # Tiền trong dự án này là INTEGER đồng (SHARED_CONTRACTS §16). Thấy float ở tầng log thì
        # giữ nguyên để nhìn thấy mà sửa, không âm thầm làm tròn.
        return d
    return che_chuoi(d)


def quet_bi_mat(van_ban, bi_mats):
    """Tìm `bi_mats` trong `van_ban` ở BA DẠNG: thô · hex · base64.

    Vì sao ba dạng: một bí mật rò ra log hiếm khi rò nguyên văn. Nó đi qua `repr()` của bytes,
    qua `.hex()` của một digest, qua base64 của một payload webhook. Quét đúng một dạng rồi kết
    luận "không rò" là câu "0 lỗi" vượt phạm vi mà §12.1 luật 5 cấm.

    PHẠM VI phép đo này (nói ra để không ai suy rộng): nó chỉ bắt được bí mật mà NGƯỜI GỌI ĐƯA
    VÀO `bi_mats`. Nó KHÔNG phát hiện bí mật mà bộ thử không biết, không phát hiện bí mật đã bị
    mã hóa/nén/ký, và không phát hiện rò rỉ qua kênh khác (stderr của thư viện, core dump,
    tên file tạm). Trả về danh sách `(bi_mat, dang)` — rỗng nghĩa là không thấy TRONG phạm vi đó.
    """
    thay = []
    thap = van_ban.lower() if isinstance(van_ban, str) else van_ban.decode("utf-8", "replace").lower()
    for bm in bi_mats:
        if not bm:
            continue
        tho = bm if isinstance(bm, str) else bm.decode("utf-8", "replace")
        b = tho.encode()
        dang = {
            "tho": tho,
            "hex": b.hex(),
            "base64": base64.b64encode(b).decode(),
            "base64_khong_dem": base64.b64encode(b).decode().rstrip("="),
            "base64url": base64.urlsafe_b64encode(b).decode().rstrip("="),
        }
        for ten, chuoi in dang.items():
            if len(chuoi) < 6:      # chuỗi quá ngắn thì trùng ngẫu nhiên, báo là báo nhiễu
                continue
            if chuoi.lower() in thap:
                thay.append((tho, ten))
    return thay


# ===========================================================================
# 2. LOG CÓ CẤU TRÚC + REQUEST ID / CORRELATION ID
# ===========================================================================
_ngu_canh = threading.local()
MAU_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _id_sach(tho):
    """ID do client gửi là DỮ LIỆU KHÔNG TIN ĐƯỢC. Không khớp mẫu thì BỎ và tự sinh — không
    'làm sạch rồi dùng', vì chuỗi đã bị cắt gọt không còn truy vết được sang hệ bên kia."""
    if tho and MAU_ID.match(str(tho).strip()):
        return str(tho).strip()
    return None


def bat_dau_yeu_cau(headers=None, request_id=None, correlation_id=None):
    """Mở ngữ cảnh quan sát cho một lượt yêu cầu. Trả `(request_id, correlation_id)`.

    `request_id`    — định danh của ĐÚNG lượt này, luôn do hệ sinh.
    `correlation_id`— định danh của cả CHUỖI việc, nhận từ bên gọi nếu có (`X-Correlation-Id`)
                      để nối được một việc đi qua nhiều dịch vụ. Không có thì bằng request_id.
    """
    h = {str(k).lower(): v for k, v in (headers or {}).items()}
    rid = _id_sach(request_id) or uuid.uuid4().hex[:16]
    cid = (_id_sach(correlation_id)
           or _id_sach(h.get("x-correlation-id"))
           or _id_sach(h.get("x-request-id"))
           or rid)
    _ngu_canh.rid = rid
    _ngu_canh.cid = cid
    _ngu_canh.bat_dau = time.time()
    return rid, cid


def ket_thuc_yeu_cau():
    """Trả số milli giây của lượt vừa rồi, rồi xoá ngữ cảnh. Xoá là bắt buộc: thread của
    `ThreadingHTTPServer` được dùng lại, ID sót lại sẽ gán sai cho lượt sau."""
    bd = getattr(_ngu_canh, "bat_dau", None)
    ms = None if bd is None else int((time.time() - bd) * 1000)
    _ngu_canh.rid = None
    _ngu_canh.cid = None
    _ngu_canh.bat_dau = None
    return ms


def id_hien_tai():
    return getattr(_ngu_canh, "rid", None), getattr(_ngu_canh, "cid", None)


_khoa_log = threading.Lock()
_luong_log = None           # None = dùng sys.stderr lúc ghi (đổi được trong bộ thử)
DONG_LOG_TOI_DA = 8 * 1024  # một dòng log dài hơn chừng này làm hỏng mọi bộ đọc log theo dòng


def dat_luong_log(luong):
    """Đổi nơi ghi log (bộ thử dùng StringIO). None = về `sys.stderr`."""
    global _luong_log
    _luong_log = luong
    return luong


def ghi(loai, muc="tin", **truong):
    """Ghi MỘT dòng JSON. Mọi trường đi qua `che()` trước khi ra khỏi tiến trình.

    Một dòng một JSON (JSONL) chứ không phải JSON nhiều dòng: log bị cắt giữa dòng vẫn đọc được
    những dòng trước, và `grep` vẫn dùng được. Khoá `_khoa_log` để hai thread không xen dòng vào
    nhau — dòng bị xen là dòng không parse nổi, tức là mất im lặng đúng lúc cần nó nhất.
    """
    rid, cid = id_hien_tai()
    ban = {
        "luc": _bay_gio(),
        "loai": str(loai)[:64],
        "muc": muc if muc in ("tin", "canh_bao", "loi") else "tin",
        "request_id": rid,
        "correlation_id": cid,
        "pid": os.getpid(),
        "thread": threading.current_thread().name,
    }
    ban.update(che(truong))
    try:
        dong = json.dumps(ban, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        dong = json.dumps({"luc": ban["luc"], "loai": "log_khong_tuan_tu_hoa_duoc",
                           "muc": "loi", "request_id": rid}, ensure_ascii=False)
    if len(dong) > DONG_LOG_TOI_DA:
        dong = dong[:DONG_LOG_TOI_DA - 20] + '"...<cat>"}'
    luong = _luong_log if _luong_log is not None else sys.stderr
    with _khoa_log:
        luong.write(dong + "\n")
        try:
            luong.flush()
        except Exception:
            # Không nuốt im lặng (§12.2): flush hỏng thì nói ra, nhưng KHÔNG để việc ghi log làm
            # chết lượt yêu cầu nghiệp vụ. Ghi thẳng stderr vì chính kênh log đang hỏng.
            sys.stderr.write("[quan_sat] flush log thất bại\n")
    return dong


def _bay_gio():
    """Giờ địa phương VN KÈM múi giờ. §12.2: mốc thời gian không nhãn múi giờ đã làm vault chủ
    dự án kết luận ngược ba lần trong một ngày."""
    try:
        import csdl
        return csdl.bay_gio()
    except Exception:
        from datetime import datetime, timedelta, timezone
        return datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d %H:%M:%S%z")


# ===========================================================================
# 3. HEALTH — tiến trình còn sống
# ===========================================================================
_khoi_dong_luc = time.time()


def suc_khoe():
    """HEALTH. Rẻ, KHÔNG chạm CSDL, KHÔNG chạm đĩa.

    Nó trả lời đúng một câu: *tiến trình này còn nhận và trả được một yêu cầu HTTP không?*
    Nó KHÔNG trả lời được 'hệ dùng được chưa' — đó là `san_sang()`. Dùng cái này cho bộ giám sát
    tiến trình (restart policy); dùng `san_sang()` cho bộ cân tải.
    """
    return {
        "ok": True,
        "song_giay": int(time.time() - _khoi_dong_luc),
        "pid": os.getpid(),
        "phien_ban_ma": PHIEN_BAN_MA,
        # Nói rõ phạm vi NGAY TRONG kết quả, để người đọc dashboard không suy rộng.
        "pham_vi": "chi do tien trinh con song; KHONG do CSDL/khoa/worker — xem /san-sang",
    }


PHIEN_BAN_MA = os.environ.get("VIP_HUB_PHIEN_BAN", "0.3-SaaS")


# ===========================================================================
# 4. READINESS — sẵn sàng nhận việc
# ===========================================================================
def _kiem_csdl():
    """CSDL mở được và đọc được thật. Phép đo là MỘT TRUY VẤN THẬT, không phải `os.path.exists`:
    file có mặt mà hỏng vẫn là file có mặt."""
    try:
        import csdl
        r = csdl.mot("SELECT COUNT(*) n FROM sqlite_master WHERE type='table'")
        return True, {"so_bang": r["n"] if r else 0}
    except Exception as e:
        return False, {"loi": che_chuoi(repr(e))}


def _kiem_schema():
    """Schema trong CSDL phải BẰNG phiên bản mã cần. `server.chay()` đã tự `SystemExit(3)` khi
    CSDL cũ hơn mã — cổng này nói ra điều đó TRƯỚC khi nhận lưu lượng, thay vì để container
    khởi động lại vòng quanh mà không ai biết vì sao."""
    try:
        import csdl
        pb = csdl.phien_ban_hien_tai()
        can = csdl.PHIEN_BAN_SCHEMA
        if pb < can:
            return False, {"phien_ban": pb, "can": can,
                           "loi": "CSDL cu hon ma — phai chay migration truoc"}
        if pb > can:
            # Mã cũ hơn CSDL: cột mới chưa biết thì chịu được, nhưng ràng buộc mới thì không.
            # Không tự nhận an toàn — báo CẢNH BÁO và vẫn cho qua, ghi rõ là chưa đo.
            return True, {"phien_ban": pb, "can": can,
                          "canh_bao": "CSDL moi hon ma — tinh tuong thich CHUA DUOC DO"}
        return True, {"phien_ban": pb, "can": can}
    except Exception as e:
        return False, {"loi": che_chuoi(repr(e))}


def _kiem_khoa():
    """Khóa mã hóa ĐỌC ĐƯỢC và ĐỦ 32 byte cho AES-256.

    Phép đo là `lay_khoa()` thật qua `secret_provider` — không phải `os.path.exists`. Khóa 31
    byte vẫn là một file tồn tại, và nó sẽ nổ ở lượt giải mã credentials ĐẦU TIÊN, tức là trước
    mặt người dùng. CẤM tự sinh khóa ở đây (§12.1 luật (b)): cổng kiểm mà tự vá cái nó kiểm thì
    nó luôn xanh. `LocalSecretProvider` có tự sinh khóa khi thiếu — nên ở đây CHỈ gọi
    `danh_sach_key_id()`/`lay_khoa()` sau khi đã thấy có khóa, và báo thiếu nếu chưa có.
    """
    try:
        import secret_provider
        ncc = secret_provider.nha_cung_cap()
        ds = ncc.danh_sach_key_id()
        if not ds:
            return False, {"loi": "chua co khoa nao — chay buoc khoi tao khoa truoc"}
        # KHÔNG gọi `khoa_hien_hanh()` khi con trỏ 'hien-hanh' còn thiếu: hàm đó gọi
        # `_dam_bao_co_khoa()` và sẽ TỰ GHI con trỏ. Cổng kiểm mà tự sửa cái nó kiểm thì lượt
        # kiểm thứ hai luôn xanh và không ai còn biết lượt đầu đã hỏng (§12.1 luật (b)).
        tro = os.path.join(getattr(ncc, "thu_muc", ""), secret_provider.TEN_FILE_TRO)
        if not os.path.exists(tro):
            return False, {"so_khoa": len(ds),
                           "loi": "thieu con tro khoa hien hanh 'hien-hanh' — KHONG tu tao o cong kiem"}
        key_id, khoa = ncc.khoa_hien_hanh()
        if not isinstance(khoa, (bytes, bytearray)) or len(khoa) != 32:
            return False, {"key_id": key_id, "loi": f"khoa dai {len(khoa)} byte, can 32"}
        # KHÔNG trả `khoa` ra ngoài, kể cả độ dài-và-đầu-cuối. Chỉ key_id và số khóa.
        return True, {"key_id": key_id, "so_khoa": len(ds)}
    except Exception as e:
        return False, {"loi": che_chuoi(repr(e))}


def _kiem_worker():
    """Worker webhook còn sống. `webhook.py` do AG-03 sở hữu nên ở đây chỉ ĐỌC, và đọc PHÒNG XA:
    thiếu thuộc tính thì báo 'chua do duoc', không đoán là tốt."""
    try:
        import webhook
        w = getattr(webhook, "_worker", None)
        if w is None:
            return False, {"loi": "worker chua khoi dong"}
        song = bool(w.is_alive())
        hq = getattr(webhook, "_hang_doi", None)
        ct = {"song": song, "ten": w.name}
        if hq is not None:
            ct["qsize"] = hq.qsize()
            ct["dang_xu_ly"] = getattr(webhook, "_dang_xu_ly", None)
        else:
            ct["ghi_chu"] = "khong doc duoc hang doi — CHUA DO"
        return song, ct
    except Exception as e:
        return False, {"loi": che_chuoi(repr(e))}


def _kiem_thu_muc_du_lieu():
    """Thư mục dữ liệu phải GHI ĐƯỢC. Container chạy user không phải root rất hay dính đúng chỗ
    này, và nó hỏng lúc GHI chứ không lúc khởi động — tức là hỏng sau khi đã báo xanh."""
    tm = cau_hinh.THU_MUC_DU_LIEU
    if not os.path.isdir(tm):
        return False, {"loi": "thu muc du lieu khong ton tai"}
    if not os.access(tm, os.W_OK | os.X_OK):
        return False, {"loi": "thu muc du lieu KHONG ghi duoc"}
    return True, {}


KIEM = (
    ("thu_muc_du_lieu", _kiem_thu_muc_du_lieu),
    ("csdl", _kiem_csdl),
    ("schema", _kiem_schema),
    ("khoa", _kiem_khoa),
    ("worker", _kiem_worker),
)


def san_sang(bo_qua=()):
    """READINESS. Chạy MỌI phép kiểm (không ngắn mạch) rồi mới kết luận.

    Vì sao không ngắn mạch ở cái hỏng đầu tiên: một lượt kiểm chỉ nói được 'hỏng ở CSDL' thì
    người sửa phải chạy lại cổng kiểm sau mỗi lần vá, mà mỗi lượt chạy lại là một lượt chẩn đoán
    mới. Chạy hết và trả hết thì sửa được một lượt.

    `bo_qua` là tên phép kiểm cố ý bỏ, và lượt bỏ đó ĐƯỢC GHI RA trong kết quả — rủi ro cố ý bỏ
    qua phải ghi ra, rủi ro không ghi là rủi ro bị bỏ quên.
    """
    ra = {"ok": True, "kiem": {}, "bo_qua": list(bo_qua), "luc": _bay_gio(),
          "phien_ban_ma": PHIEN_BAN_MA}
    for ten, ham in KIEM:
        if ten in bo_qua:
            ra["kiem"][ten] = {"ok": None, "ghi_chu": "CO Y BO QUA — khong phai da dat"}
            continue
        try:
            ok, ct = ham()
        except Exception as e:
            ok, ct = False, {"loi": che_chuoi(repr(e))}
        ra["kiem"][ten] = dict(ct, ok=bool(ok))
        if not ok:
            ra["ok"] = False
    ra["pham_vi"] = ("do: thu muc ghi duoc, CSDL mo duoc, phien ban schema, khoa doc duoc, "
                    "worker webhook song. NGOAI pham vi: ket noi hang van chuyen, DNS, HTTPS, "
                    "dung luong dia, do tre CSDL, tinh dung cua du lieu nghiep vu")
    return ra


# ===========================================================================
# 5. METRIC
# ===========================================================================
_khoa_dem = threading.Lock()
_dem = {}
_dem_tu = time.time()


def cong(ten, so=1):
    """Cộng một bộ đếm trong bộ nhớ TIẾN TRÌNH NÀY.

    PHẠM VI phải nói ra, vì chính kiểu quên phạm vi này đã thành rủi ro R-a của dự án (trần rate
    limit sống trong bộ nhớ một tiến trình): số đếm ở đây MẤT khi khởi động lại và KHÔNG gộp
    giữa nhiều tiến trình. Nhiều worker thì mỗi worker một bộ số khác nhau. Muốn số cộng dồn
    thật thì phải có kho ngoài — CHƯA LÀM, ghi ở G11_FINAL_REPORT.
    """
    with _khoa_dem:
        _dem[ten] = _dem.get(ten, 0) + so
        return _dem[ten]


def dat_lai_dem():
    global _dem_tu
    with _khoa_dem:
        _dem.clear()
        _dem_tu = time.time()


def metric():
    """Ảnh số đếm + trạng thái hàng đợi/worker tại thời điểm gọi."""
    with _khoa_dem:
        so = dict(_dem)
    ok_w, ct_w = _kiem_worker()
    ra = {
        "luc": _bay_gio(),
        "pid": os.getpid(),
        "song_giay": int(time.time() - _khoi_dong_luc),
        "dem_tu_giay_truoc": int(time.time() - _dem_tu),
        "dem": so,
        "worker_webhook": dict(ct_w, ok=ok_w),
        "pham_vi": ("so dem CHI cua tien trinh PID nay, MAT khi khoi dong lai, KHONG gop giua "
                   "nhieu tien trinh"),
    }
    try:
        import csdl
        if _co_bang("wh_su_kien"):
            r = csdl.mot("SELECT COUNT(*) n FROM wh_su_kien WHERE trang_thai='dlq'")
            ra["wh_dlq"] = r["n"] if r else None
            r = csdl.mot("SELECT COUNT(*) n FROM wh_su_kien WHERE trang_thai='cho_thu_lai'")
            ra["wh_cho_thu_lai"] = r["n"] if r else None
        else:
            ra["wh_dlq"] = None
            ra["ghi_chu_bang"] = "bang wh_su_kien CHUA CO — chua chay migration"
    except Exception as e:
        ra["ghi_chu_bang"] = che_chuoi(repr(e))
    return ra


def _co_bang(ten):
    try:
        import csdl
        return csdl.mot("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (ten,)) is not None
    except Exception:
        return False


def ghi_su_kien(loai, muc="tin", **chi_tiet):
    """Ghi một mốc vận hành vào CSDL *nếu* bảng đã có. Bảng chưa có thì CHỈ ghi log và nói rõ —
    lớp quan sát không được tự thành nguyên nhân sự cố mà nó định quan sát.
    Trả `True` nếu đã ghi vào CSDL, `False` nếu chỉ ghi log."""
    ghi(loai, muc=muc, **chi_tiet)
    if not _co_bang(TEN_BANG):
        return False
    try:
        import csdl
        rid, cid = id_hien_tai()
        csdl.ghi(
            f"INSERT INTO {TEN_BANG} (luc, loai, muc, request_id, correlation_id, chi_tiet,"
            " phien_ban_schema, tien_trinh) VALUES (?,?,?,?,?,?,?,?)",
            (csdl.bay_gio(), str(loai)[:64], muc, rid, cid,
             json.dumps(che(chi_tiet), ensure_ascii=False, default=str)[:4000],
             csdl.phien_ban_hien_tai(), os.getpid()))
        return True
    except Exception as e:
        ghi("ghi_su_kien_that_bai", muc="canh_bao", loi=che_chuoi(repr(e)))
        return False


# ===========================================================================
# 6. CLI — để runbook và Dockerfile gọi được mà không cần viết Python tại chỗ
# ===========================================================================
def _main(argv):
    viec = argv[1] if len(argv) > 1 else "san-sang"
    if viec == "suc-khoe":
        print(json.dumps(suc_khoe(), ensure_ascii=False, indent=2))
        return 0
    if viec == "san-sang":
        kq = san_sang()
        print(json.dumps(kq, ensure_ascii=False, indent=2))
        return 0 if kq["ok"] else 1
    if viec == "metric":
        print(json.dumps(metric(), ensure_ascii=False, indent=2))
        return 0
    if viec == "ddl":
        print(DDL_G11)
        return 0
    sys.stderr.write("dung: python3 app/quan_sat.py [suc-khoe|san-sang|metric|ddl]\n")
    return 2


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    raise SystemExit(_main(sys.argv))
