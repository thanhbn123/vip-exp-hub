"""Hồi quy: mã trạng thái LẠ của hãng phải (a) KHÔNG đẩy trạng thái, (b) BỊ NÊU RA.

Vì sao có bộ thử này: AG-03 (đợt 3) đọc tài liệu J&T bằng trình duyệt thật và thấy ví dụ trả
lời dùng **một bộ mã thứ hai** — `10` Nhận hàng · `50` Gửi hàng · `92` Hàng đến · `94` Quét
phát hàng · `100` Ký nhận — khác hẳn bộ trong bảng tham số (`103`…`121`). Năm mã đó KHÔNG có
trong `JT_MA`.

Hệ quả THẬT, AG-00 đo lại: một đơn **đã giao** mang mã `100` sẽ **không** về `giao_thanh_cong`.
Nó đứng ở trạng thái cũ cho tới khi có người xử.

Nhưng AG-03 mô tả là *"không báo lỗi gì"* — chỗ đó **nói quá**. AG-00 đo: mã lạ ra
`can_soat=True` + `do_tin_cay='ma_la'`, và cột `can_soat` đã được phơi ra cửa
`GET /api/v2/webhook/su-kien?can_soat=1` từ đợt 2. Nên nó **được nêu ra**, chỉ là không tự
tiến trạng thái. Hai câu đó khác nhau: "mất im lặng" với "đứng chờ người xử, có chỗ tra".

Vì sao KHÔNG thêm mã `100` vào bảng ngay: làm vậy là **đoán nghĩa của bộ mã thứ hai** khi chưa
có văn bản của hãng — đúng thứ `V-13906-04` nói là quyết định của chủ dự án, chưa cấp. Thà đơn
đứng chờ người xử còn hơn hệ tự tuyên bố "đã giao" dựa trên suy đoán, vì tuyên bố đó mở cửa
cho đối soát COD áp tiền theo một dữ kiện chưa chắc.

Bộ thử này khoá CẢ HAI mặt: mã lạ không được tự tiến, VÀ mã lạ không được bị che.
"""
import os
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC)
os.environ.setdefault("VIP_HUB_DATA", tempfile.mkdtemp(prefix="veh-mala-"))

import trang_thai_hang as tt    # noqa: E402

# Năm mã của bộ thứ hai mà AG-03 đọc được trên open.jtexpress.vn ngày 15/10/2026.
# `100` là mã nguy hiểm nhất: nó nghĩa "Ký nhận", tức là ĐÃ GIAO.
BO_MA_THU_HAI = {
    10: "Nhận hàng",
    50: "Gửi hàng",
    92: "Hàng đến",
    94: "Quét phát hàng",
    100: "Ký nhận",          # ← nghĩa là đã giao, nhưng KHÔNG có trong JT_MA
}


class ThuMaLaHang(unittest.TestCase):

    def test_a1_bo_ma_thu_hai_chua_duoc_khai(self):
        """Dữ kiện nền: năm mã đó chưa có trong bảng. Ca này sẽ HỎNG khi ai đó thêm chúng —
        và hỏng ở đây là ĐÚNG, nó buộc người thêm phải đọc hai ca dưới và cập nhật tài liệu."""
        co = sorted(m for m in BO_MA_THU_HAI if m in tt.JT_MA)
        self.assertEqual(
            co, [],
            f"các mã {co} nay ĐÃ có trong JT_MA. Nếu đây là chủ ý (hãng đã trả lời "
            f"V-13906-04) thì cập nhật bộ thử này + docs/JT_CAU_HOI_CHINH_THUC.md. "
            f"Nếu không phải chủ ý thì đó là đoán nghĩa mã của hãng — gỡ ra.")

    def test_a2_ma_la_KHONG_tu_day_trang_thai(self):
        """Mã lạ KHÔNG được tự tiến trạng thái. Đây là chốt chống đoán."""
        for ma, mo_ta in BO_MA_THU_HAI.items():
            qd = tt.quyet_dinh("jt", str(ma), mo_ta)
            self.assertIsNone(
                qd.trang_thai_ap,
                f"mã lạ {ma} ({mo_ta}) tự đẩy trạng thái sang {qd.trang_thai_ap!r} — "
                f"đó là ĐOÁN nghĩa mã của hãng")

    def test_a3_ma_la_PHAI_bi_neu_ra_khong_duoc_che(self):
        """Mã lạ phải bị nêu ra, nếu không thì đơn đứng im mà KHÔNG ai biết — lúc đó mô tả
        'mất im lặng' mới đúng, và đó là thứ phải chặn."""
        for ma, mo_ta in BO_MA_THU_HAI.items():
            qd = tt.quyet_dinh("jt", str(ma), mo_ta)
            self.assertTrue(
                getattr(qd, "can_soat", False),
                f"mã lạ {ma} ({mo_ta}) KHÔNG bật cờ can_soat ⇒ đơn đứng im và không có "
                f"chỗ nào tra ra. Mã lạ phải vào danh sách cần soát.")
            self.assertIn(getattr(qd, "nhan", None), ("NEEDS_REVIEW", "AMBIGUOUS"),
                          f"mã lạ {ma} mang nhãn {getattr(qd, 'nhan', None)!r}")

    def test_a4_co_cho_TRA_RA_su_kien_can_soat(self):
        """Cờ `can_soat` chỉ có nghĩa nếu có đường tra. Đo trên `server.py` THẬT."""
        s = open(os.path.join(GOC, "server.py"), encoding="utf-8").read()
        self.assertIn("s.can_soat", s,
                      "SELECT của /webhook/su-kien không lấy cột can_soat ⇒ cờ bật mà không "
                      "ai xem được")
        self.assertIn('ts.get("can_soat")', s,
                      "không có bộ lọc ?can_soat=1 ⇒ người vận hành phải tự lọc tay giữa "
                      "hàng nghìn sự kiện")

    def test_a5_ma_110_van_la_AMBIGUOUS_co_chu_y(self):
        """`110` KHÁC năm mã trên: nó CÓ trong bảng, và cố ý giữ AMBIGUOUS vì hai nguồn tài
        liệu nói hai nghĩa khác nhau. Đừng lẫn hai ca: `110` là nhập nhằng ĐÃ BIẾT, còn `100`
        là mã CHƯA KHAI."""
        self.assertIn(110, tt.JT_MA, "mã 110 phải CÓ trong bảng (nhập nhằng đã biết)")
        qd = tt.quyet_dinh("jt", "110", "Quét kiện vấn đề")
        self.assertIsNone(qd.trang_thai_ap)
        self.assertEqual(getattr(qd, "nhan", None), "AMBIGUOUS",
                         "110 phải là AMBIGUOUS, không phải NEEDS_REVIEW — hai nhãn nói hai "
                         "việc khác nhau cho người xử")

    def test_a6_khong_ma_la_nao_dan_toi_trang_thai_cuoi(self):
        """Chốt rộng: KHÔNG mã lạ nào, dù mô tả nghe như 'đã giao', được dẫn tới trạng thái
        cuối. Thử cả mô tả gây nhầm, vì mô tả là thứ hãng viết tự do."""
        for ma in (100, 999, 7, 1000, 100000):
            for mo_ta in ("Ký nhận", "Giao thành công", "Delivered", "签收", ""):
                qd = tt.quyet_dinh("jt", str(ma), mo_ta)
                self.assertNotIn(
                    qd.trang_thai_ap, ("giao_thanh_cong", "hoan_hang"),
                    f"mã lạ {ma} + mô tả {mo_ta!r} dẫn tới trạng thái CUỐI "
                    f"{qd.trang_thai_ap!r} — mô tả do hãng viết tự do, không được dùng làm "
                    f"căn cứ kết thúc đơn")


if __name__ == "__main__":
    unittest.main(verbosity=2)
