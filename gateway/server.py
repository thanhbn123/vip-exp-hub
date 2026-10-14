# VIP Express Hub — G01 Universal Webhook Gateway (local-first, Python stdlib + SQLite).
# Nhận webhook mô phỏng đa hãng, lưu bền sự kiện thô, xử lý qua hàng đợi, replay có RBAC + audit.
# KHÔNG mở ra internet — chỉ bind 127.0.0.1. Không gọi API hãng thật nào.
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import csdl
import hang_doi
import xac_thuc
from cau_hinh import CONG_MAC_DINH, HANG


def _json_bytes(obj):
    return json.dumps(obj, ensure_ascii=False).encode()


class BoXuLy(BaseHTTPRequestHandler):
    server_version = "VIPExpressGateway/0.1-G01"

    def log_message(self, fmt, *args):  # log gọn một dòng
        sys.stderr.write("[gateway] %s - %s\n" % (self.address_string(), fmt % args))

    # ----- tiện ích -----
    def _headers_thuong(self):
        return {k.lower(): v for k, v in self.headers.items()}

    def _tra(self, ma, obj):
        body = _json_bytes(obj)
        self.send_response(ma)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # CORS cho trang demo G00 mở từ localhost:8899 đọc API này
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "X-API-Key, Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _doc_body(self):
        dai = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(dai) if dai else b""

    def _doi_vai_tro(self, can="viewer"):
        """Trả vai trò nếu đủ quyền, ngược lại tự trả lỗi và trả None."""
        vt = xac_thuc.vai_tro_api(self._headers_thuong())
        if vt is None:
            self._tra(401, {"loi": "thieu hoac sai X-API-Key"})
            return None
        if can == "admin" and vt != "admin":
            self._tra(403, {"loi": "can quyen admin"})
            return None
        return vt

    # ----- route -----
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "X-API-Key, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        duong, _, truy_van = self.path.partition("?")
        ts = {}
        for cap in truy_van.split("&"):
            if "=" in cap:
                k, v = cap.split("=", 1)
                ts[k] = v

        if duong == "/api/suc-khoe":
            return self._tra(200, {"ok": True, "phien_ban": self.server_version,
                                   "ghi_chu": "DEMO G01 — gateway local, khong noi hang that"})

        vt = self._doi_vai_tro("viewer")
        if vt is None:
            return

        if duong == "/api/su-kien":
            ds = csdl.danh_sach_su_kien(trang_thai=ts.get("trang_thai") or None,
                                        hang=ts.get("hang") or None,
                                        gioi_han=min(int(ts.get("gioi_han", "100")), 500))
            return self._tra(200, {"su_kien": [dict(d) for d in ds]})

        m = re.fullmatch(r"/api/su-kien/(\d+)", duong)
        if m:
            sk = csdl.lay_su_kien(int(m.group(1)))
            if not sk:
                return self._tra(404, {"loi": "khong co su kien"})
            d = dict(sk)
            d["payload_tho"] = d["payload_tho"].decode("utf-8", "replace")
            return self._tra(200, d)

        if duong == "/api/dlq":
            ds = csdl.danh_sach_su_kien(trang_thai="dlq")
            return self._tra(200, {"dlq": [dict(d) for d in ds]})

        if duong == "/api/van-don":
            kn = csdl.mo()
            ds = kn.execute("SELECT * FROM van_don ORDER BY cap_nhat_luc DESC LIMIT 200").fetchall()
            return self._tra(200, {"van_don": [dict(d) for d in ds]})

        m = re.fullmatch(r"/api/van-don/([A-Za-z0-9_-]+)/hanh-trinh", duong)
        if m:
            kn = csdl.mo()
            ds = kn.execute("SELECT * FROM hanh_trinh WHERE ma_van_don=? ORDER BY id", (m.group(1),)).fetchall()
            return self._tra(200, {"hanh_trinh": [dict(d) for d in ds]})

        if duong == "/api/audit":
            kn = csdl.mo()
            ds = kn.execute("SELECT * FROM audit ORDER BY id DESC LIMIT 200").fetchall()
            return self._tra(200, {"audit": [dict(d) for d in ds]})

        return self._tra(404, {"loi": "khong co duong nay"})

    def do_POST(self):
        duong = self.path.split("?")[0]
        body = self._doc_body()
        headers = self._headers_thuong()

        m = re.fullmatch(r"/api/webhook/([a-z]+)", duong)
        if m:
            ma_hang = m.group(1)
            if ma_hang not in HANG:
                return self._tra(404, {"loi": f"hang '{ma_hang}' khong ton tai"})
            dat, ly_do = xac_thuc.kiem_webhook(ma_hang, headers, body)
            if not dat:
                # Không lưu sự kiện không xác thực được — tránh ai cũng nhét được rác vào kho.
                return self._tra(401, {"loi": ly_do})
            # Lấy event_id để chống trùng; payload hỏng JSON vẫn được LƯU BỀN rồi DLQ ở worker.
            try:
                event_id = json.loads(body).get("event_id") or ""
            except Exception:
                event_id = ""
            if not event_id:
                # không có event_id thì không chống trùng được → dùng băm nội dung làm khóa
                import hashlib
                event_id = "noid-" + hashlib.sha256(body).hexdigest()[:24]
            sk_id, trung = csdl.ghi_su_kien_tho(ma_hang, event_id, body, headers)
            if trung:
                return self._tra(200, {"ket_qua": "da_nhan_truoc_do", "su_kien_id": sk_id,
                                       "ghi_chu": "idempotent: khong xu ly lai"})
            hang_doi.nap(sk_id)
            return self._tra(202, {"ket_qua": "da_nhan", "su_kien_id": sk_id})

        m = re.fullmatch(r"/api/su-kien/(\d+)/replay", duong)
        if m:
            vt = self._doi_vai_tro("admin")
            if vt is None:
                return
            sk_id = int(m.group(1))
            sk = csdl.lay_su_kien(sk_id)
            if not sk:
                return self._tra(404, {"loi": "khong co su kien"})
            csdl.cap_nhat_su_kien(sk_id, trang_thai="moi", so_lan_thu=0, loi_cuoi=None)
            hang_doi.nap(sk_id)
            csdl.ghi_audit(headers.get("x-api-key", "?"), vt, "replay", f"su_kien:{sk_id}",
                           f"trang thai truoc: {sk['trang_thai']}")
            return self._tra(202, {"ket_qua": "da_nap_lai", "su_kien_id": sk_id})

        return self._tra(404, {"loi": "khong co duong nay"})


def chay(cong=CONG_MAC_DINH):
    csdl.mo()
    hang_doi.khoi_dong()
    sv = ThreadingHTTPServer(("127.0.0.1", cong), BoXuLy)
    print(f"[gateway] G01 demo chay tai http://127.0.0.1:{cong} — Ctrl+C de dung")
    try:
        sv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        hang_doi.dung()
        sv.server_close()


if __name__ == "__main__":
    chay(int(sys.argv[1]) if len(sys.argv) > 1 else CONG_MAC_DINH)
