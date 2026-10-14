# Bộ thử TÍCH HỢP của AG-00 — canh những thứ CẤU TRÚC mà từng agent lẻ không thấy được.
# Mỗi ca ở đây sinh ra từ một cảnh báo thật của agent trong đợt 14/10/2026.
import os
import re
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_DA = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)
os.environ.setdefault("VIP_HUB_DATA", tempfile.mkdtemp(prefix="vip-hub-tichhop-"))

import csdl      # noqa: E402
import bao_mat   # noqa: E402


def doc(duong):
    """Đọc file và ĐÓNG hẳn — tránh ResourceWarning làm bẩn kết quả chạy."""
    with open(duong, encoding="utf-8") as f:
        return f.read()


class CanhCauTruc(unittest.TestCase):

    def test_01_moi_cot_ma_hoa_deu_duoc_xoay_khoa_phu(self):
        """AG-01 cảnh báo: `xoay_khoa()` chỉ phủ `carrier_accounts`. Thêm bảng có cột mã hóa
        mà quên thêm vào hàm xoay khóa thì bản mã đó sẽ KHÔNG BAO GIỜ xoay được — hỏng im lặng.
        Ca này quét schema, bắt mọi cột `*_ma_hoa` và đòi chúng nằm trong danh sách đã phủ."""
        cot_ma_hoa = set(re.findall(r"^\s*(\w*_ma_hoa)\s", csdl.SCHEMA, re.M))
        nguon = doc(os.path.join(GOC_APP, "bao_mat.py"))
        than = nguon[nguon.index("def ma_hoa_lai_carrier_accounts"):] if \
            "def ma_hoa_lai_carrier_accounts" in nguon else ""
        self.assertTrue(than, "không tìm thấy hàm mã hóa lại — xoay khóa đã biến mất?")
        than = than[:than.index("\ndef ", 5)] if "\ndef " in than[5:] else than
        thieu = [c for c in cot_ma_hoa if c not in than]
        self.assertEqual(thieu, [], f"Cột mã hóa KHÔNG được xoay khóa phủ: {thieu}. "
                                    "Thêm vào bao_mat.ma_hoa_lai_carrier_accounts() rồi thêm ca thử.")

    def test_02_ma_san_pham_khong_goi_ma_hoa_tran(self):
        """AG-01 cảnh báo: `ma_hoa()`/`giai_ma()` trần sinh bản mã KHÔNG mang key_id (không xoay
        khóa được) và KHÔNG có AAD (chép chéo tenant được). Chỉ `migrate.py` được dùng chúng,
        vì nó phải đọc định dạng lịch sử. Mã sản phẩm khác phải dùng 4 hàm contract."""
        duoc_phep = {"migrate.py", "bao_mat.py", "secret_provider.py"}
        vi_pham = []
        for ten in sorted(os.listdir(GOC_APP)):
            if not ten.endswith(".py") or ten in duoc_phep:
                continue
            noi_dung = doc(os.path.join(GOC_APP, ten))
            for so, dong in enumerate(noi_dung.splitlines(), 1):
                if re.search(r"bao_mat\.(ma_hoa|giai_ma)\s*\(", dong) and \
                   not re.search(r"bao_mat\.(ma_hoa|giai_ma)_(cred|wh)\s*\(", dong):
                    vi_pham.append(f"{ten}:{so}")
        self.assertEqual(vi_pham, [], "Gọi mã hóa trần ngoài migrate — dùng ma_hoa_cred/ma_hoa_wh: "
                                      + ", ".join(vi_pham))

    def test_03_chong_trung_webhook_do_CSDL_canh_khong_phai_if(self):
        """AG-02 cảnh báo: chống trùng webhook nên do ràng buộc CSDL cưỡng chế, không phải `if`.
        Ca này đòi UNIQUE thật trong schema."""
        self.assertRegex(csdl.SCHEMA, r"UNIQUE\s*\(\s*carrier_account_id\s*,\s*event_id\s*\)",
                         "wh_su_kien thiếu UNIQUE(carrier_account_id, event_id)")
        self.assertRegex(csdl.SCHEMA, r"UNIQUE\s*\(\s*tenant_id\s*,\s*idem_key\s*\)",
                         "don_hang thiếu UNIQUE(tenant_id, idem_key) — idempotency mất cưỡng chế")

    def test_04_khoa_ma_hoa_khong_duoc_vao_git(self):
        """Khóa lọt vào git là mất sạch secret. Canh bằng chính git, không bằng niềm tin."""
        import subprocess
        for duong in ("app/du-lieu/khoa", "app/du-lieu/khoa-noi-bo.key", "app/du-lieu/hub.db"):
            kq = subprocess.run(["git", "check-ignore", "-q", duong], cwd=GOC_DA)
            self.assertEqual(kq.returncode, 0, f"{duong} KHÔNG bị gitignore — nguy cơ lộ secret")
        theo_doi = subprocess.run(["git", "ls-files", "app/du-lieu"], cwd=GOC_DA,
                                  capture_output=True, text=True).stdout.strip()
        self.assertEqual(theo_doi, "", f"git đang theo dõi file trong app/du-lieu: {theo_doi}")

    def test_05_adapter_khong_co_duong_goi_mang_nao(self):
        """Mọi adapter còn ở chế độ MOCK: không file nào được nhập thư viện gọi mạng."""
        cam = ("requests", "httpx", "urllib.request", "http.client", "socket")
        for ten in [f for f in os.listdir(GOC_APP) if f.startswith("adapter")]:
            noi_dung = doc(os.path.join(GOC_APP, ten))
            for tu in cam:
                self.assertNotIn(tu, noi_dung, f"{ten} có thể gọi mạng thật qua '{tu}'")

    def test_06_live_bi_khoa_o_moi_adapter(self):
        import adapter, adapter_jt, adapter_vtp  # noqa: F401
        for ma, lop in adapter._DANG_KY.items():
            self.assertFalse(lop.CHO_PHEP_LIVE, f"{ma} đã MỞ đường LIVE — Owner chưa duyệt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
