# Cấu hình backend Multi-Tenant SaaS — local-first. Không secret thật trong file này.
import os

THU_MUC_APP = os.path.dirname(os.path.abspath(__file__))
THU_MUC_GOC = os.path.dirname(THU_MUC_APP)
THU_MUC_DU_LIEU = os.environ.get("VIP_HUB_DATA", os.path.join(THU_MUC_APP, "du-lieu"))
DUONG_DAN_CSDL = os.path.join(THU_MUC_DU_LIEU, "hub.db")
DUONG_DAN_KHOA = os.path.join(THU_MUC_DU_LIEU, "khoa-noi-bo.key")  # khóa mã hóa credentials, 0600, ngoài git
CONG_MAC_DINH = int(os.environ.get("VIP_HUB_PORT", "8897"))


# ============================================================================
# G22 — KHO ĐANG CHẠY (S8 / P-G15-02): KHAI BÁO, KHÔNG ĐOÁN
# ============================================================================
# Vì sao phải là một KHAI BÁO chứ không phải một phép đo: `app/csdl.py` thuần SQLite (không có
# nhánh PostgreSQL), nên hệ KHÔNG có cách nào tự biết dữ liệu nghiệp vụ đang nằm ở đâu. Mọi phép
# suy ra từ mtime / kích thước / tên tệp đều là ĐOÁN, và nó sẽ im lặng đúng vào lúc cần nhất:
# một `hub.db` CŨ còn sót lại trông y hệt một `hub.db` đang phục vụ (P-G15-02 `do2b`).
KHO_SQLITE = "sqlite"
KHO_POSTGRESQL = "postgresql"
KHO_DANG_CHAY_HOP_LE = (KHO_SQLITE, KHO_POSTGRESQL)
BIEN_KHAI_KHO = "VIP_KHO_DANG_CHAY"

# MẶC ĐỊNH AN TOÀN: **CHƯA KHAI ⇒ TỪ CHỐI**. `None` nghĩa là chưa ai khai, và `sao_luu()` TỪ
# CHỐI chứ không đoán — một bản sao lưu không chứa dữ liệu đang phục vụ là ĐƯỜNG LÙI GIẢ, và
# đường lùi giả chỉ lộ ra khi đã quá muộn.
#
# KHAI Ở ĐÂU: sửa thẳng dòng dưới (chỗ chính thức), hoặc đặt biến môi trường
# `VIP_KHO_DANG_CHAY=sqlite|postgresql` cho tiến trình chạy `migrate`. Khai SAI CHÍNH TẢ không
# được coi là "chưa khai": `migrate._chuan_hoa_kho()` TỪ CHỐI kèm nguyên văn giá trị sai — coi
# nó là chưa khai là âm thầm đưa hệ về đúng chỗ đang muốn tránh.
#
# CÁI GIÁ CỦA MẶC ĐỊNH NÀY (đo, không đoán — docs/G22_SAOLUU.md §4): `migrate.chay()` trên một
# thư mục dữ liệu MỚI CÓ gọi `sao_luu()`, và 8 bộ thử NGOÀI vùng được ghi của AG-02 gọi
# `migrate.chay()` mà không khai kho ⇒ chúng TỪ CHỐI cho tới khi mỗi bộ khai một dòng. Đây là
# LỰA CHỌN CỤC BỘ ĐÃ ĐƯỢC UỶ QUYỀN của AG-02 (sửa local), KHÔNG phải quyết định thay Owner.
KHO_DANG_CHAY = (os.environ.get(BIEN_KHAI_KHO) or "").strip().lower() or None

# ---------------------------------------------------------------------------------------------
# G22 — KHAI KHO CHO MỘT MÔI TRƯỜNG KIỂM THỬ CÔ LẬP (dispatch `g22-a1-cauhinh`)
# ---------------------------------------------------------------------------------------------
# `KHO_DANG_CHAY` ở trên là chỗ KHAI CHÍNH THỨC của người triển khai, và nó chỉ đọc MỘT LẦN lúc
# nạp mô-đun. Một bộ thử có ba đường khai, cả ba đi qua CÙNG một bảng biến thể dưới đây:
#   · `VIP_KHO_DANG_CHAY=sqlite` trong môi trường shell của lượt chạy;
#   · `os.environ[BIEN_KHAI_KHO] = "sqlite"` trước khi chạy tiến trình con (`migrate` đọc lại
#     biến môi trường ở MỖI lượt gọi — xem `migrate.kho_dang_chay()`);
#   · `khai_kho_kiem_thu()` — một dòng, kèm CHỐT CÔ LẬP (xem hàm).
# Bảng biến thể nằm ở ĐÂY chứ không ở `migrate.py`: chuẩn hoá cấu hình thuộc về cấu hình.
KHO_DANG_CHAY_BIEN_THE = {
    "sqlite": KHO_SQLITE,
    "sqlite3": KHO_SQLITE,
    "postgres": KHO_POSTGRESQL,
    "postgresql": KHO_POSTGRESQL,
    "pg": KHO_POSTGRESQL,
    "psql": KHO_POSTGRESQL,
}


def chuan_hoa_kho(gia_tri):
    """`'  SQLite  '` ⇒ `'sqlite'` · `'pg'` ⇒ `'postgresql'` · chưa khai HOẶC giá trị lạ ⇒ `None`.

    Trả `None` cho `None`/chuỗi rỗng (CHƯA KHAI) và cho giá trị LẠ; người gọi phân biệt hai thứ
    đó bằng chính giá trị thô. Hàm này KHÔNG ném: nó là phép chuẩn hoá thuần, còn quyết định
    "giá trị lạ thì làm gì" thuộc về chốt gọi nó — `migrate._chuan_hoa_kho()` TỪ CHỐI kèm
    nguyên văn giá trị sai, và `khai_kho_kiem_thu()` TỪ CHỐI kèm hướng dẫn sửa.
    """
    if gia_tri is None:
        return None
    v = str(gia_tri).strip().lower()
    if not v:
        return None
    return KHO_DANG_CHAY_BIEN_THE.get(v)


def khai_kho_kiem_thu(gia_tri=KHO_SQLITE):
    """KHAI kho cho MỘT MÔI TRƯỜNG KIỂM THỬ CÔ LẬP. Trả giá trị đã chuẩn hoá (`'sqlite'`).

    VÌ SAO CẦN HÀM NÀY: mỗi bộ thử gọi `migrate.chay()`/`sao_luu()` đều phải khai kho, và một
    dòng `os.environ[...] = "sqlite"` rải khắp các bộ thử là nhiều chỗ có thể viết nhầm — tệ
    nhất là viết vào môi trường của một tiến trình đang dùng DỮ LIỆU THẬT. Hàm này gom việc
    khai về một chỗ, kèm HAI CHỐT CẤU TRÚC (không phải phép đoán):

      (1) `VIP_HUB_DATA` phải được ĐẶT TƯỜNG MINH. Không đặt nghĩa là thư mục dữ liệu mặc định
          của ứng dụng (`app/du-lieu`) — nơi CSDL nghiệp vụ thật nằm.
      (2) Đường dữ liệu KHÔNG được nằm trong CÂY REPO và KHÔNG được là volume `/du-lieu` của
          container — hai vùng đó là dữ liệu thật hoặc theo thiết kế triển khai.

    Từ chối bằng `SystemExit` (mã thoát 1, thông báo đọc được) và KHÔNG đặt biến môi trường:
    một lượt khai hỏng phải không để lại tác dụng phụ nào. Đây là đường khai của BỘ THỬ, KHÔNG
    phải đường chuyển production sang SQLite: mọi giá trị khác `sqlite` đều bị từ chối, và
    quyết định `OWNER_ACTIONS C4` / `D-8` (PostgreSQL) KHÔNG nằm trong hàm này.
    """
    v = str(gia_tri if gia_tri is not None else "").strip().lower()
    kho = chuan_hoa_kho(v)
    if kho is None:
        raise SystemExit(
            "[cau_hinh] TỪ CHỐI: khai báo kho cho môi trường kiểm thử không nhận ra: %r.\n"
            "          Nhận 'sqlite' (hoặc 'sqlite3')." % (gia_tri,))
    if kho != KHO_SQLITE:
        raise SystemExit(
            "[cau_hinh] TỪ CHỐI: hàm này CHỈ dành cho môi trường kiểm thử dùng SQLite.\n"
            "          Khai %r không mở được nhánh PostgreSQL: `app/csdl.py` thuần SQLite và\n"
            "          `sao_luu()` KHÔNG CÓ nhánh PostgreSQL (xem docs/G22_SAOLUU.md)."
            % (kho,))
    duong = os.environ.get("VIP_HUB_DATA")
    if not duong:
        raise SystemExit(
            "[cau_hinh] TỪ CHỐI: chưa đặt VIP_HUB_DATA nên thư mục dữ liệu là mặc định của\n"
            "          ứng dụng (%s) — đó là CSDL nghiệp vụ, KHÔNG phải nền kiểm thử cô lập.\n"
            "          Đặt VIP_HUB_DATA vào thư mục TẠM rồi gọi lại." % DUONG_DAN_CSDL)
    that = os.path.realpath(os.path.expanduser(duong))
    goc = os.path.realpath(THU_MUC_GOC)
    if that == goc or that.startswith(goc + os.sep):
        raise SystemExit(
            "[cau_hinh] TỪ CHỐI: VIP_HUB_DATA trỏ vào CÂY REPO (%s) — không phải nền kiểm thử\n"
            "          cô lập. Dùng thư mục TẠM (tempfile.mkdtemp)." % that)
    if that == "/du-lieu" or that.startswith("/du-lieu" + os.sep):
        raise SystemExit(
            "[cau_hinh] TỪ CHỐI: VIP_HUB_DATA trỏ vào volume triển khai `/du-lieu` — đó là dữ\n"
            "          liệu thật, không phải nền kiểm thử.")
    os.environ[BIEN_KHAI_KHO] = kho
    globals()["KHO_DANG_CHAY"] = kho
    return kho

PHIEN_SONG_GIO = 12            # phiên đăng nhập sống 12 giờ
KHOA_SAU_SO_LAN_SAI = 5        # sai mật khẩu 5 lần liên tiếp → khóa TẠM
# Khóa TẠM, không khóa vĩnh viễn: khóa vĩnh viễn bằng mật khẩu sai là đường cho người lạ
# vô hiệu hóa tài khoản bất kỳ (AG-07 QA, ca q06 — 5 yêu cầu vô danh là khóa chết một tài khoản).
# Khóa vĩnh viễn chỉ do QUẢN TRỊ đặt (users.trang_thai='khoa').
KHOA_TAM_PHUT = 15
PBKDF2_VONG = 200_000
# Provider reset mật khẩu GIẢ LẬP: trả token thẳng qua API để kiểm thử luồng khi chưa có SMTP.
# MẶC ĐỊNH TẮT. Bật là lỗ hổng chiếm tài khoản: người VÔ DANH gọi /auth/quen-mat-khau cho bất kỳ
# tên đăng nhập nào sẽ nhận token hợp lệ rồi đặt lại mật khẩu — chiếm được cả PLATFORM_OWNER
# trong 3 yêu cầu HTTP (AG-07 QA chứng minh được thật ngày 14/10/2026, ca q01b).
# Chỉ bật có chủ đích khi chạy bộ thử: VIP_HUB_RESET_TOKEN=1.
HIEN_TOKEN_RESET = os.environ.get("VIP_HUB_RESET_TOKEN", "0") == "1"

VAI_TRO_PLATFORM = ("PLATFORM_OWNER", "PLATFORM_ADMIN")
VAI_TRO_TENANT = ("TENANT_OWNER", "TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER")
VAI_TRO_HOP_LE = VAI_TRO_PLATFORM + VAI_TRO_TENANT

# Thứ hạng trạng thái giao vận — chống out-of-order (kế thừa G01)
HANG_TRANG_THAI_GIAO = {
    "cho_lay": 1, "lay_hang": 2, "dang_giao": 3,
    "giao_that_bai": 4, "giao_thanh_cong": 5, "hoan_hang": 6,
}

# Gói dịch vụ mặc định (G10) — hạn mức đo và chặn từ backend
GOI_MAC_DINH = [
    {"id": "free", "ten": "Miễn phí", "gia_thang": 0,
     "han_muc_don_thang": 50, "han_muc_ai_thang": 20, "so_nhan_vien": 2, "so_tai_khoan_hang": 1},
    {"id": "basic", "ten": "Cơ bản", "gia_thang": 299000,
     "han_muc_don_thang": 1000, "han_muc_ai_thang": 500, "so_nhan_vien": 5, "so_tai_khoan_hang": 3},
    {"id": "pro", "ten": "Chuyên nghiệp", "gia_thang": 999000,
     "han_muc_don_thang": 10000, "han_muc_ai_thang": 5000, "so_nhan_vien": 20, "so_tai_khoan_hang": 10},
]

WEBHOOK_SO_LAN_THU = 3
WEBHOOK_BACKOFF_GOC = float(os.environ.get("VIP_HUB_BACKOFF", "0.5"))


# ============================================================================
# G16 — J&T: MÔI TRƯỜNG và CREDENTIALS   (AG-00 sở hữu; agent KHÔNG tự đổi — §38/§39)
# ============================================================================
# Vì sao để ở đây chứ không ở `adapter_jt.py`: "đang chạy ở môi trường nào" và "được phép gọi tới
# đâu" là quyết định của NGƯỜI VẬN HÀNH, không phải của mã adapter. Để trong adapter thì mỗi
# adapter tự trả lời một kiểu, và không có chỗ nào để CHẶN.
JT_MOCK = "mock"
JT_SANDBOX = "sandbox"
JT_PRODUCTION = "production"
JT_MOI_TRUONG_HOP_LE = (JT_MOCK, JT_SANDBOX, JT_PRODUCTION)

# MẶC ĐỊNH LÀ MOCK. Không đặt biến môi trường nào thì hệ KHÔNG chạm mạng.
JT_MOI_TRUONG = os.environ.get("VIP_JT_MOI_TRUONG", JT_MOCK).strip().lower()

# Tên 4 trường credentials — CHỈ TÊN, KHÔNG BAO GIỜ GIÁ TRỊ.
# Hai lớp, hai nguồn cấp (docs/G09_CREDENTIALS_CHECKLIST.md):
JT_TRUONG_NEN_TANG = ("apiAccount", "privateKey")     # J&T Open Platform (Console)
JT_TRUONG_BUU_CUC = ("customerCode", "password")      # bưu cục hợp tác J&T
JT_TRUONG_CREDENTIALS = JT_TRUONG_NEN_TANG + JT_TRUONG_BUU_CUC

# Hết giờ gọi hãng. Tách "kết nối" khỏi "đọc": kết nối chậm là chuyện mạng, đọc chậm là chuyện
# hãng đang xử lý. Gộp làm một con số thì lúc có sự cố không phân biệt được hai nguyên nhân.
JT_HET_GIO_KET_NOI = float(os.environ.get("VIP_JT_TIMEOUT_KET_NOI", "5"))
JT_HET_GIO_DOC = float(os.environ.get("VIP_JT_TIMEOUT_DOC", "15"))

# CỔNG GỌI HÃNG — MẶC ĐỊNH ĐÓNG, và CỐ Ý KHÔNG đọc từ biến môi trường.
# `V-G09-01` (gọi API hãng thật, kể cả sandbox) và `V-13906-05` (credentials sandbox) CHƯA CẤP.
# Lý do không cho đọc từ env: một biến môi trường bật được là một biến môi trường bật NHẦM được,
# và nó nằm trong môi trường tiến trình — thứ `docker inspect` đọc ra được. Muốn mở thì phải
# SỬA MÃ và có phiếu duyệt của anh Thành; đó là chủ ý, không phải thiếu sót.
JT_CHO_PHEP_SANDBOX = False
JT_CHO_PHEP_PRODUCTION = False


def jt_kiem_moi_truong(moi_truong=None):
    """Cổng môi trường J&T. Trả `(cho_qua: bool, ly_do: str)`.

    MẶC ĐỊNH CHẶN `sandbox` và `production`. Lý do trả về là câu ĐỌC ĐƯỢC, không phải mã lỗi:
    người vận hành phải biết CHÍNH XÁC còn thiếu giấy phép nào, chứ không phải đoán.
    """
    mt = (moi_truong if moi_truong is not None else JT_MOI_TRUONG) or ""
    mt = str(mt).strip().lower()
    if mt == JT_MOCK:
        return True, "mock: không chạm mạng, không cần credentials"
    if mt not in JT_MOI_TRUONG_HOP_LE:
        return False, (f"môi trường lạ {mt!r}; chỉ nhận {JT_MOI_TRUONG_HOP_LE}")
    if mt == JT_SANDBOX and not JT_CHO_PHEP_SANDBOX:
        return False, ("sandbox CHƯA ĐƯỢC CẤP QUYỀN — cần V-G09-01 (gọi API hãng thật, kể cả "
                       "sandbox) và V-13906-05 (credentials sandbox). "
                       "Xem docs/SHARED_CONTRACTS.md §25 và §37.")
    if mt == JT_PRODUCTION and not JT_CHO_PHEP_PRODUCTION:
        return False, ("production KHÔNG ĐƯỢC PHÉP — cần anh Thành duyệt riêng. "
                       "Xem docs/SHARED_CONTRACTS.md §37.")
    return True, f"{mt}: đã được cấp quyền"


def jt_thieu_truong(cred):
    """Tên các trường credentials còn THIẾU. CHỈ TRẢ TÊN — KHÔNG BAO GIỜ TRẢ GIÁ TRỊ.

    Vì sao trả tên chứ không trả dict: câu "còn thiếu gì" là thứ hay bị đưa vào log và màn hình.
    Trả về ĐÚNG tên trường thì không còn đường nào để một giá trị lọt ra theo.
    """
    cred = cred or {}
    return [t for t in JT_TRUONG_CREDENTIALS if not str(cred.get(t) or "").strip()]
