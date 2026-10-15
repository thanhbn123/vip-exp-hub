# Bộ thử CHỐT CHẶN D-9 — ánh xạ `area` của J&T chưa được hãng xác nhận.
#
# VÌ SAO CÓ FILE NÀY
# ------------------
# Anh Thành chốt: "Chưa chốt cách ánh xạ `area` cho đến khi hãng xác nhận." (D-9)
# Hiện `adapter_jt.TRUONG_HANH_CHINH` map `area` ← **quận/huyện**. AG-00 đã ghi rõ trong
# docstring rằng đó là **giả định**. Nhưng lời bình không chặn được máy: giả định nằm im
# trong mã sẽ **lặng lẽ thành dữ kiện** ở lượt đầu tiên có ai đó mở `CHO_PHEP_LIVE`.
# Đúng dạng §12.2 — "cấu trúc canh giữ, không canh bằng lời dặn".
#
# DỮ KIỆN MỚI ĐO ĐƯỢC 15/10/2026 — GIẢ ĐỊNH NÀY NHIỀU KHẢ NĂNG SAI
# ----------------------------------------------------------------
# Đọc bằng trình duyệt trang `open.jtexpress.vn/apiDoc/orderserve/create` (SPA, `curl`
# không đọc được), bảng tham số và ví dụ yêu cầu ghi NGUYÊN VĂN:
#
#   prov  String(40)  BẮT BUỘC (Y)  "寄件人省"  → ví dụ: "Hồ Chí Minh"
#   city  String(40)  KHÔNG (N)     "寄件人市"  → ví dụ: "Quận 1"
#   area  String(40)  BẮT BUỘC (Y)  "寄件人区"  → ví dụ: "Phường Nguyễn Thái Bình-028QQ107"
#
# và dòng chú thích của `city`: "新的两级行政区划地址无需填写该字段，可以设置为 null。"
# (địa chỉ hành chính hai cấp MỚI thì không cần điền trường này, để null được).
#
# ⇒ Theo CHÍNH VÍ DỤ CỦA HÃNG, **quận nằm ở `city`, phường/xã nằm ở `area`** — ngược với
#   giả định đang nằm trong mã. Đây là dữ kiện đo được, KHÔNG phải kết luận: bộ thử này
#   **không đổi ánh xạ** (D-9 cấm, và `adapter_jt.py` không thuộc quyền ghi của AG-03).
#   Nó chỉ dựng chốt chặn để giả định không tự đi ra đường LIVE. Hãng xác nhận bằng câu
#   hỏi 28 của `docs/JT_CAU_HOI_CHINH_THUC.md`.
#
# FILE NÀY KIỂM BA THỨ
#   A. Hiện trạng — ghim lại ánh xạ đang chạy, để lần đổi nào cũng nhìn thấy được.
#   B. Logic chốt chặn — chạy trên BẢN THAM CHIẾU chép nguyên văn từ bản vá đề xuất.
#   C. Đã cắm vào `adapter_jt.py` chưa — hiện CHƯA (AG-03 không sở hữu file đó).
#      Ca nhóm C **bỏ qua** chứ không "đạt": bỏ qua là bỏ qua, không phải xong.
#
# Chạy: python3 app/thu/thu_anh_xa_area.py
import os
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-area-")
os.environ.setdefault("VIP_HUB_DATA", _tam)

import adapter_jt      # noqa: E402
import loi_hang as lh  # noqa: E402

# ════════════════════════════════════════════════════════════════════════════════
# BẢN THAM CHIẾU — chép NGUYÊN VĂN từ bản vá đề xuất cho `app/adapter_jt.py`
# (mục "Bản vá D-9" của `docs/G12_VTP_KHAO_SAT.md`). Để ở đây thì logic chốt chặn
# được KIỂM THẬT ngay hôm nay, không phải chờ bản vá được cắm. Khi AG-00 cắm vào
# `adapter_jt.py`, nhóm C dưới đây tự bật và kiểm lại chính bản trong adapter.
# ════════════════════════════════════════════════════════════════════════════════

ANH_XA_AREA_DA_XAC_NHAN = False
NGUON_XAC_NHAN_AREA = ""
CAP_HANH_CHINH_CHO_AREA = "quan-huyen"

CAP_HOP_LE = ("quan-huyen", "phuong-xa")
DAI_NGUON_TOI_THIEU = 20
TU_GIU_CHO = ("todo", "tbd", "n/a", "na", "?", "chua biet", "chưa biết", "xxx", "...",
              "sau", "updating", "fixme")


def chot_chan_anh_xa_area(moi_truong, da_xac_nhan=None, nguon=None, cap=None):
    """Chặn đường LIVE khi ánh xạ `area` chưa được J&T xác nhận (D-9).

    MOCK luôn đi qua: bộ thử và dữ liệu demo cần chạy, và ở MOCK không có đơn thật nào
    bị định tuyến sai. Mọi môi trường khác (`sandbox`, `production`) phải qua đủ ba cửa.

    Ba cửa, và vì sao mỗi cửa tồn tại:

    1. `da_xac_nhan` còn False ⇒ chặn. Đây là cửa chính: D-9 nói "chưa chốt cho đến khi
       hãng xác nhận", nên mặc định phải là CHẶN, không phải cho qua kèm lời cảnh báo.
    2. `da_xac_nhan` True nhưng `nguon` rỗng/giữ chỗ ⇒ chặn. Không có cửa này thì chốt
       chặn tự vô hiệu hoá: ai đó sửa một chữ `False` → `True` là xong, không để lại dấu
       vết nào về việc hãng đã nói gì. Danh sách TỪ GIỮ CHỖ là danh sách **đen** — theo
       câu hỏi phân biệt của §12.2: quên một từ giữ chỗ thì chỉ lọt một chuỗi trông lạ
       mà vẫn là người thật gõ vào (vô hại); còn danh sách trắng các trích dẫn "hợp lệ"
       thì không viết nổi, và quên một dạng là chặn nhầm người làm đúng.
    3. `cap` không thuộc `CAP_HOP_LE` ⇒ chặn. Đây là danh sách **trắng**, và đúng chỗ:
       quên một cấp khỏi danh sách = bị chặn = AN TOÀN; còn cho qua một cấp lạ = đơn đi
       sai tuyến mà không ai báo. Cùng ngoại lệ mà §12.2 đã nêu sẵn.

    Tham số để None ⇒ đọc hằng của module (đường chạy thật). Truyền tường minh ⇒ dùng
    giá trị truyền vào (đường bộ thử) — nhờ vậy ca thử không phải vá hằng toàn cục.
    """
    if moi_truong == "mock":
        return

    da = ANH_XA_AREA_DA_XAC_NHAN if da_xac_nhan is None else da_xac_nhan
    ng = NGUON_XAC_NHAN_AREA if nguon is None else nguon
    cp = CAP_HANH_CHINH_CHO_AREA if cap is None else cap

    def _chan(ly_do):
        raise lh.NormalizedCarrierError(
            lh.THAM_SO_SAI,
            thong_diep=(
                "CHỐT CHẶN D-9 — ánh xạ trường `area` của J&T CHƯA ĐƯỢC HÃNG XÁC NHẬN, "
                "nên không được gửi đơn thật. " + ly_do + " "
                "Cần J&T trả lời câu hỏi 28 (docs/JT_CAU_HOI_CHINH_THUC.md): với địa chỉ "
                "hành chính HAI CẤP của Việt Nam từ 2025, `prov` và `area` phải điền chính "
                "xác chuỗi nào, và có danh mục địa danh chuẩn tải về được không. "
                "Lưu ý: ví dụ trong chính tài liệu tạo đơn đặt QUẬN vào `city` và "
                "PHƯỜNG vào `area` — ngược với ánh xạ đang dùng. "
                "Có trả lời rồi thì đặt ANH_XA_AREA_DA_XAC_NHAN=True, điền "
                "NGUON_XAC_NHAN_AREA (ai nói · ngày nào · ở đâu) và CAP_HANH_CHINH_CHO_AREA."),
            hang="jt", thao_tac="createOrder")

    if not da:
        _chan("Cờ ANH_XA_AREA_DA_XAC_NHAN đang là False.")
    chuoi = str(ng or "").strip()
    if not chuoi:
        _chan("Cờ đã đặt True nhưng NGUON_XAC_NHAN_AREA còn RỖNG — "
              "không có nguồn thì không có xác nhận.")
    thap = chuoi.lower()
    if len(chuoi) < DAI_NGUON_TOI_THIEU or any(t == thap for t in TU_GIU_CHO):
        _chan("NGUON_XAC_NHAN_AREA đang là chuỗi giữ chỗ hoặc quá ngắn "
              f"({len(chuoi)} ký tự, cần tối thiểu {DAI_NGUON_TOI_THIEU}) — "
              "phải ghi rõ ai xác nhận, ngày nào, bằng kênh nào.")
    if cp not in CAP_HOP_LE:
        _chan(f"CAP_HANH_CHINH_CHO_AREA = {cp!r} không thuộc danh sách hợp lệ "
              f"{CAP_HOP_LE}.")


# ════════════════════════════════════════════════════════════════════════════════

NGUON_THAT = "Email J&T VN gửi 20/10/2026, anh Nguyen phu trach tich hop API xac nhan"

DON_MAU = {"ma_don": "T-AREA-1", "nguoi_gui_ten": "A", "nguoi_gui_sdt": "0901111111",
           "nguoi_gui_dia_chi": "x", "nguoi_gui_tinh": "Hồ Chí Minh",
           "nguoi_gui_quan": "Quận 1",
           "nguoi_nhan_ten": "B", "nguoi_nhan_sdt": "0902222222",
           "nguoi_nhan_dia_chi": "y", "nguoi_nhan_tinh": "Hà Nội",
           "nguoi_nhan_quan": "Ba Đình",
           "hang_hoa": "z", "khoi_luong_gram": 500, "cod": 0}


class A_HienTrang(unittest.TestCase):
    """Ghim ánh xạ đang chạy. Ai đổi `TRUONG_HANH_CHINH` thì hỏng ở đây và phải đọc D-9."""

    def test_A1_area_dang_lay_tu_quan_huyen(self):
        """Dữ kiện: hôm nay `area` lấy từ cột quận/huyện. KHÔNG phải là nó đúng."""
        cap = {(nhom, truong): cot for nhom, truong, cot in adapter_jt.AdapterJT.TRUONG_HANH_CHINH}
        self.assertEqual(cap[("sender", "area")], "nguoi_gui_quan")
        self.assertEqual(cap[("receiver", "area")], "nguoi_nhan_quan")
        self.assertEqual(cap[("sender", "prov")], "nguoi_gui_tinh")
        self.assertEqual(cap[("receiver", "prov")], "nguoi_nhan_tinh")

    def test_A2_bizcontent_bo_han_truong_city(self):
        """Hệ KHÔNG gửi `city`. Ví dụ của hãng đặt QUẬN vào `city` ⇒ ghi lại để đối chiếu."""
        a = adapter_jt.AdapterJT({}, "mock")
        biz = a._dung_bizcontent_tao_don(DON_MAU)
        self.assertNotIn("city", biz["sender"])
        self.assertEqual(biz["sender"]["area"], "Quận 1")       # quận đang nằm ở `area`
        self.assertEqual(biz["receiver"]["area"], "Ba Đình")

    def test_A3_giả_dinh_chi_duoc_ghi_bang_loi_binh(self):
        """Hôm nay giả định CHỈ được canh bằng docstring — đó chính là lỗ D-9."""
        self.assertIn("giả định", adapter_jt.AdapterJT._dung_bizcontent_tao_don.__doc__)


class B_LogicChotChan(unittest.TestCase):
    """Kiểm bản THAM CHIẾU của chốt chặn (= bản vá đề xuất, chép nguyên văn)."""

    def test_B1_mock_luon_di_qua(self):
        """MOCK phải chạy được: bộ thử và dữ liệu demo cần nó."""
        chot_chan_anh_xa_area("mock")                      # cờ False — vẫn qua
        chot_chan_anh_xa_area("mock", da_xac_nhan=False, nguon="", cap="bay-ba")

    def test_B2_co_False_thi_LIVE_bi_chan(self):
        """Cửa chính: chưa xác nhận ⇒ sandbox và production đều bị chặn."""
        for mt in ("sandbox", "production"):
            with self.subTest(moi_truong=mt):
                with self.assertRaises(lh.NormalizedCarrierError) as e:
                    chot_chan_anh_xa_area(mt, da_xac_nhan=False, nguon=NGUON_THAT)
                self.assertEqual(e.exception.ma_chuan, lh.THAM_SO_SAI)

    def test_B3_thong_diep_noi_ro_can_hang_xac_nhan_cai_gi(self):
        """Chặn mà không nói cần gì thì người đọc sẽ gỡ chốt cho xong việc."""
        with self.assertRaises(lh.NormalizedCarrierError) as e:
            chot_chan_anh_xa_area("production", da_xac_nhan=False)
        td = str(e.exception)
        for phai_co in ("D-9", "area", "câu hỏi 28", "HAI CẤP", "city"):
            self.assertIn(phai_co, td, f"thiếu {phai_co!r} trong thông điệp chặn")

    def test_B4_dat_True_ma_khong_co_nguon_cung_bi_chan(self):
        """Ca canh quan trọng nhất: không cho vô hiệu hoá chốt bằng cách sửa một chữ."""
        for xau in ("", "   ", "\n\t "):
            with self.subTest(nguon=repr(xau)):
                with self.assertRaises(lh.NormalizedCarrierError):
                    chot_chan_anh_xa_area("production", da_xac_nhan=True, nguon=xau)

    def test_B5_nguon_giu_cho_bi_chan(self):
        """`TODO`, `?`, `tbd`… không phải nguồn xác nhận."""
        for xau in ("TODO", "tbd", "n/a", "?", "chưa biết", "xxx", "FIXME", "sau"):
            with self.subTest(nguon=xau):
                with self.assertRaises(lh.NormalizedCarrierError):
                    chot_chan_anh_xa_area("production", da_xac_nhan=True, nguon=xau)

    def test_B6_nguon_qua_ngan_bi_chan(self):
        with self.assertRaises(lh.NormalizedCarrierError):
            chot_chan_anh_xa_area("production", da_xac_nhan=True, nguon="J&T ok")

    def test_B7_cap_hanh_chinh_la_la_bi_chan(self):
        """Danh sách TRẮNG: cấp lạ ⇒ chặn (quên một cấp thì an toàn, không phải hỏng)."""
        for cap in ("tinh", "xa", "", "quan_huyen", "district", "Quan-Huyen"):
            with self.subTest(cap=cap):
                with self.assertRaises(lh.NormalizedCarrierError):
                    chot_chan_anh_xa_area("production", da_xac_nhan=True,
                                          nguon=NGUON_THAT, cap=cap)

    def test_B8_du_ba_cua_thi_di_qua(self):
        """Chốt chặn phải MỞ ĐƯỢC — chốt không mở được là chốt sẽ bị gỡ."""
        for cap in CAP_HOP_LE:
            with self.subTest(cap=cap):
                chot_chan_anh_xa_area("production", da_xac_nhan=True,
                                      nguon=NGUON_THAT, cap=cap)

    def test_B9_mac_dinh_cua_module_dang_la_CHAN(self):
        """Đọc hằng thật của module (không truyền tham số): phải là chặn."""
        self.assertFalse(ANH_XA_AREA_DA_XAC_NHAN)
        self.assertEqual(NGUON_XAC_NHAN_AREA, "")
        with self.assertRaises(lh.NormalizedCarrierError):
            chot_chan_anh_xa_area("production")


class C_DaCamVaoAdapterChua(unittest.TestCase):
    """Chốt chặn chỉ có tác dụng khi nằm TRONG `adapter_jt.py`.

    AG-03 không sở hữu file đó (SHARED_CONTRACTS mục 22), nên nhóm này hiện **BỎ QUA**.
    Bỏ qua KHÔNG phải đạt — §12.1. Cắm bản vá vào là nhóm này tự bật.
    """

    def setUp(self):
        if not hasattr(adapter_jt, "chot_chan_anh_xa_area"):
            self.skipTest(
                "CHƯA CẮM: `adapter_jt.chot_chan_anh_xa_area` không tồn tại. "
                "Bản vá đề xuất ở docs/G12_VTP_KHAO_SAT.md mục 'Bản vá D-9'. "
                "Chừng nào chưa cắm, giả định `area` ← quận/huyện vẫn ĐI THẲNG ra LIVE "
                "được nếu ai đó mở CHO_PHEP_LIVE.")

    def test_C1_hang_co_mat_va_mac_dinh_la_chan(self):
        self.assertFalse(adapter_jt.ANH_XA_AREA_DA_XAC_NHAN)
        self.assertEqual(str(adapter_jt.NGUON_XAC_NHAN_AREA or "").strip(), "")

    def test_C2_mock_van_tao_duoc_bizcontent(self):
        a = adapter_jt.AdapterJT({}, "mock")
        biz = a._dung_bizcontent_tao_don(DON_MAU)
        self.assertEqual(biz["sender"]["prov"], "Hồ Chí Minh")

    def test_C3_duong_LIVE_bi_chan_boi_chot(self):
        """Dựng adapter ở sandbox bằng cách mở tạm CHO_PHEP_LIVE, rồi xác nhận
        chốt D-9 vẫn chặn — chứng minh hai ổ khoá ĐỘC LẬP, không phải một."""
        lop = adapter_jt.AdapterJT
        cu = lop.CHO_PHEP_LIVE
        try:
            lop.CHO_PHEP_LIVE = True
            a = lop({"apiAccount": "x", "privateKey": "y"}, "sandbox")
            with self.assertRaises(lh.NormalizedCarrierError) as e:
                a._dung_bizcontent_tao_don(DON_MAU)
            self.assertIn("D-9", str(e.exception))
        finally:
            lop.CHO_PHEP_LIVE = cu

    def test_C4_adapter_dung_chung_mot_dinh_nghia_voi_ban_tham_chieu(self):
        """Hai bản lệch nhau là hai bản sẽ lệch tiếp — §16.6/§12.2."""
        for ten in ("CAP_HOP_LE", "DAI_NGUON_TOI_THIEU"):
            self.assertEqual(getattr(adapter_jt, ten), globals()[ten],
                             f"{ten} trong adapter_jt lệch với bản tham chiếu")


if __name__ == "__main__":
    kq = unittest.main(verbosity=2, exit=False).result
    print()
    print("=" * 78)
    if not hasattr(adapter_jt, "chot_chan_anh_xa_area"):
        print("!! CHỐT CHẶN D-9 CHƯA ĐƯỢC CẮM VÀO app/adapter_jt.py")
        print("!! Logic đã kiểm ĐẠT trên bản tham chiếu (nhóm B), nhưng đường LIVE thật")
        print("!! VẪN CHƯA ĐƯỢC CANH. Nhóm C bỏ qua — bỏ qua không phải là đạt.")
        print("!! Bản vá: docs/G12_VTP_KHAO_SAT.md, mục 'Bản vá D-9'.")
    else:
        print("Chốt chặn D-9 đã nằm trong adapter_jt.py — nhóm C đã chạy thật.")
    print(f"Tổng: {kq.testsRun} ca · hỏng {len(kq.failures)} · lỗi {len(kq.errors)} "
          f"· bỏ qua {len(kq.skipped)}")
    print("=" * 78)
    sys.exit(bool(kq.failures or kq.errors))
