"""Hồi quy: MỌI chốt hạn mức phải NGUYÊN TỬ, không chỉ chốt số đơn.

Vì sao có bộ thử này: đợt 2 đã vá `billing.kiem_va_tang_don` từ đọc-rồi-ghi sang nguyên tử
(lỗ hổng r35), nhưng **bỏ qua bước 4 của §12.2** — *sửa xong hỏi: cấu trúc này còn hỏng kiểu đó
ở đâu nữa?* Bỏ bước đó nên ba chốt hạn mức bên cạnh vẫn nguyên khuôn cũ, và AG-02 tìm ra ở
đợt 3. Bộ thử này canh CẢ BỐN chốt, để lần sau thêm chốt thứ năm thì có chỗ bắt.

Khuôn đúng, dùng chung cho mọi chốt: **đưa trần vào `WHERE` của MỘT câu ghi** rồi xét
`rowcount`. Với bộ đếm là `UPDATE ... WHERE dem+1 <= tran`; với bảng đếm dòng là
`INSERT ... SELECT ... WHERE (SELECT COUNT(*) ...) < tran`. Cả hai để CSDL tự so, nên không có
khe hở nào giữa lúc đọc và lúc ghi.

PHẠM VI (§12.1 luật 3): đo trên SQLite WAL, MỘT tiến trình, nhiều luồng. KHÔNG phủ nhiều tiến
trình và KHÔNG phủ PostgreSQL — ở đó hành vi khoá khác, phải đo lại.
"""
import os
import sys
import tempfile
import threading
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
os.environ.setdefault("VIP_HUB_DATA", tempfile.mkdtemp(prefix="veh-hmnt-"))

import bao_mat          # noqa: E402
import billing          # noqa: E402
import cau_hinh         # noqa: E402
import csdl             # noqa: E402
import migrate          # noqa: E402
import quyen            # noqa: E402

# ── Y1 · TỰ KHAI KHO ĐANG CHẠY (cổng fail-closed của G22) ─────────────────────────────────────
# `migrate.chay()` gọi TRỰC TIẾP trong tiến trình này (`setUpClass`) — không có tiến trình con
# nào chạy `migrate`. Bộ thử tự khai bằng giao diện chung `cau_hinh.khai_kho_kiem_thu()` —
# KHÔNG dựa vào việc người chạy nhớ `export VIP_KHO_DANG_CHAY`: một bộ chỉ xanh khi người chạy
# nhớ khai là một bộ GIỎ. `VIP_HUB_DATA` đã trỏ thư mục TẠM ở trên, nên hai chốt cô lập của hàm
# khai đều thoả.
cau_hinh.khai_kho_kiem_thu()

LUONG = 12


def _tenant(goi="free"):
    return csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,?,?)",
                    (os.urandom(5).hex(), "T", goi, csdl.bay_gio())).lastrowid


def _dong_thoi(viec, so_luong=LUONG):
    """Cho `so_luong` luồng cùng chạy `viec` sau một hàng rào. Trả số luồng KHÔNG nổ."""
    rao = threading.Barrier(so_luong)
    qua = []

    def chay(i):
        try:
            rao.wait(timeout=10)
            viec(i)
            qua.append(i)
        except Exception:
            pass

    ts = [threading.Thread(target=chay, args=(i,)) for i in range(so_luong)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=20)
    return len(qua)


class ThuHanMucNguyenTu(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        migrate.chay(im_lang=True)
        quyen.seed()

    # ---------- chốt 1: số đơn (đã vá ở r35 — canh để không thoái hoá) ----------
    def test_a1_so_don_nguyen_tu(self):
        tid = _tenant()
        tran = billing.goi_cua_tenant(tid)["han_muc_don_thang"]
        csdl.ghi("INSERT INTO usage_thang (tenant_id,thang,so_don,so_ai) VALUES (?,?,?,0)",
                 (tid, csdl.thang_nay(), tran - 1))          # còn ĐÚNG 1 suất
        qua = _dong_thoi(lambda i: billing.kiem_va_tang_don(tid))
        cuoi = csdl.mot("SELECT so_don FROM usage_thang WHERE tenant_id=?", (tid,))["so_don"]
        self.assertEqual(cuoi, tran, f"so_don = {cuoi}, vượt trần {tran}")
        self.assertEqual(qua, 1, f"{qua} luồng qua, phải đúng 1")

    # ---------- chốt 2: lượt AI ----------
    def test_a2_so_ai_nguyen_tu(self):
        """LỖ HỔNG AG-02 tìm ra, AG-00 đo lại: 28/40 lượt vượt trần, cao nhất 30 trên trần 20."""
        tid = _tenant()
        tran = billing.goi_cua_tenant(tid)["han_muc_ai_thang"]
        csdl.ghi("INSERT INTO usage_thang (tenant_id,thang,so_don,so_ai) VALUES (?,?,0,?)",
                 (tid, csdl.thang_nay(), tran - 1))
        qua = _dong_thoi(lambda i: billing.kiem_va_tang_ai(tid))
        cuoi = csdl.mot("SELECT so_ai FROM usage_thang WHERE tenant_id=?", (tid,))["so_ai"]
        self.assertEqual(cuoi, tran, f"so_ai = {cuoi}, vượt trần {tran}")
        self.assertEqual(qua, 1, f"{qua} luồng qua, phải đúng 1")

    # ---------- chốt 3: số tài khoản hãng ----------
    def test_a3_tai_khoan_hang_nguyen_tu(self):
        """LỖ HỔNG NẶNG NHẤT: AG-00 đo được 12/12 luồng qua, 12 tài khoản trên trần 1."""
        tid = _tenant()
        tran = billing.goi_cua_tenant(tid)["so_tai_khoan_hang"]
        cm, duoi = bao_mat.ma_hoa_cred({"u": "1"}, tid, "vtp")

        def them(i):
            wh = f"w{tid}-{i}"
            billing.chen_tai_khoan_hang_co_tran(
                tid, "vtp", f"TK{i}", "mock", cm, duoi, wh,
                bao_mat.ma_hoa_wh("s" * 16, wh))

        qua = _dong_thoi(them)
        cuoi = csdl.mot("SELECT COUNT(*) c FROM carrier_accounts WHERE tenant_id=? AND kich_hoat=1",
                        (tid,))["c"]
        self.assertEqual(cuoi, tran, f"{cuoi} tài khoản hãng, vượt trần {tran}")
        self.assertEqual(qua, 1, f"{qua} luồng qua, phải đúng 1")

    # ---------- chốt 4: số nhân viên ----------
    def test_a4_nhan_vien_nguyen_tu(self):
        """Phép đo ad-hoc KHÔNG tái hiện được chốt này (khoá ghi tình cờ che khe hở) — nhưng
        cấu trúc vẫn là kiểm-rồi-ghi, nên vẫn phải đóng. Ca này canh kết quả, không canh may."""
        tid = _tenant()
        tran = billing.goi_cua_tenant(tid)["so_nhan_vien"]
        for i in range(tran - 1):
            u = csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc,trang_thai)"
                         " VALUES (?,?,?,?,'hoat_dong')",
                         (f"nv{i}-{tid}", "x", "NV", csdl.bay_gio())).lastrowid
            csdl.ghi("INSERT INTO tenant_memberships (user_id,tenant_id,role,tao_luc,trang_thai)"
                     " VALUES (?,?,'TENANT_STAFF',?,'hoat_dong')", (u, tid, csdl.bay_gio()))

        def them(i):
            u = csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc,trang_thai)"
                         " VALUES (?,?,?,?,'hoat_dong')",
                         (f"moi{i}-{tid}", "x", "M", csdl.bay_gio())).lastrowid
            billing.chen_membership_co_tran(tid, u, "TENANT_STAFF", None)

        qua = _dong_thoi(them)
        cuoi = csdl.mot("SELECT COUNT(*) c FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                        " WHERE m.tenant_id=? AND m.trang_thai='hoat_dong'"
                        " AND u.trang_thai='hoat_dong'", (tid,))["c"]
        self.assertEqual(cuoi, tran, f"{cuoi} nhân viên, vượt trần {tran}")
        self.assertEqual(qua, 1, f"{qua} luồng qua, phải đúng 1")

    # ---------- chốt chống thoái hoá: không chốt nào được quay về đọc-rồi-ghi ----------
    def test_b1_moi_chot_han_muc_deu_co_tran_trong_cau_ghi(self):
        """Soát TĨNH. Mọi hàm trong `billing.py` có ghi và có trần phải đưa trần vào câu ghi.

        Giới hạn ghi rõ: soát theo VĂN BẢN mã nguồn, nên một hàm gọi helper ở chỗ khác có thể
        bị báo thiếu — phải xem tay. Nhưng nó bắt được đúng kiểu thoái hoá đã xảy ra thật:
        ai đó thêm chốt thứ năm theo khuôn `đọc rồi raise rồi ghi`.
        """
        import re
        s = open(os.path.join(GOC, "billing.py"), encoding="utf-8").read()
        thieu = []
        for m in re.finditer(r"\ndef (\w+)\(([^)]*)\):\n((?:[ ].*\n|\n)+)", s):
            ten, than = m.group(1), m.group(3)
            co_ghi = bool(re.search(r"(csdl\.ghi|kn\.execute\(\s*[\"']\s*(INSERT|UPDATE))", than))
            co_tran = bool(re.search(r"(han_muc|so_nhan_vien|so_tai_khoan_hang|tran)", than))
            if not (co_ghi and co_tran):
                continue
            # Khuôn đúng: trần nằm TRONG câu ghi (WHERE ... <= ? / < ?) và xét rowcount
            dung = bool(re.search(r"<=\s*\?", than) or re.search(r"<\s*\?", than)) \
                and "rowcount" in than
            if not dung:
                thieu.append(ten)
        self.assertEqual(thieu, [],
                         "chốt hạn mức KHÔNG đưa trần vào câu ghi (khuôn đọc-rồi-ghi đã hỏng "
                         f"thật ở r35 và lại hỏng ở đợt 3): {thieu}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
