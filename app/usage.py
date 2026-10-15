# G08 — Sự kiện sử dụng, bộ đếm NGUYÊN TỬ, máy tính phí, DỰ THẢO hoá đơn. AG-02 SaaS Billing.
#
# Ba điều phải nhớ khi đọc file này:
#
# 1. **Bộ đếm cộng bằng MỘT câu `UPDATE` có trần trong `WHERE`, xét `rowcount`.** Cấm
#    đọc-rồi-ghi. Khuôn này đã vỡ thật ở đợt 2: `billing.kiem_va_tang_don` bản cũ đọc
#    `usage_hien_tai` rồi mới tăng, và khi còn 1 suất thì **5/8 luồng** lọt qua. Điều kiện
#    phải nằm trong `WHERE` để chính CSDL so — khe hở giữa đọc và ghi khi đó không tồn tại.
#
# 2. **Chống thu phí hai lần bằng RÀNG BUỘC CSDL, không bằng phép kiểm trong mã.**
#    `su_kien_dung` có `UNIQUE(tenant_id, idem_key)`. Worker thử lại là chuyện bình thường;
#    thu phí hai lần thì không. Ràng buộc ở tầng CSDL thì không có khe hở giữa đọc và ghi.
#
# 3. **Không có bộ đếm thứ hai cho cùng một việc.** Đơn/AI đếm ở `usage_thang` của
#    `app/billing.py`; file/dòng/byte nhập đếm ở `han_muc_nhap_thang` của `app/gioi_han.py`.
#    G08 ĐỌC hai nơi đó và chỉ tự đếm loại mà KHÔNG ai đếm (`goi_dich_vu.LOAI_DEM_G08`).
#    Hai bộ đếm cho một việc là hai bộ sẽ lệch nhau, và không ai biết tin bên nào.
import calendar
import json
import sqlite3

import billing
import csdl
import gioi_han
import goi_dich_vu as gdv

TRAN_SO_LUONG_MOT_SU_KIEN = 10 ** 9     # chặn tràn bộ đếm: một sự kiện không được to vô hạn


class LoiUsage(gdv.LoiGoi):
    """Lỗi của tầng usage. Kế thừa `LoiGoi` (KHÔNG kế thừa `billing.VuotHanMuc` → không ra 402)."""


class DangKyTamNgung(LoiUsage):
    def __init__(self, tenant_id):
        super().__init__(f"đăng ký của tenant {tenant_id} đang tạm ngưng — "
                         f"thao tác có tính phí bị chặn", 403)


# ---------------------------------------------------------------------------------------
# B.1 — ĐO MỨC DÙNG. Mỗi con số nói rõ nó đến từ bảng nào (CLAUDE.md §12.1 luật 4).
# ---------------------------------------------------------------------------------------
def ky_hien_tai() -> str:
    return csdl.thang_nay()


def _khoang_ky(ky):
    """(ngày đầu, ngày cuối, số ngày) của kỳ `YYYY-MM`."""
    nam, thang = int(ky[:4]), int(ky[5:7])
    so_ngay = calendar.monthrange(nam, thang)[1]
    return f"{ky}-01", f"{ky}-{so_ngay:02d}", so_ngay


def _dem_g08(tenant_id, ky, loai) -> int:
    gdv._dam_bao_bang()
    r = csdl.mot("SELECT so_luong FROM bo_dem_dung WHERE tenant_id=? AND ky=? AND loai=?",
                 (tenant_id, ky, loai))
    return int(r["so_luong"]) if r else 0


def muc_dang_dung(tenant_id, ky=None) -> dict:
    """Mức đang dùng của mọi loại hạn mức, LẤY TỪ ĐÚNG BỘ ĐẾM ĐANG GIỮ SỐ ĐÓ.

    `ky=None` → kỳ hiện tại. Loại không theo kỳ (nhân viên, kết nối hãng) đếm thẳng từ bảng
    nghiệp vụ nên không phụ thuộc `ky`; nói rõ trong `nguon_do` để không ai tưởng là số tháng.
    """
    ky = ky or ky_hien_tai()
    u = billing.usage_hien_tai(tenant_id) if ky == ky_hien_tai() else _usage_thang_cua(tenant_id, ky)
    nhap = gioi_han.da_dung(tenant_id) if ky == ky_hien_tai() else {
        "so_file": 0, "so_dong": 0, "so_byte": 0}
    so_nv = csdl.mot(
        "SELECT COUNT(*) c FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
        " WHERE m.tenant_id=? AND m.trang_thai='hoat_dong' AND u.trang_thai='hoat_dong'",
        (tenant_id,))["c"]
    so_hang = csdl.mot("SELECT COUNT(*) c FROM carrier_accounts WHERE tenant_id=? AND kich_hoat=1",
                       (tenant_id,))["c"]
    return {
        "don_thang": int(u["so_don"]), "ai_thang": int(u["so_ai"]),
        "nhan_vien": int(so_nv), "tai_khoan_hang": int(so_hang),
        "api_thang": _dem_g08(tenant_id, ky, "api_thang"),
        "file_nhap_thang": int(nhap["so_file"]), "dong_nhap_thang": int(nhap["so_dong"]),
        "byte_luu_tru_thang": int(nhap["so_byte"]),
    }


def _usage_thang_cua(tenant_id, ky):
    r = csdl.mot("SELECT so_don, so_ai FROM usage_thang WHERE tenant_id=? AND thang=?",
                 (tenant_id, ky))
    return {"so_don": r["so_don"] if r else 0, "so_ai": r["so_ai"] if r else 0}


NGUON_DO = {
    "don_thang": "usage_thang.so_don (app/billing.py)",
    "ai_thang": "usage_thang.so_ai (app/billing.py)",
    "nhan_vien": "COUNT tenant_memberships ⋈ users (đếm trực tiếp, không theo kỳ)",
    "tai_khoan_hang": "COUNT carrier_accounts (đếm trực tiếp, không theo kỳ)",
    "api_thang": "bo_dem_dung (app/usage.py — G08)",
    "file_nhap_thang": "han_muc_nhap_thang.so_file (app/gioi_han.py)",
    "dong_nhap_thang": "han_muc_nhap_thang.so_dong (app/gioi_han.py)",
    "byte_luu_tru_thang": "han_muc_nhap_thang.so_byte (app/gioi_han.py)",
}


def trang_thai_han_muc(tenant_id, ky=None) -> dict:
    """Trần + đã dùng + còn lại + tỷ lệ, cho từng loại. Đây là thứ API trả ra cho giao diện.

    `tran=None` nghĩa là trần do `gioi_han` quyết (số của nó nằm ở `gioi_han.trang_thai`),
    KHÔNG phải "không có trần" — nói rõ để giao diện không vẽ ra một ô vô hạn.
    """
    ky = ky or ky_hien_tai()
    hm = gdv.han_muc_hieu_luc(tenant_id)
    dung = muc_dang_dung(tenant_id, ky)
    dong = {}
    for loai, t in hm["tran"].items():
        da = dung.get(loai, 0)
        gt = t["gia_tri"]
        if gt is None:
            con, ty = None, None
        elif gt == 0:
            con, ty = None, 0                       # 0 = không áp trần
        else:
            con, ty = max(0, gt - da), min(10000, da * 10000 // gt)   # điểm cơ bản (§16)
        dong[loai] = {"ten": t["ten"], "tran": gt, "da_dung": da, "con_lai": con,
                      "ty_le_diem_co_ban": ty, "nguon_tran": t["nguon"],
                      "nguon_do": NGUON_DO.get(loai, "?"), "nguon_dem": t["nguon_dem"]}
    return {"tenant_id": tenant_id, "ky": ky, "goi_id": hm["goi_id"], "goi_ten": hm["goi_ten"],
            "phien_ban": hm["phien_ban"], "trang_thai_dang_ky": hm["trang_thai"],
            "tu_dang_ky": hm["tu_dang_ky"], "dong": dong,
            "gioi_han_nhap": gioi_han.trang_thai(tenant_id) if ky == ky_hien_tai() else None}


NGUONG_CANH_BAO_DIEM_CO_BAN = 8000      # 80 % — điểm cơ bản, không số thập phân (§16)


def canh_bao_sap_het(tenant_id, ky=None, nguong=NGUONG_CANH_BAO_DIEM_CO_BAN) -> list:
    """Loại nào đã dùng ≥ `nguong` (điểm cơ bản) thì cảnh báo. Chỉ BÁO, không tự nâng gói."""
    ra = []
    for loai, d in trang_thai_han_muc(tenant_id, ky)["dong"].items():
        ty = d["ty_le_diem_co_ban"]
        if ty is not None and d["tran"] not in (None, 0) and ty >= nguong:
            ra.append({"loai": loai, "ten": d["ten"], "da_dung": d["da_dung"],
                       "tran": d["tran"], "ty_le_diem_co_ban": ty,
                       "het": d["con_lai"] == 0})
    return sorted(ra, key=lambda x: -x["ty_le_diem_co_ban"])


def kiem_han_muc(tenant_id, loai, them=1) -> dict:
    """Xem TRƯỚC còn chỗ hay không — để giao diện hiện cảnh báo.

    **Đây KHÔNG phải chỗ chặn.** Chặn là câu `UPDATE` trong `_cong_co_tran`/`ghi_su_kien`.
    Hàm này đọc rồi trả lời, nên giữa lúc nó trả `con_cho=True` và lúc người kia thật sự ghi
    vẫn có khe hở — ai dùng hàm này làm cổng chặn là dựng lại đúng lỗi đã vỡ ở đợt 2.
    """
    tran = gdv.tran_cua_loai(tenant_id, loai)
    da = muc_dang_dung(tenant_id).get(loai, 0)
    return {"loai": loai, "tran": tran, "da_dung": da, "them": them,
            "con_cho": da + them <= tran,
            "ghi_chu": "chỉ để hiển thị; chốt chặn nằm ở câu UPDATE của ghi_su_kien"}


# ---------------------------------------------------------------------------------------
# B.2 — GHI SỰ KIỆN SỬ DỤNG. Nguyên tử + chống trùng ở tầng CSDL.
# ---------------------------------------------------------------------------------------
def _cong_co_tran(kn, tenant_id, ky, loai, so_luong, tran) -> bool:
    """Cộng `so_luong` vào `bo_dem_dung` CHỈ KHI không vượt `tran`. MỘT câu UPDATE.

    Dùng `kn` được truyền vào để nằm trong CÙNG giao dịch với câu chèn sự kiện — nhờ vậy
    `rollback` bỏ được cả hai. Cùng khuôn `gioi_han._cong_co_tran`.
    """
    kn.execute("INSERT OR IGNORE INTO bo_dem_dung (tenant_id, ky, loai) VALUES (?,?,?)",
               (tenant_id, ky, loai))
    cur = kn.execute(
        "UPDATE bo_dem_dung SET so_luong=so_luong+?, cap_nhat_luc=?"
        " WHERE tenant_id=? AND ky=? AND loai=? AND so_luong+? <= ?",
        (so_luong, csdl.bay_gio(), tenant_id, ky, loai, so_luong, tran))
    return cur.rowcount == 1


def ghi_su_kien(tenant_id, loai, so_luong=1, idem_key=None, nguon="he_thong",
                tham_chieu=None, ky=None) -> dict:
    """Ghi MỘT sự kiện có tính phí. Nguyên tử, chống trùng, chống vượt hạn mức.

    Trả `{"ok": True, "trung": bool, ...}`. `trung=True` nghĩa là `idem_key` này đã ghi rồi:
    **không cộng lần hai**, và đó là kết quả ĐÚNG cho một worker thử lại.

    Hai đường ghi, khác nhau ở chỗ bộ đếm nằm đâu:

    * `nguon_dem='g08'` → sự kiện và bộ đếm nằm trong CÙNG MỘT giao dịch. Vượt trần thì
      `rollback` bỏ cả hai, nên lần sau thử lại (sau khi nâng gói) vẫn ghi được.
    * `nguon_dem` khác → bộ đếm do module khác giữ (`billing`, `gioi_han`). Gọi hàm của họ
      để KHÔNG dựng bộ đếm thứ hai. Hàm của họ tự `commit`, mà `csdl.mo()` trả về đúng một
      kết nối cho mỗi thread, nên lượt `commit` ấy chốt luôn câu chèn sự kiện của ta. Vì vậy
      khi họ từ chối thì ta **bù bằng một câu `DELETE` đúng dòng vừa chèn**, vẫn trong vùng
      `khoa_ghi`, để không còn lại một sự kiện "đã ghi mà chưa được đếm" — thứ đó sẽ khiến
      lần thử lại bị coi là trùng rồi lặng lẽ không thu gì.
    """
    gdv._dam_bao_bang()
    if loai not in gdv.LOAI_HAN_MUC:
        raise LoiUsage(f"loại sự kiện lạ: {loai!r}; chỉ nhận {sorted(gdv.LOAI_HAN_MUC)}", 400)
    so_luong = int(so_luong)
    if so_luong <= 0:
        raise LoiUsage("so_luong phải > 0 — sự kiện sử dụng không dùng để TRỪ bộ đếm", 400)
    if so_luong > TRAN_SO_LUONG_MOT_SU_KIEN:
        raise LoiUsage(f"so_luong {so_luong} vượt {TRAN_SO_LUONG_MOT_SU_KIEN} "
                       f"— chặn tràn bộ đếm", 400)
    if not idem_key or not str(idem_key).strip():
        raise LoiUsage("thiếu idem_key — mọi thao tác có tính phí phải có khoá chống trùng", 400)
    idem_key = str(idem_key).strip()
    if nguon not in ("he_thong", "nguoi", "hang"):
        raise LoiUsage(f"nguon lạ: {nguon!r}; chỉ nhận he_thong|nguoi|hang", 400)
    if not csdl.mot("SELECT id FROM tenants WHERE id=?", (tenant_id,)):
        raise LoiUsage(f"tenant {tenant_id} không tồn tại", 404)
    if not gdv.dang_hoat_dong(tenant_id):
        raise DangKyTamNgung(tenant_id)

    ky = ky or ky_hien_tai()
    nguon_dem = gdv.LOAI_HAN_MUC[loai]["nguon_dem"]
    cot_sk = ("tenant_id, loai, so_luong, idem_key, nguon, tham_chieu, ky, tao_luc")
    gia_tri_sk = (tenant_id, loai, so_luong, idem_key, nguon, tham_chieu, ky, csdl.bay_gio())

    with csdl.khoa_ghi:
        kn = csdl.mo()
        try:
            cur = kn.execute(f"INSERT INTO su_kien_dung ({cot_sk}) VALUES (?,?,?,?,?,?,?,?)",
                             gia_tri_sk)
        except sqlite3.IntegrityError:
            kn.rollback()
            cu = csdl.mot("SELECT * FROM su_kien_dung WHERE tenant_id=? AND idem_key=?",
                          (tenant_id, idem_key))
            return {"ok": True, "trung": True, "su_kien_id": cu["id"] if cu else None,
                    "loai": cu["loai"] if cu else loai, "so_luong": 0,
                    "ghi_chu": "idem_key đã ghi trước đó — KHÔNG thu phí lần hai"}
        sk_id = cur.lastrowid

        if nguon_dem == "g08":
            tran = gdv.tran_cua_loai(tenant_id, loai)
            if not _cong_co_tran(kn, tenant_id, ky, loai, so_luong, tran):
                kn.rollback()           # bỏ cả sự kiện lẫn lượt cộng — thử lại sau vẫn ghi được
                da = _dem_g08(tenant_id, ky, loai)
                raise billing.VuotHanMuc(
                    f"đã dùng {da}/{tran} {gdv.LOAI_HAN_MUC[loai]['ten']} kỳ {ky}")
            kn.commit()
            return {"ok": True, "trung": False, "su_kien_id": sk_id, "loai": loai,
                    "so_luong": so_luong, "bo_dem": _dem_g08(tenant_id, ky, loai),
                    "nguon_dem": nguon_dem}

        # Bộ đếm do module khác giữ. Xem docstring về lượt `commit` lồng và câu DELETE bù.
        try:
            _goi_bo_dem_ngoai(tenant_id, loai, so_luong)
        except Exception:
            kn.execute("DELETE FROM su_kien_dung WHERE id=?", (sk_id,))
            kn.commit()
            raise
        kn.commit()
        return {"ok": True, "trung": False, "su_kien_id": sk_id, "loai": loai,
                "so_luong": so_luong, "nguon_dem": nguon_dem,
                "bo_dem": muc_dang_dung(tenant_id, ky).get(loai)}


def _goi_bo_dem_ngoai(tenant_id, loai, so_luong):
    """Gọi đúng bộ đếm đang giữ con số đó. KHÔNG tự đếm lại ở G08."""
    if loai == "don_thang":
        for _ in range(so_luong):
            billing.kiem_va_tang_don(tenant_id)     # nguyên tử, trần trong WHERE
    elif loai == "ai_thang":
        for _ in range(so_luong):
            billing.kiem_va_tang_ai(tenant_id)
    elif loai == "nhan_vien":
        billing.kiem_han_muc_nhan_vien(tenant_id)   # đếm trực tiếp — không có gì để cộng
    elif loai == "tai_khoan_hang":
        billing.kiem_han_muc_tai_khoan_hang(tenant_id)
    elif loai in ("file_nhap_thang", "dong_nhap_thang", "byte_luu_tru_thang"):
        raise LoiUsage(
            f"{loai!r} do app/gioi_han.py đếm và chặn (PHẦN B). Gọi gioi_han.kiem_file_nhap /"
            f" dat_truoc_don_nhap, đừng ghi qua G08 — hai bộ đếm cho một việc sẽ lệch nhau", 400)
    else:
        raise LoiUsage(f"chưa khai bộ đếm ngoài cho {loai!r}", 500)


TRUONG_TU_YEU_CAU = ("loai", "so_luong", "idem_key", "tham_chieu")


def ghi_tu_yeu_cau(tenant_id, body, nguon="nguoi") -> dict:
    """Ghi sự kiện từ body của một yêu cầu HTTP. `tenant_id` LẤY TỪ PHIÊN, không từ body.

    **Backend chốt hạn mức. Frontend không được tự quyết.** Hàm này chỉ đọc bốn trường ở
    `TRUONG_TU_YEU_CAU`. Mọi trường khác trong body — `tran`, `han_muc_don_thang`, `goi_id`,
    `tenant_id`, `bo_dem`, `phien_ban` — bị **bỏ hoàn toàn**, và được trả lại ở
    `truong_bi_bo` để người gọi thấy mình vừa khai thứ không có tác dụng. Có ca thử gửi body
    tự khai trần `10**9` và kiểm rằng vẫn bị chặn ở trần thật.
    """
    body = dict(body or {})
    bi_bo = sorted(k for k in body if k not in TRUONG_TU_YEU_CAU)
    kq = ghi_su_kien(tenant_id,
                     loai=body.get("loai"),
                     so_luong=body.get("so_luong", 1),
                     idem_key=body.get("idem_key"),
                     nguon=nguon,
                     tham_chieu=body.get("tham_chieu"))
    kq["truong_bi_bo"] = bi_bo
    return kq


def su_kien_cua_ky(tenant_id, ky=None, loai=None) -> list:
    gdv._dam_bao_bang()
    ky = ky or ky_hien_tai()
    if loai:
        ds = csdl.nhieu("SELECT * FROM su_kien_dung WHERE tenant_id=? AND ky=? AND loai=?"
                        " ORDER BY id", (tenant_id, ky, loai))
    else:
        ds = csdl.nhieu("SELECT * FROM su_kien_dung WHERE tenant_id=? AND ky=? ORDER BY id",
                        (tenant_id, ky))
    return [dict(r) for r in ds]


def doi_soat_su_kien(tenant_id, ky=None) -> dict:
    """Đối chiếu SỔ SỰ KIỆN với BỘ ĐẾM — hai phép đo độc lập (CLAUDE.md §12.1).

    Bộ đếm là thứ dùng để chặn, nên không được tin nó mà không có cái gì soi lại. `lech != 0`
    thì hàm này KHÔNG tự sửa — sửa im lặng là che mất nguyên nhân. Chỉ với loại đếm ở G08 mới
    so được 1:1; loại đếm ở nơi khác có đường ghi riêng (ví dụ `don_hang.gui_don` gọi thẳng
    `billing`) nên sổ sự kiện của G08 không phủ hết — ghi rõ ở `ngoai_pham_vi`.
    """
    ky = ky or ky_hien_tai()
    ra, ngoai = {}, {}
    for loai, mo_ta in gdv.LOAI_HAN_MUC.items():
        tong = csdl.mot("SELECT COALESCE(SUM(so_luong),0) s FROM su_kien_dung"
                        " WHERE tenant_id=? AND ky=? AND loai=?", (tenant_id, ky, loai))["s"]
        if mo_ta["nguon_dem"] == "g08":
            dem = _dem_g08(tenant_id, ky, loai)
            ra[loai] = {"so_su_kien": int(tong), "bo_dem": dem, "lech": int(tong) - dem}
        else:
            ngoai[loai] = {"so_su_kien_qua_g08": int(tong), "bo_dem_o": NGUON_DO.get(loai),
                           "ly_do": "có đường ghi khác không đi qua G08"}
    return {"ky": ky, "so_sanh_duoc": ra, "ngoai_pham_vi": ngoai}


# ---------------------------------------------------------------------------------------
# B.3 — KỲ TÍNH PHÍ
# ---------------------------------------------------------------------------------------
def mo_ky(tenant_id, ky=None) -> dict:
    gdv._dam_bao_bang()
    ky = ky or ky_hien_tai()
    bd, kt, _ = _khoang_ky(ky)
    csdl.ghi("INSERT OR IGNORE INTO ky_tinh_phi (tenant_id, ky, bat_dau, ket_thuc, tao_luc)"
             " VALUES (?,?,?,?,?)", (tenant_id, ky, bd, kt, csdl.bay_gio()))
    return dict(csdl.mot("SELECT * FROM ky_tinh_phi WHERE tenant_id=? AND ky=?", (tenant_id, ky)))


def dong_ky(tenant_id, ky=None, boi=None) -> dict:
    ky = ky or ky_hien_tai()
    mo_ky(tenant_id, ky)
    csdl.ghi("UPDATE ky_tinh_phi SET trang_thai='dong', dong_luc=? WHERE tenant_id=? AND ky=?",
             (csdl.bay_gio(), tenant_id, ky))
    gdv.ghi_nhat_ky(tenant_id, ky, "dong_ky", "", boi=boi)
    return dict(csdl.mot("SELECT * FROM ky_tinh_phi WHERE tenant_id=? AND ky=?", (tenant_id, ky)))


# ---------------------------------------------------------------------------------------
# B.4 — MÁY TÍNH PHÍ. Chỉ DỰ THẢO nội bộ. Không phát hành hoá đơn, không trừ tiền.
# ---------------------------------------------------------------------------------------
def _doan_ky(ky, luc):
    """`True` nếu mốc `luc` (khuôn `csdl.bay_gio()`) nằm trong kỳ `ky`."""
    return isinstance(luc, str) and luc[:7] == ky


def _chang_goi_trong_ky(tenant_id, ky) -> list:
    """Các CHẶNG gói trong kỳ: [{goi_id, phien_ban, ngay_bat_dau, so_ngay, gia_thang_dong}].

    Dựng từ `dang_ky_lich_su`: mốc đổi gói nằm trong kỳ thì mở một chặng mới từ NGÀY đó.
    Gói ở ĐẦU kỳ lấy từ `tu_goi/tu_phien_ban` của lần đổi đầu tiên trong kỳ; không có lần đổi
    nào trong kỳ thì cả kỳ là gói hiện tại.

    Giới hạn đã biết, ghi ra chứ không che: lịch sử chỉ có từ lúc G08 bật, nên kỳ TRƯỚC khi
    có `dang_ky_lich_su` sẽ được tính là một chặng duy nhất theo gói hiện tại.
    """
    _, _, so_ngay_ky = _khoang_ky(ky)
    dk = gdv.dang_ky_hien_tai(tenant_id)
    if dk:
        goi_cuoi, pb_cuoi = dk["goi_id"], dk["goi_phien_ban"]
    else:
        g = gdv._goi_cua_tenant_tho(tenant_id)
        goi_cuoi, pb_cuoi = g["id"], gdv.phien_ban_moi_nhat(g["id"])
    doi = [r for r in gdv.lich_su(tenant_id)
           if r["loai"] in ("nang_goi", "ha_goi", "doi_phien_ban") and _doan_ky(ky, r["luc"])]
    if not doi:
        anh = gdv.doc_phien_ban(goi_cuoi, pb_cuoi)
        return [{"goi_id": goi_cuoi, "phien_ban": pb_cuoi, "ngay_bat_dau": 1,
                 "so_ngay": so_ngay_ky, "gia_thang_dong": int(anh["gia_thang_dong"]),
                 "ten": anh["ten"]}]
    moc = []
    dau = doi[0]
    moc.append((1, dau["tu_goi"], dau["tu_phien_ban"]))
    for r in doi:
        ngay = int(r["luc"][8:10])
        moc.append((ngay, r["den_goi"], r["den_phien_ban"]))
    chang = []
    for i, (ngay, goi_id, pb) in enumerate(moc):
        ngay_het = (moc[i + 1][0] - 1) if i + 1 < len(moc) else so_ngay_ky
        so_ngay = max(0, ngay_het - ngay + 1)
        if so_ngay == 0:
            continue                        # hai lần đổi trong cùng một ngày → chặng rỗng, bỏ
        anh = gdv.doc_phien_ban(goi_id, pb)
        chang.append({"goi_id": goi_id, "phien_ban": pb, "ngay_bat_dau": ngay,
                      "so_ngay": so_ngay, "gia_thang_dong": int(anh["gia_thang_dong"]),
                      "ten": anh["ten"]})
    return chang


def tinh_phi(tenant_id, ky=None, prorate=True) -> dict:
    """Tính tiền cho một kỳ. KHÔNG ghi gì vào CSDL — thuần đọc + tính.

    - Phí gói: chia theo NGÀY giữa các chặng gói trong kỳ (`prorate=True`). `prorate=False`
      thì lấy giá của chặng CUỐI cho cả kỳ (dùng khi muốn giữ nguyên nếp "trả theo gói cuối").
    - Phí vượt hạn mức: **0 đồng, có chủ đích.** Hệ này CHẶN khi hết hạn mức chứ không cho
      dùng quá rồi tính thêm tiền, nên không có con số vượt để thu. Nếu sau này anh Thành
      muốn bán phần vượt thì đó là quyết định về GIÁ, phải có đơn giá do anh chốt — G08 không
      tự bịa một đơn giá nào (§12 chống bịa).
    - Phần dư làm tròn của phép chia theo ngày được trả ở `phan_du_bo_dong`: nó bị bỏ, nhưng
      bị bỏ CÓ GHI SỐ, không biến mất im lặng (§16).
    """
    gdv._dam_bao_bang()
    ky = ky or ky_hien_tai()
    bd, kt, so_ngay_ky = _khoang_ky(ky)
    chang = _chang_goi_trong_ky(tenant_id, ky)
    dong_chang, tien_goi, phan_du_tong = [], 0, 0
    if prorate and len(chang) > 1:
        for c in chang:
            tien, du = gdv.chia_tien_theo_ngay(c["gia_thang_dong"], c["so_ngay"], so_ngay_ky)
            tien_goi += tien
            phan_du_tong += du
            dong_chang.append(dict(c, so_tien_dong=tien, phan_du=du))
    else:
        c = chang[-1]
        tien_goi = c["gia_thang_dong"]
        dong_chang.append(dict(c, so_tien_dong=tien_goi, phan_du=0,
                               ghi_chu="cả kỳ một gói" if len(chang) == 1 else "prorate=False"))
    dung = muc_dang_dung(tenant_id, ky)
    hm = gdv.han_muc_hieu_luc(tenant_id)
    return {
        "tenant_id": tenant_id, "ky": ky, "bat_dau": bd, "ket_thuc": kt,
        "so_ngay_ky": so_ngay_ky, "prorate": bool(prorate and len(chang) > 1),
        "chang": dong_chang,
        "tien_goi_dong": int(tien_goi),
        "tien_vuot_dong": 0,
        "ly_do_khong_thu_vuot": "hệ CHẶN khi hết hạn mức, không cho dùng quá rồi thu thêm;"
                                " đơn giá phần vượt chưa có ai chốt nên G08 không tự đặt",
        "tong_dong": int(tien_goi),
        "phan_du_bo_dong": int(phan_du_tong),
        "muc_dung": dung, "nguon_do": NGUON_DO,
        "goi_hien_tai": {"goi_id": hm["goi_id"], "phien_ban": hm["phien_ban"],
                         "trang_thai": hm["trang_thai"]},
        "la_du_thao": True, "nhan_phap_ly": gdv.NHAN_PHAP_LY,
    }


def lap_du_thao(tenant_id, ky=None, boi=None) -> dict:
    """Lập DỰ THẢO hoá đơn cho một kỳ. Gọi lại KHÔNG tạo dự thảo thứ hai.

    `UNIQUE(tenant_id, ky)` trên `du_thao_hoa_don` chặn thu phí hai lần ở tầng CSDL. Gọi lần
    hai trả lại chính dự thảo đã có kèm `trung=True` — đúng cái một worker thử lại cần.

    **Đây là bản nháp nội bộ.** Không phát hành hoá đơn điện tử, không nối cổng thanh toán,
    không tự trừ tiền. Câu cảnh báo `nhan_phap_ly` được ghi vào CHÍNH dòng dự thảo (không chỉ
    hiện trên giao diện), nên bản xuất ra ở đâu cũng mang theo nó.
    """
    gdv._dam_bao_bang()
    ky = ky or ky_hien_tai()
    mo_ky(tenant_id, ky)
    p = tinh_phi(tenant_id, ky)
    dk = gdv.dang_ky_hien_tai(tenant_id)
    with csdl.khoa_ghi:
        kn = csdl.mo()
        try:
            cur = kn.execute(
                "INSERT INTO du_thao_hoa_don (tenant_id, ky, dang_ky_id, la_du_thao,"
                " nhan_phap_ly, tien_goi_dong, tien_vuot_dong, tong_dong, phan_du_bo_dong,"
                " chi_tiet_json, tao_boi, tao_luc) VALUES (?,?,?,1,?,?,?,?,?,?,?,?)",
                (tenant_id, ky, dk["id"] if dk else None, gdv.NHAN_PHAP_LY,
                 p["tien_goi_dong"], p["tien_vuot_dong"], p["tong_dong"], p["phan_du_bo_dong"],
                 json.dumps(p, ensure_ascii=False), boi, csdl.bay_gio()))
            dt_id = cur.lastrowid
            kn.commit()
        except sqlite3.IntegrityError:
            kn.rollback()
            cu = csdl.mot("SELECT * FROM du_thao_hoa_don WHERE tenant_id=? AND ky=?",
                          (tenant_id, ky))
            gdv.ghi_nhat_ky(tenant_id, ky, "lap_du_thao", "đã có dự thảo — không lập lần hai",
                            ket_qua="trung", boi=boi)
            return dict(cu, trung=True)
    gdv.ghi_nhat_ky(tenant_id, ky, "lap_du_thao", f"tổng {p['tong_dong']} đồng", boi=boi)
    return dict(csdl.mot("SELECT * FROM du_thao_hoa_don WHERE id=?", (dt_id,)), trung=False)


def doc_du_thao(tenant_id, ky=None):
    gdv._dam_bao_bang()
    ky = ky or ky_hien_tai()
    r = csdl.mot("SELECT * FROM du_thao_hoa_don WHERE tenant_id=? AND ky=?", (tenant_id, ky))
    return dict(r) if r else None


def danh_sach_du_thao(tenant_id) -> list:
    gdv._dam_bao_bang()
    return [dict(r) for r in csdl.nhieu(
        "SELECT * FROM du_thao_hoa_don WHERE tenant_id=? ORDER BY ky DESC", (tenant_id,))]


def bao_cao_dung(tenant_id, ky=None) -> dict:
    """Báo cáo mức dùng một kỳ: trần/đã dùng/còn lại + sổ sự kiện + đối chiếu + cảnh báo."""
    ky = ky or ky_hien_tai()
    return {"ky": ky, "han_muc": trang_thai_han_muc(tenant_id, ky),
            "su_kien": su_kien_cua_ky(tenant_id, ky),
            "doi_soat": doi_soat_su_kien(tenant_id, ky),
            "canh_bao": canh_bao_sap_het(tenant_id, ky),
            "phi_du_kien": tinh_phi(tenant_id, ky),
            "du_thao": doc_du_thao(tenant_id, ky)}
