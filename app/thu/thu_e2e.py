"""E2E qua HTTP THẬT: đăng nhập → chọn tenant → import → kiểm → đơn nháp → duyệt →
chọn hãng → gửi qua adapter mock → nhận webhook mock → cập nhật trạng thái → lịch sử.
Đi qua CẢ 12 route G04 mới và 2 điểm cắm G06."""
import base64, hashlib, hmac, json, os, sqlite3, sys, urllib.error, urllib.request

GOC, S = f"http://127.0.0.1:{os.environ.get('VIP_E2E_CONG', '8947')}", os.environ["VIP_HUB_DATA"]
ck = {}
def goi(duong, pt="GET", body=None, tho=None, hdr=None, ky=None):
    d = (tho if tho is not None else
         (json.dumps(body, ensure_ascii=False).encode() if body is not None else None))
    r = urllib.request.Request(GOC + duong, data=d, method=pt)
    r.add_header("X-Requested-With", "VIPHub")
    if d is not None: r.add_header("Content-Type", "application/json")
    if ck: r.add_header("Cookie", "; ".join(f"{k}={v}" for k, v in ck.items()))
    for k, v in (hdr or {}).items(): r.add_header(k, v)
    try:
        with urllib.request.urlopen(r, timeout=20) as f:
            for h in f.headers.get_all("Set-Cookie") or []:
                k, _, v = h.split(";")[0].partition("="); ck[k] = v
            b = f.read()
            return f.status, (json.loads(b) if b.startswith(b"{") else b)
    except urllib.error.HTTPError as e:
        b = e.read()
        return e.code, (json.loads(b) if b.startswith(b"{") else b[:200])

B = []
def b(ten, dat, ghi=""):
    B.append((dat, ten, ghi)); print(f"  {'✓' if dat else '✗'} {ten}" + (f"  — {ghi}" if ghi else ""))

db = os.path.join(S, "hub.db")
def sql(q, p=()):
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    r = [dict(x) for x in c.execute(q, p)]; c.commit(); c.close(); return r

print("\n── 0. DỰNG NỀN ─────────────────────────────────────────")
# tài khoản platform đầu tiên do seed tạo; lấy từ CSDL
u = sql("SELECT ten_dang_nhap FROM users LIMIT 1")
print(f"  user có sẵn: {[x['ten_dang_nhap'] for x in u]}")
MK_DEMO = dict(__import__("re").findall(r"`([a-z-]+)` / `([^`]+)`",
    open(os.path.join(S, "TAI-KHOAN-DEMO.md"), encoding="utf-8").read()))
st, kq = goi("/api/v2/auth/dang-nhap", "POST",
             {"ten_dang_nhap": "platform-owner", "mat_khau": MK_DEMO["platform-owner"]})
b("1. ĐĂNG NHẬP", st == 200, f"HTTP {st}")
if st != 200: print("   ", kq); sys.exit(1)

st, kq = goi("/api/v2/platform/tenants", "POST",
             {"ten": "Cty E2E", "owner_ten_dang_nhap": "e2e-owner",
              "owner_mat_khau": "owner12345", "owner_ho_ten": "Chủ E2E"})
tid = kq.get("id"); b("   tạo tenant", st == 201, f"tenant_id={tid}")
goi("/api/v2/auth/dang-xuat", "POST", {})
ck.clear()
st, _ = goi("/api/v2/auth/dang-nhap", "POST", {"ten_dang_nhap": "e2e-owner", "mat_khau": "owner12345"})
b("2. CHỌN TENANT", st == 200, "đăng nhập bằng owner của tenant")
st, me = goi("/api/v2/auth/toi")
b("   ngữ cảnh tenant từ PHIÊN", me.get("tenant", {}).get("id") == tid,
  f"tenant={me.get('tenant')} vai_tro={me.get('vai_tro')}")

st, kq = goi("/api/v2/tai-khoan-hang", "POST",
             {"hang": "vtp", "ten": "VTP mock", "credentials": {"user": "u", "pass": "p"}})
tk_vtp = kq.get("id"); b("   tài khoản hãng VTP", st == 201, f"id={tk_vtp}")
# Gói Miễn phí chỉ cho 1 kết nối hãng — 402 ở đây là HẠN MỨC ĐANG CHẠY ĐÚNG, không phải lỗi.
# Đo luôn điều đó rồi mới nâng gói, vì "hạn mức có chặn thật không" là thứ đáng đo.
st_han, kq_han = goi("/api/v2/tai-khoan-hang", "POST",
                     {"hang": "jt", "ten": "J&T qua han", "credentials": {"apiAccount": "a"}})
b("   hạn mức gói chặn kết nối hãng thứ 2", st_han == 402,
  f"HTTP {st_han} · {kq_han.get('loi') if isinstance(kq_han, dict) else ''}")
ck_owner = dict(ck); ck.clear()
goi("/api/v2/auth/dang-nhap", "POST",
    {"ten_dang_nhap": "platform-owner", "mat_khau": MK_DEMO["platform-owner"]})
st_goi, kq_goi = goi(f"/api/v2/platform/tenants/{tid}/goi", "POST", {"goi_id": "pro"})
b("   nâng gói qua cửa platform", st_goi == 200, f"HTTP {st_goi} · {kq_goi}")
goi("/api/v2/auth/dang-xuat", "POST", {}); ck.clear(); ck.update(ck_owner)
st, kq = goi("/api/v2/tai-khoan-hang", "POST",
             {"hang": "jt", "ten": "J&T mock", "credentials": {"apiAccount": "a", "privateKey": "k"}})
tk_jt = kq.get("id"); wh_ma = kq.get("webhook_url", "").rsplit("/", 1)[-1]
b("   tài khoản hãng J&T", st == 201, f"id={tk_jt} webhook_ma={wh_ma[:12]}…")

print("\n── 3. IMPORT EXCEL/CSV ─────────────────────────────────")
csv = ("ten_nguoi_nhan,sdt,dia_chi,hang_hoa,khoi_luong_gram,cod\n"
       "Nguyễn Văn A,0901234567,12 Lê Lợi Quận 1 TP HCM,Áo thun,500,250000\n"
       "Trần Thị B,0912345678,34 Hai Bà Trưng Quận 3 TP HCM,Giày,1200,480000\n"
       "=cmd|' /C calc'!A1,0999999999,99 Nguy Hiểm,Thử công thức,300,0\n")
st, kq = goi("/api/v2/import", "POST",
             {"ten_file": "don-e2e.csv", "noi_dung_base64": base64.b64encode(csv.encode()).decode()})
bid = kq.get("batch_id"); b("   tải file lên", st == 201, f"batch={bid}")
st, kq = goi(f"/api/v2/import/{bid}")
dong = kq.get("dong", [])
b("4. KIỂM TRA DỮ LIỆU", len(dong) == 3, f"{len(dong)} dòng · trạng thái={[d['trang_thai'] for d in dong]}")
st, kq = goi(f"/api/v2/import/{bid}/xuat-csv")
oc = [o for o in (kq.split(b",") if isinstance(kq, bytes) else [])
      if o[:2] in (b'"=', b'"+', b'"-', b'"@')]
b("   chặn formula injection khi xuất", isinstance(kq, bytes) and b"cmd|" in kq and not oc,
  f"{len(kq) if isinstance(kq, bytes) else 0} byte · {len(oc)} ô còn mở đầu bằng dấu công thức")

print("\n── 5. TẠO ĐƠN NHÁP ────────────────────────────────────")
# Tên trạng thái THẬT lấy từ máy, không từ trí nhớ: VALID / NEEDS_REVIEW / INVALID.
ok_dong = [d["id"] for d in dong if d["trang_thai"] == "VALID"][:2]
st, kq = goi(f"/api/v2/import/{bid}/duyet", "POST",
             {"dong_ids": ok_dong, "nguoi_gui": {"ten": "Kho E2E", "sdt": "0900000000",
                                                 "dia_chi": "1 Kho, Q7, TP HCM"}})
b("   duyệt dòng import → đơn nháp", st == 200 and kq.get("SUCCESS", 0) >= 1,
  f"HTTP {st} · {json.dumps(kq, ensure_ascii=False)[:110]}")
ds = sql("SELECT id, ma_don, trang_thai FROM don_hang WHERE tenant_id=? ORDER BY id", (tid,))
b("   đơn đã vào CSDL", len(ds) >= 1, f"{[(d['ma_don'], d['trang_thai']) for d in ds]}")
don_id = ds[0]["id"]

# ROUTE MỚI 5: POST /don/kiem (dữ liệu chưa lưu)
st, kq = goi("/api/v2/don/kiem", "POST",
             {"nguoi_nhan_ten": "", "nguoi_nhan_sdt": "abc", "khoi_luong_gram": 0})
b("   [R05] POST /don/kiem", st == 200 and kq.get("hop_le") is False,
  f"HTTP {st} · {len(kq.get('loi', []))} lỗi phát hiện trước khi lưu")
# ROUTE MỚI 6: GET /don/{id}/kiem
st, kq = goi(f"/api/v2/don/{don_id}/kiem")
b("   [R06] GET /don/{id}/kiem", st == 200 and "hop_le" in kq, f"HTTP {st} · hợp_lệ={kq.get('hop_le')}")
# ROUTE MỚI 11: PUT mặt hàng
st, kq = goi(f"/api/v2/don/{don_id}/mat-hang", "PUT",
             {"mat_hang": [{"ten": "Áo thun", "ma_sku": "AT-01", "so_luong": 2,
                            "don_gia": 125000, "khoi_luong_gram": 250}]})
b("   [R11] PUT /don/{id}/mat-hang", st == 200 and kq.get("tong_khoi_luong_gram") == 500,
  f"HTTP {st} · tổng={kq.get('tong_khoi_luong_gram')}g / {kq.get('tong_gia_tri_dong')}đ")
# ROUTE MỚI 10: GET mặt hàng
st, kq = goi(f"/api/v2/don/{don_id}/mat-hang")
b("   [R10] GET /don/{id}/mat-hang", st == 200 and len(kq.get("mat_hang", [])) == 1, f"HTTP {st}")
# ROUTE MỚI 4: POST /don/tim
st, kq = goi("/api/v2/don/tim", "POST", {"trang_thai": ["nhap"], "gioi_han": 50})
b("   [R04] POST /don/tim", st == 200 and "tong" in kq,
  f"HTTP {st} · tìm được {kq.get('tong')} · bỏ qua lọc={kq.get('loc_bo_qua')}")
# ROUTE MỚI 9: GET đầy đủ
st, kq = goi(f"/api/v2/don/{don_id}/day-du")
b("   [R09] GET /don/{id}/day-du", st == 200 and "don" in kq and "mat_hang" in kq,
  f"HTTP {st} · khóa={sorted(kq.keys()) if isinstance(kq, dict) else '?'}")

print("\n── 6. DUYỆT / TỪ CHỐI ─────────────────────────────────")
don_b = ds[1]["id"] if len(ds) > 1 else None
if don_b:
    st, kq = goi(f"/api/v2/don/{don_b}/tu-choi", "POST", {})
    b("   [R01] từ chối THIẾU lý do → 400", st == 400, f"HTTP {st}")
    st, kq = goi(f"/api/v2/don/{don_b}/tu-choi", "POST", {"ly_do": "Địa chỉ không rõ phường"})
    # "Bị từ chối" KHÔNG phải một giá trị `trang_thai` mới — AG-02 cố ý mô hình hoá nó là
    # `trang_thai='nhap'` + `ly_do_tu_choi` khác NULL, vì hợp đồng đóng băng ghim `trang_thai`
    # đúng 5 giá trị và thêm giá trị là phá mọi chỗ đang đọc. Nên đo ĐÚNG thứ mang nghĩa.
    d2 = sql("SELECT trang_thai, ly_do_tu_choi, tu_choi_boi FROM don_hang WHERE id=?", (don_b,))[0]
    b("   [R01] POST /don/{id}/tu-choi", st == 200 and d2["trang_thai"] == "nhap"
      and d2["ly_do_tu_choi"] == "Địa chỉ không rõ phường" and d2["tu_choi_boi"],
      f"HTTP {st} · trạng thái={d2['trang_thai']} + lý do={d2['ly_do_tu_choi']!r}"
      f" + người từ chối={d2['tu_choi_boi']}")
st, kq = goi(f"/api/v2/don/{don_id}/duyet", "POST", {})
b("6. DUYỆT ĐƠN", st == 200 and kq["don"]["trang_thai"] == "da_duyet", f"HTTP {st}")

print("\n── 7-8. CHỌN HÃNG → GỬI QUA ADAPTER MOCK ──────────────")
st, kq = goi(f"/api/v2/don/{don_id}/gui", "POST", {"carrier_account_id": tk_vtp})
mvd = kq.get("don", {}).get("ma_van_don")
b("7-8. GỬI ĐƠN (adapter mock VTP)", st == 200 and bool(mvd),
  f"HTTP {st} · mã vận đơn={mvd} · trạng thái={kq.get('don', {}).get('trang_thai')}")
# ROUTE MỚI 8: nhãn
st, kq = goi(f"/api/v2/don/{don_id}/nhan")
b("   [R08] GET /don/{id}/nhan", st == 200 and kq.get("nhan_that") is False,
  f"HTTP {st} · nhan_that={kq.get('nhan_that')} la_mock={kq.get('la_mock')} — KHÔNG phải nhãn vận đơn thật")
# ROUTE MỚI 2: đối soát qua hãng
st, kq = goi(f"/api/v2/don/{don_id}/doi-soat", "POST", {})
b("   [R02] POST /don/{id}/doi-soat", st in (200, 409),
  f"HTTP {st} · kết luận={kq.get('ket_luan')} thao tác={kq.get('thao_tac')} mock={kq.get('la_mock')}")
# ROUTE MỚI 12: danh sách cần đối soát
st, kq = goi("/api/v2/don/can-doi-soat")
b("   [R12] GET /don/can-doi-soat", st == 200 and "don" in kq, f"HTTP {st} · {len(kq.get('don', []))} đơn")

print("\n── 9. NHẬN WEBHOOK MOCK ───────────────────────────────")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("VIP_HUB_DATA", S)
import bao_mat                                                     # noqa: E402

r_tk = sql("SELECT webhook_ma, webhook_secret_ma_hoa FROM carrier_accounts WHERE id=?",
           (tk_vtp,))[0]
wh_vtp = r_tk["webhook_ma"]
# Giải mã bằng ĐÚNG hàm của hệ (AAD gắn với webhook_ma) — không tự dựng lại cách giải mã.
sec = bao_mat.giai_ma_wh(r_tk["webhook_secret_ma_hoa"], wh_vtp)

# --- (a) lượt HỢP LỆ phải đo TRƯỚC đợt lụt, vì đợt lụt làm cạn ngân sách của mã webhook này ---
payload = json.dumps({"event": "dang_giao", "tracking_number": mvd,
                      "event_id": "e2e-evt-1", "time": "2026-10-15T01:00:00+07:00"},
                     ensure_ascii=False).encode()
sig = hmac.new(sec.encode(), payload, hashlib.sha256).hexdigest()
st, kq = goi(f"/api/v2/webhook/nhan/{wh_vtp}", "POST", tho=payload,
             hdr={"X-Webhook-Signature": sig})
b("9. NHẬN WEBHOOK (chữ ký ĐÚNG)", st == 202, f"HTTP {st} · {kq}")
import time as _t
r = None
for _ in range(40):
    _t.sleep(0.2)
    r = sql("SELECT trang_thai, so_lan_thu, loi_cuoi FROM wh_su_kien ORDER BY id DESC LIMIT 1")
    if r and r[0]["trang_thai"] in ("xong", "loi", "dlq"): break
b("   sự kiện được xử xong", bool(r) and r[0]["trang_thai"] == "xong",
  f"trạng thái={r[0]['trang_thai'] if r else '?'} lỗi={r[0]['loi_cuoi'] if r else ''}")
d3 = sql("SELECT trang_thai_giao, hang_trang_thai_giao FROM don_hang WHERE id=?", (don_id,))[0]
b("10. TRẠNG THÁI ĐƠN cập nhật TỪ webhook", d3["trang_thai_giao"] == "dang_giao",
  f"trục giao vận={d3['trang_thai_giao']} (hạng {d3['hang_trang_thai_giao']})")
st2, kq2 = goi(f"/api/v2/webhook/nhan/{wh_vtp}", "POST", tho=payload,
               hdr={"X-Webhook-Signature": sig})
n_sk = len(sql("SELECT id FROM wh_su_kien WHERE event_id='e2e-evt-1'"))
b("   gửi lại cùng event_id → idempotent", st2 == 200 and n_sk == 1,
  f"HTTP {st2} · {kq2.get('ket_qua') if isinstance(kq2, dict) else ''} · {n_sk} sự kiện trong CSDL")

# --- (b) sự kiện ĐẾN MUỘN: hạng thấp hơn thì KHÔNG được đẩy trạng thái lùi ---
pl_muon = json.dumps({"event": "cho_lay", "tracking_number": mvd,
                      "event_id": "e2e-evt-0", "time": "2026-10-14T01:00:00+07:00"},
                     ensure_ascii=False).encode()
goi(f"/api/v2/webhook/nhan/{wh_vtp}", "POST", tho=pl_muon,
    hdr={"X-Webhook-Signature": hmac.new(sec.encode(), pl_muon, hashlib.sha256).hexdigest()})
for _ in range(25):
    _t.sleep(0.2)
    if sql("SELECT trang_thai FROM wh_su_kien WHERE event_id='e2e-evt-0'") and \
       sql("SELECT trang_thai FROM wh_su_kien WHERE event_id='e2e-evt-0'")[0]["trang_thai"] \
       in ("xong", "loi", "dlq"): break
d4 = sql("SELECT trang_thai_giao FROM don_hang WHERE id=?", (don_id,))[0]
b("   sự kiện đến MUỘN không đẩy trạng thái lùi", d4["trang_thai_giao"] == "dang_giao",
  f"vẫn là {d4['trang_thai_giao']}, không lùi về cho_lay (rank guard)")

# --- (c) chữ ký sai + trần đếm-lỗi ---
st, _ = goi(f"/api/v2/webhook/nhan/{wh_vtp}", "POST", tho=b'{"x":1}',
            hdr={"X-Webhook-Signature": "sai-be-bet"})
b("   chữ ký SAI → 401", st == 401, f"HTTP {st}")
ma_sai = []
for _ in range(14):
    s2, _ = goi(f"/api/v2/webhook/nhan/{wh_vtp}", "POST", tho=b'{"x":1}',
                hdr={"X-Webhook-Signature": "sai"})
    ma_sai.append(s2)
b("   [r33] lụt chữ ký sai bị chặn", 429 in ma_sai,
  f"14 lượt sai → mã {sorted(set(ma_sai))} (trần webhook.chu_ky_sai = 10/60s)")
r_jt = sql("SELECT webhook_ma FROM carrier_accounts WHERE id=?", (tk_jt,))[0]
b("   trần khoanh theo TỪNG mã webhook",
  goi(f"/api/v2/webhook/nhan/{r_jt['webhook_ma']}", "POST", tho=b'{"x":1}',
      hdr={"X-Webhook-Signature": "sai"})[0] == 401,
  "mã webhook bị chặn KHÔNG làm chết tài khoản hãng khác")

print("\n── 10-11. TRẠNG THÁI + LỊCH SỬ ────────────────────────")
# ROUTE MỚI 3: đối soát tay
# `doi_soat_tay` CHỈ dành cho đơn mắc ở `dang_gui` — tức hãng trả kết quả KHÔNG RÕ (timeout).
# Đơn đã `da_gui` thì trả 409, và đó là đúng. Nên phải dựng đúng ca đó: một đơn thứ ba, duyệt,
# rồi ép sang `dang_gui` bằng SQL để mô phỏng lượt gửi timeout — không có cách nào bắt adapter
# mock timeout từ bên ngoài.
st_c, kq_c = goi("/api/v2/don", "POST",
                 {"nguoi_nhan_ten": "Lê Văn C", "nguoi_nhan_sdt": "0933222111",
                  "nguoi_nhan_dia_chi": "77 Nguyễn Huệ, Q1, TP HCM", "hang_hoa": "Mũ",
                  "khoi_luong_gram": 300, "cod": 0,
                  "nguoi_gui_ten": "Kho E2E", "nguoi_gui_sdt": "0900000000",
                  "nguoi_gui_dia_chi": "1 Kho, Q7, TP HCM"})
don_c = kq_c["don"]["id"]
goi(f"/api/v2/don/{don_c}/duyet", "POST", {})
sql("UPDATE don_hang SET trang_thai='dang_gui', carrier_account_id=?,"
    " can_doi_soat_ket_qua=1 WHERE id=?", (tk_vtp, don_c))
st, kq = goi(f"/api/v2/don/{don_c}/doi-soat", "POST", {})
b("   [R02] đối soát đơn MẮC ở dang_gui", st == 200 and kq.get("ket_luan") in
  ("da_vao", "chua_vao", "van_chua_ro"),
  f"HTTP {st} · kết luận={kq.get('ket_luan')} thao tác={kq.get('thao_tac')} mock={kq.get('la_mock')}")
sql("UPDATE don_hang SET trang_thai='dang_gui', can_doi_soat_ket_qua=1 WHERE id=?", (don_c,))
st, kq = goi(f"/api/v2/don/{don_c}/doi-soat-tay", "POST",
             {"ket_luan": "da_vao", "ma_van_don": "VTP-NGUOI-XAC-NHAN-1",
              "ghi_chu": "Gọi tổng đài hãng xác nhận lúc 09:15"})
b("   [R03] POST /don/{id}/doi-soat-tay", st == 200 and kq.get("nguon") == "nguoi",
  f"HTTP {st} · nguồn={kq.get('nguon')} — vết ghi rõ KẾT LUẬN DO NGƯỜI, không phải do hãng")
st, kq = goi(f"/api/v2/don/{don_id}/doi-soat-tay", "POST",
             {"ket_luan": "da_vao", "ma_van_don": mvd})
b("   [R03] đối soát tay đơn ĐÃ gửi → 409", st == 409,
  f"HTTP {st} — chỉ đơn mắc ở dang_gui mới cần người kết luận")
# ROUTE MỚI 7: hành trình
st, kq = goi(f"/api/v2/don/{don_id}/hanh-trinh")
b("10-11. [R07] GET /don/{id}/hanh-trinh", st == 200 and kq.get("so_moc", 0) > 0,
  f"HTTP {st} · {kq.get('so_moc')} mốc · trục={sorted({m['truc'] for m in kq.get('moc', [])})}")
for m in (kq.get("moc") or [])[:6]:
    print(f"       · {m['luc']} [{m['truc']}] {m['noi_dung'][:62]}")

print("\n── G06: hai điểm cắm webhook ──────────────────────────")
st, kq = goi("/api/v2/webhook/su-kien")
b("   [G06-2] cột soát được phơi ra", st == 200 and kq.get("co_cot_soat") is True,
  f"HTTP {st} · co_cot_soat={kq.get('co_cot_soat')} · {len(kq.get('su_kien', []))} sự kiện")
st, kq = goi("/api/v2/webhook/su-kien?can_soat=1")
b("   [G06-2] lọc ?can_soat=1", st == 200, f"HTTP {st} · {len(kq.get('su_kien', []))} sự kiện cần soát")
st, kq = goi("/api/v2/webhook/su-kien/999999/replay", "POST", {})
b("   [G06-1] replay ID không có → 404 (KHÔNG 409)", st == 404,
  f"HTTP {st} — 409 sẽ phân biệt được 'có ở tenant khác' với 'không có' ⇒ dò được ID")

print("\n── chặn: hạn mức + trần ───────────────────────────────")
st, kq = goi("/api/v2/billing/han-muc-nhap")
print(f"  (cửa hạn mức nhập: HTTP {st} — AG-01 đề xuất, chưa mở, không tính là ca)")

tot = sum(1 for d, _, _ in B if d)
print(f"\n{'='*58}\nKẾT QUẢ: {tot}/{len(B)} phép đo đạt")
for d, t, g in B:
    if not d: print(f"  ✗ {t} — {g}")
sys.exit(0 if tot == len(B) else 1)
