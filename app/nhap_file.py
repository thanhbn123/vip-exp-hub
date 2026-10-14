# G05/G08 — Import engine: UPLOADED → PARSING → VALIDATING → READY → APPROVED → PROCESSING
#            → COMPLETED | PARTIAL_FAILED | FAILED.
# Hỗ trợ: CSV (đầy đủ) · XLSX (parser stdlib: zipfile + XML, sheet đầu tiên) ·
# PDF có lớp văn bản (best-effort, GIỚI HẠN GHI RÕ: chỉ PDF text đơn giản, mỗi dòng một bản ghi
# phân tách bằng tab/; — PDF scan/ảnh KHÔNG hỗ trợ: batch → FAILED + dòng UNSUPPORTED, không đoán).
#
# Bảo mật của tầng này (file tải lên là DỮ LIỆU KHÔNG TIN CẬY):
#   · CSV formula injection: phát hiện khi validate (NEEDS_REVIEW) + làm sạch khi XUẤT ra CSV.
#   · Giới hạn tài nguyên: dung lượng file, số dòng, số ô/dòng, độ dài ô.
#   · XLSX là file zip → chặn zip bomb (tổng dung lượng sau giải nén + tỉ lệ nén) và
#     path traversal trong tên thành viên zip.
#   · XML: chặn DOCTYPE/ENTITY (billion-laughs) TRƯỚC khi đưa vào ElementTree.
#   · Không bao giờ thực thi macro hay mã từ file tải lên — chỉ đọc XML/văn bản thuần.
import io
import json
import re
import unicodedata
import zipfile
import zlib
from xml.etree import ElementTree

import csdl
import don_hang

TRUONG = ("nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi",
          "hang_hoa", "so_luong", "khoi_luong_gram", "cod", "gia_tri_khai", "ghi_chu")

# ---------- máy trạng thái (contract mục 6 SHARED_CONTRACTS) ----------
TRANG_THAI_BATCH = ("UPLOADED", "PARSING", "VALIDATING", "READY", "APPROVED", "PROCESSING",
                    "COMPLETED", "PARTIAL_FAILED", "FAILED")
TRANG_THAI_DONG = ("VALID", "INVALID", "READY", "SUBMITTED", "SUCCESS", "FAILED",
                   "UNSUPPORTED", "NEEDS_REVIEW")
# Dữ liệu cũ (trước contract) phải ĐỌC được — không migrate dữ liệu thì mã vẫn chịu được.
BATCH_CU = {"moi": "READY", "da_duyet_mot_phan": "PARTIAL_FAILED", "xong": "COMPLETED"}
CHUYEN_BATCH = {
    "UPLOADED": ("PARSING", "FAILED"),
    "PARSING": ("VALIDATING", "FAILED"),
    "VALIDATING": ("READY", "FAILED"),
    "READY": ("READY", "VALIDATING", "APPROVED", "FAILED"),
    "APPROVED": ("PROCESSING", "FAILED"),
    "PROCESSING": ("COMPLETED", "PARTIAL_FAILED", "FAILED"),
    "COMPLETED": ("APPROVED",),          # duyệt lại (idempotent) — không nhân đôi đơn
    "PARTIAL_FAILED": ("APPROVED", "VALIDATING", "READY"),
    "FAILED": (),                        # cuối đường: parse hỏng thì không duyệt được
}
DONG_LAM_DUOC = ("VALID", "READY", "FAILED")      # dòng được phép tạo đơn nháp
DONG_CON_VIEC = ("VALID", "READY", "INVALID", "NEEDS_REVIEW", "SUBMITTED")

# ---------- giới hạn tài nguyên (đổi ở ĐÂY, không rải ra nơi khác) ----------
GIOI_HAN_BYTE_FILE = 10 * 1024 * 1024      # 10 MiB một file tải lên
GIOI_HAN_SO_DONG = 5_000                   # số dòng dữ liệu tối đa (không kể tiêu đề)
GIOI_HAN_SO_O_MOI_DONG = 100               # số ô tối đa một dòng
GIOI_HAN_DAI_O = 10_000                    # ký tự tối đa một ô
ZIP_TONG_GIAI_NEN = 64 * 1024 * 1024       # tổng dung lượng sau giải nén của cả file xlsx
ZIP_TI_LE_TOI_DA = 120                     # tỉ lệ giải nén tối đa của MỘT thành viên zip
ZIP_SO_THANH_VIEN = 300                    # số file bên trong zip tối đa
PDF_GIOI_HAN_CHUOI = 200_000               # số chuỗi Tj/TJ tối đa rút từ PDF


class LoiKhongHoTro(don_hang.LoiNghiepVu):
    """Định dạng/nội dung hợp lệ nhưng tầng này KHÔNG đọc được (ví dụ PDF scan).
    Khác lỗi nghiệp vụ thường: dòng ghi nhận là UNSUPPORTED, không phải INVALID."""


# ---------- chuẩn hóa tên cột ----------
def _bo_dau(s):
    """Bỏ dấu tiếng Việt + đ/Đ → d. unicodedata là stdlib, không phụ thuộc ngoài."""
    s = str(s).replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c))


def chuan_ten_cot(s):
    """Khóa so khớp tên cột: bỏ dấu + hạ chữ + bỏ mọi ký tự không phải chữ/số.
    Nhờ vậy 'Số điện thoại', 'SO_DIEN_THOAI', 'so dien thoai' là MỘT."""
    return re.sub(r"[^a-z0-9]", "", _bo_dau(s).lower())


# Biến thể tên cột thật hay gặp trong file khách gửi. Thêm biến thể mới vào ĐÂY.
BIEN_THE_COT = {
    "nguoi_nhan_ten": ("recipient_name", "recipient", "customer name", "customer_name",
                       "người nhận", "nguoi nhan", "ten nguoi nhan", "tên người nhận",
                       "ho ten nguoi nhan", "họ tên người nhận", "ten khach", "tên khách",
                       "ten khach hang", "tên khách hàng", "name"),
    "nguoi_nhan_sdt": ("recipient_phone", "phone", "phone_number", "mobile", "tel", "telephone",
                       "sdt", "sđt", "so dien thoai", "số điện thoại", "điện thoại", "dien thoai",
                       "dt", "so dt", "số đt"),
    "nguoi_nhan_dia_chi": ("recipient_address", "address", "dia chi", "địa chỉ",
                           "dia chi nhan", "địa chỉ nhận", "dia_chi"),
    "hang_hoa": ("product_name", "product", "products", "item", "goods",
                 "hang hoa", "hàng hóa", "san pham", "sản phẩm", "ten hang", "tên hàng",
                 "ten san pham", "tên sản phẩm", "noi dung hang", "nội dung hàng"),
    "so_luong": ("quantity", "qty", "sl", "so luong", "số lượng", "so_luong"),
    "khoi_luong_gram": ("weight", "weight_grams", "weight_gram", "kl", "khoi luong", "khối lượng",
                        "trong luong", "trọng lượng", "can nang", "cân nặng", "khoi_luong_gram",
                        "khoi luong gram", "khối lượng (gram)", "trọng lượng (g)"),
    "cod": ("cod", "cod_amount", "thu ho", "thu hộ", "tien thu ho", "tiền thu hộ",
            "tien cod", "tiền cod", "so tien thu ho", "số tiền thu hộ"),
    "gia_tri_khai": ("declared_value", "value", "gia tri khai", "giá trị khai",
                     "gia tri hang", "giá trị hàng", "gia tri khai gia", "giá trị khai giá"),
    "ghi_chu": ("note", "notes", "remark", "remarks", "ghi chu", "ghi chú",
                "luu y", "lưu ý", "ghi chu giao hang", "ghi chú giao hàng"),
}
# bảng tra: khóa chuẩn hóa → trường chuẩn. Dựng một lần lúc nạp module.
ANH_XA_TU_DONG = {}
for _truong, _ds in BIEN_THE_COT.items():
    ANH_XA_TU_DONG[chuan_ten_cot(_truong)] = _truong
    for _bt in _ds:
        ANH_XA_TU_DONG[chuan_ten_cot(_bt)] = _truong


# ---------- chống CSV formula injection ----------
# Excel/LibreOffice/Google Sheets THỰC THI ô bắt đầu bằng = + - @ (và các ký tự đó sau
# tab/CR, vì bộ đọc bỏ qua khoảng trắng đầu). Vector thật: =cmd|'/C calc'!A0 (DDE),
# =HYPERLINK(...) dụ người bấm, =WEBSERVICE(...) gửi dữ liệu ra ngoài.
KY_TU_CONG_THUC = ("=", "+", "-", "@")
_RE_SO = re.compile(r"[+-]?\d+(?:[.,]\d+)?%?$")


def _la_so(s):
    return bool(_RE_SO.match(s.replace(" ", "").replace(" ", "")))


def rui_ro_cong_thuc(gia_tri):
    """True nếu ô này sẽ bị bảng tính coi là công thức khi mở file CSV xuất ra.
    Số âm thuần ('-5', '-1.5') KHÔNG tính là rủi ro — nếu tính thì mọi cột COD/tiền
    đều báo động giả và người dùng sẽ học cách bỏ qua cảnh báo."""
    s = "" if gia_tri is None else str(gia_tri)
    than = s.lstrip(" \t\r\n ")
    if not than:
        return False
    if _la_so(than):
        return False
    return than[0] in KY_TU_CONG_THUC


def lam_sach_o_xuat(gia_tri):
    """Làm sạch MỘT ô trước khi ghi ra CSV: vô hiệu công thức bằng tiền tố ' và
    bỏ CR/LF (chống chèn dòng giả vào file xuất). Giữ nguyên nội dung đọc được."""
    s = "" if gia_tri is None else str(gia_tri)
    s = s.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    if rui_ro_cong_thuc(s):
        s = "'" + s.lstrip(" \t ")
    return s


def _o_csv(gia_tri):
    s = lam_sach_o_xuat(gia_tri)
    return '"' + s.replace('"', '""') + '"'


def xuat_csv(tenant_id, batch_id):
    """Xuất batch ra CSV ĐÃ LÀM SẠCH. Luôn đi qua lam_sach_o_xuat — không có đường
    ghi CSV thứ hai trong file này, nên không thể quên làm sạch ở một chỗ."""
    b = csdl.mot("SELECT * FROM import_batch WHERE id=? AND tenant_id=?", (batch_id, tenant_id))
    if not b:
        raise don_hang.LoiNghiepVu("không có batch này", 404)
    cot = ("stt", "trang_thai", "loi") + TRUONG
    ra = [",".join(_o_csv(c) for c in cot)]
    for d in csdl.nhieu("SELECT * FROM import_dong WHERE batch_id=? ORDER BY stt", (batch_id,)):
        r = json.loads(d["du_lieu_json"])
        hang = [d["stt"], d["trang_thai"], d["loi"] or ""] + [r.get(t, "") for t in TRUONG]
        ra.append(",".join(_o_csv(x) for x in hang))
    return "\r\n".join(ra) + "\r\n"


# ---------- parser ----------
def _kiem_dung_luong(du_lieu: bytes):
    if len(du_lieu) > GIOI_HAN_BYTE_FILE:
        raise don_hang.LoiNghiepVu(
            f"file {len(du_lieu)} byte, vượt giới hạn {GIOI_HAN_BYTE_FILE} byte", 413)


def _kiem_bang(dong):
    """Chốt giới hạn trên BẢNG đã parse — dùng chung cho cả ba parser, nên thêm
    parser mới cũng không lọt giới hạn."""
    if len(dong) > GIOI_HAN_SO_DONG + 1:
        raise don_hang.LoiNghiepVu(
            f"file có {len(dong) - 1} dòng dữ liệu, vượt giới hạn {GIOI_HAN_SO_DONG} dòng", 413)
    for i, h in enumerate(dong, 1):
        if len(h) > GIOI_HAN_SO_O_MOI_DONG:
            raise don_hang.LoiNghiepVu(
                f"dòng {i} có {len(h)} ô, vượt giới hạn {GIOI_HAN_SO_O_MOI_DONG} ô", 413)
        for o in h:
            if len(str(o)) > GIOI_HAN_DAI_O:
                raise don_hang.LoiNghiepVu(
                    f"dòng {i} có ô dài {len(str(o))} ký tự, vượt giới hạn {GIOI_HAN_DAI_O}", 413)
    return dong


def doc_csv(text):
    dong, o, hang, trong_nhay = [], "", [], False
    for i, c in enumerate(text):
        if len(dong) > GIOI_HAN_SO_DONG + 1:
            raise don_hang.LoiNghiepVu(
                f"file vượt giới hạn {GIOI_HAN_SO_DONG} dòng dữ liệu", 413)
        if len(o) > GIOI_HAN_DAI_O:
            raise don_hang.LoiNghiepVu(f"có ô dài hơn {GIOI_HAN_DAI_O} ký tự", 413)
        if len(hang) > GIOI_HAN_SO_O_MOI_DONG:
            raise don_hang.LoiNghiepVu(f"có dòng nhiều hơn {GIOI_HAN_SO_O_MOI_DONG} ô", 413)
        if trong_nhay:
            if c == '"' and text[i + 1:i + 2] == '"':
                o += '"'
            elif c == '"':
                trong_nhay = False
            elif text[i - 1] == '"' and o and o[-1] == '"':
                pass
            else:
                o += c
        elif c == '"':
            trong_nhay = True
        elif c == ",":
            hang.append(o); o = ""
        elif c in "\r\n":
            if c == "\r" and text[i + 1:i + 2] == "\n":
                continue
            hang.append(o); o = ""
            if any(x.strip() for x in hang):
                dong.append(hang)
            hang = []
        else:
            o += c
    if o or hang:
        hang.append(o)
        if any(x.strip() for x in hang):
            dong.append(hang)
    return _kiem_bang(dong)


def _ten_zip_an_toan(ten):
    """Chặn path traversal trong tên thành viên zip. Ta chỉ ĐỌC theo tên nên không
    ghi ra đĩa, nhưng tên bẩn là dấu hiệu file dựng để tấn công → từ chối sớm."""
    if not ten or ten.startswith("/") or ten.startswith("\\"):
        return False
    if ".." in ten.replace("\\", "/").split("/"):
        return False
    if re.match(r"^[A-Za-z]:", ten):
        return False
    return True


def _doc_xml_an_toan(zf, ten, da_kiem):
    """Đọc một thành viên zip rồi parse XML. Hai chốt:
    1) chỉ đọc tên đã qua kiểm zip bomb/traversal;
    2) chặn DOCTYPE/ENTITY trước khi vào ElementTree — expat CÓ expand entity nội bộ,
       nên billion-laughs là thật; không dựa vào niềm tin 'ElementTree an toàn'."""
    if ten not in da_kiem:
        raise don_hang.LoiNghiepVu(f"XLSX: thành viên zip không qua kiểm: {ten}", 400)
    with zf.open(ten) as f:
        tho = f.read(ZIP_TONG_GIAI_NEN + 1)
    if len(tho) > ZIP_TONG_GIAI_NEN:
        raise don_hang.LoiNghiepVu("XLSX: một thành phần giải nén quá lớn", 413)
    thap = tho[:200_000].lower()
    if b"<!doctype" in thap or b"<!entity" in thap:
        raise don_hang.LoiNghiepVu(
            "XLSX chứa khai báo DOCTYPE/ENTITY — từ chối (chống XML entity expansion)", 400)
    try:
        return ElementTree.fromstring(tho)
    except ElementTree.ParseError as e:
        raise don_hang.LoiNghiepVu(f"XLSX: XML hỏng ({e})", 400)


def doc_xlsx(du_lieu: bytes):
    """Parser XLSX tối thiểu bằng stdlib: sheet1 + sharedStrings. Chống zip bomb."""
    if du_lieu[:2] != b"PK":
        raise don_hang.LoiNghiepVu("file .xlsx không phải file zip (sai định dạng)", 400)
    try:
        zf = zipfile.ZipFile(io.BytesIO(du_lieu))
    except zipfile.BadZipFile as e:
        raise don_hang.LoiNghiepVu(f"file .xlsx hỏng, không mở được: {e}", 400)
    thanh_vien = zf.infolist()
    if len(thanh_vien) > ZIP_SO_THANH_VIEN:
        raise don_hang.LoiNghiepVu(
            f"XLSX có {len(thanh_vien)} file bên trong, vượt giới hạn {ZIP_SO_THANH_VIEN}", 413)
    tong = 0
    da_kiem = set()
    for tv in thanh_vien:
        if not _ten_zip_an_toan(tv.filename):
            raise don_hang.LoiNghiepVu(
                f"XLSX có tên file bên trong không an toàn (path traversal): {tv.filename!r}", 400)
        tong += tv.file_size
        if tong > ZIP_TONG_GIAI_NEN:
            raise don_hang.LoiNghiepVu(
                f"XLSX giải nén ra hơn {ZIP_TONG_GIAI_NEN} byte — từ chối (nghi zip bomb)", 413)
        if tv.compress_size > 0:
            ti_le = tv.file_size / tv.compress_size
            if ti_le > ZIP_TI_LE_TOI_DA and tv.file_size > 1024 * 1024:
                raise don_hang.LoiNghiepVu(
                    f"XLSX có thành phần tỉ lệ nén {ti_le:.0f}x (>{ZIP_TI_LE_TOI_DA}x) — "
                    "từ chối (nghi zip bomb)", 413)
        da_kiem.add(tv.filename)

    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    chuoi = []
    if "xl/sharedStrings.xml" in da_kiem:
        goc = _doc_xml_an_toan(zf, "xl/sharedStrings.xml", da_kiem)
        for si in goc.findall("m:si", ns):
            chuoi.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
    ten_sheet = next((n for n in sorted(da_kiem) if re.fullmatch(r"xl/worksheets/sheet1\.xml", n)), None)
    if not ten_sheet:
        ten_sheet = next((n for n in sorted(da_kiem) if n.startswith("xl/worksheets/sheet")), None)
    if not ten_sheet:
        raise don_hang.LoiNghiepVu("XLSX không có worksheet nào", 400)
    goc = _doc_xml_an_toan(zf, ten_sheet, da_kiem)
    dong = []
    for row in goc.iter("{%s}row" % ns["m"]):
        if len(dong) > GIOI_HAN_SO_DONG + 1:
            raise don_hang.LoiNghiepVu(
                f"XLSX vượt giới hạn {GIOI_HAN_SO_DONG} dòng dữ liệu", 413)
        hang = {}
        for c in row.findall("m:c", ns):
            ref = c.get("r", "")
            cot = re.match(r"([A-Z]+)", ref)
            idx = 0
            if cot:
                for ch in cot.group(1):
                    idx = idx * 26 + (ord(ch) - 64)
                idx -= 1
            if idx < 0 or idx >= GIOI_HAN_SO_O_MOI_DONG:
                raise don_hang.LoiNghiepVu(
                    f"XLSX có ô ở cột {ref!r} vượt giới hạn {GIOI_HAN_SO_O_MOI_DONG} cột", 413)
            v = c.find("m:v", ns)
            gia_tri = v.text if v is not None else ""
            if c.get("t") == "s" and gia_tri:
                try:
                    vt = int(gia_tri)
                except ValueError:
                    raise don_hang.LoiNghiepVu("XLSX: chỉ số sharedStrings không phải số", 400)
                if vt < 0 or vt >= len(chuoi):
                    raise don_hang.LoiNghiepVu("XLSX: chỉ số sharedStrings ngoài khoảng", 400)
                gia_tri = chuoi[vt]
            if c.get("t") == "inlineStr":
                gia_tri = "".join(t.text or "" for t in c.iter("{%s}t" % ns["m"]))
            hang[idx] = gia_tri or ""
        if hang:
            so_cot = max(hang) + 1
            dong.append([hang.get(i, "") for i in range(so_cot)])
    return _kiem_bang([d for d in dong if any(str(x).strip() for x in d)])


def doc_pdf_text(du_lieu: bytes):
    """Best-effort: rút chuỗi trong toán tử Tj/TJ của PDF có lớp văn bản (không nén hoặc FlateDecode).
    GIỚI HẠN: PDF scan/ảnh, font subset mã hóa riêng → không đọc được; khi đó trả LoiKhongHoTro."""
    van_ban = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", du_lieu, re.S):
        tho = m.group(1)
        try:
            # decompressobj + max_length: PDF cũng có thể là quả bom nén.
            giai_nen = zlib.decompressobj()
            tho2 = giai_nen.decompress(tho, ZIP_TONG_GIAI_NEN)
            if giai_nen.unconsumed_tail:
                raise don_hang.LoiNghiepVu("PDF: luồng giải nén quá lớn — từ chối", 413)
            tho = tho2
        except zlib.error:
            pass
        for s in re.findall(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", tho):
            van_ban.append(s)
        for mang in re.findall(rb"\[(.*?)\]\s*TJ", tho, re.S):
            van_ban.extend(re.findall(rb"\(((?:[^()\\]|\\.)*)\)", mang))
        if len(van_ban) > PDF_GIOI_HAN_CHUOI:
            raise don_hang.LoiNghiepVu(
                f"PDF có hơn {PDF_GIOI_HAN_CHUOI} khối văn bản — vượt giới hạn", 413)
    if not van_ban:
        raise LoiKhongHoTro(
            "PDF không có lớp văn bản đọc được (có thể là bản scan) — chưa hỗ trợ PDF scan/OCR")

    def giai(b):
        return b.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\").decode("latin-1")

    cac_dong = "\n".join(giai(v) for v in van_ban).splitlines()
    dong = []
    for d in cac_dong:
        d = d.strip()
        if not d:
            continue
        cot = re.split(r"\t|;", d)
        dong.append([c.strip() for c in cot])
    if not dong:
        raise LoiKhongHoTro("PDF đọc được văn bản nhưng không tách được dòng dữ liệu nào")
    return _kiem_bang(dong)


# ---------- normalize + validate ----------
def anh_xa_cot(hang_dau):
    anh_xa = {}
    for i, ten in enumerate(hang_dau):
        chuan = ANH_XA_TU_DONG.get(chuan_ten_cot(ten))
        if chuan and chuan not in anh_xa.values():
            anh_xa[i] = chuan
    return anh_xa


def kiem_dong(r):
    """Lỗi CHẶN (dòng INVALID, không tạo đơn được)."""
    loi = []
    if not r.get("nguoi_nhan_ten", "").strip():
        loi.append("thiếu tên người nhận")
    sdt = r.get("nguoi_nhan_sdt", "").replace(" ", "").replace(".", "").replace("-", "")
    if not re.fullmatch(r"0\d{9}", sdt):
        loi.append("SĐT phải 10 số bắt đầu bằng 0")
    if not r.get("nguoi_nhan_dia_chi", "").strip():
        loi.append("thiếu địa chỉ")
    if not r.get("hang_hoa", "").strip():
        loi.append("thiếu tên hàng")
    try:
        if float(r.get("khoi_luong_gram") or 0) <= 0:
            loi.append("cân nặng phải > 0")
    except ValueError:
        loi.append("cân nặng không phải số")
    try:
        if float(r.get("cod") or 0) < 0:
            loi.append("COD không được âm")
    except ValueError:
        loi.append("COD không phải số")
    return loi


def canh_bao_dong(r):
    """Cảnh báo CẦN NGƯỜI XEM (dòng NEEDS_REVIEW): không chặn vĩnh viễn, nhưng
    không tự tạo đơn — người xác nhận thì mới đi tiếp."""
    cb = []
    o_xau = [t for t in TRUONG if rui_ro_cong_thuc(r.get(t, ""))]
    if o_xau:
        cb.append("ô có thể bị bảng tính thực thi như công thức: " + ", ".join(o_xau))
    return cb


def khoa_trung(r):
    """Khóa phát hiện dòng trùng trong CÙNG batch: SĐT + địa chỉ + sản phẩm."""
    sdt = re.sub(r"\D", "", r.get("nguoi_nhan_sdt", ""))
    dc = re.sub(r"\s+", " ", _bo_dau(r.get("nguoi_nhan_dia_chi", "")).lower()).strip()
    sp = re.sub(r"\s+", " ", _bo_dau(r.get("hang_hoa", "")).lower()).strip()
    if not (sdt or dc or sp):
        return None
    return (sdt, dc, sp)


def _phan_loai(r, loi, cb):
    if loi:
        return "INVALID", "; ".join(loi)
    if cb:
        return "NEEDS_REVIEW", "cần xem: " + "; ".join(cb)
    return "VALID", None


# ---------- trạng thái batch ----------
def trang_thai_batch(b):
    """Đọc trạng thái batch, dịch giá trị cũ sang contract. Mọi nơi đọc trạng thái
    batch phải đi qua đây — không so chuỗi thô ở chỗ khác."""
    tt = (b if isinstance(b, str) else b["trang_thai"]) or "UPLOADED"
    tt = BATCH_CU.get(tt, tt)
    return tt if tt in TRANG_THAI_BATCH else "UPLOADED"


_co_cot_loi = None


def _ghi_trang_thai(tenant_id, batch_id, tt, loi=None):
    """Ghi trạng thái (+ lý do nếu CSDL đã có cột `loi`). Chịu được CSDL cũ chưa migrate.

    BẮT BUỘC tenant_id trong mệnh đề WHERE: trước đây hàm này ghi theo id trần và chỉ an toàn
    nhờ mọi caller đã resolve tenant trước. Caller thứ ba quên là lỗi chéo tenant KHÔNG có gì
    báo (AG-07 QA nêu đúng dạng này ở Q-10). Phòng thủ ngay tại câu SQL."""
    global _co_cot_loi
    if _co_cot_loi is None:
        _co_cot_loi = any(c["name"] == "loi"
                          for c in csdl.nhieu("PRAGMA table_info(import_batch)"))
    if _co_cot_loi:
        csdl.ghi("UPDATE import_batch SET trang_thai=?, loi=? WHERE id=? AND tenant_id=?",
                 (tt, loi, batch_id, tenant_id))
    else:
        csdl.ghi("UPDATE import_batch SET trang_thai=? WHERE id=? AND tenant_id=?",
                 (tt, batch_id, tenant_id))


def chuyen_batch(tenant_id, batch_id, moi, loi=None):
    """Chuyển trạng thái batch THEO máy trạng thái. Chuyển sai thứ tự → lỗi, không
    im lặng ghi đè: trạng thái đi lùi mà không báo là một dạng hỏng im lặng."""
    b = csdl.mot("SELECT * FROM import_batch WHERE id=? AND tenant_id=?", (batch_id, tenant_id))
    if not b:
        raise don_hang.LoiNghiepVu("không có batch này", 404)
    cu = trang_thai_batch(b)
    if moi not in TRANG_THAI_BATCH:
        raise don_hang.LoiNghiepVu(f"trạng thái batch không hợp lệ: {moi}")
    if moi not in CHUYEN_BATCH[cu]:
        raise don_hang.LoiNghiepVu(f"batch {batch_id}: không chuyển được {cu} → {moi}")
    _ghi_trang_thai(tenant_id, batch_id, moi, loi)
    return moi


# ---------- UPLOAD → PARSE → VALIDATE ----------
def _parse(duoi, du_lieu):
    if duoi == "csv":
        return doc_csv(du_lieu.decode("utf-8-sig", "replace"))
    if duoi == "xlsx":
        return doc_xlsx(du_lieu)
    if duoi == "pdf":
        return doc_pdf_text(du_lieu)
    raise don_hang.LoiNghiepVu(f"định dạng .{duoi} chưa hỗ trợ (nhận CSV, XLSX, PDF text)")


def tao_batch(tenant_id, user_id, ten_file, du_lieu: bytes):
    """UPLOADED → PARSING → VALIDATING → READY. Hỏng ở bước nào thì batch → FAILED
    kèm lý do, rồi NÉM lỗi — batch FAILED ở lại CSDL làm dấu vết, không biến mất."""
    _kiem_dung_luong(du_lieu)
    duoi = ten_file.rsplit(".", 1)[-1].lower()
    con = csdl.ghi("INSERT INTO import_batch (tenant_id, ten_file, loai_file, trang_thai, nguoi_tao, tao_luc)"
                   " VALUES (?,?,?,?,?,?)",
                   (tenant_id, ten_file, duoi, "UPLOADED", user_id, csdl.bay_gio()))
    batch_id = con.lastrowid
    try:
        chuyen_batch(tenant_id, batch_id, "PARSING")
        bang = _parse(duoi, du_lieu)
        if len(bang) < 2:
            raise don_hang.LoiNghiepVu("file không có dữ liệu (cần dòng tiêu đề + ít nhất 1 dòng)")
        anh_xa = anh_xa_cot(bang[0])
        bat_buoc = {"nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi",
                    "hang_hoa", "khoi_luong_gram"}
        thieu = bat_buoc - set(anh_xa.values())
        if thieu:
            raise don_hang.LoiNghiepVu("không nhận diện được cột: " + ", ".join(sorted(thieu)))
        chuyen_batch(tenant_id, batch_id, "VALIDATING")
        da_thay = {}
        for stt, hang in enumerate(bang[1:], 1):
            r = {t: "" for t in TRUONG}
            for i, chuan in anh_xa.items():
                r[chuan] = str(hang[i]).strip() if i < len(hang) else ""
            loi = kiem_dong(r)
            cb = canh_bao_dong(r)
            k = khoa_trung(r)
            if k is not None and k in da_thay:
                cb.append(f"trùng dòng {da_thay[k]} (cùng SĐT + địa chỉ + sản phẩm)")
            elif k is not None:
                da_thay[k] = stt
            tt, ghi_loi = _phan_loai(r, loi, cb)
            csdl.ghi("INSERT INTO import_dong (batch_id, stt, du_lieu_json, trang_thai, loi)"
                     " VALUES (?,?,?,?,?)",
                     (batch_id, stt, json.dumps(r, ensure_ascii=False), tt, ghi_loi))
        chuyen_batch(tenant_id, batch_id, "READY")
    except LoiKhongHoTro as e:
        # Định dạng không đọc được: để lại MỘT dòng UNSUPPORTED làm dấu vết cho người xem.
        csdl.ghi("INSERT INTO import_dong (batch_id, stt, du_lieu_json, trang_thai, loi)"
                 " VALUES (?,?,?,?,?)",
                 (batch_id, 1, json.dumps({t: "" for t in TRUONG}, ensure_ascii=False),
                  "UNSUPPORTED", str(e)))
        _ghi_trang_thai(tenant_id, batch_id, "FAILED", str(e))
        csdl.audit("import_that_bai", f"batch:{batch_id}", str(e),
                   tenant_id=tenant_id, user_id=user_id, ket_qua="that_bai")
        raise
    except Exception as e:
        _ghi_trang_thai(tenant_id, batch_id, "FAILED", str(e))
        csdl.audit("import_that_bai", f"batch:{batch_id}", f"{type(e).__name__}: {e}",
                   tenant_id=tenant_id, user_id=user_id, ket_qua="that_bai")
        raise
    return batch_id


def _lay_dong(tenant_id, dong_id):
    d = csdl.mot("SELECT d.*, b.tenant_id t FROM import_dong d JOIN import_batch b ON b.id=d.batch_id"
                 " WHERE d.id=?", (dong_id,))
    if not d or d["t"] != tenant_id:
        raise don_hang.LoiNghiepVu("không có dòng này", 404)
    return d


def sua_dong(tenant_id, dong_id, du_lieu_moi):
    d = _lay_dong(tenant_id, dong_id)
    if d["trang_thai"] in ("SUBMITTED", "SUCCESS"):
        raise don_hang.LoiNghiepVu("dòng đã tạo đơn — không sửa được nữa")
    if d["trang_thai"] == "UNSUPPORTED":
        raise don_hang.LoiNghiepVu("dòng không đọc được từ file gốc — nhập lại bằng CSV/XLSX")
    r = json.loads(d["du_lieu_json"])
    r.update({k: str(v).strip() for k, v in du_lieu_moi.items() if k in TRUONG})
    loi = kiem_dong(r)
    cb = canh_bao_dong(r)
    k = khoa_trung(r)
    if k is not None:
        for khac in csdl.nhieu("SELECT stt, du_lieu_json FROM import_dong"
                               " WHERE batch_id=? AND id<>? ORDER BY stt", (d["batch_id"], dong_id)):
            if khoa_trung(json.loads(khac["du_lieu_json"])) == k:
                cb.append(f"trùng dòng {khac['stt']} (cùng SĐT + địa chỉ + sản phẩm)")
                break
    tt, ghi_loi = _phan_loai(r, loi, cb)
    csdl.ghi("UPDATE import_dong SET du_lieu_json=?, trang_thai=?, loi=? WHERE id=?",
             (json.dumps(r, ensure_ascii=False), tt, ghi_loi, dong_id))
    return {"trang_thai": tt, "loi": loi, "canh_bao": cb}


def xac_nhan_dong(tenant_id, user_id, dong_id):
    """Người đã XEM dòng NEEDS_REVIEW và chấp nhận → READY (được tạo đơn).
    Không tự loại, không tự chấp nhận: quyết định này phải do người bấm."""
    d = _lay_dong(tenant_id, dong_id)
    if d["trang_thai"] != "NEEDS_REVIEW":
        raise don_hang.LoiNghiepVu(
            f"chỉ xác nhận được dòng NEEDS_REVIEW (hiện: {d['trang_thai']})")
    loi = kiem_dong(json.loads(d["du_lieu_json"]))
    if loi:
        raise don_hang.LoiNghiepVu("dòng còn lỗi, sửa trước đã: " + "; ".join(loi))
    csdl.ghi("UPDATE import_dong SET trang_thai='READY' WHERE id=?", (dong_id,))
    csdl.audit("import_xac_nhan_dong", f"import_dong:{dong_id}", d["loi"] or "",
               tenant_id=tenant_id, user_id=user_id)
    return {"trang_thai": "READY"}


# ---------- APPROVE → PROCESSING → COMPLETED | PARTIAL_FAILED | FAILED ----------
def _dem_dong(batch_id):
    ra = {t: 0 for t in TRANG_THAI_DONG}
    for r in csdl.nhieu("SELECT trang_thai, COUNT(*) c FROM import_dong WHERE batch_id=?"
                        " GROUP BY trang_thai", (batch_id,)):
        ra[r["trang_thai"]] = ra.get(r["trang_thai"], 0) + r["c"]
    return ra


def duyet_batch(tenant_id, user_id, batch_id, dong_ids, nguoi_gui):
    """APPROVE: tạo ĐƠN NHÁP (don_hang.tao_don, idem_key) cho các dòng làm được.
    Dòng INVALID/NEEDS_REVIEW/UNSUPPORTED bị bỏ qua — không tự tạo đơn cho thứ
    người chưa xem. Dòng lỗi giữ nguyên, batch không hỏng."""
    b = csdl.mot("SELECT * FROM import_batch WHERE id=? AND tenant_id=?", (batch_id, tenant_id))
    if not b:
        raise don_hang.LoiNghiepVu("không có batch này", 404)
    cu = trang_thai_batch(b)
    if "APPROVED" not in CHUYEN_BATCH[cu]:
        raise don_hang.LoiNghiepVu(f"batch đang ở trạng thái {cu} — chưa duyệt được")
    chuyen_batch(tenant_id, batch_id, "APPROVED")
    chuyen_batch(tenant_id, batch_id, "PROCESSING")
    kq = {"SUCCESS": 0, "FAILED": 0, "bo_qua": 0}
    for dong_id in dong_ids:
        d = csdl.mot("SELECT * FROM import_dong WHERE id=? AND batch_id=?", (dong_id, batch_id))
        if not d or d["trang_thai"] not in DONG_LAM_DUOC:
            kq["bo_qua"] += 1
            continue
        r = json.loads(d["du_lieu_json"])
        csdl.ghi("UPDATE import_dong SET trang_thai='SUBMITTED' WHERE id=?", (dong_id,))
        try:
            don, _ = don_hang.tao_don(tenant_id, user_id, {
                "nguoi_gui_ten": nguoi_gui["ten"], "nguoi_gui_sdt": nguoi_gui["sdt"],
                "nguoi_gui_dia_chi": nguoi_gui["dia_chi"],
                "nguoi_nhan_ten": r["nguoi_nhan_ten"], "nguoi_nhan_sdt": r["nguoi_nhan_sdt"],
                "nguoi_nhan_dia_chi": r["nguoi_nhan_dia_chi"], "hang_hoa": r["hang_hoa"],
                "khoi_luong_gram": int(float(r["khoi_luong_gram"])),
                "cod": int(float(r.get("cod") or 0)), "gia_tri_khai": int(float(r.get("gia_tri_khai") or 0)),
                "ghi_chu": r.get("ghi_chu", ""),
            }, idem_key=f"import-{batch_id}-{dong_id}")  # idempotency: duyệt lại không nhân đôi đơn
            csdl.ghi("UPDATE import_dong SET trang_thai='SUCCESS', don_id=? WHERE id=?",
                     (don["id"], dong_id))
            kq["SUCCESS"] += 1
        except don_hang.LoiNghiepVu as e:
            csdl.ghi("UPDATE import_dong SET trang_thai='FAILED', loi=? WHERE id=?", (str(e), dong_id))
            kq["FAILED"] += 1
    dem = _dem_dong(batch_id)
    con_viec = sum(dem[t] for t in DONG_CON_VIEC)
    if dem["SUCCESS"] > 0 and dem["FAILED"] == 0 and con_viec == 0:
        cuoi = "COMPLETED"
    elif dem["SUCCESS"] == 0 and dem["FAILED"] == 0 and con_viec == 0:
        cuoi = "FAILED"          # không dòng nào làm được gì (ví dụ chỉ có UNSUPPORTED)
    else:
        cuoi = "PARTIAL_FAILED"
    chuyen_batch(tenant_id, batch_id, cuoi)
    kq["trang_thai_batch"] = cuoi
    csdl.audit("import_duyet", f"batch:{batch_id}", json.dumps(kq),
               tenant_id=tenant_id, user_id=user_id)
    return kq
