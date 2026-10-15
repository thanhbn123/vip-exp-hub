# G04 — Adapter J&T Express Việt Nam.
# Dựng THEO TÀI LIỆU CÔNG KHAI đọc được ngày 14/10/2026 tại open.jtexpress.vn/apiDoc:
#   - Headers: apiAccount (số), digest (chuỗi ký), timestamp (ms, UTC+7)
#   - digest = base64( md5( bizContent-JSON + privateKey ) )  — md5 ra BYTES rồi base64
#   - Body: application/x-www-form-urlencoded, trường bizContent = chuỗi JSON nghiệp vụ
#   - Tạo đơn: POST .../webopenplatformapi/api/order/addOrder
#     (test: demoopenapi.jtexpress.vn, prod: ylopenapi.jtexpress.vn — chép nguyên văn từ docs)
#   - bizContent tối thiểu: customerCode, password, txlogisticId (mã đơn khách, KHÔNG trùng),
#     orderType, serviceType, payType, productType, goodsType, sender{...}, receiver{...}, packageInfo{weight}
# TRẠNG THÁI: DOCUMENTED — transport dưới đây là MOCK; đường LIVE bị khóa (CHO_PHEP_LIVE=False)
# cho tới khi Owner cấp customerCode/password thật và duyệt. KHÔNG tự suy đoán gì ngoài docs.
import base64
import hashlib
import json
import random

import loi_hang
from adapter import CarrierAdapter, KetQuaHang, dang_ky

URL_TAO_DON = {
    "sandbox": "https://demoopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder",
    "production": "https://ylopenapi.jtexpress.vn/webopenplatformapi/api/order/addOrder",
}
# Tra cứu hành trình (轨迹查询) — nguồn: open.jtexpress.vn/apiDoc/logistics/query, đọc 14/10/2026.
# Tài liệu nêu rõ: billcodes ngăn cách bằng dấu phẩy, MỘT LƯỢT tối đa 30 vận đơn.
SO_VAN_DON_MOI_LUOT = 30
DUONG_TRA_HANH_TRINH = "/webopenplatformapi/api/logistics/trace"
# SỬA 14/10/2026 (đọc lại trang /apiDoc/logistics/query bằng trình duyệt): tài liệu CÓ cho URL đầy
# đủ của mục tra hành trình, ghi chú cũ "chỉ cho đường dẫn tương đối" là sai.
URL_TRA_HANH_TRINH = {
    "sandbox": "https://demoopenapi.jtexpress.vn" + DUONG_TRA_HANH_TRINH,
    "production": "https://ylopenapi.jtexpress.vn" + DUONG_TRA_HANH_TRINH,
}

CONTENT_TYPE = "application/x-www-form-urlencoded"
BANG_MA = "utf-8"
# Nguồn (trang "极兔API简介", đọc lại bằng trình duyệt 14/10/2026), nguyên văn:
#   "使用http协议表单提交的方式进行信息交互，字符编码默认统一采用UTF-8，
#    数据格式：application/x-www-form-urlencoded"
#   "digest=base64(md5(业务参数的Json+privateKey))，注：先md5得到字节数组，再base64加密"
# → md5 phải ra MẢNG BYTE trước rồi mới base64. Lấy md5 hexdigest rồi base64 là SAI chữ ký.
# Header timestamp: "时间戳，毫秒 / 时区：UTC+7" → mili giây, múi giờ UTC+7.
MUI_GIO_GIO = 7


def ky_digest(biz_content_json: str, private_key: str) -> str:
    """Đúng công thức docs: base64(md5-bytes(bizContent + privateKey))."""
    return base64.b64encode(
        hashlib.md5((biz_content_json + private_key).encode(BANG_MA)).digest()).decode()


def dau_thoi_gian_ms(bay_gio=None) -> int:
    """Mốc thời gian MILI GIÂY theo múi giờ UTC+7 như tài liệu yêu cầu.

    §12.2 ("mọi mốc thời gian phải mang múi giờ"): tính tường minh bằng UTC+7, không mượn múi
    giờ của máy đang chạy — máy chủ đặt UTC thì lệch 7 tiếng mà không báo lỗi gì.
    """
    import datetime as _dt
    tz = _dt.timezone(_dt.timedelta(hours=MUI_GIO_GIO))
    t = bay_gio or _dt.datetime.now(tz)
    return int(t.timestamp() * 1000)


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


# ── CHỐT CHẶN D-9: ánh xạ `area` CHƯA ĐƯỢC HÃNG XÁC NHẬN ──────────────────────
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

    # Trường hành chính BẮT BUỘC theo bảng tham số J&T. Thiếu là hãng trả `1450033315`.
    TRUONG_HANH_CHINH = (("sender", "prov", "nguoi_gui_tinh"),
                         ("sender", "area", "nguoi_gui_quan"),
                         ("receiver", "prov", "nguoi_nhan_tinh"),
                         ("receiver", "area", "nguoi_nhan_quan"))

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
        — hãng xác nhận khác thì đổi đúng một dòng ở `TRUONG_HANH_CHINH`.
        """
        # Chốt D-9 đặt Ở ĐÂY chứ không ở `__init__`: `__init__` chỉ chặn lúc dựng
        # adapter, còn chốt ở chỗ DÙNG thì mọi đường mới dẫn tới `bizContent` sau này
        # đều tự bị canh — kể cả khi ai đó mở LIVE cho riêng thao tác chỉ-đọc.
        chot_chan_anh_xa_area(self.moi_truong)
        g = lambda k: str(don.get(k) or "").strip()      # noqa: E731
        biz = {
            "customerCode": self.credentials.get("customerCode", ""),
            "password": self.credentials.get("password", ""),
            "txlogisticId": don["ma_don"],          # mã đơn nội bộ = chống trùng phía hãng
            "orderType": 1, "serviceType": 1, "payType": "PP_CASH",
            "productType": "EXPRESS", "goodsType": "bm000010", "deliveryType": 1,
            "sender": {"name": don["nguoi_gui_ten"], "mobile": don["nguoi_gui_sdt"],
                       "prov": g("nguoi_gui_tinh"), "area": g("nguoi_gui_quan"),
                       "address": don["nguoi_gui_dia_chi"]},
            "receiver": {"name": don["nguoi_nhan_ten"], "mobile": don["nguoi_nhan_sdt"],
                         "prov": g("nguoi_nhan_tinh"), "area": g("nguoi_nhan_quan"),
                         "address": don["nguoi_nhan_dia_chi"]},
            "packageInfo": {"weight": f"{don['khoi_luong_gram'] / 1000:.2f}"},
            # COD vào ĐÚNG cột `codMoney`. Số nguyên đồng (§16) — J&T nhận chuỗi số.
            "codMoney": str(int(don.get("cod") or 0)),
            # `isInsured` 0/1 và `goodsValue` bắt buộc. Chưa bán bảo hiểm nên 0, và giá trị
            # khai lấy từ `gia_tri_khai`; không có thì dùng COD (giá trị người nhận trả).
            "isInsured": 0,
            "goodsValue": str(int(don.get("gia_tri_khai") or don.get("cod") or 0)),
        }
        return biz

    def yeu_cau_tao_don(self, don, bay_gio=None):
        # Thiếu trường hành chính bắt buộc thì DỪNG Ở ĐÂY, đừng để hãng từ chối rồi mới biết:
        # lỗi của hãng là một mã số khó tra, còn lỗi ở đây nói rõ thiếu cột nào của hệ.
        # Ở MOCK vẫn cho đi (bộ thử và dữ liệu demo chưa có địa chỉ hành chính), nhưng gắn
        # danh sách thiếu vào payload để nó không biến mất im lặng.
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
        return {
            "url": URL_TAO_DON.get(self.moi_truong),   # None ở môi trường mock — cố ý
            "headers": dung_headers(self.credentials.get("apiAccount", ""), biz,
                                    self.credentials.get("privateKey", ""), bay_gio),
            "body": dung_body(biz),
            "bizContent": biz,
        }

    def createOrder(self, don) -> KetQuaHang:
        yc = self.yeu_cau_tao_don(don)
        digest = yc["headers"]["digest"]
        if self.moi_truong == "mock":
            # MOCK: không gửi gì ra ngoài. Hỗ trợ ép ca lỗi/timeout để kiểm thử.
            if don.get("ghi_chu") == "demo_force_fail":
                # Lỗi của hãng đi qua bảng mã lỗi THẬT (loi_hang.JT_MA_LOI), không bịa chuỗi lỗi.
                loi = loi_hang.doc_tra_loi_jt({"code": "145003050", "msg": "参数非法"},
                                              thao_tac="createOrder")
                return KetQuaHang(False, loi=f"MOCK J&T: {loi}", tho={"mock": True,
                                                                      "loi_chuan": loi.nhu_dict()})
            if don.get("ghi_chu") == "demo_force_timeout":
                loi = loi_hang.NormalizedCarrierError(
                    loi_hang.HET_GIO, thong_diep="MOCK J&T: hết giờ — không biết kết quả",
                    hang="jt", thao_tac="createOrder")
                return KetQuaHang(False, timeout=True, loi=str(loi),
                                  tho={"mock": True, "loi_chuan": loi.nhu_dict()})
            return KetQuaHang(True, ma_van_don="JTVN%010d" % random.randint(0, 10**10 - 1),
                              tho={"mock": True, "digest_da_ky": digest[:8] + "…"})
        raise PermissionError("Đường LIVE J&T đang khóa (BLOCKED — chờ Owner)")  # không bao giờ tới vì __init__ chặn

    def cancelOrder(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True})
        raise PermissionError("Đường LIVE J&T đang khóa")

    def trackOrder(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don,
                              tho={"mock": True, "trang_thai": "dang_giao"})
        raise PermissionError("Đường LIVE J&T đang khóa")

    def getShippingFee(self, don) -> KetQuaHang:
        if self.moi_truong == "mock":
            kl = max(1, don["khoi_luong_gram"])
            return KetQuaHang(True, phi=15000 + (kl // 500) * 5200, tho={"mock": True})
        raise PermissionError("Đường LIVE J&T đang khóa")

    def getShippingLabel(self, ma_van_don) -> KetQuaHang:
        if self.moi_truong == "mock":
            return KetQuaHang(True, ma_van_don=ma_van_don, tho={"mock": True, "label": "MOCK-PDF"})
        raise PermissionError("Đường LIVE J&T đang khóa")

    # Bảng mã scanTypeCode thật đã đọc từ tài liệu → xem app/trang_thai_hang.py (JT_MA).
    # Lớp nền CarrierAdapter.normalizeTrackingStatus đã dùng bảng đó, không cần ghi đè.
