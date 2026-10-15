# G08 — Gói dịch vụ, PHIÊN BẢN gói, đăng ký của tenant, hạn mức hiệu lực. AG-02 SaaS Billing.
#
# Ba luật nền của file này (SHARED_CONTRACTS §16, §19, §20):
#   1. TIỀN là `INTEGER` đơn vị ĐỒNG. Không `REAL`, không nhân 100, không thập phân.
#   2. KHÔNG đổi, KHÔNG xoá ba mã gói đang chạy (`free`/`basic`/`pro`). File này chỉ ĐỌC
#      `goi_dich_vu`; mọi thứ mới nằm ở bảng MỚI. Không một câu `ALTER`/`DROP`/`UPDATE` nào
#      chạm `goi_dich_vu` hay `tenants`.
#   3. Hạn mức đã thoả thuận KHÔNG đổi hồi tố. Xem §A.2 "phiên bản gói".
#
# Vì sao cần PHIÊN BẢN gói: `goi_dich_vu` chỉ giữ hạn mức HIỆN TẠI của mỗi gói. Sửa
# `han_muc_don_thang` của `basic` từ 1000 xuống 800 là sửa luôn hạn mức của mọi tenant đang
# chạy `basic` — họ bị siết mà không ai thông báo, và không còn cách nào dựng lại con số họ
# đã thoả thuận. Cách chữa: mỗi lần đổi hạn mức thì PHÁT HÀNH một dòng mới trong
# `goi_phien_ban` (ảnh chụp đầy đủ hạn mức + giá), và `dang_ky.goi_phien_ban` GHIM số phiên
# bản. Tenant đang ở `basic` phiên bản 1 đọc hạn mức từ ảnh chụp phiên bản 1 — phát hành
# phiên bản 2 không chạm tới họ. Chuyển họ sang phiên bản 2 là một hành động RIÊNG
# (`doi_goi`/`chuyen_phien_ban`), có ghi vết trong `dang_ky_lich_su`.
import threading

import csdl

# ---------------------------------------------------------------------------------------
# A.1 — DDL. CHỈ `CREATE TABLE/INDEX IF NOT EXISTS`. Không ALTER, không DROP, không DELETE.
#       AG-00 lấy nguyên hằng này vào migration v8.
# ---------------------------------------------------------------------------------------
DDL_G08 = """
-- Ảnh chụp hạn mức + giá của một gói tại một thời điểm. KHÔNG BAO GIỜ sửa một dòng đã có:
-- đổi hạn mức = thêm dòng phiên bản mới. Đây là thứ giữ cho hạn mức không đổi hồi tố.
CREATE TABLE IF NOT EXISTS goi_phien_ban (
  goi_id             TEXT    NOT NULL REFERENCES goi_dich_vu(id),
  phien_ban          INTEGER NOT NULL,
  ten                TEXT    NOT NULL,
  gia_thang_dong     INTEGER NOT NULL,            -- ĐỒNG, INTEGER (§16)
  han_muc_don_thang  INTEGER NOT NULL,
  han_muc_ai_thang   INTEGER NOT NULL,
  so_nhan_vien       INTEGER NOT NULL,
  so_tai_khoan_hang  INTEGER NOT NULL,
  han_muc_api_thang  INTEGER NOT NULL DEFAULT 0,  -- 0 = chưa áp trần (xem GIA_TRI_KHONG_TRAN)
  ghi_chu            TEXT,
  tao_boi            INTEGER,
  tao_luc            TEXT    NOT NULL,
  PRIMARY KEY (goi_id, phien_ban)
);

-- Đăng ký của một tenant. GHIM (goi_id, goi_phien_ban) — đây là "thoả thuận" của tenant đó.
CREATE TABLE IF NOT EXISTS dang_ky (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
  goi_id         TEXT    NOT NULL REFERENCES goi_dich_vu(id),
  goi_phien_ban  INTEGER NOT NULL,
  trang_thai     TEXT    NOT NULL DEFAULT 'dang_hoat_dong', -- dang_hoat_dong|tam_ngung|da_huy
  ky_bat_dau     TEXT    NOT NULL,                          -- YYYY-MM
  ky_ket_thuc    TEXT,                                      -- NULL = còn hiệu lực
  tao_luc        TEXT    NOT NULL,
  cap_nhat_luc   TEXT,
  FOREIGN KEY (goi_id, goi_phien_ban) REFERENCES goi_phien_ban(goi_id, phien_ban)
);
-- Một tenant chỉ được MỘT đăng ký còn sống. Ràng buộc ở CSDL, không phải phép kiểm trong mã.
CREATE UNIQUE INDEX IF NOT EXISTS ux_dang_ky_song
  ON dang_ky(tenant_id) WHERE trang_thai <> 'da_huy';

-- Lịch sử đổi gói. CHỈ GHI THÊM. Dữ liệu vượt hạn mức khi hạ gói ghi vào `vuot_json`,
-- KHÔNG xoá dữ liệu nào (§19 luật thùng rác + "đừng im lặng xoá").
CREATE TABLE IF NOT EXISTS dang_ky_lich_su (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id       INTEGER NOT NULL REFERENCES tenants(id),
  dang_ky_id      INTEGER REFERENCES dang_ky(id),
  loai            TEXT    NOT NULL,   -- kich_hoat|nang_goi|ha_goi|doi_phien_ban|tam_ngung|mo_lai|huy
  tu_goi          TEXT, tu_phien_ban INTEGER,
  den_goi         TEXT, den_phien_ban INTEGER,
  tu_gia_dong     INTEGER, den_gia_dong INTEGER,
  vuot_json       TEXT,               -- hạn mức đang bị vượt lúc hạ gói (ghi ra, không xoá dữ liệu)
  ly_do           TEXT,
  boi             INTEGER,
  luc             TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_dkls_tenant ON dang_ky_lich_su(tenant_id, id);

-- Hạn mức RIÊNG cho một tenant (nâng/hạ lẻ không cần phát hành gói mới). Không bắt buộc.
CREATE TABLE IF NOT EXISTS han_muc_rieng (
  tenant_id  INTEGER NOT NULL REFERENCES tenants(id),
  loai       TEXT    NOT NULL,
  gia_tri    INTEGER NOT NULL,
  ly_do      TEXT,
  boi        INTEGER,
  luc        TEXT    NOT NULL,
  PRIMARY KEY (tenant_id, loai)
);

-- Sổ SỰ KIỆN SỬ DỤNG (§20 UsageEvent). `UNIQUE(tenant_id, idem_key)` là ràng buộc CSDL.
CREATE TABLE IF NOT EXISTS su_kien_dung (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
  loai         TEXT    NOT NULL,
  so_luong     INTEGER NOT NULL,
  idem_key     TEXT    NOT NULL,
  nguon        TEXT    NOT NULL,      -- he_thong|nguoi|hang
  tham_chieu   TEXT,
  ky           TEXT    NOT NULL,      -- YYYY-MM, chốt lúc ghi
  tao_luc      TEXT    NOT NULL,
  UNIQUE (tenant_id, idem_key)
);
CREATE INDEX IF NOT EXISTS ix_skd_ky ON su_kien_dung(tenant_id, ky, loai);

-- Bộ đếm sử dụng cho những loại mà KHÔNG module nào khác đang đếm. Cộng bằng MỘT `UPDATE`
-- có trần trong `WHERE`. Loại nào đã có bộ đếm ở nơi khác thì KHÔNG đếm lại ở đây
-- (xem LOAI_HAN_MUC: `nguon_dem`) — hai bộ đếm cho một việc là hai bộ sẽ lệch nhau.
CREATE TABLE IF NOT EXISTS bo_dem_dung (
  tenant_id    INTEGER NOT NULL REFERENCES tenants(id),
  ky           TEXT    NOT NULL,
  loai         TEXT    NOT NULL,
  so_luong     INTEGER NOT NULL DEFAULT 0,
  cap_nhat_luc TEXT,
  PRIMARY KEY (tenant_id, ky, loai)
);

-- Kỳ tính phí. `trang_thai='dong'` = đã lập dự thảo, không nhận thêm thay đổi tính phí.
CREATE TABLE IF NOT EXISTS ky_tinh_phi (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id   INTEGER NOT NULL REFERENCES tenants(id),
  ky          TEXT    NOT NULL,
  bat_dau     TEXT    NOT NULL,
  ket_thuc    TEXT    NOT NULL,
  trang_thai  TEXT    NOT NULL DEFAULT 'mo',    -- mo | dong
  tao_luc     TEXT    NOT NULL,
  dong_luc    TEXT,
  UNIQUE (tenant_id, ky)
);

-- DỰ THẢO hoá đơn — BẢN NHÁP NỘI BỘ. KHÔNG phải hoá đơn pháp lý, KHÔNG trừ tiền.
-- `UNIQUE(tenant_id, ky)` chặn thu phí hai lần cho cùng một kỳ ở tầng CSDL.
CREATE TABLE IF NOT EXISTS du_thao_hoa_don (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id      INTEGER NOT NULL REFERENCES tenants(id),
  ky             TEXT    NOT NULL,
  dang_ky_id     INTEGER REFERENCES dang_ky(id),
  la_du_thao     INTEGER NOT NULL DEFAULT 1,     -- luôn 1; có ca thử canh
  nhan_phap_ly   TEXT    NOT NULL,               -- câu cảnh báo in trên chính dự thảo
  tien_goi_dong  INTEGER NOT NULL,
  tien_vuot_dong INTEGER NOT NULL DEFAULT 0,
  tong_dong      INTEGER NOT NULL,
  phan_du_bo_dong INTEGER NOT NULL DEFAULT 0,    -- phần dư làm tròn — ghi ra, không để mất im lặng
  chi_tiet_json  TEXT    NOT NULL,
  trang_thai     TEXT    NOT NULL DEFAULT 'nhap', -- nhap | da_gui_xem | huy
  tao_boi        INTEGER,
  tao_luc        TEXT    NOT NULL,
  UNIQUE (tenant_id, ky)
);

-- Nhật ký tính phí. CHỈ GHI THÊM.
CREATE TABLE IF NOT EXISTS nhat_ky_tinh_phi (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id  INTEGER REFERENCES tenants(id),
  ky         TEXT,
  hanh_dong  TEXT NOT NULL,
  ket_qua    TEXT NOT NULL DEFAULT 'thanh_cong',
  chi_tiet   TEXT,
  boi        INTEGER,
  luc        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_nktp_tenant ON nhat_ky_tinh_phi(tenant_id, id);
"""

# 0 trong cột hạn mức nghĩa là "chưa áp trần". Dùng một hằng thay vì rải `10**12` khắp mã.
GIA_TRI_KHONG_TRAN = 2 ** 62
NHAN_PHAP_LY = ("BẢN NHÁP NỘI BỘ — KHÔNG PHẢI HOÁ ĐƠN. Không có giá trị pháp lý, "
                "không phải chứng từ thuế, không trừ tiền tự động.")

_da_tao_bang = False
_khoa_bang = threading.Lock()


class LoiGoi(Exception):
    """Lỗi nghiệp vụ của tầng gói/đăng ký. CỐ Ý không kế thừa `billing.VuotHanMuc`.

    `server.py` đổi `billing.VuotHanMuc` thành HTTP 402 ("cần trả tiền"). Hạ gói sai hay gói
    không tồn tại KHÔNG phải chuyện trả tiền, nên nó phải ra mã khác. Kế thừa là vô tình bật
    một thông điệp thu phí mà không ai quyết định — cùng lý do `gioi_han.VuotHanMucNhap` đã
    tách ra (CLAUDE.md §12.2, hỏng im lặng).
    """

    def __init__(self, msg, ma=400):
        super().__init__(msg)
        self.ma = ma


class HaGoiVuotHanMuc(LoiGoi):
    """Hạ gói mà mức đang dùng đã vượt hạn mức gói mới. `vuot` nói rõ vượt cái gì."""

    def __init__(self, msg, vuot, ma=409):
        super().__init__(msg, ma)
        self.vuot = vuot


def _dam_bao_bang():
    """Tạo bảng của G08 nếu chưa có. Cùng khuôn `gioi_han._dam_bao_bang`."""
    global _da_tao_bang
    if _da_tao_bang:
        return
    with _khoa_bang:
        if _da_tao_bang:
            return
        with csdl.khoa_ghi:
            kn = csdl.mo()
            kn.executescript(DDL_G08)
            kn.commit()
        _da_tao_bang = True
        _dam_bao_phien_ban_goc()


def nap_lai_bang():
    """Cho bộ thử gọi sau `csdl.dong()`: quên trạng thái "đã tạo bảng"."""
    global _da_tao_bang
    _da_tao_bang = False


# ---------------------------------------------------------------------------------------
# A.2 — PHIÊN BẢN GÓI
# ---------------------------------------------------------------------------------------
COT_HAN_MUC_GOI = ("han_muc_don_thang", "han_muc_ai_thang", "so_nhan_vien", "so_tai_khoan_hang")


def _dam_bao_phien_ban_goc():
    """Chụp ảnh PHIÊN BẢN 1 cho mọi gói đang có trong `goi_dich_vu`.

    `INSERT OR IGNORE` — chạy bao nhiêu lần cũng ra một kết quả, và KHÔNG sửa ảnh chụp đã có.
    Đọc `goi_dich_vu`, không ghi vào nó: ba dòng `free`/`basic`/`pro` không bị chạm (§19).
    """
    ds = csdl.nhieu("SELECT * FROM goi_dich_vu")
    with csdl.khoa_ghi:
        kn = csdl.mo()
        for g in ds:
            kn.execute(
                "INSERT OR IGNORE INTO goi_phien_ban (goi_id, phien_ban, ten, gia_thang_dong,"
                " han_muc_don_thang, han_muc_ai_thang, so_nhan_vien, so_tai_khoan_hang,"
                " han_muc_api_thang, ghi_chu, tao_luc) VALUES (?,1,?,?,?,?,?,?,0,?,?)",
                (g["id"], g["ten"], int(g["gia_thang"]), int(g["han_muc_don_thang"]),
                 int(g["han_muc_ai_thang"]), int(g["so_nhan_vien"]), int(g["so_tai_khoan_hang"]),
                 "ảnh chụp phiên bản gốc từ goi_dich_vu", csdl.bay_gio()))
        kn.commit()


def phien_ban_moi_nhat(goi_id) -> int:
    _dam_bao_bang()
    r = csdl.mot("SELECT MAX(phien_ban) pb FROM goi_phien_ban WHERE goi_id=?", (goi_id,))
    pb = (r["pb"] or 0) if r else 0
    if pb == 0:
        raise LoiGoi(f"gói {goi_id!r} chưa có phiên bản nào", 404)
    return pb


def doc_phien_ban(goi_id, phien_ban) -> dict:
    _dam_bao_bang()
    r = csdl.mot("SELECT * FROM goi_phien_ban WHERE goi_id=? AND phien_ban=?", (goi_id, phien_ban))
    if not r:
        raise LoiGoi(f"không có gói {goi_id!r} phiên bản {phien_ban}", 404)
    return dict(r)


def danh_sach_goi() -> list:
    """Mọi gói kèm phiên bản mới nhất. Đây là thứ trả ra cho màn "danh sách gói"."""
    _dam_bao_bang()
    ra = []
    for g in csdl.nhieu("SELECT * FROM goi_dich_vu ORDER BY gia_thang"):
        pb = phien_ban_moi_nhat(g["id"])
        a = doc_phien_ban(g["id"], pb)
        a["so_phien_ban"] = csdl.mot("SELECT COUNT(*) c FROM goi_phien_ban WHERE goi_id=?",
                                     (g["id"],))["c"]
        ra.append(a)
    return ra


def phat_hanh_phien_ban(goi_id, han_muc: dict, gia_thang_dong=None, ghi_chu="", boi=None) -> dict:
    """Phát hành phiên bản MỚI của một gói. KHÔNG đổi hồi tố tenant đang chạy.

    Tenant đang ở phiên bản cũ vẫn đọc hạn mức từ ảnh chụp cũ cho tới khi có người CHUYỂN họ
    sang phiên bản mới (`chuyen_phien_ban`). Có ca thử canh điều này.

    `han_muc` chỉ nhận đúng các khoá đã khai — khoá lạ bị từ chối chứ không bỏ qua im lặng
    (bỏ qua im lặng là cách gõ sai tên hạn mức rồi tưởng đã đặt được).
    """
    _dam_bao_bang()
    if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (goi_id,)):
        raise LoiGoi(f"gói {goi_id!r} không tồn tại trong goi_dich_vu", 404)
    cu = doc_phien_ban(goi_id, phien_ban_moi_nhat(goi_id))
    cho_phep = set(COT_HAN_MUC_GOI) | {"han_muc_api_thang"}
    la = set(han_muc) - cho_phep
    if la:
        raise LoiGoi(f"hạn mức lạ: {sorted(la)}; chỉ nhận {sorted(cho_phep)}", 400)
    moi = {k: int(han_muc.get(k, cu[k])) for k in cho_phep}
    for k, v in moi.items():
        if v < 0:
            raise LoiGoi(f"hạn mức {k} không được âm", 400)
    gia = int(cu["gia_thang_dong"] if gia_thang_dong is None else gia_thang_dong)
    if gia < 0:
        raise LoiGoi("giá không được âm", 400)
    if not isinstance(gia, int):
        raise LoiGoi("giá phải là INTEGER đồng (§16)", 400)
    pb = cu["phien_ban"] + 1
    with csdl.khoa_ghi:
        kn = csdl.mo()
        kn.execute(
            "INSERT INTO goi_phien_ban (goi_id, phien_ban, ten, gia_thang_dong,"
            " han_muc_don_thang, han_muc_ai_thang, so_nhan_vien, so_tai_khoan_hang,"
            " han_muc_api_thang, ghi_chu, tao_boi, tao_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (goi_id, pb, cu["ten"], gia, moi["han_muc_don_thang"], moi["han_muc_ai_thang"],
             moi["so_nhan_vien"], moi["so_tai_khoan_hang"], moi["han_muc_api_thang"],
             ghi_chu, boi, csdl.bay_gio()))
        kn.commit()
    ghi_nhat_ky(None, None, "phat_hanh_phien_ban", f"{goi_id} v{pb}", boi=boi)
    return doc_phien_ban(goi_id, pb)


# ---------------------------------------------------------------------------------------
# A.3 — ĐĂNG KÝ CỦA TENANT
# ---------------------------------------------------------------------------------------
def dang_ky_hien_tai(tenant_id):
    """Đăng ký còn sống của tenant, hoặc None. `None` KHÔNG phải lỗi — xem `han_muc_hieu_luc`."""
    _dam_bao_bang()
    return csdl.mot("SELECT * FROM dang_ky WHERE tenant_id=? AND trang_thai<>'da_huy'",
                    (tenant_id,))


def _goi_cua_tenant_tho(tenant_id):
    g = csdl.mot("SELECT g.* FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id WHERE t.id=?",
                 (tenant_id,))
    if not g:
        raise LoiGoi(f"không xác định được gói dịch vụ của tenant {tenant_id}", 400)
    return g


def kich_hoat(tenant_id, goi_id=None, phien_ban=None, boi=None, ly_do="") -> dict:
    """Kích hoạt đăng ký cho tenant. Gọi lại thì trả đăng ký đang có (không tạo dòng thứ hai).

    `goi_id=None` → lấy đúng gói `tenants.goi_id` đang trỏ tới. Nhờ vậy mọi tenant có từ
    trước đợt này kích hoạt được mà không đổi gói của họ.
    """
    _dam_bao_bang()
    dk = dang_ky_hien_tai(tenant_id)
    if dk:
        return dict(dk)
    goi_id = goi_id or _goi_cua_tenant_tho(tenant_id)["id"]
    if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (goi_id,)):
        raise LoiGoi(f"gói {goi_id!r} không tồn tại", 404)
    pb = int(phien_ban) if phien_ban else phien_ban_moi_nhat(goi_id)
    doc_phien_ban(goi_id, pb)
    ky = csdl.thang_nay()
    with csdl.khoa_ghi:
        kn = csdl.mo()
        cur = kn.execute(
            "INSERT INTO dang_ky (tenant_id, goi_id, goi_phien_ban, trang_thai, ky_bat_dau,"
            " tao_luc) VALUES (?,?,?,'dang_hoat_dong',?,?)",
            (tenant_id, goi_id, pb, ky, csdl.bay_gio()))
        dk_id = cur.lastrowid
        kn.commit()
    _dong_bo_tenant_goi(tenant_id, goi_id)
    _ghi_lich_su(tenant_id, dk_id, "kich_hoat", None, None, goi_id, pb, ly_do=ly_do, boi=boi)
    ghi_nhat_ky(tenant_id, ky, "kich_hoat_dang_ky", f"{goi_id} v{pb}", boi=boi)
    return dict(csdl.mot("SELECT * FROM dang_ky WHERE id=?", (dk_id,)))


def _dong_bo_tenant_goi(tenant_id, goi_id):
    """Đồng bộ `tenants.goi_id` theo đăng ký. KHÔNG phải tuỳ chọn — là chỗ chống lệch.

    ĐO ĐƯỢC ngày 15/10/2026 khi viết ca `test_c4`: `billing.kiem_han_muc_nhan_vien`,
    `kiem_va_tang_don`, `kiem_va_tang_ai`, `kiem_han_muc_tai_khoan_hang` đều lấy gói qua
    `billing.goi_cua_tenant`, tức là qua `tenants.goi_id` — **không** qua `dang_ky`. Nếu
    `doi_goi` chỉ sửa `dang_ky` thì hạ gói trên giấy mà chốt chặn thật vẫn dùng gói cũ: đổi
    gói "thành công" mà không chặn thêm gì, và không ai thấy sai vì không có thông báo lỗi
    nào. Đúng họ hỏng im lặng "hai thứ giống nhau mà lệch" (CLAUDE.md §12.2).

    Vì vậy đăng ký và `tenants.goi_id` phải nói CÙNG MỘT câu. Ghi vào `tenants` là ghi một
    DÒNG DỮ LIỆU (đường mà `/api/v2/platform/tenants/{id}` đang dùng), không phải sửa file
    của người khác, và KHÔNG chạm `goi_dich_vu` (§19).

    Còn một khe CHƯA bịt được từ đây: `billing.goi_cua_tenant` đọc hạn mức HIỆN TẠI của gói
    trong `goi_dich_vu`, nên nó không thấy PHIÊN BẢN đã ghim. Phát hành phiên bản mới rồi
    sửa `goi_dich_vu` thì chốt chặn của `billing` sẽ dùng số mới cho tenant ghim số cũ. Bịt
    chỗ đó phải sửa `app/billing.py` (AG-00 giữ) — bản vá đề xuất nằm trong
    `docs/G08_FINAL_REPORT.md`. Ghi ra để không ai tưởng đã phủ hết.
    """
    csdl.ghi("UPDATE tenants SET goi_id=?, cap_nhat_luc=? WHERE id=? AND goi_id<>?",
             (goi_id, csdl.bay_gio(), tenant_id, goi_id))


def doi_soat_goi(tenant_id) -> dict:
    """So `tenants.goi_id` với `dang_ky.goi_id` — hai phép đo độc lập, không tự sửa.

    `lech=True` nghĩa là có đường nào đổi gói mà không đi qua G08 (ví dụ route platform
    `PUT /api/v2/platform/tenants/{id}` đang `UPDATE tenants SET goi_id` trực tiếp). Hàm này
    chỉ BÁO; sửa im lặng là che mất nguyên nhân (§12.1).
    """
    _dam_bao_bang()
    t = csdl.mot("SELECT goi_id FROM tenants WHERE id=?", (tenant_id,))
    dk = dang_ky_hien_tai(tenant_id)
    return {"tenant_id": tenant_id,
            "tenants_goi_id": t["goi_id"] if t else None,
            "dang_ky_goi_id": dk["goi_id"] if dk else None,
            "dang_ky_phien_ban": dk["goi_phien_ban"] if dk else None,
            "lech": bool(dk and t and dk["goi_id"] != t["goi_id"]),
            "ghi_chu": "chưa có đăng ký thì không coi là lệch" if not dk else ""}


def _ghi_lich_su(tenant_id, dk_id, loai, tu_goi, tu_pb, den_goi, den_pb,
                 tu_gia=None, den_gia=None, vuot_json=None, ly_do="", boi=None):
    csdl.ghi("INSERT INTO dang_ky_lich_su (tenant_id, dang_ky_id, loai, tu_goi, tu_phien_ban,"
             " den_goi, den_phien_ban, tu_gia_dong, den_gia_dong, vuot_json, ly_do, boi, luc)"
             " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
             (tenant_id, dk_id, loai, tu_goi, tu_pb, den_goi, den_pb, tu_gia, den_gia,
              vuot_json, ly_do, boi, csdl.bay_gio()))


def lich_su(tenant_id) -> list:
    _dam_bao_bang()
    return [dict(r) for r in csdl.nhieu(
        "SELECT * FROM dang_ky_lich_su WHERE tenant_id=? ORDER BY id", (tenant_id,))]


def ghi_nhat_ky(tenant_id, ky, hanh_dong, chi_tiet="", ket_qua="thanh_cong", boi=None):
    _dam_bao_bang()
    csdl.ghi("INSERT INTO nhat_ky_tinh_phi (tenant_id, ky, hanh_dong, ket_qua, chi_tiet, boi, luc)"
             " VALUES (?,?,?,?,?,?,?)",
             (tenant_id, ky, hanh_dong, ket_qua, chi_tiet, boi, csdl.bay_gio()))


def nhat_ky(tenant_id=None, gioi_han_dong=200) -> list:
    _dam_bao_bang()
    if tenant_id is None:
        return [dict(r) for r in csdl.nhieu(
            "SELECT * FROM nhat_ky_tinh_phi ORDER BY id DESC LIMIT ?", (gioi_han_dong,))]
    return [dict(r) for r in csdl.nhieu(
        "SELECT * FROM nhat_ky_tinh_phi WHERE tenant_id=? ORDER BY id DESC LIMIT ?",
        (tenant_id, gioi_han_dong))]


def tam_ngung(tenant_id, ly_do="", boi=None) -> dict:
    """Tạm ngưng đăng ký. Mọi thao tác CÓ TÍNH PHÍ bị chặn; dữ liệu KHÔNG bị xoá."""
    dk = dang_ky_hien_tai(tenant_id) or kich_hoat(tenant_id, boi=boi)
    if dk["trang_thai"] == "tam_ngung":
        return dict(dk)
    csdl.ghi("UPDATE dang_ky SET trang_thai='tam_ngung', cap_nhat_luc=? WHERE id=?",
             (csdl.bay_gio(), dk["id"]))
    _ghi_lich_su(tenant_id, dk["id"], "tam_ngung", dk["goi_id"], dk["goi_phien_ban"],
                 dk["goi_id"], dk["goi_phien_ban"], ly_do=ly_do, boi=boi)
    ghi_nhat_ky(tenant_id, csdl.thang_nay(), "tam_ngung_dang_ky", ly_do, boi=boi)
    return dict(csdl.mot("SELECT * FROM dang_ky WHERE id=?", (dk["id"],)))


def mo_lai(tenant_id, ly_do="", boi=None) -> dict:
    dk = dang_ky_hien_tai(tenant_id)
    if not dk:
        raise LoiGoi(f"tenant {tenant_id} chưa có đăng ký nào để mở lại", 404)
    csdl.ghi("UPDATE dang_ky SET trang_thai='dang_hoat_dong', cap_nhat_luc=? WHERE id=?",
             (csdl.bay_gio(), dk["id"]))
    _ghi_lich_su(tenant_id, dk["id"], "mo_lai", dk["goi_id"], dk["goi_phien_ban"],
                 dk["goi_id"], dk["goi_phien_ban"], ly_do=ly_do, boi=boi)
    ghi_nhat_ky(tenant_id, csdl.thang_nay(), "mo_lai_dang_ky", ly_do, boi=boi)
    return dict(csdl.mot("SELECT * FROM dang_ky WHERE id=?", (dk["id"],)))


def dang_hoat_dong(tenant_id) -> bool:
    """True nếu tenant được phép phát sinh thao tác có tính phí.

    Tenant CHƯA có dòng `dang_ky` vẫn được coi là hoạt động — nếu không thì đợt này sẽ khoá
    mọi tenant có từ trước, mà không ai yêu cầu điều đó. Chỉ `tam_ngung`/`da_huy` mới chặn.
    """
    dk = dang_ky_hien_tai(tenant_id)
    if dk is None:
        return True
    return dk["trang_thai"] == "dang_hoat_dong"


# ---------------------------------------------------------------------------------------
# A.4 — HẠN MỨC HIỆU LỰC
#
# `nguon_dem` nói BỘ ĐẾM nằm ở đâu. Đây là chỗ chặn "hai bộ đếm cho một việc":
#   billing       → `usage_thang` của `app/billing.py` (AG-00 giữ) — G08 ĐỌC, không đếm lại.
#   gioi_han      → `han_muc_nhap_thang` của `app/gioi_han.py` (AG-01) — G08 ĐỌC qua hàm của nó.
#   dem_truc_tiep → đếm thẳng từ bảng nghiệp vụ (nhân viên, kết nối hãng) — không có bộ đếm nào.
#   g08           → `bo_dem_dung` của chính file này, CHỈ cho loại chưa ai đếm.
# ---------------------------------------------------------------------------------------
LOAI_HAN_MUC = {
    "don_thang": {
        "ten": "Đơn gửi hãng mỗi tháng", "cot_goi": "han_muc_don_thang",
        "nguon_dem": "billing", "theo_ky": True},
    "ai_thang": {
        "ten": "Lượt AI mỗi tháng", "cot_goi": "han_muc_ai_thang",
        "nguon_dem": "billing", "theo_ky": True},
    "nhan_vien": {
        "ten": "Tài khoản nhân viên", "cot_goi": "so_nhan_vien",
        "nguon_dem": "dem_truc_tiep", "theo_ky": False},
    "tai_khoan_hang": {
        "ten": "Kết nối tài khoản hãng", "cot_goi": "so_tai_khoan_hang",
        "nguon_dem": "dem_truc_tiep", "theo_ky": False},
    "api_thang": {
        "ten": "Lượt gọi API mỗi tháng", "cot_goi": "han_muc_api_thang",
        "nguon_dem": "g08", "theo_ky": True},
    "file_nhap_thang": {
        "ten": "File import mỗi tháng", "cot_goi": None,
        "nguon_dem": "gioi_han", "theo_ky": True},
    "dong_nhap_thang": {
        "ten": "Dòng import mỗi tháng", "cot_goi": None,
        "nguon_dem": "gioi_han", "theo_ky": True},
    "byte_luu_tru_thang": {
        "ten": "Dung lượng file nhập mỗi tháng (byte)", "cot_goi": None,
        "nguon_dem": "gioi_han", "theo_ky": True},
}
# Loại mà `bo_dem_dung` của G08 được phép cộng. Danh sách TRẮNG cố ý: quên một dòng ở đây thì
# loại đó không đếm được (mất tiện), còn dùng danh sách đen mà quên chặn `don_thang` thì G08
# đếm song song với `billing` và hai số lệch nhau im lặng (CLAUDE.md §12.2).
LOAI_DEM_G08 = tuple(k for k, v in LOAI_HAN_MUC.items() if v["nguon_dem"] == "g08")


def han_muc_hieu_luc(tenant_id) -> dict:
    """Hạn mức ĐANG áp cho tenant này, kèm nguồn của từng con số.

    Thứ tự: ảnh chụp phiên bản gói đã ghim → hạn mức riêng của tenant (nếu có).
    Tenant chưa có `dang_ky` thì đọc `goi_dich_vu` qua `tenants.goi_id` (phiên bản mới nhất)
    — nói rõ `tu_dang_ky=False` để người đọc biết con số này CHƯA được ghim.
    """
    _dam_bao_bang()
    dk = dang_ky_hien_tai(tenant_id)
    if dk:
        anh = doc_phien_ban(dk["goi_id"], dk["goi_phien_ban"])
        tu_dang_ky, trang_thai = True, dk["trang_thai"]
    else:
        g = _goi_cua_tenant_tho(tenant_id)
        anh = doc_phien_ban(g["id"], phien_ban_moi_nhat(g["id"]))
        tu_dang_ky, trang_thai = False, "chua_dang_ky"
    rieng = {r["loai"]: int(r["gia_tri"]) for r in csdl.nhieu(
        "SELECT loai, gia_tri FROM han_muc_rieng WHERE tenant_id=?", (tenant_id,))}
    tran = {}
    for loai, mo_ta in LOAI_HAN_MUC.items():
        cot = mo_ta["cot_goi"]
        if loai in rieng:
            gia_tri, nguon = rieng[loai], "han_muc_rieng"
        elif cot:
            gia_tri, nguon = int(anh[cot]), f"goi_phien_ban:{anh['goi_id']}v{anh['phien_ban']}"
        else:
            gia_tri, nguon = None, "gioi_han.tran_cua"     # trần do module khác quyết
        tran[loai] = {"gia_tri": gia_tri, "nguon": nguon, "ten": mo_ta["ten"],
                      "nguon_dem": mo_ta["nguon_dem"], "theo_ky": mo_ta["theo_ky"]}
    return {"tenant_id": tenant_id, "goi_id": anh["goi_id"], "goi_ten": anh["ten"],
            "phien_ban": anh["phien_ban"], "gia_thang_dong": int(anh["gia_thang_dong"]),
            "tu_dang_ky": tu_dang_ky, "trang_thai": trang_thai, "tran": tran,
            "han_muc_rieng": rieng}


def tran_cua_loai(tenant_id, loai) -> int:
    """Trần của MỘT loại, đã quy về số nguyên dùng được trong `WHERE`. 0 ⇒ không áp trần."""
    if loai not in LOAI_HAN_MUC:
        raise LoiGoi(f"loại hạn mức lạ: {loai!r}; chỉ nhận {sorted(LOAI_HAN_MUC)}", 400)
    hm = han_muc_hieu_luc(tenant_id)["tran"][loai]
    gt = hm["gia_tri"]
    if gt is None:
        raise LoiGoi(f"trần của {loai!r} do {hm['nguon']} quyết — không đọc ở G08", 400)
    return GIA_TRI_KHONG_TRAN if gt == 0 else int(gt)


def dat_han_muc_rieng(tenant_id, loai, gia_tri, ly_do="", boi=None) -> dict:
    """Đặt hạn mức riêng cho một tenant. Chỉ dùng cho loại có trần ở G08."""
    _dam_bao_bang()
    if loai not in LOAI_HAN_MUC:
        raise LoiGoi(f"loại hạn mức lạ: {loai!r}", 400)
    if LOAI_HAN_MUC[loai]["cot_goi"] is None:
        raise LoiGoi(f"{loai!r} không có trần ở G08 (do gioi_han quyết)", 400)
    gia_tri = int(gia_tri)
    if gia_tri < 0:
        raise LoiGoi("hạn mức riêng không được âm", 400)
    csdl.ghi("INSERT INTO han_muc_rieng (tenant_id, loai, gia_tri, ly_do, boi, luc)"
             " VALUES (?,?,?,?,?,?) ON CONFLICT(tenant_id, loai) DO UPDATE SET"
             " gia_tri=excluded.gia_tri, ly_do=excluded.ly_do, boi=excluded.boi, luc=excluded.luc",
             (tenant_id, loai, gia_tri, ly_do, boi, csdl.bay_gio()))
    ghi_nhat_ky(tenant_id, csdl.thang_nay(), "dat_han_muc_rieng", f"{loai}={gia_tri}", boi=boi)
    return han_muc_hieu_luc(tenant_id)


# ---------------------------------------------------------------------------------------
# A.5 — ĐỔI GÓI (nâng / hạ / chuyển phiên bản)
# ---------------------------------------------------------------------------------------
def _muc_dang_dung(tenant_id) -> dict:
    """Mức đang dùng của những loại có trần ở G08. Gọi `usage` muộn để tránh nhập vòng."""
    import usage
    return usage.muc_dang_dung(tenant_id)


def so_sanh_voi_phien_ban(tenant_id, goi_id, phien_ban) -> dict:
    """Mức đang dùng so với hạn mức của (gói, phiên bản) đích. Không ghi gì."""
    anh = doc_phien_ban(goi_id, phien_ban)
    dung = _muc_dang_dung(tenant_id)
    vuot = {}
    for loai, mo_ta in LOAI_HAN_MUC.items():
        cot = mo_ta["cot_goi"]
        if not cot or loai not in dung:
            continue
        tran = int(anh[cot])
        if tran == 0:
            continue                       # 0 = không áp trần
        if dung[loai] > tran:
            vuot[loai] = {"ten": mo_ta["ten"], "dang_dung": dung[loai], "tran_moi": tran}
    return {"goi_id": goi_id, "phien_ban": phien_ban, "dang_dung": dung, "vuot": vuot}


def doi_goi(tenant_id, goi_id_moi, phien_ban=None, boi=None, ly_do="",
            cho_phep_vuot=False) -> dict:
    """Nâng hoặc hạ gói. KHÔNG trừ tiền, KHÔNG xoá dữ liệu vượt hạn mức.

    Phần kỳ dở dang (prorate): KHÔNG thu thêm và KHÔNG hoàn tiền tự động. Dự thảo của kỳ
    đang dở được CHIA THEO NGÀY giữa gói cũ và gói mới (xem `usage.tinh_phi`), nên số tiền
    trên dự thảo phản ánh đúng số ngày từng gói có hiệu lực. Chỉ dự thảo — ai thu, thu bằng
    gì, do anh Thành quyết; G08 không nối cổng thanh toán.

    Hạ gói khi mức dùng ĐÃ vượt hạn mức gói mới:
      - mặc định CHẶN (`HaGoiVuotHanMuc`) và nói rõ vượt cái gì;
      - `cho_phep_vuot=True` thì vẫn hạ, GHI phần vượt vào `dang_ky_lich_su.vuot_json`, và
        **không xoá một dòng dữ liệu nào**. Phần vượt tự nguội theo kỳ: bộ đếm đang lớn hơn
        trần nên câu `UPDATE ... WHERE so_luong+? <= tran` sẽ không cộng thêm được cho tới
        kỳ sau. Nhân viên / kết nối hãng vượt số thì bị chặn THÊM MỚI, không ai bị gỡ.
    """
    import json
    _dam_bao_bang()
    if not csdl.mot("SELECT id FROM goi_dich_vu WHERE id=?", (goi_id_moi,)):
        raise LoiGoi(f"gói {goi_id_moi!r} không tồn tại", 404)
    pb_moi = int(phien_ban) if phien_ban else phien_ban_moi_nhat(goi_id_moi)
    anh_moi = doc_phien_ban(goi_id_moi, pb_moi)
    dk = dang_ky_hien_tai(tenant_id) or kich_hoat(tenant_id, boi=boi)
    anh_cu = doc_phien_ban(dk["goi_id"], dk["goi_phien_ban"])
    if dk["goi_id"] == goi_id_moi and dk["goi_phien_ban"] == pb_moi:
        raise LoiGoi(f"tenant {tenant_id} đã ở {goi_id_moi} v{pb_moi}", 409)

    ss = so_sanh_voi_phien_ban(tenant_id, goi_id_moi, pb_moi)
    la_ha = int(anh_moi["gia_thang_dong"]) < int(anh_cu["gia_thang_dong"])
    if ss["vuot"] and not cho_phep_vuot:
        ten = ", ".join(f"{v['ten']} {v['dang_dung']}>{v['tran_moi']}"
                        for v in ss["vuot"].values())
        raise HaGoiVuotHanMuc(
            f"đang dùng vượt hạn mức của {anh_moi['ten']} v{pb_moi}: {ten}."
            " Giảm mức dùng, hoặc gọi lại với cho_phep_vuot=True (dữ liệu KHÔNG bị xoá).",
            ss["vuot"])
    if dk["goi_id"] == goi_id_moi:
        loai = "doi_phien_ban"
    else:
        loai = "ha_goi" if la_ha else "nang_goi"
    csdl.ghi("UPDATE dang_ky SET goi_id=?, goi_phien_ban=?, cap_nhat_luc=? WHERE id=?",
             (goi_id_moi, pb_moi, csdl.bay_gio(), dk["id"]))
    _dong_bo_tenant_goi(tenant_id, goi_id_moi)      # xem docstring của hàm đó — chống lệch
    _ghi_lich_su(tenant_id, dk["id"], loai, dk["goi_id"], dk["goi_phien_ban"],
                 goi_id_moi, pb_moi, int(anh_cu["gia_thang_dong"]),
                 int(anh_moi["gia_thang_dong"]),
                 vuot_json=json.dumps(ss["vuot"], ensure_ascii=False) if ss["vuot"] else None,
                 ly_do=ly_do, boi=boi)
    ghi_nhat_ky(tenant_id, csdl.thang_nay(), loai,
                f"{dk['goi_id']} v{dk['goi_phien_ban']} → {goi_id_moi} v{pb_moi}", boi=boi)
    return {"dang_ky": dict(csdl.mot("SELECT * FROM dang_ky WHERE id=?", (dk["id"],))),
            "loai": loai, "vuot_van_giu": ss["vuot"],
            "ghi_chu": "không trừ tiền, không xoá dữ liệu; kỳ dở dang chia theo ngày trên dự thảo"}


def chuyen_phien_ban(tenant_id, phien_ban=None, boi=None, ly_do="", cho_phep_vuot=False) -> dict:
    """Chuyển tenant sang phiên bản khác của ĐÚNG gói đang dùng. Hành động RIÊNG, có ghi vết."""
    dk = dang_ky_hien_tai(tenant_id) or kich_hoat(tenant_id, boi=boi)
    pb = int(phien_ban) if phien_ban else phien_ban_moi_nhat(dk["goi_id"])
    return doi_goi(tenant_id, dk["goi_id"], pb, boi=boi, ly_do=ly_do,
                   cho_phep_vuot=cho_phep_vuot)


# ---------------------------------------------------------------------------------------
# A.6 — CHIA TIỀN. §16: INTEGER đồng, dùng `//`, phần dư phải có chỗ đi.
# ---------------------------------------------------------------------------------------
def chia_tien_theo_ngay(gia_thang_dong, so_ngay, so_ngay_ky):
    """Phần tiền của `so_ngay` ngày trong kỳ `so_ngay_ky` ngày.

    Trả `(so_tien_dong, phan_du)` với bất biến **so_tien*so_ngay_ky + phan_du == gia*so_ngay**.
    Phần dư KHÔNG biến mất: nó được trả ra để người gọi ghi vào `phan_du_bo_dong` của dự thảo.
    Có ca thử canh bất biến này trên nhiều bộ số.
    """
    gia_thang_dong, so_ngay, so_ngay_ky = int(gia_thang_dong), int(so_ngay), int(so_ngay_ky)
    if so_ngay_ky <= 0:
        raise LoiGoi("số ngày trong kỳ phải > 0", 400)
    if so_ngay < 0 or gia_thang_dong < 0:
        raise LoiGoi("số ngày và giá không được âm", 400)
    tong = gia_thang_dong * so_ngay
    return tong // so_ngay_ky, tong % so_ngay_ky


def chia_deu(tong_dong, so_phan) -> list:
    """Chia `tong_dong` thành `so_phan` phần INTEGER sao cho TỔNG BẰNG ĐÚNG `tong_dong`.

    Phần dư rải vào các phần ĐẦU, mỗi phần 1 đồng — ghi rõ ở đây để không ai phải đoán phần
    dư đi đâu (§16: "không bao giờ để phần dư biến mất").
    """
    tong_dong, so_phan = int(tong_dong), int(so_phan)
    if so_phan <= 0:
        raise LoiGoi("số phần phải > 0", 400)
    co_ban, du = divmod(tong_dong, so_phan)
    return [co_ban + (1 if i < du else 0) for i in range(so_phan)]
