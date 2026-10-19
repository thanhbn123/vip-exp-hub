# -*- coding: utf-8 -*-
"""XÁC THỰC + BẢO MẬT CREDENTIAL CHO BEST EXPRESS (AGENT B2).

Phạm vi: CHỈ hai việc — (1) đăng nhập BEST bằng Username/Password để lấy token, và
(2) tách bạch hai LOẠI secret không được dùng lẫn nhau:

    LỚP A — credential đăng nhập BEST (Username + Password)   → kho credential_dang_nhap
    LỚP B — Bearer token nhận WEBHOOK (BEST gửi tới hub)      → kho bearer_webhook

Token truy cập lấy từ `/User/Login` là DẪN XUẤT của lớp A, không phải lớp B. Nó có kho
riêng (token_truy_cap) vì vòng đời khác hẳn: 30 ngày, được cache, được làm mới. Ba kho là
ba TỆP riêng, ba tên riêng; không tệp nào đọc được bằng hàm của tệp khác (xem `loai`).

ĐẶC TẢ ĐÃ XÁC NHẬN (đề bài, KHÔNG suy diễn thêm):
    POST /User/Login   body {"Username": ..., "Password": ...}   → {"token": ...}
    token sống 30 NGÀY.

MỌI THỨ KHÁC LÀ CHƯA KIỂM CHỨNG — xem docs/BEST_EXPRESS_SECURITY_REVIEW.md §"CHƯA KIỂM CHỨNG".
Đặc biệt: KHÔNG đoán endpoint refresh, KHÔNG đoán schema lỗi, KHÔNG đoán header webhook.
Vì vậy khi token hết hạn, module ĐĂNG NHẬP LẠI đúng endpoint đã xác nhận; không gọi endpoint
nào khác.

MẶC ĐỊNH AN TOÀN:
  · Không có transport mặc định ⇒ `lay_token()` TỪ CHỐI, không tự gọi mạng.
  · `TransportDangNhapHTTPS` chỉ nhận HTTPS; HTTP chỉ được phép cho loopback VÀ phải bật
    cờ `cho_phep_loopback=True` (dùng cho bộ thử MOCK). Không bao giờ tắt xác minh TLS.
  · Không trả token ra hàm mô tả trạng thái; không ghi token/password vào log/audit.
  · Mọi thao tác bắt buộc tenant_id; thiếu tenant ⇒ TỪ CHỐI trước khi chạm đĩa/mạng.

MÔI TRƯỜNG: phần mã này CHỈ được đo bằng MOCK (stub loopback). Chưa có lần chạy REAL nào
với BEST. Xem báo cáo để biết đúng phạm vi.

Ghi chú hợp đồng (§3/§14 docs/SHARED_CONTRACTS.md): chỉ dùng bốn hàm
`bao_mat.ma_hoa_cred / giai_ma_cred / ma_hoa_wh / giai_ma_wh`. Module này dùng cặp
credential (`ma_hoa_cred/giai_ma_cred`) cho CẢ HAI lớp vì AAD của nó buộc đúng
`tenant_id + hãng` — yêu cầu của đề bài. Hai lớp vẫn tách nhau bằng tệp riêng + trường
`loai` nằm TRONG bản mã (sửa/đổi tệp sẽ hỏng khi giải mã hoặc bị từ chối).
"""

from __future__ import annotations

import contextlib
import dataclasses
import fcntl
import hashlib
import hmac
import ipaddress
import json
import logging
import math
import os
import re
import ssl
import stat
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Optional

import bao_mat
import cau_hinh

# ============================================================================
# HẰNG SỐ — một chỗ khai, không rải rác
# ============================================================================
HANG = "BEST"

# Đặc tả đã xác nhận: token sống 30 ngày. KHÔNG suy diễn thành "30 ngày kể từ lúc hãng
# phát hành" hoặc "trượt" — ta chỉ biết nó sống 30 ngày, nên mốc tính là lúc NHẬN token.
HAN_TOKEN_GIAY = 30 * 24 * 60 * 60          # 2 592 000 giây
DUONG_DAN_DANG_NHAP = "/User/Login"

# Lệch đồng hồ cho phép: nếu đồng hồ hệ thống lùi quá mức này so với lúc phát hành token,
# coi token là KHÔNG hợp lệ và làm mới (thay vì tin một mốc thời gian đáng ngờ).
LECH_DONG_HO_CHO_PHEP_GIAY = 300

# Trần kích thước phản hồi / tệp kho / header — chặn đầu vào làm cạn bộ nhớ.
GIOI_HAN_PHAN_HOI_BYTE = 64 * 1024
GIOI_HAN_KHO_BYTE = 1024 * 1024
GIOI_HAN_TOKEN_BYTE = 8192
GIOI_HAN_HEADER_BYTE = 8192

# Mã lỗi ổn định — bên gọi phân nhánh theo mã, KHÔNG đọc câu chữ.
MA_LOI = {
    "THIEU_TENANT": "thiếu hoặc sai tenant_id — từ chối trước khi chạm dữ liệu",
    "THIEU_TAI_KHOAN": "thiếu hoặc sai mã tài khoản hãng",
    "THIEU_CREDENTIAL": "tenant/tài khoản chưa có credential đăng nhập BEST",
    "CREDENTIAL_KHONG_HOP_LE": "Username rỗng/sai kiểu/ký tự điều khiển; Password rỗng/sai kiểu/quá dài/NUL",
    "KHONG_DOC_DUOC_CREDENTIAL": "không giải mã được credential (sai khóa/AAD hoặc dữ liệu bị sửa)",
    "SAI_LOP_SECRET": "bản mã thuộc LỚP secret khác — từ chối dùng lẫn",
    "DU_LIEU_KHONG_KHOP": "dữ liệu đã giải mã không khớp tenant/tài khoản/trường bắt buộc",
    "MA_HOA_LOI": "không mã hóa được secret (lỗi khóa/provider)",
    "KHO_HONG": "tệp kho không đọc được hoặc sai cấu trúc — KHÔNG ghi đè",
    "KHO_KHONG_AN_TOAN": "tệp/thư mục kho không phải tệp thường hoặc là symlink",
    "KHOA_KHONG_HO_TRO": "hệ tệp không hỗ trợ khóa liên tiến trình đáng tin",
    "QUYEN_TEP_KHONG_AN_TOAN": "không đặt được quyền 0600/0700 cho kho",
    "KHONG_DOC_DUOC_TOKEN": "không giải mã được token đã cache — sẽ đăng nhập lại có kiểm soát",
    "TOKEN_KHONG_KHOP_CREDENTIAL": "token cache thuộc phiên bản credential cũ — sẽ làm mới",
    "TOKEN_KHONG_HOP_LE": "token nhận được rỗng/sai kiểu/chứa ký tự không hợp lệ",
    "CREDENTIAL_DA_DOI_KHONG_LUU": "credential đổi giữa lượt đăng nhập — từ chối token của credential cũ",
    "CHUA_CAU_HINH_TRANSPORT": "chưa cấu hình transport đăng nhập — từ chối gọi mạng",
    "TRANSPORT_KHONG_HOP_LE": "transport không có hàm dang_nhap(username, password)",
    "TRANSPORT_LOI": "transport ném lỗi không xác định — đã che chi tiết",
    "DANG_NHAP_THAT_BAI": "BEST từ chối đăng nhập hoặc trả mã HTTP lỗi",
    "KHONG_KET_NOI_DUOC": "không kết nối được tới máy chủ đăng nhập",
    "PHAN_HOI_KHONG_HOP_LE": "phản hồi đăng nhập không phải JSON đúng đặc tả {token}",
    "PHAN_HOI_QUA_LON": "phản hồi đăng nhập vượt trần kích thước",
    "CHUYEN_HUONG_BITU_CHAN": "máy chủ đăng nhập cố chuyển hướng — từ chối đi theo",
    "URL_KHONG_HOP_LE": "base_url không hợp lệ (cần origin HTTPS, không userinfo/query/path)",
    "THAM_SO_KHONG_HOP_LE": "tham số cấu hình không hợp lệ",
    "HTTP_KHONG_DUOC_PHEP": "chỉ cho HTTP với loopback khi bật cờ kiểm thử",
    "DONG_HO_KHONG_HOP_LE": "đồng hồ được truyền vào không trả số hữu hạn",
    "THIEU_HEADER": "thiếu header Authorization",
    "SAI_DINH_DANG_BEARER": "header không đúng dạng 'Bearer <token>'",
    "HEADER_QUA_DAI": "header Authorization vượt trần kích thước",
    "KHONG_CO_BEARER_DA_LUU": "tenant/tài khoản chưa lưu Bearer webhook",
    "BEARER_KHONG_KHOP": "Bearer webhook không khớp",
    "BEARER_KHONG_HOP_LE": "Bearer webhook rỗng/sai kiểu/chứa ký tự không hợp lệ",
    "KHONG_DOC_DUOC_BEARER": "không giải mã được Bearer webhook (sai khóa/AAD hoặc dữ liệu bị sửa)",
    "WEBHOOK_MA_KHONG_HOP_LE": "webhook_ma rỗng hoặc sai kiểu",
}

# Ba LOẠI bản ghi — dùng làm nhãn trong tệp và trong chính bản mã.
LOAI_CREDENTIAL = "credential_dang_nhap_best"
LOAI_TOKEN_TRUY_CAP = "token_truy_cap_best"
LOAI_WEBHOOK = "bearer_webhook_best"

TEP_KHO = {
    LOAI_CREDENTIAL: "credential_dang_nhap.enc.json",
    LOAI_TOKEN_TRUY_CAP: "token_truy_cap.enc.json",
    LOAI_WEBHOOK: "bearer_webhook.enc.json",
}

PHIEN_BAN_KHO = 1

# Mã lỗi của CACHE token (không phải credential). Gặp các mã này thì bỏ cache và đăng nhập
# lại có kiểm soát; TUYỆT ĐỐI không áp dụng cho lỗi credential (những lỗi đó phải DENY).
MA_CACHE_TOKEN_HONG = (
    "KHONG_DOC_DUOC_TOKEN",
    "TOKEN_KHONG_KHOP_CREDENTIAL",
    "DU_LIEU_KHONG_KHOP",
    "SAI_LOP_SECRET",
)

logger = logging.getLogger("vip.best_auth")


# ============================================================================
# LỖI — thông điệp KHÔNG BAO GIỜ chứa secret
# ============================================================================
class LoiXacThucBest(Exception):
    """Lỗi có mã ổn định. `str(e)` chỉ chứa mã + câu mô tả TĨNH, không chứa secret."""

    def __init__(self, ma_loi: str, http_status: Optional[int] = None):
        # CHỈ nhận mã nằm trong bảng của module. Mã lạ (ví dụ transport tự chèn dữ liệu)
        # bị quy về TRANSPORT_LOI — không để chuỗi tùy ý vào str(e)/log/audit.
        ma = str(ma_loi)
        self.ma_loi = ma if ma in MA_LOI else "TRANSPORT_LOI"
        self.http_status = http_status
        self.thong_diep = MA_LOI[self.ma_loi]
        super().__init__("%s: %s" % (self.ma_loi, self.thong_diep))


# ============================================================================
# TIỆN ÍCH AN TOÀN
# ============================================================================
def _bam_tham_chieu(tenant_id: str, tai_khoan: str) -> str:
    """Tham chiếu một chiều cho log/audit — KHÔNG chứa username, password hay token."""
    return hashlib.sha256(
        ("%s\x00%s" % (tenant_id, tai_khoan)).encode("utf-8")
    ).hexdigest()[:16]


_MA_AN_TOAN = re.compile(r"^[A-Z0-9_]{0,64}$")
_TEN_AN_TOAN = re.compile(r"^[a-z0-9_.-]{0,64}$")


def _ma_ly_do_an_toan(ma: str) -> str:
    ma = str(ma or "")
    return ma if _MA_AN_TOAN.match(ma) else "KHAC"


def _ten_an_toan(ten: str) -> str:
    """Tên sự kiện/lớp: chữ thường + số + _.- (khác mã lý do viết HOA)."""
    ten = str(ten or "")
    return ten if _TEN_AN_TOAN.match(ten) else "khac"


def _log(su_kien: str, tenant_id: str, tai_khoan: str, ma_ly_do: str = "",
         lop: str = "", http_status: Optional[int] = None) -> None:
    """Ghi log CHỈ các trường đã biết là an toàn. Không nhận chuỗi tùy ý."""
    logger.info(
        "best_auth su_kien=%s tham_chieu=%s lop=%s ma_ly_do=%s http=%s",
        _ten_an_toan(su_kien),
        _bam_tham_chieu(tenant_id, tai_khoan) if tenant_id and tai_khoan else "-",
        _ten_an_toan(lop),
        _ma_ly_do_an_toan(ma_ly_do),
        http_status if isinstance(http_status, int) else "-",
    )


def _ghi_audit(su_kien: str, tenant_id: str, tai_khoan: str, ket_qua: str,
               ma_ly_do: str, lop: str) -> None:
    """Ghi audit qua `csdl.audit` — chỉ mã lỗi + tham chiếu băm, không secret.

    Audit hỏng KHÔNG được làm hỏng luồng xác thực (nhưng cũng không im lặng: log WARNING).
    """
    try:
        import csdl  # import muộn để module vẫn dùng được khi chỉ cần kho mã hóa
        csdl.audit(
            su_kien,
            doi_tuong="best_auth:%s" % _bam_tham_chieu(tenant_id, tai_khoan),
            chi_tiet="hang=%s; lop=%s; ma_ly_do=%s"
                     % (HANG, _ten_an_toan(lop), _ma_ly_do_an_toan(ma_ly_do)),
            tenant_id=tenant_id,
            ket_qua=ket_qua,
            dia_chi="local:best-auth",
        )
    except Exception as e:  # noqa: BLE001 — audit không được che lỗi xác thực
        logger.warning(
            "best_auth audit_failed su_kien=%s tham_chieu=%s loai_loi=%s",
            _ten_an_toan(su_kien),
            _bam_tham_chieu(tenant_id, tai_khoan) if tenant_id and tai_khoan else "-",
            type(e).__name__,
        )


def _bat_buoc_tenant(tenant_id: Any) -> str:
    """Tenant BẮT BUỘC. Không xác định được tenant ⇒ DENY trước mọi thao tác."""
    if (not isinstance(tenant_id, str) or not tenant_id.strip()
            or len(tenant_id) > 128 or any(ord(c) < 0x20 for c in tenant_id)):
        raise LoiXacThucBest("THIEU_TENANT")
    return tenant_id


def _bat_buoc_tai_khoan(tai_khoan: Any) -> str:
    if (not isinstance(tai_khoan, str) or not tai_khoan.strip()
            or len(tai_khoan) > 128 or any(ord(c) < 0x20 for c in tai_khoan)):
        raise LoiXacThucBest("THIEU_TAI_KHOAN")
    return tai_khoan


def _hop_le_chuoi_bi_mat(gia_tri: Any, toi_thieu: int, toi_da: int) -> bool:
    """Token/Bearer: đúng kiểu, đủ dài, ASCII in được, KHÔNG khoảng trắng/điều khiển.

    Token đi vào header HTTP, nên khoảng trắng hay ký tự điều khiển là mơ hồ/nguy hiểm.
    Tập ký tự của token BEST CHƯA được xác nhận; nếu tài liệu thật cho phép ký tự khác,
    sửa DUY NHẤT ở đây và ghi lại bằng chứng. Password thì KHÔNG dùng hàm này — password
    là dữ liệu mờ, không được tự ý thu hẹp bảng chữ.
    """
    if not isinstance(gia_tri, str):
        return False
    if not (toi_thieu <= len(gia_tri) <= toi_da):
        return False
    for c in gia_tri:
        o = ord(c)
        if o < 0x21 or o > 0x7E:      # ASCII in được, không khoảng trắng
            return False
    return True


def _hop_le_ten_dang_nhap(gia_tri: Any) -> bool:
    """Username: chuỗi 1..256, không NUL/ký tự điều khiển. KHÔNG tự cấm Unicode."""
    if not isinstance(gia_tri, str) or not (1 <= len(gia_tri) <= 256):
        return False
    return not any(ord(c) < 0x20 or ord(c) == 0x7F for c in gia_tri)


def _hop_le_mat_khau(gia_tri: Any) -> bool:
    """Password: dữ liệu MỜ. Chỉ chặn rỗng/quá dài/NUL — không đoán bảng chữ của BEST.

    Không cấm khoảng trắng/Unicode vì đặc tả chưa nói gì; thu hẹp bảng chữ là đoán, và
    đoán sai ở đây làm hỏng đúng tài khoản thật. Password không bao giờ đi vào header.
    """
    if not isinstance(gia_tri, str) or not (1 <= len(gia_tri) <= 1024):
        return False
    return "\x00" not in gia_tri


def _kiem_token(token: Any) -> str:
    if not _hop_le_chuoi_bi_mat(token, 1, GIOI_HAN_TOKEN_BYTE):
        raise LoiXacThucBest("TOKEN_KHONG_HOP_LE")
    return token


def _bay_gio(dong_ho: Optional[Callable[[], float]]) -> float:
    try:
        now = float(dong_ho() if dong_ho is not None else time.time())
    except Exception as e:  # noqa: BLE001
        raise LoiXacThucBest("DONG_HO_KHONG_HOP_LE") from None
    if not math.isfinite(now) or now <= 0:
        raise LoiXacThucBest("DONG_HO_KHONG_HOP_LE")
    return now


# ============================================================================
# KHO TỆP RIÊNG CHO TỪNG LỚP SECRET
# ============================================================================
def _thu_muc_kho() -> str:
    duong = os.path.join(cau_hinh.THU_MUC_DU_LIEU, "best_auth")
    try:
        os.makedirs(duong, mode=0o700, exist_ok=True)
    except OSError:
        raise LoiXacThucBest("KHO_KHONG_AN_TOAN") from None
    if os.path.islink(duong) or not os.path.isdir(duong):
        raise LoiXacThucBest("KHO_KHONG_AN_TOAN")
    try:
        os.chmod(duong, 0o700)
    except OSError:
        raise LoiXacThucBest("QUYEN_TEP_KHONG_AN_TOAN") from None
    return duong


def _duong_kho(loai: str) -> str:
    if loai not in TEP_KHO:
        raise LoiXacThucBest("SAI_LOP_SECRET")
    return os.path.join(_thu_muc_kho(), TEP_KHO[loai])


def _kiem_tra_tep_thuong(duong: str) -> None:
    if os.path.islink(duong):
        raise LoiXacThucBest("KHO_KHONG_AN_TOAN")
    try:
        st = os.lstat(duong)
    except OSError:
        raise LoiXacThucBest("KHO_HONG") from None
    if not stat.S_ISREG(st.st_mode):
        raise LoiXacThucBest("KHO_KHONG_AN_TOAN")
    if st.st_size > GIOI_HAN_KHO_BYTE:
        raise LoiXacThucBest("KHO_HONG")
    try:
        if stat.S_IMODE(st.st_mode) != 0o600:
            os.chmod(duong, 0o600)
            if stat.S_IMODE(os.stat(duong).st_mode) != 0o600:
                raise LoiXacThucBest("QUYEN_TEP_KHONG_AN_TOAN")
    except LoiXacThucBest:
        raise
    except OSError:
        raise LoiXacThucBest("QUYEN_TEP_KHONG_AN_TOAN") from None


def _kho_rong(loai: str) -> Dict[str, Any]:
    return {"phien_ban": PHIEN_BAN_KHO, "loai": loai, "ban_ghi": {}}


def _doc_kho_khong_khoa(loai: str) -> Dict[str, Any]:
    duong = _duong_kho(loai)
    if not os.path.exists(duong):
        return _kho_rong(loai)
    _kiem_tra_tep_thuong(duong)
    try:
        with open(duong, "r", encoding="utf-8") as f:
            du_lieu = json.load(f)
    except (OSError, ValueError):
        raise LoiXacThucBest("KHO_HONG") from None
    if (not isinstance(du_lieu, dict)
            or du_lieu.get("loai") != loai
            or not isinstance(du_lieu.get("ban_ghi"), dict)):
        raise LoiXacThucBest("KHO_HONG")
    return du_lieu


def _ghi_kho_khong_khoa(loai: str, du_lieu: Dict[str, Any]) -> None:
    """Ghi NGUYÊN TỬ: tệp tạm cùng thư mục → fsync → os.replace. Người đọc không thấy nửa vời."""
    duong = _duong_kho(loai)
    thu_muc = os.path.dirname(duong)
    try:
        fd, tam = tempfile.mkstemp(dir=thu_muc, prefix=".tam-kho-")
    except OSError:
        raise LoiXacThucBest("KHO_HONG") from None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(du_lieu, f, ensure_ascii=False, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tam, 0o600)
        os.replace(tam, duong)
        try:
            dfd = os.open(thu_muc, os.O_RDONLY)
            try:
                os.fsync(dfd)
            finally:
                os.close(dfd)
        except OSError:
            pass
    except LoiXacThucBest:
        raise
    except (OSError, ValueError):
        raise LoiXacThucBest("KHO_HONG") from None
    finally:
        if os.path.exists(tam):
            try:
                os.unlink(tam)
            except OSError:
                pass


# ---- Khóa liên tiến trình -------------------------------------------------
_KHOA_KHO_TIEN_TRINH = threading.RLock()
_KHOA_THREAD_THEO_CAP: Dict[str, threading.Lock] = {}
_KHOA_THREAD_BAO_VE = threading.Lock()


@contextlib.contextmanager
def _giu_khoa_tep(duong: str, chia_se: bool = False):
    co = os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(duong, co, 0o600)
    except OSError:
        raise LoiXacThucBest("KHO_KHONG_AN_TOAN") from None
    try:
        try:
            os.fchmod(fd, 0o600)
        except OSError:
            raise LoiXacThucBest("QUYEN_TEP_KHONG_AN_TOAN") from None
        try:
            fcntl.flock(fd, fcntl.LOCK_SH if chia_se else fcntl.LOCK_EX)
        except OSError:
            raise LoiXacThucBest("KHOA_KHONG_HO_TRO") from None
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            pass
        finally:
            os.close(fd)


@contextlib.contextmanager
def _giu_khoa_kho():
    """Khóa GHI toàn cục cho mọi tệp kho (trong tiến trình + liên tiến trình)."""
    with _KHOA_KHO_TIEN_TRINH:
        with _giu_khoa_tep(os.path.join(_thu_muc_kho(), "kho.lock")):
            yield


def _khoa_thread_theo_cap(tenant_id: str, tai_khoan: str) -> threading.Lock:
    khoa = hashlib.sha256(
        ("%s\x00%s" % (tenant_id, tai_khoan)).encode("utf-8")
    ).hexdigest()[:24]
    with _KHOA_THREAD_BAO_VE:
        return _KHOA_THREAD_THEO_CAP.setdefault(khoa, threading.Lock())


@contextlib.contextmanager
def _giu_khoa_lam_moi(tenant_id: str, tai_khoan: str):
    """Khóa theo (tenant, tài khoản) — giữ QUA cả lượt gọi mạng để chỉ MỘT lượt đăng nhập.

    Đây là chốt chống "đồng loạt re-login": nhiều thread trong một tiến trình và nhiều
    tiến trình dùng chung một tệp khóa (flock). Người thứ hai sau khi vào khóa sẽ ĐỌC LẠI
    cache và thấy token vừa được người thứ nhất ghi ⇒ không đăng nhập nữa.
    """
    khoa = _khoa_thread_theo_cap(tenant_id, tai_khoan)
    with khoa:
        ten = hashlib.sha256(
            ("%s\x00%s" % (tenant_id, tai_khoan)).encode("utf-8")
        ).hexdigest()[:24]
        with _giu_khoa_tep(os.path.join(_thu_muc_kho(), "refresh-%s.lock" % ten)):
            yield


# ============================================================================
# ĐỌC/GHI BẢN GHI TRONG KHO (KHÔNG tự giữ khóa — hàm gọi tự quyết định)
# ============================================================================
def _doc_ban_ghi(loai: str, tenant_id: str, tai_khoan: str) -> Optional[Dict[str, Any]]:
    kho = _doc_kho_khong_khoa(loai)
    theo_tenant = kho["ban_ghi"].get(tenant_id)
    if theo_tenant is None:
        return None
    if not isinstance(theo_tenant, dict):
        raise LoiXacThucBest("KHO_HONG")
    ban_ghi = theo_tenant.get(tai_khoan)
    if ban_ghi is None:
        return None
    if (not isinstance(ban_ghi, dict)
            or not isinstance(ban_ghi.get("ban_ma"), str)
            or isinstance(ban_ghi.get("cap_nhat_luc"), bool)
            or not isinstance(ban_ghi.get("cap_nhat_luc"), (int, float))
            or not math.isfinite(float(ban_ghi["cap_nhat_luc"]))):
        raise LoiXacThucBest("KHO_HONG")
    return ban_ghi


def _dat_ban_ghi_khong_khoa(loai: str, tenant_id: str, tai_khoan: str,
                            ban_ma: str, cap_nhat_luc: float) -> None:
    kho = _doc_kho_khong_khoa(loai)
    theo_tenant = kho["ban_ghi"].get(tenant_id)
    if theo_tenant is None:
        theo_tenant = {}
        kho["ban_ghi"][tenant_id] = theo_tenant
    if not isinstance(theo_tenant, dict):
        raise LoiXacThucBest("KHO_HONG")
    theo_tenant[tai_khoan] = {
        "ban_ma": ban_ma,
        "cap_nhat_luc": float(cap_nhat_luc),
        "phien_ban": PHIEN_BAN_KHO,
    }
    _ghi_kho_khong_khoa(loai, kho)


def _xoa_ban_ghi_khong_khoa(loai: str, tenant_id: str, tai_khoan: str) -> bool:
    kho = _doc_kho_khong_khoa(loai)
    theo_tenant = kho["ban_ghi"].get(tenant_id)
    if not isinstance(theo_tenant, dict) or tai_khoan not in theo_tenant:
        return False
    del theo_tenant[tai_khoan]
    _ghi_kho_khong_khoa(loai, kho)
    return True


def _ban_ma_credential_hien_tai(tenant_id: str, tai_khoan: str) -> Optional[str]:
    ban_ghi = _doc_ban_ghi(LOAI_CREDENTIAL, tenant_id, tai_khoan)
    return ban_ghi["ban_ma"] if ban_ghi else None


# ============================================================================
# GIẢI MÃ + KIỂM TRA CẤU TRÚC BÊN TRONG BẢN MÃ
# ============================================================================
def _bam_ban_ma(ban_ma: str) -> str:
    return hashlib.sha256(ban_ma.encode("utf-8")).hexdigest()[:32]


def _giai_ma_lop(loai: str, ban_ma: str, tenant_id: str, tai_khoan: str,
                 ma_loi: str) -> Dict[str, Any]:
    try:
        ro = bao_mat.giai_ma_cred(ban_ma, tenant_id, HANG)
    except Exception:  # noqa: BLE001 — mọi lỗi giải mã đều là TỪ CHỐI, không lộ chi tiết
        raise LoiXacThucBest(ma_loi) from None
    if not isinstance(ro, dict):
        raise LoiXacThucBest(ma_loi)
    if ro.get("loai") != loai:
        raise LoiXacThucBest("SAI_LOP_SECRET")
    if ro.get("tenant_id") != tenant_id or ro.get("tai_khoan") != tai_khoan:
        raise LoiXacThucBest("DU_LIEU_KHONG_KHOP")
    return ro


@dataclasses.dataclass(frozen=True)
class _CredentialNoiBo:
    username: str
    password: str
    ban_ma: str

    def __repr__(self) -> str:  # không để password rơi vào log khi ai đó in đối tượng
        return "_CredentialNoiBo(username=<che>, password=<che>, ban_ma=<che>)"


def _doc_credential(tenant_id: str, tai_khoan: str) -> _CredentialNoiBo:
    ban_ghi = _doc_ban_ghi(LOAI_CREDENTIAL, tenant_id, tai_khoan)
    if ban_ghi is None:
        raise LoiXacThucBest("THIEU_CREDENTIAL")
    ro = _giai_ma_lop(LOAI_CREDENTIAL, ban_ghi["ban_ma"], tenant_id, tai_khoan,
                      "KHONG_DOC_DUOC_CREDENTIAL")
    username = ro.get("username")
    password = ro.get("password")
    if not _hop_le_ten_dang_nhap(username) or not _hop_le_mat_khau(password):
        raise LoiXacThucBest("CREDENTIAL_KHONG_HOP_LE")
    return _CredentialNoiBo(username=username, password=password, ban_ma=ban_ghi["ban_ma"])


def _doc_token(tenant_id: str, tai_khoan: str,
               credential_bam: str) -> Optional[Dict[str, Any]]:
    ban_ghi = _doc_ban_ghi(LOAI_TOKEN_TRUY_CAP, tenant_id, tai_khoan)
    if ban_ghi is None:
        return None
    ro = _giai_ma_lop(LOAI_TOKEN_TRUY_CAP, ban_ghi["ban_ma"], tenant_id, tai_khoan,
                      "KHONG_DOC_DUOC_TOKEN")
    token = ro.get("token")
    if not _hop_le_chuoi_bi_mat(token, 1, GIOI_HAN_TOKEN_BYTE):
        raise LoiXacThucBest("KHONG_DOC_DUOC_TOKEN")
    phat = ro.get("phat_hanh_luc")
    het = ro.get("het_han_luc")
    if (isinstance(phat, bool) or isinstance(het, bool)
            or not isinstance(phat, (int, float)) or not isinstance(het, (int, float))
            or not math.isfinite(float(phat)) or not math.isfinite(float(het))):
        raise LoiXacThucBest("KHONG_DOC_DUOC_TOKEN")
    if ro.get("credential_bam") != credential_bam:
        raise LoiXacThucBest("TOKEN_KHONG_KHOP_CREDENTIAL")
    return {
        "token": token,
        "phat_hanh_luc": float(phat),
        "het_han_luc": float(het),
    }


def _token_con_han(ro: Dict[str, Any], now: float) -> bool:
    phat = ro["phat_hanh_luc"]
    het = ro["het_han_luc"]
    if het <= phat:
        return False
    if het - phat > HAN_TOKEN_GIAY + 1:
        return False
    if now < phat - LECH_DONG_HO_CHO_PHEP_GIAY:
        return False
    return now < het


# ============================================================================
# TRANSPORT ĐĂNG NHẬP — mặc định KHÔNG có; chỉ HTTPS; không tắt TLS
# ============================================================================
class _ChanChuyenHuong(urllib.request.HTTPRedirectHandler):
    """Từ chối MỌI chuyển hướng. Login không có lý do hợp lệ để 302 sang nơi khác.

    Quan trọng: nếu đi theo redirect, ta có thể bị đẩy từ HTTPS xuống HTTP hoặc sang host
    lạ — đúng hai thứ bị cấm. Trả None ⇒ urllib phát HTTPError cho mã 3xx, ta ánh xạ thành
    lỗi đăng nhập và KHÔNG gửi lại credential.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


def _la_loopback(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _chuan_hoa_base_url(base_url: Any, cho_phep_loopback: bool) -> str:
    if not isinstance(base_url, str) or not base_url or len(base_url) > 2048:
        raise LoiXacThucBest("URL_KHONG_HOP_LE")
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in base_url):
        raise LoiXacThucBest("URL_KHONG_HOP_LE")
    try:
        u = urllib.parse.urlsplit(base_url)
    except ValueError:
        raise LoiXacThucBest("URL_KHONG_HOP_LE") from None
    if u.scheme not in ("https", "http"):
        raise LoiXacThucBest("URL_KHONG_HOP_LE")
    if not u.hostname:
        raise LoiXacThucBest("URL_KHONG_HOP_LE")
    if u.username is not None or u.password is not None:
        raise LoiXacThucBest("URL_KHONG_HOP_LE")
    if u.query or u.fragment or u.path not in ("", "/"):
        raise LoiXacThucBest("URL_KHONG_HOP_LE")
    try:
        cong = u.port
    except ValueError:
        raise LoiXacThucBest("URL_KHONG_HOP_LE") from None
    if u.scheme == "http":
        if not cho_phep_loopback or not _la_loopback(u.hostname):
            raise LoiXacThucBest("HTTP_KHONG_DUOC_PHEP")
    netloc = u.hostname
    if ":" in netloc:                      # IPv6
        netloc = "[%s]" % netloc
    if cong is not None:
        netloc = "%s:%d" % (netloc, cong)
    return "%s://%s" % (u.scheme, netloc)


class TransportDangNhapHTTPS:
    """Gọi ĐÚNG một endpoint đã xác nhận: POST {base}/User/Login.

    KHÔNG tự đọc URL từ biến môi trường. Người dùng phải tạo và truyền/đặt transport một
    cách tường minh — nhờ vậy không có đường nào tự bật gọi mạng khi chưa được duyệt.

    `cho_phep_loopback=True` chỉ dành cho bộ thử MOCK (stub 127.0.0.1). Với host thật,
    URL buộc phải là HTTPS và chứng chỉ LUÔN được xác minh bằng SSLContext mặc định.
    """

    def __init__(self, base_url: str, *, cho_phep_loopback: bool = False,
                 thoi_gian_cho_giay: float = 15.0):
        if (not isinstance(thoi_gian_cho_giay, (int, float)) or isinstance(thoi_gian_cho_giay, bool)
                or not math.isfinite(float(thoi_gian_cho_giay))
                or not (0 < float(thoi_gian_cho_giay) <= 120)):
            raise LoiXacThucBest("THAM_SO_KHONG_HOP_LE")
        self._base_url = _chuan_hoa_base_url(base_url, bool(cho_phep_loopback))
        self._thoi_gian_cho = float(thoi_gian_cho_giay)
        # SSLContext MẶC ĐỊNH: verify_mode=CERT_REQUIRED, check_hostname=True.
        self._ngu_canh = ssl.create_default_context()
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),          # không đẩy credential qua proxy môi trường
            urllib.request.HTTPSHandler(context=self._ngu_canh),
            _ChanChuyenHuong(),
        )

    def __repr__(self) -> str:
        return "TransportDangNhapHTTPS(base_url=%r, tls=verify)" % self._base_url

    def dang_nhap(self, username: str, password: str) -> str:
        if not _hop_le_ten_dang_nhap(username) or not _hop_le_mat_khau(password):
            raise LoiXacThucBest("CREDENTIAL_KHONG_HOP_LE")
        url = self._base_url + DUONG_DAN_DANG_NHAP
        than = json.dumps(
            {"Username": username, "Password": password},
            ensure_ascii=False,
        ).encode("utf-8")
        yeu_cau = urllib.request.Request(
            url,
            data=than,
            method="POST",
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json",
                "User-Agent": "vip-express-hub/best-auth",
            },
        )
        try:
            with self._opener.open(yeu_cau, timeout=self._thoi_gian_cho) as tra:
                status = int(getattr(tra, "status", 200))
                if not (200 <= status < 300):
                    raise LoiXacThucBest("DANG_NHAP_THAT_BAI", http_status=status)
                raw = tra.read(GIOI_HAN_PHAN_HOI_BYTE + 1)
        except LoiXacThucBest:
            raise
        except urllib.error.HTTPError as e:
            # KHÔNG đọc/không đưa thân phản hồi vào lỗi: thân có thể chứa token hoặc echo
            # lại password. Chỉ mã HTTP là đủ để phân loại.
            try:
                e.close()
            except Exception:  # noqa: BLE001
                pass
            raise LoiXacThucBest("DANG_NHAP_THAT_BAI", http_status=int(e.code)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise LoiXacThucBest("KHONG_KET_NOI_DUOC") from None

        if len(raw) > GIOI_HAN_PHAN_HOI_BYTE:
            raise LoiXacThucBest("PHAN_HOI_QUA_LON")
        try:
            du_lieu = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            raise LoiXacThucBest("PHAN_HOI_KHONG_HOP_LE") from None
        if not isinstance(du_lieu, dict) or "token" not in du_lieu:
            raise LoiXacThucBest("PHAN_HOI_KHONG_HOP_LE")
        return _kiem_token(du_lieu["token"])


# Transport mặc định: None = TỪ CHỐI. Chỉ đặt được bằng lời gọi tường minh.
_TRANSPORT_MAC_DINH: Optional[Any] = None


def dat_transport_mac_dinh(transport: Optional[Any]) -> None:
    """Đặt transport dùng chung cho tiến trình. `None` = gỡ (trở về TỪ CHỐI)."""
    if transport is not None and not callable(getattr(transport, "dang_nhap", None)):
        raise LoiXacThucBest("TRANSPORT_KHONG_HOP_LE")
    global _TRANSPORT_MAC_DINH
    _TRANSPORT_MAC_DINH = transport


def _lay_transport(transport: Optional[Any]) -> Any:
    tr = transport if transport is not None else _TRANSPORT_MAC_DINH
    if tr is None:
        raise LoiXacThucBest("CHUA_CAU_HINH_TRANSPORT")
    if not callable(getattr(tr, "dang_nhap", None)):
        raise LoiXacThucBest("TRANSPORT_KHONG_HOP_LE")
    return tr


# ============================================================================
# LỚP A — CREDENTIAL ĐĂNG NHẬP BEST
# ============================================================================
def luu_credential_dang_nhap(tenant_id: str, tai_khoan: str, username: str,
                             password: str, *, dong_ho: Optional[Callable[[], float]] = None) -> Dict[str, Any]:
    """Lưu credential đăng nhập BEST (Username + Password) vào kho LỚP A.

    KHÔNG gọi mạng. Password KHÔNG BAO GIỜ được ghi dạng plaintext. Khi credential được
    thay, token cache của cùng (tenant, tài khoản) bị vô hiệu trong CÙNG lượt khóa ghi —
    nếu không, token cũ (gắn credential cũ) có thể tiếp tục được dùng.
    """
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    if not _hop_le_ten_dang_nhap(username) or not _hop_le_mat_khau(password):
        raise LoiXacThucBest("CREDENTIAL_KHONG_HOP_LE")
    now = _bay_gio(dong_ho)
    goi = {
        "loai": LOAI_CREDENTIAL,
        "tenant_id": tenant_id,
        "tai_khoan": tai_khoan,
        "username": username,
        "password": password,
        "phien_ban": PHIEN_BAN_KHO,
    }
    try:
        ban_ma, _duoi = bao_mat.ma_hoa_cred(goi, tenant_id, HANG)
    except Exception:  # noqa: BLE001
        _log("credential_luu", tenant_id, tai_khoan, "MA_HOA_LOI", LOAI_CREDENTIAL)
        _ghi_audit("best_auth.credential_luu", tenant_id, tai_khoan, "that_bai",
                   "MA_HOA_LOI", LOAI_CREDENTIAL)
        raise LoiXacThucBest("MA_HOA_LOI") from None

    try:
        with _giu_khoa_kho():
            _dat_ban_ghi_khong_khoa(LOAI_CREDENTIAL, tenant_id, tai_khoan, ban_ma, now)
            _xoa_ban_ghi_khong_khoa(LOAI_TOKEN_TRUY_CAP, tenant_id, tai_khoan)
    except LoiXacThucBest as e:
        _ghi_audit("best_auth.credential_luu", tenant_id, tai_khoan, "that_bai",
                   e.ma_loi, LOAI_CREDENTIAL)
        raise
    _log("credential_luu", tenant_id, tai_khoan, "OK", LOAI_CREDENTIAL)
    _ghi_audit("best_auth.credential_luu", tenant_id, tai_khoan, "thanh_cong",
               "OK", LOAI_CREDENTIAL)
    return {
        "tenant_id": tenant_id,
        "tai_khoan": tai_khoan,
        "lop": LOAI_CREDENTIAL,
        "da_luu": True,
        "cap_nhat_luc": now,
    }


def trang_thai_credential(tenant_id: str, tai_khoan: str) -> Dict[str, Any]:
    """Mô tả LỚP A — TUYỆT ĐỐI không trả username/password."""
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    ban_ghi = _doc_ban_ghi(LOAI_CREDENTIAL, tenant_id, tai_khoan)
    if ban_ghi is None:
        return {
            "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_CREDENTIAL,
            "co_credential": False, "doc_duoc": False, "cap_nhat_luc": None,
            "ma_ly_do": "THIEU_CREDENTIAL",
        }
    doc_duoc = True
    ma = "OK"
    try:
        _doc_credential(tenant_id, tai_khoan)
    except LoiXacThucBest as e:
        doc_duoc = False
        ma = e.ma_loi
    return {
        "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_CREDENTIAL,
        "co_credential": True, "doc_duoc": doc_duoc,
        "cap_nhat_luc": float(ban_ghi["cap_nhat_luc"]), "ma_ly_do": ma,
    }


# ============================================================================
# TOKEN TRUY CẬP — cache theo (tenant, tài khoản), làm mới CÓ KIỂM SOÁT
# ============================================================================
def _dang_nhap_va_kiem(transport: Any, credential: _CredentialNoiBo,
                       tenant_id: str, tai_khoan: str) -> str:
    try:
        token = transport.dang_nhap(credential.username, credential.password)
    except LoiXacThucBest as e:
        # Transport là biên tin cậy: chỉ chấp nhận mã NẰM TRONG bảng của module. Mã lạ
        # (do transport tự đặt, có thể chứa dữ liệu) bị quy về TRANSPORT_LOI — không để
        # chuỗi tùy ý đi vào exception/audit/log.
        ma = e.ma_loi if e.ma_loi in MA_LOI else "TRANSPORT_LOI"
        status = e.http_status if isinstance(e.http_status, int) and not isinstance(e.http_status, bool) else None
        _log("token_cap", tenant_id, tai_khoan, ma, LOAI_TOKEN_TRUY_CAP, status)
        _ghi_audit("best_auth.token_cap", tenant_id, tai_khoan, "that_bai",
                   ma, LOAI_TOKEN_TRUY_CAP)
        raise LoiXacThucBest(ma, http_status=status) from None
    except Exception as e:  # noqa: BLE001 — KHÔNG đưa thông điệp gốc (có thể chứa secret)
        _log("token_cap", tenant_id, tai_khoan, "TRANSPORT_LOI", LOAI_TOKEN_TRUY_CAP)
        _ghi_audit("best_auth.token_cap", tenant_id, tai_khoan, "that_bai",
                   "TRANSPORT_LOI", LOAI_TOKEN_TRUY_CAP)
        logger.warning(
            "best_auth transport_loi kieu=%s tham_chieu=%s",
            type(e).__name__, _bam_tham_chieu(tenant_id, tai_khoan),
        )
        raise LoiXacThucBest("TRANSPORT_LOI") from None
    try:
        return _kiem_token(token)
    except LoiXacThucBest as e:
        _log("token_cap", tenant_id, tai_khoan, e.ma_loi, LOAI_TOKEN_TRUY_CAP)
        _ghi_audit("best_auth.token_cap", tenant_id, tai_khoan, "that_bai",
                   e.ma_loi, LOAI_TOKEN_TRUY_CAP)
        raise


def _cache_token_sau_dang_nhap(tenant_id: str, tai_khoan: str,
                               credential: _CredentialNoiBo, token: str,
                               now: float) -> str:
    """Ghi token cache SAU khi so lại credential đang lưu. Trả "OK" hoặc "MA_HOA_LOI".

    Vì sao so lại: trong lúc gọi mạng, một lượt đổi credential có thể đã xảy ra. Token vừa
    lấy thuộc credential CŨ; trả nó cho bên gọi là để credential đã bị thay tiếp tục được
    dùng — đúng thứ cần tránh. Vì vậy nếu credential đổi giữa chừng, hàm này KHÔNG cache và
    NÉM `CREDENTIAL_DA_DOI_KHONG_LUU`; token cũ bị bỏ, lượt sau đăng nhập bằng credential mới.
    """
    credential_bam = _bam_ban_ma(credential.ban_ma)
    sql = {
        "loai": LOAI_TOKEN_TRUY_CAP,
        "tenant_id": tenant_id,
        "tai_khoan": tai_khoan,
        "token": token,
        "phat_hanh_luc": now,
        "het_han_luc": now + HAN_TOKEN_GIAY,
        "credential_bam": credential_bam,
        "nguon": "POST %s (đặc tả B2, CHƯA KIỂM CHỨNG với BEST thật)" % DUONG_DAN_DANG_NHAP,
        "phien_ban": PHIEN_BAN_KHO,
    }
    try:
        ban_ma, _duoi = bao_mat.ma_hoa_cred(sql, tenant_id, HANG)
    except Exception:  # noqa: BLE001
        return "MA_HOA_LOI"
    with _giu_khoa_kho():
        credential_doi = _ban_ma_credential_hien_tai(tenant_id, tai_khoan) != credential.ban_ma
        if not credential_doi:
            _dat_ban_ghi_khong_khoa(LOAI_TOKEN_TRUY_CAP, tenant_id, tai_khoan, ban_ma, now)
    if credential_doi:
        _log("token_khong_luu", tenant_id, tai_khoan,
             "CREDENTIAL_DA_DOI_KHONG_LUU", LOAI_TOKEN_TRUY_CAP)
        _ghi_audit("best_auth.token_cap", tenant_id, tai_khoan, "that_bai",
                   "CREDENTIAL_DA_DOI_KHONG_LUU", LOAI_TOKEN_TRUY_CAP)
        raise LoiXacThucBest("CREDENTIAL_DA_DOI_KHONG_LUU")
    return "OK"


def lay_token(tenant_id: str, tai_khoan: str, *, transport: Optional[Any] = None,
              dong_ho: Optional[Callable[[], float]] = None) -> str:
    """Trả token còn hạn; hết hạn mới đăng nhập lại — CHỈ MỘT LẦN cho mỗi lượt hết hạn.

    Đây là API NỘI BỘ cho adapter hãng. KHÔNG được serialize kết quả vào response HTTP,
    log hay audit. Muốn mô tả trạng thái, dùng `trang_thai_token()` (không có token).

    Thứ tự kiểm tra CỐ Ý: credential được đọc/giải mã TRƯỚC token cache. Nhờ vậy:
      · thiếu credential ⇒ TỪ CHỐI, kể cả khi cache còn hạn;
      · credential của tenant A không thể "mượn" cache để dùng cho tenant B;
      · token cache gắn với băm của bản mã credential hiện tại (đổi credential ⇒ token cũ
        không còn hợp lệ, dù lượt vô hiệu cache có bị lỡ).
    """
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    credential = _doc_credential(tenant_id, tai_khoan)   # THIEU_CREDENTIAL nếu chưa có
    now = _bay_gio(dong_ho)

    try:
        ro = _doc_token(tenant_id, tai_khoan, _bam_ban_ma(credential.ban_ma))
    except LoiXacThucBest as e:
        if e.ma_loi in MA_CACHE_TOKEN_HONG:
            ro = None
            _log("token_cache_bo_qua", tenant_id, tai_khoan, e.ma_loi, LOAI_TOKEN_TRUY_CAP)
        else:
            raise
    if ro is not None and _token_con_han(ro, now):
        return ro["token"]

    tr = _lay_transport(transport)
    with _giu_khoa_lam_moi(tenant_id, tai_khoan):
        # ĐỌC LẠI sau khi vào khóa: người đi trước có thể vừa đăng nhập xong.
        credential = _doc_credential(tenant_id, tai_khoan)
        now = _bay_gio(dong_ho)
        try:
            ro = _doc_token(tenant_id, tai_khoan, _bam_ban_ma(credential.ban_ma))
        except LoiXacThucBest as e:
            if e.ma_loi in MA_CACHE_TOKEN_HONG:
                ro = None
            else:
                raise
        if ro is not None and _token_con_han(ro, now):
            return ro["token"]

        token = _dang_nhap_va_kiem(tr, credential, tenant_id, tai_khoan)
        now_sau = _bay_gio(dong_ho)
        ma_luu = _cache_token_sau_dang_nhap(tenant_id, tai_khoan, credential, token, now_sau)
        _log("token_cap", tenant_id, tai_khoan, ma_luu, LOAI_TOKEN_TRUY_CAP)
        _ghi_audit("best_auth.token_cap", tenant_id, tai_khoan, "thanh_cong",
                   ma_luu, LOAI_TOKEN_TRUY_CAP)
        return token


def lam_moi_token(tenant_id: str, tai_khoan: str, *, token_cu: Optional[str] = None,
                  transport: Optional[Any] = None,
                  dong_ho: Optional[Callable[[], float]] = None) -> str:
    """Làm mới CÓ KIỂM SOÁT — dùng khi hãng trả 401 cho token đang dùng.

    `token_cu`: token vừa bị từ chối. Nhờ nó, nếu một tiến trình/thread khác đã làm mới
    xong trước khi ta vào được khóa, ta dùng token mới của họ thay vì đăng nhập lần nữa.
    Đây là chốt chống "bão 401" làm đồng loạt re-login.
    """
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    if token_cu is not None:
        _kiem_token(token_cu)
    credential = _doc_credential(tenant_id, tai_khoan)
    tr = _lay_transport(transport)
    with _giu_khoa_lam_moi(tenant_id, tai_khoan):
        credential = _doc_credential(tenant_id, tai_khoan)
        now = _bay_gio(dong_ho)
        if token_cu is not None:
            try:
                ro = _doc_token(tenant_id, tai_khoan, _bam_ban_ma(credential.ban_ma))
            except LoiXacThucBest as e:
                if e.ma_loi in MA_CACHE_TOKEN_HONG:
                    ro = None
                else:
                    raise
            if ro is not None and _token_con_han(ro, now) and ro["token"] != token_cu:
                _log("token_lam_moi", tenant_id, tai_khoan, "DA_CO_TOKEN_MOI", LOAI_TOKEN_TRUY_CAP)
                return ro["token"]
            if ro is not None and ro["token"] == token_cu:
                # Token đã bị hãng từ chối: PHẢI bỏ khỏi cache TRƯỚC khi thử đăng nhập.
                # Nếu lượt đăng nhập sau đó hỏng, cache rỗng chứ không tiếp tục phục vụ
                # đúng token vừa bị 401 (nếu giữ, lay_token sẽ trả token chết tới 30 ngày).
                with _giu_khoa_kho():
                    _xoa_ban_ghi_khong_khoa(LOAI_TOKEN_TRUY_CAP, tenant_id, tai_khoan)
                _log("token_lam_moi", tenant_id, tai_khoan,
                     "XOA_TOKEN_BI_TU_CHOI", LOAI_TOKEN_TRUY_CAP)
                _ghi_audit("best_auth.token_lam_moi", tenant_id, tai_khoan, "thanh_cong",
                           "XOA_TOKEN_BI_TU_CHOI", LOAI_TOKEN_TRUY_CAP)
        token = _dang_nhap_va_kiem(tr, credential, tenant_id, tai_khoan)
        now_sau = _bay_gio(dong_ho)
        ma_luu = _cache_token_sau_dang_nhap(tenant_id, tai_khoan, credential, token, now_sau)
        _log("token_lam_moi", tenant_id, tai_khoan, ma_luu, LOAI_TOKEN_TRUY_CAP)
        _ghi_audit("best_auth.token_lam_moi", tenant_id, tai_khoan, "thanh_cong",
                   ma_luu, LOAI_TOKEN_TRUY_CAP)
        return token


def huy_token(tenant_id: str, tai_khoan: str, *, ly_do: str = "CHU_DONG") -> bool:
    """Vô hiệu token cache (KHÔNG phải xóa dữ liệu nghiệp vụ). Lượt sau sẽ đăng nhập lại."""
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    ma = _ma_ly_do_an_toan(ly_do)
    # Khóa theo cặp TRƯỚC khóa ghi toàn cục (cùng thứ tự với lay_token). Nếu chỉ lấy khóa
    # toàn cục, một lượt đăng nhập đang chạy có thể ghi cache SAU khi ta vừa xóa ⇒ token
    # tưởng đã hủy vẫn sống. Đây là ca đua thật, không phải lý thuyết.
    with _giu_khoa_lam_moi(tenant_id, tai_khoan):
        with _giu_khoa_kho():
            da_xoa = _xoa_ban_ghi_khong_khoa(LOAI_TOKEN_TRUY_CAP, tenant_id, tai_khoan)
    _log("token_huy", tenant_id, tai_khoan, ma, LOAI_TOKEN_TRUY_CAP)
    _ghi_audit("best_auth.token_huy", tenant_id, tai_khoan, "thanh_cong", ma, LOAI_TOKEN_TRUY_CAP)
    return da_xoa


def trang_thai_token(tenant_id: str, tai_khoan: str, *,
                     dong_ho: Optional[Callable[[], float]] = None) -> Dict[str, Any]:
    """Mô tả token cache — KHÔNG trả token. Dùng cho dashboard/chẩn đoán."""
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    now = _bay_gio(dong_ho)
    credential_bam: Optional[str] = None
    try:
        credential_bam = _bam_ban_ma(_doc_credential(tenant_id, tai_khoan).ban_ma)
    except LoiXacThucBest as e:
        if e.ma_loi != "THIEU_CREDENTIAL":
            return {
                "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_TOKEN_TRUY_CAP,
                "co_ban_ghi": _doc_ban_ghi(LOAI_TOKEN_TRUY_CAP, tenant_id, tai_khoan) is not None,
                "con_han": False, "het_han_luc": None, "con_lai_giay": 0,
                "ma_ly_do": e.ma_loi,
            }
        credential_bam = None
    ban_ghi = _doc_ban_ghi(LOAI_TOKEN_TRUY_CAP, tenant_id, tai_khoan)
    if ban_ghi is None:
        return {
            "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_TOKEN_TRUY_CAP,
            "co_ban_ghi": False, "con_han": False, "het_han_luc": None,
            "con_lai_giay": 0, "ma_ly_do": "THIEU_TOKEN",
        }
    if credential_bam is None:
        return {
            "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_TOKEN_TRUY_CAP,
            "co_ban_ghi": True, "con_han": False, "het_han_luc": None,
            "con_lai_giay": 0, "ma_ly_do": "THIEU_CREDENTIAL",
        }
    try:
        ro = _doc_token(tenant_id, tai_khoan, credential_bam)
    except LoiXacThucBest as e:
        return {
            "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_TOKEN_TRUY_CAP,
            "co_ban_ghi": True, "con_han": False, "het_han_luc": None,
            "con_lai_giay": 0, "ma_ly_do": e.ma_loi,
        }
    if ro is None:
        return {
            "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_TOKEN_TRUY_CAP,
            "co_ban_ghi": False, "con_han": False, "het_han_luc": None,
            "con_lai_giay": 0, "ma_ly_do": "THIEU_TOKEN",
        }
    con_han = _token_con_han(ro, now)
    return {
        "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_TOKEN_TRUY_CAP,
        "co_ban_ghi": True, "con_han": con_han,
        "het_han_luc": ro["het_han_luc"],
        "con_lai_giay": max(0, int(ro["het_han_luc"] - now)),
        "ma_ly_do": "OK" if con_han else "HET_HAN",
    }


# ============================================================================
# LỚP B — BEARER TOKEN NHẬN WEBHOOK (KHÁC HOÀN TOÀN LỚP A)
# ============================================================================
@dataclasses.dataclass(frozen=True)
class KetQuaKiemBearer:
    hop_le: bool
    ma_ly_do: str

    def __bool__(self) -> bool:
        return self.hop_le


def luu_bearer_webhook(tenant_id: str, tai_khoan: str, bearer: str, *,
                       webhook_ma: str = "",
                       dong_ho: Optional[Callable[[], float]] = None) -> Dict[str, Any]:
    """Lưu Bearer token BEST dùng để XÁC THỰC WEBHOOK GỬI TỚI (kho LỚP B).

    Đây KHÔNG phải token đăng nhập. Hàm của lớp này không đọc/ghi kho credential, và
    ngược lại — xem ca thử "dùng lẫn hai lớp".
    """
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    if not _hop_le_chuoi_bi_mat(bearer, 1, GIOI_HAN_TOKEN_BYTE):
        raise LoiXacThucBest("BEARER_KHONG_HOP_LE")
    if not isinstance(webhook_ma, str) or len(webhook_ma) > 128 or any(ord(c) < 0x20 for c in webhook_ma):
        raise LoiXacThucBest("WEBHOOK_MA_KHONG_HOP_LE")
    now = _bay_gio(dong_ho)
    goi = {
        "loai": LOAI_WEBHOOK,
        "tenant_id": tenant_id,
        "tai_khoan": tai_khoan,
        "webhook_ma": webhook_ma,
        "bearer": bearer,
        "phien_ban": PHIEN_BAN_KHO,
    }
    try:
        ban_ma, _duoi = bao_mat.ma_hoa_cred(goi, tenant_id, HANG)
    except Exception:  # noqa: BLE001
        _ghi_audit("best_auth.bearer_luu", tenant_id, tai_khoan, "that_bai",
                   "MA_HOA_LOI", LOAI_WEBHOOK)
        raise LoiXacThucBest("MA_HOA_LOI") from None
    try:
        with _giu_khoa_kho():
            _dat_ban_ghi_khong_khoa(LOAI_WEBHOOK, tenant_id, tai_khoan, ban_ma, now)
    except LoiXacThucBest as e:
        _ghi_audit("best_auth.bearer_luu", tenant_id, tai_khoan, "that_bai",
                   e.ma_loi, LOAI_WEBHOOK)
        raise
    _log("bearer_luu", tenant_id, tai_khoan, "OK", LOAI_WEBHOOK)
    _ghi_audit("best_auth.bearer_luu", tenant_id, tai_khoan, "thanh_cong",
               "OK", LOAI_WEBHOOK)
    return {
        "tenant_id": tenant_id,
        "tai_khoan": tai_khoan,
        "webhook_ma": webhook_ma,
        "lop": LOAI_WEBHOOK,
        "da_luu": True,
        "cap_nhat_luc": now,
    }


def kiem_bearer_webhook(tenant_id: str, tai_khoan: str, header_value: Any, *,
                        webhook_ma: Optional[str] = None) -> KetQuaKiemBearer:
    """Xác thực header `Authorization: Bearer <token>` của webhook BEST.

    Trả kết quả CÓ MÃ, không ném lỗi cho dữ liệu đến (header thiếu/sai) — webhook phải trả
    401 rõ ràng thay vì 500. Riêng tenant không xác định được thì NÉM `THIEU_TENANT`:
    không có tenant thì không có kho để so, và mọi câu trả lời "hợp lệ" đều là bịa.

    Header name `Authorization` đã được DOCX chính thức xác nhận (JWT Bearer, cấu hình trong
    V9). Hàm nhận GIÁ TRỊ header, không nhận tên; so sánh bằng `hmac.compare_digest`.
    """
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    if not isinstance(header_value, str) or not header_value.strip():
        _log("bearer_kiem", tenant_id, tai_khoan, "THIEU_HEADER", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "THIEU_HEADER")
    if len(header_value) > GIOI_HAN_HEADER_BYTE:
        _log("bearer_kiem", tenant_id, tai_khoan, "HEADER_QUA_DAI", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "HEADER_QUA_DAI")
    m = re.match(r"^[ \t]*Bearer[ \t]+(\S+)[ \t]*\Z", header_value, re.IGNORECASE)
    if not m:
        _log("bearer_kiem", tenant_id, tai_khoan, "SAI_DINH_DANG_BEARER", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "SAI_DINH_DANG_BEARER")
    ung_vien = m.group(1)
    if not _hop_le_chuoi_bi_mat(ung_vien, 1, GIOI_HAN_TOKEN_BYTE):
        _log("bearer_kiem", tenant_id, tai_khoan, "BEARER_KHONG_HOP_LE", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "BEARER_KHONG_HOP_LE")

    try:
        ban_ghi = _doc_ban_ghi(LOAI_WEBHOOK, tenant_id, tai_khoan)
    except LoiXacThucBest as e:
        _log("bearer_kiem", tenant_id, tai_khoan, e.ma_loi, LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, e.ma_loi)
    if ban_ghi is None:
        _log("bearer_kiem", tenant_id, tai_khoan, "KHONG_CO_BEARER_DA_LUU", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "KHONG_CO_BEARER_DA_LUU")
    try:
        ro = _giai_ma_lop(LOAI_WEBHOOK, ban_ghi["ban_ma"], tenant_id, tai_khoan,
                          "KHONG_DOC_DUOC_BEARER")
    except LoiXacThucBest as e:
        _log("bearer_kiem", tenant_id, tai_khoan, e.ma_loi, LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, e.ma_loi)
    if webhook_ma is not None and ro.get("webhook_ma") != webhook_ma:
        _log("bearer_kiem", tenant_id, tai_khoan, "DU_LIEU_KHONG_KHOP", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "DU_LIEU_KHONG_KHOP")
    da_luu = ro.get("bearer")
    if not _hop_le_chuoi_bi_mat(da_luu, 1, GIOI_HAN_TOKEN_BYTE):
        _log("bearer_kiem", tenant_id, tai_khoan, "KHONG_DOC_DUOC_BEARER", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "KHONG_DOC_DUOC_BEARER")
    # So sánh thời gian hằng: băm trước để không lộ độ dài/từng byte qua thời gian.
    khop = hmac.compare_digest(
        hashlib.sha256(ung_vien.encode("utf-8")).digest(),
        hashlib.sha256(da_luu.encode("utf-8")).digest(),
    )
    if not khop:
        _log("bearer_kiem", tenant_id, tai_khoan, "BEARER_KHONG_KHOP", LOAI_WEBHOOK)
        return KetQuaKiemBearer(False, "BEARER_KHONG_KHOP")
    return KetQuaKiemBearer(True, "OK")


def trang_thai_bearer_webhook(tenant_id: str, tai_khoan: str) -> Dict[str, Any]:
    """Mô tả LỚP B — không trả bearer."""
    tenant_id = _bat_buoc_tenant(tenant_id)
    tai_khoan = _bat_buoc_tai_khoan(tai_khoan)
    ban_ghi = _doc_ban_ghi(LOAI_WEBHOOK, tenant_id, tai_khoan)
    if ban_ghi is None:
        return {
            "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_WEBHOOK,
            "co_bearer": False, "doc_duoc": False, "cap_nhat_luc": None,
            "ma_ly_do": "KHONG_CO_BEARER_DA_LUU",
        }
    doc_duoc = True
    ma = "OK"
    webhook_ma = None
    try:
        ro = _giai_ma_lop(LOAI_WEBHOOK, ban_ghi["ban_ma"], tenant_id, tai_khoan,
                          "KHONG_DOC_DUOC_BEARER")
        webhook_ma = ro.get("webhook_ma")
    except LoiXacThucBest as e:
        doc_duoc = False
        ma = e.ma_loi
    return {
        "tenant_id": tenant_id, "tai_khoan": tai_khoan, "lop": LOAI_WEBHOOK,
        "co_bearer": True, "doc_duoc": doc_duoc, "webhook_ma": webhook_ma,
        "cap_nhat_luc": float(ban_ghi["cap_nhat_luc"]), "ma_ly_do": ma,
    }


# ============================================================================
# XOAY KHÓA CHO BA TỆP KHO — `bao_mat.xoay_khoa()` gọi hàm ở dưới
# ============================================================================
# Vì sao phải có: `bao_mat.xoay_khoa()` chỉ mã hóa lại `carrier_accounts`. Ba tệp kho của
# module này KHÔNG nằm trong schema, nên trước bản vá chúng không bao giờ được xoay: secret
# BEST sống mãi dưới khóa cũ, và tới lúc ai đó cho nghỉ khóa cũ thì credential/token/bearer
# của BEST thành rác — im lặng cho tới lượt gọi hãng đầu tiên (rủi ro #11 của
# docs/BEST_EXPRESS_SECURITY_REVIEW.md). Hàm dưới đây đóng đúng khoảng đó.
#
# LUẬT AN TOÀN (không phải trang trí):
#   1. CHỈ mã hóa lại bản ghi ĐÃ GIẢI ĐƯỢC và ĐÚNG chỗ của nó (loai + tenant_id + tai_khoan
#      nằm trong bản mã). Bản mã bị chép từ tenant/account khác hay bị chép sang lớp khác
#      KHÔNG được mã hóa lại: làm vậy là "hợp pháp hóa" bản ghi trộm dưới AAD của nạn nhân.
#   2. Một bản ghi hỏng KHÔNG làm hỏng cả lượt và KHÔNG bị ghi đè; nó được báo ra.
#   3. Ghi cả tệp một lần bằng đường NGUYÊN TỬ sẵn có (`_ghi_kho_khong_khoa`), dưới khóa ghi
#      toàn cục `_giu_khoa_kho()` — cùng khóa với mọi lượt ghi khác của module.
#   4. Token cache tham chiếu `credential_bam = sha256(bản mã credential)`. Khi credential được
#      mã hóa lại, băm đó đổi; hàm cập nhật luôn để KHÔNG biến một lượt xoay khóa thành một
#      loạt lượt đăng nhập lại (mỗi tài khoản một lượt) — nếu không cập nhật, token vẫn an toàn
#      nhưng bị bỏ cache, đúng "bão 401" mà `lam_moi_token` sinh ra để tránh.
#   5. Không tạo thư mục/thư mục kho khi chưa có kho: một module chưa dùng BEST không được
#      sinh tệp lạ chỉ vì ai đó xoay khóa chung.
#
# Hàm KHÔNG tự sinh khóa, KHÔNG đổi khóa hiện hành. `key_id_dich` do bên gọi quyết định (thường
# là khóa vừa được đặt làm hiện hành trong `bao_mat.xoay_khoa`). Khóa cũ vẫn nằm trong
# `secret_provider`, nên bản ghi nào chưa chuyển vẫn giải được.

_MA_LOI_DOC_KHO = {
    LOAI_CREDENTIAL: "KHONG_DOC_DUOC_CREDENTIAL",
    LOAI_TOKEN_TRUY_CAP: "KHONG_DOC_DUOC_TOKEN",
    LOAI_WEBHOOK: "KHONG_DOC_DUOC_BEARER",
}

_DEM_KHO = {
    LOAI_CREDENTIAL: "so_credential_dang_nhap",
    LOAI_TOKEN_TRUY_CAP: "so_token_truy_cap",
    LOAI_WEBHOOK: "so_bearer_webhook",
}


def _xoay_mot_kho(loai: str, key_id_dich: str, kq: Dict[str, Any],
                  bam_credential: Optional[Dict[Any, Any]] = None) -> Dict[Any, Any]:
    """Mã hóa lại MỘT tệp kho. Trả map {(tenant, tài khoản): (băm_cũ, băm_mới)} cho credential."""
    try:
        kho = _doc_kho_khong_khoa(loai)
    except LoiXacThucBest as e:
        # Tệp hỏng/sai cấu trúc: KHÔNG ghi đè, chỉ báo. Ghi đè ở đây là xóa mất secret chưa đọc.
        kq["hong"].append("%s: %s" % (loai, e.ma_loi))
        return {}
    da_doi = []
    bam_doi = {}
    for tenant_id, theo_tenant in kho["ban_ghi"].items():
        if not isinstance(theo_tenant, dict):
            kq["hong"].append("%s: KHO_HONG (nhóm tenant %r không phải object)" % (loai, tenant_id))
            continue
        for tai_khoan, ban_ghi in theo_tenant.items():
            kq["so_ban_ghi"] += 1
            if (not isinstance(ban_ghi, dict)
                    or not isinstance(ban_ghi.get("ban_ma"), str)
                    or not ban_ghi["ban_ma"]):
                kq["hong"].append("%s tenant=%s tai_khoan=%s: KHO_HONG (bản ghi không đúng cấu trúc)"
                                  % (loai, tenant_id, tai_khoan))
                continue
            ban_ma_cu = ban_ghi["ban_ma"]
            can_xoay = bao_mat.can_xoay(ban_ma_cu, key_id_dich)
            cap = (bam_credential.get((tenant_id, tai_khoan))
                   if loai == LOAI_TOKEN_TRUY_CAP and bam_credential else None)
            if not can_xoay and not cap:
                kq["so_giu_nguyen"] += 1
                continue
            # CHỈ giải được + ĐÚNG slot thì mới được mã hóa lại (luật 1 ở trên).
            try:
                ro = _giai_ma_lop(loai, ban_ma_cu, tenant_id, tai_khoan, _MA_LOI_DOC_KHO[loai])
            except LoiXacThucBest as e:
                kq["hong"].append("%s tenant=%s tai_khoan=%s: %s"
                                  % (loai, tenant_id, tai_khoan, e.ma_loi))
                continue
            if cap and ro.get("credential_bam") == cap[0]:
                ro["credential_bam"] = cap[1]
                can_xoay = True
            if not can_xoay:
                kq["so_giu_nguyen"] += 1
                continue
            try:
                ban_ma_moi, _duoi = bao_mat.ma_hoa_cred(ro, tenant_id, HANG)
                # Kiểm lại NGAY trên bản mới: sai khóa/AAD/slot thì không được ghi xuống.
                _giai_ma_lop(loai, ban_ma_moi, tenant_id, tai_khoan, _MA_LOI_DOC_KHO[loai])
                # `ma_hoa_cred` dùng khóa HIỆN HÀNH. Bên gọi phải đặt `key_id_dich` làm khóa
                # hiện hành TRƯỚC (đúng thứ tự `bao_mat.xoay_khoa` làm). Nếu lệch — ví dụ gọi
                # thẳng hàm này với một khóa cũ — thì KHÔNG được ghi: báo hỏng thay vì lặng lẽ
                # coi như đã xoay sang một khóa mà bản mã không hề mang.
                if bao_mat.key_id_cua(ban_ma_moi) != key_id_dich:
                    kq["hong"].append("%s tenant=%s tai_khoan=%s: SAI_KEY_ID_DICH"
                                      % (loai, tenant_id, tai_khoan))
                    continue
            except LoiXacThucBest:
                kq["hong"].append("%s tenant=%s tai_khoan=%s: MA_HOA_LOI"
                                  % (loai, tenant_id, tai_khoan))
                continue
            except Exception:  # noqa: BLE001 — không đưa chuỗi lạ vào kết quả/audit
                kq["hong"].append("%s tenant=%s tai_khoan=%s: MA_HOA_LOI"
                                  % (loai, tenant_id, tai_khoan))
                continue
            ban_ghi["ban_ma"] = ban_ma_moi
            da_doi.append((tenant_id, tai_khoan))
            if loai == LOAI_CREDENTIAL:
                bam_doi[(tenant_id, tai_khoan)] = (_bam_ban_ma(ban_ma_cu),
                                                   _bam_ban_ma(ban_ma_moi))
    if da_doi:
        try:
            _ghi_kho_khong_khoa(loai, kho)
        except LoiXacThucBest as e:
            # Không ghi được thì KHÔNG báo đã xoay (số đếm chỉ cộng sau khi ghi thành công).
            kq["hong"].append("%s: ghi kho hỏng (%s) — giữ nguyên %d bản ghi"
                              % (loai, e.ma_loi, len(da_doi)))
            return {}
        kq[_DEM_KHO[loai]] += len(da_doi)
    return bam_doi


def ma_hoa_lai_kho(key_id_dich: str) -> Dict[str, Any]:
    """Mã hóa lại MỌI secret trong ba tệp kho BEST sang `key_id_dich`.

    Trả dict CÓ MÃ: số bản ghi đã xoay theo từng lớp, số bản ghi giữ nguyên, và `hong` (danh
    sách bản ghi KHÔNG xoay được, kèm mã lý do). Không trả/ném nội dung secret.

    Idempotent: gọi lần hai khi mọi bản ghi đã ở `key_id_dich` thì không ghi tệp nào
    (`so_ban_ghi > 0`, các số `so_*` = 0). Chưa có thư mục kho ⇒ trả toàn 0, không tạo gì.
    """
    if (not isinstance(key_id_dich, str) or not key_id_dich or len(key_id_dich) > 128
            or any(ord(c) < 0x21 for c in key_id_dich)):
        raise LoiXacThucBest("THAM_SO_KHONG_HOP_LE")
    kq = {
        "key_id": key_id_dich,
        "so_credential_dang_nhap": 0,
        "so_token_truy_cap": 0,
        "so_bearer_webhook": 0,
        "so_ban_ghi": 0,
        "so_giu_nguyen": 0,
        "hong": [],
    }
    # KHÔNG dùng `_thu_muc_kho()` ở đây: hàm đó TẠO thư mục. Chưa có kho thì không có gì để xoay.
    if not os.path.isdir(os.path.join(cau_hinh.THU_MUC_DU_LIEU, "best_auth")):
        return kq
    # MỘT khóa ghi cho cả ba tệp: token được cập nhật `credential_bam` ngay sau khi credential
    # đổi, không để lượt đọc xen giữa thấy cặp (credential mới, token trỏ credential cũ).
    with _giu_khoa_kho():
        # 1) Credential TRƯỚC — token tham chiếu băm của chính bản mã credential.
        bam_doi = _xoay_mot_kho(LOAI_CREDENTIAL, key_id_dich, kq)
        # 2) Token — xoay khóa và/hoặc cập nhật `credential_bam` nếu credential vừa đổi.
        _xoay_mot_kho(LOAI_TOKEN_TRUY_CAP, key_id_dich, kq, bam_credential=bam_doi)
        # 3) Bearer webhook.
        _xoay_mot_kho(LOAI_WEBHOOK, key_id_dich, kq)
    return kq
