# G03/G06 — Tracking polling fallback: lấy hành trình bằng cách HỎI hãng theo lịch, dùng khi hãng
# không đẩy webhook (hoặc webhook đang hỏng). Đi qua ĐÚNG đường cập nhật của webhook:
# normalize (qua trang_thai_hang.quyet_dinh) → resolve tenant+đơn → rank guard → audit.
# Không có đường tắt nào.
#
# Giới hạn thật đã đọc từ tài liệu: J&T tra hành trình tối đa 30 vận đơn mỗi lượt
# (open.jtexpress.vn/apiDoc/logistics/query). Bộ gom lô dưới đây tôn trọng con số đó theo từng hãng.
#
# KHÔNG tự chạy theo lịch. Phải có người gọi `chay_mot_luot()` hoặc bật `BatDauNen` — đúng luật
# "tự động hóa phải do người duyệt".
#
# Bổ sung đợt G06 (AG-03, W08):
#   - mã nhập nhằng của hãng đi qua `quyet_dinh()` y như webhook: KHÔNG tự chọn nghĩa, không
#     bao giờ áp trạng thái hoàn tất, đánh dấu cần soát;
#   - trần số lượt hỏi mỗi phút THEO TỪNG TENANT (một tenant nhiều đơn không ăn hết hạn mức
#     của tenant khác — cách ly tenant phải có cả ở tầng hạn mức, không chỉ ở tầng truy vấn);
#   - ngắt mạch theo hãng khi hãng lỗi liên tiếp, thay vì đập tiếp cho hết danh sách;
#   - vòng nền có khoảng cách tối thiểu, phải xin rõ mới chạy nhanh hơn.
import threading
import time

import adapter
import adapter_jt   # noqa: F401
import adapter_vtp  # noqa: F401
import bao_mat
import csdl
import don_hang
import trang_thai_hang as tth

# Trạng thái giao vận coi là CÒN ĐANG CHẠY — chỉ hỏi hãng về những đơn này.
DANG_CHAY = ("cho_lay", "lay_hang", "dang_giao")
MAC_DINH_MOI_LUOT = 20

# Trần số lượt gọi hãng mỗi phút, tính RIÊNG cho từng tenant. Đặt rộng để lượt chạy tay của
# người vận hành không bị chặn oan; nó tồn tại để chặn ca vòng lặp/nhiều phiên gọi dồn.
GIOI_HAN_HOI_MOI_PHUT = 600
# Hãng lỗi liên tiếp quá ngưỡng này trong MỘT lượt thì ngắt mạch hãng đó, không hỏi tiếp.
NGUONG_NGAT_MACH = 5
# Khoảng cách tối thiểu giữa hai vòng nền. Muốn nhanh hơn phải truyền cho_phep_nhanh=True
# (dùng trong bộ thử), chứ không im lặng chạy 20 lượt/giây lên API hãng.
MOI_GIAY_TOI_THIEU = 30

_khoa_han_muc = threading.Lock()
_dau_vet_hoi = {}   # tenant_id -> [mốc thời gian các lượt hỏi trong 60 giây gần nhất]


def so_van_don_moi_luot(ma_hang):
    """Giới hạn gom lô theo tài liệu từng hãng; không biết thì dùng mức dè dặt."""
    mod = {"jt": getattr(adapter_jt, "SO_VAN_DON_MOI_LUOT", None)}.get(ma_hang)
    return mod or MAC_DINH_MOI_LUOT


def _con_han_muc(tenant_id, bay_gio=None):
    """Token bucket trượt 60 giây, RIÊNG từng tenant. Trả True và ghi nhận một lượt nếu còn."""
    t = bay_gio if bay_gio is not None else time.monotonic()
    with _khoa_han_muc:
        ds = [x for x in _dau_vet_hoi.get(tenant_id, []) if t - x < 60.0]
        if len(ds) >= GIOI_HAN_HOI_MOI_PHUT:
            _dau_vet_hoi[tenant_id] = ds
            return False
        ds.append(t)
        _dau_vet_hoi[tenant_id] = ds
        return True


def xoa_han_muc(tenant_id=None):
    """Xóa dấu vết hạn mức (dùng khi vận hành muốn đặt lại, và trong bộ thử)."""
    with _khoa_han_muc:
        if tenant_id is None:
            _dau_vet_hoi.clear()
        else:
            _dau_vet_hoi.pop(tenant_id, None)


def don_can_hoi(tenant_id=None, gioi_han=500):
    """Đơn đã gửi hãng, có mã vận đơn, hành trình chưa kết thúc."""
    dk = ["d.trang_thai='da_gui'", "d.ma_van_don IS NOT NULL",
          "(d.trang_thai_giao IS NULL OR d.trang_thai_giao IN (%s))" % ",".join("?" * len(DANG_CHAY))]
    ts = list(DANG_CHAY)
    if tenant_id is not None:
        dk.append("d.tenant_id=?")
        ts.append(tenant_id)
    ts.append(gioi_han)
    return csdl.nhieu(
        "SELECT d.id, d.tenant_id, d.ma_van_don, d.carrier_account_id, c.hang, c.moi_truong,"
        " c.credentials_ma_hoa FROM don_hang d JOIN carrier_accounts c ON c.id=d.carrier_account_id"
        " WHERE " + " AND ".join(dk) + " AND c.kich_hoat=1 ORDER BY d.id LIMIT ?", ts)


def _gom_lo(ds, kich_thuoc):
    for i in range(0, len(ds), kich_thuoc):
        yield ds[i:i + kich_thuoc]


def chay_mot_luot(tenant_id=None, chi_hang_khong_webhook=False):
    """Hỏi hãng một lượt cho các đơn đang chạy. Trả thống kê.
    chi_hang_khong_webhook=True → chỉ polling những hãng KHÔNG hỗ trợ webhook (đúng nghĩa fallback)."""
    ds = don_can_hoi(tenant_id)
    theo_hang = {}
    for d in ds:
        theo_hang.setdefault(d["hang"], []).append(d)

    tk = {"da_hoi": 0, "doi_trang_thai": 0, "khong_doi": 0, "ma_la": 0, "loi": 0,
          "nhap_nhang": 0, "can_soat": 0, "qua_han_muc": 0, "ngat_mach": [], "bo_qua_hang": []}
    for ma_hang, nhom in theo_hang.items():
        lop = adapter._DANG_KY.get(ma_hang)
        if lop is None:
            tk["bo_qua_hang"].append(f"{ma_hang}: chưa có adapter")
            continue
        if not lop.CAPABILITIES.get("trackOrder"):
            tk["bo_qua_hang"].append(f"{ma_hang}: không hỗ trợ trackOrder")
            continue
        if chi_hang_khong_webhook and lop.CAPABILITIES.get("webhook"):
            tk["bo_qua_hang"].append(f"{ma_hang}: đã có webhook, không cần polling")
            continue
        loi_lien_tiep = 0
        for lo in _gom_lo(nhom, so_van_don_moi_luot(ma_hang)):
            if loi_lien_tiep >= NGUONG_NGAT_MACH:
                break
            for d in lo:
                if loi_lien_tiep >= NGUONG_NGAT_MACH:
                    tk["ngat_mach"].append(f"{ma_hang}: {loi_lien_tiep} lỗi liên tiếp — ngắt mạch")
                    csdl.audit("polling_ngat_mach", f"tenant:{d['tenant_id']}",
                               f"hãng {ma_hang} lỗi {loi_lien_tiep} lượt liên tiếp — dừng lượt này",
                               tenant_id=d["tenant_id"], ket_qua="that_bai")
                    break
                # Cách ly tenant ở TẦNG HẠN MỨC, không chỉ ở tầng truy vấn.
                if not _con_han_muc(d["tenant_id"]):
                    tk["qua_han_muc"] += 1
                    csdl.audit("polling_qua_han_muc", f"tenant:{d['tenant_id']}",
                               f"vượt {GIOI_HAN_HOI_MOI_PHUT} lượt/phút — hoãn đơn {d['id']}",
                               tenant_id=d["tenant_id"], ket_qua="tu_choi")
                    continue
                try:
                    cred = bao_mat.giai_ma_cred(d["credentials_ma_hoa"], d["tenant_id"], d["hang"])
                    ad = adapter.tao_adapter(ma_hang, cred, d["moi_truong"])
                    kq = ad.trackOrder(d["ma_van_don"])
                    tk["da_hoi"] += 1
                    if not kq.ok:
                        tk["loi"] += 1
                        loi_lien_tiep += 1
                        continue
                    loi_lien_tiep = 0
                    ma_tt = (kq.tho or {}).get("trang_thai")
                    # W06: cùng MỘT chỗ quyết định nghĩa như webhook — không có bảng thứ hai.
                    qd = tth.quyet_dinh(ma_hang, ma_tt, su_kien_goc={"nguon": "polling",
                                                                     "tho": kq.tho})
                    if not qd.biet_ma:
                        tk["ma_la"] += 1
                        csdl.audit("polling_ma_la", f"don:{d['id']}",
                                   f"hãng {ma_hang} trả mã lạ: {qd.ma_goc}",
                                   tenant_id=d["tenant_id"], ket_qua="that_bai")
                        continue
                    if qd.nhap_nhang and qd.trang_thai_ap is None:
                        tk["nhap_nhang"] += 1
                        tk["can_soat"] += 1
                        csdl.audit("polling_nhap_nhang", f"don:{d['id']}",
                                   f"hãng {ma_hang} mã {qd.ma_goc!r} nhập nhằng ({qd.nhan})"
                                   f" — KHÔNG đổi trạng thái. {qd.ghi_chu}",
                                   tenant_id=d["tenant_id"], ket_qua="that_bai")
                        continue
                    if qd.trang_thai_ap is None:
                        tk["khong_doi"] += 1
                        continue
                    # ĐI QUA ĐÚNG đường của webhook: rank guard + ghi lịch sử
                    ap, ly_do = don_hang.ap_trang_thai_giao(d["id"], qd.trang_thai_ap, "polling")
                    if ap:
                        tk["doi_trang_thai"] += 1
                        csdl.audit("polling_cap_nhat", f"don:{d['id']}",
                                   f"{ma_hang} {qd.ma_goc} → {qd.trang_thai_ap}"
                                   f" (tin_cay={qd.do_tin_cay})", tenant_id=d["tenant_id"])
                    else:
                        tk["khong_doi"] += 1
                except Exception as e:
                    tk["loi"] += 1
                    loi_lien_tiep += 1
                    csdl.audit("polling_loi", f"don:{d['id']}", f"{type(e).__name__}: {e}",
                               tenant_id=d["tenant_id"], ket_qua="that_bai")
    return tk


class BatDauNen:
    """Chạy polling định kỳ trong luồng nền. CHỈ bật khi người dùng/Owner yêu cầu.

    `moi_giay` nhỏ hơn MOI_GIAY_TOI_THIEU chỉ có hiệu lực khi `cho_phep_nhanh=True` — để không ai
    lỡ tay đặt 0.05 giây rồi nã API hãng 20 lượt/giây. `moi_giay_thuc` nói rõ con số ĐANG dùng.
    """
    def __init__(self, moi_giay=300, chi_hang_khong_webhook=True, cho_phep_nhanh=False):
        self.moi_giay = moi_giay
        self.cho_phep_nhanh = cho_phep_nhanh
        self.moi_giay_thuc = moi_giay if cho_phep_nhanh else max(moi_giay, MOI_GIAY_TOI_THIEU)
        self.chi_hang_khong_webhook = chi_hang_khong_webhook
        self._dung = threading.Event()
        self._luong = None

    def bat(self):
        if self._luong and self._luong.is_alive():
            return
        self._dung.clear()
        self._luong = threading.Thread(target=self._vong, name="hub-polling", daemon=True)
        self._luong.start()

    def _vong(self):
        while not self._dung.wait(self.moi_giay_thuc):
            try:
                chay_mot_luot(chi_hang_khong_webhook=self.chi_hang_khong_webhook)
            except Exception as e:
                csdl.audit("polling_vong_loi", "he_thong:1", f"{type(e).__name__}: {e}",
                           ket_qua="that_bai")

    def tat(self):
        self._dung.set()
