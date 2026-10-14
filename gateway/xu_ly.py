# Xử lý một sự kiện thô: kiểm định dạng → áp vào vận đơn theo luật out-of-order.
import json

import csdl
from cau_hinh import HANG_TRANG_THAI, SU_KIEN_KHONG_DOI_TRANG_THAI


class LoiVinhVien(Exception):
    """Lỗi không thể tự khỏi khi thử lại (định dạng, thiếu trường) → đi thẳng DLQ."""


class LoiTamThoi(Exception):
    """Lỗi có thể khỏi khi thử lại → retry với backoff."""


TRUONG_BAT_BUOC = ("event_id", "event", "tracking_number")


def xu_ly_su_kien(sk_row):
    """Xử lý một dòng su_kien_tho. Ném LoiVinhVien/LoiTamThoi khi hỏng."""
    try:
        du_lieu = json.loads(sk_row["payload_tho"])
    except (ValueError, UnicodeDecodeError) as e:
        raise LoiVinhVien(f"payload khong phai JSON: {e}")
    if not isinstance(du_lieu, dict):
        raise LoiVinhVien("payload JSON khong phai object")
    thieu = [t for t in TRUONG_BAT_BUOC if not du_lieu.get(t)]
    if thieu:
        raise LoiVinhVien(f"thieu truong bat buoc: {', '.join(thieu)}")

    loai = du_lieu["event"]
    doi_trang_thai = loai not in SU_KIEN_KHONG_DOI_TRANG_THAI
    if doi_trang_thai and loai not in HANG_TRANG_THAI:
        raise LoiVinhVien(f"loai su kien la: {loai}")

    # Móc giả lập lỗi tạm thời để kiểm retry/DLQ (chỉ có tác dụng với dữ liệu demo).
    if du_lieu.get("demo_force_fail"):
        raise LoiTamThoi("demo_force_fail dang bat")

    cod = du_lieu.get("cod_amount")
    if cod is not None and not isinstance(cod, (int, float)):
        raise LoiVinhVien("cod_amount khong phai so")

    ap_dung, ly_do = csdl.ap_trang_thai_van_don(
        ma_van_don=du_lieu["tracking_number"],
        hang=sk_row["hang"],
        loai=loai,
        hang_moi=HANG_TRANG_THAI.get(loai, 0),
        cod=int(cod) if cod is not None else None,
        thoi_gian_su_kien=du_lieu.get("timestamp"),
        sk_id=sk_row["id"],
        doi_trang_thai=doi_trang_thai,
    )
    return {"ap_dung": bool(ap_dung), "ly_do": ly_do}
