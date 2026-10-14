# GIỚI HẠN TẦN SUẤT (rate limiting) + HẠN MỨC NHẬP FILE (import quota) — AG-01.
#
# Hai việc khác nhau nhưng cùng một họ ("chặn thứ dùng quá nhiều"), nên để cùng một file để
# chỉ có MỘT chỗ quyết định chặn (CLAUDE.md §19.4: "một chỗ quyết định xoá" — ở đây là
# "một chỗ quyết định chặn"). Hai phần tách rõ bằng tiêu đề, không dùng chung trạng thái.
#
#   PHẦN A — S04: giới hạn tần suất theo IP + định danh tài khoản + tenant + endpoint.
#   PHẦN B — S05: hạn mức nhập file (số đơn nháp/tháng, dung lượng, số dòng, số file/giờ).
#
# ---------------------------------------------------------------------------------------
# LUẬT THIẾT KẾ (ghi ra để lần sau thêm endpoint thì không phải nghĩ lại)
#
# 1. **Danh sách ĐEN, không danh sách trắng** (CLAUDE.md §12.2). Endpoint nào KHÔNG có trong
#    `CHINH_SACH` vẫn bị áp `LUAT_MAC_DINH`. Câu hỏi phân biệt: *quên một dòng thì kết quả là
#    an toàn hay hỏng?* Nếu endpoint lạ = không giới hạn, thì quên một dòng là **mở toang** một
#    cửa — đúng cái lỗi đã dính 6 lần ngày 30/08. Nên mặc định là CÓ chặn (rộng tay), và các
#    endpoint nhạy cảm được siết thêm.
#
# 2. **KHÔNG tin `X-Forwarded-For` vô điều kiện.** Mặc định `PROXY_TIN_CAY` RỖNG → chỉ dùng địa
#    chỉ TCP thật (`client_address[0]`). Tin header khi chưa có proxy nghĩa là bất kỳ ai cũng tự
#    khai IP của mình → giới hạn theo IP thành vô nghĩa, mà không có gì báo lỗi.
#
# 3. **Không chỉ dựa vào dữ liệu frontend tự khai.** `tenant_id` và `dinh_danh` phải lấy từ
#    `bao_mat.NguCanh` (phiên đã xác thực), KHÔNG lấy từ body/query. Với đường vô danh
#    (đăng nhập, quên mật khẩu) thì `dinh_danh` là tên đăng nhập người gửi tự khai — đó là lý do
#    luật theo `dinh_danh` LUÔN đi kèm một luật theo `ip`: khai tên khác thì vẫn đụng trần IP.
#
# 4. **Kiểm hết rồi mới ghi nhận.** Một yêu cầu bị chặn ở chiều nào thì KHÔNG cộng lượt ở chiều
#    nào — nếu không, kẻ bị chặn vẫn đẩy được trần của người khác lên (tự gây DoS cho nạn nhân).
#
# ---------------------------------------------------------------------------------------
# GIỚI HẠN CỦA PHẦN A — ĐỌC TRƯỚC KHI TIN (CLAUDE.md §12.1 luật 3)
#
#   - Trạng thái nằm trong **bộ nhớ tiến trình**. Khởi động lại máy chủ là **mất sạch** bộ đếm:
#     ngay sau khi restart, mọi trần đều về 0. Đây là cửa lách THẬT, không phải lý thuyết.
#   - **Nhiều tiến trình KHÔNG dùng chung** bộ đếm. Chạy 4 worker thì trần thực tế là 4 lần trần
#     khai báo. Hiện `app/server.py` là `ThreadingHTTPServer` một tiến trình nên đúng, nhưng
#     ngày nào chuyển sang nhiều tiến trình / nhiều máy thì PHẢI đổi sang kho dùng chung
#     (Redis, hoặc một bảng CSDL có UPDATE điều kiện như PHẦN B đang làm).
#   - Vì vậy phần này chặn **lạm dụng tự động** (dò mật khẩu, spam quên-mật-khẩu), KHÔNG chặn
#     được **tấn công phân tán** nhiều IP, và không thay cho WAF/gateway.
#   - PHẦN B (hạn mức nhập) thì KHÁC: nó đếm trong CSDL nên sống qua restart và dùng chung giữa
#     các tiến trình. Hai phần cố ý khác nhau vì hậu quả khác nhau: mất bộ đếm tần suất là mất
#     một lớp chống dò; mất bộ đếm hạn mức là tenant dùng quá gói mà không ai biết.
import ipaddress
import os
import threading
import time
from collections import OrderedDict, deque

import csdl

# =======================================================================================
# PHẦN A — GIỚI HẠN TẦN SUẤT
# =======================================================================================

# --- A.1 Trusted proxy -----------------------------------------------------------------
# Danh sách IP/CIDR của proxy được tin, phân tách bằng dấu phẩy.
# MẶC ĐỊNH RỖNG = KHÔNG TIN AI → luôn dùng địa chỉ TCP thật.
PROXY_TIN_CAY_THO = os.environ.get("VIP_HUB_PROXY_TIN_CAY", "").strip()
TIEU_DE_CHUYEN_TIEP = os.environ.get("VIP_HUB_PROXY_HEADER", "x-forwarded-for").lower()


def _doc_mang(tho: str):
    ra = []
    for phan in tho.split(","):
        phan = phan.strip()
        if not phan:
            continue
        try:
            ra.append(ipaddress.ip_network(phan, strict=False))
        except ValueError:
            # Cấu hình sai thì NÓI RA, không im lặng coi như rỗng (im lặng = tưởng đã tin proxy
            # mà thực ra không, hoặc ngược lại). Không ném lỗi để một dòng sai không chết cả hệ.
            import sys
            sys.stderr.write(f"[gioi_han] CẢNH BÁO: không hiểu dải proxy {phan!r} — BỎ QUA dải này\n")
    return tuple(ra)


PROXY_TIN_CAY = _doc_mang(PROXY_TIN_CAY_THO)


def _la_proxy_tin_cay(ip: str) -> bool:
    if not PROXY_TIN_CAY:
        return False
    try:
        d = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(d in m for m in PROXY_TIN_CAY)


def dia_chi_that(dia_chi_tcp: str, headers=None) -> str:
    """IP dùng để tính giới hạn.

    - `PROXY_TIN_CAY` rỗng (mặc định) → **luôn** trả địa chỉ TCP, bỏ qua mọi header.
    - Địa chỉ TCP không nằm trong `PROXY_TIN_CAY` → bỏ qua header (kẻ gửi không đi qua proxy
      của ta thì header của nó là dữ liệu tự khai).
    - Đi qua proxy tin cậy → đọc `X-Forwarded-For`, lấy phần tử **phải nhất mà KHÔNG phải proxy
      tin cậy**. Lấy phần tử trái nhất là sai: client tự thêm được một IP giả vào đầu chuỗi.

    `headers` là dict đã hạ chữ thường (server.py có sẵn `_headers_thuong()`).
    """
    dia_chi_tcp = (dia_chi_tcp or "").strip()
    if not headers or not _la_proxy_tin_cay(dia_chi_tcp):
        return dia_chi_tcp or "khong-ro"
    tho = headers.get(TIEU_DE_CHUYEN_TIEP) or ""
    chuoi = [x.strip() for x in tho.split(",") if x.strip()]
    for ip in reversed(chuoi):
        ip = ip.split("%")[0]
        if ip.startswith("[") and "]" in ip:            # [2001:db8::1]:443
            ip = ip[1:ip.index("]")]
        elif ip.count(":") == 1:                        # 1.2.3.4:5678
            ip = ip.split(":")[0]
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            continue
        if not _la_proxy_tin_cay(ip):
            return ip
    return dia_chi_tcp or "khong-ro"


# --- A.2 Chính sách --------------------------------------------------------------------
class Luat:
    """Một luật = một chiều đếm + trần + cửa sổ (+ thời gian phạt khi vượt).

    `chieu` ∈ 'ip' | 'dinh_danh' | 'tenant'. `chan_giay` > 0 thì vượt trần là bị chặn hẳn trong
    `chan_giay` giây, kể cả khi cửa sổ đã trôi — dùng cho đăng nhập để dò mật khẩu đắt hơn.
    """

    __slots__ = ("chieu", "so_lan", "cua_so_giay", "chan_giay")

    def __init__(self, chieu, so_lan, cua_so_giay, chan_giay=0):
        if chieu not in ("ip", "dinh_danh", "tenant"):
            raise ValueError(f"chiều giới hạn không hợp lệ: {chieu!r}")
        if so_lan < 1 or cua_so_giay <= 0:
            raise ValueError("so_lan phải ≥ 1 và cua_so_giay phải > 0")
        self.chieu, self.so_lan = chieu, int(so_lan)
        self.cua_so_giay, self.chan_giay = float(cua_so_giay), float(chan_giay)

    def __repr__(self):
        return f"Luat({self.chieu},{self.so_lan}/{self.cua_so_giay:g}s,chan={self.chan_giay:g}s)"


# Trần mặc định cho MỌI endpoint chưa khai riêng (xem LUẬT THIẾT KẾ số 1).
# Rộng tay có chủ đích: nó chỉ để chặn vòng lặp điên, không để chặn người dùng thật.
LUAT_MAC_DINH = (Luat("ip", 600, 60), Luat("dinh_danh", 600, 60))

# Endpoint nhạy cảm. Tên endpoint là **nhãn logic** do người gọi truyền vào, không phải đường URL
# — để đổi URL không làm mất giới hạn im lặng.
CHINH_SACH = {
    # --- đường VÔ DANH (chưa đăng nhập): siết chặt nhất ---
    # 5 lần sai/tài khoản/5 phút rồi chặn 15 phút. Khớp với cau_hinh.KHOA_SAU_SO_LAN_SAI=5 và
    # KHOA_TAM_PHUT=15 để hai lớp (khóa tạm trong CSDL + giới hạn tần suất) không đánh nhau.
    "auth.dang_nhap": (Luat("ip", 20, 300), Luat("dinh_danh", 5, 300, chan_giay=900)),
    # Quên mật khẩu: đây là cửa gửi thư/sinh token. Spam được là cửa quấy rối người thật.
    "auth.quen_mat_khau": (Luat("ip", 5, 900, chan_giay=900), Luat("dinh_danh", 3, 3600, chan_giay=1800)),
    # Đặt lại mật khẩu: token 32 byte không dò nổi, nhưng vẫn chặn để lượt thử không thành
    # đường làm kiệt máy bằng PBKDF2 200k vòng mỗi lượt.
    "auth.dat_lai_mat_khau": (Luat("ip", 10, 900, chan_giay=900),),

    # --- đường ĐÃ đăng nhập, nhạy cảm ---
    "auth.doi_mat_khau": (Luat("dinh_danh", 10, 900),),
    "membership.tao": (Luat("tenant", 30, 3600), Luat("dinh_danh", 30, 3600)),
    "membership.sua": (Luat("tenant", 60, 3600), Luat("dinh_danh", 60, 3600)),
    "tai_khoan_hang.quan_ly": (Luat("tenant", 30, 3600), Luat("dinh_danh", 30, 3600)),
    "khoa.xoay": (Luat("dinh_danh", 3, 3600), Luat("ip", 5, 3600)),
    "import.upload": (Luat("tenant", 30, 3600), Luat("dinh_danh", 30, 3600)),
    "import.duyet": (Luat("tenant", 60, 3600), Luat("dinh_danh", 60, 3600)),
    "platform.quan_tri": (Luat("dinh_danh", 120, 60), Luat("ip", 240, 60)),
    "ai.goi": (Luat("tenant", 120, 60), Luat("dinh_danh", 120, 60)),
}


def luat_cua(endpoint: str):
    return CHINH_SACH.get(endpoint, LUAT_MAC_DINH)


# --- A.3 Trạng thái --------------------------------------------------------------------
_khoa = threading.Lock()
# khoa_bucket -> deque[mốc thời gian]. OrderedDict để dọn được theo thứ tự chạm gần nhất.
_lan: "OrderedDict[str, deque]" = OrderedDict()
_chan_den = {}                     # khoa_bucket -> mốc hết chặn
TOI_DA_KHOA = int(os.environ.get("VIP_HUB_GIOI_HAN_TOI_DA_KHOA", "50000"))


class KetQuaGioiHan:
    """Kết quả một lượt kiểm.

    `cho_phep` False thì `cho_bao_lau` là số giây phải chờ (đã làm tròn lên) — đưa thẳng vào
    header `Retry-After`. `con_lai` là số lượt còn lại của chiều CHẬT NHẤT.
    """

    __slots__ = ("cho_phep", "con_lai", "cho_bao_lau", "chieu", "khoa", "luat")

    def __init__(self, cho_phep, con_lai, cho_bao_lau, chieu=None, khoa=None, luat=None):
        self.cho_phep, self.con_lai, self.cho_bao_lau = cho_phep, con_lai, cho_bao_lau
        self.chieu, self.khoa, self.luat = chieu, khoa, luat

    def bo_ba(self):
        """(cho_phep, con_lai, cho_bao_lau) — dạng bộ ba gọn cho người gọi."""
        return self.cho_phep, self.con_lai, self.cho_bao_lau

    def __repr__(self):
        return (f"KetQuaGioiHan(cho_phep={self.cho_phep}, con_lai={self.con_lai},"
                f" cho_bao_lau={self.cho_bao_lau}, chieu={self.chieu!r})")


def _gia_tri_chieu(chieu, ip, dinh_danh, tenant_id):
    if chieu == "ip":
        return ip or "khong-ro"
    if chieu == "dinh_danh":
        return None if dinh_danh in (None, "") else str(dinh_danh)
    return None if tenant_id in (None, "") else str(tenant_id)


def _don_neu_qua_dong(bay):
    """Giữ số khóa trong tầm. Dọn khóa đã trôi hết trước, hết cách thì bỏ khóa cũ nhất."""
    if len(_lan) <= TOI_DA_KHOA:
        return
    for k in list(_lan.keys()):
        d = _lan[k]
        if not d or d[-1] < bay - 3600:
            _lan.pop(k, None)
            _chan_den.pop(k, None)
        if len(_lan) <= TOI_DA_KHOA:
            return
    while len(_lan) > TOI_DA_KHOA:
        k, _ = _lan.popitem(last=False)
        _chan_den.pop(k, None)


def kiem(endpoint, ip=None, dinh_danh=None, tenant_id=None, ghi_nhan=True) -> KetQuaGioiHan:
    """Kiểm MỘT lượt gọi `endpoint`. Trả `KetQuaGioiHan`.

    Khóa bucket = `endpoint | chiều | giá trị` — nên giới hạn tách theo từng endpoint, và
    `tenant` tách theo từng tenant (cách ly: tenant A spam không ăn vào trần của tenant B).

    Chiều nào không có dữ liệu (ví dụ `dinh_danh=None` ở đường vô danh chưa biết tên) thì **bỏ
    qua chiều đó**, không coi là một bucket chung — gộp mọi người vô danh vào một bucket là tự
    biến giới hạn thành cửa để một người chặn tất cả.

    `ghi_nhan=False` chỉ xem trạng thái, không cộng lượt.
    """
    luats = luat_cua(endpoint)
    bay = time.monotonic()
    chat_nhat = None
    with _khoa:
        can_ghi = []
        for lt in luats:
            gt = _gia_tri_chieu(lt.chieu, ip, dinh_danh, tenant_id)
            if gt is None:
                continue
            k = f"{endpoint}|{lt.chieu}|{gt}"
            den = _chan_den.get(k)
            if den and den > bay:
                return KetQuaGioiHan(False, 0, int(den - bay) + 1, lt.chieu, k, lt)
            d = _lan.get(k)
            if d is None:
                d = _lan[k] = deque()
            else:
                _lan.move_to_end(k)
            moc = bay - lt.cua_so_giay
            while d and d[0] <= moc:
                d.popleft()
            if len(d) >= lt.so_lan:
                cho = int(d[0] + lt.cua_so_giay - bay) + 1
                if lt.chan_giay > 0:
                    _chan_den[k] = bay + lt.chan_giay
                    cho = int(lt.chan_giay) + 1
                return KetQuaGioiHan(False, 0, max(1, cho), lt.chieu, k, lt)
            con = lt.so_lan - len(d) - (1 if ghi_nhan else 0)
            if chat_nhat is None or con < chat_nhat[0]:
                chat_nhat = (con, lt.chieu, k, lt)
            can_ghi.append(d)
        # Chỉ ghi nhận khi MỌI chiều đều còn chỗ (xem LUẬT THIẾT KẾ số 4).
        if ghi_nhan:
            for d in can_ghi:
                d.append(bay)
        _don_neu_qua_dong(bay)
    if chat_nhat is None:
        return KetQuaGioiHan(True, -1, 0)      # -1 = không chiều nào áp được (thiếu dữ liệu)
    con, chieu, k, lt = chat_nhat
    return KetQuaGioiHan(True, max(0, con), 0, chieu, k, lt)


def kiem_yeu_cau(endpoint, dia_chi_tcp, headers=None, dinh_danh=None, tenant_id=None):
    """Bản tiện cho `server.py`: tự giải địa chỉ thật rồi gọi `kiem`.

    Đây là hàm AG-00 nên gọi — nó gộp luôn luật trusted proxy nên call site không có cơ hội
    quên (cùng lý do bốn hàm `ma_hoa_cred/...` gộp AAD, xem docs/MA_HOA.md).
    """
    return kiem(endpoint, ip=dia_chi_that(dia_chi_tcp, headers),
                dinh_danh=dinh_danh, tenant_id=tenant_id)


def dat_lai(endpoint, ip=None, dinh_danh=None, tenant_id=None):
    """Xóa bộ đếm (và lệnh chặn) của các bucket liên quan — gọi sau khi ĐĂNG NHẬP THÀNH CÔNG.

    Vì sao cần: không có nó thì người dùng thật gõ sai 4 lần rồi gõ đúng vẫn bị trần đè ở lần
    sau. Chỉ gọi sau một lượt THÀNH CÔNG, tuyệt đối không gọi khi thất bại.
    """
    with _khoa:
        for lt in luat_cua(endpoint):
            gt = _gia_tri_chieu(lt.chieu, ip, dinh_danh, tenant_id)
            if gt is None:
                continue
            k = f"{endpoint}|{lt.chieu}|{gt}"
            _lan.pop(k, None)
            _chan_den.pop(k, None)


def tieu_de(kq: KetQuaGioiHan) -> dict:
    """Header nên trả kèm. `Retry-After` là header chuẩn cho HTTP 429."""
    h = {}
    if kq.luat is not None:
        h["X-RateLimit-Limit"] = str(kq.luat.so_lan)
        h["X-RateLimit-Window"] = str(int(kq.luat.cua_so_giay))
    if kq.con_lai >= 0:
        h["X-RateLimit-Remaining"] = str(kq.con_lai)
    if not kq.cho_phep:
        h["Retry-After"] = str(max(1, int(kq.cho_bao_lau)))
    return h


def xoa_het():
    """Xóa toàn bộ trạng thái — CHỈ dùng cho bộ thử."""
    with _khoa:
        _lan.clear()
        _chan_den.clear()


def thong_ke():
    """Số bucket đang giữ — để nhìn được mức tiêu tốn bộ nhớ, không chứa dữ liệu người dùng."""
    with _khoa:
        return {"so_bucket": len(_lan), "so_dang_chan": len(_chan_den), "tran_bucket": TOI_DA_KHOA}


# =======================================================================================
# PHẦN B — HẠN MỨC NHẬP FILE (S05)
# =======================================================================================
#
# LỖ HỔNG ĐANG VÁ: `don_hang.tao_don` KHÔNG gọi `billing`; chỉ `gui_don` gọi
# `billing.kiem_va_tang_don`. Nên `nhap_file.duyet_batch` (gọi `tao_don` cho từng dòng) tạo được
# **rất nhiều đơn nháp** mà không tính vào hạn mức nào. Một tenang gói `free`
# (`han_muc_don_thang=50`) duyệt một file 5.000 dòng là có 5.000 đơn nháp trong CSDL.
#
# BA ĐIỀU CỐ Ý Ở ĐÂY:
#
#   1. **KHÔNG tự bật thu phí.** Hạn mức này chỉ ĐO và CHẶN, không ghi gì vào `usage_thang`,
#      không đụng `billing.py`. Đơn nháp không phải đơn đã gửi; cộng nó vào `usage_thang.so_don`
#      là âm thầm làm tenant hết hạn mức GỬI đơn — đổi nghĩa một con số đang có người dùng.
#      Vì vậy bộ đếm nằm ở BẢNG RIÊNG `han_muc_nhap_thang`.
#
#   2. **Kế toán NGUYÊN TỬ.** Không đọc-rồi-ghi (đó là chỗ `billing.kiem_va_tang_don` đang hở:
#      `usage_hien_tai` rồi mới `_tang`, hai yêu cầu song song lọt cả hai). Ở đây dùng **một câu
#      UPDATE có điều kiện trong WHERE**: CSDL tự so trần, `rowcount==0` nghĩa là vượt. Một câu
#      lệnh = một thao tác nguyên tử, không có khe hở giữa đọc và ghi.
#
#   3. **Cách ly theo tenant.** Mọi câu SQL ở đây đều có `tenant_id=?`; khóa chính là
#      `(tenant_id, thang)`. Tenant A dùng hết hạn mức không ảnh hưởng tenant B.
#
# BẢNG MỚI — bảng này do chính module tạo bằng `CREATE TABLE IF NOT EXISTS` (thao tác THÊM,
# không `ALTER` bảng nào đang có). AG-00 nên đưa đúng câu DDL này vào `csdl.SCHEMA` + một bước
# migration; xem docs/SECURITY_HARDENING_REPORT.md phần "Điểm cắm cần AG-00 làm".

DDL_HAN_MUC_NHAP = """
CREATE TABLE IF NOT EXISTS han_muc_nhap_thang (
  tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
  thang       TEXT    NOT NULL,
  so_don_nhap INTEGER NOT NULL DEFAULT 0,
  so_dong     INTEGER NOT NULL DEFAULT 0,
  so_file     INTEGER NOT NULL DEFAULT 0,
  so_byte     INTEGER NOT NULL DEFAULT 0,
  cap_nhat_luc TEXT,
  PRIMARY KEY (tenant_id, thang)
);
"""

# --- B.1 Cấu hình chính sách ----------------------------------------------------------
# Đặt ở đây vì `app/cau_hinh.py` do AG-00 giữ (AG-01 cấm sửa). Mỗi hằng số có env tương ứng
# để đổi được không cần sửa mã. AG-00 muốn dọn về `cau_hinh.py` thì chuyển cả khối này.
#
# Trần đơn nháp/tháng = `goi.han_muc_don_thang * BOI_SO_DON_NHAP`. Nhân lên vì nháp là nơi
# người ta thử, sửa, bỏ — siết bằng đúng hạn mức gửi là chặn cả việc làm bình thường.
BOI_SO_DON_NHAP = int(os.environ.get("VIP_HUB_BOI_SO_DON_NHAP", "3"))
TRAN_DON_NHAP_TOI_THIEU = int(os.environ.get("VIP_HUB_TRAN_DON_NHAP_MIN", "100"))

# Dung lượng và số dòng. `nhap_file.py` (AG-04, chỉ-đọc với AG-01) đã chặn ở mức
# GIOI_HAN_BYTE_FILE=10MiB / GIOI_HAN_SO_DONG=5000 cho MỘT file. Hai hằng dưới đây CỐ Ý không
# lỏng hơn, và có ca thử `thu_gioi_han` đối chiếu để nếu `nhap_file` siết lại mà chỗ này quên
# thì bộ thử hỏng (không để lệch im lặng).
GIOI_HAN_BYTE_MOI_FILE = int(os.environ.get("VIP_HUB_NHAP_BYTE_FILE", str(10 * 1024 * 1024)))
GIOI_HAN_DONG_MOI_FILE = int(os.environ.get("VIP_HUB_NHAP_DONG_FILE", "5000"))

# Trần theo THỜI GIAN, đếm từ CSDL (`import_batch.tao_luc`) nên sống qua restart.
GIOI_HAN_FILE_MOI_GIO = int(os.environ.get("VIP_HUB_NHAP_FILE_GIO", "20"))
GIOI_HAN_BYTE_MOI_THANG = int(os.environ.get("VIP_HUB_NHAP_BYTE_THANG", str(2 * 1024 * 1024 * 1024)))
GIOI_HAN_DONG_MOI_THANG_BOI_SO = int(os.environ.get("VIP_HUB_NHAP_DONG_THANG_BOI_SO", "20"))


class VuotHanMucNhap(Exception):
    """Vượt hạn mức nhập. CỐ Ý không kế thừa `billing.VuotHanMuc`.

    `server.py` đang bắt `billing.VuotHanMuc` → HTTP 402 ("cần trả tiền"). Hạn mức nhập là
    chống lạm dụng, KHÔNG phải mời nâng gói, nên nó phải ra mã khác (429 hoặc 413). Kế thừa là
    vô tình bật một thông điệp thu phí mà không ai quyết định — đúng dạng hỏng im lặng.
    """

    def __init__(self, msg, ma=429):
        super().__init__(msg)
        self.ma = ma


_da_tao_bang = False
_khoa_bang = threading.Lock()


def _dam_bao_bang():
    global _da_tao_bang
    if _da_tao_bang:
        return
    with _khoa_bang:
        if _da_tao_bang:
            return
        csdl.ghi(DDL_HAN_MUC_NHAP.strip().rstrip(";"))
        _da_tao_bang = True


def _moc_truoc_day(hours=1) -> str:
    """Mốc thời gian cách đây `hours` giờ, cùng múi giờ và cùng khuôn với `csdl.bay_gio()`."""
    from datetime import datetime, timedelta
    return (datetime.now(csdl.MUI_GIO_VN) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S%z")


def _goi(tenant_id):
    g = csdl.mot("SELECT g.* FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id WHERE t.id=?",
                 (tenant_id,))
    if not g:
        # Không có tenant/gói thì KHÔNG đoán một trần rộng rãi — từ chối để người xử.
        raise VuotHanMucNhap(f"không xác định được gói dịch vụ của tenant {tenant_id}", 400)
    return g


def tran_cua(tenant_id) -> dict:
    """Mọi trần áp cho tenant này, kèm trần của gói — để hiển thị và để bộ thử đối chiếu."""
    g = _goi(tenant_id)
    han_don = int(g["han_muc_don_thang"] or 0)
    return {
        "goi_id": g["id"], "goi_ten": g["ten"], "han_muc_don_thang_cua_goi": han_don,
        "tran_don_nhap_thang": max(TRAN_DON_NHAP_TOI_THIEU, han_don * BOI_SO_DON_NHAP),
        "tran_dong_thang": max(TRAN_DON_NHAP_TOI_THIEU, han_don * BOI_SO_DON_NHAP)
                           * GIOI_HAN_DONG_MOI_THANG_BOI_SO,
        "tran_byte_thang": GIOI_HAN_BYTE_MOI_THANG,
        "tran_byte_moi_file": GIOI_HAN_BYTE_MOI_FILE,
        "tran_dong_moi_file": GIOI_HAN_DONG_MOI_FILE,
        "tran_file_moi_gio": GIOI_HAN_FILE_MOI_GIO,
    }


def da_dung(tenant_id) -> dict:
    """Số đã dùng tháng này. Thiếu dòng = chưa dùng gì (không phải lỗi)."""
    _dam_bao_bang()
    thang = csdl.thang_nay()
    r = csdl.mot("SELECT * FROM han_muc_nhap_thang WHERE tenant_id=? AND thang=?",
                 (tenant_id, thang))
    return {"thang": thang,
            "so_don_nhap": r["so_don_nhap"] if r else 0,
            "so_dong": r["so_dong"] if r else 0,
            "so_file": r["so_file"] if r else 0,
            "so_byte": r["so_byte"] if r else 0}


def trang_thai(tenant_id) -> dict:
    """Gộp trần + đã dùng + còn lại. Đây là thứ nên trả ra API cho giao diện."""
    t, d = tran_cua(tenant_id), da_dung(tenant_id)
    return {"tran": t, "da_dung": d, "con_lai": {
        "don_nhap": max(0, t["tran_don_nhap_thang"] - d["so_don_nhap"]),
        "dong": max(0, t["tran_dong_thang"] - d["so_dong"]),
        "byte": max(0, t["tran_byte_thang"] - d["so_byte"])}}


def _cong_co_tran(tenant_id, cot, so_luong, tran) -> bool:
    """Cộng `so_luong` vào `cot` CHỈ KHI không vượt `tran`. Nguyên tử. True nếu cộng được.

    Điều kiện nằm trong WHERE nên CSDL tự so — không có khe hở giữa đọc và ghi. Hai yêu cầu
    song song thì đúng một yêu cầu thắng ở câu UPDATE.
    """
    _dam_bao_bang()
    thang = csdl.thang_nay()
    csdl.ghi("INSERT OR IGNORE INTO han_muc_nhap_thang (tenant_id, thang) VALUES (?,?)",
             (tenant_id, thang))
    con = csdl.ghi(
        f"UPDATE han_muc_nhap_thang SET {cot}={cot}+?, cap_nhat_luc=?"
        f" WHERE tenant_id=? AND thang=? AND {cot}+? <= ?",
        (so_luong, csdl.bay_gio(), tenant_id, thang, so_luong, tran))
    return con.rowcount == 1


def kiem_file_nhap(tenant_id, so_byte, so_dong=None, ghi_nhan=True) -> dict:
    """Chặn TRƯỚC khi phân tích file: dung lượng, số dòng, số file/giờ, dung lượng/tháng.

    Gọi ở `/api/v2/import` POST, NGAY TRƯỚC `nhap_file.tao_batch`. `so_dong=None` nghĩa là chưa
    biết số dòng (chưa parse) — khi đó chỉ kiểm những thứ biết được, và `nhap_file` vẫn còn lớp
    chặn số dòng của nó. Không giả vờ đã kiểm thứ chưa đo được.
    """
    if so_byte > GIOI_HAN_BYTE_MOI_FILE:
        raise VuotHanMucNhap(
            f"file {so_byte} byte, vượt trần {GIOI_HAN_BYTE_MOI_FILE} byte một file", 413)
    if so_dong is not None and so_dong > GIOI_HAN_DONG_MOI_FILE:
        raise VuotHanMucNhap(
            f"file có {so_dong} dòng dữ liệu, vượt trần {GIOI_HAN_DONG_MOI_FILE} dòng", 413)
    t = tran_cua(tenant_id)
    # Số file trong một giờ: đếm từ `import_batch` của ĐÚNG tenant này. Đếm từ CSDL (không từ
    # bộ nhớ) để restart không xóa trần.
    #
    # Mốc tính BẰNG PYTHON với ĐÚNG múi giờ và ĐÚNG khuôn của `csdl.bay_gio()` (có hậu tố
    # `+0700`). Không dùng `datetime('now','localtime')` của SQLite: nó lấy múi giờ của MÁY, còn
    # `tao_luc` ghi theo `MUI_GIO_VN` cố định — hai nguồn giờ khác nhau thì so chuỗi sẽ lệch một
    # cách im lặng khi máy đổi múi giờ (CLAUDE.md §12.2: "mọi mốc thời gian phải mang múi giờ").
    moc = _moc_truoc_day(hours=1)
    so_gio = csdl.mot("SELECT COUNT(*) c FROM import_batch WHERE tenant_id=? AND tao_luc>=?",
                      (tenant_id, moc))["c"]
    if so_gio >= t["tran_file_moi_gio"]:
        raise VuotHanMucNhap(
            f"đã tải {so_gio} file trong một giờ, trần {t['tran_file_moi_gio']} file/giờ", 429)
    if not ghi_nhan:
        return {"so_file_gio_qua": so_gio, "so_byte": so_byte}
    if not _cong_co_tran(tenant_id, "so_byte", so_byte, t["tran_byte_thang"]):
        d = da_dung(tenant_id)
        raise VuotHanMucNhap(
            f"đã nhập {d['so_byte']}/{t['tran_byte_thang']} byte tháng {d['thang']}", 413)
    _cong_co_tran(tenant_id, "so_file", 1, 10 ** 12)      # chỉ để thống kê, không phải trần
    return {"so_file_gio_qua": so_gio, "so_byte": so_byte}


def dat_truoc_don_nhap(tenant_id, so_luong) -> int:
    """ĐẶT TRƯỚC `so_luong` suất đơn nháp. Trả số đã đặt được, hoặc ném `VuotHanMucNhap`.

    Gọi ở `/api/v2/import/{id}/duyet` TRƯỚC vòng lặp tạo đơn, với `so_luong = len(dong_ids)`.
    Đặt trước (không cộng dần trong vòng lặp) để một lượt duyệt hoặc đi hết hoặc bị chặn ngay —
    không để nửa batch lọt qua rồi nửa sau bị chặn giữa đường.

    Dòng nào cuối cùng KHÔNG tạo được đơn thì gọi `nha_don_nhap` để hoàn lại suất.
    """
    if so_luong <= 0:
        return 0
    t = tran_cua(tenant_id)
    if not _cong_co_tran(tenant_id, "so_don_nhap", so_luong, t["tran_don_nhap_thang"]):
        d = da_dung(tenant_id)
        raise VuotHanMucNhap(
            f"lượt này cần {so_luong} đơn nháp, đã dùng {d['so_don_nhap']}/"
            f"{t['tran_don_nhap_thang']} của gói {t['goi_ten']} tháng {d['thang']}", 429)
    _cong_co_tran(tenant_id, "so_dong", so_luong, 10 ** 12)
    return so_luong


def nha_don_nhap(tenant_id, so_luong) -> int:
    """Hoàn lại suất đã đặt trước nhưng không dùng. Không bao giờ để bộ đếm xuống dưới 0."""
    if so_luong <= 0:
        return 0
    _dam_bao_bang()
    thang = csdl.thang_nay()
    con = csdl.ghi(
        "UPDATE han_muc_nhap_thang SET so_don_nhap=MAX(0, so_don_nhap-?), cap_nhat_luc=?"
        " WHERE tenant_id=? AND thang=?", (so_luong, csdl.bay_gio(), tenant_id, thang))
    return con.rowcount


def doi_soat(tenant_id) -> dict:
    """Đối chiếu bộ đếm với SỐ ĐƠN THẬT trong `don_hang` — phép đo ĐỘC LẬP (CLAUDE.md §12.1).

    Bộ đếm là thứ ta dùng để chặn, nên không được tin nó mà không có cái gì khác soi lại. Hàm
    này đếm đơn thật do import sinh ra (`idem_key` tiền tố `import-`) trong tháng rồi so.
    `lech != 0` không tự sửa gì — in ra để người xử, vì sửa im lặng là che mất nguyên nhân.
    """
    d = da_dung(tenant_id)
    thang = d["thang"]
    thuc = csdl.mot(
        "SELECT COUNT(*) c FROM don_hang WHERE tenant_id=? AND idem_key LIKE 'import-%'"
        " AND substr(tao_luc,1,7)=?", (tenant_id, thang))["c"]
    return {"thang": thang, "bo_dem": d["so_don_nhap"], "don_that": thuc,
            "lech": d["so_don_nhap"] - thuc}
