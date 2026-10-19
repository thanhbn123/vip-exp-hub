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
import secret_provider


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
        csdl.audit("dang_nhap_that_bai", f"user:{u['id']}", "tài khoản bị quản trị khóa",
                   user_id=u["id"], dia_chi=dia_chi, ket_qua="tu_choi")
        # r07: trước đây ca này trả thông điệp RIÊNG, nên người vô danh gõ mật khẩu rác vẫn
        # phân biệt được "tên có thật đang bị khóa" với "tên không tồn tại" ⇒ dò ra tài khoản.
        # Hai ca khóa còn lại (khóa tạm) đã trả CHUNG từ trước; ca này là chỗ sót.
        # Người bị quản trị khóa biết lý do qua kênh khác (quản trị nói), không qua trang đăng nhập.
        return None, CHUNG
    bay = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if u["khoa_den"] and u["khoa_den"] > bay:
        csdl.audit("dang_nhap_that_bai", f"user:{u['id']}", f"đang khóa tạm tới {u['khoa_den']}",
                   user_id=u["id"], dia_chi=dia_chi, ket_qua="tu_choi")
        return None, CHUNG          # không nói ra là đang khóa tạm (tránh dò tài khoản)
    if not kiem_mat_khau(mat_khau, u["mat_khau_hash"]):
        so_sai = u["so_lan_sai"] + 1
        if so_sai >= cau_hinh.KHOA_SAU_SO_LAN_SAI:
            # KHÓA TẠM, tự mở sau KHOA_TAM_PHUT. Không khóa vĩnh viễn để người lạ không
            # vô hiệu hóa được tài khoản người khác chỉ bằng mật khẩu sai.
            den = (datetime.now() + timedelta(minutes=cau_hinh.KHOA_TAM_PHUT)
                   ).strftime("%Y-%m-%d %H:%M:%S")
            csdl.ghi("UPDATE users SET so_lan_sai=0, khoa_den=? WHERE id=?", (den, u["id"]))
            csdl.audit("khoa_tam_tai_khoan", f"user:{u['id']}",
                       f"sai mật khẩu {so_sai} lần → khóa tạm tới {den}",
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

    csdl.ghi("UPDATE users SET so_lan_sai=0, khoa_den=NULL WHERE id=?", (u["id"],))
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
    # r29: CHỈ MỘT token sống cho mỗi tài khoản. Trước đây mỗi lượt "quên mật khẩu" thêm một
    # token mà không giết token trước, nên 5 lượt = 5 token dùng được đồng thời trong 30 phút —
    # kẻ xấu xin một token rồi chờ, chính chủ xin token mới và đặt lại, token của kẻ xấu VẪN
    # còn sống. Đánh dấu `da_dung` (không DELETE) để còn dấu vết cho audit — §19 luật thùng rác.
    csdl.ghi("UPDATE reset_tokens SET da_dung=1 WHERE user_id=? AND da_dung=0", (u["id"],))
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
    # ĐỔI MẬT KHẨU LÀ VÔ HIỆU MỌI TOKEN RESET CŨ (AG-01, S01 — vá 15/10/2026).
    # Trước đây hàm này chỉ kiểm `da_dung` + `het_han`, nên chuỗi sau đây CHẠY ĐƯỢC: kẻ xấu xin
    # token lúc T → chính chủ phát hiện, tự đổi mật khẩu lúc T+1 qua /auth/doi-mat-khau → token
    # cũ VẪN còn hiệu lực tới T+30 phút, kẻ xấu đặt lại mật khẩu và chiếm tài khoản. Chính chủ
    # làm đúng mọi thứ mà vẫn mất tài khoản, và không có gì báo lỗi.
    # So theo MỐC (không đánh dấu từng token) để mọi token cũ — kể cả token sinh ở phiên khác,
    # kể cả token chưa ai biết là có — cùng chết một lúc. Quên một token thì mất tài khoản, nên
    # đây phải là phép so bao trùm, không phải danh sách phải nhớ.
    u = csdl.mot("SELECT doi_mat_khau_luc FROM users WHERE id=?", (r["user_id"],))
    if u and u["doi_mat_khau_luc"] and r["tao_luc"] and r["tao_luc"] < u["doi_mat_khau_luc"]:
        csdl.audit("dat_lai_mat_khau", f"user:{r['user_id']}",
                   "từ chối: token sinh trước lần đổi mật khẩu gần nhất",
                   user_id=r["user_id"], ket_qua="tu_choi")
        return False, "token không hợp lệ hoặc đã dùng"
    # MỞ KHÓA luôn: trước đây chỉ xóa so_lan_sai mà giữ trang_thai='khoa', nên chính chủ đặt
    # lại mật khẩu xong vẫn không đăng nhập được — và kẻ xấu khóa tài khoản người khác từ xa
    # bằng 5 lần đoán sai thì nạn nhân không có đường tự mở (AG-07, ca q06).
    csdl.ghi("UPDATE users SET mat_khau_hash=?, doi_mat_khau_luc=?, so_lan_sai=0, khoa_den=NULL"
             " WHERE id=?",
             (bam_mat_khau(mat_khau_moi), csdl.bay_gio(), r["user_id"]))
    csdl.ghi("UPDATE reset_tokens SET da_dung=1 WHERE token_hash=?", (_hash_token(token),))
    thu_hoi_moi_phien(r["user_id"])     # đổi mật khẩu → mọi phiên cũ hết hiệu lực
    csdl.audit("dat_lai_mat_khau", f"user:{r['user_id']}", "qua token reset", user_id=r["user_id"])
    return True, ""


# ====== Mã hóa credentials: AES-256-GCM ======
# Owner duyệt 14/10/2026: chuyển từ bản tự dựng (XOR+HMAC) sang AES-256-GCM chuẩn.
# Dùng `cryptography` (thư viện đã được kiểm định) — KHÔNG tự cài đặt AES.
#
# Định dạng bản mã (ĐỌC được cả ba, secret MỚI luôn ghi bằng v3):
#   v3$<key_id>$<nonce_hex>$<ciphertext_hex>   ← AES-256-GCM CÓ định danh khóa → xoay khóa được
#   v2$<nonce_hex>$<ciphertext_hex>            ← AES-256-GCM không key_id (khóa 'goc'), chỉ đọc
#   <nonce>$<ct>$<mac>                         ← v1 cũ (XOR+HMAC), CHỈ còn đọc để migrate
#
# Vì sao thêm v3: bản mã v2 không nói nó dùng khóa nào, nên đổi khóa là mọi bản mã cũ thành rác
# → thực tế KHÔNG xoay khóa được. v3 mang key_id, nên khóa cũ và khóa mới sống song song: bản nào
# chưa kịp chuyển vẫn giải được bằng đúng khóa của nó. Khóa do `secret_provider` cấp.
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
    """Khóa 32 byte của ĐỊNH DẠNG CŨ (v1/v2 — bản mã không mang key_id), file 0600, ngoài git.

    Giữ lại vì bản mã v1/v2 không nói nó dùng khóa nào, nên chỉ có một chỗ để tra: file này.
    Secret MỚI không dùng đường này nữa — xem ma_hoa_v3() và secret_provider.
    """
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
    """ĐỊNH DẠNG v2 — CHỈ dùng cho đường migrate lịch sử (nang_len_v3) và tương thích ngược.

    Bản mã v2 KHÔNG mang key_id nên KHÔNG xoay khóa được. Secret mới phải dùng ma_hoa_v3()
    (hoặc bốn hàm contract ma_hoa_cred/giai_ma_cred/ma_hoa_wh/giai_ma_wh gọi sẵn v3).
    """
    nonce = secrets.token_bytes(12)          # 96 bit — kích thước chuẩn cho GCM
    ct = AESGCM(_khoa_noi_bo()).encrypt(nonce, ro.encode(), aad.encode() if aad else None)
    return "v2$" + nonce.hex() + "$" + ct.hex()


def ma_hoa_v3(ro: str, aad: str = "", key_id=None) -> str:
    """Mã hóa AES-256-GCM CÓ key_id: `v3$<key_id>$<nonce>$<ct>`. Đây là đường ghi mặc định.

    key_id=None → dùng khóa hiện hành do secret_provider cấp.
    """
    if key_id is None:
        key_id, khoa = secret_provider.nha_cung_cap().khoa_hien_hanh()
    else:
        key_id = secret_provider.kiem_key_id(key_id)
        khoa = secret_provider.nha_cung_cap().lay_khoa(key_id)
    nonce = secrets.token_bytes(12)
    ct = AESGCM(khoa).encrypt(nonce, ro.encode(), aad.encode() if aad else None)
    return "v3$" + key_id + "$" + nonce.hex() + "$" + ct.hex()


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
    """Giải mã. Tự nhận v3 (có key_id), v2 (khóa cũ) hay v1. Sai khóa/AAD → hỏng, đúng thiết kế."""
    goi = str(goi)
    if goi.startswith("v3$"):
        phan = goi.split("$")
        if len(phan) != 4:
            raise ValueError(f"Bản mã v3 sai cấu trúc: cần 4 phần, có {len(phan)}")
        _, key_id, nonce_hex, ct_hex = phan
        khoa = secret_provider.nha_cung_cap().lay_khoa(key_id)   # thiếu khóa → LoiKhoa, không im
        return _giai_gcm(khoa, nonce_hex, ct_hex, aad, f"v3 key_id={key_id}")
    if goi.startswith("v2$"):
        _, nonce_hex, ct_hex = goi.split("$")
        return _giai_gcm(_khoa_noi_bo(), nonce_hex, ct_hex, aad, "v2")
    return _giai_ma_v1(goi)


def _giai_gcm(khoa: bytes, nonce_hex: str, ct_hex: str, aad: str, nhan: str) -> str:
    try:
        ro = AESGCM(khoa).decrypt(bytes.fromhex(nonce_hex), bytes.fromhex(ct_hex),
                                  aad.encode() if aad else None)
    except Exception as e:
        # KHÔNG đưa nội dung bản mã hay khóa vào thông báo lỗi — lỗi thường bị ghi ra log.
        raise ValueError(f"Giải mã AES-GCM ({nhan}) hỏng (sai khóa, sai AAD, hoặc dữ liệu bị sửa): "
                         f"{type(e).__name__}")
    return ro.decode()


def la_dinh_dang_cu(goi: str) -> bool:
    """True nếu bản mã còn ở định dạng v1 (XOR+HMAC) — cần migrate."""
    return not str(goi).startswith(("v2$", "v3$"))


def key_id_cua(goi: str):
    """key_id trong bản mã, hoặc None nếu bản mã không mang key_id (v1/v2)."""
    goi = str(goi)
    if not goi.startswith("v3$"):
        return None
    phan = goi.split("$")
    return phan[1] if len(phan) == 4 else None


def can_xoay(goi: str, key_id_dich=None) -> bool:
    """True nếu bản mã này chưa nằm dưới khóa hiện hành (hoặc khóa đích) — cần mã hóa lại."""
    if key_id_dich is None:
        key_id_dich = secret_provider.nha_cung_cap().khoa_hien_hanh()[0]
    return key_id_cua(goi) != key_id_dich


# --- CẶP hàm theo từng loại secret ---
# Bên ghi và bên đọc dùng CHUNG một hàm dựng AAD, nên không thể lệch nhau. Trước đây hai bên
# tự gọi ma_hoa()/giai_ma() rồi tự truyền AAD: chỉ cần một chỗ quên là bản mã thành không đọc được
# (đã dính thật 14/10/2026 — webhook trả 500 vì bên ghi quên AAD). Đừng dùng ma_hoa/giai_ma trần
# cho credentials và webhook secret nữa; dùng bốn hàm dưới đây.

def ma_hoa_cred(cred: dict, tenant_id, hang):
    """Mã hóa credentials của tài khoản hãng. Trả (bản_mã, đuôi_hiển_thị). Ghi bằng v3."""
    ro = json.dumps(cred, ensure_ascii=False)
    duoi = next((str(v)[-4:] for v in cred.values() if v), "")
    return ma_hoa_v3(ro, aad_credentials(tenant_id, hang)), duoi


def giai_ma_cred(ban_ma, tenant_id, hang) -> dict:
    return json.loads(giai_ma(ban_ma, aad_credentials(tenant_id, hang)))


def ma_hoa_wh(secret: str, webhook_ma: str) -> str:
    return ma_hoa_v3(secret, aad_webhook(webhook_ma))


def giai_ma_wh(ban_ma: str, webhook_ma: str) -> str:
    return giai_ma(ban_ma, aad_webhook(webhook_ma))


def luu_credentials(cred: dict, aad: str = ""):
    """CŨ — giữ cho tương thích. Dùng ma_hoa_cred() để khỏi tự dựng AAD."""
    ro = json.dumps(cred, ensure_ascii=False)
    duoi = next((str(v)[-4:] for v in cred.values() if v), "")
    return ma_hoa_v3(ro, aad), duoi


# ====== Xoay khóa (key rotation) ======
# Thứ tự CỐ Ý: sinh khóa mới → đặt làm hiện hành → mới mã hóa lại dữ liệu.
# Nếu lượt mã hóa lại hỏng giữa đường thì những hàng chưa chuyển vẫn mang key_id CŨ, và khóa cũ
# vẫn còn trong thư mục khóa, nên vẫn giải được. Đổi thứ tự (xóa khóa cũ trước) là mất dữ liệu.
#
# Khóa cũ KHÔNG BAO GIỜ bị xóa ở đây. Muốn bỏ một khóa cũ thì phải tự tay kiểm không còn bản mã
# nào mang key_id đó — việc đó do người làm, không để lệnh chạy nền tự quyết (CLAUDE.md §19).

def _cap_doc_ghi(kn):
    """Trả (đọc, ghi) chạy được cả trên kết nối dùng chung của csdl lẫn kết nối migrate truyền vào."""
    if kn is None:
        return (lambda sql, p=(): csdl.nhieu(sql, p)), (lambda sql, p=(): csdl.ghi(sql, p))
    kn.row_factory = csdl.Row
    return (lambda sql, p=(): kn.execute(sql, p).fetchall()), (lambda sql, p=(): kn.execute(sql, p))


def ma_hoa_lai_carrier_accounts(kn=None, key_id_dich=None) -> dict:
    """Mã hóa lại MỌI secret trong carrier_accounts sang khóa đích (mặc định: khóa hiện hành).

    Phủ CẢ HAI cột secret: `credentials_ma_hoa` và `webhook_secret_ma_hoa`. Hàng nào không giải
    được thì GHI RA rồi đi tiếp — một hàng hỏng không được làm nổ cả lượt, nhưng cũng không được
    im lặng bỏ qua (secret đó còn nằm dưới khóa cũ cho tới khi có người xử).
    """
    if key_id_dich is None:
        key_id_dich = secret_provider.nha_cung_cap().khoa_hien_hanh()[0]
    doc, ghi_ = _cap_doc_ghi(kn)
    so_cred = so_wh = 0
    da_dat = 0
    hong = []
    for r in doc("SELECT id, tenant_id, hang, webhook_ma, credentials_ma_hoa,"
                 " webhook_secret_ma_hoa FROM carrier_accounts"):
        da_dat += 1
        for cot, ban_ma, aad in (
            ("credentials_ma_hoa", r["credentials_ma_hoa"], aad_credentials(r["tenant_id"], r["hang"])),
            ("webhook_secret_ma_hoa", r["webhook_secret_ma_hoa"], aad_webhook(r["webhook_ma"])),
        ):
            if not can_xoay(ban_ma, key_id_dich):
                continue
            try:
                ro = giai_ma(ban_ma, aad)
            except Exception as e:
                # Bản mã v1 (chưa qua migrate v3) không có AAD — thử lại không AAD trước khi kết luận.
                try:
                    ro = giai_ma(ban_ma, "")
                except Exception:
                    hong.append(f"carrier_account {r['id']} {cot}: {type(e).__name__}")
                    continue
            ghi_(f"UPDATE carrier_accounts SET {cot}=? WHERE id=?",
                 (ma_hoa_v3(ro, aad, key_id=key_id_dich), r["id"]))
            if cot == "credentials_ma_hoa":
                so_cred += 1
            else:
                so_wh += 1
    return {"key_id": key_id_dich, "so_hang_da_doc": da_dat,
            "so_credentials": so_cred, "so_webhook_secret": so_wh, "hong": hong}


def xoay_khoa(user_id=None, dia_chi=None) -> dict:
    """Xoay khóa: sinh khóa mới, đặt hiện hành, mã hóa lại mọi secret sang khóa đó.

    Khóa cũ GIỮ LẠI. Audit chỉ ghi key_id và số lượng — KHÔNG ghi secret, không ghi nội dung khóa.
    KHÔNG đụng `credentials_doi_luc`: cột đó ghi lần đổi CREDENTIALS của hãng, còn đây là đổi KHÓA
    mã hóa; gộp hai việc vào một cột làm mất nghĩa cả hai.

    PHẢI PHỦ CẢ BA TỆP KHO BEST (`xac_thuc_best.credential_dang_nhap/token_truy_cap/
    bearer_webhook`): chúng KHÔNG nằm trong schema, nên quét `carrier_accounts` không đại diện
    cho chúng. Trước bản vá, secret BEST sống mãi dưới khóa cũ mà không ai thấy — tới lúc cho
    nghỉ khóa cũ thì credential/token/bearer thành rác, im lặng (rủi ro #11 của
    docs/BEST_EXPRESS_SECURITY_REVIEW.md). Hàng nào không xoay được thì BÁO RA (`hong`), không
    ghi đè: `xac_thuc_best.ma_hoa_lai_kho` chỉ mã hóa lại bản ghi giải được ĐÚNG slot của nó.
    """
    p = secret_provider.nha_cung_cap()
    key_id_cu = p.khoa_hien_hanh()[0]
    key_id_moi = p.tao_khoa_moi()
    p.dat_khoa_hien_hanh(key_id_moi)
    kq = ma_hoa_lai_carrier_accounts(key_id_dich=key_id_moi)
    kq["key_id_cu"] = key_id_cu
    try:
        import xac_thuc_best
        kq_best = xac_thuc_best.ma_hoa_lai_kho(key_id_moi)
    except Exception:  # noqa: BLE001 — lỗi ở kho tệp KHÔNG được nuốt, nhưng cũng không che
        # việc `carrier_accounts` đã xoay xong. Không đưa chuỗi lỗi gốc vào audit (có thể chứa
        # đường dẫn/định danh lạ); chỉ báo một mã cố định.
        kq_best = {"key_id": key_id_moi, "so_credential_dang_nhap": 0,
                   "so_token_truy_cap": 0, "so_bearer_webhook": 0, "so_ban_ghi": 0,
                   "so_giu_nguyen": 0, "hong": ["best_auth: KHONG_XOAY_DUOC"]}
    kq["best_auth"] = kq_best
    kq["hong"] = list(kq["hong"]) + ["best_auth " + x for x in kq_best.get("hong", [])]
    kq["so_khoa_dang_giu"] = len(p.danh_sach_key_id())
    csdl.audit("xoay_khoa_ma_hoa", f"khoa:{key_id_moi}",
               f"từ {key_id_cu}; mã hóa lại {kq['so_credentials']} credentials"
               f" + {kq['so_webhook_secret']} webhook secret trên {kq['so_hang_da_doc']} tài khoản hãng"
               f"; BEST: {kq_best.get('so_credential_dang_nhap', 0)} credential"
               f" + {kq_best.get('so_token_truy_cap', 0)} token"
               f" + {kq_best.get('so_bearer_webhook', 0)} bearer"
               + (f"; HỎNG: {'; '.join(kq['hong'])}" if kq["hong"] else ""),
               user_id=user_id, dia_chi=dia_chi,
               ket_qua="that_bai" if kq["hong"] else "thanh_cong")
    return kq
