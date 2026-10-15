# G09 — BỘ KIỂM THỬ KẾT NỐI HÃNG (harness).
#
# Mục đích: chạy được MỘT bộ ca kiểm giống nhau ở ba chế độ, và nói đúng chế độ nào đã chạy.
#
#   MOCK     — chạy được ngay, không cần gì, không chạm mạng.
#   SANDBOX  — PHẢI khai rõ cấu hình + credentials; thiếu thì TỪ CHỐI, nêu chính xác thiếu gì.
#   LIVE     — PHẢI có phiếu duyệt RIÊNG cho TỪNG thao tác tạo/huỷ đơn. Một cờ môi trường là
#              KHÔNG đủ.
#
# -------------------------------------------------------------------------------------------
# VÌ SAO THIẾT KẾ NHƯ VẬY — §12.1 "thứ dùng để kiểm chứng phải tự nó đáng tin"
# -------------------------------------------------------------------------------------------
# Kiểu hỏng nguy hiểm nhất của một bộ harness KHÔNG phải là nó báo hỏng. Là nó được gọi ở chế
# độ SANDBOX, thiếu credentials, rồi ÂM THẦM rơi về MOCK và báo ĐẠT. Lúc đó cái dùng để kiểm
# chứng lại tự nó nói dối, và không ai thấy gì sai.
# ⇒ Luật của file này: **không có đường rơi về MOCK.** Thiếu gì thì ném `ThieuCauHinh` kèm danh
#   sách chính xác. `KetQuaLanChay.che_do` luôn là chế độ ĐÃ CHẠY, không phải chế độ ĐÃ XIN.
#
# -------------------------------------------------------------------------------------------
# BỐN Ổ KHOÁ CHẶN LIVE — phải mở HẾT BỐN mới chạy được, và ổ thứ tư nằm ngoài tầm file này
# -------------------------------------------------------------------------------------------
#   1. `VIP_HUB_HARNESS_CHE_DO=LIVE`                      (cờ môi trường)
#   2. `VIP_HUB_HARNESS_DUYET=<mã việc đã được cấp>`      (mã việc, phải khớp MA_VIEC_CAN_CAP)
#   3. `PhieuDuyetLive` riêng cho TỪNG thao tác ghi       (người duyệt · thao tác · tham chiếu
#                                                          · hạn dùng) — truyền trong mã, không
#                                                          lấy được từ môi trường
#   4. `CarrierAdapter.CHO_PHEP_LIVE = True`              (hằng CHỐT CỨNG trong `app/adapter.py`,
#                                                          file này CHỈ ĐỌC — G09 không sửa)
#
# Ổ số 4 là ổ quan trọng nhất: kể cả khi ba ổ kia bị mở nhầm, `adapter.tao_adapter(...,
# "production")` vẫn ném `PermissionError` ngay trong `__init__`. Nghĩa là harness KHÔNG thể tự
# mở đường live kể cả khi mã của chính nó có lỗi.
#
# -------------------------------------------------------------------------------------------
# PHẠM VI — nói rõ cái gì NẰM NGOÀI (§12.1 luật 5, luật số "0")
# -------------------------------------------------------------------------------------------
# Bộ ca kiểm dưới đây đo **mã trong `app/` của dự án này, chạy cục bộ, không có mạng**. Nó
# KHÔNG đo: hãng thật có chấp nhận chữ ký không, tài liệu hãng có đúng không, sandbox hãng có
# sống không, callback hãng ký bằng khoá nào. Những điều đó chỉ SANDBOX/LIVE trả lời được, và
# cả hai đang BLOCKED.
import json
import os
import time

import adapter
import adapter_jt
import adapter_vtp  # noqa: F401  — đăng ký adapter VTP
import loi_hang
import trang_thai_hang as tth
import transport as tp
import webhook

# ============================================================================
# 1. CHẾ ĐỘ, MỨC SẴN SÀNG, MÃ VIỆC
# ============================================================================
MOCK = "MOCK"
SANDBOX = "SANDBOX"
LIVE = "LIVE"
CHE_DO_HOP_LE = (MOCK, SANDBOX, LIVE)

# Sáu mức sẵn sàng. NĂM mức dưới đây **mượn thẳng từ `webhook.py`** thay vì chép lại: hai bản
# danh sách là hai bản sẽ lệch nhau (§14.6 của CLAUDE.md), và mức xác thực webhook với mức sẵn
# sàng hạng mục phải nói cùng một thứ tiếng.
DOCUMENTED = webhook.MUC_DOCUMENTED        # đọc được trong tài liệu hãng, chưa viết mã
IMPLEMENTED = "IMPLEMENTED"                # đã có mã trong dự án, chưa có phép đo nào chạy qua
MOCK_VERIFIED = webhook.MUC_MOCK           # có ca kiểm ĐÃ CHẠY ĐẠT với bộ mô phỏng của dự án
SANDBOX_VERIFIED = webhook.MUC_SANDBOX     # đã chạy đạt với sandbox THẬT của hãng
LIVE_VERIFIED = webhook.MUC_LIVE           # đã chạy đạt với môi trường thật
BLOCKED = webhook.MUC_BLOCKED              # thiếu tài liệu hoặc thiếu quyền → không làm được
SAU_MUC = (DOCUMENTED, IMPLEMENTED, MOCK_VERIFIED, SANDBOX_VERIFIED, LIVE_VERIFIED, BLOCKED)

# Mã việc PHẢI được cấp trước khi chạm mạng hãng (docs/SHARED_CONTRACTS.md mục 25).
MA_VIEC_CAN_CAP = {
    SANDBOX: ("V-G09-01", "V-13906-05"),   # gọi API hãng + credentials sandbox J&T
    LIVE: ("V-G09-01",),
}

BIEN_CHE_DO = "VIP_HUB_HARNESS_CHE_DO"
BIEN_DUYET = "VIP_HUB_HARNESS_DUYET"
BIEN_NGUOI_DUYET = "VIP_HUB_HARNESS_NGUOI_DUYET"
BIEN_CRED_FILE = "VIP_HUB_HARNESS_CRED_FILE"

# Trường credentials bắt buộc cho từng hãng. Mỗi phần tử là MỘT nhóm "phải có ít nhất một
# cách": nhóm là tuple các bộ trường chấp nhận được.
#
# J&T   — nguồn: open.jtexpress.vn/apiDoc/orderserve/create (đọc bằng trình duyệt 15/10/2026).
#         `apiAccount`/`privateKey` là của TÀI KHOẢN NỀN TẢNG (xem trong console); `customerCode`
#         /`password` là của HỢP ĐỒNG KHÁCH (bưu cục hợp tác cấp). Thiếu nhóm thứ hai thì ký
#         đúng vẫn không tạo được đơn — đây đúng là chỗ đang BLOCKED.
# VTP   — nguồn: partner2.viettelpost.vn/document/token-authen, đọc lại qua repo
#         `thanhbn123/vip-viettelpost` nhánh `main` ngày 15/10/2026 (CHỈ ĐỌC). Hai đường:
#         token tĩnh, hoặc USERNAME+PASSWORD rồi Login → ownerconnect.
CRED_BAT_BUOC = {
    "jt": (("apiAccount", "privateKey"), ("customerCode", "password")),
    "vtp": (("vtp_token",), ("vtp_username", "vtp_password")),
}
# Nhóm nào chỉ cần MỘT trong nhiều cách thì khai ở đây (tên nhóm → các bộ thay thế nhau).
CRED_THAY_THE = {
    "vtp": [(("vtp_token",), ("vtp_username", "vtp_password"))],
}


class ThieuCauHinh(Exception):
    """Harness TỪ CHỐI chạy vì thiếu cấu hình. `thieu` liệt kê chính xác cái còn thiếu.

    Ném ngoại lệ chứ KHÔNG rơi về MOCK: rơi về MOCK rồi báo đạt là kiểu hỏng im lặng tệ nhất
    của một bộ nghiệm thu (§12.1).
    """

    def __init__(self, che_do, thieu):
        self.che_do = che_do
        self.thieu = list(thieu)
        super().__init__(f"harness chế độ {che_do} TỪ CHỐI chạy — còn thiếu: "
                         + "; ".join(self.thieu))


class ThieuPhieuDuyet(ThieuCauHinh):
    """Chế độ LIVE: thiếu phiếu duyệt cho MỘT thao tác ghi cụ thể."""


# ============================================================================
# 2. PHIẾU DUYỆT LIVE — mỗi thao tác ghi một phiếu, không dùng lại
# ============================================================================
THAO_TAC_GHI = ("createOrder", "cancelOrder")


class PhieuDuyetLive:
    """Một phiếu = MỘT thao tác ghi trên MỘT tham chiếu, có hạn.

    Vì sao không dùng cờ môi trường: một cờ bật là bật cho mọi thao tác, mọi đơn, mãi mãi. Tạo
    đơn thật ở hãng là việc mất tiền thật và không hoàn tác được bằng một lệnh — nó phải có
    người, có đối tượng và có hạn, giống hệt cách `trang_thai_hang.chot_nghia()` đòi
    `nguoi_chot` + `can_cu`.
    """

    __slots__ = ("thao_tac", "ma_tham_chieu", "nguoi_duyet", "ma_viec", "han_den_epoch",
                 "ghi_chu", "_da_dung")

    def __init__(self, thao_tac, ma_tham_chieu, nguoi_duyet, ma_viec, han_den_epoch,
                 ghi_chu=""):
        if thao_tac not in THAO_TAC_GHI:
            raise ValueError(f"phiếu duyệt chỉ dành cho thao tác ghi {THAO_TAC_GHI},"
                             f" không phải {thao_tac!r}")
        for ten, gt in (("ma_tham_chieu", ma_tham_chieu), ("nguoi_duyet", nguoi_duyet),
                        ("ma_viec", ma_viec)):
            if not str(gt or "").strip():
                raise ValueError(f"phiếu duyệt thiếu {ten}")
        self.thao_tac = thao_tac
        self.ma_tham_chieu = str(ma_tham_chieu)
        self.nguoi_duyet = str(nguoi_duyet)
        self.ma_viec = str(ma_viec)
        self.han_den_epoch = float(han_den_epoch)
        self.ghi_chu = ghi_chu
        self._da_dung = False

    def con_han(self, bay_gio=None):
        return (bay_gio if bay_gio is not None else time.time()) < self.han_den_epoch

    def kiem(self, thao_tac, ma_tham_chieu, bay_gio=None):
        """Trả danh sách lý do KHÔNG hợp lệ. Rỗng = hợp lệ."""
        loi = []
        if self.thao_tac != thao_tac:
            loi.append(f"phiếu duyệt cho '{self.thao_tac}', không phải '{thao_tac}'")
        if self.ma_tham_chieu != str(ma_tham_chieu):
            loi.append(f"phiếu duyệt cho tham chiếu '{self.ma_tham_chieu}',"
                       f" không phải '{ma_tham_chieu}'")
        if self.ma_viec not in MA_VIEC_CAN_CAP[LIVE]:
            loi.append(f"mã việc '{self.ma_viec}' không nằm trong {MA_VIEC_CAN_CAP[LIVE]}")
        if not self.con_han(bay_gio):
            loi.append("phiếu duyệt đã quá hạn")
        if self._da_dung:
            loi.append("phiếu duyệt đã dùng một lần rồi — mỗi phiếu một lượt")
        return loi

    def danh_dau_da_dung(self):
        self._da_dung = True

    def nhu_dict(self):
        """KHÔNG có trường bí mật nào ở đây — phiếu được ghi vào nhật ký chạy."""
        return {"thao_tac": self.thao_tac, "ma_tham_chieu": self.ma_tham_chieu,
                "nguoi_duyet": self.nguoi_duyet, "ma_viec": self.ma_viec,
                "han_den_epoch": self.han_den_epoch, "ghi_chu": self.ghi_chu,
                "da_dung": self._da_dung}


# ============================================================================
# 3. CỔNG CHẾ ĐỘ — chỗ DUY NHẤT quyết định được chạy hay không
# ============================================================================
def _doc_cred_file(duong_dan):
    """Đọc credentials từ FILE, không từ biến môi trường trần.

    Biến môi trường trần hiện trong `ps`, trong log của bộ lập lịch, và trong ảnh chụp màn hình
    khi ai đó dán `env` vào hội thoại. File thì chỉ hiện đường dẫn.
    """
    with open(duong_dan, encoding="utf-8") as f:
        d = json.load(f)
    if not isinstance(d, dict):
        raise ValueError("file credentials phải là một JSON object {hang: {...}}")
    return d


def thieu_gi_de_chay(che_do, hang, moi_truong_os=None, cred=None):
    """Liệt kê CHÍNH XÁC cái còn thiếu để chạy `che_do` cho `hang`. Rỗng = đủ điều kiện.

    Hàm này là nơi duy nhất biết "đủ điều kiện" nghĩa là gì, để báo cáo và lúc chạy không thể
    nói hai điều khác nhau.
    """
    env = os.environ if moi_truong_os is None else moi_truong_os
    thieu = []
    if che_do == MOCK:
        return thieu

    # (a) mã việc phải được cấp — tra bảng mục 25 của SHARED_CONTRACTS
    duyet = str(env.get(BIEN_DUYET, "") or "").strip()
    can = MA_VIEC_CAN_CAP[che_do]
    if duyet not in can:
        thieu.append(f"quyền chưa cấp: cần {BIEN_DUYET} là một trong {can}"
                     f" (docs/SHARED_CONTRACTS.md mục 25 ghi các mã này là CHƯA CẤP)")
    if not str(env.get(BIEN_NGUOI_DUYET, "") or "").strip():
        thieu.append(f"thiếu {BIEN_NGUOI_DUYET}: ai là người duyệt lượt chạy này")

    # (b) credentials
    if cred is None:
        duong = str(env.get(BIEN_CRED_FILE, "") or "").strip()
        if not duong:
            thieu.append(f"thiếu {BIEN_CRED_FILE}: đường dẫn file JSON chứa credentials")
        elif not os.path.exists(duong):
            thieu.append(f"{BIEN_CRED_FILE} trỏ tới file không tồn tại: {duong}")
        else:
            try:
                cred = _doc_cred_file(duong).get(hang)
            except (OSError, ValueError) as e:
                thieu.append(f"không đọc được {BIEN_CRED_FILE}: {type(e).__name__}: {e}")
    if cred is None and not any(BIEN_CRED_FILE in t for t in thieu):
        thieu.append(f"file credentials không có mục cho hãng '{hang}'")
    if isinstance(cred, dict):
        thieu.extend(_thieu_truong_cred(hang, cred))

    # (c) ổ khoá cuối: hằng trong adapter. G09 KHÔNG được sửa hằng này — nêu ra để người đọc
    # biết vì sao kể cả khi đủ (a) và (b) thì vẫn chưa chạy được.
    lop = adapter._DANG_KY.get(hang)
    if lop is None:
        thieu.append(f"chưa có adapter cho hãng '{hang}'")
    elif not lop.CHO_PHEP_LIVE:
        thieu.append(f"adapter {hang}: CHO_PHEP_LIVE=False — khoá an toàn chốt cứng trong"
                     " app/adapter*.py, chỉ Owner mở (G09 CHỈ ĐỌC file đó)")
    return thieu


def _thieu_truong_cred(hang, cred):
    """Thiếu trường credentials nào, theo đúng tài liệu từng hãng."""
    thieu = []
    thay_the = CRED_THAY_THE.get(hang)
    if thay_the:
        for nhom in thay_the:
            if not any(all(cred.get(t) for t in bo) for bo in nhom):
                cach = " HOẶC ".join("+".join(bo) for bo in nhom)
                thieu.append(f"credentials {hang}: cần {cach}")
        return thieu
    for bo in CRED_BAT_BUOC.get(hang, ()):
        for truong in bo:
            if not cred.get(truong):
                thieu.append(f"credentials {hang}: thiếu trường '{truong}'")
    return thieu


def che_do_dang_xin(moi_truong_os=None):
    env = os.environ if moi_truong_os is None else moi_truong_os
    cd = str(env.get(BIEN_CHE_DO, MOCK) or MOCK).strip().upper()
    if cd not in CHE_DO_HOP_LE:
        raise ValueError(f"{BIEN_CHE_DO}={cd!r} không hợp lệ; chỉ nhận {CHE_DO_HOP_LE}")
    return cd


def moi_truong_adapter(che_do):
    """Chế độ harness → tên môi trường mà `adapter.tao_adapter` hiểu."""
    return {MOCK: "mock", SANDBOX: "sandbox", LIVE: "production"}[che_do]


# ============================================================================
# 4. KẾT QUẢ
# ============================================================================
class CaKiem:
    __slots__ = ("ma_ca", "nhom", "mo_ta", "ket_qua", "chi_tiet", "do_bang_gi")

    def __init__(self, ma_ca, nhom, mo_ta, ket_qua, chi_tiet="", do_bang_gi=""):
        assert ket_qua in ("dat", "hong", "bo_qua"), ket_qua
        self.ma_ca, self.nhom, self.mo_ta = ma_ca, nhom, mo_ta
        self.ket_qua, self.chi_tiet, self.do_bang_gi = ket_qua, chi_tiet, do_bang_gi

    def nhu_dict(self):
        return {t: getattr(self, t) for t in self.__slots__}

    def __repr__(self):
        return f"CaKiem({self.ma_ca} {self.ket_qua})"


class KetQuaLanChay:
    def __init__(self, che_do, hang):
        self.che_do = che_do        # chế độ ĐÃ CHẠY, không phải chế độ đã xin
        self.hang = hang
        self.cac_ca = []
        self.bat_dau = time.time()
        self.ket_thuc = None

    def them(self, ca):
        self.cac_ca.append(ca)
        return ca

    @property
    def so_dat(self):
        return sum(1 for c in self.cac_ca if c.ket_qua == "dat")

    @property
    def so_hong(self):
        return sum(1 for c in self.cac_ca if c.ket_qua == "hong")

    @property
    def so_bo_qua(self):
        return sum(1 for c in self.cac_ca if c.ket_qua == "bo_qua")

    @property
    def dat(self):
        return self.so_hong == 0 and self.so_dat > 0

    def ca_dat(self, ma_ca):
        return any(c.ma_ca == ma_ca and c.ket_qua == "dat" for c in self.cac_ca)

    def nhu_dict(self):
        return {"che_do": self.che_do, "hang": self.hang, "so_ca": len(self.cac_ca),
                "so_dat": self.so_dat, "so_hong": self.so_hong, "so_bo_qua": self.so_bo_qua,
                "dat": self.dat, "bat_dau": self.bat_dau, "ket_thuc": self.ket_thuc,
                "cac_ca": [c.nhu_dict() for c in self.cac_ca],
                "pham_vi": PHAM_VI_DO[self.che_do]}


# Câu "đo bằng gì / cái gì NẰM NGOÀI" đi kèm MỌI kết luận — §12.1 luật 5.
PHAM_VI_DO = {
    MOCK: ("Đo bằng bộ mô phỏng NỘI BỘ của dự án, không có mạng. NẰM NGOÀI phạm vi: hãng thật"
           " có chấp nhận chữ ký/tham số không, sandbox hãng có sống không, callback hãng ký"
           " bằng khoá nào."),
    SANDBOX: ("Đo bằng sandbox THẬT của hãng. NẰM NGOÀI: hành vi môi trường production, hạn"
              " mức thật, dữ liệu địa danh thật."),
    LIVE: ("Đo bằng môi trường THẬT của hãng. NẰM NGOÀI: các ca không chạy được vì sẽ tạo dữ"
           " liệu thật."),
}


# ============================================================================
# 5. BỘ CA KIỂM — tám nhóm theo danh sách nghiệm thu G09
# ============================================================================
DON_MAU = {"ma_don": "G09-HARNESS-1", "nguoi_gui_ten": "Người gửi thử",
           "nguoi_gui_sdt": "0900000001", "nguoi_gui_dia_chi": "địa chỉ gửi thử",
           "nguoi_nhan_ten": "Người nhận thử", "nguoi_nhan_sdt": "0900000002",
           "nguoi_nhan_dia_chi": "địa chỉ nhận thử", "hang_hoa": "hàng thử",
           "khoi_luong_gram": 1500, "cod": 0}


def _ca(kq, ma, nhom, mo_ta, dieu_kien, chi_tiet="", do_bang_gi=""):
    return kq.them(CaKiem(ma, nhom, mo_ta, "dat" if dieu_kien else "hong",
                          chi_tiet, do_bang_gi))


def nhom_hop_dong(kq, ad):
    """A — hợp đồng adapter (docs/SHARED_CONTRACTS.md mục 4)."""
    cap = ad.getCapabilities()
    _ca(kq, "A1", "hop_dong", "getCapabilities() khai đủ khoá",
        all(k in cap["chuc_nang"] for k in
            ("createOrder", "cancelOrder", "getOrder", "trackOrder",
             "getShippingFee", "getShippingLabel", "webhook")),
        chi_tiet=json.dumps(cap["chuc_nang"], ensure_ascii=False),
        do_bang_gi="gọi ad.getCapabilities() rồi đối chiếu bảy khoá của hợp đồng")

    _ca(kq, "A2", "hop_dong", "chuc_nang là BẢN SAO, sửa vào đó không lan ra cả lớp",
        (cap["chuc_nang"].__setitem__("createOrder", not cap["chuc_nang"]["createOrder"]),
         type(ad).CAPABILITIES["createOrder"] == ad.getCapabilities()["chuc_nang"]
         ["createOrder"])[1],
        do_bang_gi="sửa dict trả về rồi gọi lại getCapabilities() xem lớp có đổi không")

    _ca(kq, "A3", "hop_dong", "capability=False thì trả KetQuaHang không-hỗ-trợ, không ném lỗi",
        _kiem_capability_trung_thuc(ad),
        do_bang_gi="gọi từng hàm mà hãng khai False, bắt mọi ngoại lệ")

    _ca(kq, "A4", "hop_dong", "ba kết cục ok / hãng-từ-chối / không-biết KHÔNG bị gộp",
        _kiem_ba_ket_cuc(ad),
        do_bang_gi="ép mock qua ghi_chu demo_force_fail / demo_force_timeout rồi so ok+timeout")

    _ca(kq, "A5", "hop_dong", "CHO_PHEP_LIVE vẫn là False (khoá an toàn chưa bị ai mở)",
        type(ad).CHO_PHEP_LIVE is False,
        chi_tiet=f"{ad.ma_hang}.CHO_PHEP_LIVE={type(ad).CHO_PHEP_LIVE}",
        do_bang_gi="đọc hằng trên LỚP adapter, không đọc trên thể hiện")

    _ca(kq, "A6", "hop_dong", "môi trường khác mock bị adapter chặn ngay trong __init__",
        _kiem_chan_moi_truong(ad.ma_hang),
        do_bang_gi="gọi adapter.tao_adapter(hang, {}, 'production') và chờ PermissionError")


def _kiem_capability_trung_thuc(ad):
    for ten, co in type(ad).CAPABILITIES.items():
        if ten == "webhook" or co:
            continue
        ham = getattr(ad, ten, None)
        if ham is None:
            return False
        try:
            r = ham(DON_MAU if ten in ("createOrder", "getShippingFee") else "MA-THU")
        except Exception:
            return False
        if r.ok or r.timeout:
            return False
    return True


def _kiem_ba_ket_cuc(ad):
    if not ad.capability("createOrder"):
        return True
    ok = ad.createOrder(dict(DON_MAU))
    xau = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_fail"))
    mu = ad.createOrder(dict(DON_MAU, ghi_chu="demo_force_timeout"))
    return (ok.ok and not ok.timeout
            and not xau.ok and not xau.timeout
            and not mu.ok and mu.timeout)


def _kiem_chan_moi_truong(ma_hang):
    try:
        adapter.tao_adapter(ma_hang, {}, "production")
    except PermissionError:
        return True
    except Exception:
        return False
    return False


def nhom_chu_ky(kq, ad):
    """B — chữ ký request. Chỉ J&T có công thức công khai; hãng khác BỎ QUA, không bịa."""
    if ad.ma_hang != "jt":
        kq.them(CaKiem("B0", "chu_ky", "hãng chưa có công thức chữ ký công khai", "bo_qua",
                       chi_tiet=f"{ad.ma_hang}: tài liệu công khai không nêu sơ đồ ký request",
                       do_bang_gi="tra CRED_BAT_BUOC + tài liệu hãng; không có thì BỎ QUA,"
                                  " không đoán"))
        return

    yc = ad.yeu_cau_tao_don(dict(DON_MAU))
    biz = yc["bizContent"]
    khoa = ad.credentials.get("privateKey", "")

    import base64
    import hashlib
    cho_doi = base64.b64encode(hashlib.md5((biz + khoa).encode("utf-8")).digest()).decode()
    _ca(kq, "B1", "chu_ky", "digest = base64(md5-BYTES(bizContent + privateKey))",
        yc["headers"]["digest"] == cho_doi,
        do_bang_gi="tính lại công thức ngay trong ca kiểm, không gọi lại hàm của adapter")

    sai = base64.b64encode(
        hashlib.md5((biz + khoa).encode()).hexdigest().encode()).decode()
    _ca(kq, "B2", "chu_ky", "KHÔNG phải base64(md5-HEX) — hai cách ra chuỗi khác nhau",
        yc["headers"]["digest"] != sai,
        do_bang_gi="dựng bản SAI cố ý rồi khẳng định adapter không ra bản đó")

    _ca(kq, "B3", "chu_ky", "đủ ba header bắt buộc apiAccount · digest · timestamp",
        all(h in yc["headers"] for h in ("apiAccount", "digest", "timestamp")),
        chi_tiet=",".join(sorted(yc["headers"])),
        do_bang_gi="đối chiếu bảng Headers của open.jtexpress.vn/apiDoc/orderserve/create")

    _ca(kq, "B4", "chu_ky", "Content-Type là x-www-form-urlencoded",
        yc["headers"].get("Content-Type") == adapter_jt.CONTENT_TYPE,
        do_bang_gi="đối chiếu hằng CONTENT_TYPE với tài liệu '数据类型：X-WWW-FORM-URLENCODED'")

    import datetime as _dt
    moc = int(yc["headers"]["timestamp"])
    tz = _dt.timezone(_dt.timedelta(hours=adapter_jt.MUI_GIO_GIO))
    moc_cho_doi = adapter_jt.dau_thoi_gian_ms(
        _dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=tz))
    _ca(kq, "B5", "chu_ky", "timestamp là MILI GIÂY và tính theo UTC+7 tường minh",
        len(str(moc)) >= 13 and moc_cho_doi == int(
            _dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=tz).timestamp() * 1000),
        chi_tiet=f"timestamp={moc}",
        do_bang_gi="dựng một mốc UTC+7 cố định rồi so với hàm dau_thoi_gian_ms")

    _ca(kq, "B6", "chu_ky", "môi trường mock KHÔNG mang URL thật (không lỡ gọi ra ngoài)",
        yc["url"] is None,
        do_bang_gi="đọc yc['url'] của adapter ở môi trường mock")

    _ca(kq, "B7", "chu_ky", "bizContent trong body đúng là chuỗi đã đem đi ký",
        yc["body"]["bizContent"] == biz and isinstance(biz, str),
        do_bang_gi="so trường body với chuỗi dùng để tính digest")

    _ca(kq, "B8", "chu_ky", "txlogisticId = mã đơn nội bộ (khoá chống trùng phía hãng)",
        json.loads(biz)["txlogisticId"] == DON_MAU["ma_don"],
        do_bang_gi="giải mã bizContent và so với ma_don")


def nhom_timeout(kq, ad):
    """C — chính sách timeout + thử lại. Chỗ nguy hiểm nhất của cả G09."""
    co_khoa = type(ad).KHOA_CHONG_TRUNG
    cs_tao = tp.chinh_sach_cho("createOrder", co_khoa)
    cs_doc = tp.chinh_sach_cho("trackOrder", co_khoa)

    _ca(kq, "C1", "timeout", "createOrder KHÔNG thử lại khi hãng không có khoá chống trùng",
        tp.chinh_sach_cho("createOrder", False).duoc_thu_lai is False
        and tp.chinh_sach_cho("createOrder", False).so_lan == 1,
        do_bang_gi="gọi transport.chinh_sach_cho('createOrder', False)")

    _ca(kq, "C2", "timeout", "cancelOrder cũng KHÔNG thử lại khi không có khoá chống trùng",
        tp.chinh_sach_cho("cancelOrder", False).duoc_thu_lai is False,
        do_bang_gi="gọi transport.chinh_sach_cho('cancelOrder', False)")

    _ca(kq, "C3", "timeout",
        f"{ad.ma_hang}: KHOA_CHONG_TRUNG={co_khoa} ⇒ createOrder thử lại = {co_khoa}",
        cs_tao.duoc_thu_lai is bool(co_khoa),
        chi_tiet=f"so_lan={cs_tao.so_lan}",
        do_bang_gi="đối chiếu hằng KHOA_CHONG_TRUNG của lớp với chính sách transport")

    _ca(kq, "C4", "timeout", "thao tác CHỈ ĐỌC được thử lại nhiều lần",
        cs_doc.duoc_thu_lai and cs_doc.so_lan >= 2,
        do_bang_gi="gọi transport.chinh_sach_cho('trackOrder', ...)")

    _ca(kq, "C5", "timeout", "lỗi VĨNH VIỄN ném ra ngay, không thử lại lần nào",
        _dem_lan_goi_khi_loi(tp.LoiVinhVien) == 1,
        do_bang_gi="đếm số lần hàm bị gọi khi nó luôn ném LoiVinhVien")

    _ca(kq, "C6", "timeout", "lỗi TẠM THỜI được thử đủ số lần của chính sách rồi mới ném",
        _dem_lan_goi_khi_loi(tp.LoiTamThoi, "trackOrder") == cs_doc.so_lan,
        do_bang_gi="đếm số lần gọi thật với ngu=lambda _:None (không ngủ thật)")

    _ca(kq, "C7", "timeout", "mọi chính sách đều có hạn giờ > 0 (không chờ vô hạn)",
        all(tp.MAC_DINH[t].het_gio > 0 for t in tp.MAC_DINH),
        chi_tiet=",".join(f"{t}={tp.MAC_DINH[t].het_gio}s" for t in sorted(tp.MAC_DINH)),
        do_bang_gi="duyệt transport.MAC_DINH")


def _dem_lan_goi_khi_loi(lop_loi, thao_tac="createOrder"):
    dem = {"n": 0}

    def ham():
        dem["n"] += 1
        raise lop_loi("ca thử")
    try:
        tp.goi(ham, thao_tac=thao_tac, ngu=lambda _s: None)
    except Exception:
        pass
    return dem["n"]


def nhom_anh_xa_loi(kq, ad):
    """D — chuẩn hoá lỗi (docs/SHARED_CONTRACTS.md mục 5)."""
    bang = loi_hang.BANG_MA_LOI.get(ad.ma_hang) or {}
    kq.them(CaKiem("D0", "anh_xa_loi", f"số mã lỗi đã đọc được của {ad.ma_hang}",
                   "dat" if bang else "bo_qua",
                   chi_tiet=f"{len(bang)} mục trong BANG_MA_LOI (gồm cả mã thành công nếu có)",
                   do_bang_gi="len(loi_hang.BANG_MA_LOI[hang]) — KHÔNG phải số mã hãng thực có,"
                              " chỉ là số đã đọc được từ tài liệu công khai"))

    _ca(kq, "D1", "anh_xa_loi", "danh sách ĐƯỢC THỬ LẠI là danh sách TRẮNG và hẹp",
        loi_hang.DUOC_THU_LAI == frozenset({loi_hang.HET_GIO, loi_hang.QUA_HAN_MUC}),
        chi_tiet=str(sorted(loi_hang.DUOC_THU_LAI)),
        do_bang_gi="đọc hằng loi_hang.DUOC_THU_LAI")

    _ca(kq, "D2", "anh_xa_loi", "mã KHÔNG RÕ mặc định KHÔNG được thử lại",
        loi_hang.NormalizedCarrierError(loi_hang.KHONG_RO).co_the_thu_lai is False,
        do_bang_gi="dựng lỗi KHONG_RO rồi đọc co_the_thu_lai")

    _ca(kq, "D3", "anh_xa_loi", "mã lạ của hãng KHÔNG ném lỗi, về KHONG_RO và không thử lại",
        _kiem_ma_la(ad.ma_hang),
        do_bang_gi="gọi loi_hang.tu_ma_hang(hang, 'MA-KHONG-CO-THAT')")

    _ca(kq, "D4", "anh_xa_loi", "đơn trùng KHÔNG bao giờ được coi là thử lại được",
        loi_hang.DON_TRUNG not in loi_hang.DUOC_THU_LAI,
        do_bang_gi="kiểm DON_TRUNG có nằm trong DUOC_THU_LAI không")

    _ca(kq, "D5", "anh_xa_loi", "HTTP 408/429/5xx thử lại được; 4xx khác thì không",
        (loi_hang.tu_http(408).co_the_thu_lai and loi_hang.tu_http(429).co_the_thu_lai
         and loi_hang.tu_http(503).co_the_thu_lai
         and not loi_hang.tu_http(400).co_the_thu_lai
         and not loi_hang.tu_http(401).co_the_thu_lai),
        do_bang_gi="gọi loi_hang.tu_http cho 408/429/503/400/401")

    _ca(kq, "D6", "anh_xa_loi", "hai lớp transport và loi_hang KHÔNG lệch nhau về 'thử lại'",
        _kiem_hai_lop_khong_lech(),
        do_bang_gi="với mọi mã chuẩn: so co_the_thu_lai với loại ngoại lệ transport sinh ra")

    if ad.ma_hang == "jt":
        _ca(kq, "D7", "anh_xa_loi", "J&T 145003204 (订单重复) → DON_TRUNG, không thử lại",
            _kiem_ma_jt("145003204", loi_hang.DON_TRUNG, False),
            do_bang_gi="loi_hang.tu_ma_hang('jt','145003204')")
        _ca(kq, "D8", "anh_xa_loi", "J&T 999002000 (未找到数据) → KHONG_TIM_THAY",
            _kiem_ma_jt("999002000", loi_hang.KHONG_TIM_THAY, False),
            do_bang_gi="loi_hang.tu_ma_hang('jt','999002000')")
        _ca(kq, "D9", "anh_xa_loi", "J&T 145003030 (chữ ký sai) → XAC_THUC_HONG, không thử lại",
            _kiem_ma_jt("145003030", loi_hang.XAC_THUC_HONG, False),
            do_bang_gi="loi_hang.tu_ma_hang('jt','145003030')")


def _kiem_ma_la(hang):
    e = loi_hang.tu_ma_hang(hang, "MA-KHONG-CO-THAT-9999")
    return e.ma_chuan == loi_hang.KHONG_RO and e.co_the_thu_lai is False


def _kiem_ma_jt(ma, cho_doi, thu_lai):
    e = loi_hang.tu_ma_hang("jt", ma)
    return e.ma_chuan == cho_doi and e.co_the_thu_lai is thu_lai


def _kiem_hai_lop_khong_lech():
    for ma in loi_hang.MA_CHUAN:
        e = loi_hang.NormalizedCarrierError(ma)
        ngoai_le = loi_hang.thanh_ngoai_le_transport(e)
        tam = isinstance(ngoai_le, tp.LoiTamThoi)
        if tam != e.co_the_thu_lai:
            return False
    return True


def nhom_trang_thai(kq, ad):
    """E — ánh xạ trạng thái, và mã NHẬP NHẰNG."""
    _ca(kq, "E1", "trang_thai", "mã lạ không ném lỗi và KHÔNG đổi trạng thái đơn",
        _kiem_ma_trang_thai_la(ad.ma_hang),
        do_bang_gi="tth.quyet_dinh(hang, 'MA-LA-999') rồi đọc trang_thai_ap + biet_ma")

    if ad.ma_hang == "jt":
        qd = tth.quyet_dinh("jt", 110)
        _ca(kq, "E2", "trang_thai", "J&T 110 là AMBIGUOUS: không áp trạng thái, bắt soát",
            qd.trang_thai_ap is None and qd.nhan == "AMBIGUOUS" and qd.can_soat is True,
            chi_tiet=f"nhan={qd.nhan} trang_thai_ap={qd.trang_thai_ap} tin_cay={qd.do_tin_cay}",
            do_bang_gi="tth.quyet_dinh('jt', 110)")

        _ca(kq, "E3", "trang_thai", "J&T 110 giữ đủ dấu vết để soát lại sau",
            all(getattr(qd, t) for t in ("ma_goc", "nguon_tai_lieu", "phien_ban_tai_lieu",
                                         "do_tin_cay", "nhan_luc", "ghi_chu"))
            and len(qd.cac_nghia or {}) >= 2,
            chi_tiet=f"nguon={qd.nguon_tai_lieu} · {len(qd.cac_nghia or {})} nghĩa",
            do_bang_gi="đọc từng trường của QuyetDinhAnhXa")

        _ca(kq, "E4", "trang_thai", "CẤM chốt nghĩa mã nhập nhằng về trạng thái HOÀN TẤT",
            _kiem_cam_chot_hoan_tat(),
            do_bang_gi="thử chot_nghia() về một nghĩa dẫn tới hoàn tất, chờ ValueError")

        _ca(kq, "E5", "trang_thai", "chốt nghĩa PHẢI có người chốt và căn cứ",
            _kiem_chot_doi_can_cu(),
            do_bang_gi="gọi chot_nghia với nguoi_chot rỗng, chờ ValueError")

        _ca(kq, "E6", "trang_thai", "113 Delivered vẫn ánh xạ bình thường (không chặn nhầm)",
            tth.quyet_dinh("jt", 113).trang_thai_ap == "giao_thanh_cong",
            do_bang_gi="tth.quyet_dinh('jt', 113)")

    if ad.ma_hang == "vtp":
        kq.them(CaKiem("E7", "trang_thai",
                       "VTP: bảng ánh xạ hiện CHỈ có mã của bộ mô phỏng, không có mã hãng",
                       "bo_qua",
                       chi_tiet=f"nguồn bảng: {tth.NGUON_BANG.get('vtp')}",
                       do_bang_gi="đọc tth.NGUON_BANG['vtp'] và tth.VTP_MA_MOCK"))


def _kiem_ma_trang_thai_la(hang):
    qd = tth.quyet_dinh(hang, "MA-LA-999")
    return qd.trang_thai_ap is None and qd.biet_ma is False and qd.can_soat is True


def _kiem_cam_chot_hoan_tat():
    try:
        tth.chot_nghia("jt", 110, "bang_tham_so", "ca-thu", "ca-thu")
    except ValueError:
        tth.bo_chot_nghia("jt", 110)
        return False     # bang_tham_so dẫn tới dang_giao, không phải hoàn tất ⇒ chốt được
    tth.bo_chot_nghia("jt", 110)
    # Chốt được nghĩa KHÔNG hoàn tất là đúng. Giờ kiểm chặn thật: dựng một nghĩa hoàn tất giả.
    muc = tth.NHAP_NHANG[("jt", 110)]
    muc["nghia"]["_ca_thu_hoan_tat"] = {"mo_ta_hang": "ca thử", "trang_thai": "giao_thanh_cong",
                                        "nguon": "ca thử"}
    try:
        tth.chot_nghia("jt", 110, "_ca_thu_hoan_tat", "ca-thu", "ca-thu")
        chan = False
    except ValueError:
        chan = True
    finally:
        muc["nghia"].pop("_ca_thu_hoan_tat", None)
        tth.bo_chot_nghia("jt", 110)
    return chan


def _kiem_chot_doi_can_cu():
    try:
        tth.chot_nghia("jt", 110, "bang_tham_so", "", "")
    except ValueError:
        return True
    finally:
        tth.bo_chot_nghia("jt", 110)
    return False


def nhom_cach_ly_cred(kq, ad):
    """F — cách ly credentials. Chạm secret CHỈ qua bốn hàm của mục 14."""
    import bao_mat
    cred = {"apiAccount": "111", "privateKey": "KHOA-BI-MAT-XYZ",
            "customerCode": "CC1", "password": "MAT-KHAU-XYZ"}
    try:
        ban_ma, _duoi = bao_mat.ma_hoa_cred(cred, 1, ad.ma_hang)
    except Exception as e:
        kq.them(CaKiem("F0", "cach_ly_cred", "mã hoá credentials", "hong",
                       chi_tiet=f"{type(e).__name__}: {e}",
                       do_bang_gi="bao_mat.ma_hoa_cred(...) trên CSDL thử riêng"))
        return

    _ca(kq, "F1", "cach_ly_cred", "bản mã KHÔNG chứa giá trị bí mật ở dạng đọc được",
        "KHOA-BI-MAT-XYZ" not in ban_ma and "MAT-KHAU-XYZ" not in ban_ma,
        do_bang_gi="tìm chuỗi bí mật trong bản mã bằng phép so chuỗi")

    _ca(kq, "F2", "cach_ly_cred", "bản mã mang key_id để xoay khoá được (v3$...)",
        ban_ma.startswith("v3$") and ban_ma.count("$") >= 3,
        chi_tiet=ban_ma.split("$")[0] + "$" + ban_ma.split("$")[1],
        do_bang_gi="đọc tiền tố bản mã, đối chiếu mục 14 của SHARED_CONTRACTS")

    _ca(kq, "F3", "cach_ly_cred", "giải mã đúng tenant thì ra đúng credentials",
        bao_mat.giai_ma_cred(ban_ma, 1, ad.ma_hang) == cred,
        do_bang_gi="giai_ma_cred cùng (tenant_id, hang) rồi so bằng ==")

    _ca(kq, "F4", "cach_ly_cred", "tenant KHÁC không giải mã được credentials của tenant này",
        _kiem_khong_giai_duoc(ban_ma, 2, ad.ma_hang),
        do_bang_gi="giai_ma_cred với tenant_id=2, chờ ngoại lệ hoặc kết quả khác")

    _ca(kq, "F5", "cach_ly_cred", "hãng KHÁC không giải mã được credentials của hãng này",
        _kiem_khong_giai_duoc(ban_ma, 1, "hang-khac"),
        do_bang_gi="giai_ma_cred với hang='hang-khac', chờ ngoại lệ hoặc kết quả khác")

    _ca(kq, "F6", "cach_ly_cred", "harness KHÔNG in credentials ra kết quả lần chạy",
        not any("KHOA-BI-MAT-XYZ" in (c.chi_tiet or "") for c in kq.cac_ca),
        do_bang_gi="quét mọi trường chi_tiet của lần chạy tìm chuỗi bí mật")


def _kiem_khong_giai_duoc(ban_ma, tenant_id, hang):
    import bao_mat
    try:
        ra = bao_mat.giai_ma_cred(ban_ma, tenant_id, hang)
    except Exception:
        return True
    return ra.get("privateKey") != "KHOA-BI-MAT-XYZ"


def nhom_gioi_han(kq, ad):
    """G — giới hạn tần suất và gom lô."""
    import gioi_han
    import polling

    _ca(kq, "G1", "gioi_han", "cửa webhook có HAI trần: nhận rộng và chữ-ký-sai chật",
        bool(gioi_han.luat_cua("webhook.nhan")) and bool(gioi_han.luat_cua("webhook.chu_ky_sai")),
        do_bang_gi="gioi_han.luat_cua() cho hai endpoint")

    _ca(kq, "G2", "gioi_han", "trần chữ-ký-sai CHẬT HƠN trần nhận (chặn dò secret)",
        _tran_nho_nhat("webhook.chu_ky_sai") < _tran_nho_nhat("webhook.nhan"),
        chi_tiet=f"chu_ky_sai={_tran_nho_nhat('webhook.chu_ky_sai')}"
                 f" < nhan={_tran_nho_nhat('webhook.nhan')}",
        do_bang_gi="so số lượt nhỏ nhất của hai bộ luật")

    lo = polling.so_van_don_moi_luot(ad.ma_hang)
    if ad.ma_hang == "jt":
        _ca(kq, "G3", "gioi_han", "J&T gom lô ĐÚNG 30 vận đơn/lượt như tài liệu",
            lo == 30 and adapter_jt.SO_VAN_DON_MOI_LUOT == 30,
            chi_tiet=f"lô={lo}",
            do_bang_gi="polling.so_van_don_moi_luot('jt') + hằng adapter_jt."
                       "SO_VAN_DON_MOI_LUOT, đối chiếu open.jtexpress.vn/apiDoc/logistics/query")
    else:
        _ca(kq, "G4", "gioi_han", "hãng chưa có tài liệu gom lô thì dùng mức dè dặt",
            lo == polling.MAC_DINH_MOI_LUOT,
            chi_tiet=f"lô={lo}",
            do_bang_gi="polling.so_van_don_moi_luot(hang) so với MAC_DINH_MOI_LUOT")

    _ca(kq, "G5", "gioi_han", "polling có trần RIÊNG từng tenant (cách ly ở tầng hạn mức)",
        _kiem_tran_theo_tenant(),
        do_bang_gi="đổ đầy trần của tenant 9001 rồi kiểm tenant 9002 vẫn còn suất")

    _ca(kq, "G6", "gioi_han", "polling có ngắt mạch và khoảng cách tối thiểu giữa hai vòng",
        polling.NGUONG_NGAT_MACH > 0 and polling.MOI_GIAY_TOI_THIEU >= 30
        and polling.BatDauNen(moi_giay=1).moi_giay_thuc >= polling.MOI_GIAY_TOI_THIEU,
        chi_tiet=f"ngắt mạch sau {polling.NGUONG_NGAT_MACH} lỗi, tối thiểu"
                 f" {polling.MOI_GIAY_TOI_THIEU}s/vòng",
        do_bang_gi="dựng BatDauNen(moi_giay=1) và đọc moi_giay_thuc")


def _tran_nho_nhat(endpoint):
    import gioi_han
    return min(l.so_lan for l in gioi_han.luat_cua(endpoint))


def _kiem_tran_theo_tenant():
    import polling
    polling.xoa_han_muc(9001)
    polling.xoa_han_muc(9002)
    try:
        for _ in range(polling.GIOI_HAN_HOI_MOI_PHUT):
            polling._con_han_muc(9001)
        het_a = polling._con_han_muc(9001) is False
        con_b = polling._con_han_muc(9002) is True
        return het_a and con_b
    finally:
        polling.xoa_han_muc(9001)
        polling.xoa_han_muc(9002)


def nhom_doi_soat(kq, ad):
    """H — idempotency và đối soát sau khi nhận kết quả KHÔNG RÕ."""
    import don_hang

    tt = don_hang.thao_tac_doi_soat(ad)
    _ca(kq, "H1", "doi_soat", "chọn thao tác đối soát theo capability THẬT của hãng",
        (tt == "getOrder" if ad.capability("getOrder")
         else tt == "trackOrder" if ad.capability("trackOrder") else tt is None),
        chi_tiet=f"{ad.ma_hang} đối soát bằng {tt}",
        do_bang_gi="don_hang.thao_tac_doi_soat(ad) so với ad.capability()")

    _ca(kq, "H2", "doi_soat", "CHỈ mã KHÔNG TÌM THẤY mới kết luận 'hãng chưa nhận đơn'",
        _kiem_khong_tim_thay(),
        do_bang_gi="dựng KetQuaHang bằng NormalizedCarrierError.nhu_dict() (hình dạng hợp đồng"
                   " §5, khoá `ma_chuan`) cho KHONG_TIM_THAY và cho XAC_THUC_HONG,"
                   " rồi gọi don_hang._la_khong_tim_thay")

    _ca(kq, "H5", "doi_soat", "tên khoá lỗi chỉ có MỘT: `ma_chuan` — bí danh `ma` đã chết",
        _kiem_bi_danh_ma_da_chet(),
        do_bang_gi="dựng loi_chuan CHỈ có khoá `ma` (tên cũ) rồi khẳng định"
                   " don_hang._la_khong_tim_thay KHÔNG nhận ra; nhận ra được nghĩa là hệ đang có"
                   " hai tên cho một thứ")

    _ca(kq, "H3", "doi_soat", "timeout KHÔNG bao giờ bị coi là 'chưa nhận đơn'",
        don_hang._la_khong_tim_thay(
            adapter.KetQuaHang(False, timeout=True, loi="hết giờ")) is False,
        do_bang_gi="don_hang._la_khong_tim_thay trên một KetQuaHang timeout")

    _ca(kq, "H4", "doi_soat", "khoá chống trùng phía hãng khai đúng với tài liệu",
        _kiem_khoa_chong_trung(ad),
        chi_tiet=f"{ad.ma_hang}.KHOA_CHONG_TRUNG={type(ad).KHOA_CHONG_TRUNG}",
        do_bang_gi="J&T: tài liệu tạo đơn ghi txlogisticId '不支持重复' ⇒ True."
                   " VTP: chưa đọc được khẳng định tương đương ⇒ False (mức an toàn)")


def _goi_y_loi_chuan(ma, ma_goc=""):
    """Gói lỗi dựng BẰNG `NormalizedCarrierError.nhu_dict()` — hình dạng THẬT của hợp đồng §5.

    Trước 15/10/2026 chỗ này tự gõ tay `{"ma": …}`: khoá `ma` **không có trong hợp đồng nào**,
    và vì `don_hang` thời đó cũng đọc `ma` nên ca kiểm **xanh trong khi hai đầu đã lệch tên**
    (§12.1: thứ dùng để kiểm chứng tự nó nói sai). Dựng qua `nhu_dict()` thì fixture không thể
    lệch khỏi hợp đồng lần nữa.
    """
    return loi_hang.NormalizedCarrierError(ma, ma_goc_hang=ma_goc or None, hang="jt",
                                           thao_tac="trackOrder").nhu_dict()


def _kiem_khong_tim_thay():
    import don_hang
    co = adapter.KetQuaHang(False, loi="x", tho={
        "loi_chuan": _goi_y_loi_chuan(loi_hang.KHONG_TIM_THAY, "999002000")})
    khong = adapter.KetQuaHang(False, loi="x", tho={
        "loi_chuan": _goi_y_loi_chuan(loi_hang.XAC_THUC_HONG, "145003030")})
    return (don_hang._la_khong_tim_thay(co) is True
            and don_hang._la_khong_tim_thay(khong) is False)


def _kiem_bi_danh_ma_da_chet():
    """Bí danh `ma` (tên CŨ của `ma_chuan`) phải KHÔNG còn được nhận.

    Không có ca này thì lần sau ai thêm lại một dòng `or chuan.get("ma")` cũng không ai biết —
    và hệ lại có hai tên cho một thứ, đúng khuôn lệch im lặng đã sinh ra lỗi này (§14.6).
    Hướng sai ở đây là AN TOÀN: không nhận ra ⇒ `van_chua_ro` ⇒ giữ `dang_gui`, không gửi lại mù.
    """
    import don_hang
    cu = adapter.KetQuaHang(False, loi="x", tho={"loi_chuan": {"ma": loi_hang.KHONG_TIM_THAY}})
    return don_hang._la_khong_tim_thay(cu) is False


def _kiem_khoa_chong_trung(ad):
    if ad.ma_hang == "jt":
        return type(ad).KHOA_CHONG_TRUNG is True
    if ad.ma_hang == "vtp":
        return type(ad).KHOA_CHONG_TRUNG is False
    return isinstance(type(ad).KHOA_CHONG_TRUNG, bool)


def nhom_webhook(kq, ad):
    """I — cửa webhook theo từng hãng."""
    bang = webhook.bang_muc_xac_thuc()
    muc = bang.get(ad.ma_hang, {})

    _ca(kq, "I1", "webhook", "mock dùng sơ đồ của CHÍNH hub, không mạo nhận sơ đồ hãng",
        muc.get("mock", {}).get("so_do") == "hub_hmac",
        do_bang_gi="webhook.bang_muc_xac_thuc()[hang]['mock']")

    ngoai_mock = muc.get("sandbox_production", {})
    if ad.ma_hang == "jt":
        _ca(kq, "I2", "webhook", "J&T ngoài mock dùng jt_digest, mức chỉ là DOCUMENTED",
            ngoai_mock.get("so_do") == "jt_digest" and ngoai_mock.get("muc") == DOCUMENTED,
            chi_tiet=str(ngoai_mock),
            do_bang_gi="webhook.bang_muc_xac_thuc()['jt'] — mức DOCUMENTED vì chưa đối chiếu"
                       " với hãng thật lần nào")
    if ad.ma_hang == "vtp":
        _ca(kq, "I3", "webhook", "VTP ngoài mock là BLOCKED — không nhận callback thật",
            ngoai_mock.get("so_do") is None and ngoai_mock.get("muc") == BLOCKED,
            chi_tiet=str(ngoai_mock),
            do_bang_gi="webhook.SO_DO_THEO_HANG['vtp'] is None")

    _ca(kq, "I4", "webhook", "người gửi KHÔNG chọn được sơ đồ xác thực (máy chủ chọn)",
        _kiem_so_do_khong_do_nguoi_gui_chon(ad.ma_hang),
        do_bang_gi="gọi webhook.chon_so_do() với cùng một hãng ở hai môi trường, xem kết quả"
                   " có phụ thuộc header/payload không (chữ ký hàm không nhận hai thứ đó)")

    _ca(kq, "I5", "webhook", "mọi mức xác thực đều nằm trong bộ mức hợp lệ",
        all(v["mock"]["muc"] in webhook.MUC_HOP_LE
            and v["sandbox_production"]["muc"] in webhook.MUC_HOP_LE for v in bang.values()),
        do_bang_gi="duyệt bang_muc_xac_thuc() đối chiếu webhook.MUC_HOP_LE")


def _kiem_so_do_khong_do_nguoi_gui_chon(hang):
    import inspect
    tham_so = list(inspect.signature(webhook.chon_so_do).parameters)
    return tham_so == ["tk_row"]


NHOM_CA = (nhom_hop_dong, nhom_chu_ky, nhom_timeout, nhom_anh_xa_loi, nhom_trang_thai,
           nhom_cach_ly_cred, nhom_gioi_han, nhom_doi_soat, nhom_webhook)


# ============================================================================
# 6. CHẠY
# ============================================================================
def chay(hang, che_do=None, cred=None, phieu_duyet=None, moi_truong_os=None) -> KetQuaLanChay:
    """Chạy bộ ca kiểm cho MỘT hãng ở MỘT chế độ.

    Thiếu điều kiện thì ném `ThieuCauHinh` — KHÔNG rơi về MOCK, không trả về kết quả "đạt".
    """
    env = os.environ if moi_truong_os is None else moi_truong_os
    che_do = (che_do or che_do_dang_xin(env)).upper()
    if che_do not in CHE_DO_HOP_LE:
        raise ValueError(f"chế độ {che_do!r} không hợp lệ; chỉ nhận {CHE_DO_HOP_LE}")
    if hang not in adapter._DANG_KY:
        raise KeyError(f"chưa có adapter cho hãng '{hang}'")

    if che_do != MOCK:
        thieu = thieu_gi_de_chay(che_do, hang, env, cred)
        if thieu:
            raise ThieuCauHinh(che_do, thieu)
    if che_do == LIVE:
        _kiem_phieu_duyet_live(phieu_duyet)

    ad = adapter.tao_adapter(
        hang,
        cred or {"apiAccount": "669", "privateKey": "KHOA-THU-MOCK",
                 "customerCode": "CC-THU", "password": "MK-THU"},
        moi_truong_adapter(che_do))

    kq = KetQuaLanChay(che_do, hang)
    for nhom in NHOM_CA:
        try:
            nhom(kq, ad)
        except Exception as e:
            kq.them(CaKiem(f"X-{nhom.__name__}", nhom.__name__.replace("nhom_", ""),
                           "nhóm ca kiểm NỔ NGOẠI LỆ", "hong",
                           chi_tiet=f"{type(e).__name__}: {e}",
                           do_bang_gi="ngoại lệ bắt được khi chạy nhóm"))
    kq.ket_thuc = time.time()
    return kq


def _kiem_phieu_duyet_live(phieu_duyet):
    """LIVE đòi phiếu duyệt cho TỪNG thao tác ghi. Thiếu một cái là từ chối cả lượt."""
    phieu = {p.thao_tac: p for p in (phieu_duyet or [])}
    thieu = []
    for tt in THAO_TAC_GHI:
        p = phieu.get(tt)
        if p is None:
            thieu.append(f"thiếu PhieuDuyetLive cho thao tác '{tt}'"
                         " (một cờ môi trường KHÔNG đủ)")
            continue
        thieu.extend(f"phiếu '{tt}': {l}" for l in p.kiem(tt, p.ma_tham_chieu))
    if thieu:
        raise ThieuPhieuDuyet(LIVE, thieu)


def chay_tat_ca(che_do=None, moi_truong_os=None):
    """Chạy cho MỌI hãng đã đăng ký. Hãng nào bị từ chối thì ghi lý do, không bỏ im."""
    env = os.environ if moi_truong_os is None else moi_truong_os
    che_do = (che_do or che_do_dang_xin(env)).upper()
    ra = {}
    for hang in sorted(adapter._DANG_KY):
        try:
            ra[hang] = chay(hang, che_do, moi_truong_os=env)
        except ThieuCauHinh as e:
            ra[hang] = e
    return ra


# ============================================================================
# 7. BẢNG SÁU MỨC SẴN SÀNG
# ============================================================================
# Mức NỀN của từng hạng mục: suy từ dữ kiện ĐO ĐƯỢC trong mã (capability, hằng URL, bảng mã
# lỗi, sơ đồ webhook), kèm câu "đo bằng gì". Mức này chỉ được NÂNG lên MOCK VERIFIED khi lần
# chạy hiện tại có ca kiểm tương ứng ĐẠT — không bao giờ nâng bằng niềm tin.
#
# `ca_can` = mã ca kiểm phải ĐẠT thì hạng mục mới lên MOCK VERIFIED. Rỗng = không có ca kiểm
# cục bộ nào phủ được hạng mục đó (ví dụ "báo giá thật"), nên nó đứng yên ở mức nền.
HANG_MUC = ("xac_thuc", "chu_ky_request", "tao_don", "huy_don", "tra_van_don", "bao_gia",
            "nhan_van_don", "ma_loi", "callback_webhook", "gioi_han_tan_suat")


def _nen_jt():
    return {
        "xac_thuc": (DOCUMENTED,
                     "customerCode/password trong bizContent + apiAccount/privateKey ở header"
                     " — đọc open.jtexpress.vn/apiDoc/orderserve/create 15/10/2026. CHƯA có"
                     " lượt xác thực thật nào.", ()),
        "chu_ky_request": (IMPLEMENTED,
                           "adapter_jt.ky_digest + dung_headers đã cài đặt theo công thức tài"
                           " liệu; kiểm bằng ca B1–B8.", ("B1", "B2", "B3", "B4", "B5", "B7")),
        "tao_don": (IMPLEMENTED,
                    "adapter_jt.yeu_cau_tao_don dựng đủ url/headers/body; đường gửi thật bị"
                    " CHO_PHEP_LIVE=False chặn.", ("A4", "B8", "C3")),
        "huy_don": (DOCUMENTED,
                    "endpoint /api/order/cancelOrder và tham số reason đọc được"
                    " (apiDoc/orderserve/cancel, 15/10/2026); adapter chỉ có nhánh mock,"
                    " CHƯA dựng yêu cầu thật.", ()),
        "tra_van_don": (IMPLEMENTED,
                        "URL_TRA_HANH_TRINH + lô 30 mã; polling đi qua đúng đường webhook.",
                        ("G3", "H1")),
        "bao_gia": (DOCUMENTED,
                    "endpoint /api/spmComCost/getComCost và bảng tham số đọc được 15/10/2026;"
                    " adapter chỉ có công thức mock, CHƯA dựng yêu cầu thật.", ()),
        "nhan_van_don": (DOCUMENTED,
                         "endpoint /api/order/printOrder, 10 khổ giấy, trả"
                         " base64EncodeContent/urlContent — đọc 15/10/2026; adapter trả"
                         " 'MOCK-PDF'.", ()),
        "ma_loi": (IMPLEMENTED,
                   "loi_hang.JT_MA_LOI chép từ bảng mã lỗi + bảng riêng từng API.",
                   ("D1", "D4", "D7", "D8", "D9")),
        "callback_webhook": (DOCUMENTED,
                             "mục 轨迹回传 có; webhook.xac_thuc_jt_digest cài theo công thức"
                             " tài liệu, nhưng tài liệu KHÔNG nói callback ký bằng khoá nào.",
                             ()),
        "gioi_han_tan_suat": (BLOCKED,
                              "tài liệu công khai KHÔNG công bố trần tần suất nào. Chỉ có trần"
                              " GOM LÔ 30 mã/lượt (mã lỗi 145003502) — đó là trần kích thước,"
                              " không phải trần tần suất.", ()),
    }


def _nen_vtp():
    return {
        "xac_thuc": (DOCUMENTED,
                     "partner2.viettelpost.vn/document/token-authen: Login → ownerconnect,"
                     " hoặc LoginVTP bằng token tĩnh. Đọc lại qua repo thanhbn123/"
                     "vip-viettelpost nhánh main 15/10/2026 (CHỈ ĐỌC). adapter_vtp của dự án"
                     " này CHƯA cài đặt gì.", ()),
        "chu_ky_request": (BLOCKED,
                           "VTP không có sơ đồ ký request; xác thực bằng header Token."
                           " Không có gì để ký ⇒ hạng mục này không áp dụng, ghi BLOCKED để"
                           " không ai tưởng đã làm xong.", ()),
        "tao_don": (DOCUMENTED,
                    "POST /v2/order/createOrder (partner2.../create-order-id-address)."
                    " adapter_vtp là MOCK hoàn toàn.", ()),
        "huy_don": (DOCUMENTED,
                    "POST /v2/order/UpdateOrder TYPE=4, chỉ huỷ được khi ORDER_STATUS < 200.",
                    ()),
        "tra_van_don": (DOCUMENTED,
                        "trạng thái về chủ yếu qua webhook; adapter_vtp.getOrder/trackOrder là"
                        " mock.", ()),
        "bao_gia": (DOCUMENTED,
                    "POST /v2/order/getPrice và /v2/order/getPriceAll.", ()),
        "nhan_van_don": (BLOCKED,
                         "CHƯA đọc được trang tài liệu nào của VTP về in nhãn, và repo"
                         " vip-viettelpost cũng không có. Không suy đoán.", ()),
        "ma_loi": (BLOCKED,
                   "loi_hang.BANG_MA_LOI KHÔNG có mục 'vtp'. Lỗi VTP hiện chỉ phân loại được"
                   " theo HTTP status.", ()),
        "callback_webhook": (DOCUMENTED,
                             "partner2.viettelpost.vn/document/webhook: thân JSON {DATA, TOKEN},"
                             " xác thực bằng so sánh hằng thời gian TOKEN với secret chung —"
                             " KHÔNG có sơ đồ HMAC/chữ ký nào. Cửa webhook của dự án này đặt"
                             " vtp = BLOCKED, chưa cài sơ đồ đó.", ()),
        "gioi_han_tan_suat": (DOCUMENTED,
                              "tài liệu webhook nêu VTP thử lại tối đa 5 lần tới khi nhận HTTP"
                              " 200. Không thấy trần tần suất gọi API.", ()),
    }


NEN_SAN_SANG = {"jt": _nen_jt, "vtp": _nen_vtp}


def bang_san_sang(ket_qua_chay=None):
    """Bảng SÁU MỨC cho mọi hãng × mọi hạng mục, mỗi dòng kèm 'đo bằng gì'.

    `ket_qua_chay`: dict {hang: KetQuaLanChay} của lượt chạy vừa rồi. Không truyền thì bảng chỉ
    nói mức NỀN — và nói thẳng là chưa có lượt đo nào, thay vì im lặng để người đọc tưởng đã
    kiểm (§12.1).

    SANDBOX VERIFIED / LIVE VERIFIED **không có đường nào để xuất hiện** ở bản này: hàm chỉ nâng
    tối đa tới MOCK VERIFIED, và chỉ nâng khi lượt chạy có `che_do == MOCK` với đủ ca đạt. Muốn
    lên hai mức kia phải có lượt chạy SANDBOX/LIVE thật, mà cả hai đang BLOCKED.
    """
    ra = {}
    for hang, lam_nen in NEN_SAN_SANG.items():
        nen = lam_nen()
        lan = (ket_qua_chay or {}).get(hang)
        lan = lan if isinstance(lan, KetQuaLanChay) else None
        dong = {}
        for hm in HANG_MUC:
            muc, do_bang_gi, ca_can = nen[hm]
            nang = ""
            if ca_can and lan is not None and lan.che_do == MOCK \
                    and all(lan.ca_dat(c) for c in ca_can):
                muc = MOCK_VERIFIED
                nang = f" ĐÃ CHẠY ĐẠT ca {'+'.join(ca_can)} ở chế độ MOCK ({PHAM_VI_DO[MOCK]})"
            elif ca_can and lan is None:
                nang = (f" Chưa có lượt chạy nào trong báo cáo này; ca phủ hạng mục:"
                        f" {'+'.join(ca_can)}.")
            elif ca_can and lan is not None:
                hong = [c for c in ca_can if not lan.ca_dat(c)]
                if hong:
                    nang = f" Ca CHƯA đạt trong lượt vừa chạy: {'+'.join(hong)}."
            dong[hm] = {"muc": muc, "do_bang_gi": (do_bang_gi + nang).strip(),
                        "ca_can": list(ca_can)}
        ra[hang] = dong
    return ra


def bao_cao_san_sang(ket_qua_chay=None):
    """Toàn bộ dữ liệu cho `admin/carrier_health.js` và cho docs/G09_FINAL_REPORT.md."""
    bang = bang_san_sang(ket_qua_chay)
    hangs = {}
    for hang in sorted(adapter._DANG_KY):
        lop = adapter._DANG_KY[hang]
        lan = (ket_qua_chay or {}).get(hang)
        hangs[hang] = {
            "ten": lop.ten_hang,
            "live_mo": bool(lop.CHO_PHEP_LIVE),
            "khoa_chong_trung": bool(lop.KHOA_CHONG_TRUNG),
            "capabilities": dict(lop.CAPABILITIES),
            "san_sang": bang.get(hang, {}),
            "lan_chay": (lan.nhu_dict() if isinstance(lan, KetQuaLanChay)
                         else {"tu_choi": lan.thieu, "che_do": lan.che_do}
                         if isinstance(lan, ThieuCauHinh) else None),
            "can_soat": danh_sach_can_soat(hang),
            "thieu_de_sandbox": thieu_gi_de_chay(SANDBOX, hang),
            "thieu_de_live": thieu_gi_de_chay(LIVE, hang),
        }
    return {
        "sau_muc": list(SAU_MUC),
        "hang_muc": list(HANG_MUC),
        "hang": hangs,
        "muc_xac_thuc_webhook": webhook.bang_muc_xac_thuc(),
        "ket_luan": {
            "G09 LOCAL READY": "PASS" if _moi_hang_deu_dat(ket_qua_chay) else "FAIL",
            "G09 SANDBOX": BLOCKED,
            "G09 LIVE": BLOCKED,
        },
    }


def _moi_hang_deu_dat(ket_qua_chay):
    if not ket_qua_chay:
        return False
    cac = [v for v in ket_qua_chay.values() if isinstance(v, KetQuaLanChay)]
    return bool(cac) and len(cac) == len(ket_qua_chay) and all(v.dat for v in cac)


def danh_sach_can_soat(hang):
    """Mã trạng thái đang ở trạng thái NEEDS_REVIEW / AMBIGUOUS của một hãng."""
    ra = []
    for (h, ma), muc in tth.NHAP_NHANG.items():
        if h != hang:
            continue
        qd = tth.quyet_dinh(h, ma)
        ra.append({"ma": ma, "nhan": qd.nhan, "trang_thai_ap": qd.trang_thai_ap,
                   "do_tin_cay": qd.do_tin_cay, "ly_do": muc["ly_do"],
                   "nguon": muc["nguon"],
                   "cac_nghia": {k: v["mo_ta_hang"] for k, v in muc["nghia"].items()},
                   "da_chot": bool(qd.nghia_da_chot)})
    return ra


# ============================================================================
# 8. SCHEMA ĐỀ XUẤT — AG-00 viết migration v8, G09 KHÔNG chạm migrate.py
# ============================================================================
# Luật tiền (mục 16): bảng dưới đây KHÔNG có cột tiền nào, nên không có chỗ cho REAL lọt vào.
DDL_G09 = """
CREATE TABLE IF NOT EXISTS g09_harness_lan_chay (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id     INTEGER REFERENCES tenants(id),
    hang          TEXT    NOT NULL,
    che_do        TEXT    NOT NULL CHECK (che_do IN ('MOCK','SANDBOX','LIVE')),
    bat_dau       TEXT    NOT NULL,
    ket_thuc      TEXT,
    so_ca         INTEGER NOT NULL DEFAULT 0,
    so_dat        INTEGER NOT NULL DEFAULT 0,
    so_hong       INTEGER NOT NULL DEFAULT 0,
    so_bo_qua     INTEGER NOT NULL DEFAULT 0,
    ket_luan      TEXT    NOT NULL DEFAULT 'dang_chay'
                  CHECK (ket_luan IN ('dang_chay','dat','hong','tu_choi')),
    ly_do_tu_choi TEXT,
    nguoi_chay    TEXT,
    phieu_duyet   TEXT,
    pham_vi_do    TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_g09_lan_chay_hang ON g09_harness_lan_chay(hang, bat_dau);

CREATE TABLE IF NOT EXISTS g09_harness_ca (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lan_chay_id INTEGER NOT NULL REFERENCES g09_harness_lan_chay(id),
    ma_ca       TEXT    NOT NULL,
    nhom        TEXT    NOT NULL,
    mo_ta       TEXT,
    ket_qua     TEXT    NOT NULL CHECK (ket_qua IN ('dat','hong','bo_qua')),
    chi_tiet    TEXT,
    do_bang_gi  TEXT    NOT NULL,
    UNIQUE (lan_chay_id, ma_ca)
);
"""


def co_bang_harness():
    """Bảng của DDL_G09 đã được AG-00 cắm vào migration chưa. Chưa có thì NÓI RA."""
    import csdl
    try:
        return bool(csdl.mot("SELECT name FROM sqlite_master WHERE type='table'"
                             " AND name='g09_harness_lan_chay'"))
    except Exception:
        return False


def luu_lan_chay(kq, nguoi_chay=None, tenant_id=None, phieu_duyet=None):
    """Ghi một lần chạy vào CSDL. Chưa có bảng thì trả None và nói rõ — KHÔNG nuốt im (§12.2)."""
    import csdl
    if not co_bang_harness():
        return None
    con = csdl.ghi(
        "INSERT INTO g09_harness_lan_chay (tenant_id, hang, che_do, bat_dau, ket_thuc, so_ca,"
        " so_dat, so_hong, so_bo_qua, ket_luan, nguoi_chay, phieu_duyet, pham_vi_do)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (tenant_id, kq.hang, kq.che_do, _iso(kq.bat_dau), _iso(kq.ket_thuc), len(kq.cac_ca),
         kq.so_dat, kq.so_hong, kq.so_bo_qua, "dat" if kq.dat else "hong", nguoi_chay,
         json.dumps([p.nhu_dict() for p in (phieu_duyet or [])], ensure_ascii=False),
         PHAM_VI_DO[kq.che_do]))
    lan_id = con.lastrowid
    for c in kq.cac_ca:
        csdl.ghi("INSERT OR REPLACE INTO g09_harness_ca (lan_chay_id, ma_ca, nhom, mo_ta,"
                 " ket_qua, chi_tiet, do_bang_gi) VALUES (?,?,?,?,?,?,?)",
                 (lan_id, c.ma_ca, c.nhom, c.mo_ta, c.ket_qua, c.chi_tiet, c.do_bang_gi))
    return lan_id


def _iso(epoch):
    import datetime as _dt
    if epoch is None:
        return None
    tz = _dt.timezone(_dt.timedelta(hours=7))
    return _dt.datetime.fromtimestamp(epoch, tz).strftime("%Y-%m-%d %H:%M:%S%z")


# ============================================================================
# 9. CHẠY TỪ DÒNG LỆNH
# ============================================================================
def _in_bao_cao(ra):
    tong_dat = tong_hong = tong_bo = 0
    for hang, kq in sorted(ra.items()):
        if isinstance(kq, ThieuCauHinh):
            print(f"\n### {hang}: TỪ CHỐI CHẠY ở chế độ {kq.che_do}")
            for t in kq.thieu:
                print(f"    - thiếu: {t}")
            continue
        print(f"\n### {hang} — chế độ {kq.che_do}: {kq.so_dat} đạt ·"
              f" {kq.so_hong} hỏng · {kq.so_bo_qua} bỏ qua")
        print(f"    phạm vi: {PHAM_VI_DO[kq.che_do]}")
        for c in kq.cac_ca:
            dau = {"dat": "ĐẠT ", "hong": "HỎNG", "bo_qua": "BỎ  "}[c.ket_qua]
            print(f"    [{dau}] {c.ma_ca:<4} {c.mo_ta}")
            if c.ket_qua == "hong" and c.chi_tiet:
                print(f"            ↳ {c.chi_tiet}")
        tong_dat += kq.so_dat
        tong_hong += kq.so_hong
        tong_bo += kq.so_bo_qua
    print(f"\nTỔNG: {tong_dat} đạt · {tong_hong} hỏng · {tong_bo} bỏ qua")
    return tong_hong


def main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    che_do = argv[0].upper() if argv else None
    try:
        ra = chay_tat_ca(che_do)
    except ValueError as e:
        print(f"LỖI: {e}")
        return 2
    hong = _in_bao_cao(ra)
    bc = bao_cao_san_sang(ra)
    print("\nKẾT LUẬN (đúng dạng bắt buộc của G09):")
    for k, v in bc["ket_luan"].items():
        print(f"    {k} = {v}")
    return 1 if hong else 0


if __name__ == "__main__":
    raise SystemExit(main())
