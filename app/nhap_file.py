# G08 — Import engine: UPLOAD → PARSE → NORMALIZE → VALIDATE → PREVIEW → APPROVE → CREATE ORDERS.
# Hỗ trợ: CSV (đầy đủ) · XLSX (parser stdlib: zipfile + XML, sheet đầu tiên) ·
# PDF có lớp văn bản (best-effort, GIỚI HẠN GHI RÕ: chỉ PDF text đơn giản, mỗi dòng một bản ghi
# phân tách bằng tab/; — PDF scan/ảnh KHÔNG hỗ trợ, trả lỗi rõ ràng, không đoán).
import io
import json
import re
import zipfile
import zlib
from xml.etree import ElementTree

import csdl
import don_hang

TRUONG = ("nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi",
          "hang_hoa", "so_luong", "khoi_luong_gram", "cod", "gia_tri_khai", "ghi_chu")
# tên cột hay gặp → trường chuẩn (normalize)
ANH_XA_TU_DONG = {
    "recipient_name": "nguoi_nhan_ten", "ten nguoi nhan": "nguoi_nhan_ten", "người nhận": "nguoi_nhan_ten",
    "recipient_phone": "nguoi_nhan_sdt", "sdt": "nguoi_nhan_sdt", "số điện thoại": "nguoi_nhan_sdt",
    "recipient_address": "nguoi_nhan_dia_chi", "dia chi": "nguoi_nhan_dia_chi", "địa chỉ": "nguoi_nhan_dia_chi",
    "product_name": "hang_hoa", "hang hoa": "hang_hoa", "hàng hóa": "hang_hoa",
    "quantity": "so_luong", "weight_grams": "khoi_luong_gram", "trọng lượng": "khoi_luong_gram",
    "cod_amount": "cod", "cod": "cod", "declared_value": "gia_tri_khai", "note": "ghi_chu", "ghi chú": "ghi_chu",
}


# ---------- parser ----------
def doc_csv(text):
    dong, o, hang, trong_nhay = [], "", [], False
    for i, c in enumerate(text):
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
    return dong


def doc_xlsx(du_lieu: bytes):
    """Parser XLSX tối thiểu bằng stdlib: sheet1 + sharedStrings."""
    zf = zipfile.ZipFile(io.BytesIO(du_lieu))
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    chuoi = []
    if "xl/sharedStrings.xml" in zf.namelist():
        goc = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in goc.findall("m:si", ns):
            chuoi.append("".join(t.text or "" for t in si.iter("{%s}t" % ns["m"])))
    ten_sheet = next((n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet1\.xml", n)), None)
    if not ten_sheet:
        ten_sheet = next((n for n in sorted(zf.namelist()) if n.startswith("xl/worksheets/sheet")), None)
    if not ten_sheet:
        raise ValueError("XLSX không có worksheet nào")
    goc = ElementTree.fromstring(zf.read(ten_sheet))
    dong = []
    for row in goc.iter("{%s}row" % ns["m"]):
        hang = {}
        for c in row.findall("m:c", ns):
            ref = c.get("r", "")
            cot = re.match(r"([A-Z]+)", ref)
            idx = 0
            if cot:
                for ch in cot.group(1):
                    idx = idx * 26 + (ord(ch) - 64)
                idx -= 1
            v = c.find("m:v", ns)
            gia_tri = v.text if v is not None else ""
            if c.get("t") == "s" and gia_tri:
                gia_tri = chuoi[int(gia_tri)]
            if c.get("t") == "inlineStr":
                gia_tri = "".join(t.text or "" for t in c.iter("{%s}t" % ns["m"]))
            hang[idx] = gia_tri or ""
        if hang:
            so_cot = max(hang) + 1
            dong.append([hang.get(i, "") for i in range(so_cot)])
    return [d for d in dong if any(str(x).strip() for x in d)]


def doc_pdf_text(du_lieu: bytes):
    """Best-effort: rút chuỗi trong toán tử Tj/TJ của PDF có lớp văn bản (không nén hoặc FlateDecode).
    GIỚI HẠN: PDF scan/ảnh, font subset mã hóa riêng → không đọc được; khi đó trả lỗi rõ."""
    van_ban = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", du_lieu, re.S):
        tho = m.group(1)
        try:
            tho = zlib.decompress(tho)
        except zlib.error:
            pass
        for s in re.findall(rb"\(((?:[^()\\]|\\.)*)\)\s*Tj", tho):
            van_ban.append(s)
        for mang in re.findall(rb"\[(.*?)\]\s*TJ", tho, re.S):
            van_ban.extend(re.findall(rb"\(((?:[^()\\]|\\.)*)\)", mang))
    if not van_ban:
        raise ValueError("PDF không có lớp văn bản đọc được (có thể là bản scan) — G08 chưa hỗ trợ PDF scan/OCR")
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
    return dong


# ---------- normalize + validate ----------
def anh_xa_cot(hang_dau):
    anh_xa = {}
    for i, ten in enumerate(hang_dau):
        chuan = ANH_XA_TU_DONG.get(str(ten).strip().lower())
        if chuan and chuan not in anh_xa.values():
            anh_xa[i] = chuan
    return anh_xa


def kiem_dong(r):
    loi = []
    if not r.get("nguoi_nhan_ten", "").strip():
        loi.append("thiếu tên người nhận")
    sdt = r.get("nguoi_nhan_sdt", "").replace(" ", "").replace(".", "")
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


def tao_batch(tenant_id, user_id, ten_file, du_lieu: bytes):
    """Parse file → tạo batch + các dòng VALID/INVALID. Không tạo đơn nào ở bước này."""
    duoi = ten_file.rsplit(".", 1)[-1].lower()
    if duoi == "csv":
        bang = doc_csv(du_lieu.decode("utf-8-sig", "replace"))
    elif duoi == "xlsx":
        bang = doc_xlsx(du_lieu)
    elif duoi == "pdf":
        bang = doc_pdf_text(du_lieu)
    else:
        raise don_hang.LoiNghiepVu(f"định dạng .{duoi} chưa hỗ trợ (G08 nhận CSV, XLSX, PDF text)")
    if len(bang) < 2:
        raise don_hang.LoiNghiepVu("file không có dữ liệu (cần dòng tiêu đề + ít nhất 1 dòng)")
    anh_xa = anh_xa_cot(bang[0])
    bat_buoc = {"nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa", "khoi_luong_gram"}
    thieu = bat_buoc - set(anh_xa.values())
    if thieu:
        raise don_hang.LoiNghiepVu("không nhận diện được cột: " + ", ".join(sorted(thieu)))
    con = csdl.ghi("INSERT INTO import_batch (tenant_id, ten_file, loai_file, nguoi_tao, tao_luc) VALUES (?,?,?,?,?)",
                   (tenant_id, ten_file, duoi, user_id, csdl.bay_gio()))
    batch_id = con.lastrowid
    for stt, hang in enumerate(bang[1:], 1):
        r = {t: "" for t in TRUONG}
        for i, chuan in anh_xa.items():
            r[chuan] = str(hang[i]).strip() if i < len(hang) else ""
        loi = kiem_dong(r)
        csdl.ghi("INSERT INTO import_dong (batch_id, stt, du_lieu_json, trang_thai, loi) VALUES (?,?,?,?,?)",
                 (batch_id, stt, json.dumps(r, ensure_ascii=False),
                  "INVALID" if loi else "VALID", "; ".join(loi) or None))
    return batch_id


def sua_dong(tenant_id, dong_id, du_lieu_moi):
    d = csdl.mot("SELECT d.*, b.tenant_id t FROM import_dong d JOIN import_batch b ON b.id=d.batch_id WHERE d.id=?",
                 (dong_id,))
    if not d or d["t"] != tenant_id:
        raise don_hang.LoiNghiepVu("không có dòng này", 404)
    if d["trang_thai"] in ("SUBMITTED", "SUCCESS"):
        raise don_hang.LoiNghiepVu("dòng đã tạo đơn — không sửa được nữa")
    r = json.loads(d["du_lieu_json"])
    r.update({k: str(v).strip() for k, v in du_lieu_moi.items() if k in TRUONG})
    loi = kiem_dong(r)
    csdl.ghi("UPDATE import_dong SET du_lieu_json=?, trang_thai=?, loi=? WHERE id=?",
             (json.dumps(r, ensure_ascii=False), "INVALID" if loi else "VALID", "; ".join(loi) or None, dong_id))
    return {"trang_thai": "INVALID" if loi else "VALID", "loi": loi}


def duyet_batch(tenant_id, user_id, batch_id, dong_ids, nguoi_gui):
    """APPROVE: tạo đơn nháp cho các dòng VALID được chọn. Dòng lỗi giữ nguyên, batch không hỏng."""
    b = csdl.mot("SELECT * FROM import_batch WHERE id=? AND tenant_id=?", (batch_id, tenant_id))
    if not b:
        raise don_hang.LoiNghiepVu("không có batch này", 404)
    kq = {"SUCCESS": 0, "FAILED": 0, "bo_qua": 0}
    for dong_id in dong_ids:
        d = csdl.mot("SELECT * FROM import_dong WHERE id=? AND batch_id=?", (dong_id, batch_id))
        if not d or d["trang_thai"] not in ("VALID", "READY", "FAILED"):
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
            csdl.ghi("UPDATE import_dong SET trang_thai='SUCCESS', don_id=? WHERE id=?", (don["id"], dong_id))
            kq["SUCCESS"] += 1
        except don_hang.LoiNghiepVu as e:
            csdl.ghi("UPDATE import_dong SET trang_thai='FAILED', loi=? WHERE id=?", (str(e), dong_id))
            kq["FAILED"] += 1
    csdl.ghi("UPDATE import_batch SET trang_thai=? WHERE id=?",
             ("xong" if kq["FAILED"] == 0 else "da_duyet_mot_phan", batch_id))
    csdl.audit("import_duyet", f"batch:{batch_id}", json.dumps(kq), tenant_id=tenant_id, user_id=user_id)
    return kq
