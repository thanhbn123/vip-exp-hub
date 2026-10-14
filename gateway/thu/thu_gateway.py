# Bộ thử G01 — chạy gateway thật trên cổng tạm, CSDL tạm, bắn HTTP thật vào.
# Chạy: python3 gateway/thu/thu_gateway.py
import base64
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)

# CSDL tạm + backoff ngắn cho bộ thử — đặt TRƯỚC khi import các mô-đun gateway.
_thu_muc_tam = tempfile.mkdtemp(prefix="vip-gateway-thu-")
os.environ["VIP_GATEWAY_DB"] = os.path.join(_thu_muc_tam, "thu.db")
os.environ["VIP_GATEWAY_BACKOFF"] = "0.05"

import csdl            # noqa: E402
import hang_doi        # noqa: E402
import server          # noqa: E402
import xac_thuc        # noqa: E402
from cau_hinh import HANG  # noqa: E402

# Cổng 0 = để hệ tự cấp một cổng RỖI. Cổng cố định làm bộ thử báo HỎNG GIẢ khi hai
# worktree chạy cùng lúc (AG-04 đo được 15/10: `Address already in use` ở lượt đầu,
# chạy lại thì đạt). Cổng thật đọc lại từ `sv.server_address[1]` sau khi bind.
CONG = 0
ADMIN = {"X-API-Key": "demo-admin-key"}
VIEWER = {"X-API-Key": "demo-viewer-key"}


def goi(duong, method="GET", du_lieu=None, headers=None, body_tho=None):
    body = body_tho if body_tho is not None else (
        json.dumps(du_lieu, ensure_ascii=False).encode() if du_lieu is not None else None)
    yc = urllib.request.Request(f"http://127.0.0.1:{CONG}{duong}", data=body,
                                headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(yc, timeout=5) as ph:
            return ph.status, json.loads(ph.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def headers_hang(ma_hang, body: bytes):
    ch = HANG[ma_hang]
    h = {"Content-Type": "application/json"}
    if ch["kieu_xac_thuc"] == "hmac_sha256":
        h[ch.get("header_chu_ky", "X-VTP-Signature")] = xac_thuc.ky_hmac(ma_hang, body)
    elif ch["kieu_xac_thuc"] == "bearer":
        h["Authorization"] = f"Bearer {ch['token']}"
    elif ch["kieu_xac_thuc"] == "header_token":
        h[ch["header"]] = ch["token"]
    elif ch["kieu_xac_thuc"] == "basic":
        h["Authorization"] = "Basic " + base64.b64encode(
            f"{ch['user']}:{ch['mat_khau']}".encode()).decode()
    return h


def ban_su_kien(ma_hang, du_lieu):
    body = json.dumps(du_lieu, ensure_ascii=False).encode()
    return goi(f"/api/webhook/{ma_hang}", "POST", headers=headers_hang(ma_hang, body), body_tho=body)


class ThuGateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global CONG      # gán lại sau khi bind cổng 0
        csdl.mo()
        hang_doi.khoi_dong()
        cls.sv = server.ThreadingHTTPServer(("127.0.0.1", CONG), server.BoXuLy)
        # Cổng THẬT do hệ cấp — gán lại CONG để mọi chỗ dựng URL lúc chạy tự đúng.
        CONG = cls.sv.server_address[1]
        cls.luong = threading.Thread(target=cls.sv.serve_forever, daemon=True)
        cls.luong.start()

    @classmethod
    def tearDownClass(cls):
        cls.sv.shutdown()
        cls.sv.server_close()
        hang_doi.dung()
        csdl.dong()

    # 1. Xác thực theo từng hãng
    def test_01_xac_thuc_tung_hang(self):
        du_lieu = {"event_id": "XT-1", "event": "don_moi", "tracking_number": "VD-XT-1"}
        body = json.dumps(du_lieu).encode()
        # thiếu/sai chữ ký → 401, KHÔNG được lưu
        st, kq = goi("/api/webhook/vtp", "POST", body_tho=body,
                     headers={"X-VTP-Signature": "sai-chu-ky"})
        self.assertEqual(st, 401)
        st, kq = goi("/api/webhook/ghn", "POST", body_tho=body,
                     headers={"Authorization": "Bearer sai-token"})
        self.assertEqual(st, 401)
        kn = csdl.mo()
        so = kn.execute("SELECT COUNT(*) c FROM su_kien_tho WHERE event_id='XT-1'").fetchone()["c"]
        self.assertEqual(so, 0, "su kien khong xac thuc duoc ma van bi luu")
        # đúng sơ đồ từng hãng → 202, cho cả 5 hãng
        for h in HANG:
            st, kq = ban_su_kien(h, {"event_id": f"XT-OK-{h}", "event": "don_moi",
                                     "tracking_number": f"VD-XT-{h}"})
            self.assertEqual(st, 202, f"hang {h} phai nhan duoc: {kq}")

    # 2. Idempotency: trùng (hãng, event_id) chỉ lưu và xử lý MỘT lần — cưỡng chế bằng UNIQUE của CSDL
    def test_02_idempotency(self):
        d = {"event_id": "IDEM-1", "event": "don_moi", "tracking_number": "VD-IDEM-1"}
        st1, kq1 = ban_su_kien("vtp", d)
        st2, kq2 = ban_su_kien("vtp", d)
        self.assertEqual(st1, 202)
        self.assertEqual(st2, 200)
        self.assertEqual(kq2["ket_qua"], "da_nhan_truoc_do")
        self.assertEqual(kq1["su_kien_id"], kq2["su_kien_id"])
        hang_doi.cho_rong()
        kn = csdl.mo()
        so = kn.execute("SELECT COUNT(*) c FROM su_kien_tho WHERE hang='vtp' AND event_id='IDEM-1'").fetchone()["c"]
        self.assertEqual(so, 1)
        so_ht = kn.execute("SELECT COUNT(*) c FROM hanh_trinh WHERE ma_van_don='VD-IDEM-1'").fetchone()["c"]
        self.assertEqual(so_ht, 1, "xu ly lai su kien trung → hanh trinh bi nhan doi")

    # 3. Out-of-order: sự kiện muộn không lùi trạng thái, nhưng vẫn vào sổ hành trình
    def test_03_out_of_order(self):
        ma = "VD-OOO-1"
        ban_su_kien("ghn", {"event_id": "OOO-1", "event": "giao_thanh_cong", "tracking_number": ma})
        hang_doi.cho_rong()
        ban_su_kien("ghn", {"event_id": "OOO-2", "event": "dang_giao", "tracking_number": ma})
        hang_doi.cho_rong()
        kn = csdl.mo()
        vd = kn.execute("SELECT * FROM van_don WHERE ma_van_don=?", (ma,)).fetchone()
        self.assertEqual(vd["trang_thai"], "giao_thanh_cong", "su kien muon da keo lui trang thai")
        ht = kn.execute("SELECT * FROM hanh_trinh WHERE ma_van_don=? ORDER BY id", (ma,)).fetchall()
        self.assertEqual(len(ht), 2)
        self.assertEqual(ht[1]["ap_dung"], 0)
        self.assertIn("out-of-order", ht[1]["ly_do"])

    # 4. Lưu bền sự kiện thô: byte lưu lại đúng từng byte đã gửi
    def test_04_luu_ben_tho(self):
        d = {"event_id": "THO-1", "event": "don_moi", "tracking_number": "VD-THO-1",
             "note": "tiếng Việt có dấu — kiểm byte"}
        body = json.dumps(d, ensure_ascii=False).encode()
        goi("/api/webhook/ghtk", "POST", body_tho=body, headers=headers_hang("ghtk", body))
        kn = csdl.mo()
        dong = kn.execute("SELECT payload_tho FROM su_kien_tho WHERE event_id='THO-1'").fetchone()
        self.assertEqual(bytes(dong["payload_tho"]), body)

    # 5. Lỗi vĩnh viễn (thiếu trường) → DLQ ngay, không retry
    def test_05_loi_vinh_vien_vao_dlq(self):
        st, kq = ban_su_kien("jt", {"event_id": "VV-1", "event": "don_moi"})  # thiếu tracking_number
        self.assertEqual(st, 202, "van phai NHAN va luu ben, hong o buoc xu ly")
        hang_doi.cho_rong()
        sk = csdl.lay_su_kien(kq["su_kien_id"])
        self.assertEqual(sk["trang_thai"], "dlq")
        self.assertIn("vinh vien", sk["loi_cuoi"])
        self.assertEqual(sk["so_lan_thu"], 0, "loi vinh vien ma van retry")

    # 6. Lỗi tạm thời → retry 3 lần với backoff rồi DLQ; replay sau khi hết lỗi thì xử lý xong
    def test_06_retry_dlq_va_replay(self):
        st, kq = ban_su_kien("best", {"event_id": "TT-1", "event": "don_moi",
                                      "tracking_number": "VD-TT-1", "demo_force_fail": True})
        sk_id = kq["su_kien_id"]
        import time
        moc = time.time() + 5
        while time.time() < moc:
            sk = csdl.lay_su_kien(sk_id)
            if sk["trang_thai"] == "dlq":
                break
            time.sleep(0.05)
        self.assertEqual(sk["trang_thai"], "dlq")
        self.assertEqual(sk["so_lan_thu"], 3)
        st, kq2 = goi("/api/dlq", headers=VIEWER)
        self.assertIn(sk_id, [d["id"] for d in kq2["dlq"]])
        # gỡ cờ lỗi trong payload (mô phỏng "nguồn đã sửa") rồi replay bằng quyền admin
        kn = csdl.mo()
        moi = json.dumps({"event_id": "TT-1", "event": "don_moi", "tracking_number": "VD-TT-1"}).encode()
        kn.execute("UPDATE su_kien_tho SET payload_tho=? WHERE id=?", (moi, sk_id))
        kn.commit()
        st, kq3 = goi(f"/api/su-kien/{sk_id}/replay", "POST", headers=ADMIN)
        self.assertEqual(st, 202)
        hang_doi.cho_rong()
        self.assertEqual(csdl.lay_su_kien(sk_id)["trang_thai"], "xong")

    # 7. RBAC: không khóa → 401; viewer đọc được nhưng không replay được; audit ghi lại replay
    def test_07_rbac_va_audit(self):
        st, _ = goi("/api/su-kien")
        self.assertEqual(st, 401)
        st, _ = goi("/api/su-kien", headers=VIEWER)
        self.assertEqual(st, 200)
        st, kq = ban_su_kien("vtp", {"event_id": "RB-1", "event": "don_moi", "tracking_number": "VD-RB-1"})
        sk_id = kq["su_kien_id"]
        hang_doi.cho_rong()
        st, _ = goi(f"/api/su-kien/{sk_id}/replay", "POST", headers=VIEWER)
        self.assertEqual(st, 403)
        st, _ = goi(f"/api/su-kien/{sk_id}/replay", "POST", headers=ADMIN)
        self.assertEqual(st, 202)
        hang_doi.cho_rong()
        st, kq_a = goi("/api/audit", headers=VIEWER)
        hanh_dong = [(a["hanh_dong"], a["doi_tuong"]) for a in kq_a["audit"]]
        self.assertIn(("replay", f"su_kien:{sk_id}"), hanh_dong)
        # viewer bị chặn thì KHÔNG được có vết audit replay nào của viewer
        self.assertTrue(all(a["vai_tro"] != "viewer" for a in kq_a["audit"] if a["hanh_dong"] == "replay"))

    # 8. Payload không phải JSON: vẫn lưu bền (đã xác thực) rồi vào DLQ với lý do rõ
    def test_08_payload_hong_json(self):
        body = b"day khong phai json"
        st, kq = goi("/api/webhook/ghtk", "POST", body_tho=body, headers=headers_hang("ghtk", body))
        self.assertEqual(st, 202)
        hang_doi.cho_rong()
        sk = csdl.lay_su_kien(kq["su_kien_id"])
        self.assertEqual(sk["trang_thai"], "dlq")
        self.assertEqual(bytes(sk["payload_tho"]), body)

    # 9. Hãng không tồn tại → 404; sức khỏe không cần khóa
    def test_09_duong_bien(self):
        st, _ = goi("/api/webhook/fedex", "POST", body_tho=b"{}")
        self.assertEqual(st, 404)
        st, kq = goi("/api/suc-khoe")
        self.assertEqual(st, 200)
        self.assertTrue(kq["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
