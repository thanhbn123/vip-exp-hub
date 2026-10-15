# G07 / G04 — Order Service: mô hình dữ liệu, vòng đời, idempotency, đối soát, gửi hãng qua adapter.
#
# ===== HAI BẤT BIẾN LỚN NHẤT CỦA FILE NÀY (docs/SHARED_CONTRACTS.md mục 10) =====
#
# 1) HAI TRỤC TRẠNG THÁI TÁCH NHAU, KHÔNG GỘP:
#       don_hang.trang_thai        — NGHIỆP VỤ, do NGƯỜI điều khiển: nhap · da_duyet · dang_gui ·
#                                    da_gui · huy
#       don_hang.trang_thai_giao   — GIAO VẬN, do HÃNG báo về: cho_lay · lay_hang · dang_giao ·
#                                    giao_that_bai · giao_thanh_cong · hoan_hang
#                                    (+ hang_trang_thai_giao để chặn sự kiện đến muộn)
#    Vòng đời "mở rộng" kiểu DRAFT/VALIDATED/SUBMITTING/IN_TRANSIT… KHÔNG thêm giá trị mới vào
#    hai cột trên — nó được SUY RA từ hai trục (xem ANH_XA_MO_RONG + trang_thai_mo_rong()).
#    Lý do: thêm enum mới vào cột là phá hợp đồng đang chạy và làm dữ liệu cũ đọc sai.
#
# 2) CHỈ VÀO `da_gui` KHI HÃNG XÁC NHẬN. Hãng hết giờ ⇒ giữ `dang_gui` + can_doi_soat_ket_qua=1.
#    "Không rõ" TUYỆT ĐỐI không được coi là thành công, cũng không được coi là thất bại.
#
# ===== QUY ƯỚC TIỀN (O01) =====
# Mọi trường tiền (`cod`, `gia_tri_khai`, `phi_van_chuyen`, `don_gia` của mặt hàng) là SỐ NGUYÊN
# theo ĐƠN VỊ NHỎ NHẤT của VND — tức ĐỒNG. 150000 = 150.000đ. CẤM dùng float/Decimal ở mọi tầng:
# float làm tiền sai lặng lẽ (0.1+0.2) và `int(float(x))` cắt cụt không báo. `_so_nguyen_tien()`
# dưới đây CHẶN số có phần thập phân thay vì cắt cụt.
# Khối lượng: `khoi_luong_gram` số nguyên GRAM (đơn vị nhỏ nhất), cùng lý do.
#
# ===== IDEMPOTENCY =====
# Do CSDL cưỡng chế bằng UNIQUE(tenant_id, idem_key) — KHÔNG bằng `if`. Mã dưới đây vẫn đọc
# trước cho nhanh, nhưng đường bắt csdl.LoiToanVen mới là đường bảo đảm.
#
# ===== CHỊU ĐƯỢC CSDL CHƯA MIGRATE =====
# Cột/bảng của đợt O01 (external_reference, approved_by, địa chỉ có cấu trúc, don_mat_hang) đều
# được DÒ bằng PRAGMA table_info trước khi dùng (nếp của nhap_file._ghi_trang_thai). Mục đích:
# AG-00 gộp mã này vào trước khi chạy migration thì hệ vẫn chạy, chỉ thiếu tính năng mới.
import re
import threading

import adapter
import adapter_jt   # noqa: F401 — đăng ký adapter
import adapter_vtp  # noqa: F401
import bao_mat
import billing
import csdl
import loi_hang
import quyen


# ============================================================================
# DDL ĐỀ XUẤT CHO AG-00 (O01) — don_hang.py KHÔNG tự chạy nó
# ============================================================================
#
# Hằng số này là MỘT NGUỒN DUY NHẤT cho ba chỗ đang nói về cùng một schema: tài liệu
# docs/G04_ORDER_SERVICE.md, bộ thử app/thu/thu_don_hang.py, và đề xuất gửi AG-00. Viết tay ba
# bản là ba bản sẽ lệch nhau (CLAUDE.md §14.6: hai bản nội dung là hai bản sẽ lệch).
#
# AG-02 KHÔNG được sửa csdl.py / migrate.py (hợp đồng mục 15), nên AG-00 chép khối dưới vào
# `csdl.SCHEMA` và thêm một bước `migrate` cho CSDL đang chạy. Mã trong file này chịu được CSDL
# CHƯA chạy DDL này: cột mới dò bằng PRAGMA, bảng mới dò bằng co_bang().
DDL_G04 = """
ALTER TABLE don_hang ADD COLUMN external_reference TEXT;
ALTER TABLE don_hang ADD COLUMN approved_by INTEGER REFERENCES users(id);
ALTER TABLE don_hang ADD COLUMN approved_luc TEXT;
ALTER TABLE don_hang ADD COLUMN ly_do_tu_choi TEXT;
ALTER TABLE don_hang ADD COLUMN tu_choi_boi INTEGER REFERENCES users(id);
ALTER TABLE don_hang ADD COLUMN tu_choi_luc TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_gui_tinh TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_gui_quan TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_gui_xa TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_gui_buu_chinh TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_nhan_tinh TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_nhan_quan TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_nhan_xa TEXT;
ALTER TABLE don_hang ADD COLUMN nguoi_nhan_buu_chinh TEXT;
CREATE INDEX IF NOT EXISTS ix_don_extref ON don_hang(tenant_id, external_reference);
CREATE TABLE IF NOT EXISTS don_mat_hang (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  don_id INTEGER NOT NULL REFERENCES don_hang(id),
  stt INTEGER NOT NULL,
  ten TEXT NOT NULL,
  ma_sku TEXT NOT NULL DEFAULT '',
  so_luong INTEGER NOT NULL DEFAULT 1,
  don_gia INTEGER NOT NULL DEFAULT 0,          -- ĐỒNG, số nguyên. Cấm float.
  khoi_luong_gram INTEGER NOT NULL DEFAULT 0,  -- GRAM, số nguyên
  ghi_chu TEXT NOT NULL DEFAULT '',
  tao_luc TEXT NOT NULL,
  UNIQUE (don_id, stt)
);
CREATE INDEX IF NOT EXISTS ix_mh_don ON don_mat_hang(don_id);
CREATE INDEX IF NOT EXISTS ix_mh_tenant ON don_mat_hang(tenant_id);
"""


class LoiNghiepVu(Exception):
    def __init__(self, msg, ma=400):
        super().__init__(msg)
        self.ma = ma


# ============================================================================
# O02 — VÒNG ĐỜI: máy trạng thái trục NGHIỆP VỤ + bảng ánh xạ sang vòng đời mở rộng
# ============================================================================

# Chuyển trạng thái HỢP LỆ trên trục nghiệp vụ. Thiếu trong bảng = KHÔNG được chuyển.
# Đây là danh sách TRẮNG có lý do (CLAUDE.md §12.2 nêu đúng ngoại lệ này): quên một dòng thì
# kết quả là CHẶN một chuyển hợp lệ (mất tiện, thấy ngay), không phải CHO QUA một chuyển sai
# (hỏng im lặng). Dùng danh sách đen ở đây là mở cửa cho mọi chuyển trạng thái chưa nghĩ tới.
CHUYEN_DUOC = {
    "nhap":     {"nhap", "da_duyet", "huy"},
    "da_duyet": {"nhap", "dang_gui", "huy"},      # → nhap = sửa lại hoặc bị từ chối duyệt
    "dang_gui": {"da_gui", "da_duyet", "huy"},    # → da_duyet chỉ qua đối soát "hãng chưa nhận"
    "da_gui":   {"huy"},
    "huy":      set(),                            # huy là trạng thái CUỐI
}

# Quyền cần có để thực hiện một chuyển trạng thái (tra CSDL qua quyen.co_quyen).
QUYEN_CHUYEN = {
    ("nhap", "nhap"): "tenant.don.ghi",
    ("nhap", "da_duyet"): "tenant.don.duyet",
    ("nhap", "huy"): "tenant.don.duyet",
    ("da_duyet", "nhap"): "tenant.don.duyet",     # từ chối duyệt / bỏ duyệt
    ("da_duyet", "dang_gui"): "tenant.don.duyet",
    ("da_duyet", "huy"): "tenant.don.duyet",
    ("dang_gui", "da_gui"): "tenant.don.duyet",
    ("dang_gui", "da_duyet"): "tenant.don.duyet",
    ("dang_gui", "huy"): "tenant.don.duyet",
    ("da_gui", "huy"): "tenant.don.duyet",
}

# Hạng trạng thái giao — PHẢI khớp cau_hinh.HANG_TRANG_THAI_GIAO (có ca thử canh).
# Ánh xạ vòng đời mở rộng (directive) ↔ hai trục hiện có.
# Mỗi dòng: (ten_mo_rong, trang_thai, trang_thai_giao, dieu_kien_phu)
ANH_XA_MO_RONG = (
    ("CANCELLED",        "huy",      None,                None),
    ("REJECTED",         "nhap",     None,                "co_ly_do_tu_choi"),
    ("DRAFT",            "nhap",     None,                "chua_hop_le"),
    ("PENDING_APPROVAL", "nhap",     None,                None),   # = VALIDATED, xem ghi chú
    ("APPROVED",         "da_duyet", None,                None),
    ("SUBMIT_UNKNOWN",   "dang_gui", None,                "can_doi_soat"),
    ("SUBMITTING",       "dang_gui", None,                None),
    ("SUBMITTED",        "da_gui",   "cho_lay",           None),
    ("PICKED_UP",        "da_gui",   "lay_hang",          None),
    ("IN_TRANSIT",       "da_gui",   "dang_giao",         None),
    ("DELIVERY_FAILED",  "da_gui",   "giao_that_bai",     None),
    ("DELIVERED",        "da_gui",   "giao_thanh_cong",   None),
    ("RETURNED",         "da_gui",   "hoan_hang",         None),
)

# VALIDATED và PENDING_APPROVAL trong directive là HAI tên cho CÙNG một tình trạng ở hệ này:
# một đơn nháp đã hợp lệ thì đương nhiên đang chờ duyệt — không có bước "bấm nút validate" riêng
# lưu vào CSDL. Nói rõ ở đây để người đọc không đi tìm cột không tồn tại.
MO_RONG_DONG_NGHIA = {"VALIDATED": "PENDING_APPROVAL"}


def kiem_chuyen(cu, moi):
    """Chuyển trạng thái nghiệp vụ hợp lệ hay không. Sai → LoiNghiepVu 409."""
    if cu not in CHUYEN_DUOC:
        raise LoiNghiepVu(f"trạng thái hiện tại lạ: '{cu}'", 500)
    if moi not in CHUYEN_DUOC[cu]:
        raise LoiNghiepVu(
            f"không được chuyển '{cu}' → '{moi}' (hợp lệ: {sorted(CHUYEN_DUOC[cu]) or 'không còn gì'})",
            409)


def trang_thai_mo_rong(don):
    """Suy ra tên vòng đời MỞ RỘNG từ hai trục + cờ phụ. KHÔNG đọc cột nào mới bắt buộc."""
    d = dict(don)
    tt = d.get("trang_thai")
    ttg = d.get("trang_thai_giao")
    for ten, c_tt, c_ttg, dk in ANH_XA_MO_RONG:
        if tt != c_tt:
            continue
        if c_ttg is not None and ttg != c_ttg:
            continue
        if dk == "can_doi_soat" and not d.get("can_doi_soat_ket_qua"):
            continue
        if dk == "co_ly_do_tu_choi" and not d.get("ly_do_tu_choi"):
            continue
        if dk == "chua_hop_le" and not _kiem_du_lieu(d):
            continue
        return ten
    # da_gui mà trang_thai_giao lạ/trống: nói thẳng là chưa xác định, không đoán.
    return "SUBMITTED" if tt == "da_gui" else f"KHONG_RO:{tt}/{ttg}"


# ============================================================================
# O01 — MÔ HÌNH DỮ LIỆU: dò schema (chịu được CSDL chưa migrate) + quy ước tiền
# ============================================================================

# Cột MỚI của đợt O01 trên don_hang. Mã dưới đây chỉ ghi/đọc cột nào CSDL thật sự có.
COT_MOI_DON = (
    "external_reference",      # mã đơn phía hệ ngoài (sàn, ERP) — để đối chiếu hai đầu
    "approved_by", "approved_luc",
    "ly_do_tu_choi", "tu_choi_boi", "tu_choi_luc",
    "nguoi_gui_tinh", "nguoi_gui_quan", "nguoi_gui_xa", "nguoi_gui_buu_chinh",
    "nguoi_nhan_tinh", "nguoi_nhan_quan", "nguoi_nhan_xa", "nguoi_nhan_buu_chinh",
)
COT_DIA_CHI_CO_CAU_TRUC = tuple(c for c in COT_MOI_DON if c.startswith(("nguoi_gui_", "nguoi_nhan_")))

_cache_cot = {}
_cache_bang = {}
_khoa_cache = threading.RLock()


def _cot_cua(bang):
    """Tập tên cột thật của một bảng. Có nhớ đệm — schema không đổi trong một lượt chạy.
    PRAGMA chỉ đọc SIÊU DỮ LIỆU, không đọc dòng dữ liệu nào, nên không cần điều kiện tenant."""
    with _khoa_cache:
        if bang not in _cache_cot:
            try:
                _cache_cot[bang] = {r["name"] for r in csdl.nhieu(f"PRAGMA table_info({bang})")}
            except csdl.LoiCSDL:
                _cache_cot[bang] = set()
        return _cache_cot[bang]


def co_cot(bang, cot):
    return cot in _cot_cua(bang)


def co_bang(bang):
    with _khoa_cache:
        if bang not in _cache_bang:
            _cache_bang[bang] = bool(_cot_cua(bang))
        return _cache_bang[bang]


def quen_cache_schema():
    """Gọi sau migration (hoặc trong bộ thử dựng lại CSDL) để dò lại schema."""
    with _khoa_cache:
        _cache_cot.clear()
        _cache_bang.clear()


def _so_nguyen_tien(gt, ten):
    """Tiền và khối lượng: SỐ NGUYÊN theo đơn vị nhỏ nhất (đồng / gram).

    CHẶN phần thập phân thay vì cắt cụt. `int(float("150000.7"))` = 150000 — mất 7 hào mà
    không báo gì; mất tiền im lặng là dạng hỏng xấu nhất (§12.2). Thà báo lỗi để người sửa.
    """
    if gt is None or gt == "":
        return 0
    if isinstance(gt, bool):
        raise LoiNghiepVu(f"{ten} không được là true/false")
    if isinstance(gt, int):
        return gt
    if isinstance(gt, float):
        if gt != int(gt):
            raise LoiNghiepVu(f"{ten} phải là số nguyên theo đồng/gram, nhận {gt!r} có phần thập phân")
        return int(gt)
    s = str(gt).strip().replace(" ", "")
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    m = re.fullmatch(r"(-?\d+)[.,](\d+)", s)
    if m:
        if int(m.group(2)) != 0:
            raise LoiNghiepVu(f"{ten} phải là số nguyên theo đồng/gram, nhận {gt!r} có phần thập phân")
        return int(m.group(1))
    raise LoiNghiepVu(f"{ten} không phải số nguyên: {gt!r}")


TRUONG_TIEN = ("cod", "gia_tri_khai")


def _kiem_du_lieu(d):
    """Trả DANH SÁCH lỗi (rỗng = hợp lệ). Không ném — để người gọi quyết định."""
    loi = []
    for t in ("nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi",
              "nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa"):
        if not str(d.get(t, "") or "").strip():
            loi.append(f"thiếu {t}")
    for t in ("nguoi_gui_sdt", "nguoi_nhan_sdt"):
        v = str(d.get(t, "") or "").replace(" ", "").replace(".", "")
        if v and not re.fullmatch(r"0\d{9}", v):
            loi.append(f"{t} phải 10 số bắt đầu bằng 0")
    try:
        if _so_nguyen_tien(d.get("khoi_luong_gram", 0), "khoi_luong_gram") <= 0:
            loi.append("khoi_luong_gram phải > 0")
    except LoiNghiepVu as e:
        loi.append(str(e))
    for t in TRUONG_TIEN:
        try:
            if _so_nguyen_tien(d.get(t, 0), t) < 0:
                loi.append(f"{t} không được âm")
        except LoiNghiepVu as e:
            loi.append(str(e))
    return loi


def kiem_don(tenant_id, don_id=None, d=None):
    """O03 — VALIDATE ORDER riêng: kiểm mà KHÔNG đổi gì trong CSDL.

    Gọi được hai kiểu: `kiem_don(tid, don_id=5)` kiểm đơn đã lưu, hoặc `kiem_don(tid, d={...})`
    kiểm dữ liệu chưa lưu (màn nhập liệu gọi trước khi bấm Lưu).
    Trả: {"hop_le": bool, "loi": [...], "canh_bao": [...], "trang_thai_mo_rong": "..."}.
    """
    if d is None:
        if don_id is None:
            raise LoiNghiepVu("kiem_don cần don_id hoặc d")
        don = lay_don(tenant_id, don_id)
        if not don:
            raise LoiNghiepVu("không có đơn này", 404)
        d = dict(don)
    loi = _kiem_du_lieu(d)
    canh_bao = []
    # CẢNH BÁO ≠ LỖI: cảnh báo không chặn lưu, chỉ nhắc người xem lại. Trộn hai thứ này làm
    # người dùng bỏ qua cả hai.
    try:
        if _so_nguyen_tien(d.get("cod", 0), "cod") > 0 and \
           _so_nguyen_tien(d.get("gia_tri_khai", 0), "gia_tri_khai") == 0:
            canh_bao.append("có thu hộ (COD) nhưng chưa khai giá trị hàng — hãng có thể từ chối bồi thường")
        if _so_nguyen_tien(d.get("khoi_luong_gram", 0), "khoi_luong_gram") > 30_000:
            canh_bao.append("khối lượng > 30kg — nhiều hãng tính là hàng nặng, cần xác nhận phí")
    except LoiNghiepVu:
        pass          # phần tiền đã vào `loi` ở trên rồi; không nhân đôi thông báo
    if d.get("nguoi_gui_sdt") and d.get("nguoi_gui_sdt") == d.get("nguoi_nhan_sdt"):
        canh_bao.append("số điện thoại người gửi và người nhận giống nhau")
    ra = {"hop_le": not loi, "loi": loi, "canh_bao": canh_bao}
    if d.get("trang_thai"):
        ra["trang_thai_mo_rong"] = trang_thai_mo_rong(d)
    return ra


# ============================================================================
# QUYỀN CỦA ACTOR — tra CSDL, không tin người gọi
# ============================================================================

def vai_tro_trong_tenant(tenant_id, user_id):
    r = csdl.mot("SELECT role FROM tenant_memberships WHERE user_id=? AND tenant_id=?"
                 " AND trang_thai='hoat_dong'", (user_id, tenant_id))
    return r["role"] if r else None


def _can_quyen(tenant_id, user_id, hanh_dong):
    """Cưỡng chế quyền NGAY TRONG tầng nghiệp vụ, không chỉ ở route.

    server.py đã có `_can()` ở từng endpoint, nhưng lớp đó chỉ phủ đường HTTP. Import engine,
    polling và mọi người gọi sau này đi thẳng vào đây. Kiểm ở hai nơi là cố ý — khác với
    "lọc hai chỗ" mà §12.2 cấm: ở đây cả hai lớp CÙNG tra một nguồn (bảng role_permissions),
    nên không thể lệch nhau; cái §12.2 cấm là hai BỘ LỌC khác nhau chồng lên nhau.
    """
    vt = vai_tro_trong_tenant(tenant_id, user_id)
    if not vt:
        raise LoiNghiepVu("người dùng không thuộc doanh nghiệp này", 403)
    if not quyen.co_quyen(vt, hanh_dong):
        raise LoiNghiepVu(f"vai trò {vt} không có quyền {hanh_dong}", 403)
    return vt


# ============================================================================
# LÕI: tạo / sửa / lấy
# ============================================================================

def _sinh_ma_don(tenant_id):
    so = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (tenant_id,))["c"]
    return f"T{tenant_id}-{so + 1:06d}"


def _ghi_lich_su(don_id, nguon, noi_dung):
    csdl.ghi("INSERT INTO don_lich_su (don_id, luc, nguon, noi_dung) VALUES (?,?,?,?)",
             (don_id, csdl.bay_gio(), nguon, noi_dung))


def lay_don(tenant_id, don_id):
    """Luôn kèm điều kiện tenant — resource ownership."""
    return csdl.mot("SELECT * FROM don_hang WHERE id=? AND tenant_id=?", (don_id, tenant_id))


def _chuan_hoa_vao(d):
    """Chuẩn hóa dữ liệu vào: cắt khoảng trắng, đổi tiền/khối lượng sang số nguyên."""
    ra = dict(d)
    for t in ("nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi", "nguoi_nhan_ten",
              "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa") + COT_DIA_CHI_CO_CAU_TRUC:
        if ra.get(t) is not None:
            ra[t] = str(ra[t]).strip()
    for t in TRUONG_TIEN + ("khoi_luong_gram",):
        if t in ra:
            ra[t] = _so_nguyen_tien(ra[t], t)
    return ra


def tao_don(tenant_id, user_id, d, idem_key=None, kiem_quyen=True):
    """Tạo đơn nháp. idem_key trùng → trả đơn cũ, không tạo mới (UNIQUE CSDL cưỡng chế).

    Trả (don_dict, da_trung_idem). `kiem_quyen=False` chỉ dành cho lượt dựng dữ liệu nền của
    bộ thử — đường chạy thật KHÔNG được truyền False.
    """
    if kiem_quyen:
        _can_quyen(tenant_id, user_id, "tenant.don.ghi")
    d = _chuan_hoa_vao(d)
    loi = _kiem_du_lieu(d)
    if loi:
        raise LoiNghiepVu("; ".join(loi))
    if d.get("khach_hang_id"):
        kh = csdl.mot("SELECT id FROM khach_hang WHERE id=? AND tenant_id=?",
                      (d["khach_hang_id"], tenant_id))
        if not kh:
            raise LoiNghiepVu("khách hàng không thuộc doanh nghiệp này", 404)

    cot = ["tenant_id", "ma_don", "idem_key", "khach_hang_id",
           "nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi",
           "nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi",
           "hang_hoa", "khoi_luong_gram", "cod", "gia_tri_khai", "ghi_chu",
           "nguoi_tao", "tao_luc", "cap_nhat_luc"]
    gt = [tenant_id, None, idem_key, d.get("khach_hang_id"),
          d["nguoi_gui_ten"], d["nguoi_gui_sdt"], d["nguoi_gui_dia_chi"],
          d["nguoi_nhan_ten"], d["nguoi_nhan_sdt"], d["nguoi_nhan_dia_chi"],
          d["hang_hoa"], d["khoi_luong_gram"], d.get("cod", 0) or 0,
          d.get("gia_tri_khai", 0) or 0, d.get("ghi_chu", ""), user_id,
          csdl.bay_gio(), csdl.bay_gio()]
    # Cột mới: chỉ ghi nếu CSDL ĐÃ migrate (dò bằng PRAGMA). Chưa có cột thì bỏ qua lặng
    # lẽ ĐƯỢC — vì đó là trường phụ, và mục đích là để AG-00 gộp mã trước migration.
    for c in ("external_reference",) + COT_DIA_CHI_CO_CAU_TRUC:
        if d.get(c) not in (None, "") and co_cot("don_hang", c):
            cot.append(c)
            gt.append(d[c])
    sql = ("INSERT INTO don_hang (" + ",".join(cot) + ") VALUES ("
           + ",".join("?" * len(cot)) + ")")

    with csdl.khoa_ghi:
        if idem_key:
            cu = csdl.mot("SELECT * FROM don_hang WHERE tenant_id=? AND idem_key=?",
                          (tenant_id, idem_key))
            if cu:
                return dict(cu), True
        con = None
        for lan in range(5):
            gt[1] = _sinh_ma_don(tenant_id)
            try:
                con = csdl.ghi(sql, gt)
                break
            except csdl.LoiToanVen as e:
                # Phân biệt HAI ràng buộc khác nhau, không gộp làm một:
                #  - UNIQUE(tenant_id, idem_key) → lượt song song vừa tạo đúng đơn này ⇒ trả đơn đó
                #  - UNIQUE(tenant_id, ma_don)   → COUNT(*) đụng nhau giữa hai TIẾN TRÌNH ⇒ sinh lại
                if idem_key:
                    cu = csdl.mot("SELECT * FROM don_hang WHERE tenant_id=? AND idem_key=?",
                                  (tenant_id, idem_key))
                    if cu:
                        return dict(cu), True
                if "ma_don" in str(e) and lan < 4:
                    continue
                raise
        if con is None:
            raise LoiNghiepVu("không sinh được mã đơn duy nhất sau 5 lần thử", 500)
    don_id = con.lastrowid
    _ghi_lich_su(don_id, f"user:{user_id}", "tạo đơn nháp")
    if d.get("mat_hang"):
        luu_mat_hang(tenant_id, user_id, don_id, d["mat_hang"], kiem_quyen=False)
    return dict(lay_don(tenant_id, don_id)), False


TRUONG_SUA_DUOC = ("nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi", "nguoi_nhan_ten",
                   "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa", "khoi_luong_gram",
                   "cod", "gia_tri_khai", "ghi_chu")


def sua_don(tenant_id, user_id, don_id, d):
    _can_quyen(tenant_id, user_id, "tenant.don.ghi")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] not in ("nhap", "da_duyet"):
        raise LoiNghiepVu(f"đơn ở trạng thái '{don['trang_thai']}' — chỉ sửa được trước khi gửi hãng",
                          409)
    kiem_chuyen(don["trang_thai"], "nhap")   # sửa = quay về nháp; để máy trạng thái nói, không tự quyết
    d = _chuan_hoa_vao(d)
    gop = dict(don)
    gop.update({k: v for k, v in d.items() if k in TRUONG_SUA_DUOC})
    loi = _kiem_du_lieu(gop)
    if loi:
        raise LoiNghiepVu("; ".join(loi))
    dat = [f"{c}=?" for c in TRUONG_SUA_DUOC]
    tsq = [gop[c] if c != "ghi_chu" else (gop.get("ghi_chu") or "") for c in TRUONG_SUA_DUOC]
    # Sửa lại đơn thì lý do từ chối cũ hết nghĩa — xóa để trạng thái mở rộng không mắc ở REJECTED.
    for c in ("external_reference",) + COT_DIA_CHI_CO_CAU_TRUC:
        if c in d and co_cot("don_hang", c):
            dat.append(f"{c}=?")
            tsq.append(d[c])
    for c in ("ly_do_tu_choi", "tu_choi_boi", "tu_choi_luc"):
        if co_cot("don_hang", c):
            dat.append(f"{c}=NULL")
    csdl.ghi(f"UPDATE don_hang SET {','.join(dat)}, trang_thai='nhap', cap_nhat_luc=?"
             " WHERE id=? AND tenant_id=?", tsq + [csdl.bay_gio(), don_id, tenant_id])
    _ghi_lich_su(don_id, f"user:{user_id}", "sửa đơn (về trạng thái nháp)")
    return dict(lay_don(tenant_id, don_id))


def duyet_don(tenant_id, user_id, don_id):
    _can_quyen(tenant_id, user_id, "tenant.don.duyet")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    kiem_chuyen(don["trang_thai"], "da_duyet")
    loi = _kiem_du_lieu(dict(don))
    if loi:
        # Duyệt một đơn chưa hợp lệ là đẩy lỗi xuống tận lượt gọi hãng mới phát hiện.
        raise LoiNghiepVu("đơn chưa hợp lệ, không duyệt được: " + "; ".join(loi))
    dat = ["trang_thai='da_duyet'", "cap_nhat_luc=?"]
    tsq = [csdl.bay_gio()]
    if co_cot("don_hang", "approved_by"):
        dat.append("approved_by=?"); tsq.append(user_id)
    if co_cot("don_hang", "approved_luc"):
        dat.append("approved_luc=?"); tsq.append(csdl.bay_gio())
    for c in ("ly_do_tu_choi", "tu_choi_boi", "tu_choi_luc"):
        if co_cot("don_hang", c):
            dat.append(f"{c}=NULL")
    csdl.ghi(f"UPDATE don_hang SET {','.join(dat)} WHERE id=? AND tenant_id=?",
             tsq + [don_id, tenant_id])
    _ghi_lich_su(don_id, f"user:{user_id}", "duyệt đơn")
    return dict(lay_don(tenant_id, don_id))


def tu_choi_don(tenant_id, user_id, don_id, ly_do):
    """O03 — TỪ CHỐI DUYỆT, bắt buộc có lý do.

    Ánh xạ: REJECTED của directive = `trang_thai='nhap'` + `ly_do_tu_choi` khác NULL. KHÔNG
    thêm giá trị enum mới vào `trang_thai` (hợp đồng mục 10 đóng băng 5 giá trị đó).
    Người bị từ chối sửa đơn rồi xin duyệt lại — `sua_don` tự xóa lý do cũ.
    """
    _can_quyen(tenant_id, user_id, "tenant.don.duyet")
    ly_do = str(ly_do or "").strip()
    if not ly_do:
        raise LoiNghiepVu("từ chối phải có lý do — người sửa đơn cần biết sửa gì")
    if len(ly_do) > 1000:
        raise LoiNghiepVu("lý do từ chối quá dài (tối đa 1000 ký tự)")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] not in ("nhap", "da_duyet"):
        raise LoiNghiepVu(f"chỉ từ chối được đơn chờ duyệt hoặc đã duyệt (hiện: {don['trang_thai']})",
                          409)
    kiem_chuyen(don["trang_thai"], "nhap")
    if not co_cot("don_hang", "ly_do_tu_choi"):
        # Không có cột thì KHÔNG được âm thầm bỏ lý do: lý do là toàn bộ giá trị của hành động này.
        raise LoiNghiepVu("CSDL chưa có cột ly_do_tu_choi — cần chạy migration G04 trước khi dùng"
                          " chức năng từ chối", 501)
    dat = ["trang_thai='nhap'", "ly_do_tu_choi=?", "cap_nhat_luc=?"]
    tsq = [ly_do, csdl.bay_gio()]
    if co_cot("don_hang", "tu_choi_boi"):
        dat.append("tu_choi_boi=?"); tsq.append(user_id)
    if co_cot("don_hang", "tu_choi_luc"):
        dat.append("tu_choi_luc=?"); tsq.append(csdl.bay_gio())
    if co_cot("don_hang", "approved_by"):
        dat.append("approved_by=NULL")
    if co_cot("don_hang", "approved_luc"):
        dat.append("approved_luc=NULL")
    csdl.ghi(f"UPDATE don_hang SET {','.join(dat)} WHERE id=? AND tenant_id=?",
             tsq + [don_id, tenant_id])
    _ghi_lich_su(don_id, f"user:{user_id}", f"TỪ CHỐI duyệt: {ly_do}")
    csdl.audit("don_tu_choi", f"don:{don_id}", ly_do, tenant_id=tenant_id, user_id=user_id)
    return dict(lay_don(tenant_id, don_id))


# ============================================================================
# O04 — GỬI HÃNG, IDEMPOTENCY, KẾT QUẢ KHÔNG RÕ, ĐỐI SOÁT
# ============================================================================

def _adapter_cua_account(tenant_id, account_id):
    tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=? AND tenant_id=? AND kich_hoat=1",
                  (account_id, tenant_id))
    if not tk:
        raise LoiNghiepVu("tài khoản hãng không tồn tại hoặc không thuộc doanh nghiệp này", 404)
    cred = bao_mat.giai_ma_cred(tk["credentials_ma_hoa"], tk["tenant_id"], tk["hang"])
    return adapter.tao_adapter(tk["hang"], cred, tk["moi_truong"]), tk


def _chiem_de_gui(tenant_id, don_id, carrier_account_id):
    """CHIẾM đơn để gửi bằng MỘT câu UPDATE có điều kiện — không phải đọc-rồi-ghi.

    Vì sao phải vậy: hai lượt gửi song song cùng đọc thấy `da_duyet` thì cả hai đều tưởng mình
    là người đầu tiên và cả hai đều gọi createOrder ⇒ HAI vận đơn cho một đơn, mất tiền thật
    và không có gì báo. Câu UPDATE dưới đây chỉ khớp khi đơn còn ở `da_duyet`, nên đúng MỘT
    lượt thắng; lượt thua thấy rowcount=0 và dừng.

    Chỉ chiếm từ `da_duyet`. Đơn đang ở `dang_gui` KHÔNG được gửi lại ở đây — phải đi qua
    `doi_soat_don()` để biết hãng đã nhận chưa (xem gui_don).
    """
    with csdl.khoa_ghi:
        con = csdl.ghi(
            "UPDATE don_hang SET trang_thai='dang_gui', carrier_account_id=?, cap_nhat_luc=?"
            " WHERE id=? AND tenant_id=? AND trang_thai='da_duyet'",
            (carrier_account_id, csdl.bay_gio(), don_id, tenant_id))
        return con.rowcount


def gui_don(tenant_id, user_id, don_id, carrier_account_id):
    """Gửi đơn ĐÃ DUYỆT sang hãng (qua adapter). Chỉ `da_gui` khi hãng XÁC NHẬN."""
    _can_quyen(tenant_id, user_id, "tenant.don.duyet")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] == "da_gui":
        return dict(don)       # đã gửi rồi — idempotent, KHÔNG gửi lại, không tăng usage
    if don["trang_thai"] == "dang_gui":
        if don["can_doi_soat_ket_qua"]:
            raise LoiNghiepVu(
                "lượt gửi trước KHÔNG RÕ kết quả — phải đối soát với hãng (doi_soat_don) trước"
                " khi gửi lại, nếu không có nguy cơ tạo vận đơn trùng", 409)
        raise LoiNghiepVu("đơn đang được gửi ở một lượt khác — chờ kết quả", 409)
    if don["trang_thai"] != "da_duyet":
        raise LoiNghiepVu(f"đơn phải được duyệt trước khi gửi (hiện: {don['trang_thai']})", 409)
    kiem_chuyen(don["trang_thai"], "dang_gui")

    ad, tk = _adapter_cua_account(tenant_id, carrier_account_id)
    if not ad.capability("createOrder"):
        raise LoiNghiepVu(f"hãng {ad.ten_hang} không hỗ trợ tạo đơn qua API")
    # G04-L3 (AG-00 vá 15/10). Bản cũ trừ suất TRƯỚC khi chiếm đơn, nên rò suất ở BA đường:
    #   (1) luồng thua ở `_chiem_de_gui` đã bị trừ suất dù KHÔNG gửi gì;
    #   (2) hãng TỪ CHỐI — không có vận đơn nào, nhưng suất đã mất và lượt gửi lại mất suất nữa;
    #   (3) hãng TIMEOUT rồi đối soát ra `chua_vao` — gửi lại là trừ lần hai cho CÙNG một đơn.
    # Đổi thứ tự xử (1): chiếm trước, chỉ luồng THẮNG mới bị trừ. Vượt hạn mức thì phải NHẢ
    # chỗ đã chiếm, nếu không đơn mắc ở `dang_gui` vĩnh viễn.
    if _chiem_de_gui(tenant_id, don_id, carrier_account_id) == 0:
        raise LoiNghiepVu("đơn vừa được một lượt khác chiếm để gửi — không gửi lần hai", 409)
    try:
        billing.kiem_va_tang_don(tenant_id)
    except Exception:
        csdl.ghi("UPDATE don_hang SET trang_thai='da_duyet', cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=? AND trang_thai='dang_gui'",
                 (csdl.bay_gio(), don_id, tenant_id))
        raise

    try:
        kq = ad.createOrder(dict(don))
    except Exception:
        # Ngoại lệ lúc gọi hãng: KHÔNG hoàn suất. Ở đây không biết hãng đã nhận đơn hay chưa —
        # cùng tình huống với timeout. Hoàn suất tức là khẳng định "không có đơn nào", mà mình
        # không có bằng chứng đó. Thà tính dư một suất còn hơn mở đường tạo vận đơn trùng.
        csdl.ghi("UPDATE don_hang SET can_doi_soat_ket_qua=1, cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=?", (csdl.bay_gio(), don_id, tenant_id))
        _ghi_lich_su(don_id, f"user:{user_id}",
                     f"gửi {ad.ten_hang} NỔ NGOẠI LỆ — chưa rõ kết quả, cần đối soát")
        raise
    if kq.ok:
        phi = ad.getShippingFee(dict(don)) if ad.capability("getShippingFee") else None
        csdl.ghi("UPDATE don_hang SET trang_thai='da_gui', ma_van_don=?, phi_van_chuyen=?,"
                 " can_doi_soat_ket_qua=0, trang_thai_giao='cho_lay', hang_trang_thai_giao=1,"
                 " cap_nhat_luc=? WHERE id=? AND tenant_id=?",
                 (kq.ma_van_don, phi.phi if (phi and phi.ok) else None, csdl.bay_gio(),
                  don_id, tenant_id))
        _ghi_lich_su(don_id, f"user:{user_id}",
                     f"hãng {ad.ten_hang} ({tk['moi_truong']}) xác nhận, mã vận đơn {kq.ma_van_don}")
    elif kq.timeout:
        # KHÔNG biết kết quả — giữ dang_gui, bật cờ phải đối soát; KHÔNG nhận thành công/thất bại.
        csdl.ghi("UPDATE don_hang SET can_doi_soat_ket_qua=1, cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=?", (csdl.bay_gio(), don_id, tenant_id))
        _ghi_lich_su(don_id, f"user:{user_id}",
                     f"gửi {ad.ten_hang} TIMEOUT — chưa rõ kết quả, cần đối soát bằng"
                     f" {'getOrder' if ad.capability('getOrder') else 'trackOrder'}")
    else:
        csdl.ghi("UPDATE don_hang SET trang_thai='da_duyet', cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=?", (csdl.bay_gio(), don_id, tenant_id))
        # Hãng TỪ CHỐI là câu trả lời RÕ RÀNG: không có vận đơn nào được tạo. Nên hoàn suất —
        # khác hẳn timeout, nơi mình không biết gì. Đây là chỗ duy nhất trong gui_don được hoàn.
        billing.hoan_don(tenant_id)
        _ghi_lich_su(don_id, f"user:{user_id}",
                     f"hãng {ad.ten_hang} từ chối: {kq.loi} — đã hoàn 1 suất đơn của gói")
        raise LoiNghiepVu(f"hãng từ chối: {kq.loi}", 502)
    return dict(lay_don(tenant_id, don_id))


def thao_tac_doi_soat(ad):
    """Thao tác CHỈ ĐỌC dùng để đối soát, theo capability THẬT của hãng — không giả định.

    J&T: tài liệu công khai chưa thấy getOrder riêng ⇒ `getOrder=False`, đối soát bằng
    `trackOrder`. VTP: khai `getOrder=True`. Hãng nào không có cả hai thì KHÔNG đối soát
    bằng máy được — phải người xác nhận (doi_soat_tay).
    """
    if ad.capability("getOrder"):
        return "getOrder"
    if ad.capability("trackOrder"):
        return "trackOrder"
    return None


def doi_soat_don(tenant_id, user_id, don_id):
    """O04 — ĐỐI SOÁT đơn "không rõ kết quả" với hãng TRƯỚC khi cho gửi lại.

    Ba kết luận, KHÔNG gộp:
      `da_vao`       — hãng xác nhận có đơn ⇒ chuyển `da_gui`, lấy mã vận đơn của hãng.
      `chua_vao`     — hãng nói KHÔNG TÌM THẤY ⇒ lùi về `da_duyet`, cho gửi lại an toàn.
      `van_chua_ro`  — hỏi mà vẫn không biết ⇒ GIỮ NGUYÊN `dang_gui` + cờ. Không mở đường gửi lại.

    Luật an toàn quan trọng nhất ở đây: chỉ kết luận `chua_vao` khi hãng nói RÕ là không tìm
    thấy (mã chuẩn KHONG_TIM_THAY). Mọi lỗi khác — sai chữ ký, quá hạn mức, lỗi lạ — đều là
    `van_chua_ro`. Coi "lỗi nào cũng là chưa vào" là đường ngắn nhất tới vận đơn trùng.
    """
    _can_quyen(tenant_id, user_id, "tenant.don.duyet")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if not don["can_doi_soat_ket_qua"]:
        return {"ket_luan": "khong_can", "don": dict(don),
                "ghi_chu": "đơn không có cờ cần đối soát"}
    if not don["carrier_account_id"]:
        raise LoiNghiepVu("đơn chưa gắn tài khoản hãng — không biết hỏi ai", 409)
    ad, tk = _adapter_cua_account(tenant_id, don["carrier_account_id"])
    thao_tac = thao_tac_doi_soat(ad)
    if not thao_tac:
        raise LoiNghiepVu(
            f"hãng {ad.ten_hang} không hỗ trợ getOrder lẫn trackOrder — máy KHÔNG đối soát được."
            " Người phải tra trên cổng của hãng rồi xác nhận bằng doi_soat_tay()", 409)
    # Khóa tra: ưu tiên mã vận đơn; chưa có thì dùng mã đơn nội bộ — với J&T đó đúng là
    # `txlogisticId` đã gửi lên, nên hãng tra được.
    khoa_tra = don["ma_van_don"] or don["ma_don"]
    kq = getattr(ad, thao_tac)(khoa_tra)

    if kq.ok and kq.ma_van_don:
        phi = ad.getShippingFee(dict(don)) if ad.capability("getShippingFee") else None
        csdl.ghi("UPDATE don_hang SET trang_thai='da_gui', ma_van_don=?, phi_van_chuyen=?,"
                 " can_doi_soat_ket_qua=0, trang_thai_giao=COALESCE(trang_thai_giao,'cho_lay'),"
                 " hang_trang_thai_giao=MAX(hang_trang_thai_giao,1), cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=?",
                 (kq.ma_van_don, phi.phi if (phi and phi.ok) else don["phi_van_chuyen"],
                  csdl.bay_gio(), don_id, tenant_id))
        _ghi_lich_su(don_id, f"user:{user_id}",
                     f"ĐỐI SOÁT {thao_tac} với {ad.ten_hang}: hãng ĐÃ nhận đơn,"
                     f" mã vận đơn {kq.ma_van_don} → da_gui")
        ket_luan = "da_vao"
    elif _la_khong_tim_thay(kq):
        csdl.ghi("UPDATE don_hang SET trang_thai='da_duyet', can_doi_soat_ket_qua=0,"
                 " cap_nhat_luc=? WHERE id=? AND tenant_id=?", (csdl.bay_gio(), don_id, tenant_id))
        # G04-L3 đường (3): hãng nói RÕ là không có đơn ⇒ suất đã trừ ở lượt gửi timeout là
        # suất của một đơn KHÔNG TỒN TẠI, và lượt gửi lại sẽ trừ suất lần nữa cho cùng một đơn.
        # CHỈ hoàn ở nhánh `chua_vao`: `van_chua_ro` thì hoàn là khẳng định điều mình không
        # biết, còn `da_vao` thì đơn có thật nên suất đã dùng đúng.
        billing.hoan_don(tenant_id)
        _ghi_lich_su(don_id, f"user:{user_id}",
                     f"ĐỐI SOÁT {thao_tac} với {ad.ten_hang}: hãng KHÔNG có đơn này"
                     f" → lùi về da_duyet, được gửi lại; đã hoàn 1 suất đơn của gói")
        ket_luan = "chua_vao"
    else:
        _ghi_lich_su(don_id, f"user:{user_id}",
                     f"ĐỐI SOÁT {thao_tac} với {ad.ten_hang}: VẪN CHƯA RÕ ({kq.loi})"
                     f" — giữ dang_gui, KHÔNG gửi lại")
        ket_luan = "van_chua_ro"
    csdl.audit("don_doi_soat", f"don:{don_id}", f"{thao_tac}:{ket_luan}",
               tenant_id=tenant_id, user_id=user_id)
    return {"ket_luan": ket_luan, "thao_tac": thao_tac, "hang": ad.ma_hang,
            "moi_truong": tk["moi_truong"], "la_mock": tk["moi_truong"] == "mock",
            "don": dict(lay_don(tenant_id, don_id))}


def _la_khong_tim_thay(kq):
    """Hãng có nói RÕ là không tìm thấy đơn hay không. Mặc định: KHÔNG (an toàn)."""
    if kq.ok or kq.timeout:
        return False
    tho = kq.tho or {}
    if tho.get("khong_tim_thay") is True:
        return True
    chuan = tho.get("loi_chuan") or {}
    return chuan.get("ma") == loi_hang.KHONG_TIM_THAY


KET_LUAN_TAY = ("da_vao", "chua_vao")

# Sáu mã lý do từ chối. NGUỒN CHÂN LÝ ở đây (backend), `admin/logic.js` phải khớp — có ca thử
# đối chiếu hai bên, vì hai bản danh sách là hai bản sẽ lệch nhau (§14.6).
LY_DO_TU_CHOI_MA = {
    "sai_dia_chi": "Địa chỉ nhận sai hoặc không đủ",
    "trung_don": "Đơn trùng với đơn đã tạo",
    "khach_huy": "Khách hủy trước khi gửi",
    "qua_kho": "Hàng quá khổ / quá cân so với hãng nhận",
    "sai_cod": "COD sai so với thỏa thuận",
    "khac": "Lý do khác (ghi rõ ở ghi chú)",
}


def doi_soat_tay(tenant_id, user_id, don_id, ket_luan, ma_van_don=None, ghi_chu=""):
    """Đối soát do NGƯỜI xác nhận, cho hãng mà máy không tra được.

    Vì sao cần: không có đường này thì một đơn `dang_gui` của hãng thiếu getOrder/trackOrder sẽ
    mắc ở đó vĩnh viễn. Vì sao phải là NGƯỜI: máy không có bằng chứng nào để kết luận, nên
    người mang bằng chứng (ảnh cổng hãng, điện thoại cho hãng) và chịu trách nhiệm — vết ghi
    rõ là kết luận của người, không phải của hệ (§12.1: đừng để dấu vết nói sai ai đã làm).
    """
    _can_quyen(tenant_id, user_id, "tenant.don.duyet")
    if ket_luan not in KET_LUAN_TAY:
        raise LoiNghiepVu(f"ket_luan phải là một trong {KET_LUAN_TAY}")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] != "dang_gui":
        raise LoiNghiepVu(f"chỉ đối soát tay đơn đang ở dang_gui (hiện: {don['trang_thai']})", 409)
    if ket_luan == "da_vao":
        if not str(ma_van_don or "").strip():
            raise LoiNghiepVu("kết luận 'hãng đã nhận' phải kèm mã vận đơn thật của hãng")
        csdl.ghi("UPDATE don_hang SET trang_thai='da_gui', ma_van_don=?, can_doi_soat_ket_qua=0,"
                 " trang_thai_giao=COALESCE(trang_thai_giao,'cho_lay'),"
                 " hang_trang_thai_giao=MAX(hang_trang_thai_giao,1), cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=?",
                 (str(ma_van_don).strip(), csdl.bay_gio(), don_id, tenant_id))
    else:
        csdl.ghi("UPDATE don_hang SET trang_thai='da_duyet', can_doi_soat_ket_qua=0,"
                 " cap_nhat_luc=? WHERE id=? AND tenant_id=?", (csdl.bay_gio(), don_id, tenant_id))
        # Cùng lý do như đường (3): NGƯỜI kết luận hãng không có đơn, nên suất đã trừ là của
        # một đơn không tồn tại và lượt gửi lại sẽ trừ lần nữa.
        billing.hoan_don(tenant_id)
    _ghi_lich_su(don_id, f"user:{user_id}",
                 f"ĐỐI SOÁT TAY — NGƯỜI kết luận '{ket_luan}'"
                 + (f", mã vận đơn {ma_van_don}" if ket_luan == "da_vao" else "")
                 + (f". Ghi chú: {ghi_chu}" if ghi_chu else ""))
    csdl.audit("don_doi_soat_tay", f"don:{don_id}", f"{ket_luan}|{ghi_chu}",
               tenant_id=tenant_id, user_id=user_id)
    return {"ket_luan": ket_luan, "nguon": "nguoi", "don": dict(lay_don(tenant_id, don_id))}


def don_can_doi_soat(tenant_id, gioi_han=200):
    """Danh sách đơn đang treo "không rõ kết quả" — màn vận hành phải thấy được, không để trôi."""
    ds = csdl.nhieu("SELECT * FROM don_hang WHERE tenant_id=? AND can_doi_soat_ket_qua=1"
                    " ORDER BY cap_nhat_luc LIMIT ?", (tenant_id, int(gioi_han)))
    return [dict(x) for x in ds]


def huy_don(tenant_id, user_id, don_id):
    _can_quyen(tenant_id, user_id, "tenant.don.duyet")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] == "huy":
        return dict(don)
    kiem_chuyen(don["trang_thai"], "huy")
    if don["trang_thai"] == "dang_gui" and don["can_doi_soat_ket_qua"]:
        # Hủy khi chưa biết hãng có đơn hay không = có thể bỏ lại một vận đơn sống ở hãng.
        raise LoiNghiepVu("lượt gửi trước chưa rõ kết quả — đối soát trước khi hủy, nếu không có"
                          " nguy cơ bỏ lại vận đơn sống ở hãng", 409)
    if don["trang_thai"] == "da_gui":
        ad, _ = _adapter_cua_account(tenant_id, don["carrier_account_id"])
        if not ad.capability("cancelOrder"):
            raise LoiNghiepVu(f"hãng {ad.ten_hang} không hỗ trợ hủy qua API")
        kq = ad.cancelOrder(don["ma_van_don"])
        if not kq.ok:
            raise LoiNghiepVu(f"hãng không hủy được: {kq.loi}", 502)
        _ghi_lich_su(don_id, f"user:{user_id}", f"hãng xác nhận hủy vận đơn {don['ma_van_don']}")
    csdl.ghi("UPDATE don_hang SET trang_thai='huy', cap_nhat_luc=? WHERE id=? AND tenant_id=?",
             (csdl.bay_gio(), don_id, tenant_id))
    _ghi_lich_su(don_id, f"user:{user_id}", "hủy đơn")
    return dict(lay_don(tenant_id, don_id))


def ap_trang_thai_giao(tenant_id, don_id, loai, nguon):
    """Webhook/polling gọi: cập nhật TRỤC GIAO VẬN với rank guard. Trả (ap_dung, ly_do).

    G04-L2 (AG-00 vá 15/10): `tenant_id` nay là tham số BẮT BUỘC và đứng ĐẦU. Bản cũ không
    nhận nó, chỉ dựa vào lời cam kết "người gọi đã giải quyết đơn theo tenant rồi" — một lời
    cam kết không có gì canh. Thêm một người gọi thứ ba quên bước ấy thì hàm này vui vẻ ghi
    chéo tenant và KHÔNG báo lỗi nào. Đưa tenant_id vào chữ ký là biến lời cam kết thành thứ
    trình biên dịch bắt được: gọi thiếu là `TypeError` ngay, không phải hỏng im lặng (§12.2).
    Rủi ro cấu trúc này từng ghi ở QA Q-10 (`thu_qa_soat.py`) — nay đóng.
    """
    import cau_hinh
    hang_moi = cau_hinh.HANG_TRANG_THAI_GIAO.get(loai)
    if hang_moi is None:
        return 0, f"loại sự kiện lạ: {loai}"
    with csdl.khoa_ghi:
        don = csdl.mot("SELECT * FROM don_hang WHERE id=? AND tenant_id=?", (don_id, tenant_id))
        if don is None:
            return 0, "không có đơn này trong doanh nghiệp đó"
        if don["hang_trang_thai_giao"] >= hang_moi:
            _ghi_lich_su(don_id, nguon,
                         f"sự kiện {loai} đến muộn/out-of-order — KHÔNG áp"
                         f" (giữ {don['trang_thai_giao']})")
            return 0, "out-of-order"
        csdl.ghi("UPDATE don_hang SET trang_thai_giao=?, hang_trang_thai_giao=?, cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=?",
                 (loai, hang_moi, csdl.bay_gio(), don_id, tenant_id))
    _ghi_lich_su(don_id, nguon, f"trạng thái giao → {loai}")
    return 1, ""


# ============================================================================
# O01 — ORDER ITEM: nhiều mặt hàng trên một đơn (bảng don_mat_hang)
# ============================================================================

BANG_MAT_HANG = "don_mat_hang"
TRUONG_MAT_HANG = ("ten", "ma_sku", "so_luong", "don_gia", "khoi_luong_gram", "ghi_chu")


def _doi_bang_mat_hang():
    if not co_bang(BANG_MAT_HANG):
        raise LoiNghiepVu(
            f"CSDL chưa có bảng {BANG_MAT_HANG} — cần chạy migration G04 (DDL ở"
            " docs/G04_ORDER_SERVICE.md) trước khi dùng nhiều mặt hàng trên một đơn", 501)


def co_tinh_nang_mat_hang():
    """Giao diện hỏi trước khi hiện ngăn mặt hàng — đỡ phải thử rồi nhận 501."""
    return co_bang(BANG_MAT_HANG)


def lay_mat_hang(tenant_id, don_id):
    """Danh sách mặt hàng của đơn. CSDL chưa migrate → trả [] (đơn một mặt hàng vẫn chạy)."""
    if not co_bang(BANG_MAT_HANG):
        return []
    ds = csdl.nhieu(f"SELECT * FROM {BANG_MAT_HANG} WHERE don_id=? AND tenant_id=? ORDER BY stt, id",
                    (don_id, tenant_id))
    return [dict(x) for x in ds]


def _kiem_mat_hang(cac_mon):
    if not isinstance(cac_mon, (list, tuple)):
        raise LoiNghiepVu("mat_hang phải là danh sách")
    if len(cac_mon) > 200:
        raise LoiNghiepVu("tối đa 200 mặt hàng trên một đơn")
    ra = []
    for i, m in enumerate(cac_mon, 1):
        if not isinstance(m, dict):
            raise LoiNghiepVu(f"mặt hàng {i} không phải đối tượng")
        ten = str(m.get("ten", "") or "").strip()
        if not ten:
            raise LoiNghiepVu(f"mặt hàng {i} thiếu tên")
        so_luong = _so_nguyen_tien(m.get("so_luong", 1) or 1, f"mặt hàng {i}: so_luong")
        if so_luong <= 0:
            raise LoiNghiepVu(f"mặt hàng {i}: so_luong phải > 0")
        don_gia = _so_nguyen_tien(m.get("don_gia", 0), f"mặt hàng {i}: don_gia")
        if don_gia < 0:
            raise LoiNghiepVu(f"mặt hàng {i}: don_gia không được âm")
        klg = _so_nguyen_tien(m.get("khoi_luong_gram", 0), f"mặt hàng {i}: khoi_luong_gram")
        if klg < 0:
            raise LoiNghiepVu(f"mặt hàng {i}: khoi_luong_gram không được âm")
        ra.append({"stt": i, "ten": ten, "ma_sku": str(m.get("ma_sku", "") or "").strip(),
                   "so_luong": so_luong, "don_gia": don_gia, "khoi_luong_gram": klg,
                   "ghi_chu": str(m.get("ghi_chu", "") or "")})
    return ra


def luu_mat_hang(tenant_id, user_id, don_id, cac_mon, kiem_quyen=True):
    """Thay TOÀN BỘ danh sách mặt hàng của đơn (không sửa lẻ — tránh lệch tổng).

    Lưu xong thì ĐỒNG BỘ lại `khoi_luong_gram` và `gia_tri_khai` của đơn bằng TỔNG từ mặt hàng,
    vì hai trường đó là thứ adapter gửi lên hãng. Để lệch nhau là để hai con số nói hai chuyện
    khác nhau về cùng một đơn — đúng họ hỏng "hai thứ đáng lẽ giống nhau".
    """
    if kiem_quyen:
        _can_quyen(tenant_id, user_id, "tenant.don.ghi")
    _doi_bang_mat_hang()
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] not in ("nhap", "da_duyet"):
        raise LoiNghiepVu(f"đơn ở '{don['trang_thai']}' — chỉ sửa mặt hàng trước khi gửi hãng", 409)
    mon = _kiem_mat_hang(cac_mon)
    tong_kl = sum(m["so_luong"] * m["khoi_luong_gram"] for m in mon)
    tong_gt = sum(m["so_luong"] * m["don_gia"] for m in mon)
    with csdl.khoa_ghi:
        csdl.ghi(f"DELETE FROM {BANG_MAT_HANG} WHERE don_id=? AND tenant_id=?",
                 (don_id, tenant_id))
        for m in mon:
            csdl.ghi(
                f"INSERT INTO {BANG_MAT_HANG} (tenant_id, don_id, stt, ten, ma_sku, so_luong,"
                " don_gia, khoi_luong_gram, ghi_chu, tao_luc) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (tenant_id, don_id, m["stt"], m["ten"], m["ma_sku"], m["so_luong"],
                 m["don_gia"], m["khoi_luong_gram"], m["ghi_chu"], csdl.bay_gio()))
        if mon and tong_kl > 0:
            csdl.ghi("UPDATE don_hang SET khoi_luong_gram=?, gia_tri_khai=?, cap_nhat_luc=?"
                     " WHERE id=? AND tenant_id=?",
                     (tong_kl, tong_gt, csdl.bay_gio(), don_id, tenant_id))
    _ghi_lich_su(don_id, f"user:{user_id}",
                 f"đặt lại danh sách mặt hàng: {len(mon)} dòng, tổng {tong_kl}g,"
                 f" tổng giá trị {tong_gt} đồng")
    return {"mat_hang": lay_mat_hang(tenant_id, don_id),
            "tong_khoi_luong_gram": tong_kl, "tong_gia_tri_dong": tong_gt,
            "don": dict(lay_don(tenant_id, don_id))}


# ============================================================================
# O03 — TÌM KIẾM NÂNG CAO
# ============================================================================

# Cột được phép SẮP XẾP theo. Đây là danh sách TRẮNG bắt buộc: tên cột không thể tham số hóa
# bằng `?`, nên nhận tên tự do là mở cửa SQL injection. Quên một cột ở đây = mất một kiểu sắp
# xếp (thấy ngay); dùng danh sách đen = một tên lạ lọt qua thành câu SQL do người ngoài viết.
SAP_XEP_DUOC = {
    "moi_nhat": "id DESC", "cu_nhat": "id ASC",
    "cap_nhat_moi": "cap_nhat_luc DESC", "cap_nhat_cu": "cap_nhat_luc ASC",
    "cod_cao": "cod DESC", "cod_thap": "cod ASC",
    "nang_nhat": "khoi_luong_gram DESC",
}
GIOI_HAN_TOI_DA = 500


def tim_don(tenant_id, loc=None):
    """Tìm đơn theo nhiều điều kiện. MỌI câu đều kèm tenant_id — không có đường nào bỏ qua.

    `loc` nhận: trang_thai / trang_thai_giao (chuỗi hoặc danh sách), trang_thai_mo_rong,
    carrier_account_id, khach_hang_id, can_doi_soat_ket_qua, ma_don, ma_van_don,
    external_reference, q (tìm mờ), tu_ngay / den_ngay (theo tao_luc, dạng YYYY-MM-DD),
    cod_tu / cod_den (đồng), sap_xep, gioi_han, lech.
    Trả {"don": [...], "tong": n, "gioi_han": …, "lech": …, "loc_bo_qua": [...]}.

    `loc_bo_qua` nói thẳng điều kiện nào đã bị BỎ vì CSDL chưa có cột — im lặng bỏ một điều
    kiện lọc là trả về nhiều hơn người hỏi tưởng, và không có gì báo (§12.2).
    """
    loc = dict(loc or {})
    dk, tsq, bo_qua = ["tenant_id=?"], [tenant_id], []

    def nhieu_gia_tri(ten, cot):
        gt = loc.get(ten)
        if gt in (None, "", []):
            return
        ds = gt if isinstance(gt, (list, tuple)) else [gt]
        ds = [str(x) for x in ds if str(x).strip()]
        if not ds:
            return
        dk.append(f"{cot} IN (" + ",".join("?" * len(ds)) + ")")
        tsq.extend(ds)

    nhieu_gia_tri("trang_thai", "trang_thai")
    nhieu_gia_tri("trang_thai_giao", "trang_thai_giao")
    for ten, cot in (("carrier_account_id", "carrier_account_id"),
                     ("khach_hang_id", "khach_hang_id")):
        if loc.get(ten) not in (None, ""):
            dk.append(f"{cot}=?")
            tsq.append(int(loc[ten]))
    if loc.get("can_doi_soat_ket_qua") not in (None, ""):
        dk.append("can_doi_soat_ket_qua=?")
        tsq.append(1 if loc["can_doi_soat_ket_qua"] in (1, "1", True, "true") else 0)
    for ten in ("ma_don", "ma_van_don", "external_reference"):
        if loc.get(ten) in (None, ""):
            continue
        if ten == "external_reference" and not co_cot("don_hang", "external_reference"):
            bo_qua.append("external_reference (CSDL chưa migrate)")
            continue
        dk.append(f"{ten}=?")
        tsq.append(str(loc[ten]))
    if str(loc.get("q", "") or "").strip():
        q = f"%{str(loc['q']).strip()}%"
        dk.append("(ma_don LIKE ? OR ma_van_don LIKE ? OR nguoi_nhan_ten LIKE ?"
                  " OR nguoi_nhan_sdt LIKE ? OR hang_hoa LIKE ?)")
        tsq += [q] * 5
    for ten, dau in (("tu_ngay", ">="), ("den_ngay", "<=")):
        v = str(loc.get(ten, "") or "").strip()
        if not v:
            continue
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise LoiNghiepVu(f"{ten} phải dạng YYYY-MM-DD")
        # tao_luc dạng "YYYY-MM-DD HH:MM:SS+0700" → so 10 ký tự đầu là so theo NGÀY giờ VN.
        dk.append(f"substr(tao_luc,1,10) {dau} ?")
        tsq.append(v)
    for ten, dau in (("cod_tu", ">="), ("cod_den", "<=")):
        if loc.get(ten) in (None, ""):
            continue
        dk.append(f"cod {dau} ?")
        tsq.append(_so_nguyen_tien(loc[ten], ten))

    thu_tu = SAP_XEP_DUOC.get(str(loc.get("sap_xep") or "moi_nhat"))
    if thu_tu is None:
        raise LoiNghiepVu(f"sap_xep phải là một trong {sorted(SAP_XEP_DUOC)}")
    gioi_han = max(1, min(int(loc.get("gioi_han") or 100), GIOI_HAN_TOI_DA))
    lech = max(0, int(loc.get("lech") or 0))
    dieu_kien = " AND ".join(dk)
    tong = csdl.mot(f"SELECT COUNT(*) c FROM don_hang WHERE {dieu_kien}", tsq)["c"]
    ds = csdl.nhieu(f"SELECT * FROM don_hang WHERE {dieu_kien} ORDER BY {thu_tu} LIMIT ? OFFSET ?",
                    tsq + [gioi_han, lech])
    ra = [dict(x) for x in ds]
    for x in ra:
        x["trang_thai_mo_rong"] = trang_thai_mo_rong(x)
    # Lọc theo tên vòng đời mở rộng làm SAU, trong Python: nó là giá trị SUY RA từ hai trục
    # (có điều kiện gọi cả hàm kiểm dữ liệu), không phải một cột để đưa vào WHERE.
    if loc.get("trang_thai_mo_rong"):
        can = loc["trang_thai_mo_rong"]
        can = MO_RONG_DONG_NGHIA.get(can, can)
        ra = [x for x in ra if x["trang_thai_mo_rong"] == can]
    return {"don": ra, "tong": tong, "gioi_han": gioi_han, "lech": lech,
            "loc_bo_qua": bo_qua,
            "ghi_chu_tong": "`tong` đếm theo điều kiện SQL, CHƯA trừ phần lọc"
                            " trang_thai_mo_rong làm sau ở tầng Python"
                            if loc.get("trang_thai_mo_rong") else ""}


# ============================================================================
# O03 — DÒNG THỜI GIAN HÀNH TRÌNH + SIÊU DỮ LIỆU NHÃN VẬN ĐƠN
# ============================================================================

def dong_thoi_gian(tenant_id, don_id):
    """Hành trình đơn: trộn lịch sử nghiệp vụ và sự kiện giao vận, theo thứ tự thời gian.

    Dữ liệu lấy TỪ `don_lich_su` — nguồn đã có sẵn và đã ghi mọi lần đổi trạng thái. KHÔNG gọi
    hãng ở đây: một màn xem hành trình không được phụ thuộc mạng của hãng.
    """
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    import cau_hinh
    ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don_id,))
    moc = []
    for r in ls:
        d = dict(r)
        noi_dung = d["noi_dung"]
        m = re.match(r"trạng thái giao → (\w+)$", noi_dung)
        moc.append({
            "luc": d["luc"], "nguon": d["nguon"], "noi_dung": noi_dung,
            "truc": "giao_van" if m else "nghiep_vu",
            "trang_thai_giao": m.group(1) if m else None,
            "hang": cau_hinh.HANG_TRANG_THAI_GIAO.get(m.group(1)) if m else None,
        })
    return {
        "don_id": don_id, "ma_don": don["ma_don"], "ma_van_don": don["ma_van_don"],
        "trang_thai": don["trang_thai"], "trang_thai_giao": don["trang_thai_giao"],
        "hang_trang_thai_giao": don["hang_trang_thai_giao"],
        "trang_thai_mo_rong": trang_thai_mo_rong(don),
        "can_doi_soat_ket_qua": don["can_doi_soat_ket_qua"],
        "moc": moc, "so_moc": len(moc),
        "nguon_du_lieu": "don_lich_su (CSDL nội bộ) — KHÔNG gọi hãng",
    }


def sieu_du_lieu_nhan_van_don(tenant_id, user_id, don_id):
    """Siêu dữ liệu NHÃN vận đơn (shipping label metadata) — KHÔNG trả nội dung nhãn.

    Cố ý chỉ trả siêu dữ liệu: nội dung nhãn là tệp nhị phân của hãng, nhét vào JSON là phình
    log và phình CSDL. Và ở môi trường mock thì "nhãn" chỉ là chuỗi giả — trả nó ra như nhãn
    thật là để người tưởng in được. Nên có cờ `la_mock` và `nhan_that=False`.
    """
    _can_quyen(tenant_id, user_id, "tenant.don.xem")
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] != "da_gui" or not don["ma_van_don"]:
        raise LoiNghiepVu("chưa có mã vận đơn — nhãn chỉ có sau khi hãng xác nhận đơn", 409)
    ad, tk = _adapter_cua_account(tenant_id, don["carrier_account_id"])
    ho_tro = ad.capability("getShippingLabel")
    ra = {"don_id": don_id, "ma_don": don["ma_don"], "ma_van_don": don["ma_van_don"],
          "hang": ad.ma_hang, "ten_hang": ad.ten_hang, "moi_truong": tk["moi_truong"],
          "la_mock": tk["moi_truong"] == "mock", "ho_tro_nhan": bool(ho_tro),
          "nhan_that": False, "dinh_dang": None, "do_lon_byte": None, "canh_bao": []}
    if not ho_tro:
        ra["canh_bao"].append(f"hãng {ad.ten_hang} không hỗ trợ getShippingLabel")
        return ra
    kq = ad.getShippingLabel(don["ma_van_don"])
    if not kq.ok:
        ra["canh_bao"].append(f"hãng không trả nhãn: {kq.loi}")
        return ra
    nhan = (kq.tho or {}).get("label")
    ra["dinh_dang"] = "pdf" if str(nhan or "").lower().endswith("pdf") or \
                              str(nhan or "").startswith("MOCK-PDF") else "khong_ro"
    ra["do_lon_byte"] = len(str(nhan).encode()) if nhan is not None else None
    ra["nhan_that"] = tk["moi_truong"] != "mock"
    if tk["moi_truong"] == "mock":
        ra["canh_bao"].append("nhãn này là MOCK — không in được, không phải nhãn hãng")
    _ghi_lich_su(don_id, f"user:{user_id}", f"lấy siêu dữ liệu nhãn vận đơn ({tk['moi_truong']})")
    return ra


def lay_don_day_du(tenant_id, don_id):
    """Một lượt đọc gom đủ thứ màn chi tiết cần: đơn + mặt hàng + hành trình + kết quả kiểm."""
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    d = dict(don)
    d["trang_thai_mo_rong"] = trang_thai_mo_rong(d)
    return {"don": d, "mat_hang": lay_mat_hang(tenant_id, don_id),
            "hanh_trinh": dong_thoi_gian(tenant_id, don_id),
            "kiem": kiem_don(tenant_id, d=d),
            "chuyen_duoc_sang": sorted(CHUYEN_DUOC.get(d["trang_thai"], set())),
            "co_tinh_nang_mat_hang": co_tinh_nang_mat_hang()}
