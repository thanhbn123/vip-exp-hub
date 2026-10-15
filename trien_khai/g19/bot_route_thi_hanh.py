"""BỘ TRÍCH ROUTE **THỨ BA** cho `/api/v2/*` — nguyên lý: THI HÀNH (execution).

VÌ SAO CẦN BỘ THỨ BA (G19 / AG-04)
----------------------------------
Lượt nghiệm thu G18 (`docs/QA_G18_INTEGRATED.md`) đo được: hai dụng cụ đo V5 (cách ly tenant)
**ĐỒNG Ý ở 73 route** và chỉ **lệch PHẠM VI ở 31 route** — AG-06 phủ 104 route, AG-01 phủ 73.
Ba con số đó do **hai** bộ trích sinh ra, và cả hai đều đọc `server.py` ở tầng VĂN BẢN/MÃ NGUỒN:

* **AG-06** — `thu_g17_baomat._cua_tu_nguon()`: `ast.parse()` rồi đi theo cây cú pháp, có trạng
  thái `dang_cho` để nối `re.fullmatch(...)` với khối `if` bên dưới. Nguyên lý: **CÚ PHÁP**.
* **AG-01** — `thu_qa_g18.duong_ghi_tinh/duong_ghi_dong/duong_platform()`: `re` trên từng DÒNG
  văn bản nguồn. Nguyên lý: **VĂN BẢN**.

Hai nguyên lý ấy dùng CHUNG một giả định: *"route là thứ đọc được từ mã nguồn"*. Bộ này bỏ giả
định đó. Nguyên lý thứ ba: **một route TỒN TẠI khi và chỉ khi máy chủ ĐANG CHẠY thật sự phục vụ
nó** — tức là khi lượt HTTP thật tới `127.0.0.1` **KHÔNG** rơi vào nhánh chót của router.

    BỘ THỨ BA = (không gian ứng viên từ HẰNG SỐ ĐÃ BIÊN DỊCH)  ∩  (PHÂN LOẠI BẰNG THI HÀNH)

* `hang_so_nguon()` — nạp `server.py` thành **đối tượng mã** (`compile`) rồi moi mọi hằng số
  chuỗi chứa `/api/v2` trong `co_consts` của **mọi** code object lồng nhau. Đây không phải đọc
  văn bản: nó đọc đúng bảng hằng số mà **máy ảo** sẽ dùng. Hệ quả đo được: một dòng **chú thích**
  chứa `/api/v2/...` KHÔNG vào được không gian ứng viên (chú thích không được biên dịch), còn
  một **docstring/thông điệp log** thì CÓ vào — và sẽ bị tầng thi hành loại ra. Hai tầng, hai
  kiểu răng khác nhau; cả hai đều được đo bằng đột biến (xem `tiem_*` và ca B của
  `app/thu/thu_g19_route.py`).
* `ung_vien()` — mở rộng nhóm chọn `(a|b|c)` rồi thay nhóm tham số `(\\d+)` / `([A-Za-z0-9_-]+)`
  bằng giá trị đại diện **không tồn tại** (`919191`, `g19-khong-co`). Không gian này là **SIÊU
  TẬP** của tập route thật, nên nó cố ý chứa rác: `"/api/v2/platform/"` (tiền tố cổng chặn) và
  `"/api/v2/webhook/nhan/"` (tiền tố để dựng URL) đều là hằng số thật trong mã. Việc dọn rác
  KHÔNG do tầng tĩnh làm — mà do tầng thi hành.
* `do_thi_hanh()` — bắn HTTP THẬT (socket loopback) vào một máy chủ THẬT đang chạy, rồi phân loại
  theo **phản hồi của chính máy chủ đó**:

      "ROI"          → 404 + {"loi": "không có đường này"}  ⇒ KHÔNG có route
      "CO_ROUTE"     → mọi mã khác (200/201/400/401/402/403/409/413/422/500...) ⇒ CÓ route
      "KHONG_KET_LUAN" → 429 (trần tần suất) ⇒ không kết luận, đo lại

  Vì sao 404-khác-mã vẫn tính là CÓ route: router thật trả `{"loi": "không có đơn này"}` cho
  route `/api/v2/don/(\\d+)` khi id không tồn tại — đó là route CÓ, chỉ là dữ liệu không có. Hai
  câu đó khác nhau, và bộ đếm phải phân biệt được; nên phép phân loại so **ĐÚNG CÂU CHỮ** của
  nhánh rơi, không so mỗi mã HTTP.

GIỚI HẠN ĐÃ BIẾT (nói thẳng, không giấu)
----------------------------------------
Không gian ứng viên chỉ đầy đủ nếu mọi route được so bằng một hằng số **có mặt trong mã đã biên
dịch**. Nếu ai đó dựng đường bằng f-string rồi so (`if duong == f"/api/v2/x/{y}"`) thì bộ này
mất route đó. Trong `app/server.py` hiện tại **không có** chỗ nào như vậy (f-string `/api/v2`
duy nhất là để DỰNG URL webhook trả cho khách, dòng 849, không phải để so). Đây là giả định
ĐƯỢC KHAI, không phải điều được chứng minh — nằm ngoài phạm vi lượt này.
"""

import json
import os
import re
import subprocess
import sys

THU_MUC_G19 = os.path.dirname(os.path.abspath(__file__))
MAY_CHU = os.path.join(THU_MUC_G19, "may_chu_do.py")

# Câu chữ CHÍNH XÁC của hai nhánh rơi cuối router (`_api_platform` và `_api_tenant`).
# Phép phân loại bám vào câu này; ca A3 của `thu_g19_route.py` tự kiểm rằng nó vẫn đúng.
CAU_ROI = "không có đường này"
SO_NHANH_ROI = 2

ID_GIA = "919191"        # thay cho (\d+) — id KHÔNG tồn tại, để handler đi nhánh "không có X"
MA_GIA = "g19-khong-co"  # thay cho ([A-Za-z0-9_-]+)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# 1. TẦNG TĨNH — HẰNG SỐ ĐÃ BIÊN DỊCH (không đọc văn bản, không đi cây cú pháp)
# ═════════════════════════════════════════════════════════════════════════════════════════════
def doc_ma(duong_dan):
    with open(duong_dan, "r", encoding="utf-8") as f:
        return f.read()


def hang_so_nguon(nguon, ten="app/server.py"):
    """Mọi hằng số chuỗi chứa `/api/v2` trong MÃ ĐÃ BIÊN DỊCH, kể cả trong hàm lồng nhau.

    Đây là nguyên lý khác hẳn `ast.parse` (AG-06) và `re` trên dòng (AG-01): ta không hỏi
    "nguồn viết gì" mà hỏi "máy ảo sẽ giữ những chuỗi nào".
    """
    cay = compile(nguon, ten, "exec")
    ra, da = set(), set()

    def duyet(co):
        if id(co) in da:
            return
        da.add(id(co))
        for c in co.co_consts:
            if isinstance(c, str):
                if "/api/v2" in c:
                    ra.add(c)
            elif hasattr(c, "co_consts"):
                duyet(c)

    duyet(cay)
    return ra


def mo_rong_nhom(mau):
    """`/api/v2/don/(\\d+)/(duyet|gui|huy)` → 3 mẫu. Nhóm KHÔNG có `|` giữ nguyên."""
    m = re.search(r"\(([^()]*\|[^()]*)\)", mau)
    if not m:
        return [mau]
    ra = []
    for phan in m.group(1).split("|"):
        ra += mo_rong_nhom(mau[:m.start()] + phan + mau[m.end():])
    return ra


def duong_do(mau):
    """Mẫu → đường CỤ THỂ để bắn thật. Nhóm tham số → giá trị đại diện KHÔNG tồn tại."""
    d = mau.replace(r"(\d+)", ID_GIA)
    d = re.sub(r"\([^()]*\)", MA_GIA, d)
    return d


def ung_vien(nguon, ten="app/server.py"):
    """Không gian ứng viên = mọi đường cụ thể suy ra từ hằng số đã biên dịch.

    CỐ Ý chứa rác (tiền tố, thông điệp log). Việc dọn rác thuộc tầng THI HÀNH.
    """
    consts = hang_so_nguon(nguon, ten)
    duong = set()
    for c in consts:
        if not c.startswith("/api/v2/"):
            # hằng số chứa /api/v2 ở GIỮA (thông điệp log, URL trả cho khách) — vẫn đưa vào
            # nếu sau khi cắt nó thành đường hợp lệ; cách rẻ nhất là thử cả hậu tố.
            i = c.find("/api/v2/")
            if i < 0:
                continue
            c = c[i:]
        for mau in mo_rong_nhom(c):
            duong.add(duong_do(mau))
    return sorted(duong), sorted(consts)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# 2. TẦNG THI HÀNH — chạy `may_chu_do.py` trong tiến trình con
# ═════════════════════════════════════════════════════════════════════════════════════════════
def chay_may_chu(app_dir, che_do, dau_vao, giay=900, them=()):
    """Chạy harness đo trong tiến trình RIÊNG (CSDL tạm riêng) và trả JSON nó ghi ra.

    Vì sao tiến trình riêng: `cau_hinh` đọc `VIP_HUB_DATA` lúc IMPORT, nên muốn mỗi phép đo có
    một CSDL tạm sạch thì phải là tiến trình mới. Đây cũng là cách chạy được BẢN SAO đã đột biến
    của `server.py` mà không đụng vào tệp thật.
    """
    import tempfile
    with tempfile.TemporaryDirectory(prefix="g19-do-") as td:
        vao = os.path.join(td, "vao.json")
        ra = os.path.join(td, "ra.json")
        with open(vao, "w", encoding="utf-8") as f:
            json.dump(dau_vao, f, ensure_ascii=False)
        lenh = [sys.executable, MAY_CHU, "--app", app_dir, "--che-do", che_do,
                "--vao", vao, "--ra", ra, "--du-lieu", os.path.join(td, "csdl")]
        lenh += list(them)
        mt = dict(os.environ)
        mt["PYTHONDONTWRITEBYTECODE"] = "1"
        mt.pop("VIP_HUB_BIND", None)
        r = subprocess.run(lenh, capture_output=True, text=True, timeout=giay, env=mt)
        if r.returncode != 0 or not os.path.isfile(ra):
            raise RuntimeError("may_chu_do thất bại (exit %s):\nSTDOUT:%s\nSTDERR:%s"
                               % (r.returncode, r.stdout[-2000:], r.stderr[-3000:]))
        with open(ra, "r", encoding="utf-8") as f:
            kq = json.load(f)
        kq["_stdout"] = r.stdout
        kq["_stderr"] = r.stderr
        return kq


def liet_ke(app_dir, server_py=None, giay=900):
    """LIỆT KÊ ĐẦY ĐỦ route `/api/v2/*` bằng nguyên lý thi hành.

    Trả dict: `ung_vien` (tầng tĩnh), `chi_tiet` (từng lượt đo), `route` (tập CÓ route),
    `roi` (tập bị tầng thi hành loại ra — kèm lý do đo được).
    """
    nguon = doc_ma(server_py or os.path.join(app_dir, "server.py"))
    ds_ung_vien, consts = ung_vien(nguon)
    chi = [[d, m] for d in ds_ung_vien for m in ("GET", "POST", "PUT", "DELETE")]
    kq = chay_may_chu(app_dir, "liet-ke", chi, giay=giay)
    co, roi, khong_ket_luan = set(), [], []
    for muc in kq["ket_qua"]:
        if muc["phan_loai"] == "CO_ROUTE":
            co.add(muc["duong"])
        elif muc["phan_loai"] == "ROI":
            roi.append(muc)
        else:
            khong_ket_luan.append(muc)
    # Đường bị loại ở MỌI phương thức = ứng viên KHÔNG được máy chủ phục vụ chút nào. Đây mới
    # là thứ đáng gọi là "không phải route"; một đường chỉ bị loại ở VÀI phương thức thì vẫn là
    # route thật (chỉ là không nhận phương thức đó).
    moi_pm = {}
    for m in roi:
        moi_pm.setdefault(m["duong"], []).append(m["method"])
    khong_phai = sorted(d for d, ms in moi_pm.items() if len(set(ms)) == 4)
    return {"ung_vien": ds_ung_vien, "hang_so": consts, "chi_tiet": kq["ket_qua"],
            "route": sorted(co), "roi": roi, "khong_ket_luan": khong_ket_luan,
            "khong_phai_route": khong_phai,
            "cap": sorted({(m["duong"], m["method"]) for m in kq["ket_qua"]
                           if m["phan_loai"] == "CO_ROUTE"}),
            "giam_sat": kq.get("giam_sat", {})}


# ═════════════════════════════════════════════════════════════════════════════════════════════
# 3. ĐỘT BIẾN — chứng minh bộ trích CÓ RĂNG (chạy trên BẢN SAO, không sửa tệp thật)
# ═════════════════════════════════════════════════════════════════════════════════════════════
MOC_CUOI = "\n\ndef chay("
# Dòng RƠI cuối cùng của router (cuối `_api_tenant`). Chèn NGAY TRƯỚC nó — chèn SAU nó là
# code không tới được, và lượt đo sẽ báo "không thấy route giả" vì lý do sai (đã dính đúng
# bẫy này ở lần chạy đầu: route giả nằm sau `return`, trả 404 nhánh rơi).
MOC_ROI_CUOI = '        return self._tra(404, {"loi": "không có đường này"})\n'


def _chen_truoc_ham_chay(nguon, khoi):
    """Chèn ở CẤP MODULE, ngay trước `def chay(` — dùng cho đột biến âm (chuỗi/chú thích)."""
    i = nguon.index(MOC_CUOI)
    return nguon[:i] + khoi + nguon[i:]


def _chen_truoc_nhanh_roi(nguon, khoi):
    """Chèn trong THÂN `_api_tenant`, ngay trước nhánh rơi cuối — chỗ code TỚI ĐƯỢC."""
    cuoi = nguon.index(MOC_CUOI)
    i = nguon.rindex(MOC_ROI_CUOI, 0, cuoi)
    return nguon[:i] + khoi + nguon[i:]


def tiem_route(nguon, duong, ma_http=200):
    """Tiêm một route GIẢ vào bản sao, ĐÚNG chỗ router thật sẽ so nó (cuối `_api_tenant`).

    Trả (nguồn_mới, thân_phản_hồi) để ca đo còn kiểm được chính lượt HTTP của route giả.
    """
    than = {"g19_tiem": True}
    khoi = ('        if duong == "%s" and method == "GET":\n'
            '            return self._tra(%d, %r)\n' % (duong, ma_http, than))
    return _chen_truoc_nhanh_roi(nguon, khoi), than


def tiem_bia(nguon, duong, kieu):
    """Tiêm ĐỘT BIẾN ÂM: một chuỗi TRÔNG NHƯ route nhưng KHÔNG phải route.

    * `kieu="chu_thich"` — dòng chú thích `#` ⇒ **KHÔNG** vào `co_consts` ⇒ tầng TĨNH phải
      từ chối. Chứng minh tầng tĩnh không phải `grep` văn bản.
    * `kieu="chuoi"` — gán hằng số chuỗi thật ở cấp module ⇒ **CÓ** vào `co_consts` ⇒ tầng TĨNH
      sẽ nhận, và tầng THI HÀNH phải loại ra (404 nhánh rơi). Chứng minh tầng thi hành có răng,
      chứ không phải vật trang trí.
    """
    if kieu == "chu_thich":
        khoi = '\n# %s — dòng chú thích này KHÔNG được biên dịch\n' % duong
    elif kieu == "chuoi":
        khoi = '\n_bia_g19 = "%s"   # hằng số THẬT, sẽ vào co_consts\n' % duong
    else:
        raise ValueError("kiểu bịa lạ: %r" % (kieu,))
    return _chen_truoc_ham_chay(nguon, khoi)


def xoa_route(nguon, duong, method="GET"):
    """XOÁ một route THẬT khỏi bản sao (đột biến dương-tính-ngược).

    Nếu bộ trích vẫn báo route đó là CÓ, thì nó đang đọc một danh sách ghim cứng chứ không đo.
    """
    mau = 'if duong == "%s" and method == "%s"' % (duong, method)
    dong = nguon.splitlines(keepends=True)
    vt = [i for i, d in enumerate(dong) if mau in d]
    if len(vt) != 1:
        raise ValueError("kỳ vọng đúng 1 dòng %r, thấy %d" % (mau, len(vt)))
    i = vt[0]
    j = i + 1
    while j < len(dong):
        d = dong[j]
        if d.strip() == "":
            j += 1
            continue
        thut = len(d) - len(d.lstrip())
        if thut <= 8:
            break
        j += 1
    return "".join(dong[:i] + dong[j:])


def ban_sao_app(app_dir, server_py_moi=None):
    """Bản sao `app/` trong thư mục tạm + `server.py` đã đột biến. KHÔNG đụng tệp thật."""
    import shutil
    import tempfile
    td = tempfile.mkdtemp(prefix="g19-app-")
    dich = os.path.join(td, "app")
    shutil.copytree(app_dir, dich, ignore=shutil.ignore_patterns("__pycache__", "du-lieu"))
    if server_py_moi is not None:
        with open(os.path.join(dich, "server.py"), "w", encoding="utf-8") as f:
            f.write(server_py_moi)
    return dich


# ═════════════════════════════════════════════════════════════════════════════════════════════
# 4. CLI — để chạy tay và dán bằng chứng vào báo cáo
# ═════════════════════════════════════════════════════════════════════════════════════════════
def _main(argv):
    import argparse
    goc = os.path.dirname(os.path.dirname(THU_MUC_G19))
    p = argparse.ArgumentParser(description="Bộ trích route thứ ba (nguyên lý: thi hành)")
    p.add_argument("--app", default=os.path.join(goc, "app"))
    p.add_argument("--ra", default="")
    a = p.parse_args(argv)
    kq = liet_ke(a.app)
    so_luot = len(kq["chi_tiet"])
    print("[G19] hằng số /api/v2 đã biên dịch : %d" % len(kq["hang_so"]))
    print("[G19] không gian ứng viên (tĩnh)   : %d đường" % len(kq["ung_vien"]))
    print("[G19] CÓ ROUTE  (đo bằng thi hành)  : %d đường" % len(kq["route"]))
    print("[G19] lượt đo                      : %d lượt (%d đường × 4 phương thức)"
          % (so_luot, len(kq["ung_vien"])))
    print("[G19] lượt bị loại (404 nhánh rơi)  : %d lượt" % len(kq["roi"]))
    print("[G19] đường bị loại ở MỌI 4 phương thức (⇒ KHÔNG phải route): %d"
          % len(kq["khong_phai_route"]))
    for d in kq["khong_phai_route"]:
        print("       KHÔNG PHẢI ROUTE: %s" % d)
    print("[G19] không kết luận (429)          : %d lượt" % len(kq["khong_ket_luan"]))
    print("[G19] cặp (đường, phương thức)      : %d" % len(kq["cap"]))
    if a.ra:
        with open(a.ra, "w", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False, indent=1)
        print("[G19] đã ghi %s" % a.ra)
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
