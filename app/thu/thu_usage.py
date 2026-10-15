# Bộ thử SỰ KIỆN SỬ DỤNG + BỘ ĐẾM NGUYÊN TỬ + MÁY TÍNH PHÍ (G08.2, G08.3, G08.4) — AG-02.
# Chạy: python3 app/thu/thu_usage.py
#
# Luật của bộ thử này (CLAUDE.md §12.1):
#
# 1. **Ca "nguyên tử" đo bằng NHIỀU THREAD THẬT đua nhau**, không bằng đọc mã thấy có `UPDATE`.
#    Số luồng qua được là số ĐO ĐƯỢC, dán nguyên vào báo cáo.
# 2. **Thứ dùng để kiểm chứng phải được kiểm trước khi tin.** Lớp `C_KiemChinhPhepDo` dựng
#    một bộ đếm CỐ Ý SAI theo đúng khuôn đọc-rồi-ghi đã vỡ ở đợt 2, rồi đòi phép đo PHẢI
#    thấy nó vượt trần. Nếu ca đó "đạt" thì phép đo ở mục 1 không chứng minh được gì.
# 3. **Dữ liệu mẫu soi dữ liệu thật**: tenant/gói/bộ đếm dựng từ đúng schema và đúng ba gói
#    đang chạy, không dựng bảng giả theo giả định của chính bộ thử.
import os
import sys
import tempfile
import threading
import time
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-g08-usage-")
os.environ["VIP_HUB_DATA"] = _tam

import billing                  # noqa: E402
import csdl                     # noqa: E402
import goi_dich_vu as gdv       # noqa: E402
import quyen                    # noqa: E402
import usage                    # noqa: E402

csdl.mo()
quyen.seed()

# Số luồng đua nhau ở các ca đồng thời. Dán kết quả đo vào báo cáo.
SO_LUONG_DUA = 8
DO_DUOC = {}        # tên ca -> số đo thật, in ra cuối phiên


def tao_tenant(code, goi_id="free"):
    return csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                    (code, "Tenant " + code, goi_id, csdl.bay_gio())).lastrowid


def dua_nhau(ham, so_luong=SO_LUONG_DUA):
    """Cho `so_luong` thread cùng gọi `ham(i)` tại gần như cùng một thời điểm.

    `Barrier` để mọi thread xuất phát cùng lúc — không có nó thì thread đầu xong trước khi
    thread cuối bắt đầu, và ca "đồng thời" chỉ là ca tuần tự đội tên.
    """
    cong = threading.Barrier(so_luong)
    ket_qua, loi = [], []
    khoa = threading.Lock()

    def chay(i):
        cong.wait()
        try:
            r = ham(i)
            with khoa:
                ket_qua.append(r)
        except Exception as e:          # noqa: BLE001 — ghi lại lỗi để ĐẾM, không nuốt
            with khoa:
                loi.append(e)

    ts = [threading.Thread(target=chay, args=(i,)) for i in range(so_luong)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return ket_qua, loi


class A_DoMucDung(unittest.TestCase):
    """G08.2 — đo mức dùng, và nói rõ MỖI con số đến từ bảng nào."""

    def test_a1_moi_con_so_khai_ro_nguon(self):
        t = tao_tenant("u-a1", "basic")
        tt = usage.trang_thai_han_muc(t)
        for loai, d in tt["dong"].items():
            self.assertTrue(d["nguon_do"], f"{loai} không nói đo từ đâu")
            self.assertTrue(d["nguon_tran"], f"{loai} không nói trần từ đâu")

    def test_a2_doc_dung_bo_dem_cua_billing_khong_dem_lai(self):
        t = tao_tenant("u-a2", "basic")
        billing.kiem_va_tang_don(t)
        billing.kiem_va_tang_don(t)
        self.assertEqual(usage.muc_dang_dung(t)["don_thang"], 2)
        self.assertEqual(usage._dem_g08(t, usage.ky_hien_tai(), "don_thang"), 0,
                         "G08 đang đếm SONG SONG với billing — hai bộ đếm sẽ lệch nhau")

    def test_a3_doc_dung_bo_dem_cua_gioi_han(self):
        import gioi_han
        t = tao_tenant("u-a3", "basic")
        gioi_han.dat_truoc_don_nhap(t, 5)
        self.assertEqual(usage.muc_dang_dung(t)["dong_nhap_thang"],
                         gioi_han.da_dung(t)["so_dong"])

    def test_a4_tran_None_la_do_module_khac_quyet_khong_phai_vo_han(self):
        t = tao_tenant("u-a4", "basic")
        d = usage.trang_thai_han_muc(t)["dong"]["dong_nhap_thang"]
        self.assertIsNone(d["tran"])
        self.assertIn("gioi_han", d["nguon_tran"])
        self.assertIsNotNone(usage.trang_thai_han_muc(t)["gioi_han_nhap"],
                             "phải trả kèm số thật của gioi_han, không để giao diện đoán")

    def test_a5_canh_bao_sap_het_han_muc(self):
        t = tao_tenant("u-a5", "free")          # free: 50 đơn/tháng
        csdl.ghi("INSERT INTO usage_thang (tenant_id, thang, so_don, so_ai) VALUES (?,?,?,0)",
                 (t, usage.ky_hien_tai(), 45))  # 45/50 = 90 %
        cb = {c["loai"]: c for c in usage.canh_bao_sap_het(t)}
        self.assertIn("don_thang", cb)
        self.assertEqual(cb["don_thang"]["ty_le_diem_co_ban"], 9000)
        self.assertFalse(cb["don_thang"]["het"])

    def test_a6_ty_le_la_diem_co_ban_khong_thap_phan(self):
        t = tao_tenant("u-a6", "free")
        csdl.ghi("INSERT INTO usage_thang (tenant_id, thang, so_don, so_ai) VALUES (?,?,?,0)",
                 (t, usage.ky_hien_tai(), 1))
        for d in usage.trang_thai_han_muc(t)["dong"].values():
            self.assertIsInstance(d["ty_le_diem_co_ban"], (int, type(None)))


class B_ChanHanMuc(unittest.TestCase):
    """G08.2 — backend chặn. Frontend KHÔNG được tự quyết."""

    def _tenant_co_tran(self, code, tran):
        t = tao_tenant(code, "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", tran, ly_do="bộ thử")
        return t

    def test_b1_het_han_muc_thi_chan(self):
        t = self._tenant_co_tran("u-b1", 3)
        for i in range(3):
            usage.ghi_su_kien(t, "api_thang", 1, f"b1-{i}")
        with self.assertRaises(billing.VuotHanMuc):
            usage.ghi_su_kien(t, "api_thang", 1, "b1-qua")
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 3)

    def test_b2_body_TU_KHAI_han_muc_cao_hon_VAN_bi_chan(self):
        """Ca bắt buộc theo chỉ thị: gọi API với body tự khai hạn mức cao hơn → bị chặn."""
        t = self._tenant_co_tran("u-b2", 2)
        body = {"loai": "api_thang", "so_luong": 1, "idem_key": "b2-1",
                "tran": 10 ** 9, "han_muc_don_thang": 10 ** 9, "api_thang": 10 ** 9,
                "goi_id": "pro", "phien_ban": 99, "bo_dem": 0, "tenant_id": 99999}
        kq = usage.ghi_tu_yeu_cau(t, body)
        self.assertFalse(kq["trung"])
        self.assertEqual(sorted(kq["truong_bi_bo"]),
                         ["api_thang", "bo_dem", "goi_id", "han_muc_don_thang", "phien_ban",
                          "tenant_id", "tran"])
        usage.ghi_tu_yeu_cau(t, dict(body, idem_key="b2-2"))
        with self.assertRaises(billing.VuotHanMuc):
            usage.ghi_tu_yeu_cau(t, dict(body, idem_key="b2-3"))
        self.assertEqual(gdv.tran_cua_loai(t, "api_thang"), 2, "trần thật bị body sửa được!")

    def test_b3_body_khong_doi_duoc_tenant(self):
        """`tenant_id` đến từ PHIÊN. Body khai tenant khác thì bộ đếm tenant kia không đổi."""
        a = self._tenant_co_tran("u-b3a", 5)
        b = self._tenant_co_tran("u-b3b", 5)
        usage.ghi_tu_yeu_cau(a, {"loai": "api_thang", "idem_key": "b3-1", "tenant_id": b})
        self.assertEqual(usage.muc_dang_dung(a)["api_thang"], 1)
        self.assertEqual(usage.muc_dang_dung(b)["api_thang"], 0,
                         "ghi chéo tenant — body đã lái được tenant_id")

    def test_b4_so_luong_phai_duong_khong_dung_de_tru(self):
        t = self._tenant_co_tran("u-b4", 5)
        for xau in (0, -1, -1000):
            with self.assertRaises(usage.LoiUsage):
                usage.ghi_su_kien(t, "api_thang", xau, f"b4-{xau}")

    def test_b5_chan_tran_bo_dem(self):
        """Một sự kiện khổng lồ không được phép làm tràn bộ đếm."""
        t = self._tenant_co_tran("u-b5", gdv.GIA_TRI_KHONG_TRAN)
        with self.assertRaises(usage.LoiUsage):
            usage.ghi_su_kien(t, "api_thang", 10 ** 15, "b5-1")
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 0)

    def test_b6_thieu_idem_key_thi_tu_choi(self):
        t = self._tenant_co_tran("u-b6", 5)
        for xau in (None, "", "   "):
            with self.assertRaises(usage.LoiUsage):
                usage.ghi_su_kien(t, "api_thang", 1, xau)

    def test_b7_loai_la_nguon_la_tenant_la(self):
        t = self._tenant_co_tran("u-b7", 5)
        with self.assertRaises(usage.LoiUsage):
            usage.ghi_su_kien(t, "loai_khong_ton_tai", 1, "b7-1")
        with self.assertRaises(usage.LoiUsage):
            usage.ghi_su_kien(t, "api_thang", 1, "b7-2", nguon="trời ơi")
        with self.assertRaises(usage.LoiUsage):
            usage.ghi_su_kien(999999, "api_thang", 1, "b7-3")

    def test_b8_loai_do_gioi_han_dem_thi_tu_choi_ghi_qua_G08(self):
        """Chặn đúng chỗ dễ sinh bộ đếm thứ hai nhất."""
        t = self._tenant_co_tran("u-b8", 5)
        for loai in ("file_nhap_thang", "dong_nhap_thang", "byte_luu_tru_thang"):
            with self.assertRaises(usage.LoiUsage) as e:
                usage.ghi_su_kien(t, loai, 1, f"b8-{loai}")
            self.assertIn("gioi_han", str(e.exception))

    def test_b9_kiem_han_muc_tu_khai_KHONG_phai_cho_chan(self):
        t = self._tenant_co_tran("u-b9", 1)
        self.assertTrue(usage.kiem_han_muc(t, "api_thang")["con_cho"])
        usage.ghi_su_kien(t, "api_thang", 1, "b9-1")
        self.assertFalse(usage.kiem_han_muc(t, "api_thang")["con_cho"])
        self.assertIn("chốt chặn", usage.kiem_han_muc(t, "api_thang")["ghi_chu"])


class C_KiemChinhPhepDo(unittest.TestCase):
    """Kiểm thứ dùng để kiểm chứng TRƯỚC khi tin nó (CLAUDE.md §12.1 luật 1).

    Lớp này KHÔNG kiểm mã sản phẩm. Nó dựng lại đúng khuôn đọc-rồi-ghi đã vỡ ở đợt 2 và đòi
    phép đo ở lớp D phải THẤY nó vượt trần. Ca này đạt nghĩa là: khi lớp D nói "đúng 1 luồng
    qua", câu đó có giá trị — vì phép đo đã chứng minh được nó bắt được bản sai.
    """

    def test_c1_phep_do_BAT_DUOC_bo_dem_doc_roi_ghi(self):
        t = tao_tenant("u-c1", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 10, ly_do="bộ thử")
        ky = usage.ky_hien_tai()
        csdl.ghi("INSERT INTO bo_dem_dung (tenant_id, ky, loai, so_luong) VALUES (?,?,?,9)",
                 (t, ky, "api_thang"))
        tran = 10

        def cong_sai(_i):
            # KHUÔN SAI — cố ý. Đọc trước, ngủ, rồi ghi không điều kiện.
            r = csdl.mot("SELECT so_luong FROM bo_dem_dung WHERE tenant_id=? AND ky=? AND loai=?",
                         (t, ky, "api_thang"))
            dang = int(r["so_luong"])
            time.sleep(0.05)                       # phóng to khe hở cho đo được chắc chắn
            if dang + 1 > tran:
                raise billing.VuotHanMuc("hết chỗ")
            csdl.ghi("UPDATE bo_dem_dung SET so_luong=so_luong+1"
                     " WHERE tenant_id=? AND ky=? AND loai=?", (t, ky, "api_thang"))
            return True

        ok, loi = dua_nhau(cong_sai)
        cuoi = usage._dem_g08(t, ky, "api_thang")
        DO_DUOC["c1_doc_roi_ghi"] = {"luong": SO_LUONG_DUA, "qua": len(ok),
                                     "bi_chan": len(loi), "bo_dem_cuoi": cuoi, "tran": tran}
        self.assertGreater(len(ok), 1,
                           "khuôn đọc-rồi-ghi mà chỉ 1 luồng qua → phép đo KHÔNG bắt được lỗi,"
                           " nên kết luận 'nguyên tử' ở lớp D vô giá trị")
        self.assertGreater(cuoi, tran, "bộ đếm không vượt trần → phép đo không đủ nhạy")


class D_NguyenTu(unittest.TestCase):
    """G08.3 — usage nguyên tử. Số trong các ca này là số ĐO ĐƯỢC."""

    def test_d1_N_luong_tranh_1_suat_cuoi_dung_1_luong_qua(self):
        t = tao_tenant("u-d1", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 10, ly_do="bộ thử")
        for i in range(9):
            usage.ghi_su_kien(t, "api_thang", 1, f"d1-nap-{i}")
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 9)

        ok, loi = dua_nhau(lambda i: usage.ghi_su_kien(t, "api_thang", 1, f"d1-dua-{i}"))
        cuoi = usage.muc_dang_dung(t)["api_thang"]
        DO_DUOC["d1_tranh_suat_cuoi"] = {"luong": SO_LUONG_DUA, "qua": len(ok),
                                         "bi_chan": len(loi), "bo_dem_cuoi": cuoi, "tran": 10}
        self.assertEqual(len(ok), 1, f"ĐO ĐƯỢC {len(ok)}/{SO_LUONG_DUA} luồng qua — lách hạn mức")
        self.assertEqual(len(loi), SO_LUONG_DUA - 1)
        self.assertTrue(all(isinstance(e, billing.VuotHanMuc) for e in loi))
        self.assertEqual(cuoi, 10, "bộ đếm vượt trần")

    def test_d2_bi_chan_thi_KHONG_de_lai_su_kien_mo_coi(self):
        """Sự kiện đã ghi mà chưa được đếm sẽ khiến lần thử lại bị coi là trùng rồi lặng lẽ
        không thu gì. Vượt trần phải `rollback` cả hai."""
        t = tao_tenant("u-d2", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 1, ly_do="bộ thử")
        usage.ghi_su_kien(t, "api_thang", 1, "d2-1")
        with self.assertRaises(billing.VuotHanMuc):
            usage.ghi_su_kien(t, "api_thang", 1, "d2-2")
        self.assertEqual(
            csdl.mot("SELECT COUNT(*) c FROM su_kien_dung WHERE tenant_id=? AND idem_key=?",
                     (t, "d2-2"))["c"], 0, "còn sự kiện mồ côi")
        # Nâng trần rồi thử lại CÙNG idem_key → phải ghi được, và chỉ một lần
        gdv.dat_han_muc_rieng(t, "api_thang", 5, ly_do="bộ thử nâng")
        kq = usage.ghi_su_kien(t, "api_thang", 1, "d2-2")
        self.assertFalse(kq["trung"])
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 2)

    def test_d3_su_kien_trung_KHONG_thu_phi_lan_hai(self):
        t = tao_tenant("u-d3", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 100, ly_do="bộ thử")
        a = usage.ghi_su_kien(t, "api_thang", 5, "d3-mot-lan")
        self.assertFalse(a["trung"])
        for _ in range(4):                      # worker thử lại 4 lần
            b = usage.ghi_su_kien(t, "api_thang", 5, "d3-mot-lan")
            self.assertTrue(b["trung"])
            self.assertEqual(b["so_luong"], 0)
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 5, "đã thu phí nhiều lần")
        self.assertEqual(
            csdl.mot("SELECT COUNT(*) c FROM su_kien_dung WHERE tenant_id=? AND idem_key=?",
                     (t, "d3-mot-lan"))["c"], 1)

    def test_d4_N_luong_cung_idem_key_chi_1_lan_duoc_tinh(self):
        """Worker thử lại ĐỒNG THỜI — chặn trùng phải là ràng buộc CSDL, không phải if."""
        t = tao_tenant("u-d4", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 1000, ly_do="bộ thử")
        ok, loi = dua_nhau(lambda i: usage.ghi_su_kien(t, "api_thang", 1, "d4-CUNG-MOT-KHOA"))
        tinh = [r for r in ok if not r["trung"]]
        cuoi = usage.muc_dang_dung(t)["api_thang"]
        DO_DUOC["d4_cung_idem_key"] = {"luong": SO_LUONG_DUA, "duoc_tinh": len(tinh),
                                       "bao_trung": len(ok) - len(tinh), "loi": len(loi),
                                       "bo_dem_cuoi": cuoi}
        self.assertEqual(len(tinh), 1, f"ĐO ĐƯỢC {len(tinh)} lượt được tính — thu phí hai lần")
        self.assertEqual(cuoi, 1)
        self.assertEqual(len(loi), 0)

    def test_d5_idem_key_trung_nhau_GIUA_hai_tenant_la_hop_le(self):
        """UNIQUE là (tenant_id, idem_key). Hai tenant dùng cùng khoá không được chặn nhau."""
        a = tao_tenant("u-d5a", "basic")
        b = tao_tenant("u-d5b", "basic")
        for t in (a, b):
            gdv.kich_hoat(t)
            gdv.dat_han_muc_rieng(t, "api_thang", 10, ly_do="bộ thử")
        self.assertFalse(usage.ghi_su_kien(a, "api_thang", 1, "KHOA-CHUNG")["trung"])
        self.assertFalse(usage.ghi_su_kien(b, "api_thang", 1, "KHOA-CHUNG")["trung"])
        self.assertEqual(usage.muc_dang_dung(a)["api_thang"], 1)
        self.assertEqual(usage.muc_dang_dung(b)["api_thang"], 1)

    def test_d6_khong_cap_nhat_cheo_tenant_khi_chay_dong_thoi(self):
        a = tao_tenant("u-d6a", "basic")
        b = tao_tenant("u-d6b", "basic")
        for t in (a, b):
            gdv.kich_hoat(t)
            gdv.dat_han_muc_rieng(t, "api_thang", 1000, ly_do="bộ thử")
        ok, loi = dua_nhau(lambda i: usage.ghi_su_kien(a if i % 2 == 0 else b, "api_thang", 1,
                                                       f"d6-{i}"), so_luong=10)
        da, db = usage.muc_dang_dung(a)["api_thang"], usage.muc_dang_dung(b)["api_thang"]
        DO_DUOC["d6_cheo_tenant"] = {"luong": 10, "qua": len(ok), "loi": len(loi),
                                     "a": da, "b": db}
        self.assertEqual((da, db), (5, 5), "bộ đếm chéo tenant")

    def test_d7_don_thang_di_qua_billing_khong_sinh_bo_dem_thu_hai(self):
        t = tao_tenant("u-d7", "free")              # free: 50 đơn
        gdv.kich_hoat(t, "free", 1)
        kq = usage.ghi_su_kien(t, "don_thang", 1, "d7-don-1", tham_chieu="don:1")
        self.assertEqual(kq["nguon_dem"], "billing")
        self.assertEqual(billing.usage_hien_tai(t)["so_don"], 1)
        self.assertEqual(usage._dem_g08(t, usage.ky_hien_tai(), "don_thang"), 0)

    def test_d8_don_thang_het_han_muc_thi_chan_va_khong_de_su_kien_mo_coi(self):
        t = tao_tenant("u-d8", "free")
        gdv.kich_hoat(t, "free", 1)
        csdl.ghi("INSERT INTO usage_thang (tenant_id, thang, so_don, so_ai) VALUES (?,?,50,0)",
                 (t, usage.ky_hien_tai()))          # đã dùng hết 50/50
        with self.assertRaises(billing.VuotHanMuc):
            usage.ghi_su_kien(t, "don_thang", 1, "d8-qua")
        self.assertEqual(
            csdl.mot("SELECT COUNT(*) c FROM su_kien_dung WHERE tenant_id=? AND idem_key=?",
                     (t, "d8-qua"))["c"], 0, "sự kiện mồ côi — lần thử lại sẽ bị coi là trùng")
        self.assertEqual(billing.usage_hien_tai(t)["so_don"], 50)

    def test_d9_don_thang_N_luong_tranh_1_suat_cuoi(self):
        """Đo lại chốt chặn của `billing.kiem_va_tang_don` qua đường G08."""
        t = tao_tenant("u-d9", "free")
        gdv.kich_hoat(t, "free", 1)
        csdl.ghi("INSERT INTO usage_thang (tenant_id, thang, so_don, so_ai) VALUES (?,?,49,0)",
                 (t, usage.ky_hien_tai()))
        ok, loi = dua_nhau(lambda i: usage.ghi_su_kien(t, "don_thang", 1, f"d9-{i}"))
        cuoi = billing.usage_hien_tai(t)["so_don"]
        DO_DUOC["d9_don_thang_suat_cuoi"] = {"luong": SO_LUONG_DUA, "qua": len(ok),
                                             "bi_chan": len(loi), "so_don_cuoi": cuoi,
                                             "tran": 50}
        self.assertEqual(len(ok), 1, f"ĐO ĐƯỢC {len(ok)}/{SO_LUONG_DUA} luồng qua")
        self.assertEqual(cuoi, 50)

    def test_d10_doi_soat_su_kien_voi_bo_dem(self):
        t = tao_tenant("u-d10", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 100, ly_do="bộ thử")
        for i in range(3):
            usage.ghi_su_kien(t, "api_thang", 2, f"d10-{i}")
        ds = usage.doi_soat_su_kien(t)
        self.assertEqual(ds["so_sanh_duoc"]["api_thang"], {"so_su_kien": 6, "bo_dem": 6, "lech": 0})
        self.assertIn("don_thang", ds["ngoai_pham_vi"],
                      "phải nói rõ loại nào NGOÀI phạm vi đối chiếu được")

    def test_d11_doi_soat_THAY_duoc_lech_khong_tu_sua(self):
        t = tao_tenant("u-d11", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 100, ly_do="bộ thử")
        usage.ghi_su_kien(t, "api_thang", 1, "d11-1")
        csdl.ghi("UPDATE bo_dem_dung SET so_luong=so_luong+7 WHERE tenant_id=? AND loai=?",
                 (t, "api_thang"))                  # giả lập lệch
        ds = usage.doi_soat_su_kien(t)
        self.assertEqual(ds["so_sanh_duoc"]["api_thang"]["lech"], -7)
        self.assertEqual(usage._dem_g08(t, usage.ky_hien_tai(), "api_thang"), 8,
                         "đối chiếu đã TỰ SỬA — che mất nguyên nhân")


class D2_DoBillingAI(unittest.TestCase):
    """ĐO (không phán) chốt chặn lượt AI của `app/billing.py` — file AG-00 giữ.

    `billing.kiem_va_tang_ai` hiện vẫn theo khuôn ĐỌC-RỒI-GHI (`usage_hien_tai` rồi `_tang`),
    đúng khuôn đã vỡ ở đợt 2 với `kiem_va_tang_don`. Ca này KHÔNG khẳng định nó đúng hay sai —
    nó ĐO và in số ra để báo cáo, vì sửa `billing.py` là việc của AG-00. Khẳng định chỉ được
    nói trong đúng phạm vi đã đo (CLAUDE.md §12.1 luật 3).

    Ca này chỉ đòi hai điều không thể sai theo cách nào: có ít nhất một luồng qua, và bộ đếm
    không tụt. Số vượt trần (nếu có) nằm ở `DO_DUOC`.
    """

    def test_d12_do_so_luong_lot_qua_cua_kiem_va_tang_ai(self):
        t = tao_tenant("u-d12", "free")             # free: 20 lượt AI
        gdv.kich_hoat(t, "free", 1)
        csdl.ghi("INSERT INTO usage_thang (tenant_id, thang, so_don, so_ai) VALUES (?,?,0,19)",
                 (t, usage.ky_hien_tai()))
        ok, loi = dua_nhau(lambda i: usage.ghi_su_kien(t, "ai_thang", 1, f"d12-{i}"))
        cuoi = billing.usage_hien_tai(t)["so_ai"]
        DO_DUOC["d12_ai_thang_suat_cuoi"] = {
            "luong": SO_LUONG_DUA, "qua": len(ok), "bi_chan": len(loi), "so_ai_cuoi": cuoi,
            "tran": 20, "vuot_tran": max(0, cuoi - 20),
            "ket_luan": "billing.kiem_va_tang_ai còn đọc-rồi-ghi — bản vá đề xuất ở G08_FINAL_REPORT"}
        self.assertGreaterEqual(len(ok), 1)
        self.assertGreaterEqual(cuoi, 19)

    def test_d13_su_kien_ai_bi_chan_khong_de_lai_su_kien_mo_coi(self):
        t = tao_tenant("u-d13", "free")
        gdv.kich_hoat(t, "free", 1)
        csdl.ghi("INSERT INTO usage_thang (tenant_id, thang, so_don, so_ai) VALUES (?,?,0,20)",
                 (t, usage.ky_hien_tai()))
        with self.assertRaises(billing.VuotHanMuc):
            usage.ghi_su_kien(t, "ai_thang", 1, "d13-qua")
        self.assertEqual(
            csdl.mot("SELECT COUNT(*) c FROM su_kien_dung WHERE tenant_id=? AND idem_key=?",
                     (t, "d13-qua"))["c"], 0)


class E_TamNgung(unittest.TestCase):
    def test_e1_dang_ky_tam_ngung_thi_chan_thao_tac_co_tinh_phi(self):
        t = tao_tenant("u-e1", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 100, ly_do="bộ thử")
        usage.ghi_su_kien(t, "api_thang", 1, "e1-truoc")
        gdv.tam_ngung(t, "thử e1")
        with self.assertRaises(usage.DangKyTamNgung) as e:
            usage.ghi_su_kien(t, "api_thang", 1, "e1-trong")
        self.assertEqual(e.exception.ma, 403, "tạm ngưng không được ra 402 'cần trả tiền'")
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 1)
        gdv.mo_lai(t)
        usage.ghi_su_kien(t, "api_thang", 1, "e1-sau")
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 2)

    def test_e2_tam_ngung_KHONG_xoa_du_lieu(self):
        t = tao_tenant("u-e2", "basic")
        gdv.kich_hoat(t)
        gdv.dat_han_muc_rieng(t, "api_thang", 100, ly_do="bộ thử")
        usage.ghi_su_kien(t, "api_thang", 3, "e2-1")
        gdv.tam_ngung(t)
        self.assertEqual(len(usage.su_kien_cua_ky(t)), 1)
        self.assertEqual(usage.muc_dang_dung(t)["api_thang"], 3)


class F_TinhPhi(unittest.TestCase):
    """G08.4 — máy tính phí. CHỈ DỰ THẢO nội bộ."""

    def test_f1_ca_ky_mot_goi_thi_bang_dung_gia_goi(self):
        t = tao_tenant("u-f1", "basic")
        gdv.kich_hoat(t, "basic", 1)
        p = usage.tinh_phi(t)
        self.assertEqual(p["tien_goi_dong"], 299000)
        self.assertEqual(p["tong_dong"], 299000)
        self.assertEqual(p["phan_du_bo_dong"], 0)
        self.assertFalse(p["prorate"])
        self.assertIsInstance(p["tong_dong"], int)

    def test_f2_prorate_chia_theo_ngay_va_khong_lam_mat_dong_nao(self):
        """Đổi gói giữa kỳ → hai chặng, tiền chia theo số ngày từng gói có hiệu lực."""
        t = tao_tenant("u-f2", "free")
        gdv.kich_hoat(t, "free", 1)
        ky = usage.ky_hien_tai()
        # Dựng mốc đổi gói vào NGÀY 11 của kỳ (bộ thử tự dựng dữ liệu của chính nó).
        csdl.ghi("UPDATE dang_ky_lich_su SET luc=? WHERE tenant_id=? AND loai='nang_goi'",
                 (f"{ky}-11 09:00:00+0700", t))
        gdv.doi_goi(t, "pro", 1)
        csdl.ghi("UPDATE dang_ky_lich_su SET luc=? WHERE tenant_id=? AND loai='nang_goi'",
                 (f"{ky}-11 09:00:00+0700", t))
        p = usage.tinh_phi(t)
        self.assertTrue(p["prorate"])
        self.assertEqual(len(p["chang"]), 2)
        c1, c2 = p["chang"]
        self.assertEqual((c1["goi_id"], c1["ngay_bat_dau"], c1["so_ngay"]), ("free", 1, 10))
        self.assertEqual((c2["goi_id"], c2["ngay_bat_dau"]), ("pro", 11))
        self.assertEqual(c1["so_ngay"] + c2["so_ngay"], p["so_ngay_ky"],
                         "tổng số ngày các chặng không bằng số ngày trong kỳ")
        self.assertEqual(sum(c["so_tien_dong"] for c in p["chang"]), p["tien_goi_dong"])
        # Bất biến tiền: tổng (tiền*ngày_kỳ + dư) phải khớp từng chặng
        for c in p["chang"]:
            self.assertEqual(c["so_tien_dong"] * p["so_ngay_ky"] + c["phan_du"],
                             c["gia_thang_dong"] * c["so_ngay"])
        self.assertLess(p["tong_dong"], 999000, "trả cả tháng gói pro dù chỉ dùng hơn nửa kỳ")

    def test_f3_khong_thu_phi_vuot_va_noi_ro_vi_sao(self):
        t = tao_tenant("u-f3", "basic")
        gdv.kich_hoat(t)
        p = usage.tinh_phi(t)
        self.assertEqual(p["tien_vuot_dong"], 0)
        self.assertTrue(p["ly_do_khong_thu_vuot"])

    def test_f4_du_thao_mang_nhan_KHONG_PHAI_HOA_DON(self):
        t = tao_tenant("u-f4", "basic")
        gdv.kich_hoat(t)
        dt = usage.lap_du_thao(t)
        self.assertEqual(dt["la_du_thao"], 1)
        self.assertIn("KHÔNG PHẢI HOÁ ĐƠN", dt["nhan_phap_ly"])
        self.assertIn("không trừ tiền", dt["nhan_phap_ly"])
        self.assertEqual(dt["tong_dong"], 299000)

    def test_f5_lap_du_thao_hai_lan_KHONG_thu_phi_hai_lan(self):
        t = tao_tenant("u-f5", "basic")
        gdv.kich_hoat(t)
        a = usage.lap_du_thao(t)
        self.assertFalse(a["trung"])
        for _ in range(3):
            b = usage.lap_du_thao(t)
            self.assertTrue(b["trung"])
            self.assertEqual(b["id"], a["id"])
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM du_thao_hoa_don WHERE tenant_id=?",
                                  (t,))["c"], 1)

    def test_f6_tinh_phi_KHONG_cheo_tenant(self):
        a = tao_tenant("u-f6a", "basic")
        b = tao_tenant("u-f6b", "free")
        for t in (a, b):
            gdv.kich_hoat(t)
            gdv.dat_han_muc_rieng(t, "api_thang", 1000, ly_do="bộ thử")
        for i in range(5):
            usage.ghi_su_kien(a, "api_thang", 1, f"f6-{i}")
        pa, pb = usage.tinh_phi(a), usage.tinh_phi(b)
        self.assertEqual(pa["muc_dung"]["api_thang"], 5)
        self.assertEqual(pb["muc_dung"]["api_thang"], 0, "mức dùng của A lọt vào phí của B")
        self.assertEqual(pa["tong_dong"], 299000)
        self.assertEqual(pb["tong_dong"], 0)
        dta, dtb = usage.lap_du_thao(a), usage.lap_du_thao(b)
        self.assertEqual(dta["tenant_id"], a)
        self.assertEqual(dtb["tenant_id"], b)
        self.assertNotEqual(dta["id"], dtb["id"])

    def test_f7_ky_tinh_phi_mo_roi_dong(self):
        t = tao_tenant("u-f7", "basic")
        gdv.kich_hoat(t)
        self.assertEqual(usage.mo_ky(t)["trang_thai"], "mo")
        self.assertEqual(usage.dong_ky(t)["trang_thai"], "dong")
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM ky_tinh_phi WHERE tenant_id=?",
                                  (t,))["c"], 1)

    def test_f8_nhat_ky_tinh_phi_ghi_du_viec(self):
        t = tao_tenant("u-f8", "basic")
        gdv.kich_hoat(t)
        gdv.doi_goi(t, "pro", 1)
        usage.lap_du_thao(t)
        hd = [r["hanh_dong"] for r in gdv.nhat_ky(t)]
        for can in ("kich_hoat_dang_ky", "nang_goi", "lap_du_thao"):
            self.assertIn(can, hd)

    def test_f9_bao_cao_dung_du_bay_phan(self):
        t = tao_tenant("u-f9", "basic")
        gdv.kich_hoat(t)
        bc = usage.bao_cao_dung(t)
        for k in ("ky", "han_muc", "su_kien", "doi_soat", "canh_bao", "phi_du_kien", "du_thao"):
            self.assertIn(k, bc)
        self.assertTrue(bc["phi_du_kien"]["la_du_thao"])

    def test_f10_tien_tren_du_thao_la_INTEGER(self):
        for r in csdl.nhieu("PRAGMA table_info(du_thao_hoa_don)"):
            if r["name"].endswith("_dong"):
                self.assertEqual(r["type"].upper(), "INTEGER", f"{r['name']} không INTEGER")


def in_so_do():
    print("\n===== SỐ ĐO THẬT (dán vào báo cáo, không ghi lại từ trí nhớ) =====")
    for ten, d in DO_DUOC.items():
        print(f"  {ten}: {d}")


if __name__ == "__main__":
    try:
        # GIỮ kết quả rồi THOÁT theo nó. `exit=False` một mình làm bộ thử
        # LUÔN thoát 0 kể cả khi có ca hỏng — cổng chặn hồi quy mất tác dụng,
        # và nó không báo gì cả (§12.2: hỏng im lặng).
        _kq = unittest.main(verbosity=2, exit=False)
    finally:
        in_so_do()
    sys.exit(0 if _kq.result.wasSuccessful() else 1)
