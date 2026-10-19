# Bộ thử LỚP QUAN SÁT (G11) — AG-05 DEVOPS.
# Chạy: python3 app/thu/thu_quan_sat.py
#
# Nguyên tắc (CLAUDE.md §12.1): mỗi khẳng định do MỘT PHÉP ĐO THẬT tạo ra. Cụ thể ở đây:
#   - "log không rò bí mật" đo bằng cách DỰNG LOG THẬT từ dữ liệu có số điện thoại / COD /
#     credentials rồi QUÉT chuỗi log ở BA DẠNG (thô · hex · base64). Không grep mã rồi kết luận.
#   - "health khác readiness" đo bằng cách LÀM HỎNG thật một thành phần (đổi đường CSDL, xoá
#     khóa) rồi xem hai hàm trả khác nhau. Không đọc comment rồi tin.
#   - "cổng kiểm không tự vá cái nó kiểm" đo bằng cách chụp danh sách file TRƯỚC và SAU lượt
#     kiểm. Đây là ca quan trọng nhất của file: ca đã xảy ra thật trong vault chủ dự án là bước
#     nghiệm thu TỰ CHẠY HỘ nên luôn báo đạt.
#   - "readiness chạy HẾT phép kiểm" đo bằng cách làm hỏng CÁI ĐẦU rồi xem cái SAU có kết quả.
import io
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-quansat-")
os.environ["VIP_HUB_DATA"] = _tam

import cau_hinh      # noqa: E402
import csdl          # noqa: E402
import quan_sat      # noqa: E402
import secret_provider  # noqa: E402


# ===========================================================================
class A_CheBiMat(unittest.TestCase):
    """`che()` dùng DANH SÁCH TRẮNG: trường không khai thì bị che, kể cả trường mới chưa ai biết."""

    def test_a1_truong_la_bi_che(self):
        ra = quan_sat.che({"mat_khau": "bimat123", "token": "abc", "tenant_id": 7})
        self.assertEqual(ra["mat_khau"], quan_sat.CHE)
        self.assertEqual(ra["token"], quan_sat.CHE)
        self.assertEqual(ra["tenant_id"], 7, "trường đã khai phải đi qua nguyên vẹn")

    def test_a2_truong_moi_chua_ai_biet_van_bi_che(self):
        """Đây là lý do chọn danh sách trắng: một trường SINH RA SAU khi viết file này vẫn an
        toàn mặc định. Danh sách đen thì trường mới mặc định LỘ."""
        ra = quan_sat.che({"api_key_hang_moi_2027": "sk-live-xyz"})
        self.assertEqual(ra["api_key_hang_moi_2027"], quan_sat.CHE)

    def test_a3_giu_ten_truong_bo_gia_tri(self):
        """Giữ TÊN để log còn nói được 'có trường này', bỏ GIÁ TRỊ."""
        ra = quan_sat.che({"passphrase": "x"})
        self.assertIn("passphrase", ra)
        self.assertNotIn("x", json.dumps(ra))

    def test_a4_lop_hinh_dang_bat_sdt_trong_truong_duoc_phep(self):
        """Hai lớp lọc theo HAI TIÊU CHÍ khác nhau nên không che nhau: `thong_diep` là trường
        ĐƯỢC PHÉP, nhưng số điện thoại trong giá trị vẫn phải bị che."""
        ra = quan_sat.che({"thong_diep": "goi khach 0987654321 khong duoc"})
        self.assertNotIn("0987654321", ra["thong_diep"])
        self.assertIn("<sdt>", ra["thong_diep"])

    def test_a5_che_ban_ma_credentials(self):
        ra = quan_sat.che({"loi": "giai ma that bai cho v3$k-20261015-aa$Tm9uY2U=$Q2lwaGVy="})
        self.assertIn("<ban_ma>", ra["loi"])

    def test_a6_che_email_va_authorization(self):
        ra = quan_sat.che({"ghi_chu": "gui cho a@b.com, header Bearer abcdef1234567890"})
        self.assertNotIn("a@b.com", ra["ghi_chu"])
        self.assertNotIn("abcdef1234567890", ra["ghi_chu"])

    def test_a7_khong_cho_chen_dong_log_gia(self):
        """`\\n` trong giá trị do client gửi là đường CHÈN DÒNG LOG GIẢ. Một dòng giả trong log
        là một lần chẩn đoán đi sai hướng."""
        ra = quan_sat.che({"loi": 'a\n{"loai":"dang_nhap","muc":"tin"}'})
        self.assertNotIn("\n", ra["loi"])

    def test_a8_khong_treo_voi_json_long_sau(self):
        d = cur = {}
        for _ in range(50):
            cur["loai"] = {}
            cur = cur["loai"]
        ra = quan_sat.che(d)       # phải trả về, không đệ quy vô hạn
        self.assertIn("<sau_qua>", json.dumps(ra))

    def test_a9_khong_che_vao_giua_ma_van_don(self):
        """Che SAI cũng làm log mất tác dụng. Mã vận đơn/idem_key không được biến thành <sdt>."""
        ra = quan_sat.che({"idem_key": "VD0987654321234567890"})
        self.assertEqual(ra["idem_key"], "VD0987654321234567890")


# ===========================================================================
class B_QuetBiMatBaDang(unittest.TestCase):
    """Ca thử BẮT BUỘC của G11.5: dựng log THẬT từ dữ liệu có bí mật rồi quét 3 dạng."""

    BI_MAT = [
        "MatKhauSieuBiMat2026",          # mật khẩu người dùng
        "sk-live-jt-0123456789abcdef",   # api key hãng
        "hmac-secret-viettelpost-xyz",   # secret webhook
        "passphrase-goi-khoa-cua-anh",   # passphrase gói backup khóa
    ]

    def test_b1_quet_tu_bat_duoc_ca_ba_dang(self):
        """ĐO CHÍNH CÔNG CỤ ĐO TRƯỚC KHI TIN NÓ (§12.1 luật 1). Một bộ quét luôn trả rỗng cũng
        làm mọi ca sau 'đạt' — và đó đúng là kiểu hỏng đã xảy ra thật trong vault."""
        import base64
        bm = self.BI_MAT[0]
        for van_ban, mong in (
            ("loi: " + bm, "tho"),
            ("hex=" + bm.encode().hex(), "hex"),
            ("b64=" + base64.b64encode(bm.encode()).decode(), "base64"),
            ("b64=" + base64.b64encode(bm.encode()).decode().rstrip("="), "base64_khong_dem"),
        ):
            thay = quan_sat.quet_bi_mat(van_ban, [bm])
            self.assertTrue(thay, f"bộ quét KHÔNG bắt được dạng {mong} — công cụ đo hỏng")
            self.assertIn(mong, [d for _, d in thay])

    def test_b2_log_dung_tu_du_lieu_that_khong_ro_bi_mat(self):
        """Dựng log từ một bản ghi đơn hàng ĐẦY ĐỦ: SĐT người gửi/nhận, COD, credentials hãng,
        passphrase. Rồi quét toàn bộ chuỗi log."""
        luong = io.StringIO()
        quan_sat.dat_luong_log(luong)
        try:
            quan_sat.bat_dau_yeu_cau({"X-Correlation-Id": "chuoi-viec-01"})
            quan_sat.ghi("tao_don", tenant_id=3, don_id=99,
                         sdt_nguoi_nhan="0987654321", sdt_nguoi_gui="+84912345678",
                         cod=1500000, dia_chi="12 Nguyen Trai, Q1",
                         ten_nguoi_nhan="Nguyen Van A",
                         mat_khau=self.BI_MAT[0], api_key=self.BI_MAT[1],
                         webhook_secret=self.BI_MAT[2], passphrase=self.BI_MAT[3],
                         thong_diep="goi 0987654321 ma khong duoc, email a@b.com")
            quan_sat.ghi("loi_hang", muc="loi", ma_chuan="TU_CHOI",
                         loi="hang tra ve: credential " + self.BI_MAT[1] + " khong hop le")
            quan_sat.ket_thuc_yeu_cau()
        finally:
            quan_sat.dat_luong_log(None)
        ban = luong.getvalue()
        self.assertTrue(ban.strip(), "không có dòng log nào — phép đo vô nghĩa")

        thay = quan_sat.quet_bi_mat(ban, self.BI_MAT)
        self.assertEqual(thay, [], f"RÒ BÍ MẬT trong log: {thay}\n--- log ---\n{ban}")
        # Thông tin khách hàng: SĐT và email cũng không được nằm trong log.
        for pii in ("0987654321", "+84912345678", "912345678", "a@b.com"):
            self.assertNotIn(pii, ban, f"rò thông tin khách hàng: {pii}")

    def test_b3_moi_dong_log_la_mot_json_hop_le(self):
        """Log một-dòng-một-JSON (JSONL): bị cắt giữa file vẫn đọc được các dòng trước."""
        luong = io.StringIO()
        quan_sat.dat_luong_log(luong)
        try:
            for i in range(5):
                quan_sat.ghi("thu", don_id=i, mat_khau="x\ny")
        finally:
            quan_sat.dat_luong_log(None)
        dong = [d for d in luong.getvalue().split("\n") if d.strip()]
        self.assertEqual(len(dong), 5)
        for d in dong:
            o = json.loads(d)           # nổ ở đây = dòng log không parse được
            self.assertIn("luc", o)
            self.assertIn("pid", o)

    def test_b4_hai_thread_khong_xen_dong_vao_nhau(self):
        """Dòng bị xen là dòng không parse nổi — mất im lặng đúng lúc cần log nhất."""
        luong = io.StringIO()
        quan_sat.dat_luong_log(luong)
        try:
            def chay(n):
                for i in range(40):
                    quan_sat.ghi("dua", don_id=n * 1000 + i, ghi_chu="x" * 200)
            ts = [threading.Thread(target=chay, args=(n,)) for n in range(6)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
        finally:
            quan_sat.dat_luong_log(None)
        dong = [d for d in luong.getvalue().split("\n") if d.strip()]
        self.assertEqual(len(dong), 240)
        for d in dong:
            json.loads(d)

    def test_b5_dong_log_qua_dai_bi_cat_nhung_van_la_mot_dong(self):
        luong = io.StringIO()
        quan_sat.dat_luong_log(luong)
        try:
            quan_sat.ghi("to", ghi_chu="x" * 50000)
        finally:
            quan_sat.dat_luong_log(None)
        ban = luong.getvalue()
        self.assertEqual(ban.count("\n"), 1)
        self.assertLessEqual(len(ban), quan_sat.DONG_LOG_TOI_DA + 2)


# ===========================================================================
class C_RequestId(unittest.TestCase):

    def test_c1_tu_sinh_khi_khong_co_header(self):
        rid, cid = quan_sat.bat_dau_yeu_cau({})
        self.assertTrue(rid)
        self.assertEqual(cid, rid, "không có correlation thì bằng request_id")
        quan_sat.ket_thuc_yeu_cau()

    def test_c2_nhan_correlation_id_hop_le_tu_ben_goi(self):
        rid, cid = quan_sat.bat_dau_yeu_cau({"x-correlation-id": "viec-abc_01.2"})
        self.assertEqual(cid, "viec-abc_01.2")
        self.assertNotEqual(rid, cid, "request_id luôn do HỆ sinh, không nhận từ client")
        quan_sat.ket_thuc_yeu_cau()

    def test_c3_id_ban_tu_client_bi_BO_chu_khong_lam_sach_roi_dung(self):
        """Chuỗi đã bị cắt gọt không còn truy vết được sang hệ bên kia — nên BỎ và tự sinh."""
        for xau in ('a"b', "a\nb", "x" * 200, "a b", "../../etc/passwd", ""):
            _, cid = quan_sat.bat_dau_yeu_cau({"x-correlation-id": xau})
            self.assertNotIn(xau if xau else "@", cid)
            self.assertTrue(quan_sat.MAU_ID.match(cid))
            quan_sat.ket_thuc_yeu_cau()

    def test_c4_ket_thuc_xoa_ngu_canh(self):
        """Thread của `ThreadingHTTPServer` được DÙNG LẠI — ID sót lại sẽ gán sai cho lượt sau."""
        quan_sat.bat_dau_yeu_cau({})
        self.assertIsNotNone(quan_sat.id_hien_tai()[0])
        ms = quan_sat.ket_thuc_yeu_cau()
        self.assertIsInstance(ms, int)
        self.assertEqual(quan_sat.id_hien_tai(), (None, None))

    def test_c5_hai_thread_hai_id_khac_nhau(self):
        thay = []

        def chay():
            rid, _ = quan_sat.bat_dau_yeu_cau({})
            thay.append(rid)
            quan_sat.ket_thuc_yeu_cau()
        ts = [threading.Thread(target=chay) for _ in range(20)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len(set(thay)), 20, "ID bị chia sẻ giữa thread")


# ===========================================================================
class D_HealthKhacReadiness(unittest.TestCase):

    def test_d1_health_khong_cham_csdl(self):
        """Đo bằng cách trỏ CSDL vào đường KHÔNG THỂ MỞ rồi gọi `suc_khoe()`: nó vẫn phải ok."""
        cu = cau_hinh.DUONG_DAN_CSDL
        try:
            cau_hinh.DUONG_DAN_CSDL = "/khong-ton-tai-chac-chan/x.db"
            kq = quan_sat.suc_khoe()
            self.assertTrue(kq["ok"])
        finally:
            cau_hinh.DUONG_DAN_CSDL = cu

    def test_d2_health_noi_ro_pham_vi_trong_chinh_ket_qua(self):
        """Người đọc dashboard không được phép suy rộng từ một chữ 'ok' (§12.1 luật 5)."""
        kq = quan_sat.suc_khoe()
        self.assertIn("pham_vi", kq)
        self.assertIn("san-sang", kq["pham_vi"])

    def test_d3_readiness_noi_ro_cai_gi_NGOAI_pham_vi(self):
        kq = quan_sat.san_sang()
        self.assertIn("pham_vi", kq)
        self.assertIn("NGOAI pham vi", kq["pham_vi"])

    def test_d4_readiness_dat_khi_moi_thu_binh_thuong(self):
        csdl.mo()
        csdl.ghi("INSERT OR IGNORE INTO schema_version (phien_ban, ap_dung_luc) VALUES (?,?)",
                 (csdl.PHIEN_BAN_SCHEMA, csdl.bay_gio()))
        secret_provider.nha_cung_cap().tao_khoa_moi()   # tạo khóa CÓ CHỦ Ý, ngoài cổng kiểm
        import webhook
        webhook.khoi_dong()
        try:
            kq = quan_sat.san_sang()
            self.assertTrue(kq["ok"], json.dumps(kq, ensure_ascii=False, indent=2))
        finally:
            webhook.dung()

    def test_d5_readiness_HONG_khi_schema_cu_hon_ma(self):
        """`server.chay()` tự `SystemExit(3)` khi CSDL cũ hơn mã. Readiness phải nói ra điều đó
        TRƯỚC, thay vì để container khởi động lại vòng quanh mà không ai biết vì sao."""
        cu = csdl.PHIEN_BAN_SCHEMA
        try:
            csdl.PHIEN_BAN_SCHEMA = cu + 99
            ok, ct = quan_sat._kiem_schema()
            self.assertFalse(ok)
            self.assertIn("migration", ct["loi"])
            kq = quan_sat.san_sang()
            self.assertFalse(kq["ok"], "readiness phải HỎNG khi schema cũ hơn mã")
        finally:
            csdl.PHIEN_BAN_SCHEMA = cu

    def test_d6_readiness_CHAY_HET_phep_kiem_khong_ngan_mach(self):
        """Hỏng cái ĐẦU thì cái SAU vẫn phải có kết quả — sửa được một lượt, không phải chạy lại
        cổng kiểm sau mỗi lần vá."""
        cu = cau_hinh.THU_MUC_DU_LIEU
        try:
            cau_hinh.THU_MUC_DU_LIEU = "/khong-ton-tai-chac-chan"
            kq = quan_sat.san_sang()
            self.assertFalse(kq["kiem"]["thu_muc_du_lieu"]["ok"])
            for ten in ("csdl", "schema", "khoa", "worker"):
                self.assertIn(ten, kq["kiem"], f"phép kiểm '{ten}' bị ngắt mạch")
                self.assertIn("ok", kq["kiem"][ten])
        finally:
            cau_hinh.THU_MUC_DU_LIEU = cu

    def test_d7_bo_qua_duoc_GHI_RA_chu_khong_tinh_la_dat(self):
        """Rủi ro cố ý bỏ qua PHẢI ghi ra. `ok: None` chứ không phải `ok: True`."""
        kq = quan_sat.san_sang(bo_qua=("worker",))
        self.assertIsNone(kq["kiem"]["worker"]["ok"])
        self.assertIn("BO QUA", kq["kiem"]["worker"]["ghi_chu"])
        self.assertIn("worker", kq["bo_qua"])

    def test_d8_readiness_khong_ro_khoa_ra_ngoai(self):
        secret_provider.nha_cung_cap().tao_khoa_moi()
        key_id, khoa = secret_provider.nha_cung_cap().khoa_hien_hanh()
        kq = quan_sat.san_sang()
        ban = json.dumps(kq, ensure_ascii=False, default=str)
        thay = quan_sat.quet_bi_mat(ban, [khoa.hex(), khoa.decode("latin-1")])
        self.assertEqual(thay, [], f"readiness rò nội dung khóa: {thay}")


# ===========================================================================
class E_CongKiemKhongTuVa(unittest.TestCase):
    """Ca quan trọng nhất của file. Ca đã xảy ra THẬT trong vault chủ dự án: bước nghiệm thu của
    một bộ cài TỰ CHẠY HỘ bằng shell có sẵn quyền nên LUÔN báo đạt, che mất việc bộ lập lịch
    không chạy nổi. Cổng kiểm mà tự vá cái nó kiểm thì nó luôn xanh."""

    def test_e1_kiem_khoa_KHONG_tu_sinh_khoa(self):
        nen = tempfile.mkdtemp(prefix="vip-khoa-trong-")
        ncc_cu = secret_provider.nha_cung_cap()
        try:
            p = secret_provider.LocalSecretProvider(
                thu_muc=os.path.join(nen, "khoa"),
                duong_khoa_cu=os.path.join(nen, "khoa-noi-bo.key"))
            secret_provider.dat_nha_cung_cap(p)
            truoc = sorted(os.listdir(nen))
            ok, ct = quan_sat._kiem_khoa()
            sau = sorted(os.listdir(nen))
            self.assertFalse(ok, "chưa có khóa mà cổng kiểm báo ĐẠT")
            self.assertEqual(truoc, sau,
                             f"cổng kiểm đã TẠO file: truoc={truoc} sau={sau}")
        finally:
            secret_provider.dat_nha_cung_cap(ncc_cu)
            shutil.rmtree(nen, ignore_errors=True)

    def test_e2_kiem_khoa_KHONG_tu_ghi_con_tro_hien_hanh(self):
        """Có khóa nhưng mất con trỏ: `khoa_hien_hanh()` sẽ TỰ GHI con trỏ. Cổng kiểm phải
        tránh đúng đường đó, nếu không lượt kiểm thứ hai luôn xanh."""
        nen = tempfile.mkdtemp(prefix="vip-khoa-mattro-")
        ncc_cu = secret_provider.nha_cung_cap()
        try:
            tm = os.path.join(nen, "khoa")
            p = secret_provider.LocalSecretProvider(
                thu_muc=tm, duong_khoa_cu=os.path.join(nen, "khoa-noi-bo.key"))
            secret_provider.dat_nha_cung_cap(p)
            p.tao_khoa_moi()
            os.remove(os.path.join(tm, secret_provider.TEN_FILE_TRO))
            truoc = sorted(os.listdir(tm))
            ok, ct = quan_sat._kiem_khoa()
            sau = sorted(os.listdir(tm))
            self.assertFalse(ok, "mất con trỏ mà cổng kiểm báo ĐẠT")
            self.assertEqual(truoc, sau, f"cổng kiểm đã TỰ GHI con trỏ: {sau}")
            self.assertIn("hien-hanh", ct["loi"])
        finally:
            secret_provider.dat_nha_cung_cap(ncc_cu)
            shutil.rmtree(nen, ignore_errors=True)

    def test_e3_kiem_thu_muc_KHONG_tu_tao_thu_muc(self):
        nen = tempfile.mkdtemp(prefix="vip-tm-")
        cu = cau_hinh.THU_MUC_DU_LIEU
        try:
            thieu = os.path.join(nen, "chua-co")
            cau_hinh.THU_MUC_DU_LIEU = thieu
            ok, ct = quan_sat._kiem_thu_muc_du_lieu()
            self.assertFalse(ok)
            self.assertFalse(os.path.exists(thieu), "cổng kiểm đã TẠO thư mục dữ liệu")
        finally:
            cau_hinh.THU_MUC_DU_LIEU = cu
            shutil.rmtree(nen, ignore_errors=True)

    def test_e4_kiem_khoa_khoa_sai_do_dai_la_HONG(self):
        """File khóa 31 byte vẫn là một file tồn tại. `os.path.exists` sẽ nói ĐẠT; phép đo thật
        phải đọc nội dung."""
        nen = tempfile.mkdtemp(prefix="vip-khoa-ngan-")
        ncc_cu = secret_provider.nha_cung_cap()
        try:
            tm = os.path.join(nen, "khoa")
            os.makedirs(tm)
            with open(os.path.join(tm, "xau.key"), "wb") as f:
                f.write(b"x" * 31)
            with open(os.path.join(tm, secret_provider.TEN_FILE_TRO), "w") as f:
                f.write("xau")
            p = secret_provider.LocalSecretProvider(
                thu_muc=tm, duong_khoa_cu=os.path.join(nen, "khoa-noi-bo.key"))
            secret_provider.dat_nha_cung_cap(p)
            ok, ct = quan_sat._kiem_khoa()
            self.assertFalse(ok, "khóa 31 byte mà báo ĐẠT")
        finally:
            secret_provider.dat_nha_cung_cap(ncc_cu)
            shutil.rmtree(nen, ignore_errors=True)


# ===========================================================================
class F_Metric(unittest.TestCase):

    def test_f1_cong_nguyen_tu_voi_nhieu_thread(self):
        """Đo bằng NHIỀU THREAD THẬT đua nhau, không bằng đọc mã thấy có khóa."""
        quan_sat.dat_lai_dem()

        def chay():
            for _ in range(500):
                quan_sat.cong("loi_5xx")
        ts = [threading.Thread(target=chay) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(quan_sat.metric()["dem"]["loi_5xx"], 4000)

    def test_f2_metric_noi_ro_so_dem_chi_cua_mot_tien_trinh(self):
        """Đúng kiểu quên phạm vi đã thành rủi ro R-a của dự án (trần rate limit trong bộ nhớ
        một tiến trình). Không nói ra là mời người đọc suy rộng."""
        m = quan_sat.metric()
        self.assertIn("pham_vi", m)
        self.assertIn("MAT khi khoi dong lai", m["pham_vi"])
        self.assertIn("KHONG gop giua", m["pham_vi"])

    def test_f3_metric_bao_hang_doi_webhook(self):
        import webhook
        webhook.khoi_dong()
        try:
            m = quan_sat.metric()
            self.assertTrue(m["worker_webhook"]["ok"])
            self.assertIn("qsize", m["worker_webhook"])
        finally:
            webhook.dung()

    def test_f4_metric_khong_no_khi_bang_chua_co(self):
        """Lớp quan sát KHÔNG được tự thành nguyên nhân sự cố mà nó định quan sát."""
        m = quan_sat.metric()
        self.assertIn("luc", m)


# ===========================================================================
class G_GhiSuKien(unittest.TestCase):

    def test_g1_bang_chua_co_thi_chi_ghi_log_va_NOI_RA(self):
        """`DDL_G11` chờ AG-00 cắm vào migration v8. Tới lúc đó `ghi_su_kien` phải trả False —
        chứ không âm thầm coi như đã ghi."""
        csdl.mo()
        co = quan_sat._co_bang(quan_sat.TEN_BANG)
        luong = io.StringIO()
        quan_sat.dat_luong_log(luong)
        try:
            kq = quan_sat.ghi_su_kien("khoi_dong", phien_ban_schema=7)
        finally:
            quan_sat.dat_luong_log(None)
        self.assertEqual(kq, co, "giá trị trả về phải khớp việc bảng có thật hay không")
        self.assertIn("khoi_dong", luong.getvalue())

    def test_g2_ghi_duoc_sau_khi_cam_DDL_G11(self):
        """Đo DDL thật: chạy `DDL_G11` lên CSDL thử rồi ghi một mốc và đọc lại."""
        kn = csdl.mo()
        with csdl.khoa_ghi:
            kn.executescript(quan_sat.DDL_G11)
            kn.commit()
        self.assertTrue(quan_sat._co_bang(quan_sat.TEN_BANG))
        quan_sat.bat_dau_yeu_cau({"x-correlation-id": "trien-khai-01"})
        try:
            self.assertTrue(quan_sat.ghi_su_kien(
                "trien_khai", muc="tin", phien_ban_schema=7, mat_khau="PHAI-BI-CHE"))
        finally:
            quan_sat.ket_thuc_yeu_cau()
        r = csdl.mot(f"SELECT * FROM {quan_sat.TEN_BANG} ORDER BY id DESC LIMIT 1")
        self.assertEqual(r["loai"], "trien_khai")
        self.assertEqual(r["correlation_id"], "trien-khai-01")
        self.assertNotIn("PHAI-BI-CHE", r["chi_tiet"], "bí mật vào tới CSDL quan sát")
        self.assertEqual(r["tien_trinh"], os.getpid())

    def test_g3_DDL_G11_chay_lai_duoc(self):
        """Chạy hai lần không nổ — migration nào cũng có ngày bị chạy lại."""
        kn = csdl.mo()
        with csdl.khoa_ghi:
            kn.executescript(quan_sat.DDL_G11)
            kn.executescript(quan_sat.DDL_G11)
            kn.commit()


# ===========================================================================
class H_CauHinhTrienKhai(unittest.TestCase):
    """Những khẳng định về file triển khai phải ĐO trên chính file đó, không tin trí nhớ."""

    GOC = os.path.dirname(GOC_APP)

    def test_h1_env_example_khong_chua_bi_mat_that(self):
        duong = os.path.join(self.GOC, ".env.example")
        self.assertTrue(os.path.exists(duong), ".env.example chưa tồn tại")
        noi_dung = open(duong, encoding="utf-8").read()
        # Mọi giá trị phải RÕ RÀNG LÀ GIẢ: rỗng, hoặc mang nhãn THAY-, hoặc là số/cờ.
        xau = []
        for dong in noi_dung.split("\n"):
            d = dong.strip()
            if not d or d.startswith("#") or "=" not in d:
                continue
            ten, _, gt = d.partition("=")
            if not gt:
                continue
            if gt.startswith("THAY-") or gt.isdigit() or gt in ("0", "1", "true", "false"):
                continue
            if re.match(r"^[A-Za-z0-9/_.:,-]{0,40}$", gt) and not re.search(r"[A-Za-z0-9]{24,}", gt):
                continue
            xau.append(ten)
        self.assertEqual(xau, [], f"giá trị trông như bí mật thật: {xau}")

    def test_h2_env_example_khong_co_dong_bi_mat_co_gia_tri(self):
        duong = os.path.join(self.GOC, ".env.example")
        noi_dung = open(duong, encoding="utf-8").read()
        for ten in ("VIP_HUB_BACKUP_PASSPHRASE", "VIP_HUB_KMS_KEY", "VIP_HUB_MASTER_KEY"):
            for dong in noi_dung.split("\n"):
                if dong.strip().startswith(ten + "="):
                    gt = dong.split("=", 1)[1].strip()
                    self.assertTrue(gt == "" or gt.startswith("THAY-"),
                                    f"{ten} có giá trị không phải placeholder: {gt!r}")

    def test_h3_dockerfile_khong_nhung_bi_mat(self):
        duong = os.path.join(self.GOC, "Dockerfile")
        self.assertTrue(os.path.exists(duong), "Dockerfile chưa tồn tại")
        noi_dung = open(duong, encoding="utf-8").read()
        # Không ENV/ARG nào mang giá trị trông như secret, và không COPY .env vào image.
        self.assertNotRegex(noi_dung, r"(?im)^\s*COPY\s+\.env\b",
                            "Dockerfile COPY .env vào image — bí mật nằm trong layer vĩnh viễn")
        for dong in noi_dung.split("\n"):
            if re.match(r"(?i)^\s*(ENV|ARG)\s", dong):
                # Digest image `@sha256:<64 hex>` là ĐỊNH DANH CÔNG KHAI, không phải secret.
                # Bỏ qua đúng dạng này; mọi chuỗi dài khác vẫn bị canh.
                if re.search(r"@sha256:[0-9a-f]{64}\b", dong):
                    continue
                self.assertNotRegex(dong, r"[A-Za-z0-9+/=_-]{24,}",
                                    f"ENV/ARG mang giá trị dài như secret: {dong.strip()}")

    def test_h4_dockerfile_khong_chay_bang_root(self):
        noi_dung = open(os.path.join(self.GOC, "Dockerfile"), encoding="utf-8").read()
        self.assertRegex(noi_dung, r"(?im)^\s*USER\s+(?!root\b)\S+",
                         "Dockerfile không có USER khác root")

    def test_h5_dockerignore_chan_du_lieu_va_khoa(self):
        duong = os.path.join(self.GOC, ".dockerignore")
        self.assertTrue(os.path.exists(duong), ".dockerignore chưa tồn tại")
        nd = open(duong, encoding="utf-8").read()
        for mau in (".env", "*.key", "*.db", "du-lieu", "*.vipkb"):
            self.assertIn(mau, nd, f".dockerignore thiếu {mau} — nó sẽ vào build context")

    def test_h6_compose_khong_ghi_bi_mat_truc_tiep(self):
        duong = os.path.join(self.GOC, "docker-compose.yml")
        self.assertTrue(os.path.exists(duong), "docker-compose.yml chưa tồn tại")
        nd = open(duong, encoding="utf-8").read()
        self.assertNotRegex(nd, r"(?i)(passphrase|password|secret|api_key)\s*:\s*[\"']?\S{8,}",
                            "compose ghi bí mật trực tiếp")

    def test_h7_compose_health_va_readiness_KHAC_nhau(self):
        """Gộp hai thứ là một lần báo XANH khi thực ra chưa sẵn sàng."""
        nd = open(os.path.join(self.GOC, "Dockerfile"), encoding="utf-8").read()
        # Đọc DÒNG LỆNH, bỏ dòng ghi chú. Bản đầu của ca này cắt tại chữ "HEALTHCHECK" trong một
        # dòng `#` nên nó HỎNG trên một Dockerfile ĐÚNG — phép đo tự giới hạn phạm vi rồi kết
        # luận ngoài phạm vi ấy (§12.1 luật 3). Sửa 15/10/2026.
        lenh = [d for d in nd.split("\n") if d.strip() and not d.lstrip().startswith("#")]
        khoi, dang = [], False
        for d in lenh:
            if re.match(r"(?i)^\s*HEALTHCHECK\b", d):
                dang = True
            if dang:
                khoi.append(d)
                if not d.rstrip().endswith("\\"):
                    break
        self.assertTrue(khoi, "Dockerfile không có DÒNG LỆNH HEALTHCHECK")
        sau = "\n".join(khoi)
        self.assertIn("suc-khoe", sau, "HEALTHCHECK của image không gọi đường health")
        self.assertNotIn("san-sang", sau,
                         "HEALTHCHECK dùng readiness — khởi động lại container vì CSDL chưa nâng")


if __name__ == "__main__":
    try:
        # GIỮ kết quả rồi THOÁT theo nó. `exit=False` một mình làm bộ thử
        # LUÔN thoát 0 kể cả khi có ca hỏng — cổng chặn hồi quy mất tác dụng,
        # và nó không báo gì cả (§12.2: hỏng im lặng).
        _kq = unittest.main(verbosity=2, exit=False)
    finally:
        shutil.rmtree(_tam, ignore_errors=True)
    sys.exit(0 if _kq.result.wasSuccessful() else 1)
