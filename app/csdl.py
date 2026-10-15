# CSDL SQLite của Multi-Tenant SaaS (schema v2). CSDL riêng (hub.db) — KHÔNG đụng gateway/du-lieu/gateway.db.
# v2 đổi lõi quyền: user ↔ NHIỀU tenant qua tenant_memberships; quyền lưu trong CSDL (roles/permissions).
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta

import cau_hinh

PHIEN_BAN_SCHEMA = 8

MUI_GIO_VN = timezone(timedelta(hours=7))
khoa_ghi = threading.RLock()   # serialize mọi lượt GHI (WAL: một writer tại một thời điểm)
# Mỗi THREAD một kết nối SQLite riêng. Dùng chung một connection giữa các thread
# (dù check_same_thread=False) làm các truy vấn đồng thời giẫm lên nhau → trả về byte rác
# (đã gặp: UnicodeDecodeError 0x80 khi dashboard gọi 2 API song song). Đây là cách an toàn chuẩn.
_local = threading.local()
_da_khoi_tao = threading.Event()
_khoa_khoi_tao = threading.Lock()


def bay_gio():
    return datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S%z")


def thang_nay():
    return datetime.now(MUI_GIO_VN).strftime("%Y-%m")


# Bảng nghiệp vụ dùng tên tiếng Việt (giữ nguyên từ bản trước để không phá mã đang chạy).
# Ánh xạ sang tên trong brief: users=users · tenants=tenants · tenant_memberships=tenant_memberships
# roles/permissions/role_permissions · user_sessions=sessions · customers=khach_hang
# carrier_providers=carrier_providers · carrier_accounts=carrier_accounts · orders=don_hang
# order_events=don_lich_su · audit_logs=audit.
SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
  phien_ban INTEGER PRIMARY KEY,
  ap_dung_luc TEXT NOT NULL,
  ghi_chu TEXT
);
CREATE TABLE IF NOT EXISTS goi_dich_vu (
  id TEXT PRIMARY KEY, ten TEXT NOT NULL, gia_thang INTEGER NOT NULL,
  han_muc_don_thang INTEGER NOT NULL, han_muc_ai_thang INTEGER NOT NULL,
  so_nhan_vien INTEGER NOT NULL, so_tai_khoan_hang INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tenants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE,
  ten TEXT NOT NULL,
  goi_id TEXT NOT NULL REFERENCES goi_dich_vu(id),
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',   -- hoat_dong | khoa
  tao_luc TEXT NOT NULL,
  cap_nhat_luc TEXT
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ten_dang_nhap TEXT NOT NULL UNIQUE,
  mat_khau_hash TEXT NOT NULL,
  ho_ten TEXT NOT NULL,
  platform_role TEXT,                              -- NULL = người thường; PLATFORM_OWNER/PLATFORM_ADMIN
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',    -- hoat_dong | khoa (do QUẢN TRỊ khóa)
  so_lan_sai INTEGER NOT NULL DEFAULT 0,
  khoa_den TEXT,                                   -- khóa TẠM do đoán sai; hết giờ tự mở
  tao_luc TEXT NOT NULL,
  doi_mat_khau_luc TEXT
);
-- Một user thuộc NHIỀU tenant. Vai trò trong tenant nằm ở đây, không nằm ở users.
CREATE TABLE IF NOT EXISTS tenant_memberships (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id),
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  role TEXT NOT NULL REFERENCES roles(ma),
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',    -- hoat_dong | vo_hieu
  moi_boi INTEGER REFERENCES users(id),
  tao_luc TEXT NOT NULL,
  UNIQUE (user_id, tenant_id)
);
CREATE INDEX IF NOT EXISTS ix_mem_user ON tenant_memberships(user_id, trang_thai);
CREATE INDEX IF NOT EXISTS ix_mem_tenant ON tenant_memberships(tenant_id, trang_thai);
CREATE TABLE IF NOT EXISTS roles (
  ma TEXT PRIMARY KEY, ten TEXT NOT NULL,
  pham_vi TEXT NOT NULL                            -- platform | tenant
);
CREATE TABLE IF NOT EXISTS permissions (
  ma TEXT PRIMARY KEY, mo_ta TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS role_permissions (
  role_ma TEXT NOT NULL REFERENCES roles(ma),
  perm_ma TEXT NOT NULL REFERENCES permissions(ma),
  PRIMARY KEY (role_ma, perm_ma)
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,                     -- SHA-256 của token; token gốc không lưu
  user_id INTEGER NOT NULL REFERENCES users(id),
  active_tenant_id INTEGER REFERENCES tenants(id), -- tenant đang thao tác (đổi bằng switch-tenant)
  tao_luc TEXT NOT NULL,
  het_han TEXT NOT NULL,
  thu_hoi INTEGER NOT NULL DEFAULT 0,
  dia_chi TEXT
);
CREATE INDEX IF NOT EXISTS ix_session_user ON sessions(user_id, thu_hoi);
CREATE TABLE IF NOT EXISTS reset_tokens (
  token_hash TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id),
  het_han TEXT NOT NULL,
  da_dung INTEGER NOT NULL DEFAULT 0,
  tao_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS khach_hang (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ten TEXT NOT NULL, sdt TEXT, dia_chi TEXT, ghi_chu TEXT,
  tao_luc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_khach_tenant ON khach_hang(tenant_id);
CREATE TABLE IF NOT EXISTS carrier_providers (
  ma TEXT PRIMARY KEY, ten TEXT NOT NULL,
  capabilities_json TEXT NOT NULL,
  live_mo INTEGER NOT NULL DEFAULT 0,
  cap_nhat_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS carrier_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  hang TEXT NOT NULL REFERENCES carrier_providers(ma),
  ten TEXT NOT NULL,
  moi_truong TEXT NOT NULL DEFAULT 'mock',         -- mock | sandbox | production (prod khóa ở local)
  credentials_ma_hoa TEXT NOT NULL,                -- JSON mã hóa (bao_mat.ma_hoa)
  credentials_duoi TEXT NOT NULL DEFAULT '',       -- 4 ký tự cuối để hiển thị
  credentials_doi_luc TEXT,                        -- lần rotate gần nhất
  webhook_ma TEXT NOT NULL,                        -- định danh công khai trên URL webhook
  webhook_secret_ma_hoa TEXT NOT NULL,
  kich_hoat INTEGER NOT NULL DEFAULT 1,            -- 1=ACTIVE, 0=DISABLED
  tao_luc TEXT NOT NULL,
  UNIQUE (webhook_ma)
);
CREATE INDEX IF NOT EXISTS ix_ca_tenant ON carrier_accounts(tenant_id, kich_hoat);
CREATE TABLE IF NOT EXISTS don_hang (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ma_don TEXT NOT NULL,
  idem_key TEXT,
  khach_hang_id INTEGER REFERENCES khach_hang(id),
  nguoi_gui_ten TEXT NOT NULL, nguoi_gui_sdt TEXT NOT NULL, nguoi_gui_dia_chi TEXT NOT NULL,
  nguoi_nhan_ten TEXT NOT NULL, nguoi_nhan_sdt TEXT NOT NULL, nguoi_nhan_dia_chi TEXT NOT NULL,
  hang_hoa TEXT NOT NULL, khoi_luong_gram INTEGER NOT NULL,
  cod INTEGER NOT NULL DEFAULT 0, gia_tri_khai INTEGER NOT NULL DEFAULT 0,
  phi_van_chuyen INTEGER,
  ghi_chu TEXT,
  carrier_account_id INTEGER REFERENCES carrier_accounts(id),
  ma_van_don TEXT,
  trang_thai TEXT NOT NULL DEFAULT 'nhap',         -- nhap | da_duyet | dang_gui | da_gui | huy
  can_doi_soat_ket_qua INTEGER NOT NULL DEFAULT 0,
  trang_thai_giao TEXT,
  hang_trang_thai_giao INTEGER NOT NULL DEFAULT 0,
  nguoi_tao INTEGER NOT NULL REFERENCES users(id),
  tao_luc TEXT NOT NULL, cap_nhat_luc TEXT NOT NULL,
  UNIQUE (tenant_id, ma_don),
  UNIQUE (tenant_id, idem_key)
);
CREATE INDEX IF NOT EXISTS ix_don_tenant ON don_hang(tenant_id, trang_thai);
CREATE INDEX IF NOT EXISTS ix_don_mvd ON don_hang(ma_van_don);
CREATE TABLE IF NOT EXISTS don_lich_su (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  don_id INTEGER NOT NULL REFERENCES don_hang(id),
  luc TEXT NOT NULL, nguon TEXT NOT NULL,
  noi_dung TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ls_don ON don_lich_su(don_id);
CREATE TABLE IF NOT EXISTS wh_su_kien (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  carrier_account_id INTEGER NOT NULL REFERENCES carrier_accounts(id),
  event_id TEXT NOT NULL,
  payload_tho BLOB NOT NULL, headers_json TEXT NOT NULL,
  nhan_luc TEXT NOT NULL,
  trang_thai TEXT NOT NULL DEFAULT 'moi',
  so_lan_thu INTEGER NOT NULL DEFAULT 0, loi_cuoi TEXT, xu_ly_xong_luc TEXT,
  UNIQUE (carrier_account_id, event_id)
);
CREATE TABLE IF NOT EXISTS import_batch (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ten_file TEXT NOT NULL, loai_file TEXT NOT NULL,
  -- UPLOADED PARSING VALIDATING READY APPROVED PROCESSING COMPLETED PARTIAL_FAILED FAILED
  -- (SHARED_CONTRACTS mục 6). Giá trị cũ 'moi'/'da_duyet_mot_phan'/'xong' vẫn ĐỌC được
  -- qua nhap_file.trang_thai_batch() — không cần migrate dữ liệu để mã chạy.
  trang_thai TEXT NOT NULL DEFAULT 'UPLOADED',
  loi TEXT,                                        -- lý do khi batch ở FAILED
  nguoi_tao INTEGER NOT NULL REFERENCES users(id), tao_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS import_dong (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES import_batch(id),
  stt INTEGER NOT NULL,
  du_lieu_json TEXT NOT NULL,
  -- VALID INVALID READY SUBMITTED SUCCESS FAILED UNSUPPORTED NEEDS_REVIEW
  trang_thai TEXT NOT NULL,
  loi TEXT,                                        -- lỗi chặn HOẶC cảnh báo 'cần xem: ...'
  don_id INTEGER REFERENCES don_hang(id)
);
CREATE TABLE IF NOT EXISTS usage_thang (
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  thang TEXT NOT NULL,
  so_don INTEGER NOT NULL DEFAULT 0,
  so_ai INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant_id, thang)
);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  luc TEXT NOT NULL,
  tenant_id INTEGER,
  user_id INTEGER,                                 -- actor_id
  hanh_dong TEXT NOT NULL,                         -- action
  doi_tuong TEXT NOT NULL,                         -- "<resource_type>:<resource_id>"
  resource_type TEXT, resource_id TEXT,
  ket_qua TEXT NOT NULL DEFAULT 'thanh_cong',      -- thanh_cong | tu_choi | that_bai
  chi_tiet TEXT, dia_chi TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_tenant ON audit(tenant_id, id);
"""


def _khoi_tao_schema():
    """Tạo schema + seed MỘT lần (dùng một kết nối tạm). An toàn khi nhiều thread cùng gọi."""
    with _khoa_khoi_tao:
        if _da_khoi_tao.is_set():
            return
        os.makedirs(cau_hinh.THU_MUC_DU_LIEU, exist_ok=True)
        kn = sqlite3.connect(cau_hinh.DUONG_DAN_CSDL)
        try:
            kn.execute("PRAGMA journal_mode=WAL")
            kn.executescript(SCHEMA)
            for g in cau_hinh.GOI_MAC_DINH:
                kn.execute(
                    "INSERT OR IGNORE INTO goi_dich_vu (id,ten,gia_thang,han_muc_don_thang,han_muc_ai_thang,so_nhan_vien,so_tai_khoan_hang) "
                    "VALUES (:id,:ten,:gia_thang,:han_muc_don_thang,:han_muc_ai_thang,:so_nhan_vien,:so_tai_khoan_hang)", g)
            kn.commit()
        finally:
            kn.close()
        _da_khoi_tao.set()


def mo():
    """Trả kết nối RIÊNG của thread hiện tại (tạo nếu chưa có)."""
    if not _da_khoi_tao.is_set():
        _khoi_tao_schema()
    kn = getattr(_local, "kn", None)
    if kn is not None:
        return kn
    kn = sqlite3.connect(cau_hinh.DUONG_DAN_CSDL, timeout=10)
    kn.row_factory = sqlite3.Row
    kn.execute("PRAGMA journal_mode=WAL")
    kn.execute("PRAGMA foreign_keys=ON")
    kn.execute("PRAGMA busy_timeout=10000")
    _local.kn = kn
    return kn


def dong():
    """Đóng kết nối của thread hiện tại và cho phép khởi tạo lại (phục vụ bộ thử)."""
    kn = getattr(_local, "kn", None)
    if kn is not None:
        kn.close()
        _local.kn = None
    _da_khoi_tao.clear()


def phien_ban_hien_tai():
    """Phiên bản schema đang có trong CSDL (0 nếu chưa ghi nhận)."""
    r = mot("SELECT MAX(phien_ban) pb FROM schema_version")
    return (r["pb"] or 0) if r else 0


def ghi(sql, tham_so=()):
    kn = mo()
    with khoa_ghi:
        con = kn.execute(sql, tham_so)
        kn.commit()
        return con


def mot(sql, tham_so=()):
    return mo().execute(sql, tham_so).fetchone()


def nhieu(sql, tham_so=()):
    return mo().execute(sql, tham_so).fetchall()


def audit(hanh_dong, doi_tuong, chi_tiet="", tenant_id=None, user_id=None, dia_chi=None,
          ket_qua="thanh_cong"):
    """Ghi audit log. doi_tuong dạng '<resource_type>:<resource_id>' — tự tách thành 2 cột."""
    rt, _, rid = doi_tuong.partition(":")
    ghi("INSERT INTO audit (luc, tenant_id, user_id, hanh_dong, doi_tuong, resource_type, resource_id,"
        " ket_qua, chi_tiet, dia_chi) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (bay_gio(), tenant_id, user_id, hanh_dong, doi_tuong, rt or None, rid or None,
         ket_qua, chi_tiet, dia_chi))
