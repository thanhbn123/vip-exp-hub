# SecretProvider — nơi DUY NHẤT giữ và cấp khóa mã hóa (master key) cho hệ.
#
# Vì sao có file này: trước đây khóa AES nằm cố định ở một file duy nhất
# (`app/du-lieu/khoa-noi-bo.key`) và bản mã KHÔNG mang định danh khóa (key_id). Hệ quả đo được:
# đổi khóa là mọi bản mã cũ thành rác, nên thực tế KHÔNG xoay khóa được. Lớp này tách việc
# "lấy khóa ở đâu" ra khỏi việc "mã hóa thế nào", để sau này chuyển sang KMS (Key Management
# Service — dịch vụ quản lý khóa của nhà cung cấp hạ tầng) mà không phải sửa `bao_mat.py`.
#
# Luật cứng:
#   - Khóa KHÔNG BAO GIỜ nằm trong CSDL (ai đọc được CSDL là đọc được mọi secret).
#   - Khóa KHÔNG BAO GIỜ vào git (`.gitignore` đã chặn cả thư mục `app/du-lieu/`).
#   - Khóa cũ GIỮ LẠI sau khi xoay — còn bản mã nào chưa chuyển thì còn phải giải được.
#   - Thiếu khóa thì ném lỗi, KHÔNG tự sinh khóa khác rồi coi như xong (sẽ mất dữ liệu im lặng).
import os
import re
import secrets
from datetime import datetime

import cau_hinh

# Thư mục khóa: mỗi khóa một file 32 byte (AES-256), quyền 0600, tên file = "<key_id>.key".
THU_MUC_KHOA = os.path.join(cau_hinh.THU_MUC_DU_LIEU, "khoa")
# File trỏ khóa hiện hành (nội dung = key_id). KHÔNG mang đuôi .key để không bị tính là khóa.
TEN_FILE_TRO = "hien-hanh"
DUOI_KHOA = ".key"
DAI_KHOA = 32                     # AES-256
KEY_ID_CU = "goc"                 # key_id gán cho khóa cũ `khoa-noi-bo.key` khi di cư

# key_id phải an toàn cho tên file VÀ cho định dạng bản mã `v3$<key_id>$<nonce>$<ct>`:
# không có '$', không có dấu phân cách đường dẫn, không rỗng.
MAU_KEY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,62}$")


class LoiKhoa(Exception):
    """Lỗi liên quan tới khóa: thiếu khóa, khóa sai độ dài, key_id không hợp lệ."""


def kiem_key_id(key_id: str) -> str:
    if not isinstance(key_id, str) or not MAU_KEY_ID.match(key_id):
        raise LoiKhoa(f"key_id không hợp lệ: {key_id!r} (cho phép a-z 0-9 . _ -, tối đa 63 ký tự)")
    return key_id


class SecretProvider:
    """Lớp nền. Mọi nguồn khóa (file nội bộ, KMS, HSM...) phải cài đủ ba hàm này."""

    def lay_khoa(self, key_id: str) -> bytes:
        """Khóa 32 byte theo key_id. Không có thì ném LoiKhoa — KHÔNG trả khóa khác."""
        raise NotImplementedError

    def khoa_hien_hanh(self):
        """Trả (key_id, khóa_32_byte) của khóa đang dùng để mã hóa MỚI."""
        raise NotImplementedError

    def danh_sach_key_id(self):
        """Mọi key_id còn giữ (gồm khóa cũ, vì bản mã cũ còn cần)."""
        raise NotImplementedError

    # --- phục vụ xoay khóa; nguồn nào không xoay được thì cứ để NotImplementedError ---
    def tao_khoa_moi(self) -> str:
        """Sinh khóa mới, trả key_id. KHÔNG tự đặt làm hiện hành."""
        raise NotImplementedError

    def dat_khoa_hien_hanh(self, key_id: str) -> str:
        """Đặt khóa hiện hành. Khóa cũ vẫn giữ."""
        raise NotImplementedError


class LocalSecretProvider(SecretProvider):
    """Khóa nằm trong file trên đĩa — đủ cho local-first, KHÔNG đủ cho máy chủ thật (xem KMS)."""

    def __init__(self, thu_muc=None, duong_khoa_cu=None):
        self.thu_muc = thu_muc or THU_MUC_KHOA
        # Khóa cũ (một file, không key_id) — di cư thành KEY_ID_CU để bản mã v1/v2 còn đọc được.
        self.duong_khoa_cu = duong_khoa_cu or cau_hinh.DUONG_DAN_KHOA
        self._cache = {}          # key_id -> bytes (nội dung khóa bất biến nên cache được)

    # ----- đĩa -----
    def _duong(self, key_id):
        return os.path.join(self.thu_muc, kiem_key_id(key_id) + DUOI_KHOA)

    def _duong_tro(self):
        return os.path.join(self.thu_muc, TEN_FILE_TRO)

    def _ghi_khoa(self, key_id, khoa: bytes):
        if len(khoa) != DAI_KHOA:
            raise LoiKhoa(f"khóa phải đúng {DAI_KHOA} byte cho AES-256, đang có {len(khoa)}")
        os.makedirs(self.thu_muc, exist_ok=True)
        os.chmod(self.thu_muc, 0o700)
        duong = self._duong(key_id)
        # Ghi file tạm cùng thư mục rồi đổi tên: đổi tên là thao tác nguyên tử, hỏng giữa đường
        # thì file khóa thật còn nguyên (CLAUDE.md §16.3).
        tam = duong + ".tam-" + secrets.token_hex(4)
        with open(tam, "wb") as f:
            f.write(khoa)
        os.chmod(tam, 0o600)      # đặt quyền TRƯỚC khi đổi tên, để không có khe hở 0644
        os.replace(tam, duong)
        self._cache[key_id] = khoa
        return key_id

    def _di_cu_khoa_cu(self):
        """Đưa khóa cũ `khoa-noi-bo.key` vào thư mục khóa dưới key_id 'goc'.

        BẮT BUỘC chép chứ không di chuyển: bản mã định dạng v1/v2 không mang key_id nên
        `bao_mat` vẫn phải đọc đúng file cũ ở đúng chỗ cũ. Xóa file cũ = mất dữ liệu đã mã hóa.
        """
        if os.path.exists(self._duong(KEY_ID_CU)):
            return KEY_ID_CU
        if not os.path.exists(self.duong_khoa_cu):
            # Máy mới chưa có khóa nào: tạo luôn file khóa cũ rồi di cư. Làm vậy để
            # khóa 'goc' và file `khoa-noi-bo.key` LUÔN là cùng một khóa — nếu để hai
            # đường tự sinh khóa riêng thì bản mã v2 (không mang key_id) và bản mã v3
            # sẽ nằm dưới hai khóa khác nhau, và không có gì báo lỗi.
            os.makedirs(os.path.dirname(self.duong_khoa_cu), exist_ok=True)
            tam = self.duong_khoa_cu + ".tam-" + secrets.token_hex(4)
            with open(tam, "wb") as f:
                f.write(secrets.token_bytes(DAI_KHOA))
            os.chmod(tam, 0o600)
            os.replace(tam, self.duong_khoa_cu)
        with open(self.duong_khoa_cu, "rb") as f:
            khoa = f.read()
        if len(khoa) != DAI_KHOA:
            raise LoiKhoa(f"khóa cũ {self.duong_khoa_cu} dài {len(khoa)} byte, cần {DAI_KHOA}")
        return self._ghi_khoa(KEY_ID_CU, khoa)

    def _dam_bao_co_khoa(self):
        """Đảm bảo có ít nhất một khóa và một con trỏ hiện hành. Idempotent."""
        os.makedirs(self.thu_muc, exist_ok=True)
        if not self.danh_sach_key_id():
            self._di_cu_khoa_cu()
        if not os.path.exists(self._duong_tro()):
            ds = self.danh_sach_key_id()
            # Mất con trỏ thì chọn khóa cũ 'goc' nếu còn, không thì khóa mới nhất theo tên
            # (tên mang mốc thời gian). CỐ Ý không sinh khóa mới ở đây: mất con trỏ không
            # phải là mất khóa, và thêm khóa thừa chỉ làm rối đường xoay khóa.
            self.dat_khoa_hien_hanh(KEY_ID_CU if KEY_ID_CU in ds else max(ds))

    @staticmethod
    def _key_id_moi():
        return "k-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)

    # ----- giao diện SecretProvider -----
    def lay_khoa(self, key_id: str) -> bytes:
        kiem_key_id(key_id)
        if key_id in self._cache:
            return self._cache[key_id]
        duong = self._duong(key_id)
        if not os.path.exists(duong):
            # Khóa biến mất là sự cố phải NGƯỜI xử: không sinh khóa thay thế, vì làm vậy
            # chỉ biến "giải mã hỏng" thành "dữ liệu mất im lặng".
            raise LoiKhoa(f"không thấy khóa '{key_id}' trong {self.thu_muc} — bản mã dùng khóa này"
                          " sẽ KHÔNG giải được. Khôi phục khóa từ bản sao lưu, đừng sinh khóa mới.")
        with open(duong, "rb") as f:
            khoa = f.read()
        if len(khoa) != DAI_KHOA:
            raise LoiKhoa(f"khóa '{key_id}' dài {len(khoa)} byte, cần {DAI_KHOA}")
        self._cache[key_id] = khoa
        return khoa

    def khoa_hien_hanh(self):
        self._dam_bao_co_khoa()
        with open(self._duong_tro(), encoding="utf-8") as f:
            key_id = f.read().strip()
        return kiem_key_id(key_id), self.lay_khoa(key_id)

    def danh_sach_key_id(self):
        if not os.path.isdir(self.thu_muc):
            return []
        return sorted(t[:-len(DUOI_KHOA)] for t in os.listdir(self.thu_muc) if t.endswith(DUOI_KHOA))

    def tao_khoa_moi(self) -> str:
        self._dam_bao_co_khoa()
        key_id = self._key_id_moi()
        while os.path.exists(self._duong(key_id)):      # cùng giây thì đổi phần ngẫu nhiên
            key_id = self._key_id_moi()
        return self._ghi_khoa(key_id, secrets.token_bytes(DAI_KHOA))

    def dat_khoa_hien_hanh(self, key_id: str) -> str:
        kiem_key_id(key_id)
        if not os.path.exists(self._duong(key_id)):
            raise LoiKhoa(f"không thấy khóa '{key_id}' — không đặt làm hiện hành")
        tam = self._duong_tro() + ".tam-" + secrets.token_hex(4)
        with open(tam, "w", encoding="utf-8") as f:
            f.write(key_id)
        os.chmod(tam, 0o600)
        os.replace(tam, self._duong_tro())
        return key_id


class KMSSecretProvider(SecretProvider):
    """CHỈ LÀ GIAO DIỆN — chưa triển khai, và CỐ Ý chưa triển khai.

    Khi lên máy chủ thật thì khóa nên nằm trong KMS/HSM chứ không nằm trong file trên đĩa.
    Nhưng viết sẵn một bản KMS "trông như thật" mà chưa đo được với dịch vụ thật là đúng kiểu
    hỏng im lặng (CLAUDE.md §12.2): mọi hàm đều chạy, không ai biết nó chưa bao giờ nối được
    tới KMS nào. Nên ở đây mỗi hàm ném NotImplementedError kèm việc cần làm.

    Khi triển khai thật, phải giữ đúng ba điều:
      1. key_id của hệ phải ánh xạ 1-1 sang định danh khóa trong KMS; bản mã chỉ mang key_id
         của hệ, KHÔNG mang ARN/URI của nhà cung cấp (đổi nhà cung cấp là đổi hết bản mã).
      2. Khóa cũ không được xóa khỏi KMS khi xoay — chỉ đánh dấu thôi mã hóa mới.
      3. Nên dùng envelope encryption: KMS giữ khóa gốc, hệ xin khóa dữ liệu theo từng lượt;
         khi đó `lay_khoa` phải có cache có thời hạn, vì mỗi lượt gọi KMS là một lượt mạng.
    """

    def __init__(self, cau_hinh_kms=None):
        self.cau_hinh_kms = cau_hinh_kms

    def _chua_lam(self, ten):
        raise NotImplementedError(
            f"KMSSecretProvider.{ten}() chưa triển khai. Hệ đang dùng LocalSecretProvider "
            "(khóa trong file 0600, ngoài git). Muốn dùng KMS thì phải: chọn nhà cung cấp, "
            "nối SDK, ánh xạ key_id ↔ khóa KMS, và đo thật một lượt mã hóa/giải mã trước khi bật."
        )

    def lay_khoa(self, key_id: str) -> bytes:
        self._chua_lam("lay_khoa")

    def khoa_hien_hanh(self):
        self._chua_lam("khoa_hien_hanh")

    def danh_sach_key_id(self):
        self._chua_lam("danh_sach_key_id")

    def tao_khoa_moi(self) -> str:
        self._chua_lam("tao_khoa_moi")

    def dat_khoa_hien_hanh(self, key_id: str) -> str:
        self._chua_lam("dat_khoa_hien_hanh")


# ====== Nhà cung cấp dùng chung cho cả tiến trình ======
_nha_cung_cap = None


def nha_cung_cap() -> SecretProvider:
    global _nha_cung_cap
    if _nha_cung_cap is None:
        _nha_cung_cap = LocalSecretProvider()
    return _nha_cung_cap


def dat_nha_cung_cap(p: SecretProvider):
    """Đổi nguồn khóa (dùng cho bộ thử, và cho ngày chuyển sang KMS). None = về mặc định."""
    global _nha_cung_cap
    _nha_cung_cap = p
    return p
