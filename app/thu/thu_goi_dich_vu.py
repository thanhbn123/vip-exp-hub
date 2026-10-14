# Bộ thử GÓI DỊCH VỤ + PHIÊN BẢN GÓI + ĐĂNG KÝ (G08.1, G08.2, một phần G08.4) — AG-02.
# Chạy: python3 app/thu/thu_goi_dich_vu.py
#
# Nguyên tắc (CLAUDE.md §12.1): mỗi khẳng định do MỘT phép đo thật tạo ra. Không grep mã rồi
# kết luận hành vi. Đặc biệt ba ca canh những chỗ dễ hỏng im lặng nhất:
#   - `test_a4` đo rằng phát hành phiên bản mới KHÔNG đổi hạn mức tenant đang chạy. Đây là
#     chỗ cả thiết kế đứng hay đổ: nếu đọc hạn mức từ `goi_dich_vu` thì ca này hỏng.
#   - `test_f*` canh DDL và canh ba dòng gói đang chạy — đổi tên gói thì bộ thử phải hỏng,
#     không để lọt rồi phát hiện khi tenant thật không đăng nhập được.
#   - `test_e*` canh bất biến chia tiền: không một đồng nào được biến mất im lặng.
import os
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-g08-goi-")
os.environ["VIP_HUB_DATA"] = _tam

import csdl                     # noqa: E402
import cau_hinh                 # noqa: E402
import goi_dich_vu as gdv       # noqa: E402
import quyen                    # noqa: E402
import usage                    # noqa: E402

csdl.mo()
quyen.seed()


def tao_tenant(code, goi_id="free"):
    return csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                    (code, "Tenant " + code, goi_id, csdl.bay_gio())).lastrowid


def tao_nhan_vien(tenant_id, ten_dang_nhap, role="TENANT_STAFF"):
    u = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                 " VALUES (?,?,?,?)", (ten_dang_nhap, "x", ten_dang_nhap, csdl.bay_gio())).lastrowid
    csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
             " VALUES (?,?,?,?)", (u, tenant_id, role, csdl.bay_gio()))
    return u


class A_PhienBanGoi(unittest.TestCase):
    """Phiên bản gói — hạn mức đã thoả thuận KHÔNG đổi hồi tố."""

    def test_a1_ba_goi_dang_chay_duoc_chup_phien_ban_1(self):
        for ma in ("free", "basic", "pro"):
            a = gdv.doc_phien_ban(ma, 1)
            g = csdl.mot("SELECT * FROM goi_dich_vu WHERE id=?", (ma,))
            self.assertEqual(a["gia_thang_dong"], g["gia_thang"])
            self.assertEqual(a["han_muc_don_thang"], g["han_muc_don_thang"])
            self.assertEqual(a["so_nhan_vien"], g["so_nhan_vien"])

    def test_a2_tien_la_integer_dong(self):
        """§16: mọi số tiền là INTEGER đồng. REAL lọt vào là một đồng lệch trong đối soát."""
        for r in csdl.nhieu("PRAGMA table_info(goi_phien_ban)"):
            if "gia" in r["name"] or "dong" in r["name"]:
                self.assertEqual(r["type"].upper(), "INTEGER",
                                 f"cột tiền {r['name']} không phải INTEGER")
        for a in gdv.danh_sach_goi():
            self.assertIsInstance(a["gia_thang_dong"], int)

    def test_a3_phat_hanh_phien_ban_tang_so(self):
        gdv.phat_hanh_phien_ban("basic", {"han_muc_don_thang": 1500}, ghi_chu="thử a3")
        self.assertGreaterEqual(gdv.phien_ban_moi_nhat("basic"), 2)
        self.assertEqual(gdv.doc_phien_ban("basic", 1)["han_muc_don_thang"], 1000,
                         "phiên bản 1 bị SỬA — ảnh chụp phải bất biến")

    def test_a4_phat_hanh_phien_ban_KHONG_doi_han_muc_tenant_dang_chay(self):
        """Ca quan trọng nhất của G08.1. Tenant ghim v1 thì v2 không chạm tới họ."""
        t = tao_tenant("g08-a4", "basic")
        pb_dau = gdv.phien_ban_moi_nhat("basic")
        gdv.kich_hoat(t, "basic", pb_dau)
        truoc = gdv.han_muc_hieu_luc(t)
        gdv.phat_hanh_phien_ban("basic", {"han_muc_don_thang": 99999, "so_nhan_vien": 99},
                                gia_thang_dong=777000, ghi_chu="thử a4")
        sau = gdv.han_muc_hieu_luc(t)
        self.assertEqual(sau["phien_ban"], pb_dau, "tenant bị nhảy phiên bản — đổi hồi tố!")
        self.assertEqual(sau["tran"]["don_thang"]["gia_tri"],
                         truoc["tran"]["don_thang"]["gia_tri"])
        self.assertEqual(sau["gia_thang_dong"], truoc["gia_thang_dong"], "giá bị đổi hồi tố")
        self.assertNotEqual(gdv.phien_ban_moi_nhat("basic"), pb_dau)

    def test_a5_chuyen_phien_ban_la_hanh_dong_rieng_co_ghi_vet(self):
        t = tao_tenant("g08-a5", "basic")
        gdv.kich_hoat(t, "basic", 1)
        gdv.phat_hanh_phien_ban("basic", {"han_muc_don_thang": 1234}, ghi_chu="thử a5")
        pb_moi = gdv.phien_ban_moi_nhat("basic")
        gdv.chuyen_phien_ban(t, pb_moi, ly_do="thử a5", cho_phep_vuot=True)
        self.assertEqual(gdv.han_muc_hieu_luc(t)["phien_ban"], pb_moi)
        ls = [r for r in gdv.lich_su(t) if r["loai"] == "doi_phien_ban"]
        self.assertTrue(ls, "đổi phiên bản mà không có dòng lịch sử")

    def test_a6_han_muc_la_bi_tu_choi_khong_bo_qua_im_lang(self):
        with self.assertRaises(gdv.LoiGoi):
            gdv.phat_hanh_phien_ban("free", {"han_muc_don_thanggg": 10})

    def test_a7_goi_khong_ton_tai(self):
        with self.assertRaises(gdv.LoiGoi):
            gdv.phat_hanh_phien_ban("enterprise", {"han_muc_don_thang": 1})

    def test_a8_them_goi_moi_khong_pha_ba_goi_cu(self):
        """§19: muốn thêm gói thì THÊM dòng. Ca này dựng gói thứ tư và kiểm ba gói cũ còn nguyên."""
        truoc = {r["id"]: dict(r) for r in csdl.nhieu("SELECT * FROM goi_dich_vu")}
        csdl.ghi("INSERT OR IGNORE INTO goi_dich_vu (id,ten,gia_thang,han_muc_don_thang,"
                 "han_muc_ai_thang,so_nhan_vien,so_tai_khoan_hang)"
                 " VALUES ('enterprise','Doanh nghiệp',2999000,100000,50000,100,50)")
        gdv.nap_lai_bang()
        gdv._dam_bao_bang()
        self.assertEqual(gdv.doc_phien_ban("enterprise", 1)["gia_thang_dong"], 2999000)
        for ma in ("free", "basic", "pro"):
            sau = dict(csdl.mot("SELECT * FROM goi_dich_vu WHERE id=?", (ma,)))
            self.assertEqual(sau, truoc[ma], f"gói đang chạy {ma} bị sửa")


class B_DangKy(unittest.TestCase):
    def test_b1_kich_hoat_khong_tao_dong_thu_hai(self):
        t = tao_tenant("g08-b1", "basic")
        a = gdv.kich_hoat(t)
        b = gdv.kich_hoat(t)
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM dang_ky WHERE tenant_id=?", (t,))["c"], 1)

    def test_b2_tenant_chua_dang_ky_van_doc_duoc_han_muc(self):
        """Tenant có từ trước đợt này không được tự dưng mất hạn mức."""
        t = tao_tenant("g08-b2", "pro")
        hm = gdv.han_muc_hieu_luc(t)
        self.assertFalse(hm["tu_dang_ky"])
        self.assertEqual(hm["goi_id"], "pro")
        self.assertEqual(hm["trang_thai"], "chua_dang_ky")
        self.assertTrue(gdv.dang_hoat_dong(t), "tenant cũ bị khoá oan")

    def test_b3_tam_ngung_roi_mo_lai(self):
        t = tao_tenant("g08-b3", "basic")
        gdv.kich_hoat(t)
        gdv.tam_ngung(t, "thử b3")
        self.assertFalse(gdv.dang_hoat_dong(t))
        gdv.mo_lai(t, "thử b3")
        self.assertTrue(gdv.dang_hoat_dong(t))
        loai = [r["loai"] for r in gdv.lich_su(t)]
        self.assertIn("tam_ngung", loai)
        self.assertIn("mo_lai", loai)

    def test_b4_mot_tenant_mot_dang_ky_song_rang_buoc_o_csdl(self):
        import sqlite3
        t = tao_tenant("g08-b4", "basic")
        gdv.kich_hoat(t)
        with self.assertRaises(sqlite3.IntegrityError):
            csdl.ghi("INSERT INTO dang_ky (tenant_id, goi_id, goi_phien_ban, ky_bat_dau, tao_luc)"
                     " VALUES (?,?,1,?,?)", (t, "pro", csdl.thang_nay(), csdl.bay_gio()))


class C_DoiGoi(unittest.TestCase):
    def test_c1_nang_goi(self):
        t = tao_tenant("g08-c1", "free")
        gdv.kich_hoat(t, "free", 1)
        kq = gdv.doi_goi(t, "pro", ly_do="thử c1")
        self.assertEqual(kq["loai"], "nang_goi")
        self.assertEqual(gdv.han_muc_hieu_luc(t)["goi_id"], "pro")
        self.assertEqual(gdv.tran_cua_loai(t, "don_thang"), 10000)

    def test_c2_ha_goi_khi_dang_vuot_thi_BI_CHAN_va_noi_ro_vuot_gi(self):
        t = tao_tenant("g08-c2", "pro")
        gdv.kich_hoat(t, "pro", 1)
        for i in range(3):
            tao_nhan_vien(t, f"c2-nv{i}")          # free chỉ cho 2 nhân viên
        with self.assertRaises(gdv.HaGoiVuotHanMuc) as e:
            gdv.doi_goi(t, "free")
        self.assertIn("nhan_vien", e.exception.vuot)
        self.assertEqual(e.exception.vuot["nhan_vien"]["dang_dung"], 3)
        self.assertEqual(gdv.han_muc_hieu_luc(t)["goi_id"], "pro", "đã hạ gói dù bị chặn")

    def test_c3_ha_goi_co_phep_vuot_GIU_NGUYEN_du_lieu(self):
        t = tao_tenant("g08-c3", "pro")
        gdv.kich_hoat(t, "pro", 1)
        for i in range(4):
            tao_nhan_vien(t, f"c3-nv{i}")
        so_truoc = usage.muc_dang_dung(t)["nhan_vien"]
        kq = gdv.doi_goi(t, "free", cho_phep_vuot=True, ly_do="thử c3")
        self.assertEqual(kq["loai"], "ha_goi")
        self.assertEqual(usage.muc_dang_dung(t)["nhan_vien"], so_truoc,
                         "hạ gói đã XOÁ dữ liệu vượt hạn mức — cấm")
        ls = [r for r in gdv.lich_su(t) if r["loai"] == "ha_goi"][-1]
        self.assertIsNotNone(ls["vuot_json"], "phần vượt không được ghi lại")
        self.assertIn("nhan_vien", ls["vuot_json"])

    def test_c4_ha_goi_roi_thi_them_moi_bi_chan(self):
        """Dữ liệu cũ giữ nguyên, nhưng THÊM MỚI thì chặn theo trần gói mới."""
        import billing
        t = tao_tenant("g08-c4", "pro")
        gdv.kich_hoat(t, "pro", 1)
        for i in range(4):
            tao_nhan_vien(t, f"c4-nv{i}")
        gdv.doi_goi(t, "free", cho_phep_vuot=True)
        with self.assertRaises(billing.VuotHanMuc):
            billing.kiem_han_muc_nhan_vien(t)

    def test_c4b_doi_goi_dong_bo_voi_cho_billing_thuc_su_doc(self):
        """Chống lệch: `billing` lấy gói qua `tenants.goi_id`, G08 qua `dang_ky`.

        Hai nơi phải nói cùng một câu, nếu không thì đổi gói trên giấy mà chốt chặn thật vẫn
        dùng gói cũ — không có thông báo lỗi nào để ai kịp thấy.
        """
        import billing
        t = tao_tenant("g08-c4b", "free")
        gdv.kich_hoat(t, "free", 1)
        gdv.doi_goi(t, "pro", 1)
        self.assertEqual(billing.goi_cua_tenant(t)["id"], "pro")
        self.assertEqual(gdv.han_muc_hieu_luc(t)["goi_id"], "pro")
        ds = gdv.doi_soat_goi(t)
        self.assertFalse(ds["lech"], f"lệch gói giữa hai nguồn: {ds}")

    def test_c4c_doi_soat_PHAT_HIEN_duoc_duong_doi_goi_khong_qua_G08(self):
        """Route platform đang `UPDATE tenants SET goi_id` trực tiếp. Phép đo phải THẤY."""
        t = tao_tenant("g08-c4c", "free")
        gdv.kich_hoat(t, "free", 1)
        csdl.ghi("UPDATE tenants SET goi_id='pro' WHERE id=?", (t,))     # giả lập route cũ
        ds = gdv.doi_soat_goi(t)
        self.assertTrue(ds["lech"], "đối chiếu KHÔNG thấy lệch — phép đo vô dụng")
        self.assertEqual((ds["tenants_goi_id"], ds["dang_ky_goi_id"]), ("pro", "free"))

    def test_c5_doi_sang_dung_goi_dang_o_thi_tu_choi(self):
        t = tao_tenant("g08-c5", "basic")
        dk = gdv.kich_hoat(t)
        with self.assertRaises(gdv.LoiGoi):
            gdv.doi_goi(t, dk["goi_id"], dk["goi_phien_ban"])

    def test_c6_lich_su_doi_goi_day_du(self):
        t = tao_tenant("g08-c6", "free")
        gdv.kich_hoat(t, "free", 1)
        gdv.doi_goi(t, "basic", 1)
        gdv.doi_goi(t, "pro", 1)
        ls = gdv.lich_su(t)
        self.assertEqual([r["loai"] for r in ls], ["kich_hoat", "nang_goi", "nang_goi"])
        self.assertEqual(ls[1]["tu_goi"], "free")
        self.assertEqual(ls[1]["den_goi"], "basic")
        self.assertEqual(ls[1]["tu_gia_dong"], 0)
        self.assertEqual(ls[1]["den_gia_dong"], 299000)


class D_HanMuc(unittest.TestCase):
    def test_d1_moi_loai_han_muc_noi_ro_bo_dem_nam_dau(self):
        """Chống "hai bộ đếm cho một việc": mỗi loại phải khai đúng một nguồn đếm."""
        hop_le = {"billing", "gioi_han", "dem_truc_tiep", "g08"}
        for loai, m in gdv.LOAI_HAN_MUC.items():
            self.assertIn(m["nguon_dem"], hop_le, f"{loai} khai nguồn đếm lạ")
            self.assertIn(loai, usage.NGUON_DO, f"{loai} không nói rõ đo từ đâu")
        self.assertEqual(gdv.LOAI_HAN_MUC["file_nhap_thang"]["nguon_dem"], "gioi_han")
        self.assertEqual(gdv.LOAI_HAN_MUC["dong_nhap_thang"]["nguon_dem"], "gioi_han")
        self.assertEqual(gdv.LOAI_HAN_MUC["don_thang"]["nguon_dem"], "billing")

    def test_d2_du_tam_loai_han_muc_theo_chi_thi(self):
        for loai in ("nhan_vien", "tai_khoan_hang", "don_thang", "file_nhap_thang",
                     "dong_nhap_thang", "byte_luu_tru_thang", "ai_thang", "api_thang"):
            self.assertIn(loai, gdv.LOAI_HAN_MUC)

    def test_d3_han_muc_rieng_de_len_han_muc_goi(self):
        t = tao_tenant("g08-d3", "free")
        gdv.kich_hoat(t, "free", 1)
        self.assertEqual(gdv.tran_cua_loai(t, "don_thang"), 50)
        gdv.dat_han_muc_rieng(t, "don_thang", 123, ly_do="thử d3")
        self.assertEqual(gdv.tran_cua_loai(t, "don_thang"), 123)
        self.assertEqual(gdv.han_muc_hieu_luc(t)["tran"]["don_thang"]["nguon"], "han_muc_rieng")

    def test_d4_loai_do_gioi_han_quyet_thi_G08_khong_tra_tran(self):
        """Không bịa một con số cho thứ module khác đang quyết."""
        t = tao_tenant("g08-d4", "basic")
        with self.assertRaises(gdv.LoiGoi):
            gdv.tran_cua_loai(t, "dong_nhap_thang")
        self.assertIsNone(gdv.han_muc_hieu_luc(t)["tran"]["dong_nhap_thang"]["gia_tri"])

    def test_d5_loai_la_bi_tu_choi(self):
        t = tao_tenant("g08-d5", "basic")
        with self.assertRaises(gdv.LoiGoi):
            gdv.tran_cua_loai(t, "khong_co_loai_nay")
        with self.assertRaises(gdv.LoiGoi):
            gdv.dat_han_muc_rieng(t, "khong_co_loai_nay", 5)

    def test_d6_han_muc_rieng_am_bi_tu_choi(self):
        t = tao_tenant("g08-d6", "basic")
        with self.assertRaises(gdv.LoiGoi):
            gdv.dat_han_muc_rieng(t, "don_thang", -1)

    def test_d7_so_0_la_khong_ap_tran_khong_phai_tran_0(self):
        t = tao_tenant("g08-d7", "free")
        gdv.kich_hoat(t, "free", 1)
        self.assertEqual(gdv.doc_phien_ban("free", 1)["han_muc_api_thang"], 0)
        self.assertEqual(gdv.tran_cua_loai(t, "api_thang"), gdv.GIA_TRI_KHONG_TRAN)


class E_ChiaTien(unittest.TestCase):
    """§16: dùng `//`, phần dư phải có chỗ đi, tổng các phần bằng đúng số ban đầu."""

    def test_e1_chia_theo_ngay_bat_bien(self):
        for gia in (0, 1, 299000, 999000, 2999000):
            for ngay_ky in (28, 29, 30, 31):
                for ngay in range(0, ngay_ky + 1):
                    tien, du = gdv.chia_tien_theo_ngay(gia, ngay, ngay_ky)
                    self.assertEqual(tien * ngay_ky + du, gia * ngay,
                                     f"mất tiền: gia={gia} ngay={ngay}/{ngay_ky}")
                    self.assertIsInstance(tien, int)
                    self.assertTrue(0 <= du < ngay_ky)

    def test_e2_ca_ky_mot_goi_thi_dung_bang_gia_goi(self):
        for ngay_ky in (28, 30, 31):
            tien, du = gdv.chia_tien_theo_ngay(299000, ngay_ky, ngay_ky)
            self.assertEqual((tien, du), (299000, 0))

    def test_e3_chia_deu_khong_lam_mat_dong_nao(self):
        for tong in (0, 1, 7, 299000, 999999):
            for n in (1, 2, 3, 7, 12):
                phan = gdv.chia_deu(tong, n)
                self.assertEqual(sum(phan), tong, f"tổng lệch: {tong}/{n}")
                self.assertEqual(len(phan), n)
                self.assertLessEqual(max(phan) - min(phan), 1)

    def test_e4_so_phan_0_bi_tu_choi(self):
        with self.assertRaises(gdv.LoiGoi):
            gdv.chia_deu(100, 0)
        with self.assertRaises(gdv.LoiGoi):
            gdv.chia_tien_theo_ngay(100, 1, 0)


class F_DDL(unittest.TestCase):
    def test_f1_ddl_khong_ALTER_khong_DROP_khong_DELETE(self):
        d = gdv.DDL_G08.upper()
        for tu in ("ALTER", "DROP", "DELETE", "UPDATE ", "INSERT "):
            self.assertNotIn(tu, d, f"DDL_G08 có {tu} — chỉ được CREATE IF NOT EXISTS")
        self.assertEqual(d.count("CREATE TABLE IF NOT EXISTS"), d.count("CREATE TABLE"))
        self.assertEqual(d.count("CREATE INDEX IF NOT EXISTS")
                         + d.count("CREATE UNIQUE INDEX IF NOT EXISTS"), d.count("CREATE INDEX")
                         + d.count("CREATE UNIQUE INDEX"))

    def test_f2_moi_bang_G08_da_duoc_tao_that(self):
        gdv._dam_bao_bang()
        for b in ("goi_phien_ban", "dang_ky", "dang_ky_lich_su", "han_muc_rieng", "su_kien_dung",
                  "bo_dem_dung", "ky_tinh_phi", "du_thao_hoa_don", "nhat_ky_tinh_phi"):
            self.assertIsNotNone(
                csdl.mot("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (b,)),
                f"bảng {b} chưa được tạo")

    def test_f3_khong_cham_bang_dang_chay(self):
        """DDL_G08 không nhắc tên bảng đang chạy ở vị trí CREATE/ALTER."""
        for b in ("goi_dich_vu", "tenants", "usage_thang", "han_muc_nhap_thang", "don_hang"):
            self.assertNotIn(f"CREATE TABLE IF NOT EXISTS {b}", gdv.DDL_G08)
            self.assertNotIn(f"ALTER TABLE {b}", gdv.DDL_G08)

    def test_f4_ba_ma_goi_dang_chay_con_nguyen(self):
        ma = [r["id"] for r in csdl.nhieu("SELECT id FROM goi_dich_vu ORDER BY id")]
        for can in ("free", "basic", "pro"):
            self.assertIn(can, ma, "MÃ GÓI ĐANG CHẠY BỊ ĐỔI/XOÁ — phá mọi tenant")
        self.assertEqual([g["id"] for g in cau_hinh.GOI_MAC_DINH], ["free", "basic", "pro"])

    def test_f5_UNIQUE_idem_key_va_UNIQUE_ky_la_rang_buoc_csdl(self):
        """§20: chặn trùng ở tầng CSDL, không phải phép kiểm trong mã."""
        ds = [r["sql"] for r in csdl.nhieu(
            "SELECT sql FROM sqlite_master WHERE name IN ('su_kien_dung','du_thao_hoa_don')")]
        noi = " ".join(ds)
        self.assertIn("UNIQUE (tenant_id, idem_key)", noi)
        self.assertIn("UNIQUE (tenant_id, ky)", noi)

    def test_f6_loi_goi_khong_ke_thua_VuotHanMuc_cua_billing(self):
        """Kế thừa là vô tình bật thông điệp 402 "cần trả tiền" mà không ai quyết định."""
        import billing
        self.assertFalse(issubclass(gdv.LoiGoi, billing.VuotHanMuc))
        self.assertFalse(issubclass(usage.LoiUsage, billing.VuotHanMuc))


if __name__ == "__main__":
    unittest.main(verbosity=2)
