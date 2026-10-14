# Bảo mật v2: mật khẩu, phiên, TENANT CONTEXT theo membership, RBAC tra CSDL, mã hóa credentials.
# Luật cứng: tenant_id KHÔNG BAO GIỜ lấy từ request body/query — chỉ từ phiên đã xác thực
# và chỉ sau khi xác minh membership còn hiệu lực.
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta

import cau_hinh
import csdl
import quyen


# ====== Mật khẩu ======
def bam_mat_khau(mat_khau: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.pbkdf2_hmac("sha256", mat_khau.encode(), salt, cau_hinh.PBKDF2_VONG)
    return f"pbkdf2${cau_hinh.PBKDF2_VONG}${salt.hex()}${h.hex()}"


def kiem_mat_khau(mat_khau: str, luu: str) -> bool:
    try:
        _, vong, salt_hex, h_hex = luu.split("$")
        h = hashlib.pbkdf2_hmac("sha256", mat_khau.encode(), bytes.fromhex(salt_hex), int(vong))
        return hmac.compare_digest(h.hex(), h_hex)
    except (ValueError, TypeError):
        return False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ====== Membership ======
def memberships_cua(user_id, chi_hoat_dong=True):
    """Danh sách tenant user được vào (membership hoạt động + tenant hoạt động)."""
    sql = ("SELECT m.id mem_id, m.tenant_id, m.role, m.trang_thai tt_mem,"
           " t.ten tenant_ten, t.code tenant_code, t.trang_thai tt_tenant"
           " FROM tenant_memberships m JOIN tenants t ON t.id=m.tenant_id WHERE m.user_id=?")
    if chi_hoat_dong:
        sql += " AND m.trang_thai='hoat_dong' AND t.trang_thai='hoat_dong'"
    return csdl.nhieu(sql + " ORDER BY t.id", (user_id,))


def membership(user_id, tenant_id):
    """Membership CÒN HIỆU LỰC của user ở tenant (tenant phải đang hoạt động), hoặc None."""
    return csdl.mot(
        "SELECT m.*, t.ten tenant_ten, t.code tenant_code FROM tenant_memberships m"
        " JOIN tenants t ON t.id=m.tenant_id"
        " WHERE m.user_id=? AND m.tenant_id=? AND m.trang_thai='hoat_dong'"
        " AND t.trang_thai='hoat_dong'", (user_id, tenant_id))


# ====== Đăng nhập / phiên ======
def dang_nhap(ten_dang_nhap, mat_khau, dia_chi=None):
    """Trả (token, user_row) hoặc (None, lý_do). Thông báo lỗi KHÔNG tiết lộ tài khoản có tồn tại hay không."""
    CHUNG = "sai tên đăng nhập hoặc mật khẩu"
    u = csdl.mot("SELECT * FROM users WHERE ten_dang_nhap=?", (ten_dang_nhap,))
    if not u:
        csdl.audit("dang_nhap_that_bai", f"user:{ten_dang_nhap}", "không có tài khoản",
                   dia_chi=dia_chi, ket_qua="that_bai")
        return None, CHUNG
    if u["trang_thai"] == "khoa":
        csdl.audit("dang_nhap_that_bai", f"user:{u['id']}", "tài khoản bị khóa",
                   user_id=u["id"], dia_chi=dia_chi, ket_qua="tu_choi")
        return None, "tài khoản đã bị khóa — liên hệ quản trị"
    if not kiem_mat_khau(mat_khau, u["mat_khau_hash"]):
        so_sai = u["so_lan_sai"] + 1
        if so_sai >= cau_hinh.KHOA_SAU_SO_LAN_SAI:
            csdl.ghi("UPDATE users SET so_lan_sai=?, trang_thai='khoa' WHERE id=?", (so_sai, u["id"]))
            thu_hoi_moi_phien(u["id"])
            csdl.audit("khoa_tai_khoan_tu_dong", f"user:{u['id']}", f"sai mật khẩu {so_sai} lần",
                       user_id=u["id"], dia_chi=dia_chi, ket_qua="tu_choi")
            return None, CHUNG   # không nói ra là vừa bị khóa (tránh dò tài khoản)
        csdl.ghi("UPDATE users SET so_lan_sai=? WHERE id=?", (so_sai, u["id"]))
        csdl.audit("dang_nhap_that_bai", f"user:{u['id']}", "sai mật khẩu",
                   user_id=u["id"], dia_chi=dia_chi, ket_qua="that_bai")
        return None, CHUNG

    ds = memberships_cua(u["id"])
    if u["platform_role"] is None and not ds:
        csdl.audit("dang_nhap_that_bai", f"user:{u['id']}", "không có membership hoạt động",
                   user_id=u["id"], dia_chi=dia_chi, ket_qua="tu_choi")
        return None, "tài khoản chưa được gán vào doanh nghiệp nào đang hoạt động"

    csdl.ghi("UPDATE users SET so_lan_sai=0 WHERE id=?", (u["id"],))
    token = secrets.token_urlsafe(32)
    het_han = (datetime.now() + timedelta(hours=cau_hinh.PHIEN_SONG_GIO)).strftime("%Y-%m-%d %H:%M:%S")
    active = ds[0]["tenant_id"] if ds else None
    csdl.ghi("INSERT INTO sessions (token_hash, user_id, active_tenant_id, tao_luc, het_han, dia_chi)"
             " VALUES (?,?,?,?,?,?)",
             (_hash_token(token), u["id"], active, csdl.bay_gio(), het_han, dia_chi))
    csdl.audit("dang_nhap", f"user:{u['id']}", "", tenant_id=active, user_id=u["id"], dia_chi=dia_chi)
    return token, u


class NguCanh:
    """Tenant Context đã được backend xác minh: user + tenant đang thao tác + vai trò."""
    def __init__(self, user, token, tenant_id=None, role=None, tenant_ten=None):
        self.user = user
        self.user_id = user["id"]
        self.token = token
        self.tenant_id = tenant_id          # None = đang ở ngữ cảnh nền tảng
        self.role = role                    # vai trò áp dụng cho yêu cầu hiện tại
        self.tenant_ten = tenant_ten
        self.platform_role = user["platform_role"]

    def co_quyen(self, hanh_dong):
        return quyen.co_quyen(self.role, hanh_dong)


def ngu_canh(token):
    """AUTHENTICATE → RESOLVE MEMBERSHIP → SELECT ACTIVE TENANT. Trả NguCanh hoặc None.
    Mỗi yêu cầu đều xác minh lại: phiên còn hiệu lực, user hoạt động, membership còn hiệu lực."""
    if not token:
        return None
    s = csdl.mot("SELECT * FROM sessions WHERE token_hash=?", (_hash_token(token),))
    if not s or s["thu_hoi"]:
        return None
    if s["het_han"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        return None
    u = csdl.mot("SELECT * FROM users WHERE id=?", (s["user_id"],))
    if not u or u["trang_thai"] != "hoat_dong":
        return None

    if s["active_tenant_id"] is not None:
        m = membership(u["id"], s["active_tenant_id"])   # membership/tenant bị vô hiệu → mất quyền ngay
        if m:
            return NguCanh(u, token, m["tenant_id"], m["role"], m["tenant_ten"])
        # active tenant không còn hợp lệ: thử tenant khác còn hiệu lực
        ds = memberships_cua(u["id"])
        if ds:
            csdl.ghi("UPDATE sessions SET active_tenant_id=? WHERE token_hash=?",
                     (ds[0]["tenant_id"], _hash_token(token)))
            return NguCanh(u, token, ds[0]["tenant_id"], ds[0]["role"], ds[0]["tenant_ten"])
        if u["platform_role"] is None:
            return None
    if u["platform_role"]:
        return NguCanh(u, token, None, u["platform_role"], None)
    ds = memberships_cua(u["id"])
    if not ds:
        return None
    return NguCanh(u, token, ds[0]["tenant_id"], ds[0]["role"], ds[0]["tenant_ten"])


def doi_tenant(nc, tenant_id):
    """Switch tenant: chỉ đổi khi membership còn hiệu lực. Không mang dữ liệu tenant cũ sang."""
    m = membership(nc.user_id, tenant_id)
    if not m:
        csdl.audit("doi_tenant", f"tenant:{tenant_id}", "không có membership hiệu lực",
                   user_id=nc.user_id, ket_qua="tu_choi")
        return None
    csdl.ghi("UPDATE sessions SET active_tenant_id=? WHERE token_hash=?",
             (tenant_id, _hash_token(nc.token)))
    csdl.audit("doi_tenant", f"tenant:{tenant_id}", f"vai trò {m['role']}",
               tenant_id=tenant_id, user_id=nc.user_id)
    return m


def dang_xuat(token):
    csdl.ghi("UPDATE sessions SET thu_hoi=1 WHERE token_hash=?", (_hash_token(token),))


def thu_hoi_moi_phien(user_id, tru_token=None):
    if tru_token:
        csdl.ghi("UPDATE sessions SET thu_hoi=1 WHERE user_id=? AND token_hash<>?",
                 (user_id, _hash_token(tru_token)))
    else:
        csdl.ghi("UPDATE sessions SET thu_hoi=1 WHERE user_id=?", (user_id,))


# ====== Quên mật khẩu (provider giả lập — chưa cấu hình SMTP) ======
def tao_token_reset(ten_dang_nhap):
    """Trả token nếu tài khoản tồn tại, None nếu không — NHƯNG caller luôn trả cùng một thông báo
    cho người dùng để không lộ tài khoản nào có thật."""
    u = csdl.mot("SELECT * FROM users WHERE ten_dang_nhap=?", (ten_dang_nhap,))
    if not u:
        return None
    token = secrets.token_urlsafe(32)
    het_han = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
    csdl.ghi("INSERT INTO reset_tokens (token_hash, user_id, het_han, tao_luc) VALUES (?,?,?,?)",
             (_hash_token(token), u["id"], het_han, csdl.bay_gio()))
    csdl.audit("yeu_cau_reset_mat_khau", f"user:{u['id']}", "", user_id=u["id"])
    return token


def dat_lai_mat_khau(token, mat_khau_moi):
    """Dùng token reset một lần. Trả (ok, lý do)."""
    if len(mat_khau_moi or "") < 8:
        return False, "mật khẩu mới phải từ 8 ký tự"
    r = csdl.mot("SELECT * FROM reset_tokens WHERE token_hash=?", (_hash_token(token),))
    if not r or r["da_dung"]:
        return False, "token không hợp lệ hoặc đã dùng"
    if r["het_han"] < datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        return False, "token đã hết hạn"
    csdl.ghi("UPDATE users SET mat_khau_hash=?, doi_mat_khau_luc=?, so_lan_sai=0 WHERE id=?",
             (bam_mat_khau(mat_khau_moi), csdl.bay_gio(), r["user_id"]))
    csdl.ghi("UPDATE reset_tokens SET da_dung=1 WHERE token_hash=?", (_hash_token(token),))
    thu_hoi_moi_phien(r["user_id"])     # đổi mật khẩu → mọi phiên cũ hết hiệu lực
    csdl.audit("dat_lai_mat_khau", f"user:{r['user_id']}", "qua token reset", user_id=r["user_id"])
    return True, ""


# ====== Mã hóa credentials: AES-256-GCM ======
# Owner duyệt 14/10/2026: chuyển từ bản tự dựng (XOR+HMAC) sang AES-256-GCM chuẩn.
# Dùng `cryptography` (thư viện đã được kiểm định) — KHÔNG tự cài đặt AES.
#
# Định dạng bản mã:
#   v2$<nonce_hex>$<ciphertext_hex>   ← AES-256-GCM (nonce 96 bit, tag nằm trong ciphertext)
#   <nonce>$<ct>$<mac>                ← v1 cũ (XOR+HMAC), CHỈ còn đọc được để migrate
#
# AAD (additional authenticated data) buộc bản mã vào ĐÚNG chỗ của nó: chép bản mã của tenant A
# sang hàng của tenant B sẽ giải mã HỎNG. Xây AAD ở một nơi duy nhất để bên ghi và bên đọc
# không thể lệch nhau.
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as _e:   # KHÔNG âm thầm tụt về sơ đồ yếu — hỏng thì phải hỏng to
    raise ImportError(
        "Thiếu thư viện 'cryptography' — bắt buộc cho AES-256-GCM. Cài: python3 -m pip install cryptography. "
        "Hệ thống CỐ Ý không chạy tiếp bằng sơ đồ mã hóa yếu."
    ) from _e


def aad_credentials(tenant_id, hang) -> str:
    """AAD cho credentials của tài khoản hãng — buộc vào tenant + hãng."""
    return f"cred:{tenant_id}:{hang}"


def aad_webhook(webhook_ma) -> str:
    """AAD cho webhook secret — buộc vào định danh webhook công khai."""
    return f"wh:{webhook_ma}"


def _khoa_noi_bo() -> bytes:
    """Khóa 32 byte (AES-256) trong file 0600, ngoài git. Tạo lần đầu nếu chưa có."""
    duong = cau_hinh.DUONG_DAN_KHOA
    if not os.path.exists(duong):
        os.makedirs(os.path.dirname(duong), exist_ok=True)
        with open(duong, "wb") as f:
            f.write(secrets.token_bytes(32))
        os.chmod(duong, 0o600)
    with open(duong, "rb") as f:
        khoa = f.read()
    if len(khoa) != 32:
        raise ValueError(f"Khóa nội bộ phải đúng 32 byte cho AES-256, đang có {len(khoa)} byte")
    return khoa


def ma_hoa(ro: str, aad: str = "") -> str:
    """Mã hóa bằng AES-256-GCM. aad buộc bản mã vào ngữ cảnh của nó (xem aad_*)."""
    nonce = secrets.token_bytes(12)          # 96 bit — kích thước chuẩn cho GCM
    ct = AESGCM(_khoa_noi_bo()).encrypt(nonce, ro.encode(), aad.encode() if aad else None)
    return "v2$" + nonce.hex() + "$" + ct.hex()


def _giai_ma_v1(goi: str) -> str:
    """Đọc bản mã ĐỊNH DẠNG CŨ (XOR keystream + HMAC). Chỉ dùng khi migrate, không mã hóa mới nữa."""
    key = _khoa_noi_bo()
    nonce_hex, ct_hex, mac = goi.split("$")
    nonce, ct = bytes.fromhex(nonce_hex), bytes.fromhex(ct_hex)
    if not hmac.compare_digest(mac, hmac.new(key, nonce + ct, hashlib.sha256).hexdigest()):
        raise ValueError("MAC sai — dữ liệu mã hóa (v1) đã bị sửa")
    ra, dem = b"", 0
    while len(ra) < len(ct):
        ra += hashlib.sha256(key + nonce + dem.to_bytes(4, "big")).digest()
        dem += 1
    return bytes(a ^ b for a, b in zip(ct, ra[:len(ct)])).decode()


def giai_ma(goi: str, aad: str = "") -> str:
    """Giải mã. Tự nhận biết v2 (AES-GCM) hay v1 (cũ). Sai AAD → hỏng, đúng như thiết kế."""
    if goi.startswith("v2$"):
        _, nonce_hex, ct_hex = goi.split("$")
        try:
            ro = AESGCM(_khoa_noi_bo()).decrypt(
                bytes.fromhex(nonce_hex), bytes.fromhex(ct_hex), aad.encode() if aad else None)
        except Exception as e:
            raise ValueError(f"Giải mã AES-GCM hỏng (sai khóa, sai AAD, hoặc dữ liệu bị sửa): {type(e).__name__}")
        return ro.decode()
    return _giai_ma_v1(goi)


def la_dinh_dang_cu(goi: str) -> bool:
    return not str(goi).startswith("v2$")


# --- CẶP hàm theo từng loại secret ---
# Bên ghi và bên đọc dùng CHUNG một hàm dựng AAD, nên không thể lệch nhau. Trước đây hai bên
# tự gọi ma_hoa()/giai_ma() rồi tự truyền AAD: chỉ cần một chỗ quên là bản mã thành không đọc được
# (đã dính thật 14/10/2026 — webhook trả 500 vì bên ghi quên AAD). Đừng dùng ma_hoa/giai_ma trần
# cho credentials và webhook secret nữa; dùng bốn hàm dưới đây.

def ma_hoa_cred(cred: dict, tenant_id, hang):
    """Mã hóa credentials của tài khoản hãng. Trả (bản_mã, đuôi_hiển_thị)."""
    ro = json.dumps(cred, ensure_ascii=False)
    duoi = next((str(v)[-4:] for v in cred.values() if v), "")
    return ma_hoa(ro, aad_credentials(tenant_id, hang)), duoi


def giai_ma_cred(ban_ma, tenant_id, hang) -> dict:
    return json.loads(giai_ma(ban_ma, aad_credentials(tenant_id, hang)))


def ma_hoa_wh(secret: str, webhook_ma: str) -> str:
    return ma_hoa(secret, aad_webhook(webhook_ma))


def giai_ma_wh(ban_ma: str, webhook_ma: str) -> str:
    return giai_ma(ban_ma, aad_webhook(webhook_ma))


def luu_credentials(cred: dict, aad: str = ""):
    """CŨ — giữ cho tương thích. Dùng ma_hoa_cred() để khỏi tự dựng AAD."""
    ro = json.dumps(cred, ensure_ascii=False)
    duoi = next((str(v)[-4:] for v in cred.values() if v), "")
    return ma_hoa(ro, aad), duoi
