# Hàng đợi + worker nền: xử lý tuần tự, retry với backoff, quá 3 lần → DLQ.
import queue
import threading

import csdl
import xu_ly
from cau_hinh import GIAY_BACKOFF_GOC, SO_LAN_THU_TOI_DA

_hang_doi = queue.Queue()
_worker = None
_dung = threading.Event()
_cho_trong = threading.Condition()  # báo cho ai đợi hàng đợi rỗng (phục vụ bộ thử)
_dang_xu_ly = 0


def nap(sk_id):
    _hang_doi.put(sk_id)


def _chay_mot(sk_id):
    sk = csdl.lay_su_kien(sk_id)
    if sk is None or sk["trang_thai"] in ("xong", "dlq"):
        return
    csdl.cap_nhat_su_kien(sk_id, trang_thai="dang_xu_ly")
    try:
        kq = xu_ly.xu_ly_su_kien(sk)
        csdl.cap_nhat_su_kien(
            sk_id, trang_thai="xong", loi_cuoi=None, xu_ly_xong_luc=csdl.bay_gio()
        )
        return kq
    except xu_ly.LoiVinhVien as e:
        # Thử lại không cứu được lỗi định dạng → vào DLQ ngay, ghi rõ lý do.
        csdl.cap_nhat_su_kien(sk_id, trang_thai="dlq", loi_cuoi=f"vinh vien: {e}")
    except Exception as e:  # LoiTamThoi và mọi lỗi bất ngờ khác: thử lại có kiểm soát
        so_lan = sk["so_lan_thu"] + 1
        if so_lan >= SO_LAN_THU_TOI_DA:
            csdl.cap_nhat_su_kien(sk_id, trang_thai="dlq", so_lan_thu=so_lan, loi_cuoi=f"qua {so_lan} lan: {e}")
        else:
            csdl.cap_nhat_su_kien(sk_id, trang_thai="cho_thu_lai", so_lan_thu=so_lan, loi_cuoi=str(e))
            tre = GIAY_BACKOFF_GOC * (2 ** (so_lan - 1))
            threading.Timer(tre, nap, args=(sk_id,)).start()


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
    """Bật worker; nạp lại việc dở từ CSDL (phục hồi sau khi tiến trình chết)."""
    global _worker
    if _worker is not None and _worker.is_alive():
        return
    # Sự kiện 'dang_xu_ly' mồ côi (tiến trình chết giữa chừng) → trả về 'moi' rồi nạp lại.
    kn = csdl.mo()
    kn.execute("UPDATE su_kien_tho SET trang_thai='moi' WHERE trang_thai='dang_xu_ly'")
    kn.commit()
    for dong in kn.execute("SELECT id FROM su_kien_tho WHERE trang_thai IN ('moi','cho_thu_lai') ORDER BY id"):
        nap(dong["id"])
    _dung.clear()
    _worker = threading.Thread(target=_vong_lap, name="gateway-worker", daemon=True)
    _worker.start()


def dung():
    _dung.set()


def cho_rong(het_gio=10.0):
    """Đợi tới khi hàng đợi rỗng và không còn việc đang xử lý (dùng trong bộ thử)."""
    import time
    moc = time.time() + het_gio
    while time.time() < moc:
        with _cho_trong:
            if _hang_doi.unfinished_tasks == 0 and _dang_xu_ly == 0:
                return True
            _cho_trong.wait(timeout=0.1)
    return False
