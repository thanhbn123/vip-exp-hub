# CSDL SQLite của Multi-Tenant SaaS. CSDL riêng (hub.db) — KHÔNG đụng gateway/du-lieu/gateway.db.
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta

import cau_hinh

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


SCHEMA = """
CREATE TABLE IF NOT EXISTS goi_dich_vu (
  id TEXT PRIMARY KEY, ten TEXT NOT NULL, gia_thang INTEGER NOT NULL,
  han_muc_don_thang INTEGER NOT NULL, han_muc_ai_thang INTEGER NOT NULL,
  so_nhan_vien INTEGER NOT NULL, so_tai_khoan_hang INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS tenants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ten TEXT NOT NULL,
  goi_id TEXT NOT NULL REFERENCES goi_dich_vu(id),
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',   -- hoat_dong | khoa
  tao_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER REFERENCES tenants(id),        -- NULL = người của nền tảng
  ten_dang_nhap TEXT NOT NULL UNIQUE,
  mat_khau_hash TEXT NOT NULL,                     -- pbkdf2$vòng$salt$hash
  ho_ten TEXT NOT NULL,
  vai_tro TEXT NOT NULL,
  trang_thai TEXT NOT NULL DEFAULT 'hoat_dong',    -- hoat_dong | khoa
  so_lan_sai INTEGER NOT NULL DEFAULT 0,
  tao_luc TEXT NOT NULL,
  doi_mat_khau_luc TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,                     -- SHA-256 của token; token gốc không lưu
  user_id INTEGER NOT NULL REFERENCES users(id),
  tao_luc TEXT NOT NULL,
  het_han TEXT NOT NULL,
  thu_hoi INTEGER NOT NULL DEFAULT 0,
  dia_chi TEXT
);
CREATE TABLE IF NOT EXISTS khach_hang (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ten TEXT NOT NULL, sdt TEXT, dia_chi TEXT, ghi_chu TEXT,
  tao_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS carrier_accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  hang TEXT NOT NULL,                              -- vtp | jt | ...
  ten TEXT NOT NULL,
  moi_truong TEXT NOT NULL DEFAULT 'mock',         -- mock | sandbox | production (prod khóa ở local)
  credentials_ma_hoa TEXT NOT NULL,                -- JSON mã hóa (bao_mat.ma_hoa)
  credentials_duoi TEXT NOT NULL DEFAULT '',       -- 4 ký tự cuối để hiển thị
  webhook_ma TEXT NOT NULL,                        -- định danh công khai trên URL webhook
  webhook_secret_ma_hoa TEXT NOT NULL,
  kich_hoat INTEGER NOT NULL DEFAULT 1,
  tao_luc TEXT NOT NULL,
  UNIQUE (webhook_ma)
);
CREATE TABLE IF NOT EXISTS don_hang (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ma_don TEXT NOT NULL,                            -- mã nội bộ, duy nhất trong tenant
  idem_key TEXT,                                   -- khóa idempotency client gửi
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
  can_doi_soat_ket_qua INTEGER NOT NULL DEFAULT 0, -- 1 khi gửi hãng timeout, phải getOrder kiểm lại
  trang_thai_giao TEXT,                            -- cho_lay... (từ webhook, tách riêng)
  hang_trang_thai_giao INTEGER NOT NULL DEFAULT 0,
  nguoi_tao INTEGER NOT NULL REFERENCES users(id),
  tao_luc TEXT NOT NULL, cap_nhat_luc TEXT NOT NULL,
  UNIQUE (tenant_id, ma_don),
  UNIQUE (tenant_id, idem_key)                     -- idempotency cưỡng chế bằng CSDL
);
CREATE TABLE IF NOT EXISTS don_lich_su (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  don_id INTEGER NOT NULL REFERENCES don_hang(id),
  luc TEXT NOT NULL, nguon TEXT NOT NULL,          -- user:<id> | webhook:<sk_id> | he_thong
  noi_dung TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS wh_su_kien (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  carrier_account_id INTEGER NOT NULL REFERENCES carrier_accounts(id),
  event_id TEXT NOT NULL,
  payload_tho BLOB NOT NULL, headers_json TEXT NOT NULL,
  nhan_luc TEXT NOT NULL,
  trang_thai TEXT NOT NULL DEFAULT 'moi',          -- moi|dang_xu_ly|xong|cho_thu_lai|dlq|khong_khop
  so_lan_thu INTEGER NOT NULL DEFAULT 0, loi_cuoi TEXT, xu_ly_xong_luc TEXT,
  UNIQUE (carrier_account_id, event_id)            -- chống trùng + replay cưỡng chế bằng CSDL
);
CREATE TABLE IF NOT EXISTS import_batch (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id),
  ten_file TEXT NOT NULL, loai_file TEXT NOT NULL,
  trang_thai TEXT NOT NULL DEFAULT 'moi',          -- moi | da_duyet_mot_phan | xong
  nguoi_tao INTEGER NOT NULL REFERENCES users(id), tao_luc TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS import_dong (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES import_batch(id),
  stt INTEGER NOT NULL,
  du_lieu_json TEXT NOT NULL,
  trang_thai TEXT NOT NULL,                        -- VALID|INVALID|READY|SUBMITTED|SUCCESS|FAILED
  loi TEXT,
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
  tenant_id INTEGER,                               -- NULL = cấp nền tảng
  user_id INTEGER,
  hanh_dong TEXT NOT NULL, doi_tuong TEXT NOT NULL, chi_tiet TEXT, dia_chi TEXT
);
"""


def _khoi_tao_schema():
    """Tạo schema + seed gói MỘT lần (dùng một kết nối tạm). An toàn khi nhiều thread cùng gọi."""
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


def audit(hanh_dong, doi_tuong, chi_tiet="", tenant_id=None, user_id=None, dia_chi=None):
    ghi("INSERT INTO audit (luc, tenant_id, user_id, hanh_dong, doi_tuong, chi_tiet, dia_chi) VALUES (?,?,?,?,?,?,?)",
        (bay_gio(), tenant_id, user_id, hanh_dong, doi_tuong, chi_tiet, dia_chi))
