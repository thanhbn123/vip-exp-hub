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
    sh trien_khai/g21-gioihan/chay_hopdong.sh # khối B7 trên HAI cây (đối chứng âm/dương)

KHỐI B7 — HỢP ĐỒNG TENANT + PHỦ TUYẾN + PHÂN TRANG (lượt AG-04 mới)
------------------------------------------------------------------
Hợp đồng §1 của AG-02 (`docs/G22_TRUYVAN.md`) là một TỜ KHAI; B7 là phép đo GHIM ĐÚNG mã trạng
thái của nó trên **fixture SQLite TẠM** với **hai tenant A và B** (không dữ liệu thật, không
migration CSDL nghiệp vụ — D-8):

    · A đọc dữ liệu của A          ⇒ **đúng 200** + đúng bảng khoá §1.5 + trang mặc định 50.
    · B gửi `tenant_id=<A>`        ⇒ **đúng 400** (hợp đồng §1.4: KHÔNG có đường nào để client
      chọn tenant). `assertIn(200, 400)` bị BÁC BỎ: 200 nghĩa là máy chủ bỏ qua im lặng.
    · B lọc `ma_don`/`q` của A     ⇒ 200 nhưng thân RỖNG — kiểm CẢ THÂN, không chỉ mã.
    · Đối chứng DƯƠNG của mỗi vế âm: chính A lọc cùng tham số ⇒ thấy đúng đơn của mình.
    · Phân trang: mặc định 50 · trần 500 bị KẸP · trang 2 RỜI trang 1 (giao hai tập = rỗng).
    · Phủ tuyến: MỌI tuyến `/api/v2/don*` được dò bằng HTTP thật với **bộ đếm cắm trong chính
      tiến trình máy chủ**; tuyến nào KHÔNG đi qua `truy_van.chay()` được in rõ là **LỖ HỔNG**.
      Nếu KHÔNG tuyến nào đi qua ⇒ KHUYẾT: "hợp đồng §1 chưa được cắm vào cây này" — cây thiếu
      tuyến, không phải phép đo sai.

ĐO TRÊN CÂY KHÁC (chỉ ĐỌC, để lấy đối chứng dương của B7):
    VIP_G22_CAY_APP=/đường/dẫn/cây-khác/app python3 app/thu/thu_g22_gioihan.py
Khi biến ấy được đặt, B1–B5 (C5/G7) tự BỎ QUA có ghi lý do, và `PYTHONDONTWRITEBYTECODE=1` giữ
cho cây kia không bị rơi `__pycache__`.

Dòng tổng kết cuối in ra khuôn `<N> ca — ĐẠT` / `<N> ca — HỎNG` — đúng khuôn thứ hai mà bộ đếm
`chay_tat_ca.sh` chấp nhận cho các bộ thử viết tay. Cố ý KHÔNG in dòng `Ran <số> tests` nào ở
phần kết luận: in khống khuôn của `unittest` là làm bộ đếm đọc một con số không do phép đo sinh ra.
"""
import atexit
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request

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
    try:
        shutil.copyfile(nguon, dich)
    except OSError as e:
        # Đã vấp THẬT: hai lượt chạy ĐỒNG THỜI trên cùng một cây tranh nhau tệp mượn này — lượt
        # kia chép vào rồi xoá, lượt này tới muộn thì nguồn biến mất. Nói RÕ nguyên nhân thay vì
        # để một `FileNotFoundError` trần làm chết cả cổng trước khi tới các khối đo khác.
        try:
            if os.path.exists(dich):
                os.remove(dich)            # không để lại bản sao DỞ trên cây nguồn
        except OSError:
            pass
        raise LoiMuonBanSao(
            "KHÔNG mượn được bản sao bộ kiểm AG-01: %s ← %s (%s). Nguyên nhân thường gặp: một "
            "lượt chạy KHÁC của cổng này đang giữ/xoá cùng tệp trên cùng một cây." % (dich, nguon, e))
    return True


class LoiMuonBanSao(RuntimeError):
    """Không mượn được bản sao bộ kiểm AG-01 — chuyện của MÔI TRƯỜNG chạy, không phải của phép đo."""


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


# ── CÔ LẬP DANH SÁCH ỨNG VIÊN C5 ─────────────────────────────────────────────────────────────
#
# HỢP ĐỒNG ĐO ĐƯỢC CỦA C5 (đọc trong `app/thu/thu_qa_g20.py`, KHÔNG sửa tệp đó):
#     `chay = min(Σ(ứng viên chạy thật & thoát 0), 1)`  ⇒  C5 = OR trên danh sách ứng viên.
# Vì vậy với HAI ứng viên, tiêm lỗi vào MỘT ứng viên rồi thấy `1/2 · DONG` là ĐÚNG hợp đồng
# OR, không phải bằng chứng "C5 bắt được lỗi". Muốn đo CHIỀU ĐỎ của C5, phải làm cho MỌI ứng
# viên đều hỏng — hoặc cô lập danh sách còn ĐÚNG MỘT ứng viên rồi tiêm vào nó. Fixture này chọn
# cách thứ hai: tạm đưa `thu_qa_g19.py` (ứng viên không phải bản uỷ quyền) ra khỏi khuôn tên
# `thu_qa_g19*.py`, chạy các phép tiêm, rồi TRẢ LẠI và đối chiếu sự tồn tại. Không sửa nội dung
# của bất kỳ tệp nào trong bước cô lập.
UNG_VIEN_C5_KHONG_UY_QUYEN = os.path.join("app", "thu", "thu_qa_g19.py")
_CACH_LY_C5 = []            # (đường gốc, đường tạm) — để `atexit` trả lại nếu có sự cố


def _phuc_hoi_cach_ly_cu():
    """Dọn dấu vết cô lập của một lượt trước bị chết giữa chừng (nếu có)."""
    goc = os.path.join(DU_AN, UNG_VIEN_C5_KHONG_UY_QUYEN)
    tam = goc + ".r3-c5-cach-ly"
    if not os.path.isfile(tam):
        return
    assert not os.path.exists(goc), \
        "có CẢ %s lẫn bản cách ly %s — không đoán bản nào đúng" % (goc, tam)
    os.replace(tam, goc)


def _tra_lai_cach_ly_khi_thoat():
    while _CACH_LY_C5:
        goc, tam = _CACH_LY_C5.pop()
        try:
            if os.path.isfile(tam) and not os.path.exists(goc):
                os.replace(tam, goc)
        except OSError:
            pass


atexit.register(_tra_lai_cach_ly_khi_thoat)


def _cach_ly_ung_vien_c5():
    """Tạm đưa ứng viên KHÔNG phải bản uỷ quyền ra khỏi khuôn tên C5. Trả cờ để trả lại."""
    goc = os.path.join(DU_AN, UNG_VIEN_C5_KHONG_UY_QUYEN)
    if not os.path.isfile(goc):
        return None
    tam = goc + ".r3-c5-cach-ly"
    assert not os.path.exists(tam), "đã có bản cách ly cũ: %s" % tam
    os.replace(goc, tam)
    _CACH_LY_C5.append((goc, tam))
    return goc, tam


def _tra_lai_ung_vien_c5(giu):
    if not giu:
        return
    goc, tam = giu
    assert os.path.isfile(tam), "mất bản cách ly: %s" % tam
    os.replace(tam, goc)
    if _CACH_LY_C5:
        _CACH_LY_C5.pop()
    assert os.path.isfile(goc) and not os.path.exists(tam), \
        "KHÔNG trả lại được ứng viên C5: %s" % goc


# ══════════════════════════════════════════════════════════════════════════════════════════════
# B2 — CHIỀU XANH: BẢN UỶ QUYỀN LÀNH ⇒ C5 PHẢI CHUYỂN `1/1`
# ══════════════════════════════════════════════════════════════════════════════════════════════

def b2_chieu_xanh(nguon):
    muc("B2. CHIỀU XANH — C5 chạy THẬT. Lượt TRƯỚC đo `0/1` (chỉ `thu_qa_g19.py` khớp tên, và nó "
        "tự bỏ qua). Nay bản uỷ quyền thành ứng viên thứ HAI, nên tỷ lệ ĐÚNG phải là `1/2`.")
    _phuc_hoi_cach_ly_cu()
    da_chep = _dat_ban_sao_qa_g20(nguon)
    try:
        goc = open(os.path.join(DU_AN, BO_UY_QUYEN), "rb").read()
        sha0 = hashlib.sha256(goc).hexdigest()
        ma, ra, giay = _chay_c5()
        xanh, ty, dong = _phan_quyet_c5(ra)
        print("  $ python3 %s %s   →  mã thoát %d · %.1f giây" % (QA_G20, CA_C5, ma, giay))
        print("  %s" % dong)
        # HỢP ĐỒNG OR: C5 chỉ đòi TỬ SỐ >= 1. Với hai ứng viên, một ứng viên còn xanh là đủ để
        # cổng xanh. Vì thế `1/2` ở đây chỉ là ĐỐI CHỨNG DƯƠNG của hợp đồng OR — nó KHÔNG chứng
        # minh C5 bắt được lỗi trong bản uỷ quyền. Chiều ĐỎ được đo ở B3 sau khi cô lập fixture.
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
    print("  HỢP ĐỒNG C5 = OR: `chay = min(Σ ứng viên chạy thật & thoát 0, 1)`. Vì vậy một ứng")
    print("  viên còn xanh là đủ làm cổng xanh (B2 đo đúng `1/2`). Để đo CHIỀU ĐỎ, fixture CÔ LẬP")
    print("  danh sách còn đúng bản uỷ quyền trước khi tiêm; trả lại sau `finally`.")
    _phuc_hoi_cach_ly_cu()
    da_chep = _dat_ban_sao_qa_g20(nguon)
    that_bai = []
    giu = None
    try:
        truoc = _sha(os.path.join(DU_AN, BO_UY_QUYEN))
        giu = _cach_ly_ung_vien_c5()
        con_lai = sorted(t for t in os.listdir(GOC_THU)
                         if re.match(r"thu_qa_g19.*\.py$", t))
        print("  [C5] ứng viên sau cô lập: %s" % con_lai)
        assert con_lai == [os.path.basename(BO_UY_QUYEN)], \
            "cô lập C5 thất bại — còn ứng viên khác: %s" % con_lai
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
        _tra_lai_ung_vien_c5(giu)
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
# B7 — HỢP ĐỒNG TENANT + PHỦ TUYẾN + PHÂN TRANG, ĐO TRÊN FIXTURE SQLITE **TẠM** (HAI TENANT A/B)
#
# VÌ SAO CÓ KHỐI NÀY
# ------------------
# Hợp đồng §1 của AG-02 (`docs/G22_TRUYVAN.md`) là một TỜ KHAI. Tờ khai chỉ có giá trị khi có
# phép đo GHIM ĐÚNG mã trạng thái của nó. `assertIn(200, 400)` bị BÁC BỎ: nó chấp nhận HAI hành
# vi trái ngược nhau (từ chối và bỏ qua im lặng) nên không phân biệt được "cách ly đúng" với
# "client tự chọn tenant mà máy chủ không nói gì". Ở đây mỗi vế là MỘT mã, và mỗi vế ÂM đều có
# vế DƯƠNG chạy đúng đường đó — thiếu vế dương thì một bộ lọc hỏng cho MỌI người cũng "qua" được.
#
# BỐN CHỐT AN TOÀN (D-8: CSDL nghiệp vụ VẪN là SQLite, KHÔNG migration CSDL nghiệp vụ):
#   1. CSDL đo là SQLite trong thư mục `tempfile` do CHÍNH khối này dựng. Khối này TỪ CHỐI ĐO
#      (mã thoát 9) nếu `cau_hinh.DUONG_DAN_CSDL` không nằm trong thư mục đó.
#   2. CSDL nghiệp vụ (`app/du-lieu/hub.db`) chỉ được ĐỌC dấu vân tay (sha256 · mtime · cỡ)
#      TRƯỚC và SAU; lệch là HỎNG. Không một câu `INSERT`/`UPDATE`/migration nào chạm nó.
#   3. Máy chủ đo bind `127.0.0.1` cổng 0 (hệ điều hành cấp) — không mở đường ra ngoài, không
#      tunnel, không hãng (kể cả sandbox).
#   4. `PYTHONDONTWRITEBYTECODE=1`: đo trên một cây KHÁC (`VIP_G22_CAY_APP`) là đo CHỈ ĐỌC —
#      không được rơi `__pycache__` vào cây người khác.
#
# PHỦ TUYẾN ĐO BẰNG GÌ
# --------------------
# Không đoán từ việc đọc mã. Bộ đếm được cắm vào `truy_van.chay`/`truy_van.tim_don` TRONG CHÍNH
# TIẾN TRÌNH CÓ MÁY CHỦ, rồi bắn HTTP thật; mỗi tuyến là một hiệu số bộ đếm trước/sau. Tệp nguồn
# chỉ được dùng để biết CẦN DÒ NHỮNG ĐƯỜNG NÀO — không dùng để phán quyết.
# ══════════════════════════════════════════════════════════════════════════════════════════════

MA_CHOT_AN_TOAN = 9
CAY_DO = os.path.abspath(os.environ.get("VIP_G22_CAY_APP") or GOC_APP)
GOC_CAY_DO = os.path.dirname(CAY_DO)
DO_CAY_KHAC = bool(os.environ.get("VIP_G22_CAY_APP"))

MK_B7 = "G22-AG04-HopDong-1"
SO_DON_A = 60                    # > 50 để đo được TRANG MẶC ĐỊNH (50) VÀ `con_nua`
MOC_A = "A-MOC"                  # dấu vết trong `nguoi_nhan_ten` của đơn MỐC tenant A
MOC_B = "B-MOC"
COD_MOC_A = 900000111
KHOA_CHAY = ("dong", "tong", "tong_chinh_xac", "tong_it_nhat", "gioi_han", "lech", "trang",
             "con_nua", "sap_xep", "loc_bo_qua")
# Máy chủ thêm ĐÚNG MỘT khoá `don` (bí danh tạm cho giao diện cũ) — §1.5 + §3.3 của hợp đồng.
KHOA_HOP_DONG = KHOA_CHAY + ("don",)

M = {}          # mô-đun sản phẩm của CÂY đang đo, nạp bởi `_nap_cay()`


class _Tra:
    __slots__ = ("ma", "raw", "j")

    def __init__(self, ma, raw, j=None):
        self.ma, self.raw, self.j = ma, raw, j

    @property
    def text(self):
        return self.raw.decode("utf-8", "replace") if isinstance(self.raw, (bytes, bytearray)) \
            else str(self.raw)


class _Phien:
    """Khách HTTP giữ cookie phiên — bắn như giao diện bắn, không tự khẳng định gì."""

    def __init__(self, cong):
        self.cong = cong
        self.cookie = None

    def goi(self, duong, method="GET", du_lieu=None, gio=30):
        body = json.dumps(du_lieu, ensure_ascii=False).encode("utf-8") \
            if du_lieu is not None else None
        h = {}
        if method in ("POST", "PUT", "DELETE"):
            h["X-Requested-With"] = "VIPHub"
        if body is not None:
            h["Content-Type"] = "application/json"
        if self.cookie:
            h["Cookie"] = self.cookie
        yc = urllib.request.Request("http://127.0.0.1:%d%s" % (self.cong, duong), data=body,
                                    headers=h, method=method)
        try:
            with urllib.request.urlopen(yc, timeout=gio) as ph:
                sc = ph.headers.get("Set-Cookie")
                if sc:
                    self.cookie = sc.split(";")[0]
                raw = ph.read()
                ct = ph.headers.get("Content-Type", "")
                try:
                    j = json.loads(raw) if ("json" in ct and raw) else None
                except ValueError:
                    j = None
                return _Tra(ph.status, raw, j)
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                j = json.loads(raw)
            except ValueError:
                j = None
            return _Tra(e.code, raw, j)

    def dang_nhap(self, ten, mk=MK_B7):
        return self.goi("/api/v2/auth/dang-nhap", "POST",
                        {"ten_dang_nhap": ten, "mat_khau": mk})


def _dau_van(duong):
    """Dấu vân tay CSDL NGHIỆP VỤ: `(có tệp?, sha256, mtime, cỡ)`. Chỉ ĐỌC."""
    if not os.path.isfile(duong):
        return (False, None, None, None)
    st = os.stat(duong)
    return (True, _sha(duong), st.st_mtime, st.st_size)


def _nap_cay(cay, thu_muc):
    """Nạp mô-đun sản phẩm của CÂY đang đo trên một thư mục dữ liệu TẠM.

    `VIP_HUB_DATA` phải được đặt TRƯỚC `import csdl`: `cau_hinh` đọc biến này ở thời điểm nạp
    mô-đun, nên đặt sau là đo nhầm CSDL nghiệp vụ — đúng cái mà chốt (2) cấm.
    """
    sys.dont_write_bytecode = True
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["VIP_KHO_DANG_CHAY"] = "sqlite"
    os.environ["VIP_HUB_DATA"] = thu_muc
    os.environ["VIP_HUB_BACKOFF"] = "0.05"
    os.environ.pop("VIP_THU_POSTGRES", None)                     # D-8: không PostgreSQL
    if cay not in sys.path:
        sys.path.insert(0, cay)
    import bao_mat                                               # noqa: E402
    import csdl                                                  # noqa: E402
    import don_hang                                              # noqa: E402
    import quyen                                                 # noqa: E402
    import server                                                # noqa: E402
    import truy_van                                              # noqa: E402
    M.clear()
    M.update({"bao_mat": bao_mat, "csdl": csdl, "don_hang": don_hang, "quyen": quyen,
              "server": server, "truy_van": truy_van})
    return M


def _tao_tenant(ma_tenant, ten):
    return M["csdl"].ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                         (ma_tenant, ten, "pro", M["csdl"].bay_gio())).lastrowid


def _tao_user(ten_dn, ho_ten):
    return M["csdl"].ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                         " VALUES (?,?,?,?)",
                         (ten_dn, M["bao_mat"].bam_mat_khau(MK_B7), ho_ten,
                          M["csdl"].bay_gio())).lastrowid


def _gan(uid, tid, vai):
    M["csdl"].ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
                  " VALUES (?,?,?,?)", (uid, tid, vai, M["csdl"].bay_gio()))


def _du_lieu_don(nhan, i, moc=None):
    """Một đơn đủ trường bắt buộc. Đơn MỐC mang dấu vết nhận dạng được trong CẢ `nguoi_nhan_ten`
    (để dò bằng `q`) LẪN `cod` (để dò trong thân phản hồi thô).

    `cod` mốc CHỈ gán cho đơn mốc của A: gán nhầm cho đơn của B thì mọi phép "thân B có mốc A
    không" đều đọc ra CÓ — một đối chứng âm tự phá, và nó đã xảy ra thật ở bản đầu của khối này.
    """
    ten_nhan = "Nhan %s %s%d" % (nhan, moc + " " if moc else "", i)
    return {"nguoi_gui_ten": "Gui G22HD", "nguoi_gui_sdt": "0901111111",
            "nguoi_gui_dia_chi": "1 Duong G22 Ha Noi",
            "nguoi_nhan_ten": ten_nhan, "nguoi_nhan_sdt": "0902222222",
            "nguoi_nhan_dia_chi": "2 Pho G22 HCM",
            "hang_hoa": "Hang %s %d" % (nhan, i), "khoi_luong_gram": 500,
            "cod": COD_MOC_A if moc == MOC_A else (i + 1) * 1000}


def _dong_cua(tr):
    """Danh sách dòng của một phản hồi — đọc được CẢ HAI hình dạng.

    Hợp đồng §1.5 ghim khoá `dong`; đường CŨ trả `don`. Bảng bằng chứng phải đọc được cả đường
    cũ thì mới NÓI ĐƯỢC nó sai ở đâu ("0 dòng vì sai tên khoá" là một câu vô nghĩa), nhưng PHÉP
    GHIM thì vẫn đòi đúng `dong` — xem B7c.
    """
    if not isinstance(tr.j, dict):
        return []
    for k in ("dong", "don"):
        if isinstance(tr.j.get(k), list):
            return tr.j[k]
    return []


def _khoa_dong(tr):
    """Tên khoá danh sách mà phản hồi THẬT SỰ dùng: `dong` (hợp đồng) · `don` (đường cũ)."""
    if not isinstance(tr.j, dict):
        return "—"
    for k in ("dong", "don"):
        if isinstance(tr.j.get(k), list):
            return k
    return "—"


class _ImLog:
    """Gom log truy cập của máy chủ đo vào bộ đệm thay vì để nó xen vào giữa các BẢNG BẰNG CHỨNG.

    Một bảng bị ~40 dòng JSON của `quan_sat` chèn vào là một bảng không đọc được, và bằng chứng
    không đọc được thì không phải bằng chứng. Nhưng KHÔNG nuốt: `_bao_log` in lại số dòng đã gom
    và chép ra mọi dòng có dấu vết lỗi — handler nổ mà im là hỏng đúng chỗ cần thấy nhất.
    """

    def __init__(self):
        self.dong = []

    def write(self, s):
        self.dong.extend(str(s).splitlines())

    def flush(self):
        pass


def _bao_log(im):
    if im is None:
        return
    nghi = [d for d in im.dong if re.search(r"Traceback|Error|error|Exception|LỖI", d)]
    print("  [log máy chủ đo] %d dòng đã gom (log truy cập — không xen vào bảng); dòng có dấu vết "
          "lỗi: %d" % (len(im.dong), len(nghi)))
    for d in nghi[:20]:
        print("      ! %s" % d[:180])


def _dung_nen():
    """Fixture hai tenant THẬT trên CSDL TẠM, dựng bằng CHÍNH `don_hang.tao_don` của sản phẩm.

    Không `INSERT` tay vào `don_hang`: bảng có 40 cột sau v7, và một fixture tự chế ba cột thì
    không bắt được lỗi nào thuộc về cột thứ tư.
    """
    M["quyen"].seed()
    tid_a = _tao_tenant("g22hd-a", "G22 Hop dong A")
    tid_b = _tao_tenant("g22hd-b", "G22 Hop dong B")
    uid_a = _tao_user("g22hd-a-owner", "Chu A")
    uid_b = _tao_user("g22hd-b-owner", "Chu B")
    _gan(uid_a, tid_a, "TENANT_OWNER")
    _gan(uid_b, tid_b, "TENANT_OWNER")
    don_moc_a = None
    for i in range(SO_DON_A):
        d = _du_lieu_don("A", i, MOC_A if i == 0 else None)
        don, _trung = M["don_hang"].tao_don(tid_a, uid_a, d, kiem_quyen=False)
        if i == 0:
            don_moc_a = don
    don_b, _trung = M["don_hang"].tao_don(tid_b, uid_b, _du_lieu_don("B", 0, MOC_B),
                                          kiem_quyen=False)
    return {"tid_a": tid_a, "tid_b": tid_b, "uid_a": uid_a, "uid_b": uid_b,
            "don_moc_a": don_moc_a, "don_b": don_b}


def _ung_vien_tuyen(duong_server):
    """ỨNG VIÊN tuyến `/api/v2/don*` đọc từ MÃ NGUỒN của cây đang đo.

    Chỉ là DANH SÁCH CẦN DÒ. Kết luận "tuyến này có đi qua `truy_van.chay()`" KHÔNG lấy từ đây:
    một dòng `import truy_van` trong tệp không chứng minh được đường ấy ĐI QUA nó.
    """
    than = doc(duong_server)
    ung_vien = set()
    for m in re.finditer(r'duong == "(/api/v2/don[^"]*)"', than):
        ung_vien.add(m.group(1))
    for m in re.finditer(r're\.fullmatch\(r"(/api/v2/don/[^"]*)"', than):
        ung_vien.add(m.group(1))
    return sorted(ung_vien)


def _cu_the_hoa(mau, don_id):
    """Mẫu tuyến → URL cụ thể: `(\\d+)` → id THẬT của tenant A, `(a|b|c)` → nhánh ĐẦU.

    Không cụ thể hoá thì một mẫu có nhánh (`…/(duyet|gui|huy)`) sẽ thành URL không tồn tại và
    bị chấm là "không có tuyến" — tức là một LỖ HỔNG BỊ GIẤU, đúng thứ khối này phải phơi ra.
    """
    ra = re.sub(r"\(\\d\+\)", str(don_id), mau)
    return re.sub(r"\(([A-Za-z0-9_\-]+(?:\|[A-Za-z0-9_\-]+)+)\)",
                  lambda m: m.group(1).split("|")[0], ra)


def _bang_phu_tuyen(ung_vien, phien, dem, kho_don):
    """Dò MỌI ứng viên bằng HTTP thật, trả về bảng đo. `kho_don` là kho id đơn dùng-một-lần để
    một tuyến GHI (duyệt/huỷ…) không làm hỏng phép dò của tuyến sau."""
    bang = []
    for mau in ung_vien:
        for method in ("GET", "POST"):
            don_id = kho_don.pop() if kho_don else None
            url = _cu_the_hoa(mau, don_id)
            d0 = (dem["chay"], dem["tim_don"])
            tr = phien.goi(url + ("" if "?" in url else ""), method,
                           {"gioi_han": 5} if method == "POST" else None)
            d1 = (dem["chay"], dem["tim_don"])
            bang.append({"mau": mau, "method": method, "url": url, "ma": tr.ma,
                         "d_chay": d1[0] - d0[0], "d_tim": d1[1] - d0[1],
                         "co": tr.ma != 404, "than": tr.text.replace("\n", " ")[:120]})
    return bang


def _pham_vi_hop_dong(mau, method):
    """Tuyến này có THUỘC phạm vi hợp đồng §1 không — đọc từ chính hợp đồng, không phán cảm tính.

    Cột này KHÔNG để giảm nhẹ phán quyết: mọi tuyến không đi qua `truy_van.chay()` vẫn bị ghi
    thẳng là **LỖ HỔNG** ở cột bên trái. Cột này chỉ nói thêm rằng hợp đồng §1.8 đã KHAI trước
    tuyến nào ngoài phạm vi — để người đọc biết chỗ nào là nợ đã biết, chỗ nào là bất ngờ.
    """
    if mau == "/api/v2/don" and method == "GET":
        return "TRONG §1 (đường DANH SÁCH — trọng tâm hợp đồng)"
    if mau == "/api/v2/don/loc-mo-ta":
        return "TRONG §1.7 (MÔ TẢ bộ lọc — không chạy truy vấn, xem B7p)"
    if mau == "/api/v2/don/tim":
        return "NGOÀI §1.8.5 (cửa cũ `POST /don/tim` giữ nguyên)"
    if mau == "/api/v2/don/xuat-csv":
        return "NGOÀI §1.8.5 (xuất CSV giữ nguyên)"
    return "NGOÀI §1.8 (CRUD/ghi theo id — không phải truy vấn danh sách)"


def _in_bang_phu_tuyen(bang):
    co = [r for r in bang if r["co"]]
    print("\n  ┌ BẢNG PHỦ TUYẾN `/api/v2/don*` — CỘT Δ LÀ BỘ ĐẾM TRONG TIẾN TRÌNH MÁY CHỦ")
    print("  │ %-3s %-5s %-58s %-5s %-6s %-8s %-40s %s"
          % ("#", "method", "tuyến", "mã", "Δchay", "Δtim_don", "phán quyết ĐO ĐƯỢC",
             "phạm vi hợp đồng §1"))
    for i, r in enumerate(co, 1):
        mo_ta_17 = _pham_vi_hop_dong(r["mau"], r["method"]).startswith("TRONG §1.7")
        if r["d_chay"] >= 1:
            verdict = "ĐI QUA `truy_van.chay()`"
        elif r["d_tim"] >= 1:
            verdict = "ĐI QUA `tim_don` (không qua `chay`)"
        elif mo_ta_17:
            # §1.7 là đường MÔ TẢ: nó PHẢI trả `mo_ta_bo_loc()`, KHÔNG chạy truy vấn nào. Gọi nó
            # là "lỗ hổng" là nói sai về chính hợp đồng — nhưng Δ vẫn in ra bằng 0, không giấu.
            verdict = "KHÔNG chạy truy vấn — ĐÚNG §1.7 (ghim ở B7p)"
        else:
            verdict = "KHÔNG ĐI QUA — **LỖ HỔNG**"
        print("  │ %-3d %-5s %-58s %-5s %-6d %-8d %-40s %s"
              % (i, r["method"], r["mau"], r["ma"], r["d_chay"], r["d_tim"], verdict,
                 _pham_vi_hop_dong(r["mau"], r["method"])))
    qua = sum(1 for r in co if r["d_chay"] >= 1)
    mo_ta = sum(1 for r in co if r["d_chay"] < 1 and r["d_tim"] < 1
                and _pham_vi_hop_dong(r["mau"], r["method"]).startswith("TRONG §1.7"))
    lo_hong = len(co) - qua - mo_ta
    print("  └ tuyến TỒN TẠI (mã ≠ 404): %d · ĐI QUA `truy_van.chay()`: %d · ĐÚNG §1.7 (mô tả, "
          "không chạy truy vấn): %d · LỖ HỔNG (Δchay=0): %d" % (len(co), qua, mo_ta, lo_hong))
    return co


def b7_hop_dong():
    muc("B7. HỢP ĐỒNG TENANT (§1.4) + PHỦ TUYẾN + PHÂN TRANG — FIXTURE SQLITE TẠM, HAI TENANT")
    print("  cây đo          : %s%s" % (CAY_DO, "   (CHỈ ĐỌC — cây khác)" if DO_CAY_KHAC else ""))
    print("  bảng ghim       : %s" % ", ".join(KHOA_HOP_DONG))
    print("  $ python3 app/migrate.py   ← chạy trên thư mục TẠM, KHÔNG phải CSDL nghiệp vụ")
    kq = {"ma": 0, "cay": CAY_DO, "qua": 0, "co_tuyen": 0, "co_hop_dong": False}
    duong_csdl_that = os.path.join(GOC_CAY_DO, "app", "du-lieu", "hub.db")
    truoc = _dau_van(duong_csdl_that)
    thu_muc = tempfile.mkdtemp(prefix="g22-ag04-hopdong-")
    _hub_data_cu = os.environ.get("VIP_HUB_DATA")
    sv = None
    that_chay = that_tim = None
    im_log = None
    _stderr_cu = None
    try:
        ma_mig, _ra_mig, giay_mig = chay(
            [sys.executable, os.path.join(GOC_CAY_DO, "app", "migrate.py")], gio=300,
            env={"VIP_HUB_DATA": thu_muc, "VIP_KHO_DANG_CHAY": "sqlite"}, cwd=GOC_CAY_DO)
        _nap_cay(CAY_DO, thu_muc)
        csdl, server, truy_van = M["csdl"], M["server"], M["truy_van"]
        csdl.mo()
        duong_do = os.path.abspath(csdl.cau_hinh.DUONG_DAN_CSDL)
        goc_tam = os.path.abspath(thu_muc) + os.sep
        print("  CSDL đo         : %s" % duong_do)
        print("  migration       : mã thoát %d · %.1f giây · schema v%s (mã cần v%s)"
              % (ma_mig, giay_mig, csdl.phien_ban_hien_tai(), csdl.PHIEN_BAN_SCHEMA))
        if not duong_do.startswith(goc_tam):
            ket("B7a", "CHỐT AN TOÀN: CSDL đo PHẢI nằm trong thư mục TẠM", HONG,
                "CSDL mở ra là %s — KHÔNG nằm dưới %s. TỪ CHỐI ĐO (mã thoát %d) để không chạm "
                "CSDL nghiệp vụ (D-8)." % (duong_do, thu_muc, MA_CHOT_AN_TOAN))
            return {"ma": MA_CHOT_AN_TOAN, "cay": CAY_DO, "qua": 0, "co_tuyen": 0,
                    "co_hop_dong": False}
        ket("B7a", "CHỐT AN TOÀN: CSDL đo nằm trong thư mục TẠM (`tempfile`), không phải CSDL "
            "nghiệp vụ", DAT if ma_mig == 0 else HONG,
            "CSDL đo %s · CSDL nghiệp vụ %s (%s)"
            % (duong_do, duong_csdl_that, "có" if truoc[0] else "KHÔNG có"))

        nen = _dung_nen()
        # ── bộ đếm TRONG TIẾN TRÌNH MÁY CHỦ ───────────────────────────────────────────────────
        dem = {"chay": 0, "tim_don": 0}
        that_chay, that_tim = truy_van.chay, truy_van.tim_don

        def _dem_chay(*a, **k):
            dem["chay"] += 1
            return that_chay(*a, **k)

        def _dem_tim(*a, **k):
            dem["tim_don"] += 1
            return that_tim(*a, **k)

        truy_van.chay, truy_van.tim_don = _dem_chay, _dem_tim
        im_log = _ImLog()
        _stderr_cu = sys.stderr
        sys.stderr = im_log
        sv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.BoXuLy)
        cong = sv.server_address[1]
        threading.Thread(target=sv.serve_forever, daemon=True).start()
        print("  máy chủ đo      : http://%s:%d (bind 127.0.0.1, cổng do hệ điều hành cấp)"
              % sv.server_address)
        phien_a, phien_b = _Phien(cong), _Phien(cong)
        tra_a = phien_a.dang_nhap("g22hd-a-owner")
        tra_b = phien_b.dang_nhap("g22hd-b-owner")
        print("  đăng nhập       : A → %d · B → %d" % (tra_a.ma, tra_b.ma))
        ket("B7b", "NỀN: hai tenant A/B, %d đơn ở A + 1 đơn ở B (dựng bằng `don_hang.tao_don`)"
            % SO_DON_A, DAT if (tra_a.ma == 200 and tra_b.ma == 200) else HONG,
            "A: tenant %s · người dùng %s · %d đơn · mốc `%s` (cod %d)\n"
            "     B: tenant %s · người dùng %s · 1 đơn · mốc `%s` (cod %d)\n"
            "     phiên: A %d · B %d"
            % (nen["tid_a"], "g22hd-a-owner", SO_DON_A, MOC_A, COD_MOC_A,
               nen["tid_b"], "g22hd-b-owner", MOC_B, nen["don_b"]["cod"],
               tra_a.ma, tra_b.ma))
        print("\n  ┌ BẢNG TENANT A/B — fixture SQLite TẠM (`%s`), KHÔNG dữ liệu thật" % duong_do)
        print("  │ %-4s %-9s %-4s %-16s %-8s %-12s %s"
              % ("tenant", "mã", "id", "người dùng", "số đơn", "cod mốc", "dấu vết mốc"))
        for nhan, ma_t, tid, ten_dn, so_don, moc, cod in (
                ("A", "g22hd-a", nen["tid_a"], "g22hd-a-owner", SO_DON_A,
                 "nguoi_nhan_ten ~ 'A-MOC'", COD_MOC_A),
                ("B", "g22hd-b", nen["tid_b"], "g22hd-b-owner", 1,
                 "nguoi_nhan_ten ~ 'B-MOC'", nen["don_b"]["cod"])):
            print("  │ %-4s %-9s %-4s %-16s %-8s %-12s %s"
                  % (nhan, ma_t, tid, ten_dn, so_don, cod, moc))
        print("  └ phiên đăng nhập: A %d · B %d · mã đơn MỐC của A: %s"
              % (tra_a.ma, tra_b.ma, nen["don_moc_a"]["ma_don"]))

        # ── 1. ĐỐI CHỨNG DƯƠNG: A đọc dữ liệu của A ⇒ ĐÚNG 200 theo hợp đồng §1 ──────────────
        tr = phien_a.goi("/api/v2/don")
        khoa = set(tr.j or {}) if isinstance(tr.j, dict) else set()
        dong = tr.j.get("dong") if isinstance(tr.j, dict) and isinstance(tr.j.get("dong"), list) \
            else []
        dat = (tr.ma == 200 and khoa == set(KHOA_HOP_DONG) and len(dong) == 50
               and tr.j.get("gioi_han") == 50 and tr.j.get("trang") == 1
               and tr.j.get("lech") == 0 and tr.j.get("tong") == SO_DON_A
               and tr.j.get("con_nua") is True
               and nen["don_b"]["cod"] not in [d.get("cod") for d in dong])
        ket("B7c", "ĐỐI CHỨNG DƯƠNG: A đọc dữ liệu A ⇒ **đúng 200** + hình dạng §1.5 + trang mặc "
            "định 50", DAT if dat else HONG,
            "mã %s (ghim: 200 — KHÔNG nhận '200 hoặc 400') · khoá %s (ghim: %d khoá %s) · khoá "
            "dữ liệu thật: `%s` (ghim `dong`)\n"
            "     gioi_han=%s (ghim 50) · trang=%s · lech=%s · số dòng trong `dong`=%s (ghim 50) · "
            "tong=%s (ghim %d) · con_nua=%s · đơn của B lọt vào trang 1 của A: %s (ghim KHÔNG)\n"
            "     (đơn MỐC của A xếp CUỐI theo `moi_nhat` = `id DESC` nên nằm ở trang 3; B7i ghim "
            "nó truy được bằng `?ma_don=`.)"
            % (tr.ma, sorted(khoa) if khoa else "KHÔNG CÓ", len(KHOA_HOP_DONG),
               "KHỚP" if khoa == set(KHOA_HOP_DONG) else "LỆCH", _khoa_dong(tr),
               (tr.j or {}).get("gioi_han"), (tr.j or {}).get("trang"), (tr.j or {}).get("lech"),
               len(dong), (tr.j or {}).get("tong"), SO_DON_A, (tr.j or {}).get("con_nua"),
               "CÓ" if nen["don_b"]["cod"] in [d.get("cod") for d in dong] else "KHÔNG"))

        # ── 2. PHÂN TRANG: mặc định · trần · trang 2 rời trang 1 (§1.3) ───────────────────────
        p1 = phien_a.goi("/api/v2/don?gioi_han=25&trang=1")
        p2 = phien_a.goi("/api/v2/don?gioi_han=25&trang=2")
        p3 = phien_a.goi("/api/v2/don?gioi_han=25&trang=3")
        toi_da = phien_a.goi("/api/v2/don?gioi_han=100000")
        id1 = [d["id"] for d in _dong_cua(p1)]
        id2 = [d["id"] for d in _dong_cua(p2)]
        id3 = [d["id"] for d in _dong_cua(p3)]
        id_max = [d["id"] for d in _dong_cua(toi_da)]
        print("\n  ┌ BẢNG PHÂN TRANG (§1.3) — đo THẬT trên fixture %d đơn của A" % SO_DON_A)
        print("  │ %-34s %-5s %-9s %-7s %-6s %-9s %-6s %-8s %s"
              % ("yêu cầu", "mã", "gioi_han", "lech", "trang", "số dòng", "tong", "con_nua",
                 "khoá dữ liệu"))
        for nhan, t in (("GET /api/v2/don (mặc định)", tr), ("?gioi_han=100000 (vượt trần)", toi_da),
                        ("?gioi_han=25&trang=1", p1), ("?gioi_han=25&trang=2", p2),
                        ("?gioi_han=25&trang=3", p3)):
            j = t.j or {}
            print("  │ %-34s %-5s %-9s %-7s %-6s %-9s %-6s %-8s %s"
                  % (nhan, t.ma, j.get("gioi_han"), j.get("lech"), j.get("trang"),
                     len(_dong_cua(t)), j.get("tong"), j.get("con_nua"), _khoa_dong(t)))
        print("  └ id trang 1 ∩ trang 2 = %s · hợp trang 1+2 = %d id KHÁC NHAU"
              % (sorted(set(id1) & set(id2)) or "RỖNG", len(set(id1) | set(id2))))
        ket("B7d", "MẶC ĐỊNH = 50 dòng và TRẦN = 500 bị KẸP (không 400) — giá trị THẬT trả ra",
            DAT if (tr.j.get("gioi_han") == 50 and len(dong) == 50 and toi_da.ma == 200
                    and (toi_da.j or {}).get("gioi_han") == 500 and len(id_max) == SO_DON_A
                    and (toi_da.j or {}).get("con_nua") is False) else HONG,
            "mặc định: mã %s · gioi_han=%s · %d dòng (ghim 50/50)\n"
            "     vượt trần: mã %s · xin 100000 → `gioi_han` trả ra %s (ghim 500) · %d dòng "
            "(ghim %d) · con_nua=%s"
            % (tr.ma, tr.j.get("gioi_han"), len(dong), toi_da.ma,
               (toi_da.j or {}).get("gioi_han"), len(id_max), SO_DON_A,
               (toi_da.j or {}).get("con_nua")))
        ket("B7e", "TRANG 2 KHÔNG LẶP TRANG 1: 25+25 id rời nhau; trang 3 = 10 dòng và hết",
            DAT if (p1.ma == 200 and p2.ma == 200 and p3.ma == 200 and len(id1) == 25
                    and len(id2) == 25 and not (set(id1) & set(id2)) and len(set(id1) | set(id2)) == 50
                    and len(id3) == SO_DON_A - 50 and p3.j.get("con_nua") is False) else HONG,
            "trang1=%d id · trang2=%d id · GIAO=%s (ghim RỖNG) · hợp=%d id (ghim 50)\n"
            "     trang3=%d dòng (ghim %d) · con_nua=%s · lech trang2=%s (ghim 25), trang=%s (ghim 2)"
            % (len(id1), len(id2), sorted(set(id1) & set(id2)) or "RỖNG",
               len(set(id1) | set(id2)), len(id3), SO_DON_A - 50, p3.j.get("con_nua"),
               p2.j.get("lech"), p2.j.get("trang")))

        # ── 3. THAM SỐ SAI ⇒ ĐÚNG 400 (§1.6), kèm đối chứng DƯƠNG ────────────────────────────
        xau = (("?trang=2&lech=25 (cả hai)", phien_a.goi("/api/v2/don?trang=2&lech=25")),
               ("?gioi_han=abc (sai kiểu)", phien_a.goi("/api/v2/don?gioi_han=abc")),
               ("?sap_xep=khong_co_khoa_nay", phien_a.goi("/api/v2/don?sap_xep=khong_co_khoa_nay")),
               ("?ten_tham_so_khong_he_co=1", phien_a.goi("/api/v2/don?ten_tham_so_khong_he_co=1")))
        tot = phien_a.goi("/api/v2/don?sap_xep=ma_don&gioi_han=3")
        print("\n  ┌ BẢNG MÃ LỖI (§1.6) — mỗi vế ÂM đi kèm một vế DƯƠNG")
        for nhan, t in xau:
            print("  │ %-34s mã %-4s %s" % (nhan, t.ma, (t.j or {}).get("loi", "")[:96]))
        print("  │ %-34s mã %-4s sap_xep=%s (hợp lệ ⇒ phải 200)"
              % ("?sap_xep=ma_don&gioi_han=3", tot.ma, (tot.j or {}).get("sap_xep")))
        print("  └")
        ket("B7f", "Tham số sai ⇒ **đúng 400** (4 vế âm) và tham số hợp lệ ⇒ 200 (vế dương)",
            DAT if (all(t.ma == 400 and isinstance(t.j, dict) and "loi" in t.j for _n, t in xau)
                    and tot.ma == 200 and (tot.j or {}).get("sap_xep") == "ma_don"
                    and len(_dong_cua(tot)) == 3) else HONG,
            "mã đo được: %s (ghim TẤT CẢ = 400) · vế dương: mã %s · sap_xep=%s (ghim `ma_don`) · "
            "3 dòng (ghim 3)"
            % ([(n, t.ma) for n, t in xau], tot.ma, (tot.j or {}).get("sap_xep")))

        # ── 4. ĐỐI CHỨNG ÂM CROSS-TENANT: B đòi dữ liệu của A ───────────────────────────────
        ma_don_a = nen["don_moc_a"]["ma_don"]
        # (a) B tự chọn tenant bằng tham số ⇒ hợp đồng §1.4 ghim **400** (không có đường nào để
        #     client chọn tenant). Đường CŨ bỏ qua im lặng ⇒ 200 — đây là vế PHÂN BIỆT được.
        ct1 = phien_b.goi("/api/v2/don?tenant_id=%d&gioi_han=500" % nen["tid_a"])
        # (b) mức DỮ LIỆU: B lọc đúng `ma_don` của A ⇒ 200 nhưng thân phải RỖNG.
        ct2 = phien_b.goi("/api/v2/don?ma_don=%s&gioi_han=500" % ma_don_a)
        ct2_dong = _dong_cua(ct2)
        # (c) ĐỐI CHỨNG DƯƠNG của (b): CHÍNH A lọc cùng tham số ⇒ phải thấy đúng 1 dòng.
        ct3 = phien_a.goi("/api/v2/don?ma_don=%s&gioi_han=500" % ma_don_a)
        ct3_dong = _dong_cua(ct3)
        print("\n  ┌ BẢNG CROSS-TENANT — B đòi dữ liệu của A (kèm vế DƯƠNG của chính A)")
        print("  │ %-52s %-5s %-6s %s"
              % ("lượt gọi", "mã", "khoá", "thân phản hồi (có mốc của A?)"))
        for nhan, t in (("B: ?tenant_id=<A> (tự chọn tenant)", ct1),
                        ("B: ?ma_don=<đơn MỐC của A>", ct2),
                        ("A: ?ma_don=<đơn MỐC của A>  (DƯƠNG)", ct3)):
            co_moc = (ma_don_a in t.text) or (str(COD_MOC_A) in t.text)
            print("  │ %-52s %-5s %-6s %s"
                  % (nhan, t.ma, _khoa_dong(t), "CÓ mốc A" if co_moc else "KHÔNG có mốc A"))
        print("  └")
        ket("B7g", "CROSS-TENANT (a): B gửi `tenant_id=<A>` ⇒ **đúng 400** + `loi`, thân KHÔNG có "
            "dữ liệu của A", DAT if (ct1.ma == 400 and isinstance(ct1.j, dict) and "loi" in ct1.j
                                     and ma_don_a not in ct1.text
                                     and str(COD_MOC_A) not in ct1.text) else HONG,
            "mã %s (ghim 400 — `assertIn(200,400)` bị BÁC BỎ: 200 nghĩa là máy chủ BỎ QUA IM LẶNG "
            "tham số chọn tenant)\n     `loi` = %r\n     thân có mã đơn/mốc của A: %s (ghim KHÔNG)"
            % (ct1.ma, (ct1.j or {}).get("loi", "")[:90],
               "CÓ" if (ma_don_a in ct1.text or str(COD_MOC_A) in ct1.text) else "KHÔNG"),
            nhom="cross-tenant", chieu="am")
        ket("B7h", "CROSS-TENANT (b): B lọc `ma_don` của A ⇒ 200 nhưng `dong` RỖNG, `tong`=0, "
            "thân KHÔNG có mốc A", DAT if (ct2.ma == 200 and ct2_dong == []
                                          and (ct2.j or {}).get("tong") == 0
                                          and ma_don_a not in ct2.text
                                          and str(COD_MOC_A) not in ct2.text) else HONG,
            "mã %s · số dòng %d (ghim 0) · tong=%s (ghim 0) · thân có mốc A: %s (ghim KHÔNG)"
            % (ct2.ma, len(ct2_dong), (ct2.j or {}).get("tong"),
               "CÓ" if (ma_don_a in ct2.text or str(COD_MOC_A) in ct2.text) else "KHÔNG"),
            nhom="cross-tenant", chieu="am")
        ket("B7i", "ĐỐI CHỨNG DƯƠNG của B7h: CHÍNH A lọc cùng `ma_don` ⇒ đúng 1 dòng của A",
            DAT if (ct3.ma == 200 and len(ct3_dong) == 1
                    and ct3_dong[0].get("cod") == COD_MOC_A) else HONG,
            "mã %s · số dòng %d (ghim 1) · cod=%s (ghim %d) · mã đơn=%s"
            % (ct3.ma, len(ct3_dong), ct3_dong[0].get("cod") if ct3_dong else None, COD_MOC_A,
               ma_don_a), nhom="cross-tenant", chieu="duong")
        # (d) tìm chữ: `q` tìm trong `nguoi_nhan_ten` — B tìm mốc của A phải ra 0 dòng.
        q_b = phien_b.goi("/api/v2/don?q=%s&gioi_han=500" % MOC_A)
        q_a = phien_a.goi("/api/v2/don?q=%s&gioi_han=500" % MOC_A)
        ket("B7j", "CROSS-TENANT (d): B tìm chữ `q=%s` (dấu vết trong tên người nhận của A) ⇒ 0 "
            "dòng; A tìm cùng chữ ⇒ có dòng" % MOC_A,
            DAT if (q_b.ma == 200 and len(_dong_cua(q_b)) == 0
                    and len(_dong_cua(q_a)) >= 1) else HONG,
            "mã B %s · %d dòng (ghim 0) ‖ mã A %s · %d dòng (ghim ≥ 1) · khoá dữ liệu B `%s`"
            % (q_b.ma, len(_dong_cua(q_b)), q_a.ma, len(_dong_cua(q_a)), _khoa_dong(q_b)),
            nhom="cross-tenant", chieu="am")
        # (e) danh sách KHÔNG lọc của B: chỉ có đơn của B.
        lb = phien_b.goi("/api/v2/don?gioi_han=500")
        lb_dong = _dong_cua(lb)
        ket("B7k", "CROSS-TENANT (e): danh sách KHÔNG lọc của B chỉ có đơn của B",
            DAT if (lb.ma == 200 and len(lb_dong) == 1
                    and lb_dong[0].get("cod") == nen["don_b"]["cod"]
                    and ma_don_a not in lb.text
                    and str(COD_MOC_A) not in lb.text) else HONG,
            "mã %s · %d dòng (ghim 1) · cod=%s (ghim %s) · có mốc A: %s (ghim KHÔNG)"
            % (lb.ma, len(lb_dong), lb_dong[0].get("cod") if lb_dong else None,
               nen["don_b"]["cod"],
               "CÓ" if (ma_don_a in lb.text or str(COD_MOC_A) in lb.text) else "KHÔNG"),
            nhom="cross-tenant", chieu="am")
        # (f) vô danh ⇒ 401 (§1.4); đối chứng dương: đã đăng nhập ⇒ 200.
        vo_danh = _Phien(cong).goi("/api/v2/don")
        ket("B7l", "VÔ DANH ⇒ **đúng 401** (§1.4); đã đăng nhập ⇒ 200 (đối chứng dương)",
            DAT if (vo_danh.ma == 401 and phien_a.goi("/api/v2/don").ma == 200) else HONG,
            "chưa đăng nhập: mã %s (ghim 401) · A đã đăng nhập: mã %s (ghim 200)"
            % (vo_danh.ma, phien_a.goi("/api/v2/don").ma), nhom="cross-tenant", chieu="am")
        _dc_duong("cross-tenant")

        # ── 5. HÌNH DẠNG CỦA CHÍNH MÔ-ĐUN `truy_van` (độc lập với route) ─────────────────────
        kq_chay = truy_van.chay(truy_van.BANG_DON, nen["tid_a"], {})
        ket("B7m", "Hình dạng `truy_van.chay()` (gọi TRỰC TIẾP, không qua HTTP) khớp §1.5: "
            "%d khoá" % len(KHOA_CHAY),
            DAT if set(kq_chay) == set(KHOA_CHAY) else HONG,
            "khoá đo được: %s\n     khoá hợp đồng: %s"
            % (sorted(kq_chay), sorted(KHOA_CHAY)))
        # Vì sao `loc-mo-ta` đứng Δ=0 ở bảng phủ: nó là đường MÔ TẢ (§1.7), trả nguyên văn
        # `mo_ta_bo_loc()` — KHÔNG chạy truy vấn nào. Ghim bằng ĐẲNG THỨC, không bằng lời.
        mo_ta = phien_a.goi("/api/v2/don/loc-mo-ta")
        mong_doi = truy_van.mo_ta_bo_loc()
        ket("B7p", "§1.7: `GET /api/v2/don/loc-mo-ta` trả ĐÚNG `truy_van.mo_ta_bo_loc()` (vì sao "
            "tuyến này đứng Δchay=0 ở bảng phủ)",
            DAT if (mo_ta.ma == 200 and mo_ta.j == mong_doi) else HONG,
            "mã %s (ghim 200) · thân == `mo_ta_bo_loc()`: %s · %d khoá mô tả"
            % (mo_ta.ma, mo_ta.j == mong_doi, len(mong_doi) if isinstance(mong_doi, dict) else -1))

        # ── 6. PHỦ TUYẾN — bộ đếm trong tiến trình máy chủ ───────────────────────────────────
        duong_server = os.path.join(CAY_DO, "server.py")
        ung_vien = _ung_vien_tuyen(duong_server)
        print("\n  Ứng viên tuyến đọc từ MÃ NGUỒN %s (%d mẫu):" % (duong_server, len(ung_vien)))
        for u in ung_vien:
            print("    · %s" % u)
        # Kho id DÙNG-MỘT-LẦN: một tuyến GHI (duyệt/huỷ…) không được làm hỏng phép dò tuyến sau.
        kho_don = []
        for i in range(len(ung_vien) * 2 + 2):
            don, _t = M["don_hang"].tao_don(nen["tid_a"], nen["uid_a"],
                                            _du_lieu_don("PROBE", i + 200), kiem_quyen=False)
            kho_don.append(don["id"])
        bang = _bang_phu_tuyen(ung_vien, phien_a, dem, kho_don)
        co = _in_bang_phu_tuyen(bang)
        kq["co_tuyen"] = len(co)
        kq["qua"] = sum(1 for r in co if r["d_chay"] >= 1)
        kq["co_hop_dong"] = any(r["mau"] == "/api/v2/don" and r["method"] == "GET"
                                and r["d_chay"] >= 1 for r in co)
        if not kq["co_hop_dong"]:
            ket("B7n", "PHỦ TUYẾN: **KHÔNG tuyến `/api/v2/don*` nào đi qua `truy_van.chay()`** ⇒ "
                "hợp đồng §1 (AG-02) CHƯA được cắm vào cây này", KHUYET,
                "%d/%d tuyến tồn tại đi qua `truy_van.chay()`; riêng `GET /api/v2/don` = 0 lượt ⇒ "
                "mọi ghim hợp đồng ở trên ĐỎ vì CÂY THIẾU TUYẾN, không phải vì phép đo sai.\n"
                "     Đối chứng: đo lại cùng tệp này trên cây ĐÃ gộp tuyến "
                "(`VIP_G22_CAY_APP=<cây>/app`) ⇒ bảng phủ phải chuyển XANH."
                % (kq["qua"], len(co)))
        else:
            ket("B7n", "PHỦ TUYẾN: `GET /api/v2/don` ĐI QUA `truy_van.chay()` — đo bằng bộ đếm "
                "trong tiến trình máy chủ", DAT if kq["qua"] >= 1 else HONG,
                "%d/%d tuyến tồn tại đi qua `truy_van.chay()` (xem bảng phủ ở trên)"
                % (kq["qua"], len(co)), nhom="phu-tuyen", chieu="duong")
            print("  Các tuyến KHÔNG đi qua `truy_van.chay()` (ghi rõ, không giấu — kèm phạm vi §1):")
            for r in co:
                if r["d_chay"] < 1:
                    print("    ! %-5s %-40s → mã %-4s · %s"
                          % (r["method"], r["mau"], r["ma"],
                             _pham_vi_hop_dong(r["mau"], r["method"])))
            _dc_am("phu-tuyen")

        # ── 7. D-8: CSDL NGHIỆP VỤ KHÔNG ĐỔI ────────────────────────────────────────────────
        sau = _dau_van(duong_csdl_that)
        ket("B7o", "D-8: CSDL NGHIỆP VỤ không bị chạm (sha256 · mtime · cỡ y nguyên)",
            DAT if truoc == sau else HONG,
            "%s — trước %s · sau %s" % (duong_csdl_that, truoc, sau))
    except Exception:                                            # noqa: BLE001
        ket("B7z", "Khối B7 NỔ giữa chừng — ghi rõ, KHÔNG im lặng bỏ qua", KHUYET,
            traceback.format_exc()[-1200:])
        kq["ma"] = 1
    finally:
        if that_chay is not None:
            M["truy_van"].chay, M["truy_van"].tim_don = that_chay, that_tim
        if sv is not None:
            sv.shutdown()
            sv.server_close()
        if M.get("csdl") is not None:
            try:
                M["csdl"].dong()
            except Exception:                                    # noqa: BLE001
                pass
        if _hub_data_cu is None:
            os.environ.pop("VIP_HUB_DATA", None)
        else:
            os.environ["VIP_HUB_DATA"] = _hub_data_cu
        if _stderr_cu is not None:
            sys.stderr = _stderr_cu                      # trả lại NGAY, trước khi báo cáo
        _bao_log(im_log)
        con = os.path.isdir(thu_muc)
        shutil.rmtree(thu_muc, ignore_errors=True)
        print("  [dọn] thư mục tạm %s — còn lại: %s" % (thu_muc, os.path.isdir(thu_muc)))
        assert con, "thư mục tạm chưa từng tồn tại ⇒ phép dọn không chứng minh được gì"
    return kq


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

    ma_chot = 0
    # CHỐT CHỐNG ĐỆ QUY: cổng này gọi CHÍNH C5, mà C5 lại gọi bản uỷ quyền → bộ gốc. Nếu bộ gốc
    # (hoặc runner của nó) lỡ gọi lại cổng này thì phải DỪNG ở đây, không được đệ quy vô hạn.
    if os.environ.get("VIP_G22_LONG_NHAU"):
        muc("B1–B5. BỎ QUA — CỔNG NÀY ĐANG ĐƯỢC GỌI LỒNG BÊN TRONG CHÍNH PHÉP ĐO CỦA NÓ")
        ket("B.long", "Phát hiện gọi LỒNG NHAU (`VIP_G22_LONG_NHAU=1`) — không đệ quy", BO_QUA,
            "đây là chốt chống đệ quy, KHÔNG phải một phép đo đạt; lượt chạy NGOÀI mới có phán quyết")
        nguon, _ = _tim_qa_g20(), None
        b1_bo_dem_that()
    elif DO_CAY_KHAC:
        # Đo trên cây KHÁC (`VIP_G22_CAY_APP`) là để lấy ĐỐI CHỨNG cho khối B7, không phải để đo
        # lại C5/G7 — hai phép đo ấy thuộc về cây này và đã có lượt chạy riêng ở trên.
        muc("B1–B5. BỎ QUA — LƯỢT NÀY ĐO CÂY KHÁC (`VIP_G22_CAY_APP=%s`) CHO KHỐI B7" % CAY_DO)
        ket("B.cay-khac", "Lượt đo cây khác chỉ chạy B0 + B7 (đối chứng phủ tuyến/hợp đồng tenant)",
            BO_QUA, "C5/G7 là phép đo của CÂY NÀY; chạy lại trên cây khác là đo nhầm đối tượng")
    else:
        # Bọc phần C5/G7: một sự cố MÔI TRƯỜNG ở đây (ví dụ hai lượt chạy tranh nhau tệp mượn của
        # AG-01) không được phép giết cả cổng TRƯỚC khối B7 — mất B7 là mất phép đo của lượt này,
        # và tệ hơn: cổng chết giữa đường thì dòng tổng kết cuối không bao giờ được in.
        try:
            nguon, _ = b1_bo_dem_that()
            if nguon:
                b2_chieu_xanh(nguon)
                b3_chieu_do(nguon)
            b5_khuon_bao_cao()
        except Exception as e:                                   # noqa: BLE001
            ket("B.loi-moi-truong", "Phần C5/G7 (B1–B5) dừng vì sự cố MÔI TRƯỜNG — ghi rõ, không "
                "im lặng, và vẫn chạy tiếp B7", KHUYET,
                "%s: %s\n%s" % (type(e).__name__, e, traceback.format_exc()[-800:]))

    # B7 chạy SAU cùng: nó đổi `VIP_HUB_DATA` sang thư mục tạm, và các tiến trình con ở B2–B5
    # không được thừa hưởng thư mục ấy.
    if os.environ.get("VIP_G22_LONG_NHAU"):
        muc("B7. BỎ QUA — lượt LỒNG NHAU không đo hợp đồng tenant (lượt NGOÀI đã đo)")
        ket("B7.long", "Không đo hợp đồng tenant ở lượt lồng nhau", BO_QUA,
            "tránh dựng thêm máy chủ + CSDL tạm trong chính phép đo đang chạy")
    else:
        kq7 = b7_hop_dong()
        if kq7["ma"] == MA_CHOT_AN_TOAN:
            ma_chot = MA_CHOT_AN_TOAN

    so = b6_tong_ket(time.time() - t0)
    if ma_chot:
        return ma_chot
    return 1 if (so[HONG] or so[KHUYET]) else 0


if __name__ == "__main__":
    sys.exit(main())
