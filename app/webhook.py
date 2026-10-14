# G06 — Central Webhook Gateway tenant-aware (kế thừa thiết kế G01 đã nghiệm thu):
# VERIFY → PERSIST RAW → QUEUE → NORMALIZE → RESOLVE TENANT+ORDER → UPDATE → AUDIT.
# Tenant resolve từ carrier_account (định danh trên URL + chữ ký bằng secret của CHÍNH account đó)
# — không bao giờ từ nội dung payload. Chống trùng bằng UNIQUE(account_id, event_id) trong CSDL.
import hashlib
import hmac
import json
import queue
import sqlite3
import threading

import bao_mat
import cau_hinh
import csdl
import don_hang

_hang_doi = queue.Queue()
_worker = None
_dung = threading.Event()
_cho_trong = threading.Condition()
_dang_xu_ly = 0


class LoiVinhVien(Exception):
    pass


def tim_account_theo_webhook_ma(webhook_ma):
    return csdl.mot("SELECT * FROM carrier_accounts WHERE webhook_ma=? AND kich_hoat=1", (webhook_ma,))


def kiem_chu_ky(tk_row, headers, body: bytes):
    """Mức local: HMAC-SHA256 bằng webhook_secret của account (header X-Webhook-Signature).
    Khi nối hãng thật, adapter của hãng sẽ cung cấp hàm verify riêng theo sơ đồ hãng."""
    secret = bao_mat.giai_ma(tk_row["webhook_secret_ma_hoa"])
    dung = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(headers.get("x-webhook-signature", ""), dung)


def nhan_su_kien(tk_row, body: bytes, headers: dict):
    """Lưu bền + xếp hàng. Trả (sk_id, trung)."""
    try:
        event_id = json.loads(body).get("event_id") or ""
    except Exception:
        event_id = ""
    if not event_id:
        event_id = "noid-" + hashlib.sha256(body).hexdigest()[:24]
    with csdl.khoa_ghi:
        try:
            con = csdl.ghi(
                "INSERT INTO wh_su_kien (carrier_account_id, event_id, payload_tho, headers_json, nhan_luc)"
                " VALUES (?,?,?,?,?)",
                (tk_row["id"], event_id, body, json.dumps(headers, ensure_ascii=False), csdl.bay_gio()))
        except sqlite3.IntegrityError:
            cu = csdl.mot("SELECT id FROM wh_su_kien WHERE carrier_account_id=? AND event_id=?",
                          (tk_row["id"], event_id))
            return cu["id"], True
    nap(con.lastrowid)
    return con.lastrowid, False


def nap(sk_id):
    _hang_doi.put(sk_id)


def _xu_ly(sk):
    """Normalize + resolve tenant/order + update. Ném LoiVinhVien khi không thể tự khỏi."""
    try:
        d = json.loads(sk["payload_tho"])
    except (ValueError, UnicodeDecodeError) as e:
        raise LoiVinhVien(f"payload không phải JSON: {e}")
    if not isinstance(d, dict):
        raise LoiVinhVien("payload không phải object")
    loai = d.get("event")
    ma_van_don = d.get("tracking_number")
    if not loai or not ma_van_don:
        raise LoiVinhVien("thiếu event hoặc tracking_number")
    if d.get("demo_force_fail"):
        raise RuntimeError("demo_force_fail đang bật")  # lỗi tạm thời để kiểm retry/DLQ
    tk = csdl.mot("SELECT * FROM carrier_accounts WHERE id=?", (sk["carrier_account_id"],))
    # RESOLVE: đơn phải thuộc ĐÚNG tenant của account và đúng account — không bao giờ cập nhật chéo tenant.
    don = csdl.mot(
        "SELECT * FROM don_hang WHERE ma_van_don=? AND tenant_id=? AND carrier_account_id=?",
        (ma_van_don, tk["tenant_id"], tk["id"]))
    if not don:
        return "khong_khop"  # lưu thô, đánh dấu không khớp — không đụng đơn của ai
    ap_dung, ly_do = don_hang.ap_trang_thai_giao(don["id"], loai, f"webhook:{sk['id']}")
    csdl.audit("webhook_cap_nhat_don", f"don:{don['id']}",
               f"su_kien:{sk['id']} loai={loai} ap_dung={ap_dung} {ly_do}", tenant_id=tk["tenant_id"])
    return "xong"


def _chay_mot(sk_id):
    sk = csdl.mot("SELECT * FROM wh_su_kien WHERE id=?", (sk_id,))
    if sk is None or sk["trang_thai"] in ("xong", "dlq", "khong_khop"):
        return
    csdl.ghi("UPDATE wh_su_kien SET trang_thai='dang_xu_ly' WHERE id=?", (sk_id,))
    try:
        kq = _xu_ly(sk)
        csdl.ghi("UPDATE wh_su_kien SET trang_thai=?, loi_cuoi=NULL, xu_ly_xong_luc=? WHERE id=?",
                 (kq, csdl.bay_gio(), sk_id))
    except LoiVinhVien as e:
        csdl.ghi("UPDATE wh_su_kien SET trang_thai='dlq', loi_cuoi=? WHERE id=?", (f"vinh vien: {e}", sk_id))
    except Exception as e:
        so_lan = sk["so_lan_thu"] + 1
        if so_lan >= cau_hinh.WEBHOOK_SO_LAN_THU:
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='dlq', so_lan_thu=?, loi_cuoi=? WHERE id=?",
                     (so_lan, f"qua {so_lan} lan: {e}", sk_id))
        else:
            csdl.ghi("UPDATE wh_su_kien SET trang_thai='cho_thu_lai', so_lan_thu=?, loi_cuoi=? WHERE id=?",
                     (so_lan, str(e), sk_id))
            threading.Timer(cau_hinh.WEBHOOK_BACKOFF_GOC * (2 ** (so_lan - 1)), nap, args=(sk_id,)).start()


def _vong_lap():
    global _dang_xu_ly
    while not _dung.is_set():
        try:
            sk_id = _hang_doi.get(timeout=0.2)
        except queue.Empty:
            continue
        with _cho_trong:
            _dang_xu_ly += 1
        try:
            _chay_mot(sk_id)
        finally:
            _hang_doi.task_done()
            with _cho_trong:
                _dang_xu_ly -= 1
                _cho_trong.notify_all()


def khoi_dong():
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    kn = csdl.mo()
    with csdl.khoa_ghi:
        kn.execute("UPDATE wh_su_kien SET trang_thai='moi' WHERE trang_thai='dang_xu_ly'")
        kn.commit()
    for d in kn.execute("SELECT id FROM wh_su_kien WHERE trang_thai IN ('moi','cho_thu_lai') ORDER BY id"):
        nap(d["id"])
    _dung.clear()
    _worker = threading.Thread(target=_vong_lap, name="hub-webhook-worker", daemon=True)
    _worker.start()


def dung():
    _dung.set()


def cho_rong(het_gio=10.0):
    import time
    moc = time.time() + het_gio
    while time.time() < moc:
        with _cho_trong:
            if _hang_doi.unfinished_tasks == 0 and _dang_xu_ly == 0:
                return True
            _cho_trong.wait(timeout=0.1)
    return False
