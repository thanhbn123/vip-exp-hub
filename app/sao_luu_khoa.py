# SAO LƯU / KHÔI PHỤC KHÓA MÃ HÓA (S03) — AG-01.
#
# VÌ SAO CÓ FILE NÀY: mất `app/du-lieu/khoa/` là **mất sạch credentials hãng của mọi tenant**.
# Bản mã vẫn còn trong CSDL, sao lưu CSDL vẫn chạy, không có gì báo lỗi — tới lúc cần gọi hãng
# mới biết. Đúng dạng hỏng im lặng (CLAUDE.md §12.2): thứ hỏng không nói ra là nó đã hỏng.
# `secret_provider.lay_khoa` cố ý **không sinh khóa thay thế** khi thiếu khóa, nên nếu không có
# bản sao lưu thì không có đường nào về.
#
# ĐIỀU QUAN TRỌNG NHẤT CỦA THIẾT KẾ NÀY — bản sao lưu được bảo vệ bằng **passphrase riêng do
# người vận hành cấp**, KHÔNG bằng chính khóa đang được sao lưu. Nếu gói backup được mã hóa bằng
# khóa nằm trong gói, thì nó chỉ là một file nén có mật khẩu dán sẵn ở bên trong: mất thư mục
# khóa là vừa mất khóa vừa mất đường mở backup. Nên:
#
#   - Khóa mã hóa gói (KEK) dẫn xuất TỪ PASSPHRASE: PBKDF2-HMAC-SHA256, salt 16 byte ngẫu
#     nhiên mỗi gói, 600.000 vòng.
#   - Passphrase lấy từ biến môi trường `VIP_HUB_BACKUP_PASSPHRASE`, hoặc nhập lúc chạy
#     (`getpass`, chỉ khi có terminal thật). KHÔNG hard-code. KHÔNG tự sinh rồi coi là xong —
#     tự sinh thì nó phải được lưu ở đâu đó, và chỗ đó lại là một bí mật nữa không ai giữ.
#   - Có ca kiểm thẳng: passphrase trùng nội dung một khóa đang sao lưu thì TỪ CHỐI.
#
# BA ĐIỀU CẤM, cưỡng chế bằng mã (không bằng lời dặn):
#   1. Không bao giờ ghi plaintext (khóa thô, credentials đã giải mã) ra file.
#   2. Không bao giờ đặt gói backup trong thư mục static đang được phục vụ
#      (`admin/ pages/ assets/ mock/`) — xem `_kiem_duong_ra`. Static hiện chỉ cho bốn thư mục
#      đó; file này KHÔNG đổi danh sách trắng ấy, chỉ từ chối ghi vào đó.
#   3. Không in khóa/passphrase ra báo cáo, log hay audit. Audit chỉ ghi SỐ LƯỢNG và `key_id`.
#
# GÓI BACKUP — khuôn file (`.vipkb`):
#
#     b"VIPHUBKEYBAK1\n"                 magic 14 byte
#     4 byte big-endian: độ dài header
#     header JSON (utf-8, KHÔNG chứa bí mật nào)
#     ciphertext = AESGCM(KEK).encrypt(nonce, gzip(payload JSON), aad=header_bytes)
#
# Header làm AAD nên sửa header (ví dụ hạ số vòng PBKDF2 xuống 1 để dò passphrase nhanh) là
# giải mã HỎNG. Header để đọc được mà không cần passphrase, nhờ đó kiểm tra được "gói này là của
# ngày nào, mấy khóa" mà không phải mở bí mật ra.
#
# PAYLOAD gồm bốn phần:
#   `khoa`        — từng file khóa (`<key_id>.key`), nội dung base64 + sha256 + con trỏ hiện hành
#   `khoa_cu`     — file khóa một-bản cũ `khoa-noi-bo.key` (bản mã v1/v2 CẦN đúng file này)
#   `ban_ma`      — bản mã credentials/webhook secret + RÀNG BUỘC `tenant_id`/`hang`/`webhook_ma`
#                   (chính là đầu vào dựng AAD — thiếu nó thì khôi phục khóa xong vẫn không giải
#                   được, vì AAD không dựng lại đúng)
#   `sieu_du_lieu`— phiên bản schema, số tenant/tài khoản hãng, danh sách tenant (id/code/ten)
import base64
import gzip
import hashlib
import json
import os
import secrets
import struct
import sys
from datetime import datetime

import cau_hinh
import secret_provider as sp

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError as _e:   # cùng luật với bao_mat.py — hỏng thì phải hỏng to
    raise ImportError(
        "Thiếu thư viện 'cryptography' — bắt buộc cho AES-256-GCM. "
        "Cài: python3 -m pip install cryptography."
    ) from _e

MAGIC = b"VIPHUBKEYBAK1\n"
DUOI_GOI = ".vipkb"
PHIEN_BAN_GOI = 1
BIEN_MT_PASS = "VIP_HUB_BACKUP_PASSPHRASE"
PBKDF2_VONG_BACKUP = int(os.environ.get("VIP_HUB_BACKUP_PBKDF2", "600000"))
DAI_PASS_TOI_THIEU = 16
DAI_SALT = 16
DAI_NONCE = 12
# Thư mục static đang được `server.py::_phuc_vu_tinh` phục vụ. Gói backup đặt vào đây là
# **tải về được bằng một yêu cầu GET vô danh**. Danh sách này phải khớp `THU_MUC_CHO_PHEP`
# trong server.py — có ca thử đối chiếu để nếu bên kia thêm thư mục mà bên này quên thì bộ thử
# hỏng, chứ không lệch im lặng.
THU_MUC_STATIC = ("admin", "pages", "assets", "mock")
# Passphrase rõ ràng là chỗ giữ tạm, không phải bí mật thật.
PASS_CAM = {
    "changeme", "change-me", "password", "passphrase", "123456789012345678",
    "vip-express-hub", "viphub", "secret", "backup", "0000000000000000",
    "aaaaaaaaaaaaaaaa", "test-passphrase", "khong-co", "todo", "tbd",
}


class LoiSaoLuu(Exception):
    """Lỗi sao lưu/khôi phục khóa. Thông điệp KHÔNG BAO GIỜ chứa khóa hay passphrase."""


# =======================================================================================
# Passphrase
# =======================================================================================
def lay_passphrase(passphrase=None, cho_nhap=True, nhac="Passphrase sao lưu khóa: ") -> bytes:
    """Lấy passphrase theo đúng ba đường, theo thứ tự: tham số → biến môi trường → nhập tay.

    KHÔNG có đường thứ tư. Không mặc định, không tự sinh. Thiếu thì ném `LoiSaoLuu` — người
    vận hành phải biết là họ chưa cấp bí mật, chứ không để hệ tự bịa một cái rồi báo xong.
    """
    if passphrase is None:
        passphrase = os.environ.get(BIEN_MT_PASS)
    if passphrase is None and cho_nhap and sys.stdin is not None and sys.stdin.isatty():
        import getpass
        passphrase = getpass.getpass(nhac)
    if passphrase is None or passphrase == "":
        raise LoiSaoLuu(
            f"chưa có passphrase sao lưu. Đặt biến môi trường {BIEN_MT_PASS}, hoặc chạy ở "
            "terminal để nhập lúc chạy. Hệ CỐ Ý không tự sinh passphrase: bí mật tự sinh thì "
            "phải lưu ở đâu đó, và chỗ đó lại là một bí mật nữa không ai giữ.")
    b = passphrase.encode() if isinstance(passphrase, str) else bytes(passphrase)
    if len(b) < DAI_PASS_TOI_THIEU:
        raise LoiSaoLuu(f"passphrase phải từ {DAI_PASS_TOI_THIEU} ký tự (đang có {len(b)})")
    if b.decode("utf-8", "replace").strip().lower() in PASS_CAM:
        raise LoiSaoLuu("passphrase nằm trong danh sách chuỗi giữ chỗ — đổi sang bí mật thật")
    return b


def _kiem_pass_khac_khoa(pass_b: bytes, cac_khoa):
    """Passphrase KHÔNG được là chính khóa đang sao lưu (xem đoạn đầu file).

    Chặn cả dạng hex và base64 của khóa — chép-dán khóa ra làm passphrase là đúng cái lỗi mà
    thiết kế này sinh ra để tránh, và nó sẽ không báo lỗi ở bất kỳ chỗ nào khác.
    """
    for khoa in cac_khoa:
        if pass_b == khoa or pass_b == khoa.hex().encode() \
                or pass_b == base64.b64encode(khoa) or pass_b == base64.b64encode(khoa).rstrip(b"="):
            raise LoiSaoLuu(
                "passphrase trùng nội dung một khóa đang được sao lưu. Bản backup phải được bảo "
                "vệ ĐỘC LẬP: dùng chính khóa trong gói để khóa gói thì mất thư mục khóa là mất "
                "luôn đường mở backup.")


def _dan_xuat(pass_b: bytes, salt: bytes, vong: int) -> bytes:
    if vong < 100_000:
        raise LoiSaoLuu(f"số vòng PBKDF2 quá thấp: {vong} (tối thiểu 100000)")
    return hashlib.pbkdf2_hmac("sha256", pass_b, salt, vong, dklen=32)


# =======================================================================================
# Đường ghi an toàn
# =======================================================================================
def _kiem_duong_ra(duong: str) -> str:
    """Từ chối mọi chỗ ghi không an toàn. Gọi TRƯỚC khi mã hóa, không phải sau.

    Ba điều bị từ chối: (1) trong thư mục static đang phục vụ, (2) trong thư mục khóa (lẫn
    backup với khóa thật là đường tới chỗ xóa nhầm), (3) nằm trong repo git mà KHÔNG bị
    `.gitignore` chặn — đo bằng `git check-ignore`, không bằng niềm tin vào `.gitignore`.
    """
    duong = os.path.abspath(duong)
    if not duong.endswith(DUOI_GOI):
        raise LoiSaoLuu(f"tên gói backup phải có đuôi {DUOI_GOI} (đang là {os.path.basename(duong)!r})")
    phan = duong.split(os.sep)
    goc_repo = os.path.abspath(os.path.join(cau_hinh.THU_MUC_APP, os.pardir))
    for t in THU_MUC_STATIC:
        if os.path.abspath(os.path.join(goc_repo, t)) + os.sep in duong + os.sep:
            raise LoiSaoLuu(
                f"TỪ CHỐI: {duong} nằm trong thư mục static đang được phục vụ ({t}/) — gói backup "
                "ở đó tải về được bằng một yêu cầu GET vô danh")
    t_khoa = os.path.abspath(sp.THU_MUC_KHOA)
    if duong.startswith(t_khoa + os.sep):
        raise LoiSaoLuu(f"TỪ CHỐI: không đặt gói backup trong thư mục khóa ({t_khoa})")
    if ".git" in phan:
        raise LoiSaoLuu("TỪ CHỐI: không đặt gói backup trong thư mục .git")
    # Trong repo git mà không bị gitignore chặn → có ngày `git add -A` đẩy khóa lên remote.
    #
    # `os.path.exists`, KHÔNG phải `os.path.isdir`: trong một **git worktree** thì `.git` là một
    # FILE trỏ sang repo chính, không phải thư mục. Bản đầu dùng `isdir` nên chốt chặn này CHẾT
    # IM LẶNG đúng ở nơi mọi agent đang làm việc (worktree) — bộ thử h6 bắt được ngày 15/10/2026.
    if duong.startswith(goc_repo + os.sep) and os.path.exists(os.path.join(goc_repo, ".git")):
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", os.path.relpath(duong, goc_repo)],
                           cwd=goc_repo, capture_output=True, text=True)
        if r.returncode != 0:
            raise LoiSaoLuu(
                f"TỪ CHỐI: {duong} nằm trong repo git mà .gitignore KHÔNG chặn — gói chứa khóa "
                "mã hóa, lọt vào git là lộ vĩnh viễn trong lịch sử. Ghi ra ngoài repo, hoặc "
                "thêm đường này vào .gitignore trước.")
    return duong


def _ghi_nguyen_tu(duong: str, du_lieu: bytes, quyen=0o600):
    """Ghi file tạm cùng thư mục rồi `os.replace` — đặt quyền TRƯỚC khi đổi tên (CLAUDE.md §16.3)."""
    os.makedirs(os.path.dirname(duong) or ".", exist_ok=True)
    tam = duong + ".tam-" + secrets.token_hex(4)
    with open(tam, "wb") as f:
        f.write(du_lieu)
    os.chmod(tam, quyen)
    os.replace(tam, duong)


# =======================================================================================
# Thu gom nội dung cần sao lưu
# =======================================================================================
def _thu_gom_khoa(thu_muc_khoa=None, duong_khoa_cu=None) -> dict:
    """Đọc mọi file khóa + con trỏ hiện hành. KHÔNG ghi gì, KHÔNG sinh khóa mới."""
    nguoi = sp.LocalSecretProvider(thu_muc=thu_muc_khoa, duong_khoa_cu=duong_khoa_cu)
    ds = nguoi.danh_sach_key_id()
    if not ds:
        raise LoiSaoLuu(
            f"không thấy khóa nào trong {nguoi.thu_muc} — không sao lưu một thư mục rỗng rồi báo "
            "đạt. Kiểm lại đường thư mục khóa trước.")
    khoa = []
    tho = []
    for key_id in ds:
        with open(nguoi._duong(key_id), "rb") as f:
            b = f.read()
        if len(b) != sp.DAI_KHOA:
            raise LoiSaoLuu(f"khóa '{key_id}' dài {len(b)} byte, cần {sp.DAI_KHOA} — không gói "
                            "một khóa hỏng vào bản sao lưu")
        tho.append(b)
        khoa.append({"key_id": key_id, "noi_dung_b64": base64.b64encode(b).decode(),
                     "sha256": hashlib.sha256(b).hexdigest(), "quyen": "0600"})
    hien_hanh = None
    duong_tro = nguoi._duong_tro()
    if os.path.exists(duong_tro):
        with open(duong_tro, encoding="utf-8") as f:
            hien_hanh = f.read().strip()
    khoa_cu = None
    if os.path.exists(nguoi.duong_khoa_cu):
        with open(nguoi.duong_khoa_cu, "rb") as f:
            b = f.read()
        tho.append(b)
        khoa_cu = {"ten_file": os.path.basename(nguoi.duong_khoa_cu),
                   "noi_dung_b64": base64.b64encode(b).decode(),
                   "sha256": hashlib.sha256(b).hexdigest()}
    return {"khoa": khoa, "khoa_hien_hanh": hien_hanh, "khoa_cu": khoa_cu, "_tho": tho}


def _thu_gom_ban_ma() -> dict:
    """Bản mã + ràng buộc tenant/account. KHÔNG giải mã gì — chỉ chép bản đã mã hóa.

    Vì sao phải gói cả bản mã: khóa khôi phục xong vẫn giải không ra nếu AAD dựng sai, mà AAD
    là `cred:<tenant_id>:<hang>` và `wh:<webhook_ma>` — ba trường ấy nằm ở CSDL. Gói kèm để
    khôi phục kiểm chứng được NGAY trong môi trường cô lập, không phải chờ CSDL thật.
    """
    try:
        import csdl
        csdl.mo()
    except Exception as e:
        return {"co_csdl": False, "ly_do": f"{type(e).__name__}: {e}", "ban_ma": [], "tenant": []}
    ban_ma, tenant = [], []
    try:
        for r in csdl.nhieu(
                "SELECT id, tenant_id, hang, webhook_ma, credentials_ma_hoa,"
                " credentials_duoi, webhook_secret_ma_hoa FROM carrier_accounts ORDER BY id"):
            ban_ma.append({"bang": "carrier_accounts", "id": r["id"], "tenant_id": r["tenant_id"],
                           "hang": r["hang"], "webhook_ma": r["webhook_ma"],
                           "credentials_ma_hoa": r["credentials_ma_hoa"],
                           "credentials_duoi": r["credentials_duoi"],
                           "webhook_secret_ma_hoa": r["webhook_secret_ma_hoa"]})
        for r in csdl.nhieu("SELECT id, code, ten, trang_thai FROM tenants ORDER BY id"):
            tenant.append({"id": r["id"], "code": r["code"], "ten": r["ten"],
                           "trang_thai": r["trang_thai"]})
        pb = csdl.phien_ban_hien_tai()
    except Exception as e:
        return {"co_csdl": False, "ly_do": f"{type(e).__name__}: {e}",
                "ban_ma": ban_ma, "tenant": tenant}
    return {"co_csdl": True, "ban_ma": ban_ma, "tenant": tenant, "schema_version": pb}


# =======================================================================================
# Tạo gói
# =======================================================================================
def tao_goi(duong_ra, passphrase=None, thu_muc_khoa=None, duong_khoa_cu=None,
            gom_ban_ma=True, cho_nhap=True, ghi_audit=True) -> dict:
    """Tạo gói backup đã mã hóa độc lập. Trả siêu dữ liệu (KHÔNG chứa bí mật nào).

    Thứ tự CỐ Ý: kiểm đường ra → đọc khóa → lấy passphrase → kiểm passphrase ≠ khóa → mã hóa →
    ghi nguyên tử. Kiểm đường ra TRƯỚC để không bao giờ có một file bí mật nằm sai chỗ, kể cả
    trong một phần giây.
    """
    duong_ra = _kiem_duong_ra(duong_ra)
    goi_khoa = _thu_gom_khoa(thu_muc_khoa, duong_khoa_cu)
    tho = goi_khoa.pop("_tho")
    pass_b = lay_passphrase(passphrase, cho_nhap=cho_nhap)
    _kiem_pass_khac_khoa(pass_b, tho)

    pm = _thu_gom_ban_ma() if gom_ban_ma else {"co_csdl": False, "ly_do": "gom_ban_ma=False",
                                               "ban_ma": [], "tenant": []}
    tao_luc = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
    payload = {
        "phien_ban": PHIEN_BAN_GOI, "tao_luc": tao_luc,
        "khoa": goi_khoa["khoa"], "khoa_hien_hanh": goi_khoa["khoa_hien_hanh"],
        "khoa_cu": goi_khoa["khoa_cu"],
        "ban_ma": pm["ban_ma"],
        "sieu_du_lieu": {"co_csdl": pm["co_csdl"], "ly_do_khong_co_csdl": pm.get("ly_do"),
                         "schema_version": pm.get("schema_version"),
                         "tenant": pm["tenant"], "so_tenant": len(pm["tenant"]),
                         "so_carrier_account": len(pm["ban_ma"])},
    }
    ro = gzip.compress(json.dumps(payload, ensure_ascii=False).encode(), 9)
    salt, nonce = secrets.token_bytes(DAI_SALT), secrets.token_bytes(DAI_NONCE)
    header = {"magic": "VIPHUBKEYBAK", "phien_ban": PHIEN_BAN_GOI, "tao_luc": tao_luc,
              "kdf": "pbkdf2-hmac-sha256", "vong": PBKDF2_VONG_BACKUP,
              "salt_hex": salt.hex(), "nonce_hex": nonce.hex(),
              "ma_hoa": "aes-256-gcm", "nen": "gzip",
              "so_khoa": len(payload["khoa"]), "khoa_hien_hanh": payload["khoa_hien_hanh"],
              "so_ban_ma": len(payload["ban_ma"]), "sha256_ro": hashlib.sha256(ro).hexdigest()}
    hb = json.dumps(header, ensure_ascii=False, sort_keys=True).encode()
    kek = _dan_xuat(pass_b, salt, PBKDF2_VONG_BACKUP)
    ct = AESGCM(kek).encrypt(nonce, ro, hb)     # header làm AAD → sửa header là giải mã hỏng
    _ghi_nguyen_tu(duong_ra, MAGIC + struct.pack(">I", len(hb)) + hb + ct)

    kq = {"duong": duong_ra, "so_byte": os.path.getsize(duong_ra), "tao_luc": tao_luc,
          "so_khoa": header["so_khoa"], "khoa_hien_hanh": header["khoa_hien_hanh"],
          "so_ban_ma": header["so_ban_ma"], "co_khoa_cu": payload["khoa_cu"] is not None,
          "key_id": [k["key_id"] for k in payload["khoa"]],
          "quyen": oct(os.stat(duong_ra).st_mode & 0o777)}
    if ghi_audit:
        _audit("sao_luu_khoa", f"khoa:{kq['so_khoa']}",
               f"gói {os.path.basename(duong_ra)}; {kq['so_khoa']} khóa"
               f" ({', '.join(kq['key_id'])}); {kq['so_ban_ma']} bản mã kèm ràng buộc")
    return kq


def _audit(hanh_dong, doi_tuong, chi_tiet, ket_qua="thanh_cong"):
    """Ghi audit nếu CSDL dùng được. KHÔNG nuốt lỗi im lặng (CLAUDE.md §12.2)."""
    try:
        import csdl
        csdl.audit(hanh_dong, doi_tuong, chi_tiet, ket_qua=ket_qua)
    except Exception as e:
        sys.stderr.write(f"[sao_luu_khoa] KHÔNG ghi được audit ({type(e).__name__}: {e}) — "
                         f"việc vẫn làm xong: {hanh_dong} {doi_tuong}\n")


# =======================================================================================
# Đọc / kiểm / khôi phục
# =======================================================================================
def doc_header(duong_goi) -> dict:
    """Header của gói — đọc được KHÔNG CẦN passphrase, vì header không chứa bí mật nào."""
    with open(duong_goi, "rb") as f:
        tho = f.read()
    if not tho.startswith(MAGIC):
        raise LoiSaoLuu(f"{duong_goi} không phải gói backup khóa (thiếu magic)")
    n = struct.unpack(">I", tho[len(MAGIC):len(MAGIC) + 4])[0]
    if n <= 0 or n > 1_000_000:
        raise LoiSaoLuu(f"độ dài header vô lý: {n}")
    hb = tho[len(MAGIC) + 4:len(MAGIC) + 4 + n]
    return {"header": json.loads(hb.decode()), "_hb": hb,
            "_ct": tho[len(MAGIC) + 4 + n:], "so_byte": len(tho)}


def _mo_goi(duong_goi, passphrase=None, cho_nhap=True):
    g = doc_header(duong_goi)
    h = g["header"]
    if h.get("phien_ban") != PHIEN_BAN_GOI:
        raise LoiSaoLuu(f"gói phiên bản {h.get('phien_ban')}, mã này đọc phiên bản {PHIEN_BAN_GOI}")
    pass_b = lay_passphrase(passphrase, cho_nhap=cho_nhap)
    kek = _dan_xuat(pass_b, bytes.fromhex(h["salt_hex"]), int(h["vong"]))
    try:
        ro = AESGCM(kek).decrypt(bytes.fromhex(h["nonce_hex"]), g["_ct"], g["_hb"])
    except Exception as e:
        # Không nói rõ sai passphrase hay gói bị sửa: cả hai đều là "không mở được", và nói rõ
        # chỉ giúp người dò. Cũng KHÔNG đưa nội dung gói vào thông điệp (nó hay bị ghi log).
        raise LoiSaoLuu(f"không mở được gói (sai passphrase, hoặc gói/header bị sửa): "
                        f"{type(e).__name__}") from None
    if hashlib.sha256(ro).hexdigest() != h.get("sha256_ro"):
        raise LoiSaoLuu("sha256 nội dung không khớp header — gói hỏng")
    return json.loads(gzip.decompress(ro).decode()), h


def kiem_toan_ven(duong_goi, passphrase=None, cho_nhap=True) -> dict:
    """Mở gói TRONG BỘ NHỚ và kiểm toàn vẹn. KHÔNG ghi file nào, KHÔNG in khóa.

    Dùng để nghiệm thu một gói backup mà không phải khôi phục: đúng tinh thần §12.1 — thứ dùng
    để kiểm chứng (gói backup) phải được kiểm TRƯỚC khi tin nó.
    """
    p, h = _mo_goi(duong_goi, passphrase, cho_nhap)
    loi = []
    for k in p["khoa"]:
        b = base64.b64decode(k["noi_dung_b64"])
        if len(b) != sp.DAI_KHOA:
            loi.append(f"khóa {k['key_id']}: dài {len(b)} byte")
        if hashlib.sha256(b).hexdigest() != k["sha256"]:
            loi.append(f"khóa {k['key_id']}: sha256 không khớp")
    ds = [k["key_id"] for k in p["khoa"]]
    if p["khoa_hien_hanh"] and p["khoa_hien_hanh"] not in ds:
        loi.append(f"con trỏ hiện hành trỏ tới '{p['khoa_hien_hanh']}' không có trong gói")
    if p["khoa_cu"]:
        b = base64.b64decode(p["khoa_cu"]["noi_dung_b64"])
        if hashlib.sha256(b).hexdigest() != p["khoa_cu"]["sha256"]:
            loi.append("khóa cũ (khoa-noi-bo.key): sha256 không khớp")
    # Bản mã nào mang key_id không có trong gói → khôi phục xong vẫn không giải được bản đó.
    thieu = set()
    for r in p["ban_ma"]:
        for cot in ("credentials_ma_hoa", "webhook_secret_ma_hoa"):
            bm = str(r.get(cot) or "")
            if bm.startswith("v3$"):
                kid = bm.split("$")[1] if len(bm.split("$")) == 4 else None
                if kid and kid not in ds:
                    thieu.add(kid)
    if thieu:
        loi.append(f"bản mã dùng key_id KHÔNG có trong gói: {', '.join(sorted(thieu))}")
    return {"dat": not loi, "loi": loi, "so_khoa": len(ds), "key_id": ds,
            "khoa_hien_hanh": p["khoa_hien_hanh"], "co_khoa_cu": p["khoa_cu"] is not None,
            "so_ban_ma": len(p["ban_ma"]), "tao_luc": h["tao_luc"],
            "so_tenant": p["sieu_du_lieu"]["so_tenant"],
            "key_id_thieu": sorted(thieu)}


def khoi_phuc(duong_goi, thu_muc_dich, passphrase=None, ghi_de=False, cho_nhap=True,
              duong_khoa_cu_dich=None, ghi_audit=True) -> dict:
    """Khôi phục khóa vào `thu_muc_dich`. `thu_muc_dich` BẮT BUỘC — không có mặc định.

    Vì sao bắt buộc: mặc định về thư mục khóa đang chạy nghĩa là gõ thiếu một tham số là ghi đè
    khóa thật. Người khôi phục phải nói ra họ ghi vào đâu.

    `ghi_de=False` (mặc định): file khóa đã tồn tại thì **KHÔNG ghi đè**, ghi vào `bo_qua` và
    đi tiếp. Ghi đè một khóa đang dùng bằng khóa trong gói cũ là mất dữ liệu đã mã hóa bằng
    khóa mới — mà không có gì báo lỗi cho tới lượt giải mã sau.

    KHÔNG di chuyển, KHÔNG xóa khóa gốc ở bất kỳ nhánh nào của hàm này.
    """
    p, h = _mo_goi(duong_goi, passphrase, cho_nhap)
    thu_muc_dich = os.path.abspath(thu_muc_dich)
    os.makedirs(thu_muc_dich, exist_ok=True)
    os.chmod(thu_muc_dich, 0o700)
    da_ghi, bo_qua, loi = [], [], []
    for k in p["khoa"]:
        b = base64.b64decode(k["noi_dung_b64"])
        if hashlib.sha256(b).hexdigest() != k["sha256"]:
            loi.append(f"khóa {k['key_id']}: sha256 không khớp — KHÔNG ghi")
            continue
        duong = os.path.join(thu_muc_dich, sp.kiem_key_id(k["key_id"]) + sp.DUOI_KHOA)
        if os.path.exists(duong) and not ghi_de:
            bo_qua.append(k["key_id"])
            continue
        _ghi_nguyen_tu(duong, b, 0o600)
        da_ghi.append(k["key_id"])
    # Con trỏ khóa hiện hành: khôi phục khóa mà quên con trỏ thì hệ mã hóa MỚI bằng một khóa
    # khác, và bản mã mới nằm dưới khóa không ai sao lưu.
    tro = None
    if p["khoa_hien_hanh"]:
        d_tro = os.path.join(thu_muc_dich, sp.TEN_FILE_TRO)
        if os.path.exists(d_tro) and not ghi_de:
            bo_qua.append(sp.TEN_FILE_TRO)
        else:
            _ghi_nguyen_tu(d_tro, p["khoa_hien_hanh"].encode(), 0o600)
            tro = p["khoa_hien_hanh"]
    # Khóa một-bản cũ: bản mã v1/v2 KHÔNG mang key_id nên chỉ đọc được từ đúng file này.
    khoa_cu = None
    if p["khoa_cu"]:
        d = duong_khoa_cu_dich or os.path.join(thu_muc_dich, p["khoa_cu"]["ten_file"])
        if os.path.exists(d) and not ghi_de:
            bo_qua.append(p["khoa_cu"]["ten_file"])
        else:
            _ghi_nguyen_tu(d, base64.b64decode(p["khoa_cu"]["noi_dung_b64"]), 0o600)
            khoa_cu = d
    kq = {"thu_muc_dich": thu_muc_dich, "da_ghi": da_ghi, "bo_qua": bo_qua, "loi": loi,
          "con_tro_hien_hanh": tro, "duong_khoa_cu": khoa_cu,
          "so_ban_ma_trong_goi": len(p["ban_ma"]), "tao_luc_goi": h["tao_luc"],
          "dat": not loi}
    if ghi_audit:
        _audit("khoi_phuc_khoa", f"khoa:{len(da_ghi)}",
               f"từ gói {os.path.basename(duong_goi)} (tạo {h['tao_luc']}); ghi"
               f" {len(da_ghi)} khóa, bỏ qua {len(bo_qua)}; đích {thu_muc_dich}",
               ket_qua="that_bai" if loi else "thanh_cong")
    return kq


def rang_buoc_ban_ma(duong_goi, passphrase=None, cho_nhap=True):
    """Danh sách bản mã + ràng buộc (tenant_id, hang, webhook_ma) để dựng lại AAD khi nghiệm thu.

    Trả bản mã, KHÔNG trả plaintext. Người gọi tự dùng `bao_mat.giai_ma_cred/giai_ma_wh`.
    """
    p, _ = _mo_goi(duong_goi, passphrase, cho_nhap)
    return p["ban_ma"]


def kiem_khong_lo_secret(duong_goi, cac_bi_mat) -> dict:
    """Quét BYTE THÔ của gói tìm từng bí mật (khóa, plaintext credentials) ở các dạng hay lọt.

    Đây là phép đo ĐỘC LẬP với việc mã hóa: nó không hỏi "đã mã hóa chưa", nó hỏi "chuỗi bí mật
    có xuất hiện trong file không". Mã hóa đúng thì không chuỗi nào xuất hiện.
    """
    with open(duong_goi, "rb") as f:
        tho = f.read()
    lo = []
    for bi in cac_bi_mat:
        b = bi.encode() if isinstance(bi, str) else bytes(bi)
        dang = {"tho": b, "hex": b.hex().encode(), "b64": base64.b64encode(b).rstrip(b"=")}
        for ten, x in dang.items():
            if len(x) >= 8 and x in tho:
                lo.append(ten)                      # KHÔNG ghi chính bí mật vào kết quả
    return {"dat": not lo, "dang_bi_lo": lo, "so_byte_goi": len(tho)}


# =======================================================================================
# Chạy tay
# =======================================================================================
def _cli(argv):
    dung = (f"Cách dùng:\n"
            f"  python3 app/sao_luu_khoa.py tao <duong-ra{DUOI_GOI}>\n"
            f"  python3 app/sao_luu_khoa.py kiem <goi{DUOI_GOI}>\n"
            f"  python3 app/sao_luu_khoa.py header <goi{DUOI_GOI}>\n"
            f"  python3 app/sao_luu_khoa.py khoi-phuc <goi{DUOI_GOI}> <thu-muc-dich> [--ghi-de]\n"
            f"\nPassphrase: biến môi trường {BIEN_MT_PASS}, hoặc nhập lúc chạy.\n")
    if len(argv) < 2:
        print(dung)
        return 2
    viec = argv[1]
    if viec == "tao" and len(argv) == 3:
        print(json.dumps(tao_goi(argv[2]), ensure_ascii=False, indent=2))
    elif viec == "kiem" and len(argv) == 3:
        kq = kiem_toan_ven(argv[2])
        print(json.dumps(kq, ensure_ascii=False, indent=2))
        return 0 if kq["dat"] else 1
    elif viec == "header" and len(argv) == 3:
        print(json.dumps(doc_header(argv[2])["header"], ensure_ascii=False, indent=2))
    elif viec == "khoi-phuc" and len(argv) >= 4:
        kq = khoi_phuc(argv[2], argv[3], ghi_de="--ghi-de" in argv[4:])
        print(json.dumps(kq, ensure_ascii=False, indent=2))
        return 0 if kq["dat"] else 1
    else:
        print(dung)
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_cli(sys.argv))
    except LoiSaoLuu as e:
        sys.stderr.write(f"LỖI: {e}\n")
        sys.exit(1)
