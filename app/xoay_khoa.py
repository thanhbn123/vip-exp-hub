# XOAY KHÓA CÓ KIỂM SOÁT (G12 / D-2) — AG-05 SECURITY & KEY OPS.
#
# ====== D-2, nguyên văn điều anh Thành duyệt ======
#   "Đồng ý, nhưng KHÓA BẰNG QUYỀN QUẢN TRỊ ĐẶC BIỆT và KIỂM THỬ TRÊN BẢN SAO TRƯỚC."
# Và chỉ thị dự án ghi thêm: "Không xoay khóa THẬT khi chưa kiểm tra phương án khôi phục."
#
# Nên thứ tự ở đây là **bắt buộc**, không phải khuyến nghị:
#     có gói backup kiểm được  →  đã khôi phục thật một lượt, có chứng nhận  →  diễn tập trên
#     BẢN SAO  →  mới được xoay thật.
#
# ====== VÌ SAO FILE NÀY TỒN TẠI, KHI `bao_mat.xoay_khoa()` ĐÃ CHẠY ĐƯỢC ======
# `bao_mat.xoay_khoa()` là **cơ cấu**: nó sinh khóa mới và mã hóa lại. Nó KHÔNG hỏi ai đang gọi,
# KHÔNG hỏi có đường về hay chưa. Gọi nó trên máy chủ thật mà chưa có bản sao lưu kiểm được là
# đặt toàn bộ credentials của mọi tenant lên một lượt ghi không có đường lùi: mã hóa lại hỏng
# giữa đường thì còn cứu được (khóa cũ giữ lại), nhưng **mất thư mục khóa ngay sau đó** thì
# không. File này là **cái van** đặt trước cơ cấu đó.
#
# ====== CHỐT KHÔNG THỂ BỎ QUA BẰNG MỘT CỜ MÔI TRƯỜNG ======
# Mô-đun này **không đọc biến môi trường nào** để quyết định có chạy chốt hay không, và
# `xoay_that()` **không có tham số nào** để tắt chốt. Có ca thử đo đúng điều đó
# (`thu_xoay_khoa.py` lớp `D_ChotKhongBoQuaDuoc`): đặt một loạt biến môi trường trông như cờ
# bỏ qua rồi gọi `xoay_that()` — nó vẫn phải từ chối.
#
# Vì sao viết thành luật: bản đầu của hầu hết chốt chặn đều có một "lối thoát cho trường hợp
# khẩn cấp". Trường hợp khẩn cấp là **đúng lúc** người ta dễ bỏ qua chốt nhất, và cũng là lúc
# hậu quả nặng nhất. Muốn xoay khi chưa đủ điều kiện thì phải đi làm cho đủ điều kiện — tạo gói,
# chạy chứng nhận khôi phục. Mất thêm vài phút, không mất dữ liệu.
#
# ====== THỨ DÙNG ĐỂ KIỂM CHỨNG PHẢI ĐỘC LẬP (CLAUDE.md §12.1) ======
# Ca thật trong vault: bước nghiệm thu của bộ cài TỰ CHẠY HỘ bằng shell có sẵn quyền, nên nó
# LUÔN báo đạt và che mất việc bộ lập lịch không chạy nổi. Chốt ở đây cố ý tránh đúng kiểu đó:
#
#   1. `xoay_khoa.py` **KHÔNG BAO GIỜ tự tạo gói backup.** Không có hàm nào trong file này gọi
#      `sao_luu_khoa.tao_goi()`. Gói phải do người vận hành tạo bằng một lệnh riêng.
#   2. Chứng nhận khôi phục **phải được ghi ở một lượt chạy KHÁC**: chốt từ chối chứng nhận
#      mang `pid` trùng tiến trình đang xoay. Một tiến trình không tự làm chứng cho chính nó.
#   3. Bằng chứng **mạnh nhất không nằm trong file này**: đó là dòng audit `khoi_phuc_khoa` do
#      `sao_luu_khoa` (mô-đun khác, AG-01 sở hữu) ghi vào CSDL. Chốt đòi dòng đó, và đòi nó nhắc
#      đúng tên gói đang dùng.
#
# **GIỚI HẠN PHẢI NÓI RA:** chốt này chặn được việc **quên**, không chặn được người có quyền ghi
# đĩa + ghi CSDL cố tình dựng bằng chứng giả. Bằng chứng thật sự độc lập là một lượt khôi phục
# trên **máy chủ sạch** bằng **passphrase thật** — đó là blocker **B-2** của dự án, vẫn còn
# nguyên. Xem `docs/G12_KEY_OPS.md` mục giới hạn.
#
# ====== CẤM ======
# Không in nội dung khóa, passphrase hay credentials đã giải mã ra báo cáo, log, audit hay
# thông điệp lỗi. Mọi phép so sánh plaintext trong file này làm bằng **digest trong bộ nhớ** của
# tiến trình con, và chỉ **số đếm** đi ra ngoài.
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

import cau_hinh
import csdl
import quyen
import sao_luu_khoa as skb
import secret_provider as sp

# ---------------------------------------------------------------------------------------
# Quyền
# ---------------------------------------------------------------------------------------
# D-2: "khóa bằng quyền quản trị đặc biệt". Đây là quyền MỚI, KHÔNG dùng lại quyền có sẵn.
# `platform.audit.xem` hay `platform.tenant.sua` mà cũng xoay được khóa thì PLATFORM_ADMIN
# xoay được, và D-2 nói "quản trị ĐẶC BIỆT" chứ không phải "quản trị".
QUYEN_XOAY = "platform.khoa.xoay"

# Chỉ PLATFORM_OWNER. Đây là danh sách TRẮNG, và ở đây danh sách trắng là ĐÚNG theo ngoại lệ
# đã nêu sẵn trong CLAUDE.md §12.2: câu hỏi phân biệt là *quên một dòng thì an toàn hay hỏng?*
# Quên một vai trò ở đây ⇒ vai trò đó KHÔNG xoay được khóa ⇒ an toàn, và hỏng ồn ào (có người
# báo "tôi không bấm được"). Dùng danh sách đen mà quên một vai trò ⇒ vai trò lạ xoay được khóa
# của cả nền tảng ⇒ hỏng im lặng.
VAI_TRO_DUOC_XOAY = ("PLATFORM_OWNER",)

# HAI lớp kiểm, cố ý: (1) vai trò nền tảng phải nằm trong hằng số trên — hằng số trong MÃ, không
# ai sửa được bằng một dòng UPDATE; (2) quyền phải có thật trong `role_permissions` — nguồn chân
# lý RBAC của hệ. Lớp (1) có nghĩa: dù AG-00 lỡ seed `platform.khoa.xoay` cho PLATFORM_ADMIN thì
# ADMIN vẫn KHÔNG xoay được. Đây không phải "lọc hai chỗ" mà §12.2 cấm — hai lớp đo HAI thứ khác
# nhau (danh tính vai trò / cấu hình quyền), nên chúng không che nhau.

# ---------------------------------------------------------------------------------------
# Chứng nhận khôi phục
# ---------------------------------------------------------------------------------------
TEN_CHUNG_NHAN = "chung-nhan-khoi-phuc.json"
PHIEN_BAN_CHUNG_NHAN = 1
# Chứng nhận quá hạn thì không còn nói gì về gói HÔM NAY. 30 ngày là mức bảo thủ; sửa ở đây,
# đừng rải con số ra nơi khác.
HAN_CHUNG_NHAN_NGAY = 30
KHUON_GIO = "%Y-%m-%d %H:%M:%S%z"


class LoiXoayKhoa(Exception):
    """Lỗi xoay khóa. Thông điệp KHÔNG BAO GIỜ chứa khóa, passphrase hay credentials."""


def _bay_gio():
    return datetime.now().astimezone()


def _doc_gio(s):
    return datetime.strptime(s, KHUON_GIO)


def dau_van_tay_goi(duong_goi) -> dict:
    """sha256 + kích thước của FILE gói, để buộc chứng nhận vào đúng gói đó.

    Buộc bằng nội dung chứ không bằng tên file: đổi tên một gói cũ thành tên gói mới là chuyện
    xảy ra được, và nó sẽ làm chứng nhận nói về một gói không còn là gói đang dùng.
    """
    duong_goi = os.path.abspath(duong_goi)
    h = hashlib.sha256()
    with open(duong_goi, "rb") as f:
        for khoi in iter(lambda: f.read(65536), b""):
            h.update(khoi)
    return {"duong": duong_goi, "ten": os.path.basename(duong_goi),
            "sha256": h.hexdigest(), "so_byte": os.path.getsize(duong_goi)}


# ---------------------------------------------------------------------------------------
# Bước 1 của chốt: gói có phủ đúng những khóa mà DỮ LIỆU SỐNG đang dùng không?
# ---------------------------------------------------------------------------------------
def key_id_dang_dung(kn=None) -> dict:
    """Mọi key_id xuất hiện trong bản mã của CSDL SỐNG, kèm số bản mã mỗi khóa.

    `sao_luu_khoa.kiem_toan_ven()` đã kiểm "bản mã TRONG GÓI có đủ khóa chưa" — nhưng gói là bản
    chụp của một thời điểm. Giữa lúc tạo gói và lúc xoay, hệ có thể đã ghi thêm secret dưới một
    khóa khác. Nên phải hỏi lại CSDL SỐNG, không hỏi lại cái gói.

    `None` trong kết quả = bản mã định dạng v1/v2 (không mang key_id) — chúng đọc bằng file khóa
    một-bản `khoa-noi-bo.key`, nên gói phải có `khoa_cu`.
    """
    import bao_mat
    doc = (lambda sql: csdl.nhieu(sql)) if kn is None else (lambda sql: kn.execute(sql).fetchall())
    dem = {}
    for r in doc("SELECT credentials_ma_hoa, webhook_secret_ma_hoa FROM carrier_accounts"):
        for cot in ("credentials_ma_hoa", "webhook_secret_ma_hoa"):
            bm = r[cot]
            if bm in (None, ""):
                continue
            kid = bao_mat.key_id_cua(bm)
            dem[kid] = dem.get(kid, 0) + 1
    return dem


def goi_co_phu_du_khong(duong_goi, passphrase=None, cho_nhap=True, kn=None) -> dict:
    """Gói có chứa MỌI khóa mà bản mã sống đang tham chiếu không?

    Thiếu một khóa ở đây nghĩa là: mất đĩa → khôi phục từ gói → những bản mã dưới khóa thiếu
    **vĩnh viễn không giải được**, và không có gì báo cho tới lượt gọi hãng đầu tiên.
    """
    kq = skb.kiem_toan_ven(duong_goi, passphrase, cho_nhap=cho_nhap)
    co = set(kq["key_id"])
    dang_dung = key_id_dang_dung(kn)
    thieu = sorted(k for k in dang_dung if k is not None and k not in co)
    can_khoa_cu = None in dang_dung
    if can_khoa_cu and not kq["co_khoa_cu"]:
        thieu.append("<khoa-noi-bo.key cho bản mã v1/v2>")
    return {"dat": kq["dat"] and not thieu, "loi_goi": kq["loi"], "key_id_thieu_so_voi_csdl": thieu,
            "key_id_trong_goi": kq["key_id"], "key_id_csdl_dang_dung": {str(k): v for k, v in
                                                                        sorted(dang_dung.items(),
                                                                               key=lambda x: str(x[0]))},
            "co_khoa_cu": kq["co_khoa_cu"], "can_khoa_cu": can_khoa_cu,
            "so_ban_ma_trong_goi": kq["so_ban_ma"], "tao_luc_goi": kq["tao_luc"]}


# ---------------------------------------------------------------------------------------
# Bước 2 của chốt: ghi chứng nhận khôi phục — KHÔI PHỤC THẬT rồi GIẢI MÃ LẠI
# ---------------------------------------------------------------------------------------
def ghi_chung_nhan_khoi_phuc(duong_goi, duong_chung_nhan=None, passphrase=None,
                             cho_nhap=True) -> dict:
    """Khôi phục gói vào thư mục CÔ LẬP, giải mã lại CẢ HAI đường, rồi ghi chứng nhận.

    Đây là lượt chạy mà **người vận hành phải tự khởi động**, bằng lệnh riêng. `xoay_that()`
    KHÔNG gọi hàm này — một tiến trình không được vừa làm chứng vừa thi hành.

    Phép đo quyết định là bước 3: **số dòng khớp KHÔNG chứng minh khôi phục thành công.** CSDL về
    đủ mà khóa lệch thì credentials thành rác, `integrity_check` vẫn `ok`, và không gì báo cho
    tới lượt gọi hãng đầu tiên. Nên ở đây đo bằng cách GIẢI MÃ THẬT, và đo **cả hai** đường
    (`giai_ma_cred` dùng AAD `cred:<tenant>:<hang>`, `giai_ma_wh` dùng AAD `wh:<webhook_ma>` —
    hai AAD khác nhau, đo một đường rồi kết luận cho cả hai là vượt phạm vi §12.1 luật 3).

    KHÔNG ghi plaintext ra đâu cả: chỉ đếm số bản giải được / không giải được.
    """
    import bao_mat
    van_tay = dau_van_tay_goi(duong_goi)
    if duong_chung_nhan is None:
        duong_chung_nhan = os.path.join(os.path.dirname(van_tay["duong"]), TEN_CHUNG_NHAN)
    duong_chung_nhan = os.path.abspath(duong_chung_nhan)

    # 1. Kiểm toàn vẹn TRƯỚC khi tin gói (§12.1: kiểm thứ dùng để kiểm chứng, trước khi tin nó).
    toan_ven = skb.kiem_toan_ven(duong_goi, passphrase, cho_nhap=cho_nhap)

    nen = tempfile.mkdtemp(prefix="vip-chungnhan-khoiphuc-")
    try:
        dich = os.path.join(nen, "khoa")
        kp = skb.khoi_phuc(duong_goi, dich, passphrase, ghi_de=False, cho_nhap=cho_nhap,
                           duong_khoa_cu_dich=os.path.join(nen, "khoa-noi-bo.key"))
        # 2. Dựng nhà cung cấp khóa TỪ THƯ MỤC VỪA KHÔI PHỤC — không dùng khóa đang chạy.
        nguoi_cu = sp.nha_cung_cap()
        sp.dat_nha_cung_cap(sp.LocalSecretProvider(
            thu_muc=dich, duong_khoa_cu=os.path.join(nen, "khoa-noi-bo.key")))
        cred_dat = cred_hong = wh_dat = wh_hong = 0
        ly_do = []
        try:
            for r in skb.rang_buoc_ban_ma(duong_goi, passphrase, cho_nhap=cho_nhap):
                if r.get("credentials_ma_hoa"):
                    try:
                        d = bao_mat.giai_ma_cred(r["credentials_ma_hoa"], r["tenant_id"], r["hang"])
                        cred_dat += 1 if isinstance(d, dict) else 0
                        cred_hong += 0 if isinstance(d, dict) else 1
                    except Exception as e:   # KHÔNG nuốt — ghi loại lỗi, không ghi nội dung
                        cred_hong += 1
                        ly_do.append(f"cred id={r['id']}: {type(e).__name__}")
                if r.get("webhook_secret_ma_hoa"):
                    try:
                        s = bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], r["webhook_ma"])
                        wh_dat += 1 if isinstance(s, str) and s != "" else 0
                        wh_hong += 0 if isinstance(s, str) and s != "" else 1
                    except Exception as e:
                        wh_hong += 1
                        ly_do.append(f"wh id={r['id']}: {type(e).__name__}")
        finally:
            sp.dat_nha_cung_cap(nguoi_cu)
    finally:
        shutil.rmtree(nen, ignore_errors=True)

    dat = bool(toan_ven["dat"] and kp["dat"] and not cred_hong and not wh_hong
               and (cred_dat > 0) and (wh_dat > 0))
    cn = {
        "phien_ban": PHIEN_BAN_CHUNG_NHAN,
        "luc": _bay_gio().strftime(KHUON_GIO),
        "pid": os.getpid(),          # để chốt từ chối chứng nhận do CHÍNH tiến trình xoay dựng
        "may": os.uname().nodename,
        "goi": {k: van_tay[k] for k in ("ten", "sha256", "so_byte")},
        "toan_ven_goi": {"dat": toan_ven["dat"], "loi": toan_ven["loi"],
                         "so_khoa": toan_ven["so_khoa"], "key_id": toan_ven["key_id"],
                         "tao_luc_goi": toan_ven["tao_luc"]},
        "khoi_phuc": {"dat": kp["dat"], "so_khoa_da_ghi": len(kp["da_ghi"]),
                      "con_tro_hien_hanh": kp["con_tro_hien_hanh"], "loi": kp["loi"]},
        "giai_ma_lai": {"cred_dat": cred_dat, "cred_hong": cred_hong,
                        "wh_dat": wh_dat, "wh_hong": wh_hong, "ly_do_hong": ly_do},
        "ket_qua": "dat" if dat else "khong_dat",
        # Nói thẳng phạm vi ngay TRONG chứng nhận, để ai đọc nó về sau không suy rộng (§12.1 l.5).
        "pham_vi": ("Khôi phục vào thư mục tạm CÔ LẬP trên máy này, giải mã lại bản mã NẰM TRONG "
                    "GÓI. KHÔNG phải lượt khôi phục trên máy chủ sạch bằng passphrase thật "
                    "(blocker B-2). KHÔNG đo CSDL, KHÔNG đo dữ liệu nghiệp vụ."),
    }
    _ghi_json_nguyen_tu(duong_chung_nhan, cn)
    _audit("chung_nhan_khoi_phuc_khoa", f"goi:{van_tay['ten']}",
           f"gói sha256 {van_tay['sha256'][:16]}…; giải mã lại {cred_dat} cred + {wh_dat} webhook"
           f" secret; hỏng {cred_hong}/{wh_hong}",
           ket_qua="thanh_cong" if dat else "that_bai")
    cn["duong_chung_nhan"] = duong_chung_nhan
    return cn


def _ghi_json_nguyen_tu(duong, doi_tuong):
    """Ghi file tạm cùng thư mục rồi `os.replace` — §16.3. Quyền đặt TRƯỚC khi đổi tên."""
    import secrets
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam-" + secrets.token_hex(4)
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(doi_tuong, f, ensure_ascii=False, indent=2)
    os.chmod(tam, 0o600)
    os.replace(tam, duong)


def _audit(hanh_dong, doi_tuong, chi_tiet, user_id=None, dia_chi=None, ket_qua="thanh_cong"):
    """Ghi audit nếu CSDL dùng được; hỏng thì IN RA stderr, không nuốt im lặng (§12.2)."""
    try:
        csdl.audit(hanh_dong, doi_tuong, chi_tiet, user_id=user_id, dia_chi=dia_chi,
                   ket_qua=ket_qua)
        return True
    except Exception as e:
        sys.stderr.write(f"[xoay_khoa] KHÔNG ghi được audit ({type(e).__name__}: {e}) — "
                         f"việc vẫn làm: {hanh_dong} {doi_tuong}\n")
        return False


def doc_chung_nhan(duong) -> dict:
    with open(duong, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------------------
# CHỐT — chỉ ĐỌC. Không tạo gói, không tạo chứng nhận, không sửa gì.
# ---------------------------------------------------------------------------------------
def kiem_chot(duong_goi, duong_chung_nhan=None, passphrase=None, cho_nhap=True) -> dict:
    """Sáu điều kiện. Thiếu MỘT là không xoay. Hàm này KHÔNG ghi gì, KHÔNG tạo gì.

    Cố ý không có tham số nào để bỏ qua, và cố ý không đọc biến môi trường nào.
    """
    dieu_kien = []

    def them(ma, mo_ta, dat, bang_chung):
        dieu_kien.append({"ma": ma, "mo_ta": mo_ta, "dat": bool(dat), "bang_chung": bang_chung})

    # C1 — gói tồn tại và đọc được header (không cần passphrase).
    try:
        van_tay = dau_van_tay_goi(duong_goi)
        h = skb.doc_header(van_tay["duong"])["header"]
        them("C1", "Gói backup tồn tại, đúng khuôn .vipkb", True,
             f"{van_tay['ten']} · {van_tay['so_byte']} byte · tạo {h.get('tao_luc')}"
             f" · sha256 {van_tay['sha256'][:16]}…")
    except Exception as e:
        them("C1", "Gói backup tồn tại, đúng khuôn .vipkb", False, f"{type(e).__name__}: {e}")
        return _ket_chot(dieu_kien, duong_goi, None)

    if duong_chung_nhan is None:
        duong_chung_nhan = os.path.join(os.path.dirname(van_tay["duong"]), TEN_CHUNG_NHAN)

    # C2 — gói MỞ ĐƯỢC và toàn vẹn, VÀ phủ đủ mọi khóa CSDL sống đang dùng.
    try:
        phu = goi_co_phu_du_khong(duong_goi, passphrase, cho_nhap=cho_nhap)
        them("C2", "Gói mở được, toàn vẹn, và phủ đủ khóa CSDL sống đang dùng", phu["dat"],
             f"khóa trong gói {phu['key_id_trong_goi']}; CSDL đang dùng "
             f"{phu['key_id_csdl_dang_dung']}; thiếu {phu['key_id_thieu_so_voi_csdl'] or 'không'}"
             + (f"; lỗi gói {phu['loi_goi']}" if phu["loi_goi"] else ""))
    except Exception as e:
        them("C2", "Gói mở được, toàn vẹn, và phủ đủ khóa CSDL sống đang dùng", False,
             f"{type(e).__name__}: {e}")

    # C3 — có chứng nhận khôi phục, ĐẠT, và buộc đúng vào GÓI NÀY (so bằng sha256, không bằng tên).
    cn = None
    try:
        cn = doc_chung_nhan(duong_chung_nhan)
        khop = cn.get("goi", {}).get("sha256") == van_tay["sha256"]
        them("C3", "Có chứng nhận khôi phục ĐẠT, buộc đúng vào gói này (sha256)",
             cn.get("ket_qua") == "dat" and khop and cn.get("phien_ban") == PHIEN_BAN_CHUNG_NHAN,
             f"{os.path.basename(duong_chung_nhan)} · kết quả {cn.get('ket_qua')}"
             f" · sha256 khớp {khop} · giải mã lại "
             f"cred {cn.get('giai_ma_lai', {}).get('cred_dat')}/"
             f"hỏng {cn.get('giai_ma_lai', {}).get('cred_hong')}, "
             f"wh {cn.get('giai_ma_lai', {}).get('wh_dat')}/"
             f"hỏng {cn.get('giai_ma_lai', {}).get('wh_hong')}")
    except Exception as e:
        them("C3", "Có chứng nhận khôi phục ĐẠT, buộc đúng vào gói này (sha256)", False,
             f"không đọc được {duong_chung_nhan}: {type(e).__name__}")

    # C4 — chứng nhận còn hạn.
    if cn:
        try:
            tuoi = _bay_gio() - _doc_gio(cn["luc"])
            them("C4", f"Chứng nhận còn hạn (≤ {HAN_CHUNG_NHAN_NGAY} ngày)",
                 timedelta(0) <= tuoi <= timedelta(days=HAN_CHUNG_NHAN_NGAY),
                 f"ghi lúc {cn['luc']}, cách đây {tuoi.days} ngày")
        except Exception as e:
            them("C4", f"Chứng nhận còn hạn (≤ {HAN_CHUNG_NHAN_NGAY} ngày)", False,
                 f"mốc thời gian không đọc được: {type(e).__name__}")
    else:
        them("C4", f"Chứng nhận còn hạn (≤ {HAN_CHUNG_NHAN_NGAY} ngày)", False, "không có chứng nhận")

    # C5 — ĐỘC LẬP: chứng nhận phải do một LƯỢT CHẠY KHÁC ghi ra.
    # Đây là chốt chống đúng ca đã xảy ra thật trong vault: bước nghiệm thu tự chạy hộ nên luôn
    # báo đạt. Một tiến trình không được vừa làm chứng vừa thi hành.
    them("C5", "Chứng nhận do lượt chạy KHÁC ghi (pid khác tiến trình đang xoay)",
         bool(cn) and cn.get("pid") != os.getpid(),
         f"pid chứng nhận {cn.get('pid') if cn else None} · pid hiện tại {os.getpid()}")

    # C6 — NHÂN CHỨNG NGOÀI: dòng audit `khoi_phuc_khoa` do `sao_luu_khoa` (mô-đun KHÁC) ghi.
    # Chứng nhận là file do chính mô-đun này ghi; audit là dấu vết do mô-đun khác ghi vào CSDL.
    try:
        r = csdl.mot("SELECT luc, chi_tiet FROM audit WHERE hanh_dong='khoi_phuc_khoa'"
                     " AND ket_qua='thanh_cong' AND chi_tiet LIKE ?"
                     " ORDER BY id DESC LIMIT 1", (f"%{van_tay['ten']}%",))
        them("C6", "CSDL có dấu vết `khoi_phuc_khoa` của chính gói này (do sao_luu_khoa ghi)",
             r is not None, (f"audit lúc {r['luc']}" if r else
                             f"không có dòng audit nào nhắc {van_tay['ten']}"))
    except Exception as e:
        them("C6", "CSDL có dấu vết `khoi_phuc_khoa` của chính gói này (do sao_luu_khoa ghi)",
             False, f"không tra được audit: {type(e).__name__}")

    return _ket_chot(dieu_kien, duong_goi, duong_chung_nhan)


def _ket_chot(dieu_kien, duong_goi, duong_chung_nhan):
    hong = [d["ma"] for d in dieu_kien if not d["dat"]]
    return {"dat": not hong, "chua_dat": hong, "dieu_kien": dieu_kien,
            "duong_goi": os.path.abspath(duong_goi),
            "duong_chung_nhan": duong_chung_nhan,
            "so_dieu_kien": len(dieu_kien)}


# ---------------------------------------------------------------------------------------
# Quyền
# ---------------------------------------------------------------------------------------
def kiem_quyen(nc=None, user_id=None) -> dict:
    """Hai lớp: vai trò nền tảng nằm trong hằng số MÃ, và quyền có thật trong `role_permissions`.

    `nc` là `bao_mat.NguCanh` (đường HTTP). `user_id` là đường dòng lệnh — tra thẳng CSDL.
    """
    if nc is not None:
        vai_tro = nc.user["platform_role"]
        uid = nc.user_id
    elif user_id is not None:
        u = csdl.mot("SELECT id, platform_role, trang_thai FROM users WHERE id=?", (user_id,))
        if u is None:
            raise LoiXoayKhoa(f"không có user id={user_id}")
        if u["trang_thai"] == "khoa":
            raise LoiXoayKhoa(f"user id={user_id} đang bị khóa")
        vai_tro, uid = u["platform_role"], u["id"]
    else:
        raise LoiXoayKhoa("phải nói rõ AI xoay: truyền `nc` (ngữ cảnh phiên) hoặc `user_id`")

    if vai_tro not in VAI_TRO_DUOC_XOAY:
        raise LoiXoayKhoa(
            f"TỪ CHỐI: xoay khóa mã hóa chỉ dành cho {'/'.join(VAI_TRO_DUOC_XOAY)}; "
            f"user id={uid} có vai trò nền tảng {vai_tro!r}. (D-2: quyền quản trị ĐẶC BIỆT)")
    if not quyen.co_quyen(vai_tro, QUYEN_XOAY):
        raise LoiXoayKhoa(
            f"TỪ CHỐI: vai trò {vai_tro} chưa được cấp quyền {QUYEN_XOAY!r} trong "
            "`role_permissions`. Quyền này do AG-00 seed; chưa seed thì chưa xoay được — "
            "CỐ Ý không tự seed ở đây.")
    return {"user_id": uid, "vai_tro": vai_tro, "quyen": QUYEN_XOAY}


# ---------------------------------------------------------------------------------------
# DIỄN TẬP TRÊN BẢN SAO (D-2: "kiểm thử trên bản sao trước")
# ---------------------------------------------------------------------------------------
# Chạy trong TIẾN TRÌNH CON, không trong tiến trình này. Lý do đo được: `secret_provider` giữ
# một nhà cung cấp dùng chung cho cả tiến trình, `csdl` giữ kết nối theo thread trỏ vào
# `cau_hinh.DUONG_DAN_CSDL` tính lúc import, và `bao_mat._khoa_noi_bo()` đọc
# `cau_hinh.DUONG_DAN_KHOA`. Lắp lại ba thứ đó trong tiến trình đang chạy là vá tạm, và một chỗ
# sót là lượt "diễn tập" sẽ ghi vào dữ liệu THẬT. Tiến trình con với `VIP_HUB_DATA` riêng thì
# cách ly là do HỆ ĐIỀU HÀNH cưỡng chế, không do mình nhớ.

def dien_tap(thu_muc_nguon=None, giu_ban_sao=False) -> dict:
    """Chép CSDL + thư mục khóa sang thư mục tạm, XOAY ở đó, rồi nghiệm thu.

    Nghiệm thu đo **cả hai** đường giải mã sau khi xoay, so với trạng thái TRƯỚC khi xoay bằng
    digest trong bộ nhớ của tiến trình con — chỉ **số đếm** đi ra ngoài, không plaintext.

    Hàm này KHÔNG chạm nguồn: nó chỉ đọc. Có chốt từ chối nếu thư mục tạm nằm trong nguồn.
    """
    nguon = os.path.abspath(thu_muc_nguon or cau_hinh.THU_MUC_DU_LIEU)
    if not os.path.isdir(nguon):
        raise LoiXoayKhoa(
            f"không thấy thư mục dữ liệu nguồn {nguon}. CỐ Ý không tự tạo: tạo ra một thư mục "
            "rỗng rồi 'diễn tập' trên đó là diễn tập không đo gì cả.")
    if not os.path.isdir(os.path.join(nguon, "khoa")) and not os.path.exists(
            os.path.join(nguon, os.path.basename(cau_hinh.DUONG_DAN_KHOA))):
        raise LoiXoayKhoa(f"{nguon} không có thư mục `khoa/` lẫn `khoa-noi-bo.key` — không có gì để xoay")

    nen = tempfile.mkdtemp(prefix="vip-dientap-xoaykhoa-")
    if os.path.abspath(nen).startswith(nguon + os.sep):
        shutil.rmtree(nen, ignore_errors=True)
        raise LoiXoayKhoa(f"TỪ CHỐI: nền tạm {nen} nằm TRONG nguồn {nguon} — diễn tập sẽ ghi vào "
                          "dữ liệu thật. Đặt TMPDIR ra ngoài rồi chạy lại.")
    ban_sao = os.path.join(nen, "du-lieu")
    try:
        da_chep = _chep_nguon(nguon, ban_sao)
        con = subprocess.run(
            [sys.executable, os.path.abspath(__file__), "_chay-tren-ban-sao"],
            cwd=cau_hinh.THU_MUC_GOC, capture_output=True, text=True,
            env=dict(os.environ, VIP_HUB_DATA=ban_sao,
                     PYTHONPATH=cau_hinh.THU_MUC_APP, PYTHONDONTWRITEBYTECODE="1"))
        if con.returncode != 0:
            raise LoiXoayKhoa(
                f"lượt xoay trên bản sao HỎNG (mã thoát {con.returncode}). stderr: "
                f"{con.stderr.strip()[-2000:]}")
        try:
            kq = json.loads(con.stdout)
        except json.JSONDecodeError:
            raise LoiXoayKhoa(f"tiến trình con không trả JSON. stdout: {con.stdout[-1000:]}") from None
        kq["ban_sao"] = ban_sao
        kq["nguon"] = nguon
        kq["da_chep"] = da_chep
        kq["nguon_con_nguyen"] = _anh_thu_muc(nguon) == da_chep["anh_nguon"]
        return kq
    finally:
        if not giu_ban_sao:
            shutil.rmtree(nen, ignore_errors=True)


def _anh_thu_muc(thu_muc) -> dict:
    """Ảnh chụp tên file + kích thước + quyền của thư mục khóa. KHÔNG đọc nội dung khóa."""
    anh = {}
    for goc, _, files in os.walk(thu_muc):
        for t in sorted(files):
            d = os.path.join(goc, t)
            if t.endswith((".db", ".db-wal", ".db-shm")):
                continue       # CSDL đổi byte vì WAL ngay cả khi chỉ đọc — không dùng để so
            try:
                st = os.stat(d)
            except OSError:
                continue
            anh[os.path.relpath(d, thu_muc)] = [st.st_size, oct(st.st_mode & 0o777)]
    return anh


def _chep_nguon(nguon, ban_sao) -> dict:
    """Chép CSDL + thư mục khóa + khóa một-bản cũ sang bản sao. Chỉ ĐỌC nguồn."""
    anh_nguon = _anh_thu_muc(nguon)
    os.makedirs(ban_sao, exist_ok=True)
    os.chmod(ban_sao, 0o700)
    chep = []
    ten_db = os.path.basename(cau_hinh.DUONG_DAN_CSDL)
    for t in (ten_db, ten_db + "-wal", ten_db + "-shm",
              os.path.basename(cau_hinh.DUONG_DAN_KHOA)):
        d = os.path.join(nguon, t)
        if os.path.exists(d):
            shutil.copy2(d, os.path.join(ban_sao, t))
            chep.append(t)
    t_khoa = os.path.join(nguon, "khoa")
    so_khoa = 0
    if os.path.isdir(t_khoa):
        shutil.copytree(t_khoa, os.path.join(ban_sao, "khoa"))
        os.chmod(os.path.join(ban_sao, "khoa"), 0o700)
        so_khoa = len([t for t in os.listdir(t_khoa) if t.endswith(sp.DUOI_KHOA)])
    return {"file_da_chep": chep, "so_khoa_da_chep": so_khoa, "anh_nguon": anh_nguon}


def _chay_tren_ban_sao() -> int:
    """CHẠY TRONG TIẾN TRÌNH CON, `VIP_HUB_DATA` đã trỏ vào BẢN SAO. In JSON ra stdout.

    Chốt cuối cùng trước khi ghi: nếu `VIP_HUB_DATA` chưa được đặt, hoặc nó trỏ vào thư mục dữ
    liệu mặc định, thì DỪNG. Đây là cùng loại chốt với `dien_tap_khoi_phuc.sh` của G11 — chốt
    bằng CẤU TRÚC, không bằng lời dặn.
    """
    import bao_mat
    nen = os.environ.get("VIP_HUB_DATA")
    if not nen:
        sys.stderr.write("TU CHOI: thieu VIP_HUB_DATA — tien trinh con nay chi chay tren BAN SAO.\n")
        return 9
    mac_dinh = os.path.abspath(os.path.join(cau_hinh.THU_MUC_APP, "du-lieu"))
    if os.path.abspath(nen) == mac_dinh:
        sys.stderr.write(f"TU CHOI: VIP_HUB_DATA tro vao thu muc du lieu MAC DINH ({mac_dinh}).\n")
        return 9
    csdl.mo()
    p = sp.nha_cung_cap()
    key_id_truoc = p.khoa_hien_hanh()[0]
    ds_khoa_truoc = p.danh_sach_key_id()

    # TRƯỚC khi xoay: giải mã mọi bản mã, giữ DIGEST (không giữ plaintext).
    truoc = _digest_moi_ban_ma()
    kq = bao_mat.xoay_khoa(user_id=None, dia_chi="dien-tap-ban-sao")
    sau = _digest_moi_ban_ma()

    ds_khoa_sau = p.danh_sach_key_id()
    khop = sum(1 for k, v in truoc.items() if sau.get(k) == v and v is not None)
    lech = sorted(k for k, v in truoc.items() if sau.get(k) != v)
    khong_giai_duoc_sau = sorted(k for k, v in sau.items() if v is None)
    con_key_cu = sorted(set(ds_khoa_truoc) - set(ds_khoa_sau))

    # Còn bản mã nào mang key_id cũ sau khi xoay không? (phải rỗng, trừ khi có hàng hỏng)
    con_cu = [k for k in key_id_dang_dung() if k != kq["key_id"]]

    ra = {
        "key_id_truoc": key_id_truoc, "key_id_sau": kq["key_id"],
        "so_khoa_truoc": len(ds_khoa_truoc), "so_khoa_sau": len(ds_khoa_sau),
        "khoa_cu_bi_xoa": con_key_cu,            # PHẢI rỗng — xoay không được xóa khóa cũ
        "so_hang_carrier_account": kq["so_hang_da_doc"],
        "so_credentials_ma_hoa_lai": kq["so_credentials"],
        "so_webhook_secret_ma_hoa_lai": kq["so_webhook_secret"],
        "hong_khi_ma_hoa_lai": kq["hong"],
        "so_ban_ma_do": len(truoc),
        "so_ban_ma_giai_lai_KHOP": khop,
        "ban_ma_LECH_noi_dung": lech,            # PHẢI rỗng
        "ban_ma_KHONG_giai_duoc_sau_xoay": khong_giai_duoc_sau,   # PHẢI rỗng
        "key_id_con_sot_sau_xoay": [str(k) for k in con_cu],
        "duong_giai_ma_da_do": ["giai_ma_cred", "giai_ma_wh"],
    }
    ra["dat"] = bool(not lech and not khong_giai_duoc_sau and not con_key_cu
                     and not kq["hong"] and khop == len(truoc) and len(truoc) > 0)
    print(json.dumps(ra, ensure_ascii=False))
    return 0


def _digest_moi_ban_ma() -> dict:
    """{'cred:<id>'|'wh:<id>': sha256(plaintext) hoặc None nếu KHÔNG giải được}.

    Giữ digest chứ không giữ plaintext, và digest cũng KHÔNG ra khỏi tiến trình con — hàm gọi
    chỉ lấy số đếm. Dùng để trả lời đúng một câu: nội dung TRƯỚC và SAU khi xoay có còn là một
    hay không. Số dòng khớp không trả lời được câu đó.
    """
    import bao_mat
    ra = {}
    for r in csdl.nhieu("SELECT id, tenant_id, hang, webhook_ma, credentials_ma_hoa,"
                        " webhook_secret_ma_hoa FROM carrier_accounts ORDER BY id"):
        for khoa_ra, bm, giai in (
            (f"cred:{r['id']}", r["credentials_ma_hoa"],
             lambda x: json.dumps(bao_mat.giai_ma_cred(x, r["tenant_id"], r["hang"]),
                                  ensure_ascii=False, sort_keys=True)),
            (f"wh:{r['id']}", r["webhook_secret_ma_hoa"],
             lambda x: bao_mat.giai_ma_wh(x, r["webhook_ma"])),
        ):
            if bm in (None, ""):
                continue
            try:
                ra[khoa_ra] = hashlib.sha256(giai(bm).encode()).hexdigest()
            except Exception:
                # KHÔNG nuốt im lặng: None là một GIÁ TRỊ có nghĩa ở đây ("không giải được"),
                # và nó được báo ra trong `ban_ma_KHONG_giai_duoc_sau_xoay`.
                ra[khoa_ra] = None
    return ra


# ---------------------------------------------------------------------------------------
# XOAY THẬT — chỉ chạy khi chốt ĐẠT. Không có tham số nào bỏ qua chốt.
# ---------------------------------------------------------------------------------------
def xoay_that(duong_goi, duong_chung_nhan=None, nc=None, user_id=None, dia_chi=None,
              passphrase=None, cho_nhap=True) -> dict:
    """Xoay khóa trên dữ liệu ĐANG CHẠY. Đi qua: quyền → chốt → xoay → nghiệm thu sau xoay.

    KHÔNG có tham số `bo_qua_chot`, và mô-đun này không đọc biến môi trường nào để nới chốt.
    Muốn xoay mà chốt chưa đạt thì đi làm cho đủ: tạo gói, chạy `chung-nhan`.

    Khóa cũ GIỮ LẠI — `bao_mat.xoay_khoa()` cố ý không xóa, và hàm này kiểm lại điều đó sau khi
    xoay thay vì tin nó.
    """
    import bao_mat
    ai = kiem_quyen(nc=nc, user_id=user_id)
    chot = kiem_chot(duong_goi, duong_chung_nhan, passphrase, cho_nhap=cho_nhap)
    if not chot["dat"]:
        _audit("xoay_khoa_tu_choi", "khoa:-",
               f"chốt CHƯA ĐẠT: {', '.join(chot['chua_dat'])}; gói "
               f"{os.path.basename(chot['duong_goi'])}",
               user_id=ai["user_id"], dia_chi=dia_chi, ket_qua="tu_choi")
        raise LoiXoayKhoa(
            "TỪ CHỐI xoay khóa — chốt chưa đạt: " + ", ".join(chot["chua_dat"]) + ".\n"
            + "\n".join(f"  {d['ma']} {'ĐẠT ' if d['dat'] else 'CHƯA'} · {d['mo_ta']}"
                        f"\n       {d['bang_chung']}" for d in chot["dieu_kien"]))

    p = sp.nha_cung_cap()
    ds_truoc = p.danh_sach_key_id()
    key_id_truoc = p.khoa_hien_hanh()[0]
    kq = bao_mat.xoay_khoa(user_id=ai["user_id"], dia_chi=dia_chi)

    # NGHIỆM THU SAU XOAY — không tin lượt xoay, đo lại.
    ds_sau = p.danh_sach_key_id()
    mat_khoa_cu = sorted(set(ds_truoc) - set(ds_sau))
    cred_dat = cred_hong = wh_dat = wh_hong = 0
    for r in csdl.nhieu("SELECT id, tenant_id, hang, webhook_ma, credentials_ma_hoa,"
                        " webhook_secret_ma_hoa FROM carrier_accounts"):
        if r["credentials_ma_hoa"]:
            try:
                bao_mat.giai_ma_cred(r["credentials_ma_hoa"], r["tenant_id"], r["hang"])
                cred_dat += 1
            except Exception:
                cred_hong += 1
        if r["webhook_secret_ma_hoa"]:
            try:
                bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], r["webhook_ma"])
                wh_dat += 1
            except Exception:
                wh_hong += 1

    kq.update({
        "ai_xoay": ai, "chot": {"dat": True, "so_dieu_kien": chot["so_dieu_kien"],
                                "goi": os.path.basename(chot["duong_goi"])},
        "khoa_cu_bi_mat": mat_khoa_cu, "so_khoa_truoc": len(ds_truoc), "so_khoa_sau": len(ds_sau),
        "key_id_truoc": key_id_truoc,
        "nghiem_thu_sau_xoay": {"cred_giai_duoc": cred_dat, "cred_hong": cred_hong,
                                "wh_giai_duoc": wh_dat, "wh_hong": wh_hong},
    })
    kq["dat"] = bool(not kq["hong"] and not mat_khoa_cu and not cred_hong and not wh_hong)
    _audit("xoay_khoa_nghiem_thu", f"khoa:{kq['key_id']}",
           f"từ {key_id_truoc}; giữ {len(ds_sau)} khóa (mất {len(mat_khoa_cu)}); sau xoay giải "
           f"được {cred_dat} cred + {wh_dat} webhook secret, hỏng {cred_hong}/{wh_hong}",
           user_id=ai["user_id"], dia_chi=dia_chi,
           ket_qua="thanh_cong" if kq["dat"] else "that_bai")
    return kq


# ---------------------------------------------------------------------------------------
# Chạy tay
# ---------------------------------------------------------------------------------------
_DUNG = f"""XOAY KHÓA CÓ KIỂM SOÁT (G12 / D-2)

  python3 app/xoay_khoa.py dien-tap [thu-muc-du-lieu-nguon]
        Chép CSDL + khóa sang thư mục tạm, XOAY ở BẢN SAO, nghiệm thu cả hai đường giải mã.
        KHÔNG chạm nguồn. Đây là bước D-2 bắt buộc: "kiểm thử trên bản sao trước".

  python3 app/xoay_khoa.py chung-nhan <goi{skb.DUOI_GOI}> [duong-chung-nhan.json]
        Khôi phục gói vào thư mục CÔ LẬP, giải mã lại cả hai đường, ghi chứng nhận.
        PHẢI chạy ở một lượt RIÊNG, trước lượt xoay.

  python3 app/xoay_khoa.py kiem-chot <goi{skb.DUOI_GOI}> [duong-chung-nhan.json]
        Đọc 6 điều kiện và in ra. Không ghi gì. Mã thoát 1 nếu chưa đạt.

  python3 app/xoay_khoa.py xoay-that <goi{skb.DUOI_GOI}> --user-id <N> [duong-chung-nhan.json]
        XOAY THẬT trên dữ liệu đang chạy. Chỉ chạy khi 6 điều kiện ĐẠT và user là
        {'/'.join(VAI_TRO_DUOC_XOAY)} có quyền {QUYEN_XOAY!r}.

Passphrase gói: biến môi trường {skb.BIEN_MT_PASS}, hoặc nhập lúc chạy.
KHÔNG lệnh nào ở đây TẠO gói backup — dùng `python3 app/sao_luu_khoa.py tao`.
"""


def _cli(argv) -> int:
    if len(argv) < 2:
        print(_DUNG)
        return 2
    viec = argv[1]
    if viec == "_chay-tren-ban-sao":
        return _chay_tren_ban_sao()
    if viec == "dien-tap":
        kq = dien_tap(argv[2] if len(argv) > 2 else None)
        print(json.dumps(kq, ensure_ascii=False, indent=2))
        return 0 if kq["dat"] else 1
    if viec == "chung-nhan" and len(argv) >= 3:
        kq = ghi_chung_nhan_khoi_phuc(argv[2], argv[3] if len(argv) > 3 else None)
        print(json.dumps(kq, ensure_ascii=False, indent=2))
        return 0 if kq["ket_qua"] == "dat" else 1
    if viec == "kiem-chot" and len(argv) >= 3:
        kq = kiem_chot(argv[2], argv[3] if len(argv) > 3 else None)
        print(json.dumps(kq, ensure_ascii=False, indent=2))
        return 0 if kq["dat"] else 1
    if viec == "xoay-that" and len(argv) >= 3:
        if "--user-id" not in argv:
            print("THIEU --user-id: phai noi ro AI xoay. Audit khong nhan 'khong biet'.")
            return 2
        uid = int(argv[argv.index("--user-id") + 1])
        con = [a for a in argv[3:] if a != "--user-id" and a != str(uid)]
        kq = xoay_that(argv[2], con[0] if con else None, user_id=uid, dia_chi="cli")
        print(json.dumps(kq, ensure_ascii=False, indent=2))
        return 0 if kq["dat"] else 1
    print(_DUNG)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(_cli(sys.argv))
    except (LoiXoayKhoa, skb.LoiSaoLuu, sp.LoiKhoa) as e:
        sys.stderr.write(f"LỖI: {e}\n")
        sys.exit(1)
