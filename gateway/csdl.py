# Lớp CSDL SQLite của gateway — lưu BỀN sự kiện thô trước, xử lý sau.
import json
import os
import sqlite3
import threading
from datetime import datetime, timezone, timedelta

from cau_hinh import DUONG_DAN_CSDL

MUI_GIO_VN = timezone(timedelta(hours=7))
_khoa = threading.RLock()        # serialize mọi lượt GHI
# Mỗi THREAD một kết nối SQLite riêng. Trước đây dùng CHUNG một connection giữa các thread
# (check_same_thread=False) — cách đó làm truy vấn đồng thời giẫm lên nhau: trong app/ nó trả
# byte rác, còn ở đây nó làm tiến trình CHẾT HẲN (SIGSEGV, đo được ~1/5 lượt chạy bộ thử
# ngày 14/10/2026). Sửa cấu trúc, không vá từng chỗ.
_local = threading.local()
_da_khoi_tao = threading.Event()
_khoa_khoi_tao = threading.Lock()

SCHEMA = """
    CREATE TABLE IF NOT EXISTS su_kien_tho (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      hang TEXT NOT NULL,
      event_id TEXT NOT NULL,
      payload_tho BLOB NOT NULL,
      headers_json TEXT NOT NULL,
      nhan_luc TEXT NOT NULL,
      trang_thai TEXT NOT NULL DEFAULT 'moi',  -- moi | dang_xu_ly | xong | cho_thu_lai | dlq
      so_lan_thu INTEGER NOT NULL DEFAULT 0,
      loi_cuoi TEXT,
      xu_ly_xong_luc TEXT,
      UNIQUE (hang, event_id)                  -- idempotency cưỡng chế bằng CSDL, không bằng Python
    );
    CREATE TABLE IF NOT EXISTS van_don (
      ma_van_don TEXT PRIMARY KEY,
      hang TEXT NOT NULL,
      trang_thai TEXT NOT NULL,
      hang_trang_thai INTEGER NOT NULL,
      cod INTEGER,
      cap_nhat_luc TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS hanh_trinh (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ma_van_don TEXT NOT NULL,
      hang TEXT NOT NULL,
      loai TEXT NOT NULL,
      thoi_gian_su_kien TEXT,
      su_kien_id INTEGER NOT NULL REFERENCES su_kien_tho(id),
      ap_dung INTEGER NOT NULL,                -- 1 = đổi trạng thái; 0 = đến muộn/không đổi, chỉ ghi sổ
      ly_do TEXT,
      ghi_luc TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS audit (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      luc TEXT NOT NULL,
      ai TEXT NOT NULL,
      vai_tro TEXT NOT NULL,
      hanh_dong TEXT NOT NULL,
      doi_tuong TEXT NOT NULL,
      chi_tiet TEXT
    );
"""


def bay_gio():
    return datetime.now(MUI_GIO_VN).strftime("%Y-%m-%d %H:%M:%S%z")


def _khoi_tao_schema(duong_dan):
    with _khoa_khoi_tao:
        if _da_khoi_tao.is_set():
            return
        os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
        kn = sqlite3.connect(duong_dan)
        try:
            kn.execute("PRAGMA journal_mode=WAL")
            kn.executescript(SCHEMA)
            kn.commit()
        finally:
            kn.close()
        _da_khoi_tao.set()


def mo(duong_dan=None):
    """Trả kết nối RIÊNG của thread hiện tại (tạo nếu chưa có)."""
    dd = duong_dan or DUONG_DAN_CSDL
    if not _da_khoi_tao.is_set():
        _khoi_tao_schema(dd)
    kn = getattr(_local, "kn", None)
    if kn is not None:
        return kn
    kn = sqlite3.connect(dd, timeout=10)
    kn.row_factory = sqlite3.Row
    kn.execute("PRAGMA journal_mode=WAL")
    kn.execute("PRAGMA foreign_keys=ON")
    kn.execute("PRAGMA busy_timeout=10000")
    _local.kn = kn
    return kn


def dong():
    kn = getattr(_local, "kn", None)
    if kn is not None:
        kn.close()
        _local.kn = None
    _da_khoi_tao.clear()


def ghi_su_kien_tho(hang, event_id, payload_tho, headers):
    """Lưu bền sự kiện thô. Trả (id, trung_lap). Trùng (hang,event_id) → không ghi thêm."""
    kn = mo()
    with _khoa:
        try:
            con = kn.execute(
                "INSERT INTO su_kien_tho (hang, event_id, payload_tho, headers_json, nhan_luc) VALUES (?,?,?,?,?)",
                (hang, event_id, payload_tho, json.dumps(headers, ensure_ascii=False), bay_gio()),
            )
            kn.commit()
            return con.lastrowid, False
        except sqlite3.IntegrityError:
            dong_cu = kn.execute(
                "SELECT id FROM su_kien_tho WHERE hang=? AND event_id=?", (hang, event_id)
            ).fetchone()
            return dong_cu["id"], True


def cap_nhat_su_kien(sk_id, **cot):
    kn = mo()
    with _khoa:
        dat = ", ".join(f"{k}=?" for k in cot)
        kn.execute(f"UPDATE su_kien_tho SET {dat} WHERE id=?", (*cot.values(), sk_id))
        kn.commit()


def lay_su_kien(sk_id):
    return mo().execute("SELECT * FROM su_kien_tho WHERE id=?", (sk_id,)).fetchone()


def danh_sach_su_kien(trang_thai=None, hang=None, gioi_han=100):
    dk, ts = [], []
    if trang_thai:
        dk.append("trang_thai=?"); ts.append(trang_thai)
    if hang:
        dk.append("hang=?"); ts.append(hang)
    where = ("WHERE " + " AND ".join(dk)) if dk else ""
    ts.append(gioi_han)
    return mo().execute(
        f"SELECT id, hang, event_id, nhan_luc, trang_thai, so_lan_thu, loi_cuoi, xu_ly_xong_luc "
        f"FROM su_kien_tho {where} ORDER BY id DESC LIMIT ?", ts
    ).fetchall()


def ap_trang_thai_van_don(ma_van_don, hang, loai, hang_moi, cod, thoi_gian_su_kien, sk_id, doi_trang_thai):
    """Cập nhật vận đơn theo luật out-of-order; luôn ghi hành trình. Trả (ap_dung, ly_do)."""
    kn = mo()
    with _khoa:
        vd = kn.execute("SELECT * FROM van_don WHERE ma_van_don=?", (ma_van_don,)).fetchone()
        ap_dung, ly_do = 0, ""
        if not doi_trang_thai:
            ly_do = "loai su kien khong doi trang thai"
        elif vd is None:
            kn.execute(
                "INSERT INTO van_don (ma_van_don, hang, trang_thai, hang_trang_thai, cod, cap_nhat_luc) VALUES (?,?,?,?,?,?)",
                (ma_van_don, hang, loai, hang_moi, cod, bay_gio()),
            )
            ap_dung = 1
        elif hang_moi > vd["hang_trang_thai"]:
            kn.execute(
                "UPDATE van_don SET trang_thai=?, hang_trang_thai=?, cod=COALESCE(?,cod), cap_nhat_luc=? WHERE ma_van_don=?",
                (loai, hang_moi, cod, bay_gio(), ma_van_don),
            )
            ap_dung = 1
        else:
            ly_do = f"den muon/out-of-order: hang {hang_moi} <= hien tai {vd['hang_trang_thai']}"
        kn.execute(
            "INSERT INTO hanh_trinh (ma_van_don, hang, loai, thoi_gian_su_kien, su_kien_id, ap_dung, ly_do, ghi_luc) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ma_van_don, hang, loai, thoi_gian_su_kien, sk_id, ap_dung, ly_do or None, bay_gio()),
        )
        kn.commit()
        return ap_dung, ly_do


def ghi_audit(ai, vai_tro, hanh_dong, doi_tuong, chi_tiet=""):
    kn = mo()
    with _khoa:
        kn.execute(
            "INSERT INTO audit (luc, ai, vai_tro, hanh_dong, doi_tuong, chi_tiet) VALUES (?,?,?,?,?,?)",
            (bay_gio(), ai, vai_tro, hanh_dong, doi_tuong, chi_tiet),
        )
        kn.commit()
