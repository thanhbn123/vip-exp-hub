#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22/AG-04 — CỔNG C5/G7: ĐIỂM VƯỚNG **TÊN TỆP** VÀ **KHUÔN BÁO CÁO**, ĐO HAI CHIỀU.

VÌ SAO CÓ TỆP NÀY
-----------------
Cổng `C5` (`app/thu/thu_qa_g20.py`, AG-01) và cổng `G7` (`app/thu/thu_qa_g21.py`) không đo nội
dung — chúng đếm theo **KHUÔN TÊN**:

    ung_vien = sorted(t for t in os.listdir(GOC_THU) if re.match(r"thu_qa_g19.*\\.py$", t))

Bộ tổng hợp thật của làn AG-04 tên `app/thu/thu_g19_tich_hop.py` nên **không bao giờ** lọt vào
danh sách ứng viên: cổng đo `0/1` dù bộ tổng hợp chạy thật và xanh. Đó là **lỗi đặt tên**, không
phải lỗi sản phẩm — phép đo đúng, chỉ có chỗ nó nhìn là trống.

Lượt trước tôi dựng thử một bản uỷ quyền cùng tên rồi XOÁ, vì khi đó tệp nằm NGOÀI vùng được cấp.
Lượt này AG-00 cấp tường minh `app/thu/thu_qa_g19_tich_hop.py` cho AG-04. Tệp đó là **bản uỷ
quyền MỎNG**: nó chạy bộ gốc và trả về ĐÚNG mã thoát của bộ gốc — không có bản logic thứ hai.

CỔNG NÀY ĐO CÁI GÌ — VÀ ĐO **QUA CHÍNH C5**, KHÔNG QUA RUNNER
-------------------------------------------------------------
Chạy `thu_g19_tich_hop.py` rồi tự khen nó xanh là **vô nghĩa**: đó là đối chứng dương của chính
bộ đo, không phải của cổng C5. Nên mọi phép đo ở đây gọi **CHÍNH PHÉP ĐO CỦA C5** — phương thức
`C4_C5_NoKhac.test_c5_co_bo_thu_g19_tong_hop_chay_duoc` trong tệp AG-01 — và đọc phán quyết của nó:

    B2  CHIỀU XANH: bản uỷ quyền lành ⇒ C5 phải chuyển `1/1` (XANH THẬT).
    B3  CHIỀU ĐỎ  : tiêm lỗi vào BẢN SAO của bản uỷ quyền ⇒ C5 phải ĐỎ LẠI.
                    (a) bộ gốc trả mã khác 0   (b) bộ gốc KHÔNG TỒN TẠI
                    (c) suite RỖNG (`0` ca + `OK` + thoát 0)
                    (d) MỌI CA BỎ QUA — đo cả HAI dạng bỏ qua, xem B4
    B4  LỖ HỔNG ĐO ĐƯỢC: bỏ qua ở mức PHƯƠNG THỨC cho `Ran N tests` với N>0, nên một bộ KHÔNG
                    chạy ca nào vẫn có thể được C5 phán XANH. Đây là phát hiện, KHÔNG phải giả định.
    B5  KHUÔN BÁO CÁO: bộ đếm `chay_tat_ca.sh` lấy `Ran [0-9]+` CUỐI CÙNG; C5 lấy phần tử cuối của
                    `re.findall`. Nên dòng `Ran N` cuối phải là số THẬT — đo bằng một cái bẫy.

PHẠM VI — TUYỆT ĐỐI
-------------------
Không một lời gọi nào ra hãng, kể cả sandbox (`V-G09-01` + `V-13906-05` CHƯA CẤP). Tệp này KHÔNG
mở cổng mạng nào, KHÔNG chạm `:5432` (D-8: CSDL nghiệp vụ vẫn SQLite), KHÔNG push/deploy/tunnel,
KHÔNG mở `CHO_PHEP_LIVE`. Nó chỉ: ĐỌC tệp, chạy TIẾN TRÌNH CON cục bộ, và tạm thay/mở lại đúng
hai tệp trong `app/thu/` (bản uỷ quyền + bản sao tạm của bộ kiểm AG-01) — cả hai đều được TRẢ LẠI
nguyên trạng và kiểm bằng sha256 trong `finally`.

CHẠY
----
    python3 app/thu/thu_g22_gioihan.py        # 0 = ĐẠT · 1 = có HỎNG/KHUYẾT · 9 = chốt an toàn
    sh trien_khai/g21-gioihan/chay_g22.sh     # bản ghi log ra thư mục tạm + in bảng tổng kết

Dòng tổng kết cuối in ra khuôn `<N> ca — ĐẠT` / `<N> ca — HỎNG` — đúng khuôn thứ hai mà bộ đếm
`chay_tat_ca.sh` chấp nhận cho các bộ thử viết tay. Cố ý KHÔNG in dòng `Ran <số> tests` nào ở
phần kết luận: in khống khuôn của `unittest` là làm bộ đếm đọc một con số không do phép đo sinh ra.
"""
import atexit
import hashlib
import os
import re
import shutil
import subprocess
import sys
import time

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # …/app
DU_AN = os.path.dirname(GOC_APP)
GOC_THU = os.path.join(GOC_APP, "thu")
ANH_EM = os.path.dirname(DU_AN)                                            # …/vip-express-hub

BO_GOC = os.path.join("app", "thu", "thu_g19_tich_hop.py")       # MỘT bản logic duy nhất
BO_UY_QUYEN = os.path.join("app", "thu", "thu_qa_g19_tich_hop.py")
QA_G20 = os.path.join("app", "thu", "thu_qa_g20.py")            # tệp của AG-01 — chỉ ĐỌC
CA_C5 = "C4_C5_NoKhac.test_c5_co_bo_thu_g19_tong_hop_chay_duoc"
CA_G7 = "G7_BoG19TongHop.test_g7_co_bo_g19_tong_hop_chay_duoc"
QA_G21 = os.path.join("app", "thu", "thu_qa_g21.py")            # tệp của AG-01 — chỉ ĐỌC
KHUON_C5 = r'thu_qa_g19.*\.py$'

NOI_TIM_QA_G20 = (
    os.path.join(DU_AN, "app", "thu", "thu_qa_g20.py"),                      # nếu AG-01 đã gộp
    os.path.join(ANH_EM, "g20-ag01-qa", "app", "thu", "thu_qa_g20.py"),      # worktree AG-01 G20
    os.path.join(ANH_EM, "g21-ag01-qa", "app", "thu", "thu_qa_g20.py"),      # worktree AG-01 G21
)

DAT, HONG, BO_QUA, KHUYET = "DAT", "HONG", "BO_QUA", "KHUYET"
KY = {DAT: "✓", HONG: "✗", BO_QUA: "–", KHUYET: "!"}
KQ = []
DOI_CHUNG = {}
LENH = []            # (lệnh, mã thoát) — bằng chứng "lệnh thật + mã thoát thật"
GIAY_TOI_DA_C5 = 1500

# ══════════════════════════════════════════════════════════════════════════════════════════════
# HẠ TẦNG
# ══════════════════════════════════════════════════════════════════════════════════════════════

def muc(t):
    print("\n" + "─" * 92)
    print("  " + t)
    print("─" * 92)


def ket(ma, ten, trang_thai, bang_chung="", nhom=None, chieu=None):
    KQ.append({"ma": ma, "ten": ten, "tt": trang_thai, "bc": bang_chung})
    if nhom:
        d = DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})
        if chieu == "am":
            d["am"] += 1
        elif chieu == "duong":
            d["duong"] += 1
    print("  %s %-58s %s" % (KY[trang_thai], ma, ten))
    if bang_chung:
        for d in str(bang_chung).splitlines():
            print("      %s" % d)
    return trang_thai


def _dc_am(nhom):
    DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})["am"] += 1


def _dc_duong(nhom):
    DOI_CHUNG.setdefault(nhom, {"am": 0, "duong": 0})["duong"] += 1


def chay(lenh, gio=600, env=None, cwd=None):
    """Chạy TIẾN TRÌNH THẬT. Trả (mã thoát, output, số giây). Luôn ghi vào sổ LỆNH."""
    e = dict(os.environ)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    # Chốt an toàn: gỡ mọi biến có thể mở đường ra hãng / PostgreSQL / làn đầy đủ.
    for k in ("VIP_THU_POSTGRES", "VIP_G20_DAY_DU", "VIP_G19_DAY_DU", "JT_CHO_PHEP_SANDBOX"):
        e.pop(k, None)
    e.update(env or {})
    t0 = time.time()
    try:
        r = subprocess.run(lenh, capture_output=True, text=True, env=e, timeout=gio,
                           cwd=cwd or DU_AN)
        ma = r.returncode
        ra = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as ex:
        ma = 124
        ra = "[QUÁ HẠN %ss] %s" % (gio, ex.stdout or "")
    giay = time.time() - t0
    LENH.append((" ".join(lenh), ma))
    return ma, ra, giay


def doc(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _ma_khong_chu_thich(p):
    """Mã nguồn ĐÃ GỠ chú thích và chuỗi (dùng `tokenize`) — để bộ dò an toàn không tự bắt mình."""
    import tokenize
    # `FSTRING_*` chỉ có từ Python 3.12; cây này chạy 3.9 nên tra bằng `getattr`, KHÔNG viết
    # thẳng tên — viết thẳng là NỔ trên chính cây đang đo (đã vấp thật một lần).
    bo = {tokenize.COMMENT, tokenize.STRING}
    for _t in ("FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END"):
        if hasattr(tokenize, _t):
            bo.add(getattr(tokenize, _t))
    ra = []
    with open(p, "rb") as f:
        for tok in tokenize.tokenize(f.readline):
            if tok.type in bo:
                continue
            ra.append(tok.string)
    return " ".join(ra)


def _sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B0 — CHỐT AN TOÀN: không hãng · không :5432 · không push · CHO_PHEP_LIVE vẫn đóng
# ══════════════════════════════════════════════════════════════════════════════════════════════

def b0_chot_an_toan():
    muc("B0. CHỐT AN TOÀN — không hãng · không :5432 · không push · `CHO_PHEP_LIVE` vẫn đóng")
    # Quét MÃ ĐÃ GỠ chú thích và chuỗi: chính docstring của tệp này có nhắc `CHO_PHEP_LIVE` và
    # `:5432` để GIẢI THÍCH, nếu quét nguyên văn thì bộ dò tự bắt mình — một đối chứng giả.
    ma = _ma_khong_chu_thich(os.path.abspath(__file__))
    # Chuỗi GIẢ phải chứa ĐỦ CẢ BỐN mẫu, viết đúng hình dạng mà mẫu tìm — không thì "đối chứng
    # dương" chỉ chứng minh được rằng bộ dò khớp được một nửa số mẫu của chính nó.
    gia = ("git push origin main\n"
           "ssh -R 8080:localhost:8080\n"
           "CHO_PHEP_LIVE = True\n"
           "postgres://u@127.0.0.1:5432/db\n")
    self_mau = (r"git\s+push", r"\bssh\s+-R\b", r"CHO_PHEP_LIVE\s*=\s*True", r":5432")
    bat_gia = [m for m in self_mau if re.search(m, gia)]
    than_that = [m for m in self_mau if re.search(m, ma)]
    ket("B0a", "Tệp này KHÔNG push / KHÔNG tunnel / KHÔNG mở `CHO_PHEP_LIVE` / KHÔNG chạm :5432",
        DAT if (len(bat_gia) == len(self_mau) and not than_that) else HONG,
        "bộ dò bắt đủ %d/%d mẫu trên chuỗi GIẢ (đối chứng dương) · trên MÃ của chính tệp này "
        "(đã gỡ chú thích/chuỗi): %s" % (len(bat_gia), len(self_mau), than_that or "KHÔNG CÓ"),
        nhom="chot-an-toan", chieu="am")
    _dc_duong("chot-an-toan")
    # Mọi tiến trình con đều bị GỠ `VIP_THU_POSTGRES` (D-8) — kiểm bằng một tiến trình thật.
    ma, ra, _ = chay([sys.executable, "-c",
                      "import os;print('VIP_THU_POSTGRES=' + repr(os.environ.get('VIP_THU_POSTGRES')))"])
    ket("B0b", "`VIP_THU_POSTGRES` bị GỠ khỏi môi trường tiến trình con (D-8: không PostgreSQL)",
        DAT if (ma == 0 and "VIP_THU_POSTGRES=None" in ra) else HONG,
        "$ python3 -c …  →  mã thoát %d · %s" % (ma, ra.strip().splitlines()[-1:] or ""))
    print("  Phạm vi ĐO: chỉ tệp trong cây + tiến trình con cục bộ. KHÔNG mở socket nào.")
    return True


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B1 — BỘ ĐẾM THẬT CỦA C5/G7: ĐỌC TỪ CHÍNH MÃ NGUỒN AG-01, RỒI CHẠY NÓ TRÊN CÂY THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _tim_qa_g20():
    for p in NOI_TIM_QA_G20:
        if os.path.isfile(p):
            return p
    return None


def b1_bo_dem_that():
    muc("B1. BỘ ĐẾM THẬT CỦA C5/G7 — đọc từ mã nguồn AG-01, không suy diễn")
    nguon = _tim_qa_g20()
    if not nguon:
        ket("B1a", "Tìm được bộ kiểm AG-01 (`thu_qa_g20.py`) để ĐỌC bộ đếm", KHUYET,
            "đã thử: %s" % list(NOI_TIM_QA_G20))
        return None, None
    print("  nguồn bộ kiểm AG-01 (chỉ ĐỌC): %s" % nguon)
    print("  sha256: %s" % _sha(nguon)[:32])
    than = doc(nguon)
    dong = [l.strip() for l in than.splitlines()
            if "re.match(" in l and "thu_qa_g19" in l]
    ket("B1a", "Bộ đếm của C5 dùng KHUÔN TÊN `%s` trên `os.listdir(app/thu)`" % KHUON_C5,
        DAT if len(dong) >= 1 else HONG,
        "dòng nguồn đọc được: %s" % (dong[:2] or "KHÔNG THẤY"))
    rx = re.compile(KHUON_C5)
    that = sorted(t for t in os.listdir(GOC_THU) if os.path.isfile(os.path.join(GOC_THU, t)))
    ung_vien = [t for t in that if rx.match(t)]
    print("  ứng viên C5 thấy trên cây này (%d): %s" % (len(ung_vien), ung_vien))
    uy = os.path.basename(BO_UY_QUYEN)
    goc = os.path.basename(BO_GOC)
    ket("B1b", "Bản uỷ quyền `%s` NẰM TRONG danh sách ứng viên của C5" % uy,
        DAT if uy in ung_vien else HONG,
        "ứng viên: %s" % ung_vien, nhom="khuon-ten", chieu="duong")
    ket("B1c", "Bộ gốc `%s` KHÔNG khớp khuôn (đây chính là điểm vướng đã đo ở lượt trước)" % goc,
        DAT if goc not in ung_vien else HONG,
        "`re.match(r'%s', '%s')` → %s" % (KHUON_C5, goc, bool(rx.match(goc))),
        nhom="khuon-ten", chieu="am")
    _dc_duong("khuon-ten")
    return nguon, ung_vien


# ══════════════════════════════════════════════════════════════════════════════════════════════
# HẠ TẦNG CHO B2–B4: MƯỢN BẢN SAO CỦA BỘ KIỂM AG-01, VÀ TIÊM LỖI VÀO BẢN SAO UỶ QUYỀN
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _dat_ban_sao_qa_g20(nguon):
    """Chép `thu_qa_g20.py` vào `app/thu/` để C5 chạy được, và TRẢ LẠI cờ để dọn."""
    dich = os.path.join(DU_AN, QA_G20)
    if os.path.isfile(dich):
        return False                       # đã có sẵn (AG-01 đã gộp) — KHÔNG được xoá của người ta
    shutil.copyfile(nguon, dich)
    return True


def _don_ban_sao_qa_g20(da_chep):
    if not da_chep:
        return
    dich = os.path.join(DU_AN, QA_G20)
    if os.path.isfile(dich):
        os.remove(dich)
    con = os.path.isfile(dich)
    print("  [dọn] bản sao `%s` còn lại: %s" % (QA_G20, con))
    assert not con, "bản sao tạm của bộ kiểm AG-01 KHÔNG bị xoá ⇒ để lại rác cho cây"


def _chay_c5(ca=CA_C5, gio=GIAY_TOI_DA_C5):
    """Chạy CHÍNH phương thức của cổng C5 (hoặc G7) trong tệp AG-01."""
    tep = QA_G20 if ca == CA_C5 else QA_G21
    return chay([sys.executable, os.path.join(DU_AN, tep), ca], gio=gio,
                env={"VIP_G20_CHE_DO": "gop", "VIP_G22_LONG_NHAU": "1"})


def _phan_quyet_c5(ra):
    """Đọc phán quyết C5 TỪ OUTPUT THẬT của nó: (xanh?, tỷ lệ, câu in ra)."""
    m = re.search(r"CHẠY THẬT[^\n]*?(\d+)/(\d+)", ra)
    ty = (int(m.group(1)), int(m.group(2))) if m else None
    # Lấy NGUYÊN VĂN dòng `[C5]`/`[G7]` — đó mới là câu cổng AG-01 tự in ra, không phải mô tả ca.
    m2 = re.search(r"\[(?:C5|G7)\][^\n]*", ra)
    dong = m2.group(0).strip() if m2 else "(KHÔNG thấy dòng `[C5]`/`[G7]` trong output — bộ đọc MÙ)"
    return (ty is not None and ty[0] >= 1), ty, dong


# ── ba (bốn) phép tiêm lỗi, mỗi phép ĐÚNG MỘT DÒNG ────────────────────────────────────────────
DONG_BO_THU = 'BO_THU = os.path.join("app", "thu", "thu_g19_tich_hop.py")'
DONG_LENH = '    return [sys.executable, "-u", BO_THU]'

TIEM = {
    # (a) bộ gốc chạy nhưng trả mã KHÁC 0
    "a_bo_goc_tra_ma_khac_0": (
        DONG_LENH, '    return [sys.executable, "-c", "import sys; sys.exit(7)"]'),
    # (b) bộ gốc KHÔNG TỒN TẠI  ⇒ bản uỷ quyền phải trả 127 + nói rõ KHÔNG CHẠY ĐƯỢC
    "b_bo_goc_khong_ton_tai": (
        DONG_BO_THU,
        'BO_THU = os.path.join("app", "thu", "thu_g19_khong_ton_tai_GIA.py")'),
    # (c) suite RỖNG: 0 ca + OK + thoát 0 — dạng "xanh giả" cổ điển
    "c_suite_rong_0_ca": (
        DONG_LENH,
        '    return [sys.executable, "-c", "import unittest; '
        'unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite())"]'),
    # (d) MỌI CA BỎ QUA ở mức PHƯƠNG THỨC (unittest in `Ran N tests` + `OK (skipped=N)`)
    "d_moi_ca_bo_qua_phuong_thuc": (
        DONG_LENH,
        '    return [sys.executable, "-c", "import unittest; '
        "T=type('T',(unittest.TestCase,),{"
        "'test_a':unittest.skip('x')(lambda s:None),"
        "'test_b':unittest.skip('x')(lambda s:None),"
        "'test_c':unittest.skip('x')(lambda s:None)}); "
        'unittest.TextTestRunner(verbosity=1).run('
        'unittest.TestLoader().loadTestsFromTestCase(T))"]'),
    # (d') MỌI CA BỎ QUA ở mức MÔ-ĐUN (setUpModule ném SkipTest) — dạng `thu_qa_g19.py` đang có.
    #
    # VÁ: bản đầu của phép tiêm này SAI và tôi đã đo ra cái sai đó. Nó gán `setUpModule` lên
    # CLASS rồi gọi `loadTestsFromTestCase` — nhưng `unittest` chỉ chạy mô-đun-fixture qua
    # `loadTestsFromModule`, nên phép tiêm KHÔNG bỏ qua ca nào: đo lại được `Ran 1 test` + `OK`,
    # tức ca vẫn CHẠY. Kết quả khi đó (C5 xanh) là do PHÉP TIÊM hỏng, KHÔNG phải lỗ hổng của C5 —
    # ghi nhầm nó thành lỗ hổng của AG-01 là vu oan. Bản dưới đây mới đúng khuôn bỏ qua mức mô-đun.
    "d2_moi_ca_bo_qua_module": (
        DONG_LENH,
        '    return [sys.executable, "-c", "import unittest,sys; '
        "setUpModule=(lambda: (_ for _ in ()).throw(unittest.SkipTest('x'))); "
        "T=type('T',(unittest.TestCase,),{'test_a':lambda s:None}); "
        "T.__module__='__main__'; "
        'unittest.TextTestRunner(verbosity=1).run('
        "unittest.TestLoader().loadTestsFromModule(sys.modules['__main__']))\"]"),
}


_GOC_DANG_GIU = []          # (đường dẫn, nội dung gốc) — để `atexit` trả lại nếu có sự cố


def _tra_lai_khi_thoat():
    """Chốt cuối: dù có NỔ giữa chừng, bản uỷ quyền vẫn được trả về nguyên trạng."""
    while _GOC_DANG_GIU:
        duong, goc = _GOC_DANG_GIU.pop()
        try:
            with open(duong, "wb") as f:
                f.write(goc)
        except OSError:
            pass


atexit.register(_tra_lai_khi_thoat)


def _tiem(ten):
    """Ghi BẢN SAO đã tiêm lỗi lên đường dẫn thật. Trả (nội dung gốc, sha gốc, mô tả tiêm)."""
    goc = open(os.path.join(DU_AN, BO_UY_QUYEN), "rb").read()
    than = goc.decode("utf-8")
    cu, moi = TIEM[ten]
    n = than.count(cu)
    assert n == 1, "khuôn tiêm phải xuất hiện ĐÚNG MỘT lần, thấy %d: %r" % (n, cu)
    than_moi = than.replace(cu, moi)
    khac = [(a, b) for a, b in zip(than.splitlines(), than_moi.splitlines()) if a != b]
    assert len(khac) == 1, "phép tiêm phải ĐƠN NHÂN — thấy %d dòng khác" % len(khac)
    with open(os.path.join(DU_AN, BO_UY_QUYEN), "w", encoding="utf-8") as f:
        f.write(than_moi)
    _GOC_DANG_GIU.append((os.path.join(DU_AN, BO_UY_QUYEN), goc))
    return goc, khac[0]


def _khoi_phuc(goc):
    with open(os.path.join(DU_AN, BO_UY_QUYEN), "wb") as f:
        f.write(goc)
    if _GOC_DANG_GIU:
        _GOC_DANG_GIU.pop()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B2 — CHIỀU XANH: BẢN UỶ QUYỀN LÀNH ⇒ C5 PHẢI CHUYỂN `1/1`
# ══════════════════════════════════════════════════════════════════════════════════════════════

def b2_chieu_xanh(nguon):
    muc("B2. CHIỀU XANH — C5 chạy THẬT. Lượt TRƯỚC đo `0/1` (chỉ `thu_qa_g19.py` khớp tên, và nó "
        "tự bỏ qua). Nay bản uỷ quyền thành ứng viên thứ HAI, nên tỷ lệ ĐÚNG phải là `1/2`.")
    da_chep = _dat_ban_sao_qa_g20(nguon)
    try:
        goc = open(os.path.join(DU_AN, BO_UY_QUYEN), "rb").read()
        sha0 = hashlib.sha256(goc).hexdigest()
        ma, ra, giay = _chay_c5()
        xanh, ty, dong = _phan_quyet_c5(ra)
        print("  $ python3 %s %s   →  mã thoát %d · %.1f giây" % (QA_G20, CA_C5, ma, giay))
        print("  %s" % dong)
        # Lưu ý: `ung_vien` gồm CẢ `thu_qa_g19.py` (của AG-01, tự bỏ qua ⇒ 0 ca) LẪN bản uỷ
        # quyền, nên tỷ lệ đúng là `1/2` chứ không phải `1/1`. Điều kiện là TỬ SỐ >= 1.
        ket("B2", "C5 phán XANH THẬT với bản uỷ quyền lành (`%s`)" % (ty,),
            DAT if (ma == 0 and xanh) else HONG,
            "mã thoát %d · phán quyết %s · dòng C5: %s" % (ma, ty, dong),
            nhom="c5-chieu-xanh", chieu="duong")
        _dc_am("c5-chieu-xanh")     # đối chứng âm của nhóm này nằm ở B3
        assert hashlib.sha256(open(os.path.join(DU_AN, BO_UY_QUYEN), "rb").read()).hexdigest() \
            == sha0, "bản uỷ quyền bị đổi trong lượt đo XANH"
        return ty
    finally:
        _don_ban_sao_qa_g20(da_chep)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B3+B4 — CHIỀU ĐỎ: TIÊM LỖI VÀO BẢN SAO ⇒ C5 PHẢI ĐỎ LẠI (ĐO QUA CHÍNH C5)
# ══════════════════════════════════════════════════════════════════════════════════════════════

def b3_chieu_do(nguon):
    muc("B3/B4. CHIỀU ĐỎ — tiêm lỗi vào BẢN SAO của bản uỷ quyền, ĐO QUA CHÍNH C5")
    print("  Mỗi phép tiêm ĐÚNG MỘT DÒNG. Bản gốc được giữ trong bộ nhớ và TRẢ LẠI trong `finally`,")
    print("  rồi đối chiếu sha256. Không phép tiêm nào chạm vào bộ gốc `%s`." % BO_GOC)
    da_chep = _dat_ban_sao_qa_g20(nguon)
    that_bai = []
    try:
        truoc = _sha(os.path.join(DU_AN, BO_UY_QUYEN))
        for ten in TIEM:
            goc, khac = _tiem(ten)
            try:
                ma, ra, giay = _chay_c5()
                xanh, ty, dong = _phan_quyet_c5(ra)
                do_that = (not xanh) or ma != 0
                # (d) và (d') là hai dạng "mọi ca BỎ QUA": C5 PHẢI ĐỎ. Nếu C5 vẫn XANH thì đó là
                # LỖ HỔNG CỦA C5 — ghi thành KHUYET kèm bằng chứng, KHÔNG hoà vào HONG cho dễ đọc.
                if ten.startswith("d") and xanh and ma == 0:
                    ket("B3." + ten, "C5 PHẢI ĐỎ khi mọi ca BỎ QUA — đo được: %s" % (ty,), KHUYET,
                        "tiêm: %s\n     →  %s\n     C5 vẫn XANH (%s) dù bộ KHÔNG chạy ca nào: "
                        "bộ đếm C5 chỉ đòi mã thoát 0 + `Ran N` > 0, KHÔNG trừ `skipped=N`."
                        % (khac[1].strip()[:90], dong, ty))
                else:
                    ket("B3." + ten, "C5 ĐỎ LẠI khi bản uỷ quyền bị tiêm lỗi (%s)" % ten,
                        DAT if do_that else HONG,
                        "tiêm 1 dòng: %s\n     →  mã thoát %d · %.1f giây · %s"
                        % (khac[1].strip()[:90], ma, giay, dong),
                        nhom="c5-chieu-do", chieu="am")
                if not do_that and not ten.startswith("d"):
                    that_bai.append(ten)
            finally:
                _khoi_phuc(goc)
                assert _sha(os.path.join(DU_AN, BO_UY_QUYEN)) == truoc, \
                    "KHÔI PHỤC THẤT BẠI sau phép tiêm %s" % ten
        _dc_duong("c5-chieu-do")
    finally:
        _don_ban_sao_qa_g20(da_chep)
    return that_bai


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B5 — KHUÔN BÁO CÁO: BỘ ĐẾM LẤY DÒNG `Ran N` CUỐI, NÊN DÒNG CUỐI PHẢI LÀ SỐ THẬT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _dem_nhu_chay_tat_ca(than):
    """BẢN SAO TRUNG THÀNH của hai phép `grep` trong `app/thu/chay_tat_ca.sh`."""
    m = re.findall(r"Ran [0-9]+", than)
    if m:
        return int(m[-1].split()[1]), "khuôn 1: `Ran [0-9]+` (lần CUỐI)"
    m = re.findall(r"[0-9]+ ca — ĐẠT", than)
    if m:
        return int(m[-1].split()[0]), "khuôn 2: `N ca — ĐẠT` (lần CUỐI)"
    return 0, "không khớp khuôn nào"


def b5_khuon_bao_cao():
    muc("B5. KHUÔN BÁO CÁO — bộ đếm lấy dòng CUỐI, nên dòng cuối phải là con số THẬT")
    # ĐỐI CHỨNG ÂM: một cái bẫy. Output đúng, rồi dòng `Ran 0` in SAU ⇒ bộ đếm đọc 0.
    bay = "Ran 12 tests\nOK\n... phần thân ...\nRan 0 tests\n"
    n, nguon = _dem_nhu_chay_tat_ca(bay)
    ket("B5a", "Bộ đếm QUẢ THẬT mù được bởi một dòng `Ran` in SAU (bẫy: 12 ca ⇒ đọc ra %d)" % n,
        DAT if n == 0 else HONG,
        "chuỗi bẫy có 2 dòng khuôn; đọc ra %d bằng %s ⇒ khuôn báo cáo PHẢI canh thứ tự" % (n, nguon),
        nhom="khuon-bao-cao", chieu="am")
    # ĐỐI CHỨNG DƯƠNG: cùng bộ đếm, output sạch ⇒ đọc ĐÚNG.
    n2, _ = _dem_nhu_chay_tat_ca("Ran 12 tests\nOK\n")
    ket("B5b", "Cùng bộ đếm, output SẠCH ⇒ đọc ĐÚNG 12 ca (đối chứng dương của B5a)",
        DAT if n2 == 12 else HONG, "đọc ra %d" % n2, nhom="khuon-bao-cao", chieu="duong")
    # ĐO THẬT hai tệp của làn này.
    for ten in (BO_GOC, BO_UY_QUYEN):
        p = os.path.join(DU_AN, ten)
        ma, ra, giay = chay([sys.executable, "-u", p], gio=GIAY_TOI_DA_C5,
                            env={"VIP_G22_LONG_NHAU": "1"})
        n, nguon = _dem_nhu_chay_tat_ca(ra)
        co_ok = bool(re.search(r"^OK( |$)", ra, re.M) or re.search(r"ca — ĐẠT", ra))
        # Dòng CUỐI phải là số thật: khẳng định không có `Ran <số>` nào nằm SAU lần khớp cuối.
        print("  %-34s mã thoát %-4d %6.1fs · bộ đếm đọc %d ca (%s) · dấu vết OK=%s"
              % (ten, ma, giay, n, nguon, co_ok))
        ket("B5." + os.path.basename(ten), "`%s`: bộ đếm đọc được %d ca · thoát %d"
            % (os.path.basename(ten), n, ma),
            DAT if (ma == 0 and n > 0 and co_ok) else HONG,
            "đo bằng chính hai `grep` của `chay_tat_ca.sh` (chép trung thành) · %s" % nguon)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B6 — SỔ ĐỐI CHỨNG + TỔNG KẾT
# ══════════════════════════════════════════════════════════════════════════════════════════════

def b6_tong_ket(giay):
    muc("B6. SỔ ĐỐI CHỨNG + TỔNG KẾT")
    thieu = {k: v for k, v in DOI_CHUNG.items() if v["am"] and not v["duong"]}
    for k in sorted(DOI_CHUNG):
        v = DOI_CHUNG[k]
        print("  [sổ] %-20s âm=%d dương=%d" % (k, v["am"], v["duong"]))
    ket("B6a", "Mọi nhóm ca ÂM đều có ca DƯƠNG (chốt (b) của làn AG-04)",
        DAT if not thieu else HONG, "nhóm thiếu dương: %s" % (thieu or "KHÔNG CÓ"))
    so = {DAT: 0, HONG: 0, BO_QUA: 0, KHUYET: 0}
    for k in KQ:
        so[k["tt"]] += 1
    print("\n  BẰNG CHỨNG 'LỆNH THẬT + MÃ THOÁT THẬT' (%d lượt, gộp lệnh trùng):" % len(LENH))
    for lenh, ma in sorted({(l, m) for l, m in LENH}):
        print("    mã thoát %-4d ← %s" % (ma, lenh[:150]))
    print("\n  ca ĐẠT=%d · HỎNG=%d · BỎ QUA=%d · KHUYẾT=%d · TỔNG=%d"
          % (so[DAT], so[HONG], so[BO_QUA], so[KHUYET], len(KQ)))
    for k in KQ:
        if k["tt"] in (HONG, KHUYET):
            print("  %s %s — %s" % (KY[k["tt"]], k["ma"], k["ten"]))
    print("  thời gian: %.1f giây" % giay)
    # Dòng CUỐI là khuôn thứ hai mà `chay_tat_ca.sh` chấp nhận cho bộ thử viết tay.
    if so[HONG] or so[KHUYET]:
        print("  TỔNG: %d ca — HỎNG (ĐẠT=%d · HỎNG=%d · KHUYẾT=%d)"
              % (len(KQ), so[DAT], so[HONG], so[KHUYET]))
    else:
        print("  TỔNG: %d ca — ĐẠT" % len(KQ))
    return so


def main():
    t0 = time.time()
    print("=" * 92)
    print("  G22/AG-04 — CỔNG C5/G7: ĐIỂM VƯỚNG TÊN TỆP VÀ KHUÔN BÁO CÁO, ĐO HAI CHIỀU")
    print("  cây : %s" % DU_AN)
    print("  bộ gốc (MỘT bản logic) : %s" % BO_GOC)
    print("  bản uỷ quyền (tên khớp) : %s" % BO_UY_QUYEN)
    print("=" * 92)

    b0_chot_an_toan()

    # CHỐT CHỐNG ĐỆ QUY: cổng này gọi CHÍNH C5, mà C5 lại gọi bản uỷ quyền → bộ gốc. Nếu bộ gốc
    # (hoặc runner của nó) lỡ gọi lại cổng này thì phải DỪNG ở đây, không được đệ quy vô hạn.
    if os.environ.get("VIP_G22_LONG_NHAU"):
        muc("B1–B5. BỎ QUA — CỔNG NÀY ĐANG ĐƯỢC GỌI LỒNG BÊN TRONG CHÍNH PHÉP ĐO CỦA NÓ")
        ket("B.long", "Phát hiện gọi LỒNG NHAU (`VIP_G22_LONG_NHAU=1`) — không đệ quy", BO_QUA,
            "đây là chốt chống đệ quy, KHÔNG phải một phép đo đạt; lượt chạy NGOÀI mới có phán quyết")
        nguon, _ = _tim_qa_g20(), None
        b1_bo_dem_that()
    else:
        nguon, _ = b1_bo_dem_that()
        if nguon:
            b2_chieu_xanh(nguon)
            b3_chieu_do(nguon)
        b5_khuon_bao_cao()

    so = b6_tong_ket(time.time() - t0)
    return 1 if (so[HONG] or so[KHUYET]) else 0


if __name__ == "__main__":
    sys.exit(main())
