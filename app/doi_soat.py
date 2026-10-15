# G07.4 — ĐỐI SOÁT TIỀN với bảng kê của hãng: nạp file, ánh xạ cột theo hãng, đối chiếu,
# phân loại chênh lệch, PHÊ DUYỆT rồi mới áp vào sổ.
#
# ===== ĐÂY KHÔNG PHẢI `don_hang.doi_soat_don` =====
# `don_hang.doi_soat_don` / `doi_soat_tay` là đối soát KẾT QUẢ GỬI ĐƠN: hãng có nhận đơn hay
# không, đơn `dang_gui` thì thật ra đã vào hệ hãng chưa. File này là đối soát TIỀN: hãng thu
# được bao nhiêu COD, tính bao nhiêu phí. Hai việc khác nhau, hai bảng khác nhau, hai bộ
# trạng thái khác nhau — CỐ Ý không gộp, và file này KHÔNG gọi hai hàm đó.
#
# ===== BỐN BẤT BIẾN =====
# 1) MỖI HÃNG MỘT ĐỊNH DẠNG. Không có "mẫu chung". `ANH_XA_COT` tra theo mã hãng và có
#    PHIÊN BẢN, vì hãng đổi mẫu file mà không báo ai.
# 2) IDEMPOTENT BẰNG RÀNG BUỘC CSDL, không bằng phép kiểm trong mã:
#    `UNIQUE(tenant_id, hang, ky_thanh_toan, van_tay_dong)` trên `ds_dong`. Nạp lại đúng file
#    đó thì câu `INSERT` ném `IntegrityError` và dòng được ghi là `dong_trung` — không có khe
#    hở giữa "kiểm xem có chưa" và "ghi vào".
# 3) KHÔNG TỰ ÁP SỐ CỦA HÃNG VÀO SỔ. Nạp file chỉ dẫn tới `CHO_DUYET`. Người có quyền duyệt
#    mới làm số của hãng thành số của mình.
# 4) MỖI LOẠI LỆCH MỘT NHÃN RIÊNG. Gộp thành "lỗi" là làm mất đúng cái thông tin cần để xử:
#    đơn hãng không báo thì đi hỏi hãng, COD lệch thì đối chiếu phiếu thu, dòng trùng thì bỏ.
import hashlib
import json
import threading

import csdl
import don_hang
import nhap_file
import tai_chinh


# ============================================================================
# ÁNH XẠ CỘT THEO HÃNG — có phiên bản
# ============================================================================
# Khoá so khớp đi qua `nhap_file.chuan_ten_cot` (bỏ dấu, hạ chữ, bỏ ký tự lạ), nên
# "Mã vận đơn", "MA_VAN_DON", "ma van don" là MỘT. Dùng lại hàm của AG-04 thay vì viết bản
# thứ hai: hai bộ chuẩn hoá tên cột là hai bộ sẽ lệch nhau (§12.2).
#
# Phiên bản là CHUỖI do người đặt (ví dụ '2026-10'), không phải số tăng dần — khi hãng đổi
# mẫu, bảng kê cũ vẫn phải đọc lại được bằng đúng phiên bản của nó.
TRUONG_CHUAN = ("ma_van_don", "ma_don", "cod_hang_bao", "phi_hang_bao", "ky_thanh_toan",
                "trang_thai_hang", "ghi_chu")

ANH_XA_COT = {
    "vtp": {
        "2026-10": {
            "ma_van_don": ("ma van don", "ma_van_don", "ma vd", "so van don", "tracking",
                           "tracking_code", "ma buu gui"),
            "ma_don": ("ma don", "ma_don", "ma don hang", "ma khach", "ref", "reference"),
            "cod_hang_bao": ("tien cod", "cod", "so tien cod", "cod thuc thu", "tien thu ho"),
            "phi_hang_bao": ("cuoc chinh", "tong cuoc", "phi", "phi van chuyen", "cuoc phi"),
            "ky_thanh_toan": ("ky doi soat", "ky", "ky thanh toan", "dot"),
            "trang_thai_hang": ("trang thai", "tinh trang"),
            "ghi_chu": ("ghi chu", "note"),
        },
    },
    "jt": {
        "2026-10": {
            "ma_van_don": ("billcode", "bill code", "waybill", "waybill no", "ma van don",
                           "txlogisticid"),
            "ma_don": ("orderid", "order id", "customer order", "ma don"),
            "cod_hang_bao": ("codamount", "cod amount", "cod", "actual cod", "tien cod"),
            "phi_hang_bao": ("freight", "freight fee", "shipping fee", "tong phi", "phi"),
            "ky_thanh_toan": ("settlement period", "settle date", "ky", "period"),
            "trang_thai_hang": ("status", "trang thai"),
            "ghi_chu": ("remark", "ghi chu"),
        },
    },
}

PHIEN_BAN_MAC_DINH = {"vtp": "2026-10", "jt": "2026-10"}


def _bang_tra(anh_xa_hang):
    """{khoá chuẩn hoá của biến thể → trường chuẩn}."""
    ra = {}
    for truong, bien_the in anh_xa_hang.items():
        ra[nhap_file.chuan_ten_cot(truong)] = truong
        for bt in bien_the:
            ra[nhap_file.chuan_ten_cot(bt)] = truong
    return ra


def anh_xa_cua_hang(hang, phien_ban=None, tenant_id=None):
    """Ánh xạ cột đang dùng cho một hãng. Thứ tự ưu tiên: bản ghi đè trong CSDL (theo tenant,
    rồi toàn hệ) → bảng trong mã. Trả (bang_tra, phien_ban_da_dung).

    Không có ánh xạ thì NÉM LỖI. Cố đọc file của hãng lạ bằng mẫu của hãng khác là cách tạo
    ra số tiền sai mà không ai thấy — thà từ chối để người khai ánh xạ.
    """
    tai_chinh._dam_bao_bang()
    pb = phien_ban or PHIEN_BAN_MAC_DINH.get(hang)
    if pb:
        r = csdl.mot("SELECT anh_xa_json, phien_ban FROM ds_anh_xa_cot"
                     " WHERE hang=? AND phien_ban=? AND kich_hoat=1"
                     " AND (tenant_id=? OR tenant_id IS NULL)"
                     " ORDER BY tenant_id IS NULL LIMIT 1", (hang, pb, tenant_id))
        if r:
            thuong = json.loads(r["anh_xa_json"])
            # Bản ghi đè khai TRỰC TIẾP {tên cột trong file: trường chuẩn}
            bang = {}
            for ten_cot, truong in thuong.items():
                if truong not in TRUONG_CHUAN:
                    raise tai_chinh.LoiTaiChinh(
                        f"ánh xạ ghi đè trỏ vào trường lạ: {truong!r}", 500)
                bang[nhap_file.chuan_ten_cot(ten_cot)] = truong
            return bang, r["phien_ban"]
    trong_ma = ANH_XA_COT.get(hang, {})
    if pb and pb in trong_ma:
        return _bang_tra(trong_ma[pb]), pb
    if trong_ma:
        pb2 = sorted(trong_ma)[-1]
        return _bang_tra(trong_ma[pb2]), pb2
    raise tai_chinh.LoiTaiChinh(
        f"chưa có ánh xạ cột cho hãng {hang!r} (phiên bản {phien_ban!r}) — "
        f"khai vào doi_soat.ANH_XA_COT hoặc bảng ds_anh_xa_cot trước khi nạp", 400)


def dat_anh_xa(hang, phien_ban, anh_xa: dict, tenant_id=None):
    """Khai/ghi đè ánh xạ cột trong CSDL. `anh_xa` = {'Tên cột trong file': 'truong_chuan'}."""
    tai_chinh._dam_bao_bang()
    for truong in anh_xa.values():
        if truong not in TRUONG_CHUAN:
            raise tai_chinh.LoiTaiChinh(f"trường chuẩn lạ: {truong!r} (hợp lệ: {TRUONG_CHUAN})")
    csdl.ghi("INSERT INTO ds_anh_xa_cot (tenant_id, hang, phien_ban, anh_xa_json, tao_luc)"
             " VALUES (?,?,?,?,?) ON CONFLICT(tenant_id, hang, phien_ban) DO UPDATE SET"
             " anh_xa_json=excluded.anh_xa_json, kich_hoat=1",
             (tenant_id, hang, phien_ban, json.dumps(anh_xa, ensure_ascii=False), csdl.bay_gio()))
    return True


# ============================================================================
# TRẠNG THÁI ĐỢT + PHÂN LOẠI CHÊNH LỆCH
# ============================================================================
TRANG_THAI_DOT = ("MOI", "PARSING", "DOI_CHIEU", "CHO_DUYET", "DA_AP", "TU_CHOI", "FAILED")

CHUYEN_DOT = {
    "MOI":       {"PARSING", "FAILED"},
    "PARSING":   {"DOI_CHIEU", "FAILED"},
    "DOI_CHIEU": {"CHO_DUYET", "FAILED"},
    "CHO_DUYET": {"DA_AP", "TU_CHOI"},
    "DA_AP":     set(),
    "TU_CHOI":   set(),
    "FAILED":    set(),
}

# Bảy loại, mỗi loại một cách xử khác nhau. Gộp lại thành "lỗi" là làm mất thông tin cần
# để xử — đây là lý do bảng này tồn tại.
LOAI_CHENH_LECH = {
    "thieu_don_he":          "Hãng báo mà hệ không có đơn → kiểm xem đơn tạo ngoài hệ hay sai mã",
    "thieu_dong_hang":       "Hệ có đơn đã giao mà hãng không báo → đi đòi hãng",
    "dong_trung":            "Dòng trùng trong cùng kỳ → bỏ, không cộng tiền lần hai",
    "cod_lech":              "COD hãng báo khác COD hệ → đối chiếu phiếu thu",
    "phi_lech":              "Phí hãng tính khác phí hệ ghi → kiểm bảng giá và phụ phí",
    "dieu_chinh_bat_thuong": "Số lệch quá ngưỡng hoặc âm bất thường → người xem trước khi áp",
    "khong_khop_duoc":       "Dòng không có mã nào để khớp → trả hãng hỏi lại",
}

# Ngưỡng "bất thường": lệch tuyệt đối trên 500.000đ, hoặc trên 20% số của hệ.
# Tỷ lệ lưu bằng ĐIỂM CƠ BẢN (`INTEGER`, 1 = 0,01%) theo hợp đồng §16 — không lưu 0.2.
NGUONG_LECH_DONG = 500_000
NGUONG_LECH_BPS = 2000


def _bat_thuong(so_he, so_hang) -> bool:
    if so_he is None or so_hang is None:
        return False
    lech = abs(so_hang - so_he)
    if so_hang < 0:
        return True
    if lech >= NGUONG_LECH_DONG:
        return True
    # `//` và so sánh số nguyên — không chia ra số thực ở bất kỳ bước nào (§16).
    return so_he > 0 and lech * 10_000 >= so_he * NGUONG_LECH_BPS


def chuyen_dot(tenant_id, dot_id, den, loi=None):
    """Đổi trạng thái đợt bằng MỘT câu `UPDATE` có trạng thái cũ trong `WHERE`.

    Không đọc-rồi-ghi: hai lượt song song cùng muốn đổi thì đúng một lượt thấy rowcount=1.
    """
    tai_chinh._dam_bao_bang()
    if den not in TRANG_THAI_DOT:
        raise tai_chinh.LoiTaiChinh(f"trạng thái đợt lạ: {den!r}")
    cu = csdl.mot("SELECT trang_thai FROM ds_dot WHERE id=? AND tenant_id=?", (dot_id, tenant_id))
    if not cu:
        raise tai_chinh.LoiTaiChinh("không có đợt đối soát này trong doanh nghiệp", 404)
    if den not in CHUYEN_DOT.get(cu["trang_thai"], set()):
        raise tai_chinh.LoiTaiChinh(
            f"không được chuyển đợt {cu['trang_thai']} → {den}", 409)
    con = csdl.ghi("UPDATE ds_dot SET trang_thai=?, loi=? WHERE id=? AND tenant_id=? AND trang_thai=?",
                   (den, loi, dot_id, tenant_id, cu["trang_thai"]))
    if con.rowcount != 1:
        raise tai_chinh.LoiTaiChinh("đợt vừa được một lượt khác đổi trạng thái", 409)
    return den


# ============================================================================
# NẠP FILE BẢNG KÊ
# ============================================================================
def _van_tay(*phan):
    return hashlib.sha256("|".join("" if p is None else str(p) for p in phan)
                          .encode("utf-8")).hexdigest()


def _so_tien_o(gt, ten):
    """Đọc một ô tiền từ bảng kê hãng. Trả `None` nếu ô trống (khác 0: 0 là hãng báo 'không
    thu được đồng nào', trống là 'hãng không nói gì' — hai việc khác nhau, cấm gộp)."""
    s = "" if gt is None else str(gt).strip()
    if not s:
        return None
    # Bảng kê hay có "1.234.567" hoặc "1,234,567" — bỏ dấu phân cách NGHÌN, giữ phần thập
    # phân cho `so_tien()` chặn. Không tự cắt cụt phần thập phân ở đây.
    s = s.replace(" ", "").replace("đ", "").replace("VND", "").replace("vnd", "")
    if s.count(".") > 1 or (s.count(",") > 1):
        s = s.replace(".", "").replace(",", "")
    elif s.count(".") == 1 and len(s.split(".")[1]) == 3:
        s = s.replace(".", "")
    elif s.count(",") == 1 and len(s.split(",")[1]) == 3:
        s = s.replace(",", "")
    return tai_chinh.so_tien(s, ten)


def nap_bang_ke(tenant_id, user_id, hang, ten_file, du_lieu: bytes,
                ky_thanh_toan="", carrier_account_id=None, phien_ban=None, kiem_quyen=True):
    """Nạp bảng kê của hãng thành một ĐỢT ĐỐI SOÁT ở trạng thái `DOI_CHIEU`.

    KHÔNG áp gì vào sổ tiền ở bước này. Trả về thống kê nạp + id đợt.
    Dòng trùng (đã có trong kỳ này) được ghi nhận riêng là `dong_trung`, không nhân đôi số.
    """
    tai_chinh._dam_bao_bang()
    if kiem_quyen:
        tai_chinh._can_quyen_tc(tenant_id, user_id, "ghi")
    duoi = (ten_file or "").lower().rsplit(".", 1)[-1]
    if duoi not in ("csv", "xlsx"):
        raise tai_chinh.LoiTaiChinh(
            f"chỉ nạp .csv và .xlsx; nhận {duoi!r}. XLS/PDF chưa đọc được (xem giới hạn)", 400)
    nhap_file._kiem_dung_luong(du_lieu)
    bang, pb = anh_xa_cua_hang(hang, phien_ban, tenant_id)

    if duoi == "csv":
        dong = nhap_file.doc_csv(du_lieu.decode("utf-8-sig", errors="replace"))
    else:
        dong = nhap_file.doc_xlsx(du_lieu)
    if not dong:
        raise tai_chinh.LoiTaiChinh("bảng kê rỗng", 400)

    hang_dau = dong[0]
    anh_xa_cot_so = {}
    for i, ten in enumerate(hang_dau):
        truong = bang.get(nhap_file.chuan_ten_cot(ten))
        if truong and truong not in anh_xa_cot_so.values():
            anh_xa_cot_so[i] = truong
    if "ma_van_don" not in anh_xa_cot_so.values() and "ma_don" not in anh_xa_cot_so.values():
        raise tai_chinh.LoiTaiChinh(
            f"bảng kê không có cột mã vận đơn hay mã đơn nào nhận ra được "
            f"(ánh xạ {hang}/{pb}). Tiêu đề đọc được: {hang_dau[:12]}", 400)

    dot_id = csdl.ghi(
        "INSERT INTO ds_dot (tenant_id, hang, carrier_account_id, ten_file, loai_file,"
        " van_tay_file, anh_xa_phien_ban, ky_thanh_toan, trang_thai, so_dong, tao_boi, tao_luc)"
        " VALUES (?,?,?,?,?,?,?,?, 'MOI', 0, ?, ?)",
        (tenant_id, hang, carrier_account_id, ten_file, duoi,
         hashlib.sha256(du_lieu).hexdigest(), pb, ky_thanh_toan, user_id, csdl.bay_gio())).lastrowid
    chuyen_dot(tenant_id, dot_id, "PARSING")

    so_nap = so_trung = 0
    loi_dong = []
    for stt, r in enumerate(dong[1:], start=1):
        o = {}
        for i, truong in anh_xa_cot_so.items():
            o[truong] = r[i] if i < len(r) else ""
        if not any(str(v).strip() for v in o.values()):
            continue
        try:
            cod = _so_tien_o(o.get("cod_hang_bao"), f"COD dòng {stt}")
            phi = _so_tien_o(o.get("phi_hang_bao"), f"phí dòng {stt}")
        except tai_chinh.LoiTaiChinh as e:
            loi_dong.append(f"dòng {stt}: {e}")
            cod = phi = None
        ky = (str(o.get("ky_thanh_toan") or "").strip() or ky_thanh_toan or "")
        mvd = str(o.get("ma_van_don") or "").strip()
        mdon = str(o.get("ma_don") or "").strip()
        vt = _van_tay(hang, ky, mvd, mdon, cod, phi)
        try:
            csdl.ghi("INSERT INTO ds_dong (dot_id, tenant_id, hang, stt, ma_van_don, ma_don,"
                     " cod_hang_bao, phi_hang_bao, ky_thanh_toan, tho_json, van_tay_dong)"
                     " VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                     (dot_id, tenant_id, hang, stt, mvd or None, mdon or None, cod, phi, ky,
                      json.dumps(o, ensure_ascii=False), vt))
            so_nap += 1
        except Exception as e:
            if "UNIQUE" not in str(e).upper():
                raise
            # Ràng buộc CSDL chặn — ghi nhận thành `dong_trung`, KHÔNG cộng tiền lần hai.
            so_trung += 1
            csdl.ghi("INSERT INTO ds_chenh_lech (dot_id, tenant_id, loai, chi_tiet)"
                     " VALUES (?,?, 'dong_trung', ?)",
                     (dot_id, tenant_id,
                      f"dòng {stt} (vận đơn {mvd or mdon or '?'}, kỳ {ky or '-'}) đã có trong kỳ "
                      f"này — ràng buộc UNIQUE của CSDL chặn, không cộng tiền lần hai"))
    csdl.ghi("UPDATE ds_dot SET so_dong=? WHERE id=? AND tenant_id=?",
             (so_nap, dot_id, tenant_id))
    chuyen_dot(tenant_id, dot_id, "DOI_CHIEU", loi="; ".join(loi_dong[:20]) or None)
    tai_chinh.ghi_nhat_ky(tenant_id, "nap_bang_ke", f"ds_dot:{dot_id}",
                          f"hãng {hang} file {ten_file}: nạp {so_nap}, trùng {so_trung}", user_id)
    return {"dot_id": dot_id, "so_nap": so_nap, "so_trung": so_trung,
            "anh_xa_phien_ban": pb, "cot_nhan_ra": sorted(set(anh_xa_cot_so.values())),
            "loi_dong": loi_dong}


# ============================================================================
# ĐỐI CHIẾU
# ============================================================================
def _tim_don(tenant_id, mvd, mdon):
    if mvd:
        d = csdl.mot("SELECT * FROM don_hang WHERE tenant_id=? AND ma_van_don=?", (tenant_id, mvd))
        if d:
            return d
    if mdon:
        d = csdl.mot("SELECT * FROM don_hang WHERE tenant_id=? AND ma_don=?", (tenant_id, mdon))
        if d:
            return d
    return None


def _phi_he_cua_don(tenant_id, don):
    """Phí hệ đang coi là đúng: ưu tiên tổng báo giá đã ghi vào `tc_phi`, rơi về
    `don_hang.phi_van_chuyen`. Trả `None` nếu hệ chưa có số nào — khi đó KHÔNG kết luận lệch."""
    r = csdl.mot("SELECT COALESCE(SUM(so_tien_dong),0) t, COUNT(*) c FROM tc_phi"
                 " WHERE tenant_id=? AND don_id=? AND loai='bao_gia'", (tenant_id, don["id"]))
    if r and r["c"]:
        return r["t"]
    return don["phi_van_chuyen"]


def doi_chieu(tenant_id, dot_id) -> dict:
    """Đối chiếu từng dòng bảng kê với hệ, phân loại chênh lệch, rồi đưa đợt sang `CHO_DUYET`.

    PHẠM VI phép đo này (§12.1 luật 3 và luật "0"):
      - Đối chiếu theo: hãng · tài khoản hãng (nếu đợt khai) · mã vận đơn · mã đơn · COD ·
        phí · kỳ thanh toán.
      - "Hệ có mà hãng không báo" chỉ quét các đơn CÙNG hãng, ĐÃ có mã vận đơn, và COD đang ở
        `COD_EXPECTED`/`COD_COLLECTED`. Đơn chưa có mã vận đơn hoặc của hãng khác NẰM NGOÀI
        phạm vi — không được kết luận gì về chúng.
      - Phí chỉ so khi hệ CÓ số phí. Đơn chưa biết phí thì không tính là "khớp" cũng không
        tính là "lệch".
    """
    tai_chinh._dam_bao_bang()
    dot = csdl.mot("SELECT * FROM ds_dot WHERE id=? AND tenant_id=?", (dot_id, tenant_id))
    if not dot:
        raise tai_chinh.LoiTaiChinh("không có đợt đối soát này trong doanh nghiệp", 404)
    if dot["trang_thai"] != "DOI_CHIEU":
        raise tai_chinh.LoiTaiChinh(
            f"đợt đang ở {dot['trang_thai']}, chỉ đối chiếu được khi ở DOI_CHIEU", 409)

    dem = {k: 0 for k in LOAI_CHENH_LECH}
    dem["dong_trung"] = csdl.mot("SELECT COUNT(*) c FROM ds_chenh_lech"
                                 " WHERE dot_id=? AND tenant_id=? AND loai='dong_trung'",
                                 (dot_id, tenant_id))["c"]
    so_khop = 0
    da_thay_don = set()

    def _cl(loai, dong_id=None, don_id=None, so_he=None, so_hang=None, chi_tiet=""):
        csdl.ghi("INSERT INTO ds_chenh_lech (dot_id, tenant_id, dong_id, don_id, loai, so_he,"
                 " so_hang, lech_dong, chi_tiet) VALUES (?,?,?,?,?,?,?,?,?)",
                 (dot_id, tenant_id, dong_id, don_id, loai, so_he, so_hang,
                  None if (so_he is None or so_hang is None) else so_hang - so_he, chi_tiet))
        dem[loai] += 1

    for d in csdl.nhieu("SELECT * FROM ds_dong WHERE dot_id=? AND tenant_id=? ORDER BY stt",
                        (dot_id, tenant_id)):
        mvd, mdon = d["ma_van_don"], d["ma_don"]
        if not mvd and not mdon:
            csdl.ghi("UPDATE ds_dong SET ket_qua='KHONG_KHOP' WHERE id=? AND tenant_id=?",
                     (d["id"], tenant_id))
            _cl("khong_khop_duoc", d["id"], chi_tiet=f"dòng {d['stt']} không có mã nào để khớp")
            continue
        don = _tim_don(tenant_id, mvd, mdon)
        if not don:
            csdl.ghi("UPDATE ds_dong SET ket_qua='THIEU_DON' WHERE id=? AND tenant_id=?",
                     (d["id"], tenant_id))
            _cl("thieu_don_he", d["id"], so_hang=d["cod_hang_bao"],
                chi_tiet=f"hãng báo vận đơn {mvd or '-'} / đơn {mdon or '-'} mà hệ không có")
            continue
        da_thay_don.add(don["id"])
        csdl.ghi("UPDATE ds_dong SET don_id=? WHERE id=? AND tenant_id=?",
                 (don["id"], d["id"], tenant_id))
        lech = False

        if d["cod_hang_bao"] is not None:
            cod_he = don["cod"]
            if d["cod_hang_bao"] != cod_he:
                lech = True
                loai = "dieu_chinh_bat_thuong" if _bat_thuong(cod_he, d["cod_hang_bao"]) \
                    else "cod_lech"
                _cl(loai, d["id"], don["id"], cod_he, d["cod_hang_bao"],
                    f"COD: hệ {cod_he} · hãng {d['cod_hang_bao']}")
        if d["phi_hang_bao"] is not None:
            phi_he = _phi_he_cua_don(tenant_id, don)
            if phi_he is not None and d["phi_hang_bao"] != phi_he:
                lech = True
                loai = "dieu_chinh_bat_thuong" if _bat_thuong(phi_he, d["phi_hang_bao"]) \
                    else "phi_lech"
                _cl(loai, d["id"], don["id"], phi_he, d["phi_hang_bao"],
                    f"phí: hệ {phi_he} · hãng {d['phi_hang_bao']}")
        if not lech:
            csdl.ghi("UPDATE ds_dong SET ket_qua='KHOP' WHERE id=? AND tenant_id=?",
                     (d["id"], tenant_id))
            so_khop += 1
        else:
            csdl.ghi("UPDATE ds_dong SET ket_qua='LECH' WHERE id=? AND tenant_id=?",
                     (d["id"], tenant_id))

    # Hệ có mà hãng không báo — xem phạm vi ở docstring.
    sql_thieu = (
        "SELECT d.id, d.ma_don, d.ma_van_don, d.cod FROM don_hang d"
        " JOIN carrier_accounts ca ON ca.id = d.carrier_account_id"
        " LEFT JOIN tc_cod c ON c.don_id = d.id AND c.tenant_id = d.tenant_id"
        " WHERE d.tenant_id=? AND ca.hang=? AND d.ma_van_don IS NOT NULL"
        " AND COALESCE(c.trang_thai,'COD_EXPECTED') IN ('COD_EXPECTED','COD_COLLECTED')")
    ts = [tenant_id, dot["hang"]]
    if dot["carrier_account_id"]:
        sql_thieu += " AND d.carrier_account_id=?"
        ts.append(dot["carrier_account_id"])
    for don in csdl.nhieu(sql_thieu, ts):
        if don["id"] in da_thay_don:
            continue
        _cl("thieu_dong_hang", None, don["id"], don["cod"], None,
            f"hệ có đơn {don['ma_don']} (vận đơn {don['ma_van_don']}, COD {don['cod']}) "
            f"mà bảng kê của hãng {dot['hang']} không báo")

    chuyen_dot(tenant_id, dot_id, "CHO_DUYET")
    tong = sum(dem.values())
    kq = {"dot_id": dot_id, "so_khop": so_khop, "tong_chenh_lech": tong, "theo_loai": dem,
          "trang_thai": "CHO_DUYET"}
    tai_chinh.ghi_nhat_ky(tenant_id, "doi_chieu", f"ds_dot:{dot_id}",
                          f"khớp {so_khop}, chênh lệch {tong}: {dem}")
    return kq


def chenh_lech_cua_dot(tenant_id, dot_id, loai=None):
    tai_chinh._dam_bao_bang()
    sql = ("SELECT cl.*, dg.stt, dg.ma_van_don, dg.ma_don FROM ds_chenh_lech cl"
           " LEFT JOIN ds_dong dg ON dg.id = cl.dong_id"
           " WHERE cl.dot_id=? AND cl.tenant_id=?")
    ts = [dot_id, tenant_id]
    if loai:
        if loai not in LOAI_CHENH_LECH:
            raise tai_chinh.LoiTaiChinh(f"loại chênh lệch lạ: {loai!r}")
        sql += " AND cl.loai=?"; ts.append(loai)
    sql += " ORDER BY cl.loai, cl.id"
    return [dict(r) for r in csdl.nhieu(sql, ts)]


def xu_ly_chenh_lech(tenant_id, user_id, cl_id, xu_ly, ghi_chu="", kiem_quyen=True):
    """Đánh dấu một chênh lệch đã xử (`da_xu`) hoặc bỏ qua (`bo_qua`), có người và ghi chú.

    `bo_qua` BẮT BUỘC có ghi chú: rủi ro cố ý bỏ qua mà không ghi lý do là rủi ro bị bỏ quên.
    """
    tai_chinh._dam_bao_bang()
    if kiem_quyen:
        tai_chinh._can_quyen_tc(tenant_id, user_id, "duyet")
    if xu_ly not in ("da_xu", "bo_qua"):
        raise tai_chinh.LoiTaiChinh("xử lý phải là 'da_xu' hoặc 'bo_qua'")
    if xu_ly == "bo_qua" and not str(ghi_chu or "").strip():
        raise tai_chinh.LoiTaiChinh("bỏ qua một chênh lệch PHẢI ghi lý do")
    con = csdl.ghi("UPDATE ds_chenh_lech SET xu_ly=?, xu_ly_boi=?, xu_ly_luc=?, ghi_chu_xu_ly=?"
                   " WHERE id=? AND tenant_id=? AND xu_ly='mo'",
                   (xu_ly, user_id, csdl.bay_gio(), ghi_chu, cl_id, tenant_id))
    if con.rowcount != 1:
        raise tai_chinh.LoiTaiChinh("chênh lệch không còn ở trạng thái mở", 409)
    tai_chinh.ghi_nhat_ky(tenant_id, "xu_ly_chenh_lech", f"ds_chenh_lech:{cl_id}",
                          f"{xu_ly}: {ghi_chu}", user_id)
    return True


# ============================================================================
# PHÊ DUYỆT — chỗ DUY NHẤT số của hãng vào sổ của mình
# ============================================================================
def duyet_dot(tenant_id, user_id, dot_id, kiem_quyen=True) -> dict:
    """Phê duyệt đợt và áp vào sổ. Chỉ áp các dòng `KHOP`.

    Vì sao chỉ `KHOP`: dòng lệch là chỗ hệ và hãng KHÔNG đồng ý với nhau. Áp tự động là chọn
    tin hãng mà không ai quyết định — đúng cái hợp đồng §18 cấm. Dòng lệch ở lại `ds_chenh_lech`
    cho người xử; xử xong muốn áp thì ghi `tai_chinh.dieu_chinh()` có lý do và người.

    CHIẾM đợt bằng MỘT câu `UPDATE ... WHERE trang_thai='CHO_DUYET'` rồi xét `rowcount` TRƯỚC
    khi áp bất cứ gì. Hai lượt duyệt song song: lượt thua thấy rowcount=0 và dừng, nên không
    có đường nào cộng tiền hai lần.
    """
    tai_chinh._dam_bao_bang()
    if kiem_quyen:
        tai_chinh._can_quyen_tc(tenant_id, user_id, "duyet")
    dot = csdl.mot("SELECT * FROM ds_dot WHERE id=? AND tenant_id=?", (dot_id, tenant_id))
    if not dot:
        raise tai_chinh.LoiTaiChinh("không có đợt đối soát này trong doanh nghiệp", 404)

    with csdl.khoa_ghi:
        con = csdl.ghi("UPDATE ds_dot SET trang_thai='DA_AP', duyet_boi=?, duyet_luc=?"
                       " WHERE id=? AND tenant_id=? AND trang_thai='CHO_DUYET'",
                       (user_id, csdl.bay_gio(), dot_id, tenant_id))
        if con.rowcount != 1:
            raise tai_chinh.LoiTaiChinh(
                f"đợt đối soát #{dot_id} không còn ở CHO_DUYET (đang ở {dot['trang_thai']}) "
                f"— một lượt duyệt khác đã áp, không áp lần hai", 409)

    da_ap = bo_qua = 0
    loi = []
    for d in csdl.nhieu("SELECT * FROM ds_dong WHERE dot_id=? AND tenant_id=? AND ket_qua='KHOP'"
                        " ORDER BY stt", (dot_id, tenant_id)):
        if not d["don_id"]:
            bo_qua += 1
            continue
        can_cu = (f"đợt đối soát #{dot_id} ({dot['ten_file']}), dòng {d['stt']}, "
                  f"kỳ {d['ky_thanh_toan'] or '-'}, hãng {dot['hang']}")
        try:
            c = tai_chinh.cod_cua_don(tenant_id, d["don_id"])
            if c is None:
                c = tai_chinh.mo_so_cod(tenant_id, d["don_id"], tao_boi=user_id)
            if d["cod_hang_bao"] is not None:
                if c["trang_thai"] == "COD_EXPECTED":
                    tai_chinh.chuyen_cod(tenant_id, d["don_id"], "COD_COLLECTED", "hang", can_cu,
                                         nguoi=user_id, so_tien_hang_bao=d["cod_hang_bao"],
                                         batch_id=dot_id)
                    c = tai_chinh.cod_cua_don(tenant_id, d["don_id"])
                if c["trang_thai"] == "COD_COLLECTED":
                    tai_chinh.chuyen_cod(tenant_id, d["don_id"], "COD_RECONCILED", "nguoi",
                                         can_cu + " — người duyệt chốt số", nguoi=user_id,
                                         so_tien_hang_bao=d["cod_hang_bao"], batch_id=dot_id)
            if d["phi_hang_bao"] is not None:
                tai_chinh.ghi_phi(tenant_id, d["don_id"], "thuc_te_hang", d["phi_hang_bao"],
                                  "hang", can_cu, tao_boi=user_id, batch_id=dot_id)
            da_ap += 1
        except don_hang.LoiNghiepVu as e:
            # Một dòng hỏng KHÔNG được làm cả đợt hỏng im lặng: ghi thành chênh lệch mở.
            bo_qua += 1
            loi.append(f"dòng {d['stt']}: {e}")
            csdl.ghi("INSERT INTO ds_chenh_lech (dot_id, tenant_id, dong_id, don_id, loai,"
                     " chi_tiet) VALUES (?,?,?,?, 'khong_khop_duoc', ?)",
                     (dot_id, tenant_id, d["id"], d["don_id"], f"áp không được: {e}"))
    kq = {"dot_id": dot_id, "da_ap": da_ap, "bo_qua": bo_qua, "loi": loi,
          "trang_thai": "DA_AP"}
    tai_chinh.ghi_nhat_ky(tenant_id, "duyet_dot", f"ds_dot:{dot_id}",
                          f"áp {da_ap} dòng, bỏ qua {bo_qua}", user_id)
    return kq


def tu_choi_dot(tenant_id, user_id, dot_id, ly_do, kiem_quyen=True):
    """Từ chối một đợt (bảng kê sai, nạp nhầm hãng…). Không áp gì vào sổ."""
    tai_chinh._dam_bao_bang()
    if kiem_quyen:
        tai_chinh._can_quyen_tc(tenant_id, user_id, "duyet")
    if not str(ly_do or "").strip():
        raise tai_chinh.LoiTaiChinh("từ chối đợt đối soát phải có lý do")
    con = csdl.ghi("UPDATE ds_dot SET trang_thai='TU_CHOI', loi=?, duyet_boi=?, duyet_luc=?"
                   " WHERE id=? AND tenant_id=? AND trang_thai='CHO_DUYET'",
                   (ly_do, user_id, csdl.bay_gio(), dot_id, tenant_id))
    if con.rowcount != 1:
        raise tai_chinh.LoiTaiChinh("đợt không còn ở CHO_DUYET", 409)
    tai_chinh.ghi_nhat_ky(tenant_id, "tu_choi_dot", f"ds_dot:{dot_id}", ly_do, user_id)
    return True


def danh_sach_dot(tenant_id, gioi_han=100):
    tai_chinh._dam_bao_bang()
    return [dict(r) for r in csdl.nhieu(
        "SELECT d.*, (SELECT COUNT(*) FROM ds_chenh_lech cl WHERE cl.dot_id=d.id) so_chenh_lech"
        " FROM ds_dot d WHERE d.tenant_id=? ORDER BY d.id DESC LIMIT ?",
        (tenant_id, int(gioi_han)))]


def bang_ke_cua_dot(tenant_id, dot_id, gioi_han=1000):
    tai_chinh._dam_bao_bang()
    if not csdl.mot("SELECT 1 x FROM ds_dot WHERE id=? AND tenant_id=?", (dot_id, tenant_id)):
        raise tai_chinh.LoiTaiChinh("không có đợt đối soát này trong doanh nghiệp", 404)
    return [dict(r) for r in csdl.nhieu(
        "SELECT * FROM ds_dong WHERE dot_id=? AND tenant_id=? ORDER BY stt LIMIT ?",
        (dot_id, tenant_id, int(gioi_han)))]


def xuat_csv_chenh_lech(tenant_id, dot_id):
    """Xuất chênh lệch ra CSV. Mọi ô đi qua `nhap_file.lam_sach_o_xuat` (chống công thức CSV)
    — dùng lại hàm của AG-04, không viết bản làm sạch thứ hai."""
    ds = chenh_lech_cua_dot(tenant_id, dot_id)
    cot = ("id", "loai", "stt", "ma_van_don", "ma_don", "don_id", "so_he", "so_hang",
           "lech_dong", "xu_ly", "chi_tiet")

    def _o(v):
        return '"' + nhap_file.lam_sach_o_xuat(v).replace('"', '""') + '"'

    ra = [",".join(_o(c) for c in cot)]
    for r in ds:
        ra.append(",".join(_o(r.get(c, "")) for c in cot))
    return "\r\n".join(ra) + "\r\n"
