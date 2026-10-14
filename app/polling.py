# G03 — Tracking polling fallback: lấy hành trình bằng cách HỎI hãng theo lịch, dùng khi hãng
# không đẩy webhook (hoặc webhook đang hỏng). Đi qua ĐÚNG đường cập nhật của webhook:
# normalize → resolve tenant+đơn → rank guard → audit. Không có đường tắt nào.
#
# Giới hạn thật đã đọc từ tài liệu: J&T tra hành trình tối đa 30 vận đơn mỗi lượt
# (open.jtexpress.vn/apiDoc/logistics/query). Bộ gom lô dưới đây tôn trọng con số đó theo từng hãng.
#
# KHÔNG tự chạy theo lịch. Phải có người gọi `chay_mot_luot()` hoặc bật `BatDauNen` — đúng luật
# "tự động hóa phải do người duyệt".
import json
import threading

import adapter
import adapter_jt   # noqa: F401
import adapter_vtp  # noqa: F401
import bao_mat
import csdl
import don_hang

# Trạng thái giao vận coi là CÒN ĐANG CHẠY — chỉ hỏi hãng về những đơn này.
DANG_CHAY = ("cho_lay", "lay_hang", "dang_giao")
MAC_DINH_MOI_LUOT = 20


def so_van_don_moi_luot(ma_hang):
    """Giới hạn gom lô theo tài liệu từng hãng; không biết thì dùng mức dè dặt."""
    lop = adapter._DANG_KY.get(ma_hang)
    mod = {"jt": getattr(adapter_jt, "SO_VAN_DON_MOI_LUOT", None)}.get(ma_hang)
    return mod or MAC_DINH_MOI_LUOT


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

    tk = {"da_hoi": 0, "doi_trang_thai": 0, "khong_doi": 0, "ma_la": 0, "loi": 0, "bo_qua_hang": []}
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
        for lo in _gom_lo(nhom, so_van_don_moi_luot(ma_hang)):
            for d in lo:
                try:
                    cred = json.loads(bao_mat.giai_ma(d["credentials_ma_hoa"]))
                    ad = adapter.tao_adapter(ma_hang, cred, d["moi_truong"])
                    kq = ad.trackOrder(d["ma_van_don"])
                    tk["da_hoi"] += 1
                    if not kq.ok:
                        tk["loi"] += 1
                        continue
                    ma_tt = (kq.tho or {}).get("trang_thai")
                    ax = ad.normalizeTrackingStatus(ma_tt)
                    if not ax.biet_ma:
                        tk["ma_la"] += 1
                        csdl.audit("polling_ma_la", f"don:{d['id']}",
                                   f"hãng {ma_hang} trả mã lạ: {ax.ma_goc}",
                                   tenant_id=d["tenant_id"], ket_qua="that_bai")
                        continue
                    if ax.trang_thai is None:
                        tk["khong_doi"] += 1
                        continue
                    # ĐI QUA ĐÚNG đường của webhook: rank guard + ghi lịch sử
                    ap, ly_do = don_hang.ap_trang_thai_giao(d["id"], ax.trang_thai, "polling")
                    if ap:
                        tk["doi_trang_thai"] += 1
                        csdl.audit("polling_cap_nhat", f"don:{d['id']}",
                                   f"{ma_hang} {ax.ma_goc} → {ax.trang_thai}", tenant_id=d["tenant_id"])
                    else:
                        tk["khong_doi"] += 1
                except Exception as e:
                    tk["loi"] += 1
                    csdl.audit("polling_loi", f"don:{d['id']}", f"{type(e).__name__}: {e}",
                               tenant_id=d["tenant_id"], ket_qua="that_bai")
    return tk


class BatDauNen:
    """Chạy polling định kỳ trong luồng nền. CHỈ bật khi người dùng/Owner yêu cầu."""
    def __init__(self, moi_giay=300, chi_hang_khong_webhook=True):
        self.moi_giay = moi_giay
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
        while not self._dung.wait(self.moi_giay):
            try:
                chay_mot_luot(chi_hang_khong_webhook=self.chi_hang_khong_webhook)
            except Exception as e:
                csdl.audit("polling_vong_loi", "he_thong:1", f"{type(e).__name__}: {e}",
                           ket_qua="that_bai")

    def tat(self):
        self._dung.set()
