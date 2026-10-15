# -*- coding: utf-8 -*-
"""G12 — LỚP TRUY VẤN DÙNG CHUNG: lọc, sắp xếp, phân trang Ở MÁY CHỦ.

Vì sao có file này
==================
`GET /api/v2/don` chỉ nhận `q` · `trang_thai` · `gioi_han`. Mọi điều kiện lọc nâng cao
(khoảng ngày, trạng thái giao, hãng, khoảng COD, cần đối soát) đang chạy **TẠI GIAO DIỆN,
trên tập đã tải về**. Với CSDL lớn thì người dùng tải 100 dòng đầu rồi lọc trong 100 dòng đó
và **tưởng là đã lọc cả kho** — lọc thiếu mà không có gì báo. Giao diện có ghi cảnh báo, nhưng
đó là vá bằng LỜI; §12.2 nói vá bằng lời không chặn được máy. File này là bản vá bằng CẤU TRÚC:
đưa phép lọc về đúng chỗ nó có đủ dữ liệu để đúng — máy chủ.

Thiết kế để DÙNG LẠI, không riêng đơn hàng
==========================================
Mỗi bảng khai một `BangTruyVan` (bộ quy chuẩn truy vấn của bảng đó): tên bảng, cột tenant,
bảng trường lọc, danh sách trắng sắp xếp, cột tìm chữ. Hàm `chay()` nhận bộ quy chuẩn đó và
dựng SQL. Đơn hàng đi trước (`BANG_DON`), COD / đối soát / công việc AI khai thêm bộ quy chuẩn
của mình mà không phải viết lại một dòng SQL nào.

Bốn luật cứng của file này
==========================
1. **Tham số hoá hoàn toàn.** Không có giá trị nào bị ghép thành chuỗi vào SQL. Thứ duy nhất
   ghép vào câu là TÊN CỘT và CHIỀU SẮP XẾP, và cả hai chỉ đến từ **danh sách trắng khai sẵn
   trong mã nguồn** — không bao giờ từ dữ liệu người gửi lên.

   Đây là **ngoại lệ chính đáng** của luật "dùng danh sách đen" (§12.2). Câu hỏi phân biệt của
   chính luật đó là: *quên một dòng thì kết quả an toàn hay hỏng?* Quên một cột trong danh
   sách trắng = một kiểu sắp xếp bị chặn, người dùng thấy ngay, sửa trong một phút. Quên một
   tên trong danh sách đen = một chuỗi do người ngoài viết đi thẳng vào `ORDER BY`, tức là
   SQL injection, và nó **không báo gì cả**.

2. **`tenant_id` LUÔN có trong `WHERE`.** Không có đường nào bỏ qua: hàm dựng điều kiện khởi
   tạo danh sách điều kiện bằng đúng mệnh đề tenant, và bảng nào không khai `cot_tenant` thì
   `BangTruyVan` **từ chối ngay lúc khai**, không đợi tới lúc chạy.

3. **Điều kiện lạ thì BÁO LỖI 400, không bỏ qua im lặng.** Xem `_kiem_ten_la()` để biết lý do.

4. **Đếm `tong` có TRẦN.** Xem `TRAN_DEM` để biết lý do và cách đọc kết quả.

Phạm vi KHÔNG phủ (nói trước để không ai tưởng đã xong)
=======================================================
- Chỉ `SELECT`. Không ghi, không xoá, không `JOIN` nhiều bảng tuỳ ý (chỉ có kiểu điều kiện
  `trong_bang_khac` dựng `IN (SELECT …)` theo khai báo sẵn).
- Không nhóm (`GROUP BY`), không tổng hợp (`SUM`/`AVG`). Việc thống kê là việc khác.
- Lọc trạng thái mở rộng (`trang_thai_mo_rong` của `don_hang`) **không thuộc lớp này** — nó là
  giá trị SUY RA ở tầng Python, không phải cột. `don_hang.tim_don` vẫn giữ phần đó.
"""
import datetime
import re

import csdl


class LoiTruyVan(Exception):
    """Lỗi do điều kiện truy vấn sai — luôn là lỗi của bên gọi, nên mặc định 400."""

    def __init__(self, msg, ma=400):
        super().__init__(msg)
        self.ma = ma


# ============================================================================
# 1. TRẦN VÀ MẶC ĐỊNH
# ============================================================================

GIOI_HAN_MAC_DINH = 50
GIOI_HAN_TOI_DA = 500          # khớp `don_hang.GIOI_HAN_TOI_DA` — hai trần lệch nhau là hai
                               # màn cùng một dữ liệu hiển thị khác nhau.
LECH_TOI_DA = 200_000          # trần OFFSET: xem `_kep_phan_trang`.

# Trần đếm. `COUNT(*)` không có trần là một lượt QUÉT TOÀN BẢNG cho mỗi lần bấm lọc; với bảng
# triệu dòng thì mỗi lượt gõ vào ô tìm kiếm là một lượt quét triệu dòng, và nó không báo chậm,
# chỉ chậm. Nên đếm trong một câu con có `LIMIT TRAN+1`: SQLite dừng đọc ngay khi đủ TRAN+1
# dòng khớp.
#
# Cách đọc kết quả — ba trường, KHÔNG được đọc nhầm:
#   tong              số dòng khớp, ĐÚNG khi `tong_chinh_xac` là True
#   tong_chinh_xac    False nghĩa là đã chạm trần, `tong` lúc đó bằng đúng TRAN_DEM
#   tong_it_nhat      khi chạm trần: "ít nhất ngần này", dùng để giao diện ghi "500+"
#
# Vì sao chọn trần thay vì đếm xấp xỉ bằng thống kê bảng: xấp xỉ sai một cách IM LẶNG, còn
# trần nói thẳng ra là nó không biết (§12.1 luật 3 — chỉ nói trong phạm vi đã đo).
TRAN_DEM = 10_000

NGAY_HOP_LE = re.compile(r"\d{4}-\d{2}-\d{2}")
TEN_COT_HOP_LE = re.compile(r"[a-z_][a-z0-9_]*")   # canh chính mã nguồn, không canh dữ liệu vào


# ============================================================================
# 2. BỘ QUY CHUẨN TRUY VẤN CỦA MỘT BẢNG
# ============================================================================

# Các kiểu điều kiện lọc. Mỗi kiểu là một cách dựng MỘT mệnh đề WHERE.
#   "bang"            : cột = giá trị (một giá trị, hoặc danh sách → IN)
#   "co_khong"        : cột = 0/1
#   "tu" / "den"      : cột >= / <= giá trị (tiền: số nguyên bắt buộc)
#   "ngay_tu"/"ngay_den": so 10 ký tự đầu của cột thời gian với YYYY-MM-DD
#   "tim_chu"         : LIKE %…% trên nhiều cột cùng lúc
#   "trong_bang_khac" : cột IN (SELECT khoá FROM bảng_khác WHERE tenant_id=? AND cột_lọc=?)
KIEU_LOC = ("bang", "co_khong", "tu", "den", "ngay_tu", "ngay_den", "tim_chu",
            "trong_bang_khac")


class TruongLoc:
    """Khai báo MỘT điều kiện lọc: tên người dùng gửi lên ↔ cột thật + cách so sánh.

    Tách tên ngoài (`can_doi_soat`) khỏi tên cột (`can_doi_soat_ket_qua`) là cố ý: giao diện
    đã khai tên nào thì giữ đúng tên đó, đổi tên cột trong CSDL không phá hợp đồng API.
    """

    def __init__(self, ten, kieu, cot=None, cac_cot=None, bang_khac=None,
                 khoa_bang_khac="id", cot_loc_bang_khac=None, la_tien=False, mo_ta=""):
        if kieu not in KIEU_LOC:
            raise ValueError(f"kiểu lọc lạ: {kieu}")
        self.ten = ten
        self.kieu = kieu
        self.cot = cot or ten
        self.cac_cot = tuple(cac_cot or ())
        self.bang_khac = bang_khac
        self.khoa_bang_khac = khoa_bang_khac
        self.cot_loc_bang_khac = cot_loc_bang_khac
        self.la_tien = la_tien
        self.mo_ta = mo_ta
        # Mọi tên cột phải qua phép kiểm hình dạng NGAY LÚC KHAI, không đợi lúc chạy. Tên cột
        # ghép thẳng vào SQL, nên một ký tự lạ lọt vào đây là một lỗ; bắt sớm thì nó hỏng ở
        # lượt nạp module, tức là hỏng ở bộ thử, không hỏng ở máy khách hàng.
        for t in filter(None, (self.cot, self.bang_khac, self.khoa_bang_khac,
                               self.cot_loc_bang_khac, *self.cac_cot)):
            if not TEN_COT_HOP_LE.fullmatch(t):
                raise ValueError(f"tên cột/bảng không hợp lệ trong khai báo: {t!r}")


class BangTruyVan:
    """Bộ quy chuẩn truy vấn của một bảng.

    `cot_tenant` là BẮT BUỘC. Bảng nào thật sự không có tenant thì **không dùng lớp này** —
    cố ý không mở cửa cho trường hợp đó, vì một cửa "bỏ qua tenant" mở ra là một cửa sẽ có
    người đi qua.
    """

    def __init__(self, bang, cot_tenant, truong_loc, sap_xep_duoc, sap_xep_mac_dinh,
                 cot_tra="*"):
        if not cot_tenant:
            raise ValueError(f"bảng {bang}: THIẾU cot_tenant — lớp truy vấn từ chối khai báo này")
        if not TEN_COT_HOP_LE.fullmatch(bang) or not TEN_COT_HOP_LE.fullmatch(cot_tenant):
            raise ValueError(f"tên bảng/cột tenant không hợp lệ: {bang}.{cot_tenant}")
        if sap_xep_mac_dinh not in sap_xep_duoc:
            raise ValueError(f"sắp xếp mặc định {sap_xep_mac_dinh!r} không có trong danh sách trắng")
        for khoa, bieu_thuc in sap_xep_duoc.items():
            # Danh sách trắng cũng phải tự nó đúng hình dạng (§12.1: thứ dùng để kiểm chứng
            # phải được kiểm trước khi tin). Một dòng gõ nhầm trong chính danh sách trắng là
            # một lỗ y hệt như không có danh sách trắng.
            if not re.fullmatch(r"[a-z_][a-z0-9_]*( (?:ASC|DESC))?"
                                r"(, ?[a-z_][a-z0-9_]*( (?:ASC|DESC))?)*", bieu_thuc):
                raise ValueError(f"biểu thức sắp xếp {khoa!r} = {bieu_thuc!r} sai hình dạng")
        self.bang = bang
        self.cot_tenant = cot_tenant
        self.truong_loc = {t.ten: t for t in truong_loc}
        self.sap_xep_duoc = dict(sap_xep_duoc)
        self.sap_xep_mac_dinh = sap_xep_mac_dinh
        self.cot_tra = cot_tra

    def ten_loc_hop_le(self):
        """Mọi tên được nhận: trường lọc + tham số phân trang/sắp xếp."""
        return sorted(set(self.truong_loc) | set(TEN_DIEU_KHIEN))


# Tham số không phải điều kiện lọc mà là điều khiển kết quả.
TEN_DIEU_KHIEN = ("sap_xep", "gioi_han", "lech", "trang", "dem_chinh_xac")


# ============================================================================
# 3. CHUYỂN ĐỔI VÀ KIỂM GIÁ TRỊ
# ============================================================================

def _so_nguyen_tien(gt, ten):
    """Tiền là `INTEGER` đồng (SHARED_CONTRACTS §16). CHẶN số thập phân, không cắt cụt.

    `int(float("150000.7"))` ra 150000 — mất 7 hào mà không báo gì. Mất tiền im lặng là dạng
    hỏng xấu nhất (§12.2), nên thà báo lỗi để người gọi sửa. Cùng luật với
    `don_hang._so_nguyen_tien`; viết lại ở đây để lớp truy vấn không phụ thuộc module nghiệp vụ.
    """
    if isinstance(gt, bool):
        raise LoiTruyVan(f"{ten} phải là số nguyên đồng, nhận bool")
    if isinstance(gt, float):
        raise LoiTruyVan(f"{ten} phải là số nguyên đồng (VND không có phần thập phân),"
                         f" nhận {gt!r}")
    if isinstance(gt, int):
        return gt
    s = str(gt).strip()
    if not re.fullmatch(r"-?\d+", s):
        raise LoiTruyVan(f"{ten} phải là số nguyên đồng (VND không có phần thập phân),"
                         f" nhận {gt!r}")
    return int(s)


def _so_nguyen(gt, ten):
    if isinstance(gt, bool) or isinstance(gt, float):
        raise LoiTruyVan(f"{ten} phải là số nguyên, nhận {gt!r}")
    if isinstance(gt, int):
        return gt
    s = str(gt).strip()
    if not re.fullmatch(r"-?\d+", s):
        raise LoiTruyVan(f"{ten} phải là số nguyên, nhận {gt!r}")
    return int(s)


def _rong(gt):
    return gt is None or gt == "" or gt == []


def _danh_sach(gt):
    ds = gt if isinstance(gt, (list, tuple)) else [gt]
    return [str(x) for x in ds if str(x).strip() != ""]


def _kiem_ten_la(spec, loc):
    """Tên tham số lạ → **400**, không bỏ qua im lặng. Đây là một quyết định, nên nói rõ lý do.

    Bỏ qua im lặng nghĩa là: người gõ `trang_thai_gia0` thay vì `trang_thai_giao` sẽ nhận về
    danh sách **KHÔNG LỌC** và tin rằng đó là kết quả đã lọc. Không có gì báo, không có gì
    khác thường trên màn hình — chỉ là nhiều dòng hơn mong đợi, và người ta sẽ cho rằng dữ
    liệu đúng là như thế. Đó đúng là cái hỏng mà cả nhiệm vụ G12 này sinh ra để diệt, nên
    không được tái tạo nó ở chính tầng đi vá nó.

    Hậu quả hai bên đều cân được: trả 400 làm hỏng NGAY một lượt gọi sai và người gọi sửa
    trong một phút; bỏ qua im lặng làm sai LÂU DÀI mọi lượt gọi sau đó mà không ai biết.

    Khác với `loc_bo_qua`: ở đó tên tham số ĐÚNG nhưng CSDL chưa có cột (chưa migrate). Lúc ấy
    bên gọi không sai, nên không phạt bên gọi — nhưng vẫn phải **nói ra** trong `loc_bo_qua`
    để giao diện nói lại được với người dùng, không im.
    """
    la = sorted(set(loc) - set(spec.truong_loc) - set(TEN_DIEU_KHIEN))
    if la:
        raise LoiTruyVan(
            f"điều kiện lọc không nhận ra: {', '.join(la)}."
            f" Nhận được: {', '.join(spec.ten_loc_hop_le())}")


def _kep_phan_trang(loc):
    """Kẹp `gioi_han` và `lech` ở CẢ HAI ĐẦU, rồi trả về cặp đã kẹp.

    Kẹp đầu trên của `gioi_han` là để một lượt gọi không kéo cả bảng về. Kẹp đầu trên của
    `lech` thì ít người nghĩ tới nhưng cùng lý do: `OFFSET 50000000` buộc SQLite **đọc và bỏ**
    đúng ngần ấy dòng trước khi trả dòng đầu tiên — một lượt gọi duy nhất làm kiệt máy, và
    nó không trông như một lượt tấn công. Trần `LECH_TOI_DA` chặn đúng chỗ đó.

    Kẹp, không báo lỗi: giao diện bấm "trang sau" quá đà là chuyện thường, phạt 400 ở đó là
    phiền vô ích. Nhưng giá trị thật dùng để chạy LUÔN được trả ra trong kết quả, nên bên gọi
    đối chiếu được và biết mình đã bị kẹp (không im lặng).
    """
    gioi_han = GIOI_HAN_MAC_DINH if _rong(loc.get("gioi_han")) \
        else _so_nguyen(loc["gioi_han"], "gioi_han")
    gioi_han = max(1, min(gioi_han, GIOI_HAN_TOI_DA))

    if not _rong(loc.get("trang")):
        if not _rong(loc.get("lech")):
            raise LoiTruyVan("gửi `trang` HOẶC `lech`, không gửi cả hai"
                             " — hai cách đánh số cùng lúc là hai kết quả khác nhau")
        trang = max(1, _so_nguyen(loc["trang"], "trang"))   # `trang` đếm từ 1
        lech = (trang - 1) * gioi_han
    else:
        lech = 0 if _rong(loc.get("lech")) else _so_nguyen(loc["lech"], "lech")
    lech = max(0, min(lech, LECH_TOI_DA))
    return gioi_han, lech


# ============================================================================
# 4. DỰNG CÂU VÀ CHẠY
# ============================================================================

def dung_dieu_kien(spec, tenant_id, loc, co_cot=None):
    """Dựng `(mệnh_đề_WHERE, tham_số, loc_bo_qua)`. Không chạy gì — để bộ thử soi được câu.

    `co_cot(bang, cot) -> bool` dùng để chịu được CSDL chưa migrate: cột chưa có thì BỎ điều
    kiện đó và **ghi vào `loc_bo_qua`**. Không truyền thì coi như mọi cột đều có.
    """
    if tenant_id is None:
        raise LoiTruyVan("thiếu tenant_id — lớp truy vấn không chạy câu nào không có tenant", 500)
    _kiem_ten_la(spec, loc)
    # Mệnh đề đầu tiên LUÔN là tenant. Viết thẳng ở dòng khởi tạo chứ không thêm trong vòng
    # lặp: không có nhánh nào trong hàm này chạy mà bỏ qua được dòng này.
    dk = [f"{spec.cot_tenant}=?"]
    tsq = [tenant_id]
    bo_qua = []

    for ten, truong in spec.truong_loc.items():
        gt = loc.get(ten)
        if _rong(gt):
            continue
        # Cột chưa migrate → bỏ điều kiện NHƯNG NÓI RA.
        can_cot = truong.cac_cot if truong.kieu == "tim_chu" else (truong.cot,)
        if co_cot and truong.kieu != "trong_bang_khac":
            thieu = [c for c in can_cot if not co_cot(spec.bang, c)]
            if thieu:
                bo_qua.append(f"{ten} (CSDL chưa có cột {', '.join(thieu)})")
                continue

        if truong.kieu == "bang":
            ds = _danh_sach(gt)
            if not ds:
                continue
            if len(ds) == 1:
                dk.append(f"{truong.cot}=?")
                tsq.append(ds[0])
            else:
                dk.append(f"{truong.cot} IN (" + ",".join("?" * len(ds)) + ")")
                tsq.extend(ds)
        elif truong.kieu == "co_khong":
            dk.append(f"{truong.cot}=?")
            tsq.append(1 if gt in (1, "1", True, "true", "True") else 0)
        elif truong.kieu in ("tu", "den"):
            dau = ">=" if truong.kieu == "tu" else "<="
            so = _so_nguyen_tien(gt, ten) if truong.la_tien else _so_nguyen(gt, ten)
            dk.append(f"{truong.cot} {dau} ?")
            tsq.append(so)
        elif truong.kieu in ("ngay_tu", "ngay_den"):
            v = str(gt).strip()
            if not NGAY_HOP_LE.fullmatch(v):
                raise LoiTruyVan(f"{ten} phải dạng YYYY-MM-DD, nhận {gt!r}")
            try:
                ngay = datetime.date.fromisoformat(v)
            except ValueError:
                raise LoiTruyVan(f"{ten} không phải ngày có thật: {v}") from None
            # `{cot}` lưu dạng "YYYY-MM-DD HH:MM:SS+0700" (giờ VN). So sánh CHUỖI trực tiếp
            # trên cột — KHÔNG bọc `substr()` — vì khuôn ISO so chuỗi cũng ra đúng thứ tự thời
            # gian, mà cột trần thì chỉ mục dùng được.
            #
            # Đây là một thay đổi ĐO ĐƯỢC, không phải sở thích: bản đầu viết
            # `substr(tao_luc,1,10) >= ?` và SQLite **không dùng được chỉ mục nào** cho nó
            # (hàm bọc quanh cột thì mất tính tra được), đo ra `USE TEMP B-TREE FOR ORDER BY`
            # và 2,9 ms/lượt trên 20 000 đơn. Bản này dùng `ix_g12q_don_tenant_tao`.
            #
            # CẢ HAI ĐẦU ĐỀU BAO GỒM:
            #   tu_ngay=2026-10-15  → tao_luc >= "2026-10-15"        (nhỏ hơn mọi giờ ngày 15)
            #   den_ngay=2026-10-15 → tao_luc <  "2026-10-16"        (hết 23:59:59 ngày 15)
            # Đầu cuối dùng `<` ngày-kế-tiếp chứ không `<=` cùng ngày: `<= "2026-10-15"` sẽ
            # loại SẠCH mọi đơn trong ngày 15 (vì "2026-10-15 08:00" > "2026-10-15") — lọc ra
            # rỗng mà không báo gì. tu_ngay == den_ngay = đúng một ngày.
            if truong.kieu == "ngay_tu":
                dk.append(f"{truong.cot} >= ?")
                tsq.append(v)
            else:
                dk.append(f"{truong.cot} < ?")
                tsq.append((ngay + datetime.timedelta(days=1)).isoformat())
        elif truong.kieu == "tim_chu":
            q = f"%{str(gt).strip()}%"
            dk.append("(" + " OR ".join(f"{c} LIKE ?" for c in truong.cac_cot) + ")")
            tsq.extend([q] * len(truong.cac_cot))
        elif truong.kieu == "trong_bang_khac":
            # Câu con MANG THEO tenant của chính nó. Thiếu dòng này thì lọc theo `hang` sẽ
            # khớp tài khoản hãng của tenant KHÁC — rò rỉ qua đường vòng, và vì nó chỉ ảnh
            # hưởng tập id đem đi lọc nên nhìn kết quả không thấy gì bất thường.
            ds = _danh_sach(gt)
            dk.append(
                f"{truong.cot} IN (SELECT {truong.khoa_bang_khac} FROM {truong.bang_khac}"
                f" WHERE tenant_id=? AND {truong.cot_loc_bang_khac} IN ("
                + ",".join("?" * len(ds)) + "))")
            tsq.append(tenant_id)
            tsq.extend(ds)
    return " AND ".join(dk), tsq, bo_qua


def _dem_co_tran(bang, dieu_kien, tsq, tran=None):
    """Đếm nhưng DỪNG ở `tran`. Trả `(tong, chinh_xac)`.

    `tran=None` đọc `TRAN_DEM` lúc GỌI, không lúc định nghĩa hàm: giá trị mặc định của tham
    số Python được chốt một lần lúc nạp module, nên viết `tran=TRAN_DEM` thì bộ thử đổi trần
    sẽ KHÔNG có tác dụng mà ca vẫn báo đạt — ca thử vô dụng (§12.1).

    Câu con có `LIMIT tran+1` để phân biệt "đúng bằng trần" với "nhiều hơn trần" — thiếu dấu
    `+1` thì một tập đúng 10 000 dòng sẽ bị báo nhầm là "10 000+".
    """
    tran = TRAN_DEM if tran is None else tran
    r = csdl.mot(f"SELECT COUNT(*) c FROM (SELECT 1 FROM {bang} WHERE {dieu_kien} LIMIT ?)",
                 list(tsq) + [tran + 1])
    n = r["c"]
    return (tran, False) if n > tran else (n, True)


def chay(spec, tenant_id, loc=None, co_cot=None):
    """Chạy một truy vấn theo bộ quy chuẩn `spec`.

    Trả về:
        dong             danh sách bản ghi (dict) của TRANG hiện tại
        tong             tổng số dòng KHỚP ĐIỀU KIỆN (không phải số dòng trang này)
        tong_chinh_xac   False nghĩa là đã chạm `TRAN_DEM`, `tong` khi đó = TRAN_DEM
        tong_it_nhat     khi chạm trần: số tối thiểu đã biết chắc (để hiện "10 000+")
        gioi_han/lech/trang   giá trị THẬT đã dùng sau khi kẹp — đối chiếu được
        con_nua          còn trang sau hay không
        sap_xep          khoá sắp xếp đã dùng
        loc_bo_qua       điều kiện đã BỎ vì CSDL chưa có cột (tên đúng nhưng cột chưa có)
    """
    loc = dict(loc or {})
    dieu_kien, tsq, bo_qua = dung_dieu_kien(spec, tenant_id, loc, co_cot=co_cot)

    khoa_sx = str(loc.get("sap_xep") or spec.sap_xep_mac_dinh)
    thu_tu = spec.sap_xep_duoc.get(khoa_sx)
    if thu_tu is None:
        # Tên cột KHÔNG tham số hoá được bằng `?`, nên nhận tên tự do = mở cửa SQL injection.
        # Danh sách trắng + báo lỗi, không "tìm cái gần giống".
        raise LoiTruyVan(f"sap_xep phải là một trong: {', '.join(sorted(spec.sap_xep_duoc))}")

    gioi_han, lech = _kep_phan_trang(loc)

    if loc.get("dem_chinh_xac") in (1, "1", True, "true"):
        tong = csdl.mot(f"SELECT COUNT(*) c FROM {spec.bang} WHERE {dieu_kien}", tsq)["c"]
        chinh_xac = True
    else:
        tong, chinh_xac = _dem_co_tran(spec.bang, dieu_kien, tsq)

    ds = csdl.nhieu(
        f"SELECT {spec.cot_tra} FROM {spec.bang} WHERE {dieu_kien}"
        f" ORDER BY {thu_tu} LIMIT ? OFFSET ?", list(tsq) + [gioi_han, lech])
    dong = [dict(x) for x in ds]
    return {
        "dong": dong,
        "tong": tong,
        "tong_chinh_xac": chinh_xac,
        "tong_it_nhat": None if chinh_xac else tong,
        "gioi_han": gioi_han,
        "lech": lech,
        "trang": lech // gioi_han + 1,
        "con_nua": (lech + len(dong)) < tong or not chinh_xac,
        "sap_xep": khoa_sx,
        "loc_bo_qua": bo_qua,
    }


# ============================================================================
# 5. BỘ QUY CHUẨN: ĐƠN HÀNG
# ============================================================================

# Tên trường lấy TỪ `admin/logic.js` mục `API_CHO_BACKEND` (mục "Tìm đơn nâng cao ở máy chủ"),
# không tự nghĩ ra. Giao diện đã khai tên nào thì máy chủ nhận đúng tên đó; đặt tên khác là
# bắt giao diện dịch, và một bảng dịch là một chỗ nữa để lệch.
#
# `hang` KHÔNG phải cột của `don_hang` (đo bằng `PRAGMA table_info(don_hang)`, 40 cột, không có
# `hang`) — mã hãng nằm ở `carrier_accounts.hang`. Nên nó đi đường `trong_bang_khac`.
BANG_DON = BangTruyVan(
    bang="don_hang",
    cot_tenant="tenant_id",
    truong_loc=[
        TruongLoc("tu_ngay", "ngay_tu", cot="tao_luc",
                  mo_ta="từ ngày (theo tao_luc, giờ VN, BAO GỒM cả ngày này)"),
        TruongLoc("den_ngay", "ngay_den", cot="tao_luc",
                  mo_ta="đến ngày (theo tao_luc, giờ VN, BAO GỒM cả ngày này)"),
        TruongLoc("trang_thai", "bang", mo_ta="trạng thái nghiệp vụ; nhận danh sách"),
        TruongLoc("trang_thai_giao", "bang", mo_ta="trạng thái giao vận; nhận danh sách"),
        TruongLoc("carrier_account_id", "bang", mo_ta="id tài khoản hãng"),
        TruongLoc("khach_hang_id", "bang", mo_ta="id khách hàng"),
        TruongLoc("hang", "trong_bang_khac", cot="carrier_account_id",
                  bang_khac="carrier_accounts", khoa_bang_khac="id", cot_loc_bang_khac="hang",
                  mo_ta="mã hãng (vtp/jt…) — qua carrier_accounts CỦA CHÍNH TENANT"),
        TruongLoc("ma_don", "bang"),
        TruongLoc("ma_van_don", "bang"),
        TruongLoc("external_reference", "bang", mo_ta="mã đối chiếu bên ngoài (cột v7+)"),
        TruongLoc("cod_tu", "tu", cot="cod", la_tien=True, mo_ta="COD từ (đồng, số nguyên)"),
        TruongLoc("cod_den", "den", cot="cod", la_tien=True, mo_ta="COD đến (đồng, số nguyên)"),
        TruongLoc("can_doi_soat", "co_khong", cot="can_doi_soat_ket_qua",
                  mo_ta="1 = chỉ đơn cần đối soát; 0 = chỉ đơn KHÔNG cần;"
                        " bỏ trống/chuỗi rỗng = không lọc"),
        TruongLoc("q", "tim_chu",
                  cac_cot=("ma_don", "ma_van_don", "nguoi_nhan_ten", "nguoi_nhan_sdt",
                           "hang_hoa")),
    ],
    sap_xep_duoc={
        "moi_nhat": "id DESC", "cu_nhat": "id ASC",
        "cap_nhat_moi": "cap_nhat_luc DESC, id DESC",
        "cap_nhat_cu": "cap_nhat_luc ASC, id DESC",
        "cod_cao": "cod DESC, id DESC", "cod_thap": "cod ASC, id DESC",
        "nang_nhat": "khoi_luong_gram DESC, id DESC",
        "ma_don": "ma_don ASC",
    },
    sap_xep_mac_dinh="moi_nhat",
)

# Vì sao MỌI biểu thức sắp xếp đều kết thúc bằng một cột DUY NHẤT (`id`, hoặc `ma_don` vốn
# UNIQUE cùng tenant): nhiều đơn cùng mức COD — hoặc cùng `cap_nhat_luc`, chuyện rất thường vì
# một lượt cập nhật hàng loạt đóng dấu cùng một giây — thì thứ tự GIỮA CHÚNG là KHÔNG XÁC ĐỊNH.
# Thứ tự không xác định cộng với `OFFSET` cho ra **lặp dòng ở trang này và mất dòng ở trang
# kia**: hỏng im lặng kinh điển của phân trang, vì mỗi trang nhìn riêng đều trông bình thường.
#
# Bản đầu của file này chỉ gắn khoá phá hoà cho `cod_*` và `nang_nhat`, BỎ SÓT `cap_nhat_*`.
# Nó lọt qua ca thử động (SQLite tình cờ trả theo rowid) và chỉ bị bắt bởi ca soát CẤU TRÚC
# `test_c02b` — đúng §12.1: phép đo tình cờ đúng không phải là phép đo.


# ============================================================================
# 6. CHỈ MỤC — DDL_G12Q
# ============================================================================

# AG-00 là người chạy migration (SHARED_CONTRACTS §22). Agent khai hằng DDL trong module của
# mình, AG-00 cắm vào v9. Chỉ `CREATE INDEX IF NOT EXISTS` — không `DROP`, không `ALTER`:
# một chỉ mục thừa tốn ít đĩa, một `DROP` chạy nhầm trên CSDL thật là một sự cố.
#
# Chỉ mục có hai cột đầu `(tenant_id, …)` vì MỌI câu của lớp này đều bắt đầu bằng `tenant_id=?`.
# Chỉ mục không mở đầu bằng `tenant_id` thì không dùng được cho các câu đó.
DDL_G12Q = """
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_tao
    ON don_hang(tenant_id, tao_luc);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_id_desc
    ON don_hang(tenant_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_ttgiao
    ON don_hang(tenant_id, trang_thai_giao, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_cod
    ON don_hang(tenant_id, cod, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_tk_hang
    ON don_hang(tenant_id, carrier_account_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_doisoat
    ON don_hang(tenant_id, can_doi_soat_ket_qua, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_khach
    ON don_hang(tenant_id, khach_hang_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_madon
    ON don_hang(tenant_id, ma_don);
CREATE INDEX IF NOT EXISTS ix_g12q_tkhang_tenant_hang
    ON carrier_accounts(tenant_id, hang);
"""
# KHÔNG khai chỉ mục cho `q` (tìm chữ): `LIKE '%…%'` mở đầu bằng `%` thì **không chỉ mục B-tree
# nào dùng được** — thêm chỉ mục ở đó chỉ tốn đĩa và tốn thời gian ghi mà không nhanh lên một
# phần nghìn giây nào. Muốn tìm chữ nhanh thì phải là FTS5, đó là việc khác và CHƯA được cấp
# quyền. Ghi ra đây để không ai tưởng là bỏ sót (§12.1: rủi ro cố ý bỏ qua thì phải ghi ra).


def ap_ddl(kn=None):
    """Áp `DDL_G12Q`. Chạy được nhiều lần (mọi câu đều `IF NOT EXISTS`)."""
    kn = kn or csdl.mo()
    with csdl.khoa_ghi:
        for cau in DDL_G12Q.split(";"):
            cau = cau.strip()
            if cau:
                kn.execute(cau)
        kn.commit()


# ============================================================================
# 7. CỬA DÙNG CHO ĐƠN HÀNG
# ============================================================================

def tim_don(tenant_id, loc=None, co_cot=None):
    """Tìm đơn ở MÁY CHỦ. Vỏ mỏng quanh `chay(BANG_DON, …)` để bên gọi không phải biết spec."""
    return chay(BANG_DON, tenant_id, loc, co_cot=co_cot)


def mo_ta_bo_loc(spec=BANG_DON):
    """Tự mô tả bộ lọc — để giao diện dựng form mà không phải chép tay danh sách trường.

    Chép tay là hai bản sẽ lệch nhau (§14.6 "một nguồn duy nhất"); ở đây giao diện hỏi máy chủ.
    """
    return {
        "bang": spec.bang,
        "truong": [{"ten": t.ten, "kieu": t.kieu, "la_tien": t.la_tien, "mo_ta": t.mo_ta}
                   for t in spec.truong_loc.values()],
        "sap_xep_duoc": sorted(spec.sap_xep_duoc),
        "sap_xep_mac_dinh": spec.sap_xep_mac_dinh,
        "gioi_han_mac_dinh": GIOI_HAN_MAC_DINH,
        "gioi_han_toi_da": GIOI_HAN_TOI_DA,
        "lech_toi_da": LECH_TOI_DA,
        "tran_dem": TRAN_DEM,
        "dieu_kien_la": "trả 400 — KHÔNG bỏ qua im lặng",
        "ngay_bao_gom": "tu_ngay và den_ngay đều BAO GỒM, so theo ngày lịch giờ VN trên tao_luc",
    }
