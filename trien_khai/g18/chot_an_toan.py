#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G18 — CHỐT AN TOÀN CHO HARNESS TẢI HTTP THẬT (làn AG-04).

Harness G18 dựng **máy chủ THẬT** (`app/server.py`, `ThreadingHTTPServer`) và bắn tải vào nó.
Nó khác harness G17 ở ĐÚNG MỘT ĐIỂM nguy hiểm: G17 spawn **một** máy chủ, G18 spawn **nhiều**
tiến trình máy chủ cùng lúc, cùng một CSDL. "Nhiều tiến trình" là thứ vừa là phép đo, vừa là
cách tự bắn vào chân mình: một vòng lặp tạo tiến trình sai thì phép đo biến thành bộ sinh tiến
trình, và một địa chỉ bind sai thì máy chủ mở cổng ra ngoài LAN.

VÌ SAO KHÔNG VIẾT LẠI BẢY CHỐT CỦA G17
--------------------------------------
Bảy chốt ấy (`trien_khai/g17/chot_an_toan.py`) đã được duyệt và đã chạy. Chép lại thành bản thứ
hai là tạo HAI nguồn sự thật cho cùng một bất biến: ngày ai sửa một bản, bản kia vẫn xanh và
không có gì báo. Nên ở đây **gọi thẳng** mô-đun G17 (nạp theo đường dẫn, không phải qua `sys.path`
để không lẫn với tệp cùng tên của dự án), rồi **thêm năm chốt riêng của G18** cho đúng những
thứ G18 mới mang vào: số tiến trình, địa chỉ bind của TỪNG tiến trình, không dính PostgreSQL,
cấm `pkill`/`killall`, và nền phải tách khỏi nền G17.

MƯỢN ĐƯỢC THÌ PHẢI KIỂM ĐƯỢC LÀ CÒN MƯỢN ĐƯỢC
-----------------------------------------------
Gọi mô-đun của làn khác là một phụ thuộc có thể gãy im lặng. Nên `--tu-kiem` **gọi từng chốt G17
một** trên cấu hình tổng hợp và đòi câu lý do phải khớp ĐÚNG chốt đang muốn đo (khớp bằng từ
khoá). Nếu ai đổi câu chữ trong mô-đun G17, phép khớp gãy và `--tu-kiem` **HỎNG to** — không có
đường nào để nó lặng lẽ ngừng canh.

`--tu-kiem` chạy trên **mười bốn cấu hình tổng hợp**: một cấu hình ĐỦ CHỐT (phải ĐI QUA — đối
chứng dương) và mười ba cấu hình HỎNG, mỗi cái phải bị bắt bởi **ĐÚNG chốt đang muốn đo**. Chỉ
kiểm "có bị từ chối không" thì một ca hỏng vì lý do KHÁC vẫn được tính là đạt.

CHẠY
----
    python3 trien_khai/g18/chot_an_toan.py --tu-kiem
"""
import os
import re
import sys
import tempfile

DU_AN = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOC_APP = os.path.join(DU_AN, "app")
GOC_G17 = os.path.join(DU_AN, "trien_khai", "g17")
if GOC_APP not in sys.path:
    sys.path.insert(0, GOC_APP)


def _nap_g17():
    """Nạp `trien_khai/g17/chot_an_toan.py` theo ĐƯỜNG DẪN, không qua `sys.path`.

    Vì sao không `sys.path.insert(GOC_G17)` rồi `import chot_an_toan`: như thế thì tên mô-đun là
    `chot_an_toan`, và bất kỳ tệp cùng tên nào xuất hiện sớm hơn trên `sys.path` sẽ được nạp thay
    — đúng kiểu hỏng im lặng mà cả dự án đang tránh. Nạp theo đường dẫn thì hoặc đúng tệp, hoặc
    ném lỗi.
    """
    import importlib.util
    duong = os.path.join(GOC_G17, "chot_an_toan.py")
    if not os.path.isfile(duong):
        raise RuntimeError("không thấy chốt an toàn G17 tại %s — G18 KHÔNG chạy khi thiếu nó,"
                           " vì bảy chốt của G17 là điều kiện của lượt này." % duong)
    spec = importlib.util.spec_from_file_location("g17_chot_an_toan", duong)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


G17 = _nap_g17()

# =======================================================================================
# THAM SỐ CỦA G18
# =======================================================================================
# Trần số tiến trình máy chủ. Phép đo cần biết "trần có nhân theo số bản không", mà hai bản đã
# đủ trả lời; bốn là mức cao nhất còn giải thích được. Trần này tồn tại để một lỗi vòng lặp biến
# phép đo thành bộ sinh tiến trình — không phải để tiết kiệm tài nguyên.
TOI_DA_TIEN_TRINH = 4
SO_TIEN_TRINH_MAC_DINH = 2

# Biến môi trường của lượt này. Đặt tên RIÊNG khỏi G17 để một lượt chạy nhầm không mượn được
# giấy phép của lượt kia.
CO_GOI_HANG = "VIP_G18_CHO_PHEP_GOI_HANG"
BIEN_GIAY_PHEP = "VIP_G18_GIAY_PHEP"

# Nền của G18 phải là thư mục con riêng: hai harness chạy song song trên cùng một nền là hai
# tiến trình cùng `migrate` một CSDL — hỏng ngẫu nhiên, và hỏng ở đúng chỗ đang đo.
TEN_NEN = "g18_tai"

# Dấu hiệu của một chuỗi kết nối PostgreSQL. Không phải danh sách đầy đủ (không có danh sách nào
# là đầy đủ) — nó canh ĐÚNG thứ lượt này có thể vô tình mang vào: một biến môi trường sót lại từ
# lượt chạy cụm riêng. Cổng 5432 đang giữ dữ liệu của dự án KHÁC (vip_customs, vip_customs_g16,
# vip_customs_test) — chạm vào là làm hỏng dữ liệu không thuộc về mình.
DAU_HIEU_PG = ("postgres://", "postgresql://", ":5432", "=5432", "5432/",
               "PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD", "DATABASE_URL")
TIEN_TO_BIEN_PG = ("PG", "POSTGRES", "VIP_PG")

# Cách dọn tiến trình bị CẤM. Trên máy nhiều làn, `pkill -f server.py` giết cả máy chủ của làn
# khác — một lệnh dọn tay làm hỏng lượt của người khác, và không có gì báo.
#
# Bộ dò bắt LỜI GỌI, không bắt chữ: mẫu đòi sau từ khoá phải có khoảng trắng rồi một ký tự như
# `-`/tên tệp. Không có ràng buộc ấy thì bộ dò bắt chính cái bảng cấm này và chính câu chú thích
# giải thích vì sao cấm nó — và cách chữa sai là xoá chú thích, tức là xoá đúng chỗ giải thích
# luật này tồn tại.
CACH_DON_CAM = ("pkill", "killall")
MAU_GOI_CACH_DON = re.compile(r"\b(?:%s)\b\s+[-A-Za-z./]" % "|".join(CACH_DON_CAM))

LOOPBACK = ("127.0.0.1", "localhost", "::1")


# =======================================================================================
# NĂM CHỐT RIÊNG CỦA G18
# =======================================================================================
def _so_tien_trinh_hop_le(so_tien_trinh):
    """(ok, ly_do). Số tiến trình phải là số nguyên trong [1, TOI_DA_TIEN_TRINH]."""
    try:
        n = int(so_tien_trinh)
    except (TypeError, ValueError):
        return False, ("số tiến trình máy chủ %r không phải số nguyên — từ chối, vì không đọc"
                       " được thì không được đoán." % (so_tien_trinh,))
    if n < 1:
        return False, "số tiến trình máy chủ = %d — phép đo cần ít nhất một bản. Từ chối." % n
    if n > TOI_DA_TIEN_TRINH:
        return False, ("số tiến trình máy chủ = %d vượt trần %d — vòng lặp tạo tiến trình là thứ"
                       " biến phép đo thành bộ sinh tiến trình. Từ chối."
                       % (n, TOI_DA_TIEN_TRINH))
    return True, ""


def _bind_hop_le(ds_bind):
    """(ok, ly_do). MỌI địa chỉ bind phải là loopback, và danh sách không được rỗng.

    Kiểm TỪNG phần tử chứ không kiểm phần tử đầu: một danh sách `["127.0.0.1", "0.0.0.0"]` có
    phần tử đầu đúng, và nếu chỉ kiểm nó thì tiến trình thứ hai mở cổng ra ngoài mà chốt vẫn xanh.
    """
    ds = [str(x) for x in (ds_bind or [])]
    if not ds:
        return False, "danh sách địa chỉ bind RỖNG — chốt này không canh gì thì phải TỪ CHỐI."
    for i, d in enumerate(ds):
        if d not in LOOPBACK:
            return False, ("địa chỉ bind của tiến trình #%d là %r, không phải loopback (%s) — mở"
                           " cổng ra ngoài là V-G11-01 (CHƯA CẤP). Từ chối."
                           % (i, d, ", ".join(LOOPBACK)))
    return True, ""


def _khong_dinh_postgres(env, duong_csdl=None):
    """(ok, ly_do). Môi trường truyền cho các tiến trình con KHÔNG được trỏ tới PostgreSQL.

    D-8: CSDL nghiệp vụ vẫn là SQLite. PostgreSQL chỉ chạy trên CỤM RIÊNG, và cổng 5432 đang giữ
    dữ liệu của ba cơ sở khác. Một biến môi trường sót lại là đủ để lượt đo này ghi vào đó.
    """
    env = env or {}
    for ten in sorted(env):
        if str(ten).upper() in DAU_HIEU_PG or str(ten).upper().startswith(TIEN_TO_BIEN_PG):
            return False, ("môi trường truyền cho máy chủ có biến %s — D-8: CSDL nghiệp vụ vẫn là"
                           " SQLite, PostgreSQL chỉ trên cụm riêng. Từ chối." % ten)
        gia_tri = str(env[ten] or "")
        for dau in DAU_HIEU_PG:
            if dau in gia_tri:
                return False, ("môi trường truyền cho máy chủ có %s chứa dấu hiệu PostgreSQL (%r)"
                               " — cổng 5432 đang giữ dữ liệu dự án khác. Từ chối."
                               % (ten, dau))
    if duong_csdl and not str(duong_csdl).endswith("hub.db"):
        return False, "đường dẫn CSDL %r không phải SQLite `hub.db`. Từ chối." % duong_csdl
    return True, ""


def quet_cach_don(nguon=None):
    """Tìm `pkill`/`killall` trong mã của làn G18. Trả danh sách (tệp, dòng, từ khoá).

    `nguon` TIÊM ĐƯỢC: `{"ten_tệp": "nội dung"}` để `--tu-kiem` chạy được bộ dò này trên một
    nguồn giả có `pkill` — một bộ dò chưa từng bắt được gì thì chưa chứng minh được gì.
    """
    if nguon is None:
        nguon = {}
        for ten in sorted(os.listdir(os.path.dirname(os.path.abspath(__file__)))):
            if ten.endswith((".py", ".sh")):
                with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), ten),
                          encoding="utf-8", errors="replace") as f:
                    nguon[ten] = f.read()
    thay = []
    for ten in sorted(nguon):
        for so, dong in enumerate(nguon[ten].splitlines(), 1):
            # Bỏ dòng chú thích: chính tệp này VIẾT RA chữ `pkill` để giải thích vì sao cấm nó.
            # Không bỏ thì bộ dò bắt chính tài liệu của mình — và cách chữa sai là xoá chú
            # thích, tức là xoá đúng chỗ giải thích vì sao luật này tồn tại.
            if dong.lstrip().startswith("#"):
                continue
            m = MAU_GOI_CACH_DON.search(dong)
            if m:
                thay.append((ten, so, m.group(0).strip(), dong.strip()[:110]))
    return thay


def _nen_tach_khoi_g17(nen):
    """(ok, ly_do). Nền của G18 phải là thư mục riêng, không trùng nền G17."""
    if not nen:
        return False, "nền trống — chốt này không canh gì thì phải TỪ CHỐI."
    cuoi = os.path.basename(os.path.realpath(nen))
    if "g17" in cuoi:
        return False, ("nền %r nằm trong/trùng nền của G17 — hai harness cùng `migrate` một CSDL"
                       " là hỏng ngẫu nhiên đúng ở chỗ đang đo. Từ chối." % nen)
    if not cuoi.startswith("g18"):
        return False, ("tên nền %r không bắt đầu bằng `g18` — không chứng minh được nó tách khỏi"
                       " nền của làn khác. Từ chối." % cuoi)
    return True, ""


# =======================================================================================
# CHỐT GỌN: bảy chốt G17 + năm chốt G18
# =======================================================================================
def _chot_g17(ly_do):
    """Gán số hiệu chốt G17 cho từng câu lý do, để `--tu-kiem` đòi ĐÚNG chốt.

    Khớp bằng từ khoá là chỗ dễ mục: đổi câu chữ trong mô-đun G17 là phép khớp gãy. Cố ý để nó
    gãy TO — trả nhãn `G17-KHONG-RO` thì ca tự kiểm tương ứng HỎNG và bảng tổng kết nói ra.

    Chốt 5 nhận CẢ HAI tên biến: câu lý do do mô-đun G17 in ra nên nó mang tên biến của G17,
    còn `env` của lượt này mang tên của G18 (xem `_env_cho_g17`).
    """
    for so, dau in ((1, "VIP_HUB_DATA"), (2, "VIP_HUB_BIND"), (3, "CHO_PHEP_LIVE"),
                    (4, "môi trường J&T"), (5, G17.CO_GOI_HANG), (5, CO_GOI_HANG),
                    (6, "loopback"), (7, "giấy phép")):
        if dau in ly_do:
            return "G17-%d" % so
    return "G17-KHONG-RO"


def _env_cho_g17(env):
    """Bản `env` để đưa cho mô-đun G17, có THÊM tên biến của chính G17.

    Vì sao cần: hai làn đặt tên biến khác nhau cho cùng một bất biến ("cờ cho phép gọi hãng",
    "biến khai giấy phép đã cấp"). Gọi thẳng mô-đun G17 mà chỉ truyền tên biến của G18 thì chốt
    ấy **không thấy gì và im lặng cho qua** — đo được ngay ở lượt `--tu-kiem` đầu tiên: ca `F`
    (`VIP_G18_CHO_PHEP_GOI_HANG=1`) bị bỏ lọt, 13/14.

    Đây là chỗ dễ chọn sai: cách chữa nhanh là xoá ca `F` cho bảng xanh. Không. Bất biến là
    "cờ cho phép gọi hãng phải TẮT", không phải "biến có tên đúng chính tả"; nên ánh xạ tên
    được viết ra đây, và ca `F` ở lại.
    """
    ra = dict(env)
    for ten_g18, ten_g17 in ((CO_GOI_HANG, G17.CO_GOI_HANG),
                             (BIEN_GIAY_PHEP, G17.BIEN_GIAY_PHEP)):
        if ten_g18 in env and env.get(ten_g18) not in (None, ""):
            ra[ten_g17] = env[ten_g18]
    return ra


def ly_do_tu_choi(nen, goc_url=None, so_tien_trinh=1, ds_bind=None, env=None,
                  so_dang_ky=None, cho_phep_jt=None, buoc_can_giay_phep=None, giay_phep=None,
                  duong_csdl=None, nguon_ma=None, goc_du_an=None):
    """MƯỜI HAI chốt. Trả danh sách `{"chot", "ly_do"}`; rỗng = chạy được.

    Mọi đầu vào đều TIÊM ĐƯỢC để `--tu-kiem` chạy trên cấu hình tổng hợp mà không phải đổi môi
    trường thật (cùng khuôn với `chot_an_toan.py` của G17 — có lý do: một chốt chỉ kiểm được bằng
    cách đổi môi trường thật thì không kiểm được gì cả).
    """
    env = dict(os.environ if env is None else env)
    ra = []

    # ---- 1..7. BẢY CHỐT CỦA G17 — mượn nguyên, không chép lại
    for x in G17.ly_do_tu_choi(nen, goc_url=goc_url, so_dang_ky=so_dang_ky,
                               cho_phep_jt=cho_phep_jt, env=_env_cho_g17(env),
                               goc_du_an=goc_du_an, buoc_can_giay_phep=buoc_can_giay_phep,
                               giay_phep=giay_phep):
        ra.append({"chot": _chot_g17(x), "ly_do": x})

    # ---- 8. số tiến trình máy chủ
    ok, ly_do = _so_tien_trinh_hop_le(so_tien_trinh)
    if not ok:
        ra.append({"chot": "G18-8", "ly_do": ly_do})

    # ---- 9. địa chỉ bind của TỪNG tiến trình
    ok, ly_do = _bind_hop_le(ds_bind)
    if not ok:
        ra.append({"chot": "G18-9", "ly_do": ly_do})

    # ---- 10. không dính PostgreSQL
    ok, ly_do = _khong_dinh_postgres(env, duong_csdl)
    if not ok:
        ra.append({"chot": "G18-10", "ly_do": ly_do})

    # ---- 11. cấm pkill/killall trong mã của làn này
    for ten, so, tu, dong in quet_cach_don(nguon_ma):
        ra.append({"chot": "G18-11",
                   "ly_do": ("%s dòng %d dùng %r — dọn tiến trình phải theo ĐÚNG PID. Trên máy"
                             " nhiều làn, lệnh này giết cả máy chủ của làn khác: %s"
                             % (ten, so, tu, dong))})

    # ---- 12. nền tách khỏi G17
    ok, ly_do = _nen_tach_khoi_g17(nen)
    if not ok:
        ra.append({"chot": "G18-12", "ly_do": ly_do})

    return ra


def ma_chot(ds):
    """Tập mã chốt đã nổ — để người gọi in ra một dòng thay vì cả danh sách."""
    return sorted({x["chot"] for x in ds})


# =======================================================================================
# TỰ KIỂM BỘ DÒ
# =======================================================================================
class _LopGia(object):
    """Lớp adapter giả cho ca tự kiểm — chỉ cần thuộc tính `CHO_PHEP_LIVE` và `__name__`."""

    def __init__(self, ten, live):
        self.__name__ = ten
        self.CHO_PHEP_LIVE = live


def _nen_tu_kiem(ten):
    return os.path.join(tempfile.gettempdir(), "veh-g18-tu-kiem", ten)


def bo_ca_tu_kiem():
    """(mã, mô tả, phải_từ_chối, chốt_mong_đợi, kwargs) cho `--tu-kiem`.

    Đối chứng DƯƠNG là ca A: cấu hình đủ chốt phải ĐI QUA. Thiếu nó thì một bộ dò
    `return ["từ chối"]` cũng "bắt được" cả mười ba ca hỏng và trông như đang hoạt động.
    """
    nen = _nen_tu_kiem(TEN_NEN)
    dang_ky_an = {"jt": _LopGia("AdapterJT", False), "vtp": _LopGia("AdapterVTP", False)}
    env_an = {"VIP_HUB_DATA": nen}
    khop = {"sandbox": False, "production": False}
    buoc = {"G18-TAI": ("V-G09-01", "V-13906-05")}
    goc = "http://127.0.0.1:0"
    # Ba đầu vào dùng chung cho MỌI ca; mỗi ca chỉ đổi ĐÚNG thứ nó muốn đo.
    chung = dict(nen=nen, goc_url=goc, so_tien_trinh=2, ds_bind=["127.0.0.1", "127.0.0.1"],
                 env=env_an, so_dang_ky=dang_ky_an, cho_phep_jt=khop,
                 buoc_can_giay_phep=buoc, giay_phep=set(),
                 duong_csdl=os.path.join(nen, "hub.db"), nguon_ma={})

    def ca(ma, mo_ta, phai_tu_choi, chot, **doi):
        kw = dict(chung)
        kw.update(doi)
        return (ma, mo_ta, phai_tu_choi, chot, kw)

    return [
        ca("A", "cấu hình ĐỦ CHỐT (đối chứng dương) — phải ĐI QUA", False, None),
        # --- bảy chốt mượn của G17: mỗi ca phải nổ ĐÚNG chốt ấy, không phải chốt nào khác
        ca("B", "nền trỏ vào dữ liệu THẬT", True, "G17-1",
           nen=os.path.join(DU_AN, "app", "du-lieu"),
           env={"VIP_HUB_DATA": os.path.join(DU_AN, "app", "du-lieu")},
           duong_csdl=os.path.join(DU_AN, "app", "du-lieu", "hub.db")),
        ca("C", "VIP_HUB_BIND = 0.0.0.0", True, "G17-2",
           env=dict(env_an, VIP_HUB_BIND="0.0.0.0")),
        ca("D", "một adapter có CHO_PHEP_LIVE = True", True, "G17-3",
           so_dang_ky={"jt": _LopGia("AdapterJT", True)}),
        ca("E", "cổng môi trường SANDBOX của J&T bị MỞ", True, "G17-4",
           cho_phep_jt={"sandbox": True, "production": False}),
        ca("F", "cờ %s bật" % CO_GOI_HANG, True, "G17-5",
           env=dict(env_an, **{CO_GOI_HANG: "1"})),
        ca("G", "đích không phải loopback", True, "G17-6",
           goc_url="http://open.jtexpress.vn:80"),
        ca("H", "biến môi trường KHAI là đã cấp giấy phép gọi hãng", True, "G17-7",
           env=dict(env_an, **{BIEN_GIAY_PHEP: "V-G09-01"}), giay_phep={"V-G09-01"}),
        # --- năm chốt riêng của G18
        ca("I", "số tiến trình vượt trần (%d)" % (TOI_DA_TIEN_TRINH + 1), True, "G18-8",
           so_tien_trinh=TOI_DA_TIEN_TRINH + 1),
        ca("J", "số tiến trình = 0", True, "G18-8", so_tien_trinh=0),
        ca("K", "tiến trình #1 bind 0.0.0.0 (phần tử ĐẦU vẫn đúng)", True, "G18-9",
           ds_bind=["127.0.0.1", "0.0.0.0"]),
        ca("L", "biến môi trường trỏ tới PostgreSQL cổng 5432", True, "G18-10",
           env=dict(env_an, VIP_PG_DSN="postgresql://x@127.0.0.1:5432/vip_customs")),
        ca("M", "mã của làn có `pkill`", True, "G18-11",
           nguon_ma={"gia.sh": "#!/bin/sh\npkill -f server.py\n"}),
        ca("N", "nền G18 trùng nền G17", True, "G18-12",
           nen=_nen_tu_kiem("g17_harness"),
           env={"VIP_HUB_DATA": _nen_tu_kiem("g17_harness")},
           duong_csdl=os.path.join(_nen_tu_kiem("g17_harness"), "hub.db")),
    ]


def tu_kiem(cho_in=True):
    """Chạy bộ dò trên mười bốn cấu hình tổng hợp. Trả `(so_ca, so_hong, danh_sach)`."""
    so_hong, ket_qua = 0, []
    for ma, mo_ta, phai_tu_choi, chot, kw in bo_ca_tu_kiem():
        ly_do = ly_do_tu_choi(**kw)
        bi_tu_choi = bool(ly_do)
        dung_ket_qua = (bi_tu_choi == phai_tu_choi)
        # Ca hỏng phải bị bắt bởi ĐÚNG chốt đang muốn đo — bắt vì lý do khác là ĐO SAI.
        dung_chot = (not phai_tu_choi) or (chot in ma_chot(ly_do))
        dat = dung_ket_qua and dung_chot
        if not dat:
            so_hong += 1
        ket_qua.append({"ma": ma, "mo_ta": mo_ta, "mong_doi_tu_choi": phai_tu_choi,
                        "chot_mong_doi": chot, "thuc_te_tu_choi": bi_tu_choi,
                        "chot_thuc_te": ma_chot(ly_do), "dung_chot": dung_chot, "dat": dat,
                        "ly_do": ly_do[0]["ly_do"] if ly_do else ""})
        if cho_in:
            print("  %s [%s] %s" % ("✓" if dat else "✗", ma, mo_ta))
            if not dat:
                print("        MONG ĐỢI từ chối=%s (chốt %s) · THỰC TẾ=%s (chốt %s)"
                      % (phai_tu_choi, chot, bi_tu_choi, ma_chot(ly_do) or "—"))
            elif ly_do:
                print("        bắt đúng chốt %s: %s" % (ly_do[0]["chot"], ly_do[0]["ly_do"][:100]))
    return len(ket_qua), so_hong, ket_qua


def main(argv):
    if "--tu-kiem" in argv:
        ds = bo_ca_tu_kiem()
        print("═" * 78)
        print("TỰ KIỂM BỘ DÒ CHỐT AN TOÀN G18 — %d cấu hình tổng hợp" % len(ds))
        print("(bảy chốt mượn của G17 + năm chốt riêng của G18)")
        print("═" * 78)
        tong, hong, _ = tu_kiem()
        print("─" * 78)
        print("TỰ KIỂM: %d/%d ca đạt · %d hỏng" % (tong - hong, tong, hong))
        if hong:
            print("BỘ DÒ HỎNG: nó không phân biệt được cấu hình an toàn với cấu hình nguy hiểm,")
            print("hoặc bắt đúng kết quả nhưng vì lý do khác chốt đang muốn đo.")
            print("Mọi lời khai 'harness đã từ chối chạy' ở lượt này KHÔNG có giá trị.")
            return 1
        print("Bộ dò ĐẠT: mọi cấu hình hỏng đều bị bắt bởi ĐÚNG chốt đang muốn đo.")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
