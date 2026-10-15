#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G16 — CHỐT AN TOÀN của harness nghiệm thu. Harness TỪ CHỐI CHẠY nếu mất một chốt.

SÁU CHỐT, và mỗi chốt canh một cách làm bẩn dữ liệu hoặc một cách gọi ra ngoài:

  1. `VIP_HUB_DATA` phải nằm trong thư mục TẠM và KHÔNG được là `app/du-lieu/`.
     Kịch bản G16 TẠO tenant, tài khoản hãng, đơn và sự kiện webhook THẬT trong CSDL.
     Chạy lên dữ liệu thật là làm bẩn dữ liệu đang dùng.
  2. `VIP_HUB_BIND` phải TRỐNG hoặc là địa chỉ loopback. `server.py` mặc định bind
     `127.0.0.1`, nhưng biến môi trường đổi được — và mở cổng ra Internet là `V-G11-01`,
     CHƯA CẤP.
  3. Mọi adapter trong sổ đăng ký `adapter._DANG_KY` phải có `CHO_PHEP_LIVE is False`.
     Một harness "thử" mà mở được cửa gọi hãng thật là thứ NGUY HIỂM HƠN không có harness.
  4. Cổng môi trường J&T: `cau_hinh.JT_CHO_PHEP_SANDBOX` và `JT_CHO_PHEP_PRODUCTION` phải là
     `False`, VÀ hàm dẫn xuất `adapter_jt.moi_truong_duoc_chay()` phải nói CÙNG điều đó. Hai
     nguồn lệch nhau là lúc một trong hai đã bị sửa mà không ai thấy.
     (Chốt này đọc `cau_hinh` — nguồn sự thật — chứ không đọc một bản sao trong tệp này.)
  5. Cờ `VIP_G16_CHO_PHEP_GOI_HANG` phải KHÔNG bật. Cờ này tồn tại để một lượt chạy "quên"
     không thể biến harness MOCK thành harness gọi hãng: `V-G09-01` + `V-13906-05` CHƯA CẤP,
     nên đường gọi hãng không có quyền tồn tại trong lượt này.
  6. Địa chỉ đích phải là loopback (`127.0.0.1` / `localhost` / `::1`). Không tên miền, không
     IP ngoài, không tunnel.

VÌ SAO CÓ `--tu-kiem`
--------------------
Chốt chặn CŨNG là một thứ dùng để kiểm chứng, nên nó cũng phải được kiểm
(docs/G15_E2E_HARNESS.md §0: bản đầu của chốt `CHO_PHEP_LIVE` đọc nhầm hằng của mô-đun và TỪ
CHỐI OAN cả lượt chạy).

`python3 chot_an_toan.py --tu-kiem` chạy bộ dò trên **mười cấu hình tổng hợp**: một cấu hình ĐỦ
CHỐT (phải ĐI QUA) và chín cấu hình HỎNG (mỗi cái phải bị bắt). Mỗi ca hỏng còn phải bị bắt bởi
**ĐÚNG chốt đang muốn đo** — nếu chỉ kiểm "có bị từ chối không" thì một ca hỏng vì lý do KHÁC
vẫn được tính là đạt, và bộ dò trông như đang hoạt động trong khi nó không đo thứ mình tuyên bố.

Bài học có thật, đo được ở lượt này: AG-03 đổi chữ ký `adapter_jt.moi_truong_duoc_chay()` từ hai
tham số xuống một, và ba ca G/H/I ngay lập tức "đạt" vì bị bắt bởi một `TypeError` — tức bắt
đúng kết quả nhưng SAI lý do. Phép kiểm "bắt đúng chốt" là thứ đã lôi việc đó ra ánh sáng.

CHẠY
----
    python3 trien_khai/g16/chot_an_toan.py --tu-kiem
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
CO_GOI_HANG = "VIP_G16_CHO_PHEP_GOI_HANG"


def _trong_thu_muc_tam(duong):
    """Đường này có nằm trong một thư mục tạm không. So bằng realpath để `..` không lách được."""
    that = os.path.realpath(duong)
    for goc in THU_MUC_TAM:
        if goc and (that == os.path.realpath(goc) or that.startswith(os.path.realpath(goc) + os.sep)):
            return True
    return False


def _so_dang_ky_that():
    """Sổ đăng ký adapter THẬT mà mã đang chạy dùng — không tự đoán tên lớp.

    Bản đầu của chốt này (G15) đọc `adapter_jt.CHO_PHEP_LIVE` — hằng đó là của LỚP, không phải
    của mô-đun, nên nó thấy '<thiếu>' và từ chối oan. Ở đây đọc đúng `adapter._DANG_KY`.
    """
    import adapter
    import adapter_jt          # noqa: F401  (để tự đăng ký)
    import adapter_vtp         # noqa: F401
    return adapter._DANG_KY


def _cong_moi_truong_jt(cho_phep_tiem=None):
    """(sandbox_duoc_chay, production_duoc_chay, ghi_chu) — đọc NGUỒN SỰ THẬT `cau_hinh`.

    `cho_phep_tiem` để lượt tự kiểm tiêm được trạng thái cổng mà không phải sửa mã sản phẩm.
    Hằng nào KHÔNG đọc được thì coi như ĐANG MỞ (True) — hướng an toàn là TỪ CHỐI, không phải
    đi tiếp khi không kiểm được.
    """
    import cau_hinh
    if cho_phep_tiem is not None:
        return (bool(cho_phep_tiem.get("sandbox")), bool(cho_phep_tiem.get("production")),
                "tiêm cho lượt tự kiểm")
    sb = getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", True)
    pr = getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", True)
    return bool(sb), bool(pr), "cau_hinh.JT_CHO_PHEP_SANDBOX/PRODUCTION"


def ly_do_tu_choi(nen, goc_url=None, so_dang_ky=None, cho_phep_jt=None,
                  env=None, goc_du_an=None):
    """SÁU chốt. Trả danh sách lý do TỪ CHỐI (rỗng = chạy được).

    Mọi đầu vào đều TIÊM ĐƯỢC (`env`, `so_dang_ky`, `cho_phep_jt`, `goc_url`) để `--tu-kiem`
    chạy được bộ dò trên cấu hình tổng hợp mà không phải đổi môi trường thật.
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
            ly_do.append("cổng môi trường J&T: SANDBOX đang MỞ (%s) — harness G16 chỉ chạy MOCK."
                         " Từ chối. Cần V-G09-01 + V-13906-05 mới được mở." % nguon)
        if pr:
            ly_do.append("cổng môi trường J&T: PRODUCTION đang MỞ (%s) — không agent nào được mở."
                         " Từ chối." % nguon)
    except Exception as e:                                       # noqa: BLE001
        ly_do.append("không đọc được cổng môi trường J&T (%s: %s) — từ chối."
                     % (type(e).__name__, e))
    if cho_phep_jt is None:
        # Hàm DẪN XUẤT của adapter phải nói cùng điều. Gọi bằng ĐÚNG một tham số vị trí: chữ ký
        # này đã đổi một lần trong lúc bốn làn cùng chạy, và bộ dò phải hỏng ỒN ÀO nếu nó đổi nữa.
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
    return ly_do


def bao_cao_moi_truong():
    """Dữ kiện ĐỌC ĐƯỢC về lớp vận chuyển thật — để báo cáo, KHÔNG phải một chốt.

    `app/http_jt.py` có thể đã tồn tại (AG-02 viết). Có lớp HTTP thật KHÔNG phải lỗi: cổng mở
    đường gọi hãng nằm ở `CHO_PHEP_LIVE` + `cau_hinh.JT_CHO_PHEP_*`. Ghi ra để người đọc báo cáo
    biết lớp đó CÓ mà harness KHÔNG gọi tới.
    """
    tk = {"http_jt_co_that": os.path.exists(os.path.join(GOC_APP, "http_jt.py"))}
    try:
        import cau_hinh
        tk["cau_hinh.JT_CHO_PHEP_SANDBOX"] = bool(getattr(cau_hinh, "JT_CHO_PHEP_SANDBOX", True))
        tk["cau_hinh.JT_CHO_PHEP_PRODUCTION"] = bool(getattr(cau_hinh, "JT_CHO_PHEP_PRODUCTION", True))
    except Exception as e:                                       # noqa: BLE001
        tk["loi_doc_cau_hinh"] = "%s: %s" % (type(e).__name__, e)
    try:
        # `_so_dang_ky_that()` chứ không phải `import adapter`: sổ đăng ký chỉ được ĐIỀN khi
        # `adapter_jt`/`adapter_vtp` được nạp. Chỉ `import adapter` thì sổ RỖNG, và báo cáo sẽ
        # nói "không hãng nào mở live" trong khi thật ra nó chưa từng nhìn vào hãng nào —
        # đúng kiểu hỏng im lặng mà tài liệu này dựng ra để chặn.
        tk["adapter_cho_phep_live"] = {m: getattr(lop, "CHO_PHEP_LIVE", "<thiếu>")
                                       for m, lop in sorted(_so_dang_ky_that().items())}
    except Exception as e:                                       # noqa: BLE001
        tk["loi_doc_adapter"] = "%s: %s" % (type(e).__name__, e)
    return tk


# ============================================================================
# TỰ KIỂM BỘ DÒ — mười cấu hình tổng hợp, mỗi ca phải bị bắt bởi ĐÚNG chốt
# ============================================================================
class _LopGia(object):
    def __init__(self, ten, live):
        self.__name__ = ten
        self.CHO_PHEP_LIVE = live


def bo_ca_tu_kiem():
    """(mã, mô tả, phải_từ_chối, chuỗi_chứng_minh_đúng_chốt, kwargs) cho `--tu-kiem`.

    Đối chứng DƯƠNG là ca A: cấu hình đủ chốt phải ĐI QUA được. Thiếu nó thì một bộ dò
    `return ["từ chối"]` cũng "bắt được" cả chín ca hỏng và trông như đang hoạt động.
    """
    nen = os.path.join(tempfile.gettempdir(), "veh-g16-tu-kiem-nen")
    dang_ky_an = {"jt": _LopGia("AdapterJT", False), "vtp": _LopGia("AdapterVTP", False)}
    env_an = {"VIP_HUB_DATA": nen}
    khop = {"sandbox": False, "production": False}
    return [
        ("A", "cấu hình ĐỦ CHỐT (đối chứng dương) — phải ĐI QUA", False, None,
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt=khop)),
        ("B", "VIP_HUB_DATA trỏ vào dữ liệu THẬT", True, "dữ liệu THẬT",
         dict(nen=os.path.join(DU_AN, "app", "du-lieu"), goc_url="http://127.0.0.1:18999",
              so_dang_ky=dang_ky_an, env={"VIP_HUB_DATA": os.path.join(DU_AN, "app", "du-lieu")},
              cho_phep_jt=khop)),
        ("C", "VIP_HUB_DATA ngoài thư mục tạm", True, "thư mục tạm",
         dict(nen=os.path.join(DU_AN, "nen-khong-tam"), goc_url="http://127.0.0.1:18999",
              so_dang_ky=dang_ky_an, env={"VIP_HUB_DATA": os.path.join(DU_AN, "nen-khong-tam")},
              cho_phep_jt=khop)),
        ("D", "một adapter có CHO_PHEP_LIVE = True", True, "CHO_PHEP_LIVE",
         dict(nen=nen, goc_url="http://127.0.0.1:18999",
              so_dang_ky={"jt": _LopGia("AdapterJT", True)}, env=env_an, cho_phep_jt=khop)),
        ("E", "sổ đăng ký adapter RỖNG", True, "RỖNG",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky={}, env=env_an,
              cho_phep_jt=khop)),
        ("F", "VIP_HUB_BIND = 0.0.0.0 (mở ra ngoài)", True, "VIP_HUB_BIND",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an,
              env=dict(env_an, VIP_HUB_BIND="0.0.0.0"), cho_phep_jt=khop)),
        ("G", "đích không phải loopback (tên miền ngoài)", True, "không phải loopback",
         dict(nen=nen, goc_url="http://open.jtexpress.vn:80", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt=khop)),
        ("H", "cờ %s bật" % CO_GOI_HANG, True, CO_GOI_HANG,
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an,
              env=dict(env_an, **{CO_GOI_HANG: "1"}), cho_phep_jt=khop)),
        ("I", "cổng môi trường SANDBOX của J&T bị MỞ", True, "SANDBOX đang MỞ",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt={"sandbox": True, "production": False})),
        ("J", "cổng môi trường PRODUCTION của J&T bị MỞ", True, "PRODUCTION đang MỞ",
         dict(nen=nen, goc_url="http://127.0.0.1:18999", so_dang_ky=dang_ky_an, env=env_an,
              cho_phep_jt={"sandbox": False, "production": True})),
    ]


def tu_kiem(cho_in=True):
    """Chạy bộ dò trên mười cấu hình tổng hợp. Trả (so_ca, so_hong, danh_sach)."""
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
        print("TỰ KIỂM BỘ DÒ CHỐT AN TOÀN G16 — %d cấu hình tổng hợp" % len(ds))
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
    print("SÁU CHỐT AN TOÀN: ĐỦ. Nền %s · bind loopback · CHO_PHEP_LIVE=False · không gọi hãng." % nen)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
