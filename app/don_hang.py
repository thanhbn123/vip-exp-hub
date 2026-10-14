# G07 — Order Service: vòng đời đơn, idempotency, gửi hãng qua adapter, lịch sử.
# Luật cứng: KHÔNG đánh dấu da_gui nếu hãng chưa xác nhận; timeout → dang_gui + cờ kiểm lại.
import json
import re
import sqlite3

import adapter
import adapter_jt   # noqa: F401 — đăng ký adapter
import adapter_vtp  # noqa: F401
import bao_mat
import billing
import csdl


class LoiNghiepVu(Exception):
    def __init__(self, msg, ma=400):
        super().__init__(msg)
        self.ma = ma


def _kiem_du_lieu(d):
    loi = []
    for t in ("nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi",
              "nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa"):
        if not str(d.get(t, "")).strip():
            loi.append(f"thiếu {t}")
    for t in ("nguoi_gui_sdt", "nguoi_nhan_sdt"):
        v = str(d.get(t, "")).replace(" ", "").replace(".", "")
        if v and not re.fullmatch(r"0\d{9}", v):
            loi.append(f"{t} phải 10 số bắt đầu bằng 0")
    try:
        if int(d.get("khoi_luong_gram", 0)) <= 0:
            loi.append("khoi_luong_gram phải > 0")
    except (ValueError, TypeError):
        loi.append("khoi_luong_gram không phải số")
    for t in ("cod", "gia_tri_khai"):
        try:
            if int(d.get(t, 0) or 0) < 0:
                loi.append(f"{t} không được âm")
        except (ValueError, TypeError):
            loi.append(f"{t} không phải số")
    return loi


def _sinh_ma_don(tenant_id):
    so = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (tenant_id,))["c"]
    return f"T{tenant_id}-{so + 1:06d}"


def _ghi_lich_su(don_id, nguon, noi_dung):
    csdl.ghi("INSERT INTO don_lich_su (don_id, luc, nguon, noi_dung) VALUES (?,?,?,?)",
             (don_id, csdl.bay_gio(), nguon, noi_dung))


def lay_don(tenant_id, don_id):
    """Luôn kèm điều kiện tenant — resource ownership."""
    return csdl.mot("SELECT * FROM don_hang WHERE id=? AND tenant_id=?", (don_id, tenant_id))


def tao_don(tenant_id, user_id, d, idem_key=None):
    """Tạo đơn nháp. idem_key trùng → trả đơn cũ, không tạo mới (UNIQUE CSDL)."""
    loi = _kiem_du_lieu(d)
    if loi:
        raise LoiNghiepVu("; ".join(loi))
    if d.get("khach_hang_id"):
        kh = csdl.mot("SELECT id FROM khach_hang WHERE id=? AND tenant_id=?", (d["khach_hang_id"], tenant_id))
        if not kh:
            raise LoiNghiepVu("khách hàng không thuộc doanh nghiệp này", 404)
    with csdl.khoa_ghi:
        if idem_key:
            cu = csdl.mot("SELECT * FROM don_hang WHERE tenant_id=? AND idem_key=?", (tenant_id, idem_key))
            if cu:
                return dict(cu), True
        try:
            con = csdl.ghi(
                "INSERT INTO don_hang (tenant_id, ma_don, idem_key, khach_hang_id,"
                " nguoi_gui_ten, nguoi_gui_sdt, nguoi_gui_dia_chi,"
                " nguoi_nhan_ten, nguoi_nhan_sdt, nguoi_nhan_dia_chi,"
                " hang_hoa, khoi_luong_gram, cod, gia_tri_khai, ghi_chu, nguoi_tao, tao_luc, cap_nhat_luc)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (tenant_id, _sinh_ma_don(tenant_id), idem_key, d.get("khach_hang_id"),
                 d["nguoi_gui_ten"].strip(), d["nguoi_gui_sdt"].strip(), d["nguoi_gui_dia_chi"].strip(),
                 d["nguoi_nhan_ten"].strip(), d["nguoi_nhan_sdt"].strip(), d["nguoi_nhan_dia_chi"].strip(),
                 d["hang_hoa"].strip(), int(d["khoi_luong_gram"]), int(d.get("cod", 0) or 0),
                 int(d.get("gia_tri_khai", 0) or 0), d.get("ghi_chu", ""), user_id,
                 csdl.bay_gio(), csdl.bay_gio()))
        except sqlite3.IntegrityError:
            cu = csdl.mot("SELECT * FROM don_hang WHERE tenant_id=? AND idem_key=?", (tenant_id, idem_key))
            if cu:
                return dict(cu), True
            raise
    don_id = con.lastrowid
    _ghi_lich_su(don_id, f"user:{user_id}", "tạo đơn nháp")
    return dict(lay_don(tenant_id, don_id)), False


def sua_don(tenant_id, user_id, don_id, d):
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] not in ("nhap", "da_duyet"):
        raise LoiNghiepVu(f"đơn ở trạng thái '{don['trang_thai']}' — chỉ sửa được trước khi gửi hãng")
    gop = dict(don)
    gop.update({k: v for k, v in d.items() if k in (
        "nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi", "nguoi_nhan_ten", "nguoi_nhan_sdt",
        "nguoi_nhan_dia_chi", "hang_hoa", "khoi_luong_gram", "cod", "gia_tri_khai", "ghi_chu")})
    loi = _kiem_du_lieu(gop)
    if loi:
        raise LoiNghiepVu("; ".join(loi))
    csdl.ghi(
        "UPDATE don_hang SET nguoi_gui_ten=?, nguoi_gui_sdt=?, nguoi_gui_dia_chi=?,"
        " nguoi_nhan_ten=?, nguoi_nhan_sdt=?, nguoi_nhan_dia_chi=?, hang_hoa=?, khoi_luong_gram=?,"
        " cod=?, gia_tri_khai=?, ghi_chu=?, trang_thai='nhap', cap_nhat_luc=? WHERE id=? AND tenant_id=?",
        (gop["nguoi_gui_ten"], gop["nguoi_gui_sdt"], gop["nguoi_gui_dia_chi"],
         gop["nguoi_nhan_ten"], gop["nguoi_nhan_sdt"], gop["nguoi_nhan_dia_chi"],
         gop["hang_hoa"], int(gop["khoi_luong_gram"]), int(gop["cod"] or 0),
         int(gop["gia_tri_khai"] or 0), gop.get("ghi_chu", ""), csdl.bay_gio(), don_id, tenant_id))
    _ghi_lich_su(don_id, f"user:{user_id}", "sửa đơn (về trạng thái nháp)")
    return dict(lay_don(tenant_id, don_id))


def duyet_don(tenant_id, user_id, don_id):
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] != "nhap":
        raise LoiNghiepVu(f"chỉ duyệt được đơn nháp (hiện: {don['trang_thai']})")
    csdl.ghi("UPDATE don_hang SET trang_thai='da_duyet', cap_nhat_luc=? WHERE id=? AND tenant_id=?",
             (csdl.bay_gio(), don_id, tenant_id))
    _ghi_lich_su(don_id, f"user:{user_id}", "duyệt đơn")
    return dict(lay_don(tenant_id, don_id))


def _adapter_cua_account(tenant_id, account_id):
    tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=? AND tenant_id=? AND kich_hoat=1",
                  (account_id, tenant_id))
    if not tk:
        raise LoiNghiepVu("tài khoản hãng không tồn tại hoặc không thuộc doanh nghiệp này", 404)
    cred = bao_mat.giai_ma_cred(tk["credentials_ma_hoa"], tk["tenant_id"], tk["hang"])
    return adapter.tao_adapter(tk["hang"], cred, tk["moi_truong"]), tk


def gui_don(tenant_id, user_id, don_id, carrier_account_id):
    """Gửi đơn đã duyệt sang hãng (qua adapter). Chỉ da_gui khi hãng xác nhận."""
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] == "da_gui":
        return dict(don)  # đã gửi rồi — idempotent, không gửi lại
    if don["trang_thai"] not in ("da_duyet", "dang_gui"):
        raise LoiNghiepVu(f"đơn phải được duyệt trước khi gửi (hiện: {don['trang_thai']})")
    ad, tk = _adapter_cua_account(tenant_id, carrier_account_id)
    if not ad.capability("createOrder"):
        raise LoiNghiepVu(f"hãng {ad.ten_hang} không hỗ trợ tạo đơn qua API")
    billing.kiem_va_tang_don(tenant_id)
    csdl.ghi("UPDATE don_hang SET trang_thai='dang_gui', carrier_account_id=?, cap_nhat_luc=? WHERE id=? AND tenant_id=?",
             (carrier_account_id, csdl.bay_gio(), don_id, tenant_id))
    kq = ad.createOrder(dict(don))
    if kq.ok:
        phi = ad.getShippingFee(dict(don)) if ad.capability("getShippingFee") else None
        csdl.ghi("UPDATE don_hang SET trang_thai='da_gui', ma_van_don=?, phi_van_chuyen=?,"
                 " can_doi_soat_ket_qua=0, trang_thai_giao='cho_lay', hang_trang_thai_giao=1, cap_nhat_luc=?"
                 " WHERE id=? AND tenant_id=?",
                 (kq.ma_van_don, phi.phi if (phi and phi.ok) else None, csdl.bay_gio(), don_id, tenant_id))
        _ghi_lich_su(don_id, f"user:{user_id}", f"hãng {ad.ten_hang} ({tk['moi_truong']}) xác nhận, mã vận đơn {kq.ma_van_don}")
    elif kq.timeout:
        # KHÔNG biết kết quả — giữ dang_gui, bật cờ phải kiểm lại; KHÔNG nhận là thành công/thất bại.
        csdl.ghi("UPDATE don_hang SET can_doi_soat_ket_qua=1, cap_nhat_luc=? WHERE id=? AND tenant_id=?",
                 (csdl.bay_gio(), don_id, tenant_id))
        _ghi_lich_su(don_id, f"user:{user_id}", f"gửi {ad.ten_hang} TIMEOUT — chưa rõ kết quả, cần getOrder kiểm lại")
    else:
        csdl.ghi("UPDATE don_hang SET trang_thai='da_duyet', cap_nhat_luc=? WHERE id=? AND tenant_id=?",
                 (csdl.bay_gio(), don_id, tenant_id))
        _ghi_lich_su(don_id, f"user:{user_id}", f"hãng {ad.ten_hang} từ chối: {kq.loi}")
        raise LoiNghiepVu(f"hãng từ chối: {kq.loi}", 502)
    return dict(lay_don(tenant_id, don_id))


def huy_don(tenant_id, user_id, don_id):
    don = lay_don(tenant_id, don_id)
    if not don:
        raise LoiNghiepVu("không có đơn này", 404)
    if don["trang_thai"] == "huy":
        return dict(don)
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


def ap_trang_thai_giao(don_id, loai, nguon):
    """Webhook gọi: cập nhật trạng thái giao với rank guard. Trả (ap_dung, ly_do)."""
    import cau_hinh
    hang_moi = cau_hinh.HANG_TRANG_THAI_GIAO.get(loai)
    if hang_moi is None:
        return 0, f"loại sự kiện lạ: {loai}"
    with csdl.khoa_ghi:
        don = csdl.mot("SELECT * FROM don_hang WHERE id=?", (don_id,))
        if don["hang_trang_thai_giao"] >= hang_moi:
            _ghi_lich_su(don_id, nguon, f"sự kiện {loai} đến muộn/out-of-order — KHÔNG áp (giữ {don['trang_thai_giao']})")
            return 0, "out-of-order"
        csdl.ghi("UPDATE don_hang SET trang_thai_giao=?, hang_trang_thai_giao=?, cap_nhat_luc=? WHERE id=?",
                 (loai, hang_moi, csdl.bay_gio(), don_id))
    _ghi_lich_su(don_id, nguon, f"trạng thái giao → {loai}")
    return 1, ""
