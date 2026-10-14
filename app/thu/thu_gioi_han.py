# Bộ thử GIỚI HẠN TẦN SUẤT (S04) + HẠN MỨC NHẬP FILE (S05) — AG-01.
# Chạy: python3 app/thu/thu_gioi_han.py
#
# Nguyên tắc (CLAUDE.md §12.1): mỗi khẳng định do MỘT phép đo thật tạo ra. Không grep mã rồi
# kết luận hành vi. Đặc biệt:
#   - Ca "nguyên tử" đo bằng NHIỀU THREAD thật đua nhau, không bằng đọc mã thấy có `UPDATE`.
#   - Ca "không tin X-Forwarded-For" đo bằng cách gọi hàm với header giả, không bằng đọc comment.
#   - Ca "trần không lỏng hơn nhap_file" so HẰNG SỐ THẬT của hai module, để bên kia siết lại mà
#     bên này quên thì bộ thử hỏng — không lệch im lặng.
import os
import sys
import tempfile
import threading
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-gioihan-")
os.environ["VIP_HUB_DATA"] = _tam

import csdl        # noqa: E402
import gioi_han    # noqa: E402
import quyen       # noqa: E402


def _tao_tenant(code, goi_id="free"):
    return csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                    (code, "Tenant " + code, goi_id, csdl.bay_gio())).lastrowid


class A_TrustedProxy(unittest.TestCase):
    """Không tin `X-Forwarded-For` vô điều kiện. Mặc định: chỉ dùng địa chỉ TCP thật."""

    def tearDown(self):
        gioi_han.PROXY_TIN_CAY = gioi_han._doc_mang(gioi_han.PROXY_TIN_CAY_THO)

    def test_a1_mac_dinh_khong_tin_header(self):
        """Mặc định `PROXY_TIN_CAY` rỗng → header bị bỏ qua hoàn toàn."""
        self.assertEqual(gioi_han.PROXY_TIN_CAY, (),
                         "mặc định PHẢI là không tin proxy nào")
        for gia in ("1.1.1.1", "127.0.0.1", "::1", "rác không phải IP", "1.1.1.1, 2.2.2.2"):
            self.assertEqual(gioi_han.dia_chi_that("9.9.9.9", {"x-forwarded-for": gia}), "9.9.9.9",
                             f"header {gia!r} đã lọt vào kết quả — giới hạn theo IP thành vô nghĩa")

    def test_a2_chi_tin_khi_dia_chi_tcp_la_proxy_da_khai(self):
        gioi_han.PROXY_TIN_CAY = gioi_han._doc_mang("10.0.0.0/8")
        # Đi qua proxy đã khai → đọc header
        self.assertEqual(gioi_han.dia_chi_that("10.1.2.3", {"x-forwarded-for": "203.0.113.7"}),
                         "203.0.113.7")
        # KHÔNG đi qua proxy đã khai → vẫn bỏ qua header
        self.assertEqual(gioi_han.dia_chi_that("203.0.113.9", {"x-forwarded-for": "203.0.113.7"}),
                         "203.0.113.9")

    def test_a3_lay_phan_tu_PHAI_NHAT_khong_phai_proxy(self):
        """Client tự thêm được IP giả vào ĐẦU chuỗi, nên lấy trái nhất là tin dữ liệu tự khai."""
        gioi_han.PROXY_TIN_CAY = gioi_han._doc_mang("10.0.0.0/8, 192.168.1.1")
        h = {"x-forwarded-for": "198.51.100.1, 203.0.113.7, 10.5.5.5, 192.168.1.1"}
        self.assertEqual(gioi_han.dia_chi_that("10.1.2.3", h), "203.0.113.7",
                         "phải bỏ các proxy tin cậy ở cuối rồi lấy IP ngoài phải nhất")
        # Chuỗi toàn rác → về địa chỉ TCP, không ném lỗi, không trả chuỗi rác
        self.assertEqual(gioi_han.dia_chi_that("10.1.2.3", {"x-forwarded-for": "abc, def"}),
                         "10.1.2.3")

    def test_a4_cat_cong_va_dang_ipv6(self):
        gioi_han.PROXY_TIN_CAY = gioi_han._doc_mang("10.0.0.0/8")
        self.assertEqual(gioi_han.dia_chi_that("10.0.0.1", {"x-forwarded-for": "203.0.113.7:4455"}),
                         "203.0.113.7")
        self.assertEqual(gioi_han.dia_chi_that("10.0.0.1", {"x-forwarded-for": "[2001:db8::5]:443"}),
                         "2001:db8::5")

    def test_a5_cau_hinh_proxy_sai_thi_bo_dung_dai_sai_khong_chet_ca_he(self):
        m = gioi_han._doc_mang("10.0.0.0/8, khong-phai-dai, 172.16.0.0/12")
        self.assertEqual(len(m), 2, f"phải giữ 2 dải đúng, bỏ dải sai: {m}")


class B_GioiHanTanSuat(unittest.TestCase):

    def setUp(self):
        gioi_han.xoa_het()

    def test_b1_dung_tran_thi_chan_va_noi_cho_bao_lau(self):
        """Luật `auth.dang_nhap` chiều `dinh_danh`: 5 lượt/300s rồi chặn 900s."""
        lt = [x for x in gioi_han.luat_cua("auth.dang_nhap") if x.chieu == "dinh_danh"][0]
        self.assertEqual((lt.so_lan, lt.cua_so_giay, lt.chan_giay), (5, 300.0, 900.0))
        for i in range(lt.so_lan):
            kq = gioi_han.kiem("auth.dang_nhap", ip="1.1.1.1", dinh_danh="nan-nhan")
            self.assertTrue(kq.cho_phep, f"lượt {i + 1} bị chặn sớm: {kq}")
        kq = gioi_han.kiem("auth.dang_nhap", ip="1.1.1.1", dinh_danh="nan-nhan")
        self.assertFalse(kq.cho_phep, "lượt thứ 6 phải bị chặn")
        self.assertEqual(kq.chieu, "dinh_danh")
        self.assertGreater(kq.cho_bao_lau, 800, "chan_giay=900 → phải chờ gần 900 giây")
        self.assertEqual(gioi_han.tieu_de(kq)["Retry-After"], str(int(kq.cho_bao_lau)))

    def test_b2_tach_theo_endpoint(self):
        for _ in range(6):
            gioi_han.kiem("auth.dang_nhap", ip="2.2.2.2", dinh_danh="u1")
        self.assertFalse(gioi_han.kiem("auth.dang_nhap", ip="2.2.2.2", dinh_danh="u1").cho_phep)
        # Endpoint khác của CÙNG người vẫn đi được — bucket mang tên endpoint
        self.assertTrue(gioi_han.kiem("auth.doi_mat_khau", ip="2.2.2.2", dinh_danh="u1").cho_phep)

    def test_b3_tach_theo_dinh_danh_va_theo_ip(self):
        for _ in range(6):
            gioi_han.kiem("auth.dang_nhap", ip="3.3.3.3", dinh_danh="ke-xau")
        # Người khác trên CÙNG IP vẫn đi được (trần IP là 20/300s, chưa đụng)
        self.assertTrue(gioi_han.kiem("auth.dang_nhap", ip="3.3.3.3", dinh_danh="nguoi-khac").cho_phep)
        # Cùng định danh từ IP khác thì VẪN bị chặn — nếu không, đổi IP là lách được
        self.assertFalse(gioi_han.kiem("auth.dang_nhap", ip="4.4.4.4", dinh_danh="ke-xau").cho_phep)

    def test_b4_tran_ip_chan_duoc_du_doi_ten_dang_nhap(self):
        """Dò bằng cách mỗi lượt khai một tên khác: chiều `dinh_danh` không bắt được, chiều `ip` bắt."""
        lt = [x for x in gioi_han.luat_cua("auth.dang_nhap") if x.chieu == "ip"][0]
        for i in range(lt.so_lan):
            kq = gioi_han.kiem("auth.dang_nhap", ip="5.5.5.5", dinh_danh=f"ten-{i}")
            self.assertTrue(kq.cho_phep, f"lượt {i + 1}: {kq}")
        self.assertFalse(gioi_han.kiem("auth.dang_nhap", ip="5.5.5.5", dinh_danh="ten-moi").cho_phep)

    def test_b5_cach_ly_theo_tenant(self):
        lt = [x for x in gioi_han.luat_cua("import.upload") if x.chieu == "tenant"][0]
        for _ in range(lt.so_lan):
            self.assertTrue(gioi_han.kiem("import.upload", ip="6.6.6.6", tenant_id=1).cho_phep)
        self.assertFalse(gioi_han.kiem("import.upload", ip="6.6.6.6", tenant_id=1).cho_phep)
        self.assertTrue(gioi_han.kiem("import.upload", ip="6.6.6.6", tenant_id=2).cho_phep,
                        "tenant 1 dùng hết trần KHÔNG được ảnh hưởng tenant 2")

    def test_b6_bi_chan_thi_khong_cong_luot_cho_chieu_nao(self):
        """Kẻ bị chặn ở chiều `dinh_danh` không được đẩy trần `ip` của người khác lên."""
        for _ in range(6):
            gioi_han.kiem("auth.dang_nhap", ip="7.7.7.7", dinh_danh="x")
        truoc = gioi_han.kiem("auth.dang_nhap", ip="7.7.7.7", dinh_danh="y",
                              ghi_nhan=False).con_lai
        for _ in range(30):
            gioi_han.kiem("auth.dang_nhap", ip="7.7.7.7", dinh_danh="x")   # đều bị chặn
        sau = gioi_han.kiem("auth.dang_nhap", ip="7.7.7.7", dinh_danh="y",
                            ghi_nhan=False).con_lai
        self.assertEqual(truoc, sau,
                         "lượt bị chặn vẫn cộng vào bucket IP → kẻ xấu tự gây DoS cho người khác")

    def test_b7_endpoint_la_VAN_bi_ap_tran_mac_dinh(self):
        """Danh sách ĐEN, không danh sách trắng: quên khai endpoint thì vẫn có trần."""
        self.assertNotIn("endpoint.chua-ai-khai", gioi_han.CHINH_SACH)
        self.assertEqual(gioi_han.luat_cua("endpoint.chua-ai-khai"), gioi_han.LUAT_MAC_DINH)
        lt = gioi_han.LUAT_MAC_DINH[0]
        for _ in range(lt.so_lan):
            gioi_han.kiem("endpoint.chua-ai-khai", ip="8.8.8.8", dinh_danh="u")
        self.assertFalse(gioi_han.kiem("endpoint.chua-ai-khai", ip="8.8.8.8", dinh_danh="u").cho_phep)

    def test_b8_dat_lai_sau_dang_nhap_thanh_cong(self):
        for _ in range(4):
            gioi_han.kiem("auth.dang_nhap", ip="9.9.9.9", dinh_danh="nguoi-that")
        gioi_han.dat_lai("auth.dang_nhap", ip="9.9.9.9", dinh_danh="nguoi-that")
        kq = gioi_han.kiem("auth.dang_nhap", ip="9.9.9.9", dinh_danh="nguoi-that",
                           ghi_nhan=False)
        self.assertEqual(kq.con_lai, 5, f"đặt lại rồi phải đầy trần lại: {kq}")

    def test_b9_vo_danh_chua_biet_ten_khong_gop_vao_mot_bucket_chung(self):
        """`dinh_danh=None` thì bỏ qua chiều đó — gộp mọi người vô danh là để một người chặn tất cả."""
        lt = [x for x in gioi_han.luat_cua("auth.dang_nhap") if x.chieu == "dinh_danh"][0]
        for _ in range(lt.so_lan + 3):
            gioi_han.kiem("auth.dang_nhap", ip="11.11.11.11", dinh_danh=None)
        self.assertTrue(gioi_han.kiem("auth.dang_nhap", ip="12.12.12.12", dinh_danh=None).cho_phep)

    def test_b10_dong_thoi_khong_vuot_tran(self):
        """40 thread đua nhau: số lượt được cho phép phải ĐÚNG bằng trần, không hơn."""
        gioi_han.xoa_het()
        lt = [x for x in gioi_han.luat_cua("auth.dang_nhap") if x.chieu == "dinh_danh"][0]
        dem = []
        rao = threading.Barrier(40)

        def chay():
            rao.wait()
            if gioi_han.kiem("auth.dang_nhap", ip="13.13.13.13", dinh_danh="dua").cho_phep:
                dem.append(1)

        ts = [threading.Thread(target=chay) for _ in range(40)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(sum(dem), lt.so_lan,
                         f"cho qua {sum(dem)} lượt, trần là {lt.so_lan} — bộ đếm không an toàn")

    def test_b11_bo_nho_co_tran(self):
        cu = gioi_han.TOI_DA_KHOA
        gioi_han.TOI_DA_KHOA = 50
        try:
            gioi_han.xoa_het()
            for i in range(500):
                gioi_han.kiem("endpoint.rac", ip=f"10.0.{i // 256}.{i % 256}")
            self.assertLessEqual(gioi_han.thong_ke()["so_bucket"], 51,
                                 "số bucket không bị chặn → bộ nhớ lớn vô hạn theo số IP")
        finally:
            gioi_han.TOI_DA_KHOA = cu
            gioi_han.xoa_het()

    def test_b12_moi_endpoint_nhay_cam_deu_co_luat_rieng(self):
        """Chốt lại danh sách endpoint phải được siết — thiếu một cái là bộ thử hỏng."""
        bat_buoc = ("auth.dang_nhap", "auth.quen_mat_khau", "auth.dat_lai_mat_khau",
                    "membership.tao", "membership.sua", "tai_khoan_hang.quan_ly",
                    "import.upload", "import.duyet", "platform.quan_tri", "khoa.xoay")
        for e in bat_buoc:
            self.assertIn(e, gioi_han.CHINH_SACH, f"endpoint nhạy cảm {e} chưa có luật riêng")
            self.assertTrue(gioi_han.CHINH_SACH[e], f"{e} có luật rỗng")
        # Ba đường vô danh phải có luật theo IP (người gửi chưa có tài khoản để siết)
        for e in ("auth.dang_nhap", "auth.quen_mat_khau", "auth.dat_lai_mat_khau"):
            self.assertTrue(any(x.chieu == "ip" for x in gioi_han.CHINH_SACH[e]),
                            f"{e} là đường vô danh mà không có luật theo IP")

    def test_b13_kiem_yeu_cau_gop_luat_proxy(self):
        """Hàm AG-00 nên gọi: tự giải IP, call site không có cơ hội quên luật proxy."""
        gioi_han.xoa_het()
        # dinh_danh=None → chỉ còn chiều `ip`, nên khóa bucket cho thấy IP nào đã được dùng
        kq = gioi_han.kiem_yeu_cau("auth.dang_nhap", "9.9.9.9",
                                   {"x-forwarded-for": "1.2.3.4"}, dinh_danh=None)
        self.assertTrue(kq.cho_phep)
        self.assertEqual(kq.khoa, "auth.dang_nhap|ip|9.9.9.9",
                         f"IP dùng để đếm phải là địa chỉ TCP, không phải header: {kq.khoa}")


class C_HanMucNhap(unittest.TestCase):
    """S05 — hạn mức nhập file. Kế toán phải NGUYÊN TỬ và CÁCH LY theo tenant."""

    @classmethod
    def setUpClass(cls):
        csdl.mo()
        quyen.seed()
        cls.uid = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                           " VALUES ('gh-user','x','Người thử', ?)", (csdl.bay_gio(),)).lastrowid
        cls.t_free = _tao_tenant("gh-free", "free")
        cls.t_pro = _tao_tenant("gh-pro", "pro")

    def test_c1_tran_dan_xuat_tu_goi_khong_tu_bat_thu_phi(self):
        t = gioi_han.tran_cua(self.t_free)
        self.assertEqual(t["goi_id"], "free")
        self.assertEqual(t["han_muc_don_thang_cua_goi"], 50)
        self.assertEqual(t["tran_don_nhap_thang"],
                         max(gioi_han.TRAN_DON_NHAP_TOI_THIEU, 50 * gioi_han.BOI_SO_DON_NHAP))
        # Gói to hơn thì trần to hơn — cách ly theo gói, không một trần chung
        self.assertGreater(gioi_han.tran_cua(self.t_pro)["tran_don_nhap_thang"],
                           t["tran_don_nhap_thang"])

    def test_c2_khong_dung_bo_dem_cua_billing(self):
        """Đơn nháp KHÔNG được cộng vào `usage_thang.so_don` — đó là bộ đếm ĐƠN ĐÃ GỬI."""
        import billing
        truoc = billing.usage_hien_tai(self.t_free)["so_don"]
        gioi_han.dat_truoc_don_nhap(self.t_free, 10)
        self.assertEqual(billing.usage_hien_tai(self.t_free)["so_don"], truoc,
                         "hạn mức nhập đã đụng vào usage_thang → tự bật thu phí")
        gioi_han.nha_don_nhap(self.t_free, 10)

    def test_c2b_loi_han_muc_nhap_khong_ke_thua_VuotHanMuc_cua_billing(self):
        """`server.py` map `billing.VuotHanMuc` → HTTP 402. Chặn lạm dụng không phải mời nâng gói."""
        import billing
        self.assertFalse(issubclass(gioi_han.VuotHanMucNhap, billing.VuotHanMuc))
        self.assertEqual(gioi_han.VuotHanMucNhap("x").ma, 429)
        self.assertEqual(gioi_han.VuotHanMucNhap("x", 413).ma, 413)

    def test_c3_dat_truoc_vuot_tran_thi_chan(self):
        t = _tao_tenant("gh-c3", "free")
        tran = gioi_han.tran_cua(t)["tran_don_nhap_thang"]
        gioi_han.dat_truoc_don_nhap(t, tran)
        self.assertEqual(gioi_han.da_dung(t)["so_don_nhap"], tran)
        with self.assertRaises(gioi_han.VuotHanMucNhap):
            gioi_han.dat_truoc_don_nhap(t, 1)
        # Chặn rồi thì KHÔNG được cộng thêm gì (không tăng quá trần)
        self.assertEqual(gioi_han.da_dung(t)["so_don_nhap"], tran)

    def test_c4_mot_luot_hoac_di_het_hoac_bi_chan_ngay(self):
        """Đặt trước cả lượt: không để nửa batch lọt rồi nửa sau tắc giữa đường."""
        t = _tao_tenant("gh-c4", "free")
        tran = gioi_han.tran_cua(t)["tran_don_nhap_thang"]
        with self.assertRaises(gioi_han.VuotHanMucNhap):
            gioi_han.dat_truoc_don_nhap(t, tran + 1)
        self.assertEqual(gioi_han.da_dung(t)["so_don_nhap"], 0,
                         "lượt bị chặn vẫn ghi một phần → kế toán sai")

    def test_c5_dong_thoi_khong_vuot_tran(self):
        """20 thread mỗi thread xin 30 suất trên trần 150: tổng đã cộng KHÔNG được vượt trần."""
        t = _tao_tenant("gh-c5", "free")
        tran = gioi_han.tran_cua(t)["tran_don_nhap_thang"]
        moi_luot = 30
        ok = []
        rao = threading.Barrier(20)

        def chay():
            rao.wait()
            try:
                gioi_han.dat_truoc_don_nhap(t, moi_luot)
                ok.append(1)
            except gioi_han.VuotHanMucNhap:
                pass

        ts = [threading.Thread(target=chay) for _ in range(20)]
        for x in ts:
            x.start()
        for x in ts:
            x.join()
        da = gioi_han.da_dung(t)["so_don_nhap"]
        self.assertEqual(da, len(ok) * moi_luot, f"bộ đếm {da} ≠ {len(ok)}×{moi_luot}")
        self.assertLessEqual(da, tran, f"đã cộng {da} vượt trần {tran} — kế toán KHÔNG nguyên tử")
        self.assertEqual(len(ok), tran // moi_luot,
                         f"đúng {tran // moi_luot} lượt được qua, thực tế {len(ok)}")

    def test_c6_cach_ly_tenant(self):
        a, b = _tao_tenant("gh-c6a", "free"), _tao_tenant("gh-c6b", "free")
        tran = gioi_han.tran_cua(a)["tran_don_nhap_thang"]
        gioi_han.dat_truoc_don_nhap(a, tran)
        with self.assertRaises(gioi_han.VuotHanMucNhap):
            gioi_han.dat_truoc_don_nhap(a, 1)
        self.assertEqual(gioi_han.dat_truoc_don_nhap(b, tran), tran,
                         "tenant A dùng hết KHÔNG được chặn tenant B")

    def test_c7_nha_lai_suat_khong_dung(self):
        t = _tao_tenant("gh-c7", "free")
        gioi_han.dat_truoc_don_nhap(t, 20)
        gioi_han.nha_don_nhap(t, 5)
        self.assertEqual(gioi_han.da_dung(t)["so_don_nhap"], 15)
        gioi_han.nha_don_nhap(t, 1000)
        self.assertEqual(gioi_han.da_dung(t)["so_don_nhap"], 0, "không bao giờ xuống âm")

    def test_c8_chan_dung_luong_va_so_dong_mot_file(self):
        t = _tao_tenant("gh-c8", "free")
        with self.assertRaises(gioi_han.VuotHanMucNhap) as e:
            gioi_han.kiem_file_nhap(t, gioi_han.GIOI_HAN_BYTE_MOI_FILE + 1)
        self.assertEqual(e.exception.ma, 413)
        with self.assertRaises(gioi_han.VuotHanMucNhap) as e:
            gioi_han.kiem_file_nhap(t, 1000, so_dong=gioi_han.GIOI_HAN_DONG_MOI_FILE + 1)
        self.assertEqual(e.exception.ma, 413)
        self.assertEqual(gioi_han.kiem_file_nhap(t, 1000, so_dong=10)["so_byte"], 1000)

    def test_c9_tran_khong_long_hon_nhap_file(self):
        """`nhap_file` siết lại mà chỗ này quên thì hỏng ở đây, không lệch im lặng."""
        import nhap_file
        self.assertLessEqual(gioi_han.GIOI_HAN_BYTE_MOI_FILE, nhap_file.GIOI_HAN_BYTE_FILE,
                             "trần dung lượng của gioi_han LỎNG hơn nhap_file")
        self.assertLessEqual(gioi_han.GIOI_HAN_DONG_MOI_FILE, nhap_file.GIOI_HAN_SO_DONG,
                             "trần số dòng của gioi_han LỎNG hơn nhap_file")

    def test_c10_chan_so_file_moi_gio_dem_tu_csdl(self):
        """Đếm từ `import_batch` nên sống qua khởi động lại tiến trình."""
        t = _tao_tenant("gh-c10", "free")
        tran = gioi_han.tran_cua(t)["tran_file_moi_gio"]
        for i in range(tran):
            csdl.ghi("INSERT INTO import_batch (tenant_id, ten_file, loai_file, trang_thai,"
                     " nguoi_tao, tao_luc) VALUES (?,?,?,?,?,?)",
                     (t, f"f{i}.csv", "csv", "READY", self.uid, csdl.bay_gio()))
        with self.assertRaises(gioi_han.VuotHanMucNhap) as e:
            gioi_han.kiem_file_nhap(t, 100)
        self.assertEqual(e.exception.ma, 429)
        # Batch CŨ (ngoài cửa sổ 1 giờ) không được tính
        t2 = _tao_tenant("gh-c10b", "free")
        for i in range(tran + 5):
            csdl.ghi("INSERT INTO import_batch (tenant_id, ten_file, loai_file, trang_thai,"
                     " nguoi_tao, tao_luc) VALUES (?,?,?,?,?,?)",
                     (t2, f"g{i}.csv", "csv", "READY", self.uid, gioi_han._moc_truoc_day(5)))
        self.assertIsNotNone(gioi_han.kiem_file_nhap(t2, 100))

    def test_c11_batch_cua_tenant_khac_khong_tinh_vao_tran_gio(self):
        a, b = _tao_tenant("gh-c11a", "free"), _tao_tenant("gh-c11b", "free")
        tran = gioi_han.tran_cua(a)["tran_file_moi_gio"]
        for i in range(tran + 3):
            csdl.ghi("INSERT INTO import_batch (tenant_id, ten_file, loai_file, trang_thai,"
                     " nguoi_tao, tao_luc) VALUES (?,?,?,?,?,?)",
                     (a, f"h{i}.csv", "csv", "READY", self.uid, csdl.bay_gio()))
        self.assertIsNotNone(gioi_han.kiem_file_nhap(b, 100))

    def test_c12_tenant_khong_ton_tai_thi_tu_choi_chu_khong_doan_tran(self):
        with self.assertRaises(gioi_han.VuotHanMucNhap) as e:
            gioi_han.tran_cua(999999)
        self.assertEqual(e.exception.ma, 400)

    def test_c13_doi_soat_phat_hien_lech(self):
        """Phép đo ĐỘC LẬP với bộ đếm (§12.1): đếm đơn thật trong `don_hang` rồi so."""
        t = _tao_tenant("gh-c13", "free")
        gioi_han.dat_truoc_don_nhap(t, 3)
        ds = gioi_han.doi_soat(t)
        self.assertEqual(ds["bo_dem"], 3)
        self.assertEqual(ds["don_that"], 0)
        self.assertEqual(ds["lech"], 3, "đối chiếu phải THẤY lệch, không tự sửa im lặng")

    def test_c14_trang_thai_du_ba_phan(self):
        t = _tao_tenant("gh-c14", "basic")
        tt = gioi_han.trang_thai(t)
        for k in ("tran", "da_dung", "con_lai"):
            self.assertIn(k, tt)
        self.assertEqual(tt["con_lai"]["don_nhap"], tt["tran"]["tran_don_nhap_thang"])

    def test_c15_bang_moi_khong_ALTER_bang_dang_co(self):
        """DDL chỉ CREATE TABLE IF NOT EXISTS — không ALTER bảng nào đang chạy."""
        self.assertIn("CREATE TABLE IF NOT EXISTS han_muc_nhap_thang", gioi_han.DDL_HAN_MUC_NHAP)
        self.assertNotIn("ALTER", gioi_han.DDL_HAN_MUC_NHAP.upper())
        r = csdl.mot("SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                     ("han_muc_nhap_thang",))
        self.assertIsNotNone(r, "bảng hạn mức chưa được tạo")


if __name__ == "__main__":
    unittest.main(verbosity=2)
