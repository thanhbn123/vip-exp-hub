# G03 — NormalizedCarrierError: chuẩn hóa lỗi của MỌI hãng về một kiểu chung.
#
# Vì sao cần: mỗi hãng có bộ mã lỗi riêng, kiểu chuỗi/số khác nhau, tiếng khác nhau. Order Service
# KHÔNG được biết chi tiết hãng — nó chỉ cần biết hai điều: lỗi thuộc LOẠI nào, và có ĐƯỢC THỬ LẠI
# không. Hợp đồng ở docs/SHARED_CONTRACTS.md mục 5.
#
# ---------------------------------------------------------------------------------------------
# LUẬT DANH SÁCH TRẮNG CHO `co_the_thu_lai` (CLAUDE.md §12.2 — ngoại lệ chính đáng)
# ---------------------------------------------------------------------------------------------
# §12.2 nói: cho dữ liệu đi qua thì dùng danh sách ĐEN. Nhưng ở đây câu hỏi phân biệt của chính
# §12.2 — *quên một dòng thì kết quả là AN TOÀN hay HỎNG?* — trả lời ngược lại:
#   - Danh sách TRẮNG (chỉ loại nào có tên mới được thử lại): quên một loại ⇒ không thử lại ⇒
#     chỉ mất tiện, đơn nằm chờ người xử. AN TOÀN.
#   - Danh sách ĐEN (mọi loại đều thử lại trừ loại bị cấm): quên một loại ⇒ thử lại mù một thao
#     tác ghi ⇒ có thể TẠO ĐƠN TRÙNG ở hãng. HỎNG THẬT, mất tiền thật.
# ⇒ Ở file này dùng danh sách TRẮNG, và `KHONG_RO` mặc định KHÔNG được thử lại.
#
# ---------------------------------------------------------------------------------------------
# NGUỒN MÃ LỖI J&T — ĐÃ ĐỌC ĐƯỢC (sửa ghi chú cũ "chưa đọc được")
# ---------------------------------------------------------------------------------------------
# Trang open.jtexpress.vn là SPA nên `curl` không đọc được; đọc bằng TRÌNH DUYỆT thật ngày
# 14/10/2026 tại:
#   - https://open.jtexpress.vn/apiDoc/errorCode/index   (bảng mã lỗi chung — 23 dòng, chép dưới đây)
#   - https://open.jtexpress.vn/apiDoc/logistics/query   (bảng mã lỗi riêng của tra hành trình)
#   - https://open.jtexpress.vn/apiDoc/orderserve/cancel (bảng mã lỗi riêng của hủy đơn)
# Tài liệu viết bằng tiếng Trung; phần tiếng Việt dưới đây là bản dịch của em, mã số là nguyên văn.
#
# Quy ước thành/bại của J&T (tài liệu mọi trang đều ghi giống nhau):
#   code == "1" là THÀNH CÔNG; khác "1" là thất bại và lý do nằm ở `msg`.
#   ⇒ Tuyệt đối không coi "0" là "không có lỗi" — tài liệu ghi rõ 0 = fail.

# ---- Tập mã chuẩn (dùng chung mọi hãng) ----
XAC_THUC_HONG = "XAC_THUC_HONG"          # sai chữ ký, sai tài khoản API, tài khoản bị khóa/không có quyền
THAM_SO_SAI = "THAM_SO_SAI"              # dữ liệu gửi lên sai định dạng, thiếu trường, địa chỉ không hợp lệ
QUA_HAN_MUC = "QUA_HAN_MUC"              # vượt giới hạn gọi / hạn mức của hãng
HET_GIO = "HET_GIO"                      # mạng chập, hết giờ — KHÔNG BIẾT kết quả
HANG_TU_CHOI = "HANG_TU_CHOI"            # hãng từ chối vì lý do nghiệp vụ (biết chắc là hỏng)
DON_TRUNG = "DON_TRUNG"                  # hãng báo mã đơn đã tồn tại — tức lượt trước ĐÃ VÀO
KHONG_TIM_THAY = "KHONG_TIM_THAY"        # không có dữ liệu tương ứng
KHONG_RO = "KHONG_RO"                    # chưa phân loại được — mặc định an toàn, không thử lại

MA_CHUAN = (XAC_THUC_HONG, THAM_SO_SAI, QUA_HAN_MUC, HET_GIO, HANG_TU_CHOI,
            DON_TRUNG, KHONG_TIM_THAY, KHONG_RO)

# Danh sách TRẮNG: CHỈ hai loại này được thử lại (xem luật ở đầu file).
#   - HET_GIO: chưa biết kết quả, nhưng lớp transport.py mới là chỗ quyết định có thử lại thật
#     không (thao tác ghi không có khóa chống trùng thì vẫn KHÔNG thử lại).
#   - QUA_HAN_MUC: hãng bảo chờ; thử lại sau backoff là đúng.
DUOC_THU_LAI = frozenset({HET_GIO, QUA_HAN_MUC})


class NormalizedCarrierError(Exception):
    """Lỗi hãng đã chuẩn hóa. Order Service chỉ cần đọc `ma_chuan` và `co_the_thu_lai`."""

    __slots__ = ("ma_chuan", "ma_goc_hang", "thong_diep", "co_the_thu_lai", "hang", "thao_tac",
                 "http_status", "tho")

    def __init__(self, ma_chuan, ma_goc_hang=None, thong_diep="", co_the_thu_lai=None,
                 hang=None, thao_tac=None, http_status=None, tho=None):
        if ma_chuan not in MA_CHUAN:
            # Mã lạ KHÔNG được âm thầm đi tiếp: đó là lỗi lập trình, không phải lỗi hãng.
            raise ValueError(f"ma_chuan '{ma_chuan}' không nằm trong tập chuẩn {MA_CHUAN}")
        self.ma_chuan = ma_chuan
        self.ma_goc_hang = None if ma_goc_hang is None else str(ma_goc_hang)
        self.thong_diep = thong_diep or ""
        # Mặc định suy từ danh sách trắng; cho phép ép chặt hơn, KHÔNG cho nới lỏng (xem dưới).
        suy_ra = ma_chuan in DUOC_THU_LAI
        if co_the_thu_lai is None:
            self.co_the_thu_lai = suy_ra
        else:
            # Chỉ cho ép từ True→False (chặt hơn). Ép False→True là mở cửa thử lại mù → cấm.
            self.co_the_thu_lai = bool(co_the_thu_lai) and suy_ra
        self.hang = hang
        self.thao_tac = thao_tac
        self.http_status = http_status
        self.tho = tho or {}
        super().__init__(str(self))

    def __str__(self):
        phan = [self.ma_chuan]
        if self.hang:
            phan.append(f"hãng={self.hang}")
        if self.thao_tac:
            phan.append(f"thao_tác={self.thao_tac}")
        if self.ma_goc_hang is not None:
            phan.append(f"mã_gốc={self.ma_goc_hang}")
        if self.http_status is not None:
            phan.append(f"http={self.http_status}")
        if self.thong_diep:
            phan.append(self.thong_diep)
        phan.append("thử lại được" if self.co_the_thu_lai else "KHÔNG thử lại")
        return " · ".join(str(x) for x in phan)

    def nhu_dict(self):
        """Dạng để ghi audit / trả API. KHÔNG kèm credentials — `tho` do nơi gọi tự lọc."""
        return {"ma_chuan": self.ma_chuan, "ma_goc_hang": self.ma_goc_hang,
                "thong_diep": self.thong_diep, "co_the_thu_lai": self.co_the_thu_lai,
                "hang": self.hang, "thao_tac": self.thao_tac, "http_status": self.http_status}


# =================================================================================================
# Bảng mã lỗi J&T Express — chép nguyên mã số từ tài liệu, đọc bằng trình duyệt 14/10/2026.
# Nguồn chính: open.jtexpress.vn/apiDoc/errorCode/index
# =================================================================================================
JT_MA_LOI = {
    # --- thành công ---
    "1": (None, "成功 — thành công"),
    # --- thất bại chung, không nói rõ lý do (bảng riêng từng API ghi 0 = fail) ---
    "0": (KHONG_RO, "fail — thất bại, lý do nằm ở trường msg"),

    # --- xác thực / chữ ký / tài khoản API ---
    "145003052": (XAC_THUC_HONG, "摘要为空 — thiếu header digest"),
    "145003051": (XAC_THUC_HONG, "Api Account 为空 — thiếu header apiAccount"),
    "145003053": (XAC_THUC_HONG, "Timestamp 字段为空 — thiếu header timestamp"),
    "145003010": (XAC_THUC_HONG, "API 账号不存在 — tài khoản API không tồn tại"),
    "145003030": (XAC_THUC_HONG, "请求头中的签名验证失败 — chữ ký trong header sai"),
    "145003031": (XAC_THUC_HONG, "业务参数签名失败 — chữ ký của bizContent sai"),
    "145003012": (XAC_THUC_HONG, "API账号没有接口权限 — tài khoản API không có quyền gọi API này"),
    "999011010": (XAC_THUC_HONG, "客户不存在 — khách hàng không tồn tại"),
    "999011020": (XAC_THUC_HONG, "客户已被禁用 — khách hàng đã bị vô hiệu hóa"),
    "999011030": (XAC_THUC_HONG, "客户已被锁定 — khách hàng đã bị khóa"),
    "999001030": (XAC_THUC_HONG, "客户编码或密码错误 — sai customerCode hoặc password"),

    # --- tham số sai ---
    "145003050": (THAM_SO_SAI, "参数非法 — tham số không hợp lệ"),
    "999001010": (THAM_SO_SAI, "输入参数错误，请查看 msg — sai tham số đầu vào, đọc msg"),
    "145003082": (THAM_SO_SAI, "客户订单号不能为空或过长 — txlogisticId rỗng hoặc quá dài"),
    "145003089": (THAM_SO_SAI, "取消原因不能为空 — thiếu lý do hủy"),
    "145003100": (THAM_SO_SAI, "运单号不合法 — mã vận đơn không hợp lệ"),
    "145003502": (THAM_SO_SAI, "运单号数量超过30个 — gửi quá 30 mã vận đơn một lượt"),
    "1450033315": (THAM_SO_SAI, "请正确填写寄件区县和收件区县 — sai quận/huyện gửi hoặc nhận"),
    "999009010": (THAM_SO_SAI, "未找到对应的寄件来源信息 — không tìm thấy nơi gửi"),
    "999009020": (THAM_SO_SAI, "未找到对应的目的地信息 — không tìm thấy nơi nhận"),

    # --- hãng từ chối vì nghiệp vụ ---
    "145005004": (HANG_TU_CHOI, "该收货地址暂时停用 — địa chỉ nhận tạm ngừng phục vụ"),
    "145005005": (HANG_TU_CHOI, "获取运单号失败 — hãng không cấp được mã vận đơn"),
    "999010010": (HANG_TU_CHOI, "当前订单状态无法取消 — trạng thái đơn hiện tại không hủy được"),

    # --- đơn trùng: lượt trước ĐÃ VÀO HÃNG, tuyệt đối không tạo lại ---
    "145003204": (DON_TRUNG, "订单重复 — txlogisticId đã tồn tại, phải dùng mã khác"),

    # --- không tìm thấy ---
    "999002000": (KHONG_TIM_THAY, "未找到数据 — không tìm thấy dữ liệu"),
}
# CHƯA ĐỌC ĐƯỢC / CHƯA CÓ: tài liệu công khai KHÔNG liệt kê mã nào cho vượt hạn mức gọi
# (rate limit). Vì vậy `QUA_HAN_MUC` của J&T hiện chỉ đến từ HTTP 429, không từ trường `code`.
# Cần xác minh khi có tài khoản thật.

BANG_MA_LOI = {"jt": JT_MA_LOI}
# Viettel Post: CHƯA CÓ bảng mã lỗi. Đã đọc repo `vip-viettelpost` ngày 14/10/2026 (Owner cho phép)
# — repo đó không có mã lỗi nào của hãng (xem docs/VIETTELPOST_REUSE_AUDIT.md). Để RỖNG, không bịa.
# Lỗi VTP hiện chỉ phân loại được theo HTTP status.


# ---- HTTP status → mã chuẩn. Dùng chung mọi hãng, khi không đọc được mã của hãng. ----
def tu_http(status, hang=None, thao_tac=None, thong_diep=""):
    """Phân loại theo mã HTTP. Chỉ 408/429/5xx mới được coi là có thể thử lại."""
    s = int(status)
    if s == 408:
        ma = HET_GIO
    elif s == 429:
        ma = QUA_HAN_MUC
    elif 500 <= s <= 599:
        ma = HET_GIO           # 5xx = lỗi phía hãng, KHÔNG BIẾT kết quả thao tác ghi
    elif s in (401, 403):
        ma = XAC_THUC_HONG
    elif s == 404:
        ma = KHONG_TIM_THAY
    elif s in (400, 422):
        ma = THAM_SO_SAI
    elif 400 <= s <= 499:
        ma = KHONG_RO          # 4xx lạ: không đoán, và không thử lại
    else:
        ma = KHONG_RO
    return NormalizedCarrierError(ma, ma_goc_hang=f"HTTP {s}", thong_diep=thong_diep,
                                  hang=hang, thao_tac=thao_tac, http_status=s)


def _mo_ta_msg_hang(msg):
    """Mô tả thông điệp của hãng mà KHÔNG chép nội dung của nó vào `thong_diep`.

    VÌ SAO (G21/AG-03) — `msg` là VĂN BẢN TỰ DO của máy chủ bên kia, tức DỮ LIỆU NGOÀI. Nó có thể
    echo lại CHÍNH credential vừa gửi. ĐO ĐƯỢC trước bản vá (`thu_g21_bimat.D1`): stub trả
    `{"code":"145005005","msg":"khoa cua ban: <privateKey>"}` ở một lượt HTTP **200**; vì thân 2xx
    là bằng chứng nguyên văn (hợp đồng §36) nên nó không bị che ở tầng HTTP, rồi `tu_ma_hang` chép
    thẳng vào `thong_diep` ⇒ `KetQuaHang.loi/tho` ⇒ `don_hang` ném `LoiNghiepVu` ⇒ **HTTP 502 mang
    bí mật trong thân phản hồi** — bí mật đi ra ngoài đúng đường người dùng nhìn thấy.

    Nên ở đây chỉ giữ thứ KHÔNG THỂ chứa bí mật: ĐỘ DÀI của thông điệp. Phần hành động được vẫn
    còn nguyên — mô tả tiếng Việt của mã lỗi và chính mã lỗi (`ma_goc_hang`) — nên không có chẩn
    đoán nào bị mất: người trực tra bảng mã của hãng bằng mã, không bằng câu chữ tiếng Trung.

    KHÔNG dùng vân tay băm (sha256) thay thế: băm một bí mật NGẮN là chuyện giải ngược được bằng
    vét cạn, tức vẫn là một đường rò — chỉ khó thấy hơn.
    """
    tho = str(msg or "")
    if not tho:
        return ""
    return f" | msg hãng: {len(tho)} ký tự (KHÔNG chép nguyên văn — văn bản NGOÀI có thể echo credential)"


def tu_ma_hang(hang, ma_goc, msg="", thao_tac=None, http_status=None):
    """Đổi mã lỗi riêng của hãng → NormalizedCarrierError.
    Mã không có trong bảng ⇒ KHONG_RO + KHÔNG thử lại (không đoán nghĩa mã lạ)."""
    bang = BANG_MA_LOI.get(hang) or {}
    khoa = str(ma_goc)
    if khoa in bang:
        ma_chuan, mo_ta = bang[khoa]
        if ma_chuan is None:
            raise ValueError(f"mã '{khoa}' của hãng {hang} là mã THÀNH CÔNG, không phải lỗi")
        thong_diep = f"{mo_ta}" + _mo_ta_msg_hang(msg)
    else:
        ma_chuan = KHONG_RO
        thong_diep = (f"mã lỗi '{khoa}' chưa có trong bảng đã đọc của hãng {hang}"
                      + _mo_ta_msg_hang(msg))
    return NormalizedCarrierError(ma_chuan, ma_goc_hang=khoa, thong_diep=thong_diep,
                                  hang=hang, thao_tac=thao_tac, http_status=http_status)


def tu_ngoai_le(e, hang=None, thao_tac=None):
    """Đổi ngoại lệ của transport.py → NormalizedCarrierError (một chiều: transport → lỗi chuẩn)."""
    import transport as tp
    if isinstance(e, NormalizedCarrierError):
        return e
    if isinstance(e, tp.LoiTamThoi):
        return NormalizedCarrierError(HET_GIO, thong_diep=str(e), hang=hang, thao_tac=thao_tac)
    if isinstance(e, tp.LoiVinhVien):
        return NormalizedCarrierError(THAM_SO_SAI, thong_diep=str(e), hang=hang, thao_tac=thao_tac)
    return NormalizedCarrierError(KHONG_RO, thong_diep=f"{type(e).__name__}: {e}",
                                  hang=hang, thao_tac=thao_tac)


def thanh_ngoai_le_transport(loi: NormalizedCarrierError):
    """Chiều ngược lại: lỗi chuẩn → ngoại lệ transport, để khung retry hiểu được.
    `co_the_thu_lai` là thứ DUY NHẤT quyết định, nên hai lớp không thể lệch nhau."""
    import transport as tp
    return tp.LoiTamThoi(str(loi)) if loi.co_the_thu_lai else tp.LoiVinhVien(str(loi))


# ---- J&T: đọc gói trả lời chuẩn {code, msg, data} ----
def doc_tra_loi_jt(goi, thao_tac=None, http_status=None):
    """Trả None nếu THÀNH CÔNG (code == "1"), ngược lại trả NormalizedCarrierError.
    Tài liệu J&T: `code` kiểu String; "1" là thành công, khác là thất bại và lý do ở `msg`."""
    if not isinstance(goi, dict):
        return NormalizedCarrierError(KHONG_RO, thong_diep=f"gói trả lời J&T không phải JSON object: {type(goi).__name__}",
                                      hang="jt", thao_tac=thao_tac, http_status=http_status)
    if "code" not in goi:
        return NormalizedCarrierError(KHONG_RO, thong_diep="gói trả lời J&T thiếu trường 'code'",
                                      hang="jt", thao_tac=thao_tac, http_status=http_status)
    ma = str(goi.get("code"))
    if ma == "1":
        return None
    return tu_ma_hang("jt", ma, msg=str(goi.get("msg") or ""), thao_tac=thao_tac,
                      http_status=http_status)
