# Bộ thử G05 — Import engine (AG-04). File RIÊNG của AG-04, không đụng thu_saas.py / thu_g03.py.
# Chạy: python3 app/thu/thu_nhap_file.py
#
# Gọi TRỰC TIẾP tầng nhap_file + CSDL tạm (không dựng server HTTP) để ca thử nào hỏng
# thì biết ngay hỏng ở tầng nào — không phải đoán qua mã HTTP.
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile
import zlib

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-thu-import-")
os.environ["VIP_HUB_DATA"] = _tam

import csdl        # noqa: E402
import don_hang    # noqa: E402
import nhap_file   # noqa: E402
import quyen       # noqa: E402

TIEU_DE = "Người nhận,SĐT,Địa chỉ,Sản phẩm,Trọng lượng,Thu hộ,Ghi chú"
NGUOI_GUI = {"ten": "Shop Thử", "sdt": "0901111111", "dia_chi": "1 Đường Thử"}


def csv_bytes(*hang):
    return ("\n".join((TIEU_DE,) + hang) + "\n").encode()


def xlsx_bytes(cac_dong, them=None, ss_tho=None):
    """Dựng file XLSX tối thiểu bằng stdlib. cac_dong: list[list[str]] — mọi ô là inlineStr
    nên không phụ thuộc sharedStrings."""
    hang_xml = []
    for ri, hang in enumerate(cac_dong, 1):
        o = []
        for ci, gt in enumerate(hang):
            ten_cot = chr(ord("A") + ci)
            gt = str(gt).replace("&", "&amp;").replace("<", "&lt;")
            o.append(f'<c r="{ten_cot}{ri}" t="inlineStr"><is><t>{gt}</t></is></c>')
        hang_xml.append(f'<row r="{ri}">' + "".join(o) + "</row>")
    sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
             'spreadsheetml/2006/main"><sheetData>' + "".join(hang_xml) + "</sheetData></worksheet>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "<Types/>")
        if ss_tho is not None:
            z.writestr("xl/sharedStrings.xml", ss_tho)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
        for ten, noi_dung in (them or {}).items():
            z.writestr(ten, noi_dung)
    return buf.getvalue()


def pdf_scan_bytes():
    """PDF không có toán tử Tj/TJ nào → mô phỏng bản scan (chỉ có ảnh)."""
    return (b"%PDF-1.4\n1 0 obj<</Type/Page>>endobj\nstream\n"
            + zlib.compress(b"q 612 0 0 792 0 0 cm /Im0 Do Q\n")
            + b"\nendstream\n%%EOF\n")


def pdf_text_bytes(*cac_dong):
    # mỗi dòng là MỘT toán tử Tj — parser nối các chuỗi Tj bằng ký tự xuống dòng thật
    tho = ("BT " + " ".join(f"({d}) Tj" for d in cac_dong) + " ET").encode("latin-1")
    return b"%PDF-1.4\nstream\n" + tho + b"\nendstream\n%%EOF\n"


class ThuNhapFile(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        csdl.mo()
        quyen.seed()
        cls.t = {}
        for ma, ten in (("A", "Tenant A"), ("B", "Tenant B")):
            tid = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                           (ma, ten, "pro", csdl.bay_gio())).lastrowid
            uid = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                           " VALUES (?,?,?,?)", (f"u{ma}", "x", f"User {ma}", csdl.bay_gio())).lastrowid
            csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
                     " VALUES (?,?,?,?)", (uid, tid, "TENANT_OWNER", csdl.bay_gio()))
            cls.t[ma] = (tid, uid)

    def nap(self, ma_tenant, ten_file, du_lieu):
        tid, uid = self.t[ma_tenant]
        return nhap_file.tao_batch(tid, uid, ten_file, du_lieu), tid, uid

    def tt_batch(self, batch_id):
        return nhap_file.trang_thai_batch(
            csdl.mot("SELECT * FROM import_batch WHERE id=?", (batch_id,)))

    def dong_cua(self, batch_id):
        return csdl.nhieu("SELECT * FROM import_dong WHERE batch_id=? ORDER BY stt", (batch_id,))

    # ===== 1. ánh xạ cột phong phú =====
    def test_01_anh_xa_cot_bien_the(self):
        for ten, mong in (("SĐT", "nguoi_nhan_sdt"), ("SDT", "nguoi_nhan_sdt"),
                          ("Phone", "nguoi_nhan_sdt"), ("Mobile", "nguoi_nhan_sdt"),
                          ("Điện thoại", "nguoi_nhan_sdt"), ("So dien thoai", "nguoi_nhan_sdt"),
                          ("Tel", "nguoi_nhan_sdt"),
                          ("Người nhận", "nguoi_nhan_ten"), ("Ten nguoi nhan", "nguoi_nhan_ten"),
                          ("Recipient", "nguoi_nhan_ten"), ("Customer Name", "nguoi_nhan_ten"),
                          ("Địa chỉ", "nguoi_nhan_dia_chi"), ("Dia chi", "nguoi_nhan_dia_chi"),
                          ("Address", "nguoi_nhan_dia_chi"),
                          ("Sản phẩm", "hang_hoa"), ("San pham", "hang_hoa"),
                          ("Tên hàng", "hang_hoa"), ("Product", "hang_hoa"),
                          ("SL", "so_luong"), ("Số lượng", "so_luong"),
                          ("Qty", "so_luong"), ("Quantity", "so_luong"),
                          ("KL", "khoi_luong_gram"), ("Khối lượng", "khoi_luong_gram"),
                          ("Trọng lượng", "khoi_luong_gram"), ("Weight", "khoi_luong_gram"),
                          ("COD", "cod"), ("Thu hộ", "cod"), ("Tiền thu hộ", "cod"),
                          ("Ghi chú", "ghi_chu"), ("Note", "ghi_chu"), ("Notes", "ghi_chu")):
            self.assertEqual(nhap_file.anh_xa_cot([ten]).get(0), mong, f"cột {ten!r}")
        # bỏ dấu + hoa thường + khoảng trắng đều về MỘT khóa
        self.assertEqual(nhap_file.anh_xa_cot(["  SỐ   ĐIỆN THOẠI  "]).get(0), "nguoi_nhan_sdt")
        self.assertEqual(nhap_file.anh_xa_cot(["tRọNg_LƯợNg"]).get(0), "khoi_luong_gram")

    # ===== 2. luồng CSV đúng + thứ tự trạng thái =====
    def test_02_luong_csv_va_thu_tu_trang_thai(self):
        bid, tid, uid = self.nap("A", "don.csv", csv_bytes(
            "Lê Một,0904444444,\"4 Hẻm A, HN\",Áo,500,150000,",
            "Trần Hai,0905555555,5 Hẻm B,Quần,600,0,giao giờ hành chính"))
        self.assertEqual(self.tt_batch(bid), "READY")
        dong = self.dong_cua(bid)
        self.assertEqual([d["trang_thai"] for d in dong], ["VALID", "VALID"])
        kq = nhap_file.duyet_batch(tid, uid, bid, [d["id"] for d in dong], NGUOI_GUI)
        self.assertEqual((kq["SUCCESS"], kq["FAILED"]), (2, 0), kq)
        self.assertEqual(kq["trang_thai_batch"], "COMPLETED")
        self.assertEqual(self.tt_batch(bid), "COMPLETED")
        # duyệt LẠI → idempotency: không nhân đôi đơn
        so_don = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (tid,))["c"]
        kq2 = nhap_file.duyet_batch(tid, uid, bid, [d["id"] for d in dong], NGUOI_GUI)
        self.assertEqual(kq2["bo_qua"], 2, "duyệt lại không được tạo thêm đơn")
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (tid,))["c"],
                         so_don, "duyệt lại ĐÃ nhân đôi đơn!")

    def test_03_khong_duyet_duoc_batch_FAILED(self):
        """Máy trạng thái phải CHẶN, không im lặng cho qua."""
        bid, tid, uid = self.nap("A", "ok.csv", csv_bytes("Lê Ba,0906666666,6 Hẻm,Áo,500,0,"))
        nhap_file.chuyen_batch(tid, bid, "FAILED", "thử")
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            nhap_file.duyet_batch(tid, uid, bid, [], NGUOI_GUI)
        self.assertIn("FAILED", str(e.exception))
        # chuyển lùi/nhảy bậc cũng bị chặn
        bid2, tid2, _ = self.nap("A", "ok2.csv", csv_bytes("Lê Tư,0907777777,7 Hẻm,Áo,500,0,"))
        with self.assertRaises(don_hang.LoiNghiepVu):
            nhap_file.chuyen_batch(tid2, bid2, "PROCESSING")   # READY → PROCESSING: không có đường
        self.assertEqual(self.tt_batch(bid2), "READY", "chuyển sai mà vẫn ghi đè trạng thái!")

    def test_04_doc_duoc_trang_thai_cu(self):
        """Dữ liệu cũ trong CSDL phải di cư được — mã chịu được giá trị cũ."""
        bid, tid, uid = self.nap("A", "cu.csv", csv_bytes("Lê Năm,0908888888,8 Hẻm,Áo,500,0,"))
        csdl.ghi("UPDATE import_batch SET trang_thai='moi' WHERE id=?", (bid,))
        self.assertEqual(self.tt_batch(bid), "READY")
        kq = nhap_file.duyet_batch(tid, uid, bid, [d["id"] for d in self.dong_cua(bid)], NGUOI_GUI)
        self.assertEqual(kq["SUCCESS"], 1, kq)
        for cu, moi in (("da_duyet_mot_phan", "PARTIAL_FAILED"), ("xong", "COMPLETED")):
            csdl.ghi("UPDATE import_batch SET trang_thai=? WHERE id=?", (cu, bid))
            self.assertEqual(self.tt_batch(bid), moi)

    # ===== 3. trường sai =====
    def test_05_truong_sai_thanh_INVALID(self):
        bid, tid, uid = self.nap("A", "loi.csv", csv_bytes(
            ",012,Thiếu tên,Hàng lỗi,-5,-1,",
            "Lê Sáu,0909999999,9 Hẻm,Áo,abc,0,"))
        dong = self.dong_cua(bid)
        self.assertEqual([d["trang_thai"] for d in dong], ["INVALID", "INVALID"])
        self.assertIn("thiếu tên người nhận", dong[0]["loi"])
        self.assertIn("SĐT phải 10 số", dong[0]["loi"])
        self.assertIn("cân nặng phải > 0", dong[0]["loi"])
        self.assertIn("COD không được âm", dong[0]["loi"])
        self.assertIn("cân nặng không phải số", dong[1]["loi"])
        # duyệt dòng INVALID → bỏ qua, KHÔNG tạo đơn
        kq = nhap_file.duyet_batch(tid, uid, bid, [d["id"] for d in dong], NGUOI_GUI)
        self.assertEqual((kq["SUCCESS"], kq["bo_qua"]), (0, 2), kq)
        self.assertEqual(kq["trang_thai_batch"], "PARTIAL_FAILED")
        # sửa rồi duyệt lại → chạy được
        nhap_file.sua_dong(tid, dong[0]["id"], {"nguoi_nhan_ten": "Đã Sửa",
                                                "nguoi_nhan_sdt": "0910000000",
                                                "khoi_luong_gram": "300", "cod": "0"})
        kq2 = nhap_file.duyet_batch(tid, uid, bid, [dong[0]["id"]], NGUOI_GUI)
        self.assertEqual(kq2["SUCCESS"], 1, kq2)

    # ===== 4. formula injection =====
    def test_06_formula_injection_phat_hien(self):
        bid, tid, uid = self.nap("A", "cong-thuc.csv", csv_bytes(
            '"=cmd|\'/C calc\'!A0",0911111111,10 Hẻm,Áo,500,0,',
            'Lê Bảy,0912222222,11 Hẻm,"@SUM(A1:A9)",500,0,',
            'Lê Tám,0913333333,12 Hẻm,Áo,500,0,=HYPERLINK(http://xau)',
            'Lê Chín,0914444444,13 Hẻm,Áo,500,-0,giá -5 nghìn'))
        dong = self.dong_cua(bid)
        self.assertEqual([d["trang_thai"] for d in dong[:3]],
                         ["NEEDS_REVIEW", "NEEDS_REVIEW", "NEEDS_REVIEW"],
                         [dict(d) for d in dong])
        for d in dong[:3]:
            self.assertIn("công thức", d["loi"])
        # dòng 4 KHÔNG báo động giả: '-0' là số, 'giá -5 nghìn' không bắt đầu bằng ký tự nguy hiểm
        self.assertEqual(dong[3]["trang_thai"], "VALID", dict(dong[3]))
        # NEEDS_REVIEW không tự tạo đơn
        kq = nhap_file.duyet_batch(tid, uid, bid, [d["id"] for d in dong], NGUOI_GUI)
        self.assertEqual(kq["SUCCESS"], 1, kq)      # chỉ dòng 4
        self.assertEqual(kq["bo_qua"], 3, kq)
        # người xác nhận thì mới đi tiếp
        nhap_file.xac_nhan_dong(tid, uid, dong[0]["id"])
        self.assertEqual(csdl.mot("SELECT trang_thai t FROM import_dong WHERE id=?",
                                  (dong[0]["id"],))["t"], "READY")
        kq2 = nhap_file.duyet_batch(tid, uid, bid, [dong[0]["id"]], NGUOI_GUI)
        self.assertEqual(kq2["SUCCESS"], 1, kq2)

    def test_07_formula_injection_lam_sach_khi_xuat(self):
        """Phát hiện là một nửa. Nửa còn lại: file XUẤT ra không được chứa công thức sống."""
        for xau in ("=1+1", "+1+1", "@SUM(A1)", "=cmd|'/C calc'!A0", "\t=1+1", "\r=1+1"):
            self.assertTrue(nhap_file.rui_ro_cong_thuc(xau), f"bỏ sót {xau!r}")
            sach = nhap_file.lam_sach_o_xuat(xau)
            self.assertTrue(sach.startswith("'"), f"{xau!r} → {sach!r} chưa được vô hiệu")
            self.assertNotIn("\r", sach)
            self.assertNotIn("\n", sach)
        for lanh in ("-5", "-1.5", "+7", "0912222222", "Áo thun", "", "150000"):
            self.assertFalse(nhap_file.rui_ro_cong_thuc(lanh), f"báo động giả {lanh!r}")
            self.assertEqual(nhap_file.lam_sach_o_xuat(lanh), lanh)

        bid, tid, uid = self.nap("A", "xuat.csv", csv_bytes(
            '"=1+1",0915555555,14 Hẻm,"@A1",500,0,"=WEBSERVICE(""http://xau"")"'))
        ra = nhap_file.xuat_csv(tid, bid)
        for o in ra.split(","):
            than = o.strip('"').lstrip(" \t")
            self.assertFalse(than[:1] in nhap_file.KY_TU_CONG_THUC and
                             not nhap_file._la_so(than),
                             f"ô {o!r} trong file xuất vẫn là công thức sống")
        self.assertIn("'=1+1", ra)
        self.assertIn("'@A1", ra)
        self.assertIn("'=WEBSERVICE", ra)
        # cách ly tenant: tenant B không xuất được batch của A
        with self.assertRaises(don_hang.LoiNghiepVu):
            nhap_file.xuat_csv(self.t["B"][0], bid)

    # ===== 5. dòng trùng =====
    def test_08_dong_trung_thanh_NEEDS_REVIEW_khong_tu_loai(self):
        bid, tid, uid = self.nap("A", "trung.csv", csv_bytes(
            "Lê Mười,0916666666,15 Hẻm Trùng,Áo thun,500,0,",
            "LÊ MƯỜI,0916666666,15 hẻm trùng,ÁO THUN,500,0,lần 2",
            "Lê Khác,0917777777,16 Hẻm,Áo thun,500,0,"))
        dong = self.dong_cua(bid)
        self.assertEqual([d["trang_thai"] for d in dong],
                         ["VALID", "NEEDS_REVIEW", "VALID"], [dict(d) for d in dong])
        self.assertIn("trùng dòng 1", dong[1]["loi"])
        # KHÔNG tự loại: dòng vẫn còn trong CSDL
        self.assertEqual(len(dong), 3)

    # ===== 6. XLSX =====
    def test_09_xlsx_tot_va_hong(self):
        bid, tid, uid = self.nap("A", "don.xlsx", xlsx_bytes([
            ["Người nhận", "SĐT", "Địa chỉ", "Sản phẩm", "KL", "COD"],
            ["Trần Xlsx", "0918888888", "17 Ngõ X", "Áo", "800", "0"]]))
        self.assertEqual(self.tt_batch(bid), "READY")
        self.assertEqual([d["trang_thai"] for d in self.dong_cua(bid)], ["VALID"])

        # không phải zip → lỗi rõ, batch FAILED (dấu vết còn lại, không treo im lặng)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "rac.xlsx", b"khong phai zip")
        self.assertIn("zip", str(e.exception).lower())
        b = csdl.mot("SELECT * FROM import_batch WHERE ten_file='rac.xlsx'")
        self.assertEqual(nhap_file.trang_thai_batch(b), "FAILED")
        self.assertTrue(b["loi"], "batch FAILED mà không ghi lý do")

        # zip hợp lệ nhưng XML hỏng
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("xl/worksheets/sheet1.xml", "<worksheet><khong-dong")
        with self.assertRaises(don_hang.LoiNghiepVu):
            self.nap("A", "xml-hong.xlsx", buf.getvalue())

        # zip không có worksheet
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("[Content_Types].xml", "<Types/>")
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "trong.xlsx", buf.getvalue())
        self.assertIn("worksheet", str(e.exception))

    def test_10_csv_hong_va_dinh_dang_la(self):
        # chỉ có tiêu đề, không có dữ liệu
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "trong.csv", (TIEU_DE + "\n").encode())
        self.assertIn("không có dữ liệu", str(e.exception))
        # không nhận diện được cột bắt buộc
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "la-cot.csv", b"abc,def\n1,2\n")
        self.assertIn("không nhận diện được cột", str(e.exception))
        # định dạng lạ
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "don.docx", b"PK rac")
        self.assertIn("chưa hỗ trợ", str(e.exception))
        # byte rác không phải UTF-8 → không nổ, chỉ là cột không nhận diện được
        with self.assertRaises(don_hang.LoiNghiepVu):
            self.nap("A", "rac.csv", bytes(range(256)))

    # ===== 7. PDF =====
    def test_11_pdf_scan_thanh_UNSUPPORTED(self):
        with self.assertRaises(nhap_file.LoiKhongHoTro) as e:
            self.nap("A", "scan.pdf", pdf_scan_bytes())
        self.assertIn("scan", str(e.exception).lower())
        b = csdl.mot("SELECT * FROM import_batch WHERE ten_file='scan.pdf'")
        self.assertEqual(nhap_file.trang_thai_batch(b), "FAILED")
        dong = self.dong_cua(b["id"])
        self.assertEqual([d["trang_thai"] for d in dong], ["UNSUPPORTED"],
                         "PDF scan phải để lại dòng UNSUPPORTED làm dấu vết")
        self.assertIn("scan", dong[0]["loi"].lower())
        # dòng UNSUPPORTED không sửa được, không duyệt được
        tid, uid = self.t["A"]
        with self.assertRaises(don_hang.LoiNghiepVu):
            nhap_file.sua_dong(tid, dong[0]["id"], {"nguoi_nhan_ten": "Bịa"})
        with self.assertRaises(don_hang.LoiNghiepVu):
            nhap_file.duyet_batch(tid, uid, b["id"], [dong[0]["id"]], NGUOI_GUI)

    def test_12_pdf_text_doc_duoc(self):
        # PDF chuỗi văn bản là latin-1 → dùng tiêu đề không dấu, vẫn phải khớp ánh xạ cột
        bid, tid, uid = self.nap("A", "text.pdf", pdf_text_bytes(
            "Ten nguoi nhan;So dien thoai;Dia chi;San pham;KL;COD",
            "Le Pdf;0919999999;18 Ngo P;Ao;700;0"))
        self.assertEqual(self.tt_batch(bid), "READY")
        self.assertEqual([d["trang_thai"] for d in self.dong_cua(bid)], ["VALID"])

    # ===== 8. giới hạn tài nguyên =====
    def test_13_vuot_gioi_han_dung_luong(self):
        to = b"x" * (nhap_file.GIOI_HAN_BYTE_FILE + 1)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "to.csv", to)
        self.assertEqual(e.exception.ma, 413)
        self.assertIn("vượt giới hạn", str(e.exception))
        # chặn TRƯỚC khi tạo batch → không có batch rác
        self.assertIsNone(csdl.mot("SELECT 1 FROM import_batch WHERE ten_file='to.csv'"))

    def test_14_vuot_gioi_han_so_dong(self):
        hang = ["Lê N,0910000001,1 Hẻm,Áo,500,0,"] * (nhap_file.GIOI_HAN_SO_DONG + 5)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "nhieu-dong.csv", csv_bytes(*hang))
        self.assertEqual(e.exception.ma, 413)
        self.assertIn("dòng", str(e.exception))
        self.assertEqual(
            nhap_file.trang_thai_batch(
                csdl.mot("SELECT * FROM import_batch WHERE ten_file='nhieu-dong.csv'")), "FAILED")

    def test_15_vuot_gioi_han_o_va_do_dai_o(self):
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "o-dai.csv", csv_bytes(
                "Lê D," + "0910000002," + "A" * (nhap_file.GIOI_HAN_DAI_O + 10) + ",Áo,500,0,"))
        self.assertEqual(e.exception.ma, 413)
        nhieu_o = ",".join(["x"] * (nhap_file.GIOI_HAN_SO_O_MOI_DONG + 5))
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "nhieu-o.csv", csv_bytes(nhieu_o))
        self.assertEqual(e.exception.ma, 413)

    def test_16_zip_bomb(self):
        """Thành viên zip khai file_size khổng lồ với compress_size tí xíu → chặn theo
        TỈ LỆ và theo TỔNG, không cần giải nén thật."""
        bom = zlib.compress(b"\0" * (200 * 1024 * 1024), 9)
        self.assertLess(len(bom), 1024 * 1024, "bom nén chưa đủ nhỏ, ca thử vô nghĩa")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/worksheets/sheet1.xml", b"\0" * (200 * 1024 * 1024))
        du_lieu = buf.getvalue()
        self.assertLess(len(du_lieu), nhap_file.GIOI_HAN_BYTE_FILE,
                        "file nén phải lọt giới hạn dung lượng, nếu không ca thử đo sai chốt")
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "bom.xlsx", du_lieu)
        self.assertEqual(e.exception.ma, 413)
        self.assertIn("zip bomb", str(e.exception))

    def test_17_path_traversal_trong_zip(self):
        for ten_xau in ("../../../../etc/passwd", "/etc/passwd", "C:\\Windows\\win.ini",
                        "xl/../../../ngoai.xml"):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                z.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")
                z.writestr(ten_xau, "x")
            with self.assertRaises(don_hang.LoiNghiepVu) as e:
                self.nap("A", "traversal.xlsx", buf.getvalue())
            self.assertIn("traversal", str(e.exception), f"bỏ sót tên {ten_xau!r}")

    def test_18_xml_entity_expansion(self):
        """billion-laughs: expat CÓ expand entity nội bộ → phải chặn ở tầng byte."""
        bil = ('<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
               '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">'
               '<!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">'
               ']><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
               "<sheetData><row r=\"1\"><c r=\"A1\" t=\"inlineStr\"><is><t>&lol3;</t></is></c>"
               "</row></sheetData></worksheet>")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/worksheets/sheet1.xml", bil)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "billion.xlsx", buf.getvalue())
        self.assertIn("ENTITY", str(e.exception))
        # sharedStrings cũng phải chặn, không chỉ sheet
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("xl/sharedStrings.xml", bil)
            z.writestr("xl/worksheets/sheet1.xml", "<worksheet/>")
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "billion2.xlsx", buf.getvalue())
        self.assertIn("ENTITY", str(e.exception))

    def test_19_xlsx_sharedstrings_chi_so_ngoai_khoang(self):
        sheet = ('<?xml version="1.0"?><worksheet xmlns="http://schemas.openxmlformats.org/'
                 'spreadsheetml/2006/main"><sheetData><row r="1">'
                 '<c r="A1" t="s"><v>999</v></c></row></sheetData></worksheet>')
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("xl/sharedStrings.xml",
                       '<?xml version="1.0"?><sst xmlns="http://schemas.openxmlformats.org/'
                       'spreadsheetml/2006/main"><si><t>a</t></si></sst>')
            z.writestr("xl/worksheets/sheet1.xml", sheet)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            self.nap("A", "ss-xau.xlsx", buf.getvalue())
        self.assertIn("sharedStrings", str(e.exception))

    # ===== 9. cách ly tenant =====
    def test_20_cach_ly_batch_giua_hai_tenant(self):
        bid_a, tid_a, uid_a = self.nap("A", "cua-a.csv", csv_bytes(
            "Lê A,0920000000,20 Hẻm A,Áo,500,0,"))
        tid_b, uid_b = self.t["B"]
        dong_a = self.dong_cua(bid_a)
        # B không đọc/sửa/duyệt/xuất được batch của A
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            nhap_file.duyet_batch(tid_b, uid_b, bid_a, [d["id"] for d in dong_a], NGUOI_GUI)
        self.assertEqual(e.exception.ma, 404)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            nhap_file.sua_dong(tid_b, dong_a[0]["id"], {"nguoi_nhan_ten": "B sửa"})
        self.assertEqual(e.exception.ma, 404)
        with self.assertRaises(don_hang.LoiNghiepVu):
            nhap_file.xac_nhan_dong(tid_b, uid_b, dong_a[0]["id"])
        with self.assertRaises(don_hang.LoiNghiepVu):
            nhap_file.xuat_csv(tid_b, bid_a)
        # dữ liệu của A không đổi
        self.assertEqual(json.loads(self.dong_cua(bid_a)[0]["du_lieu_json"])["nguoi_nhan_ten"],
                         "Lê A")
        # A duyệt được, và đơn sinh ra thuộc A
        kq = nhap_file.duyet_batch(tid_a, uid_a, bid_a, [d["id"] for d in dong_a], NGUOI_GUI)
        self.assertEqual(kq["SUCCESS"], 1, kq)
        don_id = self.dong_cua(bid_a)[0]["don_id"]
        self.assertIsNotNone(don_hang.lay_don(tid_a, don_id))
        self.assertIsNone(don_hang.lay_don(tid_b, don_id), "đơn của A lọt sang B!")

    # ===== 10. OrderDraft: chỉ sinh đơn NHÁP =====
    def test_21_chi_sinh_don_nhap(self):
        bid, tid, uid = self.nap("A", "nhap.csv", csv_bytes(
            "Lê Nháp,0921111111,21 Hẻm,Áo,500,25000,"))
        dong = self.dong_cua(bid)
        nhap_file.duyet_batch(tid, uid, bid, [d["id"] for d in dong], NGUOI_GUI)
        don = don_hang.lay_don(tid, self.dong_cua(bid)[0]["don_id"])
        self.assertEqual(don["trang_thai"], "nhap", "import không được tạo đơn đã gửi hãng")
        self.assertIsNone(don["ma_van_don"])
        self.assertIsNone(don["carrier_account_id"])
        self.assertEqual(don["cod"], 25000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
