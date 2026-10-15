# -*- coding: utf-8 -*-
"""Bộ thử G12 — lớp truy vấn dùng chung (`app/truy_van.py`).

Chạy: python3 app/thu/thu_truy_van.py
      python3 app/thu/thu_truy_van.py --hieu-nang     (sinh 20 000 đơn, đo trước/sau chỉ mục)

Ba điều bộ thử này CỐ Ý làm, nói rõ để sau không ai tưởng là sơ suất:

1) Nó dựng CSDL TẠM riêng bằng chính `app/migrate.py` (schema thật v8), **không** dùng bảng
   giả tự chế. Lý do: §"dữ liệu mẫu phải soi dữ liệu thật" — bốn lần trong ngày 18/09/2026 bộ
   thử ĐẠT mà hệ thật HỎNG vì bản giả làm theo giả định của chính người viết. `don_hang` thật
   có 40 cột sau v7; bảng giả ba cột sẽ không bắt được lỗi nào thuộc về cột thứ tư.

2) Nó chèn đơn bằng `INSERT` thẳng chứ không qua `don_hang.tao_don`. Lý do: đang thử TẦNG TRUY
   VẤN, không thử tầng nghiệp vụ. Đi qua `tao_don` thì mỗi ca hỏng phải tự chứng minh là hỏng
   ở đâu, và ca hiệu năng 20 000 đơn sẽ mất nhiều phút vì chạy cả máy trạng thái.

3) Mỗi ca "chặn" (tiêm SQL, tham số lạ, tiền thập phân) đều kèm một phép **đối chứng dương**:
   chứng minh câu HỢP LỆ tương ứng vẫn chạy được. Một ca chỉ kiểm "có ném ngoại lệ" sẽ vẫn
   ĐẠT khi hàm ném ngoại lệ với MỌI đầu vào — tức là ca vô dụng (§12.1).
"""
import os
import sqlite3
import sys
import tempfile
import time
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-thu-truyvan-")
os.environ["VIP_HUB_DATA"] = _tam

import csdl        # noqa: E402
import truy_van    # noqa: E402

TENANT_A = 901
TENANT_B = 902


def _migrate(thu_muc=None):
    """Dựng schema THẬT bằng migrate.py trên CSDL tạm (không chạm app/du-lieu/)."""
    import subprocess
    tm = thu_muc or _tam
    r = subprocess.run([sys.executable, os.path.join(GOC_APP, "migrate.py")],
                       capture_output=True, text=True, env={**os.environ, "VIP_HUB_DATA": tm})
    if r.returncode != 0:
        raise RuntimeError(f"migrate hỏng: {r.stdout}\n{r.stderr}")


def _tao_tenant(tid, ten):
    csdl.ghi("INSERT OR IGNORE INTO tenants (id, code, ten, goi_id, trang_thai, tao_luc)"
             " VALUES (?,?,?,'free','hoat_dong',?)", (tid, f"t{tid}", ten, csdl.bay_gio()))


def _tao_tk_hang(tid, hang, ten):
    cur = csdl.ghi("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                   " credentials_ma_hoa, credentials_duoi, webhook_ma,"
                   " webhook_secret_ma_hoa, kich_hoat, tao_luc)"
                   " VALUES (?,?,?,'mock','','', ?, '', 1, ?)",
                   (tid, hang, ten, f"wh-{tid}-{hang}", csdl.bay_gio()))
    return cur.lastrowid


COT_DON = ("tenant_id", "ma_don", "nguoi_gui_ten", "nguoi_gui_sdt", "nguoi_gui_dia_chi",
           "nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa",
           "khoi_luong_gram", "cod", "gia_tri_khai", "trang_thai", "trang_thai_giao",
           "carrier_account_id", "ma_van_don", "khach_hang_id", "can_doi_soat_ket_qua",
           "external_reference", "nguoi_tao", "tao_luc", "cap_nhat_luc")


def _chen_don(**g):
    """Chèn một đơn. Mặc định đủ mọi cột NOT NULL của schema thật v8."""
    d = {"tenant_id": TENANT_A, "ma_don": f"D{int(time.time()*1e6)%10**9}",
         "nguoi_gui_ten": "Shop", "nguoi_gui_sdt": "0901", "nguoi_gui_dia_chi": "1 Gửi",
         "nguoi_nhan_ten": "Khách", "nguoi_nhan_sdt": "0902", "nguoi_nhan_dia_chi": "2 Nhận",
         "hang_hoa": "Áo", "khoi_luong_gram": 500, "cod": 100000, "gia_tri_khai": 0,
         "trang_thai": "nhap", "trang_thai_giao": None, "carrier_account_id": None,
         "ma_van_don": None, "khach_hang_id": None, "can_doi_soat_ket_qua": 0,
         "external_reference": None, "nguoi_tao": 1,
         "tao_luc": "2026-10-15 10:00:00+0700", "cap_nhat_luc": "2026-10-15 10:00:00+0700"}
    d.update(g)
    cur = csdl.ghi(f"INSERT INTO don_hang ({','.join(COT_DON)})"
                   f" VALUES ({','.join('?' * len(COT_DON))})", tuple(d[c] for c in COT_DON))
    return cur.lastrowid


# ============================================================================
# LỚP A — ĐÚNG SAI CỦA TỪNG ĐIỀU KIỆN
# ============================================================================

# Dựng NỀN đúng MỘT lần cho cả file. Không đặt trong `setUpClass`: bốn lớp ca thử kế thừa
# `ThuDieuKien`, nên `setUpClass` sẽ chạy bốn lần và chèn bốn lần dữ liệu — mọi con số `tong`
# trong bộ thử sẽ sai theo thứ tự chạy, mà vẫn "chạy được". Đúng dạng hỏng im lặng.
NEN = {}


_da_migrate = False


def _dung_nen():
    global _da_migrate
    if NEN:
        return NEN
    if not _da_migrate:
        # Chỉ migrate MỘT lần kể cả khi lượt dựng nền sau đó hỏng: migrate lần hai từ tiến
        # trình con trong khi tiến trình này đã mở kết nối sẽ báo "database is locked" và che
        # mất lỗi THẬT. Đúng dạng §12.2 — thông báo lỗi của hệ nói về chính nó thì phải nghi.
        _migrate()
        _da_migrate = True
    _tao_tenant(TENANT_A, "Tenant A")
    _tao_tenant(TENANT_B, "Tenant B")
    csdl.ghi("INSERT OR IGNORE INTO users (id, ten_dang_nhap, mat_khau_hash, ho_ten,"
             " trang_thai, so_lan_sai, tao_luc) VALUES (1,'thu','x','Người Thử','hoat_dong',0,?)",
             (csdl.bay_gio(),))
    csdl.ghi("INSERT OR IGNORE INTO khach_hang (id, tenant_id, ten, tao_luc)"
             " VALUES (77,?,?,?)", (TENANT_A, "Khách 77", csdl.bay_gio()))
    truy_van.ap_ddl()
    NEN["tk_vtp"] = _tao_tk_hang(TENANT_A, "vtp", "VTP A")
    NEN["tk_jt"] = _tao_tk_hang(TENANT_A, "jt", "J&T A")
    NEN["tk_b"] = _tao_tk_hang(TENANT_B, "vtp", "VTP B")
    NEN["ids"] = []
    for i in range(6):
        NEN["ids"].append(_chen_don(
            ma_don=f"DON-A-{i}", cod=10000 * (i + 1), khoi_luong_gram=100 * (i + 1),
            nguoi_nhan_ten=f"Khách {i}", hang_hoa=f"Hàng {i}",
            trang_thai="da_gui" if i < 2 else "nhap",
            trang_thai_giao="giao_thanh_cong" if i == 0 else ("lay_hang" if i == 1 else None),
            carrier_account_id=NEN["tk_vtp"] if i < 3 else (NEN["tk_jt"] if i < 5 else None),
            ma_van_don=f"MVD{i}" if i < 2 else None,
            can_doi_soat_ket_qua=1 if i == 0 else 0,
            khach_hang_id=77 if i in (0, 1) else None,
            external_reference=f"EXT-{i}",
            tao_luc=f"2026-10-{10+i:02d} 08:00:00+0700",
            cap_nhat_luc=f"2026-10-{10+i:02d} 09:00:00+0700"))
    # Tenant B: 4 đơn, COD và ngày TRÙNG dải của A — cách ly mà sai thì lộ ngay.
    NEN["ids_b"] = [_chen_don(tenant_id=TENANT_B, ma_don=f"DON-B-{i}", cod=10000 * (i + 1),
                              nguoi_nhan_ten=f"Khách {i}", hang_hoa=f"Hàng {i}",
                              carrier_account_id=NEN["tk_b"],
                              tao_luc=f"2026-10-{10+i:02d} 08:00:00+0700",
                              cap_nhat_luc=f"2026-10-{10+i:02d} 08:00:00+0700")
                    for i in range(4)]
    return NEN


class Nen(unittest.TestCase):
    """Nền chung. Các lớp ca thử kế thừa lớp NÀY, không kế thừa lẫn nhau — kế thừa lẫn nhau
    thì mỗi ca của lớp cha chạy lại một lần cho mỗi lớp con, và số ca báo ra bị thổi lên gấp
    bốn mà không thêm phép kiểm nào (§12.1 luật 4: số trong báo cáo phải là số đo thật)."""

    @classmethod
    def setUpClass(cls):
        n = _dung_nen()
        cls.tk_vtp, cls.tk_jt, cls.tk_b = n["tk_vtp"], n["tk_jt"], n["tk_b"]
        cls.ids, cls.ids_b = n["ids"], n["ids_b"]

    def tim(self, loc=None, tid=TENANT_A):
        return truy_van.tim_don(tid, loc)


class ThuDieuKien(Nen):
    # --- từng điều kiện riêng ---

    def test_a01_khong_loc_tra_dung_don_cua_tenant_minh(self):
        kq = self.tim()
        self.assertEqual(kq["tong"], 6)
        self.assertTrue(kq["tong_chinh_xac"])
        self.assertEqual(self.tim(tid=TENANT_B)["tong"], 4)

    def test_a02_trang_thai_mot_va_nhieu_gia_tri(self):
        self.assertEqual(self.tim({"trang_thai": "da_gui"})["tong"], 2)
        self.assertEqual(self.tim({"trang_thai": ["da_gui", "nhap"]})["tong"], 6)
        self.assertEqual(self.tim({"trang_thai": "khong_co_that"})["tong"], 0)

    def test_a03_trang_thai_giao(self):
        self.assertEqual(self.tim({"trang_thai_giao": "giao_thanh_cong"})["tong"], 1)
        self.assertEqual(self.tim({"trang_thai_giao": ["giao_thanh_cong", "lay_hang"]})["tong"], 2)

    def test_a04_khoang_ngay_BAO_GOM_ca_hai_dau(self):
        """Đầu/cuối BAO GỒM — ghi rõ trong tài liệu, nên phải có ca canh đúng điều đã ghi."""
        kq = self.tim({"tu_ngay": "2026-10-11", "den_ngay": "2026-10-13"})
        self.assertEqual(sorted(x["ma_don"] for x in kq["dong"]),
                         ["DON-A-1", "DON-A-2", "DON-A-3"])
        mot_ngay = self.tim({"tu_ngay": "2026-10-10", "den_ngay": "2026-10-10"})
        self.assertEqual(mot_ngay["tong"], 1, "tu_ngay == den_ngay phải ra ĐÚNG MỘT ngày")
        self.assertEqual(self.tim({"tu_ngay": "2026-10-15"})["tong"], 1)

    def test_a04b_don_luc_23h59_cua_den_ngay_van_duoc_TINH(self):
        """Ranh giới cuối ngày — chỗ sai thầm lặng nhất của lọc theo ngày.

        Cột `tao_luc` là "YYYY-MM-DD HH:MM:SS+0700", nên `tao_luc <= '2026-10-20'` sẽ loại
        SẠCH mọi đơn trong ngày 20 (vì "2026-10-20 08:00" > "2026-10-20") và trả về rỗng mà
        không báo gì. Ca này canh đúng cái đó: đơn lúc 23:59:59 phải NẰM TRONG kết quả.
        """
        _chen_don(ma_don="BIEN-CUOI", tao_luc="2026-10-20 23:59:59+0700",
                  cap_nhat_luc="2026-10-20 23:59:59+0700")
        _chen_don(ma_don="BIEN-DAU", tao_luc="2026-10-20 00:00:00+0700",
                  cap_nhat_luc="2026-10-20 00:00:00+0700")
        _chen_don(ma_don="BIEN-NGOAI", tao_luc="2026-10-21 00:00:00+0700",
                  cap_nhat_luc="2026-10-21 00:00:00+0700")
        try:
            kq = self.tim({"tu_ngay": "2026-10-20", "den_ngay": "2026-10-20"})
            self.assertEqual(sorted(x["ma_don"] for x in kq["dong"]),
                             ["BIEN-CUOI", "BIEN-DAU"])
        finally:
            csdl.ghi("DELETE FROM don_hang WHERE ma_don LIKE 'BIEN-%'")

    def test_a04c_ngay_khong_co_that_bi_chan(self):
        for xau in ("2026-02-30", "2026-13-01", "2026-00-10"):
            with self.assertRaises(truy_van.LoiTruyVan, msg=f"{xau} lọt qua"):
                self.tim({"tu_ngay": xau})

    def test_a05_ngay_sai_dinh_dang_bi_chan_nhung_dung_dinh_dang_thi_chay(self):
        for xau in ("15/10/2026", "2026-10", "hom qua", "2026-13-99x"):
            with self.assertRaises(truy_van.LoiTruyVan, msg=f"{xau!r} lọt qua"):
                self.tim({"tu_ngay": xau})
        self.assertEqual(self.tim({"tu_ngay": "2026-10-10"})["tong"], 6)   # đối chứng dương

    def test_a06_khoang_cod_la_so_nguyen_dong(self):
        kq = self.tim({"cod_tu": 20000, "cod_den": 40000})
        self.assertEqual(sorted(x["cod"] for x in kq["dong"]), [20000, 30000, 40000])
        self.assertEqual(self.tim({"cod_tu": 50000})["tong"], 2)
        self.assertEqual(self.tim({"cod_den": 10000})["tong"], 1)

    def test_a07_tien_thap_phan_bi_TU_CHOI_khong_bi_cat_cut(self):
        """§16: tiền là INTEGER đồng. `int(float('20000.7'))` = 20000 — mất 7 hào im lặng."""
        for xau in (20000.5, "20000.7", "20k", True):
            with self.assertRaises(truy_van.LoiTruyVan, msg=f"{xau!r} lọt vào cod_tu"):
                self.tim({"cod_tu": xau})
        self.assertEqual(self.tim({"cod_tu": "20000"})["tong"], 5,
                         "chuỗi số nguyên phải vẫn nhận (đối chứng dương)")

    def test_a08_loc_theo_hang_di_qua_carrier_accounts(self):
        """`hang` KHÔNG phải cột của don_hang — nó phải đi qua carrier_accounts."""
        self.assertEqual(self.tim({"hang": "vtp"})["tong"], 3)
        self.assertEqual(self.tim({"hang": "jt"})["tong"], 2)
        self.assertEqual(self.tim({"hang": ["vtp", "jt"]})["tong"], 5)
        self.assertEqual(self.tim({"hang": "hang_ma"})["tong"], 0)

    def test_a09_loc_theo_hang_KHONG_rò_sang_tenant_khac(self):
        """Câu con phải mang tenant của chính nó, nếu không `hang=vtp` khớp cả tài khoản của B."""
        kq = self.tim({"hang": "vtp"}, tid=TENANT_B)
        self.assertEqual(kq["tong"], 4)
        self.assertTrue(all(x["ma_don"].startswith("DON-B-") for x in kq["dong"]))
        # Và tenant A không bao giờ thấy tài khoản của B.
        self.assertNotIn(self.tk_b, {x["carrier_account_id"] for x in self.tim({"hang": "vtp"})["dong"]})

    def test_a10_carrier_account_id_va_khach_hang_id(self):
        self.assertEqual(self.tim({"carrier_account_id": self.tk_jt})["tong"], 2)
        self.assertEqual(self.tim({"khach_hang_id": 77})["tong"], 2)
        self.assertEqual(self.tim({"carrier_account_id": self.tk_b})["tong"], 0,
                         "tài khoản hãng của tenant khác không được khớp đơn nào")

    def test_a11_can_doi_soat(self):
        self.assertEqual(self.tim({"can_doi_soat": 1})["tong"], 1)
        self.assertEqual(self.tim({"can_doi_soat": "1"})["tong"], 1)
        # Số 0 KHÔNG phải "rỗng": gửi 0 là hỏi "đơn KHÔNG cần đối soát", và phải lọc thật.
        # Nếu 0 bị coi là rỗng thì người bấm "không cần đối soát" nhận về CẢ HAI loại.
        self.assertEqual(self.tim({"can_doi_soat": 0})["tong"], 5)
        self.assertEqual(self.tim({"can_doi_soat": "0"})["tong"], 5)
        # Chuỗi rỗng / None mới là "không lọc" — giao diện gửi ô trống là chuyện thường.
        self.assertEqual(self.tim({"can_doi_soat": ""})["tong"], 6)
        self.assertEqual(self.tim({"can_doi_soat": None})["tong"], 6)

    def test_a12_tim_chu_q_tren_nhieu_cot(self):
        self.assertEqual([x["ma_don"] for x in self.tim({"q": "Khách 3"})["dong"]], ["DON-A-3"])
        self.assertEqual([x["ma_don"] for x in self.tim({"q": "Hàng 4"})["dong"]], ["DON-A-4"])
        self.assertEqual([x["ma_don"] for x in self.tim({"q": "MVD1"})["dong"]], ["DON-A-1"])
        self.assertEqual(self.tim({"q": "DON-A-"})["tong"], 6)
        self.assertEqual(self.tim({"q": "DON-B-"})["tong"], 0, "q không được vượt tenant")

    def test_a13_ma_don_ma_van_don_external_reference(self):
        self.assertEqual(self.tim({"ma_don": "DON-A-2"})["tong"], 1)
        self.assertEqual(self.tim({"ma_van_don": "MVD0"})["tong"], 1)
        self.assertEqual(self.tim({"external_reference": "EXT-5"})["tong"], 1)
        self.assertEqual(self.tim({"ma_don": "DON-B-0"})["tong"], 0)

    # --- nhiều điều kiện cùng lúc ---

    def test_a14_nhieu_dieu_kien_cung_luc_la_phep_VA(self):
        kq = self.tim({"hang": "vtp", "cod_tu": 20000, "tu_ngay": "2026-10-11",
                       "trang_thai": ["nhap", "da_gui"]})
        self.assertEqual(sorted(x["ma_don"] for x in kq["dong"]), ["DON-A-1", "DON-A-2"])
        # Thêm một điều kiện nữa chỉ được làm HẸP lại, không bao giờ rộng ra.
        hep = self.tim({"hang": "vtp", "cod_tu": 20000, "tu_ngay": "2026-10-11",
                        "trang_thai": ["nhap", "da_gui"], "trang_thai_giao": "lay_hang"})
        self.assertEqual([x["ma_don"] for x in hep["dong"]], ["DON-A-1"])

    def test_a15_moi_dieu_kien_deu_co_mat_trong_cau_SQL(self):
        """Canh TỪNG trường một: trường nào khai mà không dựng ra mệnh đề nào là trường CÂM —
        nó nhận tham số, không lọc gì, và không ai biết. Đúng dạng hỏng của cả G12."""
        mau = {"tu_ngay": "2026-10-01", "den_ngay": "2026-10-31", "trang_thai": "nhap",
               "trang_thai_giao": "lay_hang", "carrier_account_id": 1, "khach_hang_id": 1,
               "hang": "vtp", "ma_don": "X", "ma_van_don": "Y", "external_reference": "Z",
               "cod_tu": 1, "cod_den": 2, "can_doi_soat": 1, "q": "abc"}
        self.assertEqual(set(mau), set(truy_van.BANG_DON.truong_loc),
                         "có trường khai trong spec mà ca này chưa phủ")
        goc, _, _ = truy_van.dung_dieu_kien(truy_van.BANG_DON, TENANT_A, {})
        for ten, gt in mau.items():
            cau, tsq, _ = truy_van.dung_dieu_kien(truy_van.BANG_DON, TENANT_A, {ten: gt})
            self.assertNotEqual(cau, goc, f"điều kiện {ten!r} KHÔNG sinh ra mệnh đề nào")
            self.assertGreater(len(tsq), 1, f"điều kiện {ten!r} không truyền tham số nào")


# ============================================================================
# LỚP B — CÁCH LY TENANT
# ============================================================================

class ThuCachLy(Nen):
    def test_b01_tenant_id_luon_co_trong_moi_cau(self):
        """Soát mọi tổ hợp điều kiện: mệnh đề đầu tiên LUÔN là tenant_id=?."""
        tap = [{}, {"q": "x"}, {"hang": "vtp"}, {"cod_tu": 1, "cod_den": 2},
               {"tu_ngay": "2026-01-01"}, {"trang_thai": ["a", "b"]}, {"can_doi_soat": 1}]
        for loc in tap:
            cau, tsq, _ = truy_van.dung_dieu_kien(truy_van.BANG_DON, TENANT_A, loc)
            self.assertTrue(cau.startswith("tenant_id=?"), f"{loc} → {cau}")
            self.assertEqual(tsq[0], TENANT_A)

    def test_b02_khong_the_khai_bang_thieu_cot_tenant(self):
        """Cửa 'bỏ qua tenant' phải đóng Ở LÚC KHAI, không đợi lúc chạy."""
        # Kiểm cả THÔNG ĐIỆP, không chỉ "có ném ngoại lệ": phép kiểm hình dạng tên cột ở
        # ngay dưới cũng ném ValueError, nên ca chỉ kiểm loại ngoại lệ sẽ vẫn ĐẠT khi chốt
        # cot_tenant bị gỡ và thay bằng một giá trị mặc định (§12.1 — đã đo bằng lượt gỡ
        # bản vá: đột biến `cot_tenant = cot_tenant or "1"` LỌT qua bản ca cũ).
        for xau in (None, "", 0):
            with self.assertRaises(ValueError) as cm:
                truy_van.BangTruyVan("don_hang", xau, [], {"a": "id"}, "a")
            self.assertIn("THIẾU cot_tenant", str(cm.exception),
                          f"cot_tenant={xau!r} bị chặn bởi phép kiểm KHÁC, không bởi chốt tenant")

    def test_b03_loc_rong_nhat_van_khong_thay_don_tenant_khac(self):
        """Lọc rộng nhất có thể: không điều kiện, giới hạn kịch trần, đủ kiểu sắp xếp."""
        for sx in truy_van.BANG_DON.sap_xep_duoc:
            kq = self.tim({"gioi_han": 500, "sap_xep": sx})
            ma = {x["ma_don"] for x in kq["dong"]}
            self.assertFalse({m for m in ma if m.startswith("DON-B-")},
                             f"sắp xếp {sx} làm lộ đơn tenant B")
            self.assertEqual(len(ma), 6)

    def test_b04_tenant_id_None_bi_tu_choi(self):
        with self.assertRaises(truy_van.LoiTruyVan):
            truy_van.tim_don(None, {})


# ============================================================================
# LỚP C — PHÂN TRANG VÀ ĐẾM
# ============================================================================

class ThuPhanTrang(Nen):
    def test_c01_trang_lien_nhau_khong_trung_khong_sot(self):
        thay, cac_trang = [], []
        for lech in (0, 2, 4, 6):
            kq = self.tim({"gioi_han": 2, "lech": lech, "sap_xep": "cu_nhat"})
            cac_trang.append([x["ma_don"] for x in kq["dong"]])
            thay += [x["ma_don"] for x in kq["dong"]]
        self.assertEqual(len(thay), len(set(thay)), f"có dòng TRÙNG giữa các trang: {cac_trang}")
        self.assertEqual(set(thay), {f"DON-A-{i}" for i in range(6)}, "có dòng BỊ SÓT")
        self.assertEqual(cac_trang[-1], [], "trang quá cuối phải rỗng, không quay vòng")

    def test_c02_phan_trang_on_dinh_khi_sap_xep_co_gia_tri_TRUNG(self):
        """Chỗ hỏng im lặng kinh điển: ORDER BY trên cột có giá trị trùng mà không khoá phá hoà
        thì thứ tự không xác định ⇒ OFFSET cho lặp dòng trang này, mất dòng trang kia."""
        for i in range(8):
            _chen_don(ma_don=f"TRUNG-{i}", cod=777000, tenant_id=TENANT_A)
        try:
            thay = []
            for lech in range(0, 8, 2):
                kq = self.tim({"cod_tu": 777000, "cod_den": 777000,
                               "gioi_han": 2, "lech": lech, "sap_xep": "cod_cao"})
                thay += [x["ma_don"] for x in kq["dong"]]
            self.assertEqual(len(thay), len(set(thay)), f"lặp dòng khi COD trùng: {thay}")
            self.assertEqual(len(thay), 8, "sót dòng khi COD trùng")
        finally:
            csdl.ghi("DELETE FROM don_hang WHERE ma_don LIKE 'TRUNG-%'")

    def test_c02b_moi_kieu_sap_xep_deu_co_KHOA_PHA_HOA_duy_nhat(self):
        """Ca c02 ở trên KHÔNG đủ: gỡ khoá phá hoà ra thì SQLite vẫn tình cờ trả đúng thứ tự
        rowid và ca đó vẫn ĐẠT — tức là ca vô dụng cho đúng cái nó định canh (§12.1). Phép
        kiểm thật phải là kiểm CẤU TRÚC: mọi biểu thức sắp xếp phải kết thúc bằng một cột
        DUY NHẤT, nếu không thì thứ tự chỉ là may mắn của bản SQLite hôm nay.

        `id` là khoá chính nên duy nhất; `ma_don` có UNIQUE(tenant_id, ma_don) và mọi câu đều
        đã kẹp tenant_id nên nó cũng duy nhất trong phạm vi kết quả.
        """
        DUY_NHAT = {"id", "ma_don"}
        for khoa, bt in truy_van.BANG_DON.sap_xep_duoc.items():
            cuoi = bt.split(",")[-1].strip().split(" ")[0]
            self.assertIn(cuoi, DUY_NHAT,
                          f"sắp xếp {khoa!r} = {bt!r} kết thúc bằng cột KHÔNG duy nhất"
                          f" ⇒ thứ tự không xác định ⇒ phân trang lặp/sót dòng")

    def test_c03_trang_1_based_quy_ra_dung_lech(self):
        t1 = self.tim({"gioi_han": 2, "trang": 1, "sap_xep": "cu_nhat"})
        t2 = self.tim({"gioi_han": 2, "trang": 2, "sap_xep": "cu_nhat"})
        self.assertEqual(t1["lech"], 0)
        self.assertEqual(t2["lech"], 2)
        self.assertEqual(t2["trang"], 2)
        self.assertEqual([x["ma_don"] for x in t2["dong"]],
                         [x["ma_don"] for x in
                          self.tim({"gioi_han": 2, "lech": 2, "sap_xep": "cu_nhat"})["dong"]])

    def test_c04_gui_ca_trang_va_lech_bi_tu_choi(self):
        with self.assertRaises(truy_van.LoiTruyVan):
            self.tim({"trang": 2, "lech": 5})

    def test_c05_tran_gioi_han_va_lech_kep_CA_HAI_DAU(self):
        self.assertEqual(self.tim({"gioi_han": 99999})["gioi_han"], truy_van.GIOI_HAN_TOI_DA)
        self.assertEqual(self.tim({"gioi_han": 0})["gioi_han"], 1)
        self.assertEqual(self.tim({"gioi_han": -5})["gioi_han"], 1)
        self.assertEqual(self.tim({"lech": -10})["lech"], 0)
        self.assertEqual(self.tim({"lech": 10**9})["lech"], truy_van.LECH_TOI_DA,
                         "OFFSET khổng lồ phải bị kẹp — nó buộc SQLite đọc-rồi-bỏ ngần ấy dòng")
        self.assertEqual(self.tim({})["gioi_han"], truy_van.GIOI_HAN_MAC_DINH)

    def test_c06_tong_la_TONG_KHOP_khong_phai_so_dong_trang_nay(self):
        kq = self.tim({"gioi_han": 2})
        self.assertEqual(len(kq["dong"]), 2)
        self.assertEqual(kq["tong"], 6)
        self.assertTrue(kq["con_nua"])
        cuoi = self.tim({"gioi_han": 2, "lech": 4})
        self.assertEqual(cuoi["tong"], 6)
        self.assertFalse(cuoi["con_nua"])

    def test_c07_tong_dung_khi_co_dieu_kien(self):
        self.assertEqual(self.tim({"hang": "vtp", "gioi_han": 1})["tong"], 3)
        self.assertEqual(self.tim({"cod_tu": 30000, "gioi_han": 1})["tong"], 4)

    def test_c08_dem_co_TRAN_va_tu_khai_khi_cham_tran(self):
        """Đếm phải DỪNG ở trần và NÓI RA là nó đã dừng — không được trả con số sai mà im."""
        that = truy_van.TRAN_DEM
        truy_van.TRAN_DEM = 3
        try:
            kq = self.tim({})
            self.assertFalse(kq["tong_chinh_xac"])
            self.assertEqual(kq["tong"], 3)
            self.assertEqual(kq["tong_it_nhat"], 3)
            self.assertTrue(kq["con_nua"])
            # Đúng BẰNG trần thì vẫn phải là chính xác (ranh giới `+1`).
            truy_van.TRAN_DEM = 6
            kq6 = self.tim({})
            self.assertTrue(kq6["tong_chinh_xac"], "đúng bằng trần bị báo nhầm là vượt trần")
            self.assertEqual(kq6["tong"], 6)
            # Cửa thoát: xin đếm chính xác thì được đếm chính xác.
            truy_van.TRAN_DEM = 3
            self.assertTrue(self.tim({"dem_chinh_xac": 1})["tong_chinh_xac"])
            self.assertEqual(self.tim({"dem_chinh_xac": 1})["tong"], 6)
        finally:
            truy_van.TRAN_DEM = that


# ============================================================================
# LỚP D — AN TOÀN: TIÊM SQL VÀ THAM SỐ LẠ
# ============================================================================

class ThuAnToan(Nen):
    TIEM = [
        "1; DROP TABLE don_hang",
        "' OR '1'='1",
        "') OR 1=1 --",
        "id DESC; DELETE FROM don_hang WHERE 1=1",
        "cod DESC",                       # tên cột THẬT nhưng không có trong danh sách trắng
        "tao_luc/**/DESC",
        "1 UNION SELECT * FROM don_hang",
        "%",
    ]

    def _bang_con_nguyen(self):
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM don_hang")["c"], 10,
                         "số dòng don_hang đã đổi — có câu phá đã chạy")

    def test_d01_sap_xep_chi_nhan_danh_sach_trang(self):
        for xau in self.TIEM:
            with self.assertRaises(truy_van.LoiTruyVan, msg=f"{xau!r} lọt vào ORDER BY"):
                self.tim({"sap_xep": xau})
        self._bang_con_nguyen()
        kq = self.tim({"sap_xep": "cod_cao"})   # đối chứng dương
        cods = [x["cod"] for x in kq["dong"]]
        self.assertEqual(cods, sorted(cods, reverse=True))

    def test_d02_tiem_qua_MOI_tham_so_gia_tri_khong_pha_duoc_gi(self):
        """Giá trị đi qua `?` nên không thể thành câu lệnh — ca này chứng minh điều đó THẬT,
        không phải tin vào lời bình trong mã."""
        gt_truong = {"tu_ngay": "ngay", "den_ngay": "ngay", "cod_tu": "so", "cod_den": "so"}
        for ten in truy_van.BANG_DON.truong_loc:
            for xau in self.TIEM:
                try:
                    kq = self.tim({ten: xau})
                except truy_van.LoiTruyVan:
                    # Trường có định dạng chặt (ngày, tiền) từ chối — cũng là chặn hợp lệ.
                    self.assertIn(ten, gt_truong, f"{ten} từ chối {xau!r} mà không phải ngày/tiền")
                    continue
                self.assertIsInstance(kq["dong"], list)
            self._bang_con_nguyen()
        self.assertEqual(self.tim({})["tong"], 6, "dữ liệu tenant A còn nguyên sau mọi lượt tiêm")

    def test_d03_tham_so_LA_tra_400_khong_bo_qua_im_lang(self):
        """Gõ sai tên tham số mà hệ im lặng = trả về KHÔNG LỌC trong khi người dùng tưởng đã
        lọc. Đó đúng là cái hỏng G12 sinh ra để diệt."""
        for la in ("trang_thai_gia0", "codtu", "hãng", "limit", "order_by", "__proto__"):
            with self.assertRaises(truy_van.LoiTruyVan, msg=f"{la!r} bị bỏ qua im lặng"):
                self.tim({la: "x"})
        try:
            self.tim({"codtu": 1})
        except truy_van.LoiTruyVan as e:
            self.assertEqual(e.ma, 400)
            self.assertIn("cod_tu", str(e), "thông báo lỗi phải liệt kê tên hợp lệ để người sửa")

    def test_d04_ten_cot_trong_khai_bao_bi_soat_ngay_luc_khai(self):
        with self.assertRaises(ValueError):
            truy_van.TruongLoc("x", "bang", cot="cod; DROP TABLE don_hang")
        with self.assertRaises(ValueError):
            truy_van.BangTruyVan("don_hang", "tenant_id", [],
                                 {"xau": "id DESC; DROP TABLE don_hang"}, "xau")
        with self.assertRaises(ValueError):
            truy_van.BangTruyVan("don_hang", "tenant_id", [], {"a": "id ASC"}, "khong_co")

    def test_d05_loc_bo_qua_noi_ra_khi_CSDL_chua_co_cot(self):
        """Tên ĐÚNG nhưng cột chưa migrate: bỏ điều kiện nhưng PHẢI nói ra, không im."""
        def co_cot_gia(bang, cot):
            return cot != "external_reference"
        kq = truy_van.tim_don(TENANT_A, {"external_reference": "EXT-1"}, co_cot=co_cot_gia)
        self.assertTrue(any("external_reference" in x for x in kq["loc_bo_qua"]),
                        "bỏ một điều kiện mà không nói ra là trả nhiều hơn người hỏi tưởng")
        self.assertEqual(kq["tong"], 6)
        # Đối chứng: CSDL CÓ cột thì không bỏ gì và lọc thật.
        day_du = truy_van.tim_don(TENANT_A, {"external_reference": "EXT-1"})
        self.assertEqual(day_du["loc_bo_qua"], [])
        self.assertEqual(day_du["tong"], 1)


# ============================================================================
# LỚP E — DDL VÀ TỰ MÔ TẢ
# ============================================================================

class ThuDDL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _dung_nen()

    def test_e01_ddl_chi_co_CREATE_INDEX_IF_NOT_EXISTS(self):
        cau = [c.strip() for c in truy_van.DDL_G12Q.split(";") if c.strip()]
        self.assertTrue(cau)
        for c in cau:
            self.assertTrue(c.upper().startswith("CREATE INDEX IF NOT EXISTS"), c)
        for cam in ("DROP", "ALTER", "DELETE", "UPDATE"):
            self.assertNotIn(cam, truy_van.DDL_G12Q.upper())

    def test_e02_ap_ddl_chay_nhieu_lan_duoc_va_tao_du_chi_muc(self):
        truy_van.ap_ddl()
        truy_van.ap_ddl()
        co = {r["name"] for r in csdl.nhieu(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_g12q_%'")}
        self.assertEqual(len(co), 9, f"thiếu chỉ mục: {sorted(co)}")

    def test_e03_moi_chi_muc_don_hang_mo_dau_bang_tenant_id(self):
        """Chỉ mục không mở đầu bằng tenant_id thì mọi câu của lớp này đều không dùng được nó."""
        for r in csdl.nhieu("SELECT name, sql FROM sqlite_master WHERE type='index'"
                            " AND name LIKE 'ix_g12q_%'"):
            self.assertIn("(tenant_id", r["sql"].replace(" ", ""), r["name"])

    def test_e04_mo_ta_bo_loc_khop_dung_spec(self):
        mt = truy_van.mo_ta_bo_loc()
        self.assertEqual({t["ten"] for t in mt["truong"]}, set(truy_van.BANG_DON.truong_loc))
        self.assertEqual(mt["sap_xep_duoc"], sorted(truy_van.BANG_DON.sap_xep_duoc))
        self.assertTrue(mt["ngay_bao_gom"].startswith("tu_ngay và den_ngay đều BAO GỒM"))

    def test_e05_lop_dung_duoc_cho_BANG_KHAC(self):
        """Nếu lớp này chỉ chạy cho don_hang thì nó không phải lớp dùng chung — chỉ là tim_don
        viết lại. Ca này dựng spec cho `ai_job` và chạy thật."""
        spec = truy_van.BangTruyVan(
            bang="ai_job", cot_tenant="tenant_id",
            truong_loc=[truy_van.TruongLoc("loai", "bang"),
                        truy_van.TruongLoc("trang_thai", "bang"),
                        truy_van.TruongLoc("q", "tim_chu", cac_cot=("loai", "nha_cung_cap"))],
            sap_xep_duoc={"moi_nhat": "id DESC", "cu_nhat": "id ASC"},
            sap_xep_mac_dinh="moi_nhat")
        for i in range(3):
            csdl.ghi("INSERT INTO ai_job (tenant_id, user_id, loai, trang_thai, vao_json,"
                     " nha_cung_cap, phien_ban_hop_dong, can_nguoi_duyet, idem_key, tao_luc)"
                     " VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (TENANT_A, 1, "chuan_hoa_dia_chi", "moi" if i else "xong", "{}",
                      "mock", "v1", 0, f"k{i}", csdl.bay_gio()))
        csdl.ghi("INSERT INTO ai_job (tenant_id, user_id, loai, trang_thai, vao_json,"
                 " nha_cung_cap, phien_ban_hop_dong, can_nguoi_duyet, idem_key, tao_luc)"
                 " VALUES (?,?,?,?,?,?,?,?,?,?)",
                 (TENANT_B, 1, "chuan_hoa_dia_chi", "moi", "{}", "mock", "v1", 0, "kb", csdl.bay_gio()))
        kq = truy_van.chay(spec, TENANT_A, {"trang_thai": "moi"})
        self.assertEqual(kq["tong"], 2)
        self.assertEqual(truy_van.chay(spec, TENANT_B, {})["tong"], 1, "cách ly tenant hỏng")
        with self.assertRaises(truy_van.LoiTruyVan):
            truy_van.chay(spec, TENANT_A, {"cod_tu": 1})   # trường của bảng khác → 400


# ============================================================================
# ĐO HIỆU NĂNG — chạy riêng bằng cờ --hieu-nang
# ============================================================================

def do_hieu_nang(so_don=20_000):
    """Sinh `so_don` đơn rồi đo TRƯỚC / SAU chỉ mục. In số thật, không bình luận."""
    import glob
    tam = tempfile.mkdtemp(prefix="vip-hub-hieunang-")
    os.environ["VIP_HUB_DATA"] = tam
    import subprocess
    subprocess.run([sys.executable, os.path.join(GOC_APP, "migrate.py")],
                   capture_output=True, text=True, check=True,
                   env={**os.environ, "VIP_HUB_DATA": tam})
    duong = glob.glob(os.path.join(tam, "*.db"))[0]
    kn = sqlite3.connect(duong)
    kn.row_factory = sqlite3.Row
    for tid, ma in ((TENANT_A, "ta"), (TENANT_B, "tb")):
        kn.execute("INSERT OR IGNORE INTO tenants (id, code, ten, goi_id, trang_thai, tao_luc)"
                   " VALUES (?,?,?,'free','hoat_dong',?)",
                   (tid, ma, ma, "2026-10-15 00:00:00+0700"))
    kn.execute("INSERT OR IGNORE INTO users (id, ten_dang_nhap, mat_khau_hash, ho_ten,"
               " trang_thai, so_lan_sai, tao_luc) VALUES (1,'thu','x','T','hoat_dong',0,?)",
               ("2026-10-15 00:00:00+0700",))
    tk = {}
    for tid in (TENANT_A, TENANT_B):
        for h in ("vtp", "jt"):
            c = kn.execute("INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong,"
                           " credentials_ma_hoa, credentials_duoi, webhook_ma,"
                           " webhook_secret_ma_hoa, kich_hoat, tao_luc)"
                           " VALUES (?,?,?,'mock','','',?,'',1,?)",
                           (tid, h, h, f"w{tid}{h}", "2026-10-15 00:00:00+0700"))
            tk[(tid, h)] = c.lastrowid
    tt = ["nhap", "da_duyet", "da_gui", "huy"]
    ttg = [None, "lay_hang", "dang_giao", "giao_thanh_cong"]
    dong = []
    for i in range(so_don):
        tid = TENANT_A if i % 4 else TENANT_B            # 75 % A, 25 % B
        h = "vtp" if i % 2 else "jt"
        dong.append((tid, f"D{i:07d}", "S", "090", "1 G", f"Khách {i}", "090", "2 N",
                     f"Hàng {i % 97}", 100 + i % 5000, (i % 500) * 1000, 0,
                     tt[i % 4], ttg[i % 4], tk[(tid, h)], f"MVD{i:07d}", None, i % 7 == 0,
                     f"EXT{i}", 1, f"2026-{1 + i % 10:02d}-{1 + i % 28:02d} 08:00:00+0700",
                     "2026-10-15 09:00:00+0700"))
    kn.executemany(f"INSERT INTO don_hang ({','.join(COT_DON)})"
                   f" VALUES ({','.join('?' * len(COT_DON))})", dong)
    kn.commit()
    kn.execute("ANALYZE")

    CAU = [
        ("lọc khoảng ngày (câu THẬT lớp truy vấn dựng), trang 1",
         "SELECT * FROM don_hang WHERE tenant_id=? AND tao_luc>=? AND tao_luc<?"
         " ORDER BY id DESC LIMIT 50 OFFSET 0",
         (TENANT_A, "2026-03-01", "2026-08-01")),
        ("lọc khoảng ngày kiểu CŨ substr() — để thấy vì sao đổi",
         "SELECT * FROM don_hang WHERE tenant_id=? AND substr(tao_luc,1,10)>=?"
         " AND substr(tao_luc,1,10)<=? ORDER BY id DESC LIMIT 50 OFFSET 0",
         (TENANT_A, "2026-03-01", "2026-07-31")),
        ("lọc ngày + trạng thái giao, trang 1",
         "SELECT * FROM don_hang WHERE tenant_id=? AND tao_luc>=? AND tao_luc<?"
         " AND trang_thai_giao=? ORDER BY id DESC LIMIT 50 OFFSET 0",
         (TENANT_A, "2026-03-01", "2026-08-01", "dang_giao")),
        ("lọc MỘT NGÀY (dải hẹp) — dạng mới, tra được chỉ mục",
         "SELECT * FROM don_hang WHERE tenant_id=? AND tao_luc>=? AND tao_luc<?"
         " ORDER BY id DESC LIMIT 50 OFFSET 0",
         (TENANT_A, "2026-05-07", "2026-05-08")),
        ("lọc MỘT NGÀY (dải hẹp) — dạng cũ substr(), KHÔNG tra được chỉ mục",
         "SELECT * FROM don_hang WHERE tenant_id=? AND substr(tao_luc,1,10)>=?"
         " AND substr(tao_luc,1,10)<=? ORDER BY id DESC LIMIT 50 OFFSET 0",
         (TENANT_A, "2026-05-07", "2026-05-07")),
        ("khoảng COD, sắp xếp theo COD",
         "SELECT * FROM don_hang WHERE tenant_id=? AND cod>=? AND cod<=?"
         " ORDER BY cod DESC, id DESC LIMIT 50 OFFSET 0",
         (TENANT_A, 100000, 300000)),
        ("lọc theo hãng (câu con carrier_accounts)",
         "SELECT * FROM don_hang WHERE tenant_id=? AND carrier_account_id IN"
         " (SELECT id FROM carrier_accounts WHERE tenant_id=? AND hang IN (?))"
         " ORDER BY id DESC LIMIT 50 OFFSET 0",
         (TENANT_A, TENANT_A, "vtp")),
        ("cần đối soát",
         "SELECT * FROM don_hang WHERE tenant_id=? AND can_doi_soat_ket_qua=?"
         " ORDER BY id DESC LIMIT 50 OFFSET 0", (TENANT_A, 1)),
        ("đếm có trần (COUNT trong câu con LIMIT 10001)",
         "SELECT COUNT(*) c FROM (SELECT 1 FROM don_hang WHERE tenant_id=? AND cod>=?"
         " LIMIT 10001)", (TENANT_A, 100000)),
        ("phân trang sâu OFFSET 10000",
         "SELECT * FROM don_hang WHERE tenant_id=? ORDER BY id DESC LIMIT 50 OFFSET 10000",
         (TENANT_A,)),
    ]

    def do(nhan):
        print(f"\n===== {nhan} =====")
        for ten, sql, ts in CAU:
            ke = " | ".join(r["detail"] for r in kn.execute("EXPLAIN QUERY PLAN " + sql, ts))
            t0 = time.perf_counter()
            for _ in range(20):
                kn.execute(sql, ts).fetchall()
            ms = (time.perf_counter() - t0) / 20 * 1000
            print(f"  {ten}\n    {ms:8.3f} ms/lượt (trung bình 20 lượt)\n    PLAN: {ke}")

    print(f"Dữ liệu: {so_don} đơn ({kn.execute('SELECT COUNT(*) FROM don_hang').fetchone()[0]} dòng"
          f" thật), CSDL {os.path.getsize(duong)/1e6:.1f} MB — {duong}")
    do("TRƯỚC chỉ mục G12 (chỉ còn chỉ mục sẵn có: ix_don_tenant, ix_don_mvd, ix_don_extref)")
    for cau in truy_van.DDL_G12Q.split(";"):
        if cau.strip():
            kn.execute(cau)
    kn.commit()
    kn.execute("ANALYZE")
    do("SAU chỉ mục G12 (DDL_G12Q)")
    kn.close()


if __name__ == "__main__":
    if "--hieu-nang" in sys.argv:
        do_hieu_nang()
    else:
        unittest.main(verbosity=2)
