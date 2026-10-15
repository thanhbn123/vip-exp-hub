#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G17 — CHỐT AN TOÀN của harness webhook (AG-04). Harness TỪ CHỐI CHẠY nếu mất một chốt.

BẢY CHỐT. Sáu chốt đầu kế thừa nguyên từ G16 (cùng câu hỏi, cùng câu trả lời); chốt thứ bảy là
thứ G17 thêm vào, và nó canh đúng chỗ lượt này dễ tự lừa mình nhất.

  1. `VIP_HUB_DATA` phải nằm trong thư mục TẠM và KHÔNG được là `app/du-lieu/`. Kịch bản G17
     TẠO tenant, tài khoản hãng, đơn và sự kiện webhook THẬT trong CSDL.
  2. `VIP_HUB_BIND` phải TRỐNG hoặc loopback. Mở cổng ra Internet là `V-G11-01`, CHƯA CẤP.
  3. Mọi adapter trong `adapter._DANG_KY` phải có `CHO_PHEP_LIVE is False`.
  4. Cổng môi trường J&T (`cau_hinh.JT_CHO_PHEP_SANDBOX` / `JT_CHO_PHEP_PRODUCTION`) phải đóng,
     VÀ hàm dẫn xuất `adapter_jt.moi_truong_duoc_chay()` phải nói CÙNG điều đó.
  5. Cờ `VIP_G17_CHO_PHEP_GOI_HANG` phải KHÔNG bật. `V-G09-01` + `V-13906-05` CHƯA CẤP.
  6. Mọi địa chỉ đích phải là loopback (`127.0.0.1` / `localhost` / `::1`).
  7. **GIẤY PHÉP CỦA CHẶNG CHẠM HÃNG**: chặng nào cần giấy phép thì phải KHAI RA đúng mã giấy
     phép, và giấy phép đó phải CHƯA được cấp. Chốt này canh một cách tự lừa mình rất cụ thể:
     một chặng `BLOCKED` bị sửa thành `ĐẠT (MOCK)` thì lượt chạy vẫn xanh, vẫn 0 hỏng, và không
     ai đọc ra rằng chặng chạm hãng chưa từng chạy. Nên: chặng cần giấy phép mà không khai, hoặc
     khai mã rỗng ⇒ TỪ CHỐI; và nếu ai đó "cấp" giấy phép bằng biến môi trường
     `VIP_G17_GIAY_PHEP` ⇒ TỪ CHỐI NGAY, vì hai giấy phép ấy không phải thứ một harness tự cấp.

VÌ SAO CÓ `--tu-kiem`
--------------------
Chốt chặn CŨNG là thứ dùng để kiểm chứng, nên nó phải được kiểm. `--tu-kiem` chạy bộ dò trên
**mười hai cấu hình tổng hợp**: một cấu hình ĐỦ CHỐT (phải ĐI QUA) và mười một cấu hình HỎNG
(mỗi cái phải bị bắt bởi **ĐÚNG chốt đang muốn đo**). Chỉ kiểm "có bị từ chối không" thì một ca
hỏng vì lý do KHÁC vẫn được tính là đạt — bộ dò trông như đang hoạt động trong khi nó không đo
thứ mình tuyên bố (bài học có thật của G16: ba ca "đạt" vì một `TypeError`).

CHẠY
----
    python3 trien_khai/g17/chot_an_toan.py --tu-kiem
"""
import os
import sys
import tempfile

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(DU_AN, "app")
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)

LOOPBACK = ("127.0.0.1", "localhost", "::1")
THU_MUC_TAM = ("/tmp", "/var/folders", "/private/var/folders", tempfile.gettempdir())
CO_GOI_HANG = "VIP_G17_CHO_PHEP_GOI_HANG"
BIEN_GIAY_PHEP = "VIP_G17_GIAY_PHEP"


def _trong_thu_muc_tam(duong):
    """Đường này có nằm trong một thư mục tạm không. So bằng realpath để `..` không lách được."""
    that = os.path.realpath(duong)
    for goc in THU_MUC_TAM:
        if goc and (that == os.path.realpath(goc) or that.startswith(os.path.realpath(goc) + os.sep)):
            return True
    return False


def _so_dang_ky_that():
    """Sổ đăng ký adapter THẬT mà mã đang chạy dùng — không tự đoán tên lớp."""
    import adapter
    import adapter_jt          # noqa: F401  (để tự đăng ký)
    import adapter_vtp         # noqa: F401
    return adapter._DANG_KY


def _cong_moi_truong_jt(cho_phep_tiem=None):
    """(sandbox_duoc_chay, production_duoc_chay, ghi_chu) — đọc NGUỒN SỰ THẬT `cau_hinh`.

    Hằng nào KHÔNG đọc được thì coi như ĐANG MỞ (True): hướng an toàn là TỪ CHỐI.
    """
    import cau_hinh
    if cho_phep_tiem is not None:
        return (bool(cho_phep_tiem.get("sandbox")), bool(cho_phep_tiem.get("production")),
                "tiêm cho lượt tự kiểm")
    sb = getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", True)
    pr = getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", True)
    return bool(sb), bool(pr), "cau_hinh.JT_CHO_PHEP_SANDBOX/PRODUCTION"


def giay_phep_duoc_cap(env=None):
    """Tập giấy phép mà môi trường ĐANG khai là đã cấp. Rỗng là trạng thái đúng của lượt này.

    Định dạng: `VIP_G17_GIAY_PHEP=V-G09-01,V-13906-05`. Không có biến ⇒ rỗng.
    """
    env = os.environ if env is None else env
    tho = str(env.get(BIEN_GIAY_PHEP, "") or "")
    return {x.strip() for x in tho.replace(";", ",").split(",") if x.strip()}


def ly_do_tu_choi(nen, goc_url=None, so_dang_ky=None, cho_phep_jt=None,
                  env=None, goc_du_an=None, buoc_can_giay_phep=None, giay_phep=None):
    """BẢY chốt. Trả danh sách lý do TỪ CHỐI (rỗng = chạy được).

    Mọi đầu vào đều TIÊM ĐƯỢC để `--tu-kiem` chạy được bộ dò trên cấu hình tổng hợp mà không
    phải đổi môi trường thật.
    """
    env = dict(os.environ if env is None else env)
    goc_du_an = goc_du_an or DU_AN
    ly_do = []

    # ---- 1. dữ liệu: phải là nền TẠM, không bao giờ là dữ liệu thật
    that = os.path.realpath(os.path.join(goc_du_an, "app", "du-lieu"))
    nen_that = os.path.realpath(nen or "")
    if not nen:
        ly_do.append("VIP_HUB_DATA trống — harness chỉ chạy trên một nền TẠM do nó tự dựng.")
    elif nen_that == that or nen_that.startswith(that + os.sep):
        ly_do.append("VIP_HUB_DATA trỏ vào dữ liệu THẬT (%s) — từ chối." % that)
    elif not _trong_thu_muc_tam(nen):
        ly_do.append("VIP_HUB_DATA=%r không nằm trong thư mục tạm — từ chối." % nen)

    # ---- 2. bind: mặc định của server.py là 127.0.0.1, nhưng biến môi trường đổi được
    bind = str(env.get("VIP_HUB_BIND", "") or "").strip()
    if bind and bind not in LOOPBACK:
        ly_do.append("VIP_HUB_BIND=%r không phải loopback — mở cổng ra ngoài là V-G11-01"
                     " (CHƯA CẤP). Từ chối." % bind)

    # ---- 3. CHO_PHEP_LIVE của MỌI adapter trong sổ đăng ký
    if so_dang_ky is None:
        try:
            so_dang_ky = _so_dang_ky_that()
        except Exception as e:                                   # noqa: BLE001
            ly_do.append("không đọc được sổ đăng ký adapter (%s: %s) — chốt này không kiểm"
                         " được gì thì phải TỪ CHỐI, không được đoán." % (type(e).__name__, e))
            so_dang_ky = None
    if so_dang_ky is not None:
        if not so_dang_ky:
            ly_do.append("sổ đăng ký adapter RỖNG — chốt an toàn này không kiểm được gì.")
        for ma, lop in sorted(so_dang_ky.items()):
            live = getattr(lop, "CHO_PHEP_LIVE", "<thiếu>")
            if live is not False:
                ly_do.append("%s.CHO_PHEP_LIVE = %r — phải CHỐT CỨNG là False. Từ chối."
                             % (getattr(lop, "__name__", ma), live))

    # ---- 4. cổng môi trường J&T: nguồn sự thật `cau_hinh` + hàm dẫn xuất của adapter
    try:
        sb, pr, nguon = _cong_moi_truong_jt(cho_phep_jt)
        if sb:
            ly_do.append("cổng môi trường J&T: SANDBOX đang MỞ (%s) — harness G17 chỉ chạy MOCK."
                         " Từ chối. Cần V-G09-01 + V-13906-05 mới được mở." % nguon)
        if pr:
            ly_do.append("cổng môi trường J&T: PRODUCTION đang MỞ (%s) — không agent nào được mở."
                         " Từ chối." % nguon)
    except Exception as e:                                       # noqa: BLE001
        ly_do.append("không đọc được cổng môi trường J&T (%s: %s) — từ chối."
                     % (type(e).__name__, e))
    if cho_phep_jt is None:
        try:
            import adapter_jt
            for mt in ("sandbox", "production"):
                if adapter_jt.moi_truong_duoc_chay(mt):
                    ly_do.append("adapter_jt.moi_truong_duoc_chay(%r) trả True — lệch với cổng"
                                 " trong `cau_hinh`. Từ chối." % mt)
        except Exception as e:                                   # noqa: BLE001
            ly_do.append("không kiểm được cổng môi trường của adapter_jt (%s: %s) — từ chối,"
                         " vì không kiểm được thì không được đi tiếp."
                         % (type(e).__name__, e))

    # ---- 5. cờ "cho phép gọi hãng" — có mặt để một lượt chạy quên KHÔNG thể mở đường gọi hãng
    if str(env.get(CO_GOI_HANG, "") or "").strip() not in ("", "0", "false", "False"):
        ly_do.append("%s=%r đang bật — V-G09-01 + V-13906-05 CHƯA CẤP, harness không có quyền"
                     " gọi hãng kể cả sandbox. Từ chối." % (CO_GOI_HANG, env.get(CO_GOI_HANG)))

    # ---- 6. đích đến phải là loopback
    if goc_url:
        try:
            from urllib.parse import urlparse
            host = (urlparse(goc_url).hostname or "")
        except Exception:                                        # noqa: BLE001
            host = ""
        if host not in LOOPBACK:
            ly_do.append("địa chỉ đích %r không phải loopback (%s) — từ chối."
                         % (goc_url, ", ".join(LOOPBACK)))

    # ---- 7. GIẤY PHÉP của chặng chạm hãng
    if buoc_can_giay_phep is None:
        try:
            import harness_webhook
            buoc_can_giay_phep = harness_webhook.buoc_can_giay_phep()
        except Exception as e:                                   # noqa: BLE001
            ly_do.append("không đọc được danh sách chặng cần giấy phép (%s: %s) — không kiểm được"
                         " thì TỪ CHỐI: một chặng BLOCKED bị đổi thành ĐẠT sẽ không ai thấy."
                         % (type(e).__name__, e))
            buoc_can_giay_phep = None
    if buoc_can_giay_phep is not None:
        if not buoc_can_giay_phep:
            ly_do.append("không chặng nào khai giấy phép — danh sách rỗng nghĩa là chốt này"
                         " không canh gì. Từ chối.")
        for ma_buoc, gp in sorted(buoc_can_giay_phep.items()):
            if not gp:
                ly_do.append("chặng %s chạm hãng nhưng KHÔNG khai mã giấy phép — TỪ CHỐI."
                             % ma_buoc)
    cap = giay_phep_duoc_cap(env) if giay_phep is None else set(giay_phep)
    if cap:
        ly_do.append("%s=%s: có giấy phép được khai là ĐÃ CẤP (%s) — V-G09-01 và V-13906-05"
                     " KHÔNG phải thứ một harness tự cấp, và harness này chỉ được chạy MOCK."
                     " Từ chối." % (BIEN_GIAY_PHEP, ",".join(sorted(cap)), ", ".join(sorted(cap))))
    return ly_do


def bao_cao_moi_truong():
    """Dữ kiện ĐỌC ĐƯỢC về lớp vận chuyển thật — để báo cáo, KHÔNG phải một chốt."""
    tk = {"http_jt_co_that": os.path.exists(os.path.join(GOC_APP, "http_jt.py"))}
    try:
        import cau_hinh
        tk["cau_hinh.JT_CHO_PHEP_SANDBOX"] = bool(getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", True))
        tk["cau_hinh.JT_CHO_PHEP_PRODUCTION"] = bool(getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", True))
    except Exception as e:                                       # noqa: BLE001
        tk["loi_doc_cau_hinh"] = "%s: %s" % (type(e).__name__, e)
    try:
        tk["adapter_cho_phep_live"] = {m: getattr(lop, "CHO_PHEP_LIVE", "<thiếu>")
                                       for m, lop in sorted(_so_dang_ky_that().items())}
    except Exception as e:                                       # noqa: BLE001
        tk["loi_doc_adapter"] = "%s: %s" % (type(e).__name__, e)
    tk[BIEN_GIAY_PHEP] = sorted(giay_phep_duoc_cap())
    return tk


# ============================================================================
# TỰ KIỂM BỘ DÒ — mười hai cấu hình tổng hợp, mỗi ca phải bị bắt bởi ĐÚNG chốt
# ============================================================================
class _LopGia(object):
    def __init__(self, ten, live):
        self.__name__ = ten
        self.CHO_PHEP_LIVE = live


def bo_ca_tu_kiem():
    """(mã, mô tả, phải_từ_chối, chuỗi_chứng_minh_đúng_chốt, kwargs) cho `--tu-kiem`.

    Đối chứng DƯƠNG là ca A: cấu hình đủ chốt phải ĐI QUA được. Thiếu nó thì một bộ dò
    `return ["từ chối"]` cũng "bắt được" cả mười một ca hỏng và trông như đang hoạt động.
    """
    nen = os.path.join(tempfile.gettempdir(), "veh-g17-tu-kiem-nen")
    dang_ky_an = {"jt": _LopGia("AdapterJT", False), "vtp": _LopGia("AdapterVTP", False)}
    env_an = {"VIP_HUB_DATA": nen}
    khop = {"sandbox": False, "production": False}
    buoc = {"G17-SANDBOX": ("V-G09-01", "V-13906-05")}
    return [
        ("A", "cấu hình ĐỦ CHỐT (đối chứng dương) — phải ĐI QUA", False, None,
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt=khop, buoc_can_giay_phep=buoc, giay_phep=set())),
        ("B", "VIP_HUB_DATA trỏ vào dữ liệu THẬT", True, "dữ liệu THẬT",
         dict(nen=os.path.join(DU_AN, "app", "du-lieu"), goc_url="http://127.0.0.1:18999",
              so_dang_ky=dang_ky_an, env={"VIP_HUB_DATA": os.path.join(DU_AN, "app", "du-lieu")},
              cho_phep_jt=khop, buoc_can_giay_phep=buoc, giay_phep=set())),
        ("C", "VIP_HUB_DATA ngoài thư mục tạm", True, "thư mục tạm",
         dict(nen=os.path.join(DU_AN, "nen-khong-tam"), goc_url="http://127.0.0.1:18999",
              so_dang_ky=dang_ky_an, env={"VIP_HUB_DATA": os.path.join(DU_AN, "nen-khong-tam")},
              cho_phep_jt=khop, buoc_can_giay_phep=buoc, giay_phep=set())),
        ("D", "một adapter có CHO_PHEP_LIVE = True", True, "CHO_PHEP_LIVE",
         dict(nen=nen, goc_url="http://127.0.0.1:18999",
              so_dang_ky={"jt": _LopGia("AdapterJT", True)}, env=env_an, cho_phep_jt=khop,
              buoc_can_giay_phep=buoc, giay_phep=set())),
        ("E", "sổ đăng ký adapter RỖNG", True, "RỖNG",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky={}, env=env_an,
              cho_phep_jt=khop, buoc_can_giay_phep=buoc, giay_phep=set())),
        ("F", "VIP_HUB_BIND = 0.0.0.0 (mở ra ngoài)", True, "VIP_HUB_BIND",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an,
              env=dict(env_an, VIP_HUB_BIND="0.0.0.0"), cho_phep_jt=khop,
              buoc_can_giay_phep=buoc, giay_phep=set())),
        ("G", "đích không phải loopback (tên miền ngoài)", True, "không phải loopback",
         dict(nen=nen, goc_url="http://open.jtexpress.vn:80", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt=khop, buoc_can_giay_phep=buoc, giay_phep=set())),
        ("H", "cờ %s bật" % CO_GOI_HANG, True, CO_GOI_HANG,
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an,
              env=dict(env_an, **{CO_GOI_HANG: "1"}), cho_phep_jt=khop,
              buoc_can_giay_phep=buoc, giay_phep=set())),
        ("I", "cổng môi trường SANDBOX của J&T bị MỞ", True, "SANDBOX đang MỞ",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt={"sandbox": True, "production": False}, buoc_can_giay_phep=buoc,
              giay_phep=set())),
        ("J", "cổng môi trường PRODUCTION của J&T bị MỞ", True, "PRODUCTION đang MỞ",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt={"sandbox": False, "production": True}, buoc_can_giay_phep=buoc,
              giay_phep=set())),
        # --- hai ca MỚI của G17: chúng canh đúng thứ lượt này dễ tự lừa mình nhất
        ("K", "biến môi trường KHAI là đã cấp giấy phép gọi hãng", True, BIEN_GIAY_PHEP,
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an,
              env=dict(env_an, **{BIEN_GIAY_PHEP: "V-G09-01,V-13906-05"}), cho_phep_jt=khop,
              buoc_can_giay_phep=buoc, giay_phep={"V-G09-01"})),
        ("L", "chặng chạm hãng KHÔNG khai mã giấy phép", True, "KHÔNG khai mã giấy phép",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt=khop, buoc_can_giay_phep={"G17-SANDBOX": ()}, giay_phep=set())),
    ]


def tu_kiem(cho_in=True):
    """Chạy bộ dò trên mười hai cấu hình tổng hợp. Trả (so_ca, so_hong, danh_sach)."""
    so_hong, ket_qua = 0, []
    for ma, mo_ta, phai_tu_choi, chua, kw in bo_ca_tu_kiem():
        ly_do = ly_do_tu_choi(**kw)
        bi_tu_choi = bool(ly_do)
        dung_ket_qua = (bi_tu_choi == phai_tu_choi)
        # Ca hỏng phải bị bắt bởi ĐÚNG chốt đang muốn đo — bắt vì lý do khác là ĐO SAI.
        dung_chot = (not phai_tu_choi) or any(chua in x for x in ly_do)
        dat = dung_ket_qua and dung_chot
        if not dat:
            so_hong += 1
        ket_qua.append({"ma": ma, "mo_ta": mo_ta, "mong_doi_tu_choi": phai_tu_choi,
                        "thuc_te_tu_choi": bi_tu_choi, "dung_chot": dung_chot, "dat": dat,
                        "ly_do": ly_do[0] if ly_do else ""})
        if cho_in:
            print("  %s [%s] %s" % ("✓" if dat else "✗", ma, mo_ta))
            if not dat:
                print("        MONG ĐỢI từ chối=%s (bắt bởi chốt chứa %r) · THỰC TẾ=%s · lý do=%s"
                      % (phai_tu_choi, chua, bi_tu_choi, ly_do[0] if ly_do else "(không từ chối)"))
            elif ly_do:
                print("        bắt đúng chốt: %s" % ly_do[0])
    return len(ket_qua), so_hong, ket_qua


def main(argv):
    if "--tu-kiem" in argv:
        ds = bo_ca_tu_kiem()
        print("═" * 74)
        print("TỰ KIỂM BỘ DÒ CHỐT AN TOÀN G17 — %d cấu hình tổng hợp" % len(ds))
        print("═" * 74)
        tong, hong, _ = tu_kiem()
        print("─" * 74)
        print("TỰ KIỂM: %d/%d ca đạt · %d hỏng" % (tong - hong, tong, hong))
        if hong:
            print("BỘ DÒ HỎNG: nó không phân biệt được cấu hình an toàn với cấu hình nguy hiểm,")
            print("hoặc bắt đúng kết quả nhưng vì lý do khác chốt đang muốn đo.")
            print("Mọi lời khai 'harness đã từ chối chạy' ở lượt này KHÔNG có giá trị.")
            return 1
        print("Bộ dò bắt ĐÚNG chốt ở cả %d cấu hình ⇒ lời khai 'TỪ CHỐI CHẠY' mới có nghĩa." % tong)
        print("Dữ kiện lớp vận chuyển: %s" % bao_cao_moi_truong())
        return 0
    nen = os.environ.get("VIP_HUB_DATA") or ""
    ly_do = ly_do_tu_choi(nen)
    if ly_do:
        print("TỪ CHỐI CHẠY:")
        for x in ly_do:
            print("  · " + x)
        return 4
    print("BẢY CHỐT AN TOÀN: ĐỦ. Nền %s · bind loopback · CHO_PHEP_LIVE=False · không gọi hãng"
          " · chặng chạm hãng khai đúng giấy phép còn thiếu." % nen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
