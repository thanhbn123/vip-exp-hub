# Bộ MÔ PHỎNG hãng vận chuyển: gửi webhook demo (ký đúng sơ đồ từng hãng) vào gateway local.
# Không liên lạc với bất kỳ hãng thật nào — chỉ bắn vào 127.0.0.1.
import base64
import json
import random
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

import xac_thuc
from cau_hinh import CONG_MAC_DINH, HANG

MUI_GIO_VN = timezone(timedelta(hours=7))


def gui(ma_hang, du_lieu, cong):
    body = json.dumps(du_lieu, ensure_ascii=False).encode()
    ch = HANG[ma_hang]
    headers = {"Content-Type": "application/json"}
    kieu = ch["kieu_xac_thuc"]
    if kieu == "hmac_sha256":
        headers[ch.get("header_chu_ky", "X-VTP-Signature")] = xac_thuc.ky_hmac(ma_hang, body)
    elif kieu == "bearer":
        headers["Authorization"] = f"Bearer {ch['token']}"
    elif kieu == "header_token":
        headers[ch["header"]] = ch["token"]
    elif kieu == "basic":
        headers["Authorization"] = "Basic " + base64.b64encode(
            f"{ch['user']}:{ch['mat_khau']}".encode()).decode()
    yc = urllib.request.Request(
        f"http://127.0.0.1:{cong}/api/webhook/{ma_hang}", data=body, headers=headers, method="POST")
    with urllib.request.urlopen(yc, timeout=5) as ph:
        return ph.status, json.loads(ph.read())


def chay(so_van_don=6, cong=CONG_MAC_DINH, co_loi=True, co_tre=True):
    random.seed()
    cac_hang = list(HANG)
    chuoi = ["don_moi", "lay_hang", "dang_giao", "giao_thanh_cong"]
    dem = 0
    for i in range(so_van_don):
        h = cac_hang[i % len(cac_hang)]
        ma = f"{h.upper()}DEMO{random.randint(10**8, 10**9 - 1)}"
        cac_buoc = list(chuoi)
        if co_tre and i % 3 == 2:
            # cố ý đảo thứ tự hai bước giữa để kiểm out-of-order
            cac_buoc[1], cac_buoc[2] = cac_buoc[2], cac_buoc[1]
        for j, loai in enumerate(cac_buoc):
            du_lieu = {
                "event_id": f"{ma}-{loai}",
                "event": loai,
                "tracking_number": ma,
                "timestamp": (datetime.now(MUI_GIO_VN) + timedelta(seconds=j)).isoformat(),
                "cod_amount": random.choice([0, 150000, 550000]),
                "note": "DEMO — su kien mo phong, khong phai webhook that",
            }
            if co_loi and i == 0 and loai == "dang_giao":
                du_lieu["demo_force_fail"] = True  # ép lỗi tạm thời để xem retry → DLQ
            st, kq = gui(h, du_lieu, cong)
            dem += 1
            print(f"  {h:4s} {loai:16s} → HTTP {st} {kq.get('ket_qua')}")
    print(f"Đã gửi {dem} sự kiện mô phỏng vào gateway 127.0.0.1:{cong}")


if __name__ == "__main__":
    chay(cong=int(sys.argv[1]) if len(sys.argv) > 1 else CONG_MAC_DINH)
