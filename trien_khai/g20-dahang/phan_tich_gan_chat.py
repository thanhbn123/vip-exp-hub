# G20/AG-06 — ĐO RANH GIỚI "CƠ CHẾ CHUNG" vs "ĐẶC THÙ J&T" TRONG `app/http_jt.py`.
#
# VÌ SAO CÓ TỆP NÀY: nhiệm vụ AG-06 không phải "đọc rồi nhận xét" lớp HTTP. Nó là một PHÉP ĐO,
# và phép đo phải chạy lại được bằng máy, cho ra cùng kết quả, và ĐỔ ĐƯỢC khi lớp HTTP đổi.
# Đọc bằng mắt rồi viết một bảng vào tài liệu là một lời khai không ai kiểm — đúng thứ dự án
# này cấm (§12.1 luật 3: khẳng định phải có lệnh thật + mã thoát thật).
#
# CÁCH PHÂN LOẠI — không đoán, không liệt kê tay:
#   Bước 1. Đọc `app/adapter_jt.py` bằng AST để lấy BẰNG CHỨNG về thân phận J&T: tên host
#           (`HOST_API`) và bốn tên trường credentials (`TRUONG_CREDENTIAL`). Đây là NGUỒN, không
#           phải chép tay — chép tay thì mai kia adapter đổi mà bảng này không đổi.
#   Bước 2. Một hằng mức mô-đun của `http_jt.py` bị coi là ĐẶC THÙ HÃNG khi và chỉ khi giá trị
#           của nó CHỨA một dấu hiệu lấy từ bước 1 (tên host, hoặc tên trường credential), hoặc
#           chứa chính chuỗi tên hãng. Còn lại là CHUNG.
#   Bước 3. Với hằng không lộ dấu hiệu ở GIÁ TRỊ (ví dụ `CONG_HANG = 443`), xét CÁCH DÙNG: nếu
#           mọi hàm đọc nó cũng đọc một hằng đặc thù ở bước 2 thì nó bị RÀNG BUỘC theo ngữ cảnh
#           (vẫn là đặc thù, nhưng bằng chứng là "dùng chung chỗ" chứ không phải "giá trị").
#   Bước 4. Tìm ĐIỂM TIÊM: hàm nào có tham số có thể mang danh sách trắng host / bảng tên
#           credential? Không có điểm tiêm là phát hiện TRUNG TÂM của AG-06 — nó biến "hãng thứ
#           hai chạy được" từ chuyện cấu hình thành chuyện SỬA MÃ.
#
# PHẠM VI — NÓI THẲNG CÁI NẰM NGOÀI: tệp này CHỈ đọc AST trên đĩa. Nó không import `http_jt`,
# không mở socket, không chạy mã của lớp HTTP. Nó không đo được hành vi — hành vi do
# `app/thu/thu_g20_dahang.py` đo. Hai phép đo bổ sung nhau và KHÔNG thay thế nhau.
import argparse
import ast
import json
import os
import sys

# Chuỗi nhận diện HÃNG, dùng cho bước 2 khi giá trị không chứa tên host mà chứa tên hãng.
# Cố ý ngắn và chỉ gồm thứ chỉ đúng một hãng.
_DAU_HIEU_TEN_HANG = ("jtexpress", "j&t")

# Từ khóa trong CHÚ THÍCH/tên hàm KHÔNG được tính là dấu hiệu: chú thích không chạy. Chỉ GIÁ TRỊ
# của literal mới được xét. (Bài học `thu_bien_driver.py` ca a4: grep đọc cả chú thích.)
GOC_MAC_DINH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =================================================================================================
# BƯỚC 1 — đọc bằng chứng thân phận hãng TỪ CHÍNH `adapter_jt.py`
# =================================================================================================
def _literal(node):
    """Giá trị literal của một nút AST, hoặc `None` nếu không phải literal tĩnh."""
    try:
        return ast.literal_eval(node)
    except Exception:
        return None


def doc_dau_hieu_hang(duong_adapter):
    """→ `(tap_host, tap_truong_credential, nguon)` đọc bằng AST từ `adapter_jt.py`.

    Đây là NGUỒN DUY NHẤT của phép phân loại. Không có tên host nào được chép tay vào tệp này:
    nếu `adapter_jt.HOST_API` đổi, bảng phân loại đổi theo mà không ai phải nhớ sửa hai chỗ.
    """
    with open(duong_adapter, encoding="utf-8") as f:
        src = f.read()
    cay = ast.parse(src)
    hang = {}
    for n in cay.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    hang[t.id] = _literal(n.value)
    host = set()
    for url in (hang.get("HOST_API") or {}).values():
        if isinstance(url, str):
            # `https://demoopenapi.jtexpress.vn` → `demoopenapi.jtexpress.vn`
            host.add(url.split("//", 1)[-1].split("/", 1)[0].lower())
    truong = tuple(hang.get("TRUONG_CREDENTIAL") or ())
    return host, truong, {"duong_dan": duong_adapter, "HOST_API": hang.get("HOST_API"),
                          "TRUONG_CREDENTIAL": list(truong)}


# =================================================================================================
# BƯỚC 2 + 3 — phân loại từng hằng mức mô-đun của `http_jt.py`
# =================================================================================================
def _chuoi_trong(node, src):
    """Mọi literal CHUỖI thật sự có trong một biểu thức (không lấy chú thích)."""
    ra = []
    for con in ast.walk(node):
        if isinstance(con, ast.Constant) and isinstance(con.value, str):
            ra.append(con.value)
    return ra


def _ten_duoc_doc(node):
    """Mọi tên mức mô-đun được ĐỌC trong một nút (không tính tên đang được gán)."""
    return sorted({c.id for c in ast.walk(node) if isinstance(c, ast.Name)
                   and isinstance(c.ctx, ast.Load)})


def phan_tich(duong_http=None, duong_adapter=None):
    """→ dict kết quả đầy đủ. Hàm THUẦN: cùng đầu vào ⇒ cùng đầu ra, không chạm mạng/đĩa ngoài đọc."""
    duong_http = duong_http or os.path.join(GOC_MAC_DINH, "app", "http_jt.py")
    duong_adapter = duong_adapter or os.path.join(GOC_MAC_DINH, "app", "adapter_jt.py")
    host_hang, truong_cred, nguon = doc_dau_hieu_hang(duong_adapter)

    with open(duong_http, encoding="utf-8") as f:
        src = f.read()
    cay = ast.parse(src)
    # Bản đồ nút → nút cha: cần để biết một tên nằm trong phép toán nào (`in`, `join`, chỉ số…).
    _cha = {}
    for _n in ast.walk(cay):
        for _con in ast.iter_child_nodes(_n):
            _cha[id(_con)] = _n

    # -- hằng mức mô-đun ------------------------------------------------------------------------
    #
    # MỘT TÊN CÓ THỂ ĐƯỢC GÁN NHIỀU LẦN, và bản đầu của bộ dò bỏ sót điều đó: nó ghi đè theo tên
    # nên chỉ giữ lần gán CUỐI. Hệ quả đo được (ca tự kiểm `e3`): nguồn
    #     HOST_HANG = ("demoopenapi.jtexpress.vn",)      # mang dấu hiệu hãng
    #     HOST_HANG = HOST_HANG + ("api.hang-2.invalid",)
    # cho `hang["HOST_HANG"]` = biểu thức thứ hai, mà biểu thức đó chỉ đọc chính nó ⇒ không dấu
    # hiệu ⇒ phân loại "CHUNG" ⇒ bảng điểm tiêm RỖNG. Bộ dò mù đúng trước thứ nó sinh ra để bắt.
    # Nay giữ MỌI lần gán; `so_lan_gan` cũng đọc thẳng từ cây nên hai nguồn khớp nhau.
    hang = {}
    for n in cay.body:
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    v = hang.setdefault(t.id, {"dong": n.lineno, "nut_list": [], "nguon": ""})
                    v["nut_list"].append(n.value)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
            v = hang.setdefault(n.target.id, {"dong": n.lineno, "nut_list": [], "nguon": ""})
            v["nut_list"].append(n.value)
    for v in hang.values():
        v["nguon"] = " ; ".join((ast.get_source_segment(src, x) or "").strip().replace("\n", " ")
                                for x in v["nut_list"])[:120]
        v["doc_boi"] = set()
    # ai đọc cái gì
    for n in cay.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            for ten in _ten_duoc_doc(n):
                if ten in hang:
                    hang[ten]["doc_boi"].add(n.name)

    # -- BƯỚC 2: phân loại theo GIÁ TRỊ ---------------------------------------------------------
    #
    # LUẬT, cố ý hẹp và kiểm được: một hằng là ĐẶC THÙ khi giá trị của nó CHỨA một dấu hiệu thân
    # phận hãng lấy từ `adapter_jt`. Không có luật "trông có vẻ liên quan tới hãng" — luật đó sẽ
    # nuốt luôn những ngưỡng chung (`DAI_TOI_THIEU_DE_CHE = 8`) chỉ vì chúng nằm cạnh bảng tên
    # credential trong cùng một hàm. Đã thử và đã bỏ: xem ghi chú ở `trien_khai/g20-dahang/README.md`.
    def _dau_hieu_gia_tri(v):
        """→ danh sách dấu hiệu thân phận hãng tìm thấy TRONG GIÁ TRỊ của hằng (MỌI lần gán)."""
        thay = []
        for nut in v["nut_list"]:
            for s in _chuoi_trong(nut, src):
                s_l = s.lower()
                for h in host_hang:
                    if h and h in s_l:
                        thay.append(f"tên host {h!r}")
                for t in truong_cred:
                    if t and s_l.strip() == t.lower():
                        thay.append(f"tên trường credential {t!r}")
                for d in _DAU_HIEU_TEN_HANG:
                    if d in s_l:
                        thay.append(f"tên hãng {d!r}")
            # `TRUONG_CREDENTIAL = ("apiaccount", …)`: literal là TỪNG PHẦN TỬ của tuple, nên không
            # literal đơn nào khớp cả bảng. Khớp theo TẬP, và đòi khớp 100% — khớp một phần là một
            # bảng chung có lẫn vài tên của hãng, chuyện khác hẳn.
            gt = _literal(nut)
            if isinstance(gt, (tuple, list)) and gt and all(isinstance(x, str) for x in gt):
                khop = [x for x in gt if x.lower() in {t.lower() for t in truong_cred}]
                if khop and len(khop) == len(gt):
                    thay.append(f"CHÍNH LÀ bảng tên credential của hãng ({len(khop)} tên, khớp 100%)")
        return sorted(set(thay))

    for ten, v in hang.items():
        v["dau_hieu_gia_tri"] = _dau_hieu_gia_tri(v)

    # -- BƯỚC 3: DẪN XUẤT — hằng đọc một hằng đặc thù thì cũng đặc thù ---------------------------
    # `HOST_HANG = (HOST_HANG_SANDBOX, HOST_HANG_PRODUCTION)` không chứa literal nào của hãng,
    # nhưng nó CHỈ là hai hằng kia gộp lại. Bỏ qua bước này thì `host_duoc_phep` và `tach_url` —
    # đúng hai hàm giữ chốt chặn hãng — bị bảng phân loại ghi là "CHUNG", tức là bảng nói ngược
    # lại chính kết luận của nó. Lặp tới ĐIỂM BẤT ĐỘNG vì dẫn xuất có thể nối chuỗi.
    for _ in range(len(hang) + 1):
        them = False
        for ten, v in hang.items():
            if v["dau_hieu_gia_tri"]:
                continue
            doc = sorted({t for nut in v["nut_list"] for t in _ten_duoc_doc(nut)})
            nguon_dx = sorted(k for k in doc
                              if k != ten and hang.get(k, {}).get("dau_hieu_gia_tri"))
            if nguon_dx:
                v["dau_hieu_gia_tri"] = [f"dẫn xuất: đọc {', '.join(nguon_dx)}"]
                them = True
        if not them:
            break

    for ten, v in hang.items():
        if v["dau_hieu_gia_tri"]:
            v["phan_loai"] = "DAC_THU_JT" if not v["dau_hieu_gia_tri"][0].startswith("dẫn xuất") \
                else "DAN_XUAT_TU_DAC_THU"
            v["vi_sao"] = v["dau_hieu_gia_tri"]
        else:
            v["phan_loai"] = "CHUNG"
            v["vi_sao"] = ["không chứa dấu hiệu thân phận hãng, và không dẫn xuất từ hằng đặc thù"]

    # -- BƯỚC 3b: NHÁNH MÃ bị ràng buộc hãng — đo ở CHỖ DÙNG, không ở hằng -----------------------
    # `CONG_HANG = 443` là một con số chung; cái làm nó thành chuyện của J&T là nhánh
    # `if host in HOST_HANG:` trong `tach_url`. Ghi ở chỗ dùng thì không phải gán cho hằng một
    # thân phận mà bản thân nó không có.
    ten_dac_thu = {t for t, v in hang.items() if v["dau_hieu_gia_tri"]}
    nhanh_hang = []
    for n in cay.body:
        if not isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            continue
        for con in ast.walk(n):
            if isinstance(con, ast.If):
                doc = {x.id for x in ast.walk(con.test) if isinstance(x, ast.Name)}
                giao = sorted(doc & ten_dac_thu)
                if giao:
                    nhanh_hang.append({"ham": n.name, "dong": con.lineno,
                                       "dieu_kien": (ast.get_source_segment(src, con.test) or "")[:80],
                                       "hang_dac_thu": giao,
                                       "so_lenh_trong_nhanh": len(con.body)})
    nhanh_hang.sort(key=lambda d: d["dong"])

    # -- hàm: chúng chạm hằng đặc thù nào --------------------------------------------------------
    def _la_dac_thu(ten):
        return hang.get(ten, {}).get("phan_loai") in ("DAC_THU_JT", "DAN_XUAT_TU_DAC_THU")

    ham = {}
    for n in cay.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            doc = _ten_duoc_doc(n)
            ham[n.name] = {
                "dong": n.lineno,
                "hang_doc": sorted(t for t in doc if t in hang),
                "hang_dac_thu": sorted(t for t in doc if _la_dac_thu(t)),
            }
            if isinstance(n, ast.FunctionDef):
                a = n.args
                ten_ts = [x.arg for x in (a.posonlyargs + a.args + a.kwonlyargs)]
                if a.vararg:
                    ten_ts.append("*" + a.vararg.arg)
                if a.kwarg:
                    ten_ts.append("**" + a.kwarg.arg)
                ham[n.name]["tham_so"] = ten_ts
    for ten, v in ham.items():
        v["vai_tro"] = "DAC_THU_JT" if v["hang_dac_thu"] else "CHUNG"

    # -- BƯỚC 4: ĐIỂM TIÊM — đo bằng DỮ LIỆU, không bằng cái tên --------------------------------
    #
    # Bản đầu của bảng này soát TÊN tham số và tìm chữ "host"/"danh_sach"/"credential". Nó báo
    # nhầm ngay: `host_duoc_phep(host)` bị ghi là "điểm tiêm" chỉ vì tham số tên `host` — trong
    # khi `host` chính là GIÁ TRỊ ĐANG BỊ KIỂM, không phải cái danh sách. Một bảng dò theo cái tên
    # là một bảng đoán.
    #
    # Luật thay thế, đo được trên cây cú pháp: một bảng chỉ TIÊM ĐƯỢC khi còn đường ghi vào nó.
    # Ba đường ghi, soát cả ba:
    #   (1) gán lại ở mức mô-đun nhiều hơn một lần  →  có chỗ đăng ký thêm
    #   (2) được TRUYỀN làm đối số cho một lời gọi  →  có chỗ nào đó nhận nó như tham số
    #   (3) bị biến đổi tại chỗ (chỉ số, thuộc tính, `global`, `append/update/add/extend`)
    # Không đường nào mở ⇒ hai bảng này là HẰNG SỐ ĐÓNG, và hãng thứ hai chỉ vào được bằng SỬA MÃ.
    def _so_lan_gan(ten):
        n = 0
        for x in ast.walk(cay):
            if isinstance(x, ast.Assign):
                n += sum(1 for t in x.targets
                         if isinstance(t, ast.Name) and t.id == ten)
            elif isinstance(x, ast.AnnAssign) and isinstance(x.target, ast.Name) \
                    and x.target.id == ten:
                n += 1
            elif isinstance(x, (ast.AugAssign,)) and isinstance(x.target, ast.Name) \
                    and x.target.id == ten:
                n += 1
        return n

    def _truyen_di(ten):
        """Lời gọi mà `ten` đi vào ĐỐI SỐ, và ĐÍCH của lời gọi là một hàm CỦA CHÍNH MÔ-ĐUN NÀY.

        Hai giới hạn, mỗi giới hạn có lý do:

        · CHỈ hàm nội bộ. Bản đầu kể cả `', '.join(HOST_HANG)` (dòng 734, chỉ để in thông điệp)
          và `sorted(TRUONG_CREDENTIAL_PHAN_HOI)` (dòng 171, để dựng regex). Cả hai là phép ĐỌC
          thuần — chúng không trao bảng cho ai giữ. `str.join` và `sorted` không ghi vào đối số.
          Một hàm CỦA MÔ-ĐUN NÀY thì có thể: nó nằm trong tầm sửa của chính tệp đang soát.

        · SOI CẢ BÊN TRONG biểu thức đối số, không chỉ khi đối số là trần `Name`. Một sổ đăng ký
          thật thường viết `HOST_HANG = nap_them(HOST_HANG)`, chứ không truyền trần. Bắt đúng
          `Name` trần là bỏ sót đúng khuôn viết thường gặp nhất.
        """
        ten_ham_noi_bo = {x.name for x in cay.body
                          if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef))}

        def _trao_truc_tiep(nut, ten):
            """`ten` có nằm trong `nut` mà KHÔNG bị một lời gọi/định dạng nào tiêu thụ trên đường?

            Rào chắn ở `Call` và `JoinedStr` là BẮT BUỘC, không phải cho gọn. ĐO ĐƯỢC: dòng 731
            của `http_jt.py` là
                raise _loi_vinh_vien("host-bi-tu-choi", f"… {', '.join(HOST_HANG)} …")
            `HOST_HANG` nằm trong đối số của một hàm NỘI BỘ, nên nếu soi cả cây con thì bảng này
            bị ghi là "có điểm tiêm" — trong khi sự thật là nó chỉ được `join` để IN RA. Một lời
            gọi khác trên đường đi nghĩa là bảng đã bị TIÊU THỤ thành chuỗi/giá trị mới, chứ
            không được TRAO cho ai giữ.
            """
            if isinstance(nut, ast.Name):
                return nut.id == ten
            if isinstance(nut, (ast.Call, ast.JoinedStr, ast.FormattedValue)):
                # Đối số của CHÍNH lời gọi đích thì đã được xét ở tầng trên; ở đây là lời gọi LỒNG.
                if isinstance(nut, ast.Call) and isinstance(nut.func, ast.Name) \
                        and nut.func.id == ten:
                    return True
                return False
            return any(_trao_truc_tiep(c, ten) for c in ast.iter_child_nodes(nut))

        ra = []
        for x in ast.walk(cay):
            if not isinstance(x, ast.Call):
                continue
            if not (isinstance(x.func, ast.Name) and x.func.id in ten_ham_noi_bo):
                continue
            for a in list(x.args) + [k.value for k in x.keywords]:
                if _trao_truc_tiep(a, ten):
                    ra.append({"dong": x.lineno,
                               "goi": (ast.get_source_segment(src, x.func) or "?")[:60]})
                    break
        return ra

    def _cach_dung(ten):
        """Bảng này được DÙNG theo những dạng biểu thức nào. Đây là phép đo QUYẾT ĐỊNH.

        Bản trước của bảng này thử suy "tham số nào mang được bảng" từ việc tham số XUẤT HIỆN
        CHUNG CÂU với bảng. Nó sai ngay ở `tach_url`: câu `if host in HOST_HANG:` có cả `host`
        lẫn `HOST_HANG`, nên bộ dò kết luận `host` "mang được bảng" — trong khi `host` chính là
        giá trị ĐANG BỊ ĐEM ĐI SO. Quan hệ "xuất hiện chung câu" là quan hệ ĐỐI XỨNG, nó không
        phân biệt được VẾ SO với BẢNG BỊ SO. Bỏ hẳn phép suy đó.

        Điều đo được và không cần suy: bảng chỉ xuất hiện trong phép toán nào. Nếu mọi lần xuất
        hiện đều là `in`/`not in` (kiểm thành viên) hoặc `join`/`sorted` (đọc để in/dựng regex),
        thì KHÔNG có phép toán nào GHI THÊM ĐƯỢC PHẦN TỬ, và câu trả lời cho "thêm hãng thứ hai"
        chỉ còn một đường: sửa chính văn bản nguồn.
        """
        ra = []
        for n in ast.walk(cay):
            if not isinstance(n, ast.Name) or n.id != ten or not isinstance(n.ctx, ast.Load):
                continue
            cha = _cha.get(id(n))
            if isinstance(cha, ast.Compare):
                ra.append("in / not in (kiểm thành viên)")
            elif isinstance(cha, ast.Call):
                ra.append(f"{ast.get_source_segment(src, cha.func) or '?'}(…) (đọc để in/dựng)")
            elif isinstance(cha, ast.Subscript):
                ra.append("chỉ số (đọc)")
            elif isinstance(cha, ast.BinOp):
                ra.append("phép nối (dựng bảng mới, không sửa bảng cũ)")
            else:
                ra.append(type(cha).__name__ if cha is not None else "?")
        return sorted(set(ra))

    def _bi_bien_doi(ten):
        """Chỗ nào GHI VÀO bảng: `ten[...] =`, `ten.attr =`, `ten.append(...)`, `global ten`."""
        ra = []
        for x in ast.walk(cay):
            if isinstance(x, ast.Global) and ten in x.names:
                ra.append({"dong": x.lineno, "kieu": "global"})
            elif isinstance(x, ast.Assign):
                for t in x.targets:
                    if isinstance(t, (ast.Subscript, ast.Attribute)):
                        goc = t.value
                        if isinstance(goc, ast.Name) and goc.id == ten:
                            ra.append({"dong": x.lineno, "kieu": "gán vào chỉ số/thuộc tính"})
            elif isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) \
                    and x.func.attr in ("append", "extend", "update", "add", "insert", "pop",
                                        "remove", "clear", "setdefault"):
                goc = x.func.value
                if isinstance(goc, ast.Name) and goc.id == ten:
                    ra.append({"dong": x.lineno, "kieu": f".{x.func.attr}()"})
            elif isinstance(x, ast.Delete):
                for t in x.targets:
                    if isinstance(t, ast.Name) and t.id == ten:
                        ra.append({"dong": x.lineno, "kieu": "del"})
        return ra

    diem_tiem = []
    for ten, v in sorted(hang.items()):
        if not v["dau_hieu_gia_tri"]:
            continue
        so_gan = _so_lan_gan(ten)
        truyen = _truyen_di(ten)
        bien_doi = _bi_bien_doi(ten)
        ts_mang_bang = _cach_dung(ten)
        diem_tiem.append({
            "bang": ten, "dong": v["dong"], "so_lan_gan": so_gan,
            "truyen_cho_ham_noi_bo": truyen, "bi_bien_doi": bien_doi,
            "cach_dung": ts_mang_bang,
            "dong_bang": not (so_gan > 1 or truyen or bien_doi),
            "ham_doc": sorted(v["doc_boi"]),
        })

    # -- literal nêu TÊN HÃNG trong thông điệp (nhãn hiệu lộ ra cho người trực) -----------------
    #
    # CHỈ xét chuỗi CHẠY ĐƯỢC. Docstring là literal trong cây cú pháp nhưng KHÔNG BAO GIỜ được in
    # ra cho ai — tính nó vào là lặp lại đúng bài học `thu_bien_driver.py` ca a4 ("grep đọc cả
    # chú thích"): bảng sẽ báo 8 dòng "nhãn hiệu lộ" trong khi thực tế chỉ 3 dòng thật sự lộ.
    _docstring = set()
    for x in ast.walk(cay):
        if isinstance(x, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            d = ast.get_docstring(x, clean=False)
            if d is not None and x.body and isinstance(x.body[0], ast.Expr):
                _docstring.add(id(x.body[0].value))
    nhan_hieu = []
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in _docstring:
            s_l = n.value.lower()
            if any(d in s_l for d in _DAU_HIEU_TEN_HANG) or "bizcontent" in s_l:
                nhan_hieu.append({"dong": n.lineno, "trich": n.value.strip()[:110]})
    nhan_hieu.sort(key=lambda x: x["dong"])

    # -- phương thức HTTP và kiểu thân: cứng hay mềm? -------------------------------------------
    phuong_thuc = []
    for n in ast.walk(cay):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "request" and n.args):
            phuong_thuc.append({"dong": n.lineno, "phuong_thuc": _literal(n.args[0]),
                                "co_tham_so_hoa": len(n.args) > 1})

    # -- canh lệch với adapter (chốt chặn đã có từ G16, chạy lại ở đây) -------------------------
    host_trong_http = set()
    for v in hang.values():
        for nut in v["nut_list"]:
            gt = _literal(nut)
            if isinstance(gt, str) and "." in gt and " " not in gt:
                host_trong_http.add(gt.lower())
    canh_lech = sorted(host_hang - host_trong_http)

    return {
        "duong_http": duong_http, "duong_adapter": duong_adapter,
        "sha256_se_ghi_o_ngoai": None,          # do bộ thử điền; công cụ này không băm
        "nguon_dau_hieu": nguon,
        "hang": {k: {"dong": v["dong"], "phan_loai": v["phan_loai"], "vi_sao": v["vi_sao"],
                     "doc_boi": sorted(v["doc_boi"]), "nguon": v["nguon"][:90]}
                 for k, v in sorted(hang.items(), key=lambda kv: kv[1]["dong"])},
        "ham": {k: v for k, v in sorted(ham.items(), key=lambda kv: kv[1]["dong"])},
        "nhanh_ma_gan_hang": nhanh_hang,
        "diem_tiem": diem_tiem,
        "nhan_hieu_ten_hang": nhan_hieu,
        "phuong_thuc_http": phuong_thuc,
        "canh_lech_host_voi_adapter": canh_lech,
    }


# =================================================================================================
# IN BẢNG
# =================================================================================================
def in_bang(kq, ra=sys.stdout):
    w = ra.write
    w("=" * 104 + "\n")
    w("BẢNG 1 — CƠ CHẾ CHUNG vs ĐẶC THÙ J&T (đo bằng AST trên app/http_jt.py)\n")
    w("=" * 104 + "\n")
    w(f"nguồn dấu hiệu hãng: {kq['duong_adapter']}\n")
    w(f"  HOST_API         = {kq['nguon_dau_hieu']['HOST_API']}\n")
    w(f"  TRUONG_CREDENTIAL= {kq['nguon_dau_hieu']['TRUONG_CREDENTIAL']}\n\n")
    w(f"{'dòng':>5}  {'hằng mức mô-đun':34s} {'phân loại':26s} vì sao\n")
    w("-" * 104 + "\n")
    for ten, v in kq["hang"].items():
        w(f"{v['dong']:>5}  {ten:34s} {v['phan_loai']:26s} {v['vi_sao'][0][:70]}\n")
    w("\n" + "=" * 104 + "\n")
    w("BẢNG 2 — HÀM NÀO CHẠM ĐẶC THÙ J&T\n")
    w("=" * 104 + "\n")
    w(f"{'dòng':>5}  {'hàm':30s} {'vai trò':12s} hằng đặc thù đã đọc\n")
    w("-" * 104 + "\n")
    for ten, v in kq["ham"].items():
        w(f"{v['dong']:>5}  {ten:30s} {v['vai_tro']:12s} "
          f"{', '.join(v['hang_dac_thu']) or '—'}\n")
    w("\n" + "=" * 104 + "\n")
    w("BẢNG 2b — NHÁNH MÃ BỊ RÀNG BUỘC HÃNG (đo ở CHỖ DÙNG, không gán cho hằng)\n")
    w("=" * 104 + "\n")
    if kq["nhanh_ma_gan_hang"]:
        for d in kq["nhanh_ma_gan_hang"]:
            w(f"  dòng {d['dong']:>4}  {d['ham']}(): if {d['dieu_kien']}\n"
              f"            → chạm {', '.join(d['hang_dac_thu'])}; {d['so_lenh_trong_nhanh']} lệnh "
              f"trong nhánh\n")
    else:
        w("  (không có nhánh nào)\n")
    w("\n" + "=" * 104 + "\n")
    w("BẢNG 3 — ĐIỂM TIÊM: còn đường nào GHI THÊM vào bảng host / bảng tên credential không?\n")
    w("=" * 104 + "\n")
    for d in kq["diem_tiem"]:
        w(f"  {d['bang']} (dòng {d['dong']}) — đọc bởi: {', '.join(d['ham_doc']) or '(không hàm nào)'}\n")
        w(f"      số lần gán ở mức mô-đun     : {d['so_lan_gan']}\n")
        w(f"      truyền cho hàm NỘI BỘ       : "
          f"{d['truyen_cho_ham_noi_bo'] if d['truyen_cho_ham_noi_bo'] else 'KHÔNG (0 lời gọi)'}\n")
        w(f"      bị biến đổi tại chỗ         : "
          f"{d['bi_bien_doi'] if d['bi_bien_doi'] else 'KHÔNG (0 chỗ)'}\n")
        w(f"      chỉ xuất hiện trong phép toán: {', '.join(d['cach_dung']) or '(không)'}\n")
        w(f"      ⇒ BẢNG ĐÓNG (không điểm tiêm): {'CÓ' if d['dong_bang'] else 'KHÔNG'}\n")
    w("\n  Chữ ký hàm (đọc thẳng từ AST) — hãy tự thấy chúng chỉ nhận GIÁ TRỊ, không nhận BẢNG:\n")
    for ten in ("gui_form", "tach_url", "host_duoc_phep", "chan_moi_truong", "_ma_hoa_form"):
        v = kq["ham"].get(ten)
        if v and "tham_so" in v:
            w(f"    {ten}({', '.join(v['tham_so'])})\n")
    w("\n" + "=" * 104 + "\n")
    w("BẢNG 4 — NHÃN HIỆU HÃNG LỘ TRONG THÔNG ĐIỆP (chỉ là chữ, không phải chặn kỹ thuật)\n")
    w("=" * 104 + "\n")
    for d in kq["nhan_hieu_ten_hang"]:
        w(f"  dòng {d['dong']:>4}  {d['trich']}\n")
    w("\n" + "=" * 104 + "\n")
    w("BẢNG 5 — PHƯƠNG THỨC HTTP VÀ KIỂU THÂN\n")
    w("=" * 104 + "\n")
    for d in kq["phuong_thuc_http"]:
        w(f"  dòng {d['dong']:>4}  .request({d['phuong_thuc']!r}, …)\n")
    return kq


def main(argv=None):
    ap = argparse.ArgumentParser(description="Đo ranh giới chung/đặc thù của app/http_jt.py bằng AST")
    ap.add_argument("--json", help="ghi kết quả JSON ra tệp này")
    ap.add_argument("--http", default=None)
    ap.add_argument("--adapter", default=None)
    a = ap.parse_args(argv)
    kq = phan_tich(a.http, a.adapter)
    in_bang(kq)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(kq, f, ensure_ascii=False, indent=2, sort_keys=True)
        print(f"\n[bằng chứng JSON] {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
