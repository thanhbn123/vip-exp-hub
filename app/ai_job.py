# G10 — AIJobService: tầng CÔNG VIỆC AI, dựng BÊN TRÊN `ai_gateway.py` (không sửa file đó).
# AG-04 sở hữu file này (SHARED_CONTRACTS §22).
#
# ======================================================================================
# CHƯA ĐƯỢC CẤP QUYỀN NỐI AI THẬT — V-G10-01.
# Không file nào trong G10 gọi OpenAI / Claude / DeepSeek / VIP AI Brain hay bất kỳ API AI
# nào. `ai_gateway.MOCK` là `True` và không ai được đặt `False` đợt này. `VIPAIBrainConnector`
# dưới đây là GIAO DIỆN RỖNG CÓ CHỦ Ý: gọi vào là ném `ChuaCapQuyen`, không phải "chưa làm".
# ======================================================================================
#
# Bất biến của tầng này, theo thứ tự quan trọng:
#   1. `tenant_id` CHỈ đến từ phiên đã xác thực (server truyền vào). Mọi `tenant_id`/`user_id`
#      lẫn trong `vao` bị GỠ và ghi nhận — không bao giờ được dùng.
#   2. KẾT QUẢ AI LÀ DỮ LIỆU. Module này KHÔNG có đường nào gọi `don_hang.tao_don`,
#      `don_hang.gui_don`, `don_hang.duyet_don` hay adapter hãng. Nó chỉ gọi
#      `don_hang.kiem_don(..., d=...)` — phép kiểm KHÔNG ghi CSDL — và `vai_tro_trong_tenant`
#      để tra quyền. Có ca thử gài bẫy vào `tao_don`/`gui_don` chứng minh không ai gọi tới.
#   3. Đầu ra qua `ai_validator.kiem_ra` TRƯỚC khi lưu. Lệch schema ⇒ `loi`, không phải `xong`.
#   4. Chỉ trường trong danh sách trắng `TRUONG_GUI` đi vào prompt; số điện thoại bị che, COD
#      quy về KHOẢNG. Có ca thử quét bí mật trong prompt ở ba dạng (thô/hex/base64).
#   5. Việc nào cần người duyệt thì KHÔNG tự áp: nó dừng ở `cho_duyet`.
import json
import threading
import time
import uuid

import ai_gateway
import ai_validator
import billing
import csdl
import don_hang
import quyen

PHIEN_BAN_HOP_DONG = ai_validator.PHIEN_BAN_HOP_DONG
TRANG_THAI = ("moi", "dang_chay", "xong", "loi", "cho_duyet", "tu_choi")
QUYEN_DUNG = "tenant.ai.dung"
QUYEN_DUYET = "tenant.don.duyet"      # duyệt gợi ý AI đòi đúng quyền duyệt nghiệp vụ
GIAY_TIMEOUT = 20


# --------------------------------------------------------------------------------------
# SCHEMA — hằng DDL_G10. AG-04 không được sửa `csdl.py`/`migrate.py` (§22), nên khối này là
# MỘT NGUỒN DUY NHẤT cho ba chỗ: tài liệu `docs/G10_FINAL_REPORT.md`, bộ thử
# `app/thu/thu_ai_job.py`, và đề xuất gửi AG-00 làm migration v8. Viết tay ba bản là ba bản
# sẽ lệch nhau (CLAUDE.md §14.6).
#
# `bao_dam_bang()` chạy đúng khối này nên mã CHẠY ĐƯỢC trước khi AG-00 làm migration — và
# chạy lại nhiều lần vô hại (toàn bộ là IF NOT EXISTS, không có ALTER).
# --------------------------------------------------------------------------------------
DDL_G10 = """
CREATE TABLE IF NOT EXISTS ai_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  user_id INTEGER NOT NULL REFERENCES users(id),
  loai TEXT NOT NULL,
  -- moi · dang_chay · xong · loi · cho_duyet · tu_choi  (SHARED_CONTRACTS §21)
  trang_thai TEXT NOT NULL DEFAULT 'moi',
  vao_json TEXT NOT NULL,
  ra_json TEXT,
  nha_cung_cap TEXT NOT NULL,
  phien_ban_hop_dong TEXT NOT NULL,
  do_tin_cay INTEGER,                              -- 0..100, số NGUYÊN (§16: cấm float)
  can_nguoi_duyet INTEGER NOT NULL DEFAULT 1,
  duyet_boi INTEGER REFERENCES users(id),
  duyet_luc TEXT,
  idem_key TEXT NOT NULL,
  tao_luc TEXT NOT NULL,
  xong_luc TEXT,
  -- các cột dưới đây THÊM so với §21 (không đổi cột nào của §21):
  loi TEXT,                                        -- lý do khi trang_thai='loi'
  mock INTEGER NOT NULL DEFAULT 1,                 -- kết quả có phải mô phỏng không
  dau_hieu_tiem TEXT,                              -- chỉ số mẫu tiêm khớp được, dạng JSON
  ms_chay INTEGER,                                 -- thời gian chạy, mili-giây
  batch_id INTEGER REFERENCES import_batch(id),    -- lô import nguồn (nếu có)
  dong_id INTEGER REFERENCES import_dong(id),      -- dòng import nguồn (nếu có)
  UNIQUE (tenant_id, idem_key)
);
CREATE INDEX IF NOT EXISTS ix_aijob_tenant ON ai_job(tenant_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_aijob_tt ON ai_job(tenant_id, trang_thai);
CREATE INDEX IF NOT EXISTS ix_aijob_batch ON ai_job(batch_id);
CREATE TABLE IF NOT EXISTS ai_su_kien (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  job_id INTEGER REFERENCES ai_job(id),
  user_id INTEGER REFERENCES users(id),
  loai_su_kien TEXT NOT NULL,   -- tao · goi_nha_cung_cap · xong · loi · timeout
                                -- · cho_duyet · duyet · tu_choi · chan_bi_mat · chan_lenh
  so_luot_ai INTEGER NOT NULL DEFAULT 0,           -- lượt tính phí của sự kiện này
  chi_tiet TEXT NOT NULL DEFAULT '',
  luc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_aisk_tenant ON ai_su_kien(tenant_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_aisk_job ON ai_su_kien(job_id);
"""

_da_bao_dam = False
_khoa_bao_dam = threading.Lock()


def bao_dam_bang():
    """Tạo bảng của G10 nếu CSDL chưa có. Idempotent, chỉ CREATE ... IF NOT EXISTS.

    Vì sao cần: AG-00 mới được viết migration (§22), nhưng mã và bộ thử của G10 phải chạy
    được NGAY. `don_hang.py` đã dùng đúng nếp này (dò bảng bằng `co_bang`, chịu được CSDL
    chưa migrate). Khi AG-00 nhận `DDL_G10` vào migration v8 thì hàm này thành vô hại.
    """
    global _da_bao_dam
    if _da_bao_dam:
        return
    with _khoa_bao_dam:
        if _da_bao_dam:
            return
        with csdl.khoa_ghi:
            kn = csdl.mo()
            kn.executescript(DDL_G10)
        _da_bao_dam = True


class ChuaCapQuyen(Exception):
    """Việc này cần một quyền CHƯA được cấp (SHARED_CONTRACTS §25). Khác lỗi nghiệp vụ:
    không phải người dùng làm sai, mà hệ CỐ Ý chưa mở đường."""


# --------------------------------------------------------------------------------------
# TỐI GIẢN DỮ LIỆU — trường nào ĐƯỢC gửi cho nhà cung cấp, trường nào KHÔNG
# --------------------------------------------------------------------------------------
# Danh sách TRẮNG theo từng loại việc. Ngoại lệ chính đáng của §12.2 (y như chốt 4 của §18.2):
# quên khai một trường ⇒ trường đó KHÔNG được gửi ⇒ kết quả AI kém hơn, nhưng dữ liệu khách
# không rò. Dùng danh sách đen mà quên chặn một trường ⇒ số điện thoại thật rời khỏi hệ ⇒
# hỏng thật, không thu lại được. Bỏ sót ở đây phải là AN TOÀN, nên trắng mới đúng.
TRUONG_GUI = {
    # Trích đơn từ file: cần cả dòng để đọc được, nhưng SĐT bị che và COD về khoảng.
    "trich_don_tu_file": ("nguoi_nhan_ten", "nguoi_nhan_dia_chi", "hang_hoa", "so_luong",
                          "khoi_luong_gram", "ghi_chu", "sdt_che", "cod_khoang"),
    # Chuẩn hoá một trường: chỉ cần TÊN TRƯỜNG + GIÁ TRỊ của đúng trường đó. Không gửi gì khác.
    "chuan_hoa_truong": ("truong", "gia_tri"),
    # Gợi ý hãng: quyết định theo cân nặng + vùng giao, KHÔNG cần biết ai nhận.
    "goi_y_hang": ("khoi_luong_gram", "tinh", "cod_khoang"),
    # Bất thường: cần ĐỘ LỚN của COD, không cần số tiền chính xác.
    "phat_hien_bat_thuong": ("khoi_luong_gram", "cod_khoang", "so_luong", "gia_tri_khoang"),
    # Giải thích lỗi: chỉ gửi DANH SÁCH LỖI, không gửi dữ liệu khách.
    "giai_thich_loi_kiem": ("loi", "canh_bao"),
    # Tóm tắt lô: chỉ gửi SỐ ĐẾM, không gửi một dòng dữ liệu nào.
    "tom_tat_lo_import": ("ten_file", "so_dong", "so_valid", "so_invalid", "so_needs_review",
                          "ly_do_pho_bien"),
}

# Ghi RA ĐÂY để không ai phải suy: ba thứ này KHÔNG BAO GIỜ đi vào prompt, ở mọi loại việc.
TRUONG_KHONG_GUI = {
    "nguoi_nhan_sdt": "số điện thoại đầy đủ là dữ liệu cá nhân nhận dạng trực tiếp; AI không "
                      "cần nó để chuẩn hoá địa chỉ hay chọn hãng. Chỉ gửi dạng CHE "
                      "`0901***567` (3 số đầu + 3 số cuối) để người duyệt đối chiếu được dòng.",
    "cod": "số tiền thu hộ chính xác là dữ liệu tài chính của khách; phát hiện bất thường chỉ "
           "cần ĐỘ LỚN, nên gửi KHOẢNG ('>5tr') thay vì con số.",
    "gia_tri_khai": "cùng lý do với `cod` — gửi khoảng, không gửi số.",
    "nguoi_gui_*": "thông tin người gửi là của chính doanh nghiệp, AI không cần để làm sáu "
                   "việc đã khai.",
    "credentials hãng / khoá / token / mật khẩu / hash": "cấm tuyệt đối (SHARED_CONTRACTS §14, "
                                                        "§21). Có phép quét canh ở "
                                                        "`ai_validator.quet_bi_mat`.",
    "tenant_id / user_id / token phiên": "định danh nội bộ không giúp gì cho sáu việc trên, và "
                                         "gửi ra ngoài là mở đường tương quan giữa các tenant.",
}
# Địa chỉ ĐẦY ĐỦ thì CÓ gửi, cho hai việc cần nó (`trich_don_tu_file`, `chuan_hoa_truong`) —
# ghi rõ vì đây là lựa chọn có đánh đổi: chuẩn hoá địa chỉ mà không có địa chỉ thì vô nghĩa.
# Cho `goi_y_hang` thì chỉ gửi TỈNH, vì chọn hãng không cần số nhà.
GHI_CHU_DIA_CHI = ("Địa chỉ đầy đủ CÓ gửi cho `trich_don_tu_file` và `chuan_hoa_truong` — hai "
                   "việc này không làm được mà thiếu nó. `goi_y_hang` chỉ nhận TỈNH. Các việc "
                   "còn lại không nhận địa chỉ.")


def che_sdt(s):
    """0901234567 → 090***567. Giữ đủ để người duyệt nhận ra dòng, không đủ để gọi điện."""
    so = "".join(c for c in str(s or "") if c.isdigit())
    if len(so) < 7:
        return "***" if so else ""
    return so[:3] + "*" * max(3, len(so) - 6) + so[-3:]


# Mốc khoảng tiền, đơn vị ĐỒNG, số NGUYÊN (§16: cấm float cho tiền).
_MOC_TIEN = ((0, "0"), (500_000, "<=500k"), (2_000_000, "<=2tr"), (5_000_000, "<=5tr"))


def khoang_tien(v):
    try:
        n = int(v or 0)
    except (TypeError, ValueError):
        return "khong_ro"
    if n < 0:
        return "am"
    for tran, nhan in _MOC_TIEN:
        if n <= tran:
            return nhan
    return ">5tr"


def _tinh_tu_dia_chi(dc):
    """Lấy phần cuối địa chỉ làm 'tỉnh' — thô nhưng ĐỦ cho việc gợi ý hãng, và quan trọng hơn:
    nó KHÔNG gửi số nhà/đường ra ngoài. Không đoán thêm; không có thì trả rỗng."""
    phan = [p.strip() for p in str(dc or "").split(",") if p.strip()]
    return phan[-1][:60] if phan else ""


def loc_truong_gui(loai, vao):
    """Lọc `vao` về ĐÚNG danh sách trắng của loại việc, kèm che SĐT và quy COD về khoảng.

    Trả `(du_lieu_gui, da_bo: list[str])`. `da_bo` ghi lại tên trường bị loại để audit nói
    được "đã bỏ gì" — ghi ra thì kiểm lại được, bỏ im lặng thì không (§12.2).

    `trich_don_tu_file` nhận NHIỀU dòng, nên lọc từng dòng qua CHÍNH một hàm `_loc_phang` —
    một chỗ lọc duy nhất, không có bản thứ hai để lệch nhau.
    """
    cho_phep = TRUONG_GUI[loai]
    nguon = dict(vao or {})
    if loai == "trich_don_tu_file":
        dong_sach, bo = [], set()
        for dong in (nguon.get("cac_dong") or [])[:1000]:
            d = dict(dong or {})
            stt = d.pop("stt", None)
            s, b = _loc_phang(cho_phep, d)
            if stt is not None:
                s["stt"] = stt
            bo |= set(b)
            dong_sach.append(s)
        bo |= {k for k in nguon if k != "cac_dong"}
        return {"cac_dong": dong_sach}, sorted(bo)
    return _loc_phang(cho_phep, nguon)


def _loc_phang(cho_phep, nguon):
    ra = {}
    if "sdt_che" in cho_phep and nguon.get("nguoi_nhan_sdt"):
        ra["sdt_che"] = che_sdt(nguon["nguoi_nhan_sdt"])
    if "cod_khoang" in cho_phep:
        ra["cod_khoang"] = khoang_tien(nguon.get("cod"))
    if "gia_tri_khoang" in cho_phep:
        ra["gia_tri_khoang"] = khoang_tien(nguon.get("gia_tri_khai"))
    if "tinh" in cho_phep:
        ra["tinh"] = nguon.get("tinh") or _tinh_tu_dia_chi(nguon.get("nguoi_nhan_dia_chi"))
    for k in cho_phep:
        if k in ("sdt_che", "cod_khoang", "gia_tri_khoang", "tinh"):
            continue
        if k in nguon and nguon[k] not in (None, ""):
            ra[k] = nguon[k]
    da_bo = sorted(k for k in nguon if k not in cho_phep)
    return ra, da_bo


# --------------------------------------------------------------------------------------
# CHÍNH SÁCH PHÊ DUYỆT
# --------------------------------------------------------------------------------------
# True = kết quả PHẢI qua người duyệt, công việc dừng ở `cho_duyet`.
# Nguyên tắc phân loại: việc nào mà kết quả có thể ĐỔI DỮ LIỆU ĐƠN thì phải duyệt; việc nào
# chỉ sinh VĂN BẢN GIẢI THÍCH cho người đọc thì không. Một gợi ý hãng mà tự áp là một đơn đi
# sai hãng mà không ai ký tên vào.
CHINH_SACH_DUYET = {
    "trich_don_tu_file": True,
    "chuan_hoa_truong": True,
    "goi_y_hang": True,
    "phat_hien_bat_thuong": False,
    "giai_thich_loi_kiem": False,
    "tom_tat_lo_import": False,
}


def can_duyet(loai, dau_hieu):
    """Chính sách + MỘT luật đè: dữ liệu vào có dấu hiệu tiêm thì BẮT BUỘC người xem, kể cả
    loại việc bình thường không cần duyệt. Lý do: dòng đó đã là dòng đáng ngờ."""
    return bool(CHINH_SACH_DUYET.get(loai, True) or dau_hieu)


# --------------------------------------------------------------------------------------
# NHÀ CUNG CẤP AI
# --------------------------------------------------------------------------------------
class NhaCungCapAI:
    """Hợp đồng connector. Người hiện thực chỉ cần một hàm `chay`.

    `chay(loai, prompt, du_lieu_gui, tenant_id) -> dict` — trả kết quả THÔ. Người gọi
    (`chay_viec`) tự kiểm schema; nhà cung cấp KHÔNG được tự khai là mình hợp lệ (§12.1 luật 1).

    `tenant_id` là THAM SỐ, không phải biến toàn cục hay thread-local: lượt gọi chạy trong một
    thread khác (xem `_chay_co_timeout`), nên thread-local ở đây sẽ về `None` một cách im lặng
    — đúng dạng hỏng im lặng §12.2. Truyền tường minh thì không có chỗ cho nó rỗng.
    """
    ma = "truu_tuong"
    ten = "(chưa đặt tên)"
    phien_ban_hop_dong = PHIEN_BAN_HOP_DONG
    san_sang = False

    def chay(self, loai, prompt, du_lieu_gui, tenant_id):
        raise NotImplementedError


class MockAIProvider(NhaCungCapAI):
    """Nhà cung cấp MÔ PHỎNG — chạy hoàn toàn trong tiến trình, KHÔNG có lượt gọi mạng nào.

    Ba việc dùng lại `ai_gateway` (đã nghiệm thu, AG-00 giữ): chuẩn hoá địa chỉ, phát hiện bất
    thường, gợi ý hãng. Ba việc còn lại mô phỏng tại đây. Mọi kết quả mang `mock: True` —
    giao diện đọc cờ đó để dán nhãn, không tự đoán.

    Lưu ý cố ý: `ai_gateway._goi()` tự tăng usage. `chay_viec` KHÔNG tăng usage lần nữa cho ba
    việc đó (xem `_LOI_QUA_GATEWAY`) — đếm hai lần là báo mức dùng sai.
    """
    ma = "mock"
    ten = "Mô phỏng nội bộ (chưa nối AI thật)"
    san_sang = True

    def chay(self, loai, prompt, d, tenant_id):
        if loai == "chuan_hoa_truong":
            kq = ai_gateway.chuan_hoa_dia_chi(tenant_id, d.get("gia_tri", ""))
            return {"truong": d.get("truong", ""), "gia_tri_goc": kq["dia_chi_goc"] or "",
                    "gia_tri_chuan": kq["dia_chi_chuan"], "do_tin_cay": 50,
                    "ly_do": "mô phỏng: chỉ dọn khoảng trắng, KHÔNG tra cứu địa giới hành chính"}
        if loai == "goi_y_hang":
            kq = ai_gateway.goi_y_hang(tenant_id,
                                       {"khoi_luong_gram": d.get("khoi_luong_gram", 0)})
            return {"goi_y": kq["goi_y"] if kq["goi_y"] in ai_validator.MA_HANG_CHO_PHEP
                    else "khong_ro",
                    "ly_do": kq["ly_do"], "luu_y": kq["luu_y"], "do_tin_cay": 40}
        if loai == "phat_hien_bat_thuong":
            # `ai_gateway.phat_hien_bat_thuong` cần số COD thật; ở đây CHỈ có khoảng — nên suy
            # từ khoảng. Cố ý: tối giản dữ liệu thắng độ tinh của kết quả.
            cb = []
            if d.get("cod_khoang") == ">5tr":
                cb.append("COD nằm ở khoảng trên 5 triệu — nên xác nhận lại với khách")
            if d.get("cod_khoang") == "am":
                cb.append("COD âm — dữ liệu sai, không phải bất thường nghiệp vụ")
            if int(d.get("khoi_luong_gram") or 0) > 20_000:
                cb.append("kiện nặng hơn 20kg — kiểm tra hãng có nhận không")
            if int(d.get("so_luong") or 0) > 50:
                cb.append("số lượng trên 50 — kiểm tra lại đơn vị tính")
            ai_gateway.phat_hien_bat_thuong(tenant_id, {})   # giữ đường đo usage
            return {"canh_bao": cb, "muc_do": "cao" if cb else "thap", "do_tin_cay": 45}
        if loai == "giai_thich_loi_kiem":
            gt = [_GIAI_THICH.get(_khoa_loi(x), f"Lỗi: {x}") for x in (d.get("loi") or [])]
            gy = ["Sửa trực tiếp trên dòng rồi bấm kiểm lại."] if gt else []
            return {"giai_thich": gt or ["Không có lỗi chặn nào."], "goi_y_sua": gy,
                    "do_tin_cay": 60}
        if loai == "tom_tat_lo_import":
            return {"tom_tat": (f"Lô {d.get('ten_file', '(không tên)')}: {d.get('so_dong', 0)} dòng, "
                                f"{d.get('so_valid', 0)} hợp lệ, {d.get('so_invalid', 0)} sai, "
                                f"{d.get('so_needs_review', 0)} cần xem."),
                    "diem_can_xem": list(d.get("ly_do_pho_bien") or []), "do_tin_cay": 70}
        if loai == "trich_don_tu_file":
            ra = []
            for i, dong in enumerate(d.get("cac_dong") or [], 1):
                truong = {k: str(v) for k, v in dong.items()
                          if k in ai_validator.TRUONG_DON and v not in (None, "")}
                ra.append({"stt": int(dong.get("stt") or i), "truong": truong,
                           "do_tin_cay": 35,
                           "ghi_chu_ai": "mô phỏng — chép lại dòng đã qua import engine, "
                                         "KHÔNG suy diễn thêm trường nào"})
            return {"cac_dong": ra, "tom_tat": f"mô phỏng trích {len(ra)} dòng"}
        raise don_hang.LoiNghiepVu(f"nhà cung cấp mô phỏng không biết loại việc {loai!r}")


_GIAI_THICH = {
    "thieu ten nguoi nhan": "Thiếu tên người nhận. Hãng bắt buộc có tên để giao.",
    "sdt phai 10 so bat dau bang 0": "Số điện thoại phải đủ 10 số và bắt đầu bằng 0.",
    "thieu dia chi": "Thiếu địa chỉ nhận. Cần tối thiểu phường/xã, quận/huyện, tỉnh.",
    "thieu ten hang": "Thiếu tên hàng. Hãng cần biết nội dung kiện.",
    "can nang phai > 0": "Cân nặng phải lớn hơn 0 gram.",
    "can nang khong phai so": "Cân nặng không đọc được thành số.",
    "cod khong duoc am": "COD không được âm.",
    "cod khong phai so": "COD không đọc được thành số.",
}


def _khoa_loi(s):
    import re
    import unicodedata
    s = str(s).replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


class VIPAIBrainConnector(NhaCungCapAI):
    """GIAO DIỆN RỖNG CÓ CHỦ Ý — VIP AI Brain CHƯA ĐƯỢC NỐI (V-G10-01 chưa cấp quyền).

    Đây KHÔNG phải mã chưa viết xong; đây là cái chốt. Khảo sát ngày 15/10/2026: dự án này
    KHÔNG được cung cấp hợp đồng kết nối nào của VIP AI Brain — không endpoint, không dạng
    xác thực, không schema request/response. Theo chỉ thị G10.5 và §12 (chống bịa), **không
    bịa URL, không bịa dạng request**. Vì vậy ở đây không có một đường mạng nào.

    CẦN ĐỦ SÁU THỨ sau mới nối được (danh sách này cũng in trong `docs/G10_FINAL_REPORT.md`):
      1. Endpoint thật (scheme + host + path) và môi trường tương ứng (thử / thật).
      2. Dạng xác thực: header nào, loại nào (Bearer / HMAC / mTLS), ai cấp credentials, cấp
         theo tenant hay theo nền tảng, cơ chế xoay khoá.
      3. Schema REQUEST cho từng loại việc trong `ai_validator.LOAI_VIEC`.
      4. Schema RESPONSE + bảng mã lỗi + mã nào được thử lại (khuôn
         `NormalizedCarrierError` §5: ok / từ chối / KHÔNG BIẾT, ba kết cục không gộp).
      5. Hợp đồng vận hành: trần tần suất, timeout cam kết, hạn mức, đơn giá để đo chi phí.
      6. Cơ sở xử lý dữ liệu cá nhân: ai là bên xử lý, dữ liệu lưu ở đâu, bao lâu, có dùng để
         huấn luyện không, và phê duyệt của anh Thành cho đúng cấu hình đó.
    Thiếu bất kỳ mục nào ⇒ vẫn là `ChuaCapQuyen`. Mở đường này là đổi `ai_gateway.MOCK`, mà
    việc đó AG-00 giữ.
    """
    ma = "vip_ai_brain"
    ten = "VIP AI Brain (chưa nối)"
    san_sang = False

    def chay(self, loai, prompt, du_lieu_gui, tenant_id=None):
        raise ChuaCapQuyen(
            "VIP AI Brain chưa được nối (V-G10-01 CHƯA CẤP QUYỀN). Cần: endpoint, dạng xác "
            "thực, schema request/response, bảng mã lỗi, hợp đồng vận hành, cơ sở xử lý dữ "
            "liệu cá nhân đã được phê duyệt. Xem docs/G10_FINAL_REPORT.md.")


_DS_NHA_CUNG_CAP = {}
for _p in (MockAIProvider(), VIPAIBrainConnector()):
    _DS_NHA_CUNG_CAP[_p.ma] = _p


def nha_cung_cap(ma=None):
    """Chọn nhà cung cấp. Khoá an toàn: `ai_gateway.MOCK` còn True thì CHỈ `mock` được dùng,
    bất kể người gọi xin gì. Đây là chốt thứ hai — chốt gốc là `VIPAIBrainConnector.chay` tự
    ném; giữ cả hai vì một khoá là một khoá có thể bị bỏ qua."""
    if ai_gateway.MOCK:
        return _DS_NHA_CUNG_CAP["mock"]
    p = _DS_NHA_CUNG_CAP.get(ma or "mock")
    if p is None or not p.san_sang:
        raise ChuaCapQuyen(f"nhà cung cấp {ma!r} chưa sẵn sàng")
    return p


# --------------------------------------------------------------------------------------
# QUYỀN
# --------------------------------------------------------------------------------------
def _can_quyen(tenant_id, user_id, hanh_dong):
    """Tra quyền từ CSDL (bảng role_permissions) — không tin người gọi.

    Dùng lại `don_hang.vai_tro_trong_tenant` + `quyen.co_quyen`: CÙNG MỘT NGUỒN với lớp kiểm
    ở `server.py`, nên hai lớp không thể lệch nhau. Đây là nếp đã có trong `don_hang._can_quyen`
    và cố ý giống nó.
    """
    vt = don_hang.vai_tro_trong_tenant(tenant_id, user_id)
    if not vt or not quyen.co_quyen(vt, hanh_dong):
        csdl.audit("ai_tu_choi_quyen", f"permission:{hanh_dong}",
                   f"vai trò {vt or '(không có membership)'}",
                   tenant_id=tenant_id, user_id=user_id, ket_qua="tu_choi")
        raise don_hang.LoiNghiepVu(f"không có quyền {hanh_dong}", 403)
    return vt


def _su_kien(tenant_id, job_id, loai_su_kien, chi_tiet="", user_id=None, so_luot_ai=0):
    csdl.ghi("INSERT INTO ai_su_kien (tenant_id, job_id, user_id, loai_su_kien, so_luot_ai,"
             " chi_tiet, luc) VALUES (?,?,?,?,?,?,?)",
             (tenant_id, job_id, user_id, loai_su_kien, so_luot_ai, chi_tiet[:2000],
              csdl.bay_gio()))


# --------------------------------------------------------------------------------------
# TẠO CÔNG VIỆC
# --------------------------------------------------------------------------------------
KHOA_VAO_CAM = ("tenant_id", "user_id", "token", "role", "platform_role", "quyen",
                "nha_cung_cap", "mock")


def _don_vao(vao):
    """Gỡ mọi khoá tự khai định danh/quyền khỏi `vao`. Trả `(sach, da_go)`.

    §21 và §1: `tenant_id` CHỈ đến từ phiên. Không chỉ "bỏ qua" — GỠ HẲN, để không có đường
    nào ở dưới đọc lại được nó. Và GHI LẠI cái đã gỡ: một lượt gửi `tenant_id` của tenant khác
    là dấu vết đáng để lại trong audit, không phải thứ im lặng cho qua.
    """
    vao = dict(vao or {})
    da_go = {}
    for k in list(vao):
        if str(k).lower() in KHOA_VAO_CAM:
            da_go[k] = vao.pop(k)
    return vao, da_go


def tao_viec(tenant_id, user_id, loai, vao, idem_key=None, batch_id=None, dong_id=None,
             kiem_quyen=True):
    """Tạo AIJob ở trạng thái `moi`. KHÔNG gọi nhà cung cấp — `chay_viec` làm việc đó.

    `tenant_id` là tham số của hàm, do `server.py` truyền từ phiên đã xác thực. Hàm này không
    có đường nào đọc `tenant_id` từ `vao`.
    """
    bao_dam_bang()
    if loai not in ai_validator.LOAI_VIEC:
        raise don_hang.LoiNghiepVu(f"loại việc AI không hợp lệ: {loai!r}")
    if not isinstance(tenant_id, int) or isinstance(tenant_id, bool) or tenant_id <= 0:
        raise don_hang.LoiNghiepVu("tenant_id phải là số nguyên dương lấy từ phiên", 403)
    if kiem_quyen:
        _can_quyen(tenant_id, user_id, QUYEN_DUNG)

    sach, da_go = _don_vao(vao)
    if da_go:
        # Ghi nhận ĐẦY ĐỦ tên khoá bị gỡ, nhưng chỉ ghi GIÁ TRỊ của khoá định danh tenant —
        # để đối chiếu được mưu toan vượt tenant. Không ghi token/mật khẩu (§8).
        chi_tiet = "gỡ khoá tự khai trong body: " + ", ".join(sorted(da_go))
        if "tenant_id" in da_go:
            chi_tiet += f" (body khai tenant_id={da_go['tenant_id']!r}, phiên là {tenant_id})"
        csdl.audit("ai_bo_khoa_tu_khai", "ai_job:moi", chi_tiet,
                   tenant_id=tenant_id, user_id=user_id)

    tho = json.dumps(sach, ensure_ascii=False)
    dau_hieu = ai_validator.dau_hieu_tiem(tho)
    ik = idem_key or f"{loai}-{uuid.uuid4().hex}"
    p = nha_cung_cap()
    cu = csdl.mot("SELECT * FROM ai_job WHERE tenant_id=? AND idem_key=?", (tenant_id, ik))
    if cu:
        return dict(cu)          # idempotent: cùng khoá thì trả việc cũ, không tạo việc hai
    con = csdl.ghi(
        "INSERT INTO ai_job (tenant_id, user_id, loai, trang_thai, vao_json, nha_cung_cap,"
        " phien_ban_hop_dong, can_nguoi_duyet, idem_key, tao_luc, mock, dau_hieu_tiem,"
        " batch_id, dong_id) VALUES (?,?,?,'moi',?,?,?,?,?,?,?,?,?,?)",
        (tenant_id, user_id, loai, tho, p.ma, PHIEN_BAN_HOP_DONG,
         1 if can_duyet(loai, dau_hieu) else 0, ik, csdl.bay_gio(),
         1 if ai_gateway.MOCK else 0, json.dumps(dau_hieu) if dau_hieu else None,
         batch_id, dong_id))
    job_id = con.lastrowid
    _su_kien(tenant_id, job_id, "tao", f"loại {loai}; dấu hiệu tiêm: {dau_hieu or 'không'}",
             user_id=user_id)
    csdl.audit("ai_job_tao", f"ai_job:{job_id}", f"loại {loai}, nhà cung cấp {p.ma}",
               tenant_id=tenant_id, user_id=user_id)
    return lay_viec(tenant_id, job_id)


# --------------------------------------------------------------------------------------
# CHẠY CÔNG VIỆC
# --------------------------------------------------------------------------------------
# Ba loại việc đi qua `ai_gateway`, mà `ai_gateway._goi()` đã tự tăng usage. `chay_viec`
# không tăng lần nữa cho chúng — đếm hai lần là báo mức dùng sai, mà mức dùng sai thì hạn
# mức gói chặn oan người đang dùng đúng.
_LOI_QUA_GATEWAY = ("chuan_hoa_truong", "goi_y_hang", "phat_hien_bat_thuong")


def _chay_co_timeout(fn, giay):
    """Chạy `fn` trong một thread, chờ tối đa `giay`. Trả `(xong: bool, kq, loi)`.

    GIỚI HẠN GHI RÕ (rủi ro cố ý nhận): Python không giết được thread. Hết hạn chờ thì hàm
    này trả về và công việc bị đánh `loi` + `timeout`, nhưng thread kia VẪN chạy tới khi tự
    xong. Với nhà cung cấp mô phỏng (thuần CPU, không mạng) điều đó vô hại. Khi nối thật,
    đúng chỗ phải đặt timeout là TẦNG HTTP của chính lượt gọi (`timeout=` của socket), không
    phải ở đây — và đó là một dòng trong danh sách "cần gì để nối" ở báo cáo. Không giả vờ
    rằng lớp này đủ.
    """
    hop = {}

    def _bao():
        try:
            hop["kq"] = fn()
        except BaseException as e:                      # noqa: BLE001 — ghi lại, không nuốt
            hop["loi"] = e
    th = threading.Thread(target=_bao, daemon=True, name="ai-job")
    th.start()
    th.join(giay)
    if th.is_alive():
        return False, None, None
    return True, hop.get("kq"), hop.get("loi")


def chay_viec(tenant_id, job_id, giay_timeout=GIAY_TIMEOUT, _buoc_loi=None):
    """`moi` → `dang_chay` → (`cho_duyet` | `xong` | `loi`).

    Thứ tự CỐ Ý: lọc trường → dựng prompt → QUÉT BÍ MẬT → (chỉ khi sạch) gọi nhà cung cấp →
    kiểm schema đầu ra → lưu. Quét bí mật đứng TRƯỚC lượt gọi, vì quét sau khi đã gửi thì
    không cứu được gì.

    `_buoc_loi` chỉ dùng trong bộ thử để mô phỏng nhà cung cấp hỏng/treo — tham số riêng, có
    gạch dưới, không có đường nào từ HTTP đặt được nó.
    """
    bao_dam_bang()
    job = lay_viec(tenant_id, job_id)
    if not job:
        raise don_hang.LoiNghiepVu("không có công việc AI này", 404)
    if job["trang_thai"] != "moi":
        raise don_hang.LoiNghiepVu(
            f"công việc đang ở {job['trang_thai']}, chỉ chạy được việc ở 'moi'")
    loai = job["loai"]
    vao = json.loads(job["vao_json"])
    _dat_trang_thai(tenant_id, job_id, "dang_chay")

    gui, da_bo = loc_truong_gui(loai, vao)
    prompt = ai_validator.dung_prompt(loai, gui, ai_validator.SCHEMA_RA[loai])

    bi_mat = ai_validator.quet_bi_mat(prompt)
    if bi_mat:
        # KHÔNG gọi nhà cung cấp. Ghi mô tả, KHÔNG ghi giá trị bí mật (§8).
        _ket_loi(tenant_id, job_id, "prompt chứa thứ trông như bí mật, đã CHẶN trước khi gửi: "
                                    + "; ".join(bi_mat), su_kien="chan_bi_mat")
        return lay_viec(tenant_id, job_id)

    p = nha_cung_cap(job["nha_cung_cap"])
    _su_kien(tenant_id, job_id, "goi_nha_cung_cap",
             f"nhà cung cấp {p.ma}; trường gửi: {sorted(gui)}; trường đã bỏ: {da_bo}",
             so_luot_ai=0 if loai in _LOI_QUA_GATEWAY else 1)
    t0 = time.monotonic()
    try:
        if loai not in _LOI_QUA_GATEWAY:
            # Việc không đi qua `ai_gateway` thì tầng này tự đo mức dùng — mỗi lượt gọi nhà
            # cung cấp đúng một lượt, không nhiều không ít.
            billing.kiem_va_tang_ai(tenant_id)
        if _buoc_loi == "treo":
            xong, kq, loi = _chay_co_timeout(lambda: time.sleep(giay_timeout + 5), 0.2)
        elif _buoc_loi == "no":
            xong, kq, loi = _chay_co_timeout(
                lambda: (_ for _ in ()).throw(RuntimeError("nhà cung cấp hỏng (mô phỏng)")),
                giay_timeout)
        elif _buoc_loi is not None:
            xong, kq, loi = True, _buoc_loi, None
        else:
            xong, kq, loi = _chay_co_timeout(
                lambda: p.chay(loai, prompt, gui, tenant_id), giay_timeout)
    except billing.VuotHanMuc as e:
        _ket_loi(tenant_id, job_id, f"vượt hạn mức AI của gói: {e}", su_kien="loi")
        raise
    ms = int((time.monotonic() - t0) * 1000)

    if not xong:
        _ket_loi(tenant_id, job_id,
                 f"nhà cung cấp không trả lời trong {giay_timeout}s — KHÔNG BIẾT kết quả, "
                 f"không coi là thành công", su_kien="timeout", ms=ms)
        return lay_viec(tenant_id, job_id)
    if loi is not None:
        _ket_loi(tenant_id, job_id, f"nhà cung cấp lỗi: {type(loi).__name__}: {loi}",
                 su_kien="loi", ms=ms)
        return lay_viec(tenant_id, job_id)

    if kq is not None and not isinstance(kq, dict):
        # Nhà cung cấp trả về chuỗi/danh sách/số: `dict(...)` NỔ thành ValueError rồi vọt lên
        # HTTP 500 — "máy chủ hỏng" trong khi lỗi là của bên trả về. §12.2: sai kiểu từ bên
        # ngoài phải thành lỗi có thông điệp, không phải 500. Lỗi này bộ thử bắt được thật
        # (ca I_04), không phải đề phòng trên giấy.
        _ket_loi(tenant_id, job_id,
                 f"nhà cung cấp trả về {type(kq).__name__}, phải là đối tượng JSON",
                 su_kien="loi", ms=ms)
        return lay_viec(tenant_id, job_id)
    ra = dict(kq or {})
    ra.setdefault("mock", bool(ai_gateway.MOCK))
    ra.setdefault("nha_cung_cap", p.ma)
    ra.setdefault("phien_ban_hop_dong", PHIEN_BAN_HOP_DONG)
    ok, loi_schema = ai_validator.kiem_ra(loai, ra)
    if not ok:
        _ket_loi(tenant_id, job_id, "kết quả không khớp schema: " + "; ".join(loi_schema),
                 su_kien="chan_lenh" if any("LỆNH" in x for x in loi_schema) else "loi", ms=ms)
        return lay_viec(tenant_id, job_id)

    dtc = ra.get("do_tin_cay")
    tt = "cho_duyet" if job["can_nguoi_duyet"] else "xong"
    csdl.ghi("UPDATE ai_job SET trang_thai=?, ra_json=?, do_tin_cay=?, ms_chay=?,"
             " xong_luc=?, loi=NULL WHERE tenant_id=? AND id=?",
             (tt, json.dumps(ra, ensure_ascii=False), dtc if isinstance(dtc, int) else None,
              ms, csdl.bay_gio() if tt == "xong" else None, tenant_id, job_id))
    _su_kien(tenant_id, job_id, "cho_duyet" if tt == "cho_duyet" else "xong",
             f"{ms}ms; mock={ra['mock']}")
    csdl.audit("ai_job_chay", f"ai_job:{job_id}", f"loại {loai} → {tt}, {ms}ms",
               tenant_id=tenant_id)
    return lay_viec(tenant_id, job_id)


def _dat_trang_thai(tenant_id, job_id, tt):
    csdl.ghi("UPDATE ai_job SET trang_thai=? WHERE tenant_id=? AND id=?",
             (tt, tenant_id, job_id))


def _ket_loi(tenant_id, job_id, ly_do, su_kien="loi", ms=None):
    csdl.ghi("UPDATE ai_job SET trang_thai='loi', loi=?, ms_chay=?, xong_luc=?"
             " WHERE tenant_id=? AND id=?",
             (ly_do[:2000], ms, csdl.bay_gio(), tenant_id, job_id))
    _su_kien(tenant_id, job_id, su_kien, ly_do)
    csdl.audit("ai_job_loi", f"ai_job:{job_id}", ly_do[:500], tenant_id=tenant_id,
               ket_qua="that_bai")


# --------------------------------------------------------------------------------------
# PHÊ DUYỆT — người quyết, không phải AI
# --------------------------------------------------------------------------------------
def duyet_viec(tenant_id, user_id, job_id, kiem_quyen=True):
    """`cho_duyet` → `xong`. CHỈ ghi nhận rằng người đã xem và đồng ý.

    Chốt quan trọng: hàm này KHÔNG áp kết quả vào đâu cả. Nó không tạo đơn, không sửa đơn,
    không gọi hãng. Người duyệt rồi thì giao diện mới cho họ COPY gợi ý vào màn nhập liệu và
    tự bấm Lưu qua đường `don_hang` bình thường — cùng đường mọi người dùng khác đi, cùng mọi
    phép kiểm, cùng mọi dòng audit.
    """
    bao_dam_bang()
    if kiem_quyen:
        _can_quyen(tenant_id, user_id, QUYEN_DUYET)
    job = lay_viec(tenant_id, job_id)
    if not job:
        raise don_hang.LoiNghiepVu("không có công việc AI này", 404)
    if job["trang_thai"] != "cho_duyet":
        raise don_hang.LoiNghiepVu(f"chỉ duyệt được việc ở 'cho_duyet', việc này ở "
                                   f"'{job['trang_thai']}'")
    csdl.ghi("UPDATE ai_job SET trang_thai='xong', duyet_boi=?, duyet_luc=?, xong_luc=?"
             " WHERE tenant_id=? AND id=? AND trang_thai='cho_duyet'",
             (user_id, csdl.bay_gio(), csdl.bay_gio(), tenant_id, job_id))
    _su_kien(tenant_id, job_id, "duyet", "người duyệt đồng ý gợi ý", user_id=user_id)
    csdl.audit("ai_job_duyet", f"ai_job:{job_id}", "duyệt gợi ý AI",
               tenant_id=tenant_id, user_id=user_id)
    return lay_viec(tenant_id, job_id)


def tu_choi_viec(tenant_id, user_id, job_id, ly_do, kiem_quyen=True):
    bao_dam_bang()
    if kiem_quyen:
        _can_quyen(tenant_id, user_id, QUYEN_DUYET)
    if not str(ly_do or "").strip():
        raise don_hang.LoiNghiepVu("phải ghi lý do từ chối")
    job = lay_viec(tenant_id, job_id)
    if not job:
        raise don_hang.LoiNghiepVu("không có công việc AI này", 404)
    if job["trang_thai"] != "cho_duyet":
        raise don_hang.LoiNghiepVu(f"chỉ từ chối được việc ở 'cho_duyet', việc này ở "
                                   f"'{job['trang_thai']}'")
    csdl.ghi("UPDATE ai_job SET trang_thai='tu_choi', duyet_boi=?, duyet_luc=?, loi=?"
             " WHERE tenant_id=? AND id=? AND trang_thai='cho_duyet'",
             (user_id, csdl.bay_gio(), f"người từ chối: {ly_do}"[:2000], tenant_id, job_id))
    _su_kien(tenant_id, job_id, "tu_choi", str(ly_do)[:500], user_id=user_id)
    csdl.audit("ai_job_tu_choi", f"ai_job:{job_id}", str(ly_do)[:500],
               tenant_id=tenant_id, user_id=user_id)
    return lay_viec(tenant_id, job_id)


# --------------------------------------------------------------------------------------
# ĐỌC
# --------------------------------------------------------------------------------------
def lay_viec(tenant_id, job_id):
    """Đọc một công việc. `tenant_id` LUÔN nằm trong WHERE — tenant A không đọc được việc của
    tenant B, và điều đó cưỡng chế bằng câu truy vấn, không bằng một phép `if` ở trên."""
    bao_dam_bang()
    r = csdl.mot("SELECT * FROM ai_job WHERE id=? AND tenant_id=?", (job_id, tenant_id))
    return dict(r) if r else None


def ds_viec(tenant_id, trang_thai=None, loai=None, gioi_han=100):
    bao_dam_bang()
    sql = "SELECT * FROM ai_job WHERE tenant_id=?"
    ts = [tenant_id]
    if trang_thai:
        if trang_thai not in TRANG_THAI:
            raise don_hang.LoiNghiepVu(f"trạng thái lạ: {trang_thai!r}")
        sql += " AND trang_thai=?"
        ts.append(trang_thai)
    if loai:
        if loai not in ai_validator.LOAI_VIEC:
            raise don_hang.LoiNghiepVu(f"loại việc lạ: {loai!r}")
        sql += " AND loai=?"
        ts.append(loai)
    sql += " ORDER BY id DESC LIMIT ?"
    ts.append(max(1, min(int(gioi_han or 100), 500)))
    return [dict(x) for x in csdl.nhieu(sql, tuple(ts))]


def ds_su_kien(tenant_id, job_id=None, gioi_han=200):
    bao_dam_bang()
    if job_id is None:
        ds = csdl.nhieu("SELECT * FROM ai_su_kien WHERE tenant_id=? ORDER BY id DESC LIMIT ?",
                        (tenant_id, max(1, min(int(gioi_han or 200), 500))))
    else:
        ds = csdl.nhieu("SELECT * FROM ai_su_kien WHERE tenant_id=? AND job_id=? ORDER BY id",
                        (tenant_id, job_id))
    return [dict(x) for x in ds]


def thong_ke_dung(tenant_id):
    """Mức dùng AI: số đếm ĐO TỪ BACKEND. Hai nguồn, cố ý nói riêng:
      · `usage` — bộ đếm hạn mức của `billing` (cái quyết định chặn hay không);
      · `job` — số công việc theo trạng thái (cái người dùng nhìn thấy trên màn hình).
    Hai số này KHÔNG bắt buộc bằng nhau: một công việc bị chặn vì có bí mật trong prompt thì
    có job nhưng không tốn lượt. Gộp hai số là báo cáo sai, nên để nguyên hai cột.
    """
    bao_dam_bang()
    goi = billing.goi_cua_tenant(tenant_id)
    u = billing.usage_hien_tai(tenant_id)
    theo_tt = {r["trang_thai"]: r["c"] for r in csdl.nhieu(
        "SELECT trang_thai, COUNT(*) c FROM ai_job WHERE tenant_id=? GROUP BY trang_thai",
        (tenant_id,))}
    theo_loai = {r["loai"]: r["c"] for r in csdl.nhieu(
        "SELECT loai, COUNT(*) c FROM ai_job WHERE tenant_id=? GROUP BY loai", (tenant_id,))}
    luot = csdl.mot("SELECT COALESCE(SUM(so_luot_ai),0) s FROM ai_su_kien WHERE tenant_id=?",
                    (tenant_id,))["s"]
    return {
        "thang": u["thang"],
        "goi": goi["ten"] if goi else None,
        "so_ai_da_dung": u["so_ai"],
        "han_muc_ai_thang": goi["han_muc_ai_thang"] if goi else None,
        "luot_tinh_phi_tu_su_kien": luot,
        "job_theo_trang_thai": theo_tt,
        "job_theo_loai": theo_loai,
        "mock": bool(ai_gateway.MOCK),
        "nha_cung_cap": nha_cung_cap().ma,
        # Chi phí: CHƯA ĐO ĐƯỢC. Không có đơn giá nào được cung cấp, và mock không tốn tiền.
        # Ghi `None` kèm lý do thay vì bịa một con số (§12).
        "chi_phi_dong": None,
        "chi_phi_ghi_chu": "chưa có đơn giá nhà cung cấp (V-G10-01 chưa cấp) — không bịa số",
    }


# --------------------------------------------------------------------------------------
# ĐỀ XUẤT CHO NGƯỜI DUYỆT — chỉ ĐỌC, không ghi gì
# --------------------------------------------------------------------------------------
def de_xuat_cho_nguoi_duyet(tenant_id, job_id, nguoi_gui=None):
    """Dựng gói dữ liệu để màn duyệt hiển thị: gợi ý của AI + kết quả KIỂM của hệ.

    Dùng lại `don_hang.kiem_don(tenant_id, d=...)` — phép kiểm có sẵn, KHÔNG ghi CSDL, và
    KHÔNG viết phép kiểm thứ hai (chỉ thị: "đừng viết phép kiểm thứ hai").

    `nguoi_gui` là thông tin người gửi của chính doanh nghiệp, do giao diện truyền vào CHỈ để
    phép kiểm chạy đủ (`kiem_don` đòi ba trường người gửi). Nó KHÔNG bao giờ đi vào prompt —
    xem `TRUONG_KHONG_GUI`. Thiếu nó thì màn duyệt báo "thiếu người gửi", đó là lỗi GIẢ do
    thiếu bối cảnh, nên nói rõ ở `thieu_nguoi_gui` thay vì để người xem tự đoán.

    Hàm này là ranh giới cứng của G10: nó trả về DỮ LIỆU để người xem, và không có nhánh nào
    tạo/sửa/gửi đơn. Đơn nháp chỉ sinh ra khi người dùng tự bấm duyệt lô import (đường
    `nhap_file.duyet_batch` của G05, không nằm trong file này).
    """
    job = lay_viec(tenant_id, job_id)
    if not job:
        raise don_hang.LoiNghiepVu("không có công việc AI này", 404)
    vao = json.loads(job["vao_json"])
    ra = json.loads(job["ra_json"]) if job["ra_json"] else None
    de_xuat = []
    if ra and job["loai"] == "trich_don_tu_file":
        # GỘP: gợi ý của AI đè lên dòng GỐC NẰM Ở MÁY. Vì sao phải gộp: số điện thoại và COD
        # KHÔNG hề được gửi cho nhà cung cấp (xem `TRUONG_KHONG_GUI`), nên kết quả AI không
        # thể chứa chúng. Kiểm một bản nháp thiếu SĐT thì luôn báo "thiếu SĐT" — một lỗi GIẢ
        # do chính phép tối giản dữ liệu sinh ra. Gộp lại thì phép kiểm chạy trên dữ liệu đủ,
        # mà dữ liệu cá nhân vẫn chưa từng rời máy.
        goc = {int(d.get("stt") or i): d
               for i, d in enumerate(vao.get("cac_dong") or [], 1)}
        for dong in ra.get("cac_dong", []):
            stt = dong.get("stt")
            d = dict(goc.get(stt) or {})
            d.pop("stt", None)
            tu_ai = dict(dong.get("truong") or {})
            d.update(tu_ai)
            for k, v in (nguoi_gui or {}).items():
                d.setdefault(f"nguoi_gui_{k}" if not k.startswith("nguoi_gui") else k, v)
            kiem = None
            try:
                kiem = don_hang.kiem_don(tenant_id, d=d)
            except don_hang.LoiNghiepVu as e:
                kiem = {"hop_le": False, "loi": [str(e)], "canh_bao": []}
            de_xuat.append({"stt": stt, "truong": d, "truong_tu_ai": sorted(tu_ai),
                            "do_tin_cay": dong.get("do_tin_cay"), "kiem": kiem})
    return {
        "job": job,
        "mock": bool(job["mock"]),
        "nhan_mock": "MÔ PHỎNG — chưa nối AI thật (V-G10-01)" if job["mock"] else None,
        "can_nguoi_duyet": bool(job["can_nguoi_duyet"]),
        "ra": ra,
        "de_xuat": de_xuat,
        "dau_hieu_tiem": json.loads(job["dau_hieu_tiem"]) if job["dau_hieu_tiem"] else [],
        "truong_da_gui": sorted(loc_truong_gui(job["loai"], vao)[0]),
        "truong_khong_gui": sorted(TRUONG_KHONG_GUI),
        "thieu_nguoi_gui": not bool(nguoi_gui),
        # Nói thẳng ra giao diện: kết quả này KHÔNG tự áp được vào đâu.
        "ghi_chu_an_toan": "Kết quả AI là dữ liệu, không phải lệnh. Hệ không có đường nào tự "
                           "áp gợi ý này vào đơn; người duyệt phải tự nhập/xác nhận qua màn "
                           "đơn hàng như bình thường.",
    }


# --------------------------------------------------------------------------------------
# TRỢ GIÚP DỰNG ĐẦU VÀO TỪ LÔ IMPORT (G05) — đọc, không ghi
# --------------------------------------------------------------------------------------
def vao_tu_lo_import(tenant_id, batch_id, tran_dong=200):
    """Dựng `vao` cho `trich_don_tu_file` và `tom_tat_lo_import` từ một lô đã qua G05.

    Luồng G10.2: TẢI FILE → IMPORT ENGINE G05 → CHUẨN HOÁ → AI GATEWAY → GỢI Ý AI → KIỂM TRA
    → NGƯỜI DUYỆT → ĐƠN NHÁP G04. Hàm này là mũi nối giữa G05 và tầng AI, và nó chỉ ĐỌC:
    `tenant_id` nằm trong WHERE nên không lấy được lô của tenant khác.
    """
    bao_dam_bang()
    b = csdl.mot("SELECT * FROM import_batch WHERE id=? AND tenant_id=?", (batch_id, tenant_id))
    if not b:
        raise don_hang.LoiNghiepVu("không có lô import này", 404)
    ds = csdl.nhieu("SELECT d.* FROM import_dong d JOIN import_batch bb ON bb.id=d.batch_id"
                    " WHERE d.batch_id=? AND bb.tenant_id=? ORDER BY d.stt LIMIT ?",
                    (batch_id, tenant_id, max(1, min(int(tran_dong or 200), 1000))))
    cac_dong, dem, ly_do = [], {}, {}
    for d in ds:
        dem[d["trang_thai"]] = dem.get(d["trang_thai"], 0) + 1
        if d["loi"]:
            ly_do[d["loi"][:120]] = ly_do.get(d["loi"][:120], 0) + 1
        r = json.loads(d["du_lieu_json"])
        r["stt"] = d["stt"]
        cac_dong.append(r)
    return {
        "trich": {"cac_dong": cac_dong},
        "tom_tat": {"ten_file": b["ten_file"], "so_dong": len(ds),
                    "so_valid": dem.get("VALID", 0), "so_invalid": dem.get("INVALID", 0),
                    "so_needs_review": dem.get("NEEDS_REVIEW", 0),
                    "ly_do_pho_bien": [f"{k} (x{v})" for k, v in
                                       sorted(ly_do.items(), key=lambda x: -x[1])[:5]]},
        "dem_trang_thai": dem,
    }
