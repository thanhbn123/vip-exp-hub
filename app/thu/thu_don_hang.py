# Bộ thử G04 — Order Service (AG-02 ORDERS). File RIÊNG của AG-02.
# Chạy: python3 app/thu/thu_don_hang.py
#
# Gọi TRỰC TIẾP tầng don_hang + CSDL tạm (không dựng server HTTP): ca nào hỏng thì biết ngay
# hỏng ở tầng nghiệp vụ, không phải suy từ mã HTTP. Đường HTTP đã có thu_saas.py canh.
#
# Hai điều bộ thử này CỐ Ý làm khác lệ thường, nói rõ để sau không ai tưởng là sơ suất:
#
# 1) Nó TỰ chạy DDL của đợt O01 (don_hang.DDL_G04) lên CSDL tạm, vì AG-02 không được sửa
#    csdl.py/migrate.py. Lớp B (ThuChuaMigrate) chạy TRƯỚC khi áp DDL để chứng minh mã chịu
#    được CSDL chưa migrate — nếu không có lớp đó thì câu "chịu được CSDL cũ" chỉ là lời nói.
#
# 2) Ca "hãng nói không tìm thấy" chạy HAI lần, hai đường khác nhau (G13, 15/10/2026):
#    · d12 dùng adapter GIẢ nhưng phát ĐÚNG hình dạng hợp đồng (`NormalizedCarrierError.nhu_dict()`,
#      khoá `ma_chuan`) — ca này canh TÊN KHOÁ, vì đọc sai tên khoá ở `don_hang` hỏng im lặng;
#    · d12b dùng adapter THẬT `adapter_jt` (mock có sẵn nhánh `MOCK-KHONGCO…` ⇒ mã `999002000`)
#      đi hết đường `doi_soat_don`. Trước G13 hai mock không có nhánh này nên chỉ có adapter giả.
#    Ghi chú cũ ở đây nói "hai mock thật không có đường trả KHONG_TIM_THAY" — nay J&T CÓ.
import os
import sys
import tempfile
import threading
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, GOC_APP)

_tam = tempfile.mkdtemp(prefix="vip-hub-thu-don-")
os.environ["VIP_HUB_DATA"] = _tam

import adapter      # noqa: E402
import bao_mat      # noqa: E402
import csdl         # noqa: E402
import don_hang     # noqa: E402
import loi_hang     # noqa: E402
import nhap_file    # noqa: E402
import quyen        # noqa: E402

DON_MAU = {
    "nguoi_gui_ten": "Shop Thử", "nguoi_gui_sdt": "0901111111", "nguoi_gui_dia_chi": "1 Đường Gửi",
    "nguoi_nhan_ten": "Khách Thử", "nguoi_nhan_sdt": "0902222222",
    "nguoi_nhan_dia_chi": "2 Đường Nhận", "hang_hoa": "Áo thử",
    "khoi_luong_gram": 500, "cod": 150000, "gia_tri_khai": 200000,
}


def don_moi(**them):
    d = dict(DON_MAU)
    d.update(them)
    return d


def ap_ddl():
    """Chạy DDL O01 lên CSDL tạm (thay cho migration của AG-00). Chịu được chạy nhiều lần."""
    kn = csdl.mo()
    for cau in don_hang.DDL_G04.split(";"):
        cau = cau.strip()
        if not cau:
            continue
        try:
            kn.execute(cau)
        except Exception as e:                       # noqa: BLE001
            # ALTER TABLE ADD COLUMN trùng tên là bình thường khi chạy lại; mọi lỗi khác thì
            # NÓI RA, không nuốt (CLAUDE.md §12.2: cấm nuốt lỗi).
            if "duplicate column name" not in str(e):
                raise AssertionError(f"DDL G04 hỏng ở câu: {cau[:70]}… → {e}")
    kn.commit()
    don_hang.quen_cache_schema()


def dung_nen(ma_tenant, goi="pro"):
    """Một tenant + bốn vai trò + một tài khoản hãng mock. Trả dict."""
    tid = csdl.ghi("INSERT INTO tenants (code, ten, goi_id, tao_luc) VALUES (?,?,?,?)",
                   (ma_tenant, f"Tenant {ma_tenant}", goi, csdl.bay_gio())).lastrowid
    users = {}
    for vt, nhan in (("TENANT_OWNER", "owner"), ("TENANT_STAFF", "staff"),
                     ("TENANT_VIEWER", "viewer")):
        uid = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                       " VALUES (?,?,?,?)",
                       (f"{nhan}-{ma_tenant}", "x", nhan, csdl.bay_gio())).lastrowid
        csdl.ghi("INSERT INTO tenant_memberships (user_id, tenant_id, role, tao_luc)"
                 " VALUES (?,?,?,?)", (uid, tid, vt, csdl.bay_gio()))
        users[nhan] = uid
    # người KHÔNG có membership — dùng để kiểm rằng tầng nghiệp vụ tự chặn, không chỉ route chặn
    users["ngoai"] = csdl.ghi("INSERT INTO users (ten_dang_nhap, mat_khau_hash, ho_ten, tao_luc)"
                              " VALUES (?,?,?,?)",
                              (f"ngoai-{ma_tenant}", "x", "ngoai", csdl.bay_gio())).lastrowid
    tk = {}
    for hang in ("jt", "vtp"):
        cred, duoi = bao_mat.luu_credentials({"customerCode": "c", "password": "p",
                                              "apiAccount": "a", "privateKey": "k"},
                                             bao_mat.aad_credentials(tid, hang))
        wh = f"wh-{ma_tenant}-{hang}"
        tk[hang] = csdl.ghi(
            "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
            "credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc) VALUES (?,?,?,?,?,?,?,?,?)",
            (tid, hang, hang.upper(), "mock", cred, duoi, wh,
             bao_mat.ma_hoa("s", bao_mat.aad_webhook(wh)), csdl.bay_gio())).lastrowid
    return {"tid": tid, "u": users, "tk": tk}


def seed_chung():
    csdl.mo()
    quyen.seed()
    import json as _json
    for ma, h in adapter.danh_sach_hang().items():
        csdl.ghi("INSERT OR IGNORE INTO carrier_providers (ma,ten,capabilities_json,live_mo,"
                 "cap_nhat_luc) VALUES (?,?,?,?,?)",
                 (ma, h["ten"], _json.dumps(h["capabilities"]), 0, csdl.bay_gio()))


# =============================================================================
# A — CHƯA MIGRATE: mã phải chạy được trên CSDL cũ (chạy ĐẦU TIÊN, cố ý)
# =============================================================================
class A_ChuaMigrate(unittest.TestCase):
    """Lớp này chạy trước khi ap_ddl() — tên lớp bắt đầu bằng A để unittest chạy trước.

    Nó là bằng chứng cho câu "mã chịu được CSDL chưa migrate" trong báo cáo. Không có lớp này
    thì câu đó là lời nói không có phép đo.
    """
    @classmethod
    def setUpClass(cls):
        seed_chung()
        don_hang.quen_cache_schema()
        cls.n = dung_nen("CM")

    def test_a01_tao_va_duyet_duoc_khi_thieu_cot_moi(self):
        self.assertFalse(don_hang.co_cot("don_hang", "external_reference"),
                         "CSDL tạm đã có cột mới — lớp A mất ý nghĩa, kiểm lại thứ tự chạy")
        don, trung = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"],
                                      don_moi(external_reference="EXT-1"))
        self.assertFalse(trung)
        self.assertEqual(don["trang_thai"], "nhap")
        d2 = don_hang.duyet_don(self.n["tid"], self.n["u"]["owner"], don["id"])
        self.assertEqual(d2["trang_thai"], "da_duyet")

    def test_a02_tu_choi_bao_501_chu_khong_am_tham_mat_ly_do(self):
        """Thiếu cột `ly_do_tu_choi` thì PHẢI báo 501, không được ghi 'nhap' rồi bỏ lý do:
        lý do chính là toàn bộ giá trị của hành động từ chối."""
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.tu_choi_don(self.n["tid"], self.n["u"]["owner"], don["id"], "sai địa chỉ")
        self.assertEqual(e.exception.ma, 501)
        self.assertEqual(don_hang.lay_don(self.n["tid"], don["id"])["trang_thai"], "nhap")

    def test_a03_mat_hang_bao_501_va_lay_tra_rong(self):
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        self.assertFalse(don_hang.co_tinh_nang_mat_hang())
        self.assertEqual(don_hang.lay_mat_hang(self.n["tid"], don["id"]), [])
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"],
                                  [{"ten": "A", "so_luong": 1}])
        self.assertEqual(e.exception.ma, 501)

    def test_a04_tim_don_noi_ro_dieu_kien_bi_bo(self):
        """Lọc theo cột chưa có thì phải NÓI là đã bỏ, không im lặng trả rộng hơn người hỏi."""
        kq = don_hang.tim_don(self.n["tid"], {"external_reference": "EXT-1"})
        self.assertTrue(any("external_reference" in x for x in kq["loc_bo_qua"]),
                        f"không báo điều kiện bị bỏ: {kq['loc_bo_qua']}")


# =============================================================================
# B — MÔ HÌNH DỮ LIỆU, TIỀN, VALIDATE
# =============================================================================
class B_MoHinhDuLieu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_chung()
        ap_ddl()
        cls.n = dung_nen("MH")

    def test_b01_tien_la_so_nguyen_dong_khong_co_float(self):
        """Quy ước O01: tiền là SỐ NGUYÊN theo đồng. Số có phần thập phân bị CHẶN, không cắt cụt."""
        for xau in (150000.7, "150000.7", "150000,5"):
            with self.assertRaises(don_hang.LoiNghiepVu, msg=f"{xau!r} lọt qua"):
                don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi(cod=xau))
        # số thực nguyên (JSON hay gửi 150000.0) thì nhận và lưu thành int
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi(cod=150000.0))
        self.assertIsInstance(don["cod"], int)
        self.assertEqual(don["cod"], 150000)

    def test_b02_cot_tien_trong_csdl_la_INTEGER(self):
        """Canh ngay ở schema: cột tiền phải INTEGER. REAL là mở cửa cho float."""
        kieu = {r["name"]: r["type"].upper()
                for r in csdl.nhieu("PRAGMA table_info(don_hang)")}
        for c in ("cod", "gia_tri_khai", "phi_van_chuyen", "khoi_luong_gram"):
            self.assertEqual(kieu[c], "INTEGER", f"{c} không phải INTEGER")
        kieu_mh = {r["name"]: r["type"].upper()
                   for r in csdl.nhieu("PRAGMA table_info(don_mat_hang)")}
        for c in ("don_gia", "so_luong", "khoi_luong_gram"):
            self.assertEqual(kieu_mh[c], "INTEGER", f"don_mat_hang.{c} không phải INTEGER")

    def test_b03_validate_rieng_khong_doi_gi_trong_csdl(self):
        kq = don_hang.kiem_don(self.n["tid"], d=don_moi(nguoi_nhan_sdt="123", cod=-5))
        self.assertFalse(kq["hop_le"])
        self.assertTrue(any("nguoi_nhan_sdt" in x for x in kq["loi"]))
        self.assertTrue(any("cod" in x for x in kq["loi"]))
        truoc = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?",
                         (self.n["tid"],))["c"]
        don_hang.kiem_don(self.n["tid"], d=don_moi())
        sau = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (self.n["tid"],))["c"]
        self.assertEqual(truoc, sau, "kiem_don đã ghi vào CSDL — nó phải chỉ ĐỌC")

    def test_b04_canh_bao_khac_loi(self):
        """Cảnh báo không chặn lưu. Trộn cảnh báo vào lỗi là làm người dùng bỏ qua cả hai."""
        kq = don_hang.kiem_don(self.n["tid"], d=don_moi(gia_tri_khai=0))
        self.assertTrue(kq["hop_le"])
        self.assertTrue(any("COD" in x or "thu hộ" in x for x in kq["canh_bao"]))

    def test_b05_external_reference_va_dia_chi_co_cau_truc_duoc_luu(self):
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi(
            external_reference="SHOPEE-999", nguoi_nhan_tinh="Hà Nội",
            nguoi_nhan_quan="Cầu Giấy", nguoi_nhan_xa="Dịch Vọng",
            nguoi_nhan_buu_chinh="100000"))
        self.assertEqual(don["external_reference"], "SHOPEE-999")
        self.assertEqual(don["nguoi_nhan_tinh"], "Hà Nội")
        self.assertEqual(don["nguoi_nhan_buu_chinh"], "100000")
        kq = don_hang.tim_don(self.n["tid"], {"external_reference": "SHOPEE-999"})
        self.assertEqual([x["id"] for x in kq["don"]], [don["id"]])
        self.assertEqual(kq["loc_bo_qua"], [])

    def test_b06_approved_by_duoc_ghi_khi_duyet(self):
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        d = don_hang.duyet_don(self.n["tid"], self.n["u"]["owner"], don["id"])
        self.assertEqual(d["approved_by"], self.n["u"]["owner"])
        self.assertIsNotNone(d["approved_luc"])

    def test_b07_mat_hang_nhieu_mon_va_tong_khop_voi_don(self):
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        kq = don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"], [
            {"ten": "Áo", "ma_sku": "AO-1", "so_luong": 2, "don_gia": 120000,
             "khoi_luong_gram": 250},
            {"ten": "Quần", "so_luong": 1, "don_gia": 300000, "khoi_luong_gram": 400},
        ])
        self.assertEqual(len(kq["mat_hang"]), 2)
        self.assertEqual(kq["tong_khoi_luong_gram"], 2 * 250 + 400)
        self.assertEqual(kq["tong_gia_tri_dong"], 2 * 120000 + 300000)
        # tổng PHẢI đồng bộ về đơn — hai con số nói hai chuyện khác nhau là họ hỏng im lặng
        self.assertEqual(kq["don"]["khoi_luong_gram"], kq["tong_khoi_luong_gram"])
        self.assertEqual(kq["don"]["gia_tri_khai"], kq["tong_gia_tri_dong"])

    def test_b08_mat_hang_thay_toan_bo_khong_cong_don(self):
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"],
                              [{"ten": "A", "so_luong": 1, "don_gia": 1, "khoi_luong_gram": 10}])
        kq = don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"],
                                   [{"ten": "B", "so_luong": 1, "don_gia": 2,
                                     "khoi_luong_gram": 20}])
        self.assertEqual([m["ten"] for m in kq["mat_hang"]], ["B"])

    def test_b09_mat_hang_tien_float_bi_chan(self):
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"],
                                  [{"ten": "A", "so_luong": 1, "don_gia": 1.5,
                                    "khoi_luong_gram": 10}])

    def test_b10_khong_sua_mat_hang_sau_khi_gui(self):
        don = _don_da_gui(self.n, "vtp")
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"],
                                  [{"ten": "A", "so_luong": 1}])
        self.assertEqual(e.exception.ma, 409)


def _don_da_gui(n, hang="vtp", **them):
    don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(**them))
    don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
    return don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"][hang])


def _suat_don(n):
    """Số suất đơn đã dùng của tenant trong tháng. 0 nếu chưa có dòng `usage_thang`."""
    r = csdl.mot("SELECT so_don FROM usage_thang WHERE tenant_id=? AND thang=?",
                 (n["tid"], csdl.thang_nay()))
    return r["so_don"] if r else 0


# =============================================================================
# C — VÒNG ĐỜI: ánh xạ, chuyển hợp lệ/không hợp lệ, từ chối, vết audit
# =============================================================================
class C_VongDoi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_chung()
        ap_ddl()
        cls.n = dung_nen("VD")

    def test_c01_hai_truc_khong_bi_gop(self):
        """Hợp đồng mục 10: hai trục tách nhau. Canh bằng chính tập giá trị, không bằng niềm tin."""
        import cau_hinh
        self.assertEqual(set(don_hang.CHUYEN_DUOC),
                         {"nhap", "da_duyet", "dang_gui", "da_gui", "huy"},
                         "trục NGHIỆP VỤ đã mọc/mất giá trị — phá hợp đồng mục 10")
        giao = {ttg for _, _, ttg, _ in don_hang.ANH_XA_MO_RONG if ttg}
        self.assertEqual(giao, set(cau_hinh.HANG_TRANG_THAI_GIAO),
                         "bảng ánh xạ mở rộng lệch với cau_hinh.HANG_TRANG_THAI_GIAO")
        self.assertFalse(giao & set(don_hang.CHUYEN_DUOC),
                         "một giá trị nằm ở CẢ HAI trục — đúng dấu hiệu hai trục bị gộp")

    def test_c02_anh_xa_mo_rong_du_tung_tinh_trang(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi())
        self.assertEqual(don_hang.trang_thai_mo_rong(don), "PENDING_APPROVAL")
        # DRAFT = nháp nhưng CHƯA hợp lệ (sửa thẳng CSDL để dựng tình trạng đó)
        csdl.ghi("UPDATE don_hang SET hang_hoa='' WHERE id=? AND tenant_id=?", (don["id"], n["tid"]))
        self.assertEqual(don_hang.trang_thai_mo_rong(don_hang.lay_don(n["tid"], don["id"])),
                         "DRAFT")
        csdl.ghi("UPDATE don_hang SET hang_hoa='Áo' WHERE id=? AND tenant_id=?",
                 (don["id"], n["tid"]))
        d = don_hang.tu_choi_don(n["tid"], n["u"]["owner"], don["id"], "thiếu số nhà")
        self.assertEqual(don_hang.trang_thai_mo_rong(d), "REJECTED")
        d = don_hang.sua_don(n["tid"], n["u"]["staff"], don["id"],
                             {"nguoi_nhan_dia_chi": "2 Đường Nhận, số 9"})
        self.assertEqual(don_hang.trang_thai_mo_rong(d), "PENDING_APPROVAL",
                         "sửa xong vẫn mắc ở REJECTED — lý do cũ không được xóa")
        d = don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        self.assertEqual(don_hang.trang_thai_mo_rong(d), "APPROVED")
        d = don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        self.assertEqual(don_hang.trang_thai_mo_rong(d), "SUBMITTED")
        for loai, ten in (("lay_hang", "PICKED_UP"), ("dang_giao", "IN_TRANSIT"),
                          ("giao_thanh_cong", "DELIVERED")):
            don_hang.ap_trang_thai_giao(don["tenant_id"], don["id"], loai, "he_thong")
            self.assertEqual(
                don_hang.trang_thai_mo_rong(don_hang.lay_don(n["tid"], don["id"])), ten)

    def test_c03_chuyen_trang_thai_sai_bi_chan(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi())
        # gửi khi chưa duyệt
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        self.assertEqual(e.exception.ma, 409)
        self.assertEqual(don_hang.lay_don(n["tid"], don["id"])["trang_thai"], "nhap")
        # duyệt hai lần
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        self.assertEqual(e.exception.ma, 409)
        # huy là trạng thái CUỐI: không duyệt lại, không sửa, không gửi
        don_hang.huy_don(n["tid"], n["u"]["owner"], don["id"])
        for ham, dt in ((don_hang.duyet_don, ()), (don_hang.sua_don, ({"hang_hoa": "X"},)),
                        (don_hang.gui_don, (n["tk"]["vtp"],))):
            with self.assertRaises(don_hang.LoiNghiepVu, msg=f"{ham.__name__} lọt qua sau khi hủy"):
                ham(n["tid"], n["u"]["owner"], don["id"], *dt)

    def test_c04_kiem_chuyen_phu_dung_bang(self):
        """Máy trạng thái là danh sách TRẮNG: mọi cặp ngoài bảng phải bị chặn."""
        for cu in don_hang.CHUYEN_DUOC:
            for moi in ("nhap", "da_duyet", "dang_gui", "da_gui", "huy"):
                if moi in don_hang.CHUYEN_DUOC[cu]:
                    don_hang.kiem_chuyen(cu, moi)
                else:
                    with self.assertRaises(don_hang.LoiNghiepVu, msg=f"{cu}→{moi} lọt qua"):
                        don_hang.kiem_chuyen(cu, moi)
        self.assertEqual(don_hang.CHUYEN_DUOC["huy"], set(), "huy phải là trạng thái CUỐI")

    def test_c05_moi_cap_chuyen_deu_khai_quyen(self):
        """Quên khai quyền cho một chuyển trạng thái = chuyển đó không ai kiểm. Canh bằng bảng."""
        thieu = [(cu, moi) for cu, ds in don_hang.CHUYEN_DUOC.items() for moi in ds
                 if (cu, moi) not in don_hang.QUYEN_CHUYEN]
        self.assertEqual(thieu, [], f"chuyển trạng thái chưa khai quyền: {thieu}")
        for perm in set(don_hang.QUYEN_CHUYEN.values()):
            self.assertIn(perm, quyen.QUYEN, f"quyền '{perm}' không có trong bảng quyền")

    def test_c06_tu_choi_bat_buoc_co_ly_do_va_ghi_vet(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi())
        for xau in ("", "   ", None):
            with self.assertRaises(don_hang.LoiNghiepVu):
                don_hang.tu_choi_don(n["tid"], n["u"]["owner"], don["id"], xau)
        d = don_hang.tu_choi_don(n["tid"], n["u"]["owner"], don["id"], "địa chỉ thiếu số nhà")
        self.assertEqual(d["trang_thai"], "nhap", "từ chối KHÔNG được thêm enum mới vào trang_thai")
        self.assertEqual(d["ly_do_tu_choi"], "địa chỉ thiếu số nhà")
        self.assertEqual(d["tu_choi_boi"], n["u"]["owner"])
        ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don["id"],))
        self.assertTrue(any("TỪ CHỐI" in r["noi_dung"] for r in ls), "từ chối không có vết lịch sử")
        au = csdl.nhieu("SELECT * FROM audit WHERE tenant_id=? AND hanh_dong='don_tu_choi'",
                        (n["tid"],))
        self.assertTrue(au, "từ chối không có vết audit")

    def test_c07_tu_choi_don_da_duyet_thi_bo_duyet(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi())
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        d = don_hang.tu_choi_don(n["tid"], n["u"]["owner"], don["id"], "đổi ý")
        self.assertEqual(d["trang_thai"], "nhap")
        self.assertIsNone(d["approved_by"], "bỏ duyệt mà approved_by còn lại — dấu vết nói sai")

    def test_c08_khong_tu_choi_duoc_don_da_gui(self):
        don = _don_da_gui(self.n, "vtp")
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.tu_choi_don(self.n["tid"], self.n["u"]["owner"], don["id"], "muộn rồi")
        self.assertEqual(e.exception.ma, 409)

    def test_c09_duyet_don_chua_hop_le_bi_chan(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi())
        csdl.ghi("UPDATE don_hang SET nguoi_nhan_sdt='123' WHERE id=? AND tenant_id=?",
                 (don["id"], n["tid"]))
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        self.assertIn("chưa hợp lệ", str(e.exception))

    def test_c10_moi_lan_doi_trang_thai_deu_co_mot_dong_lich_su(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi())
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        don_hang.huy_don(n["tid"], n["u"]["owner"], don["id"])
        ls = [r["noi_dung"] for r in csdl.nhieu(
            "SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don["id"],))]
        self.assertTrue(any("tạo đơn" in x for x in ls))
        self.assertTrue(any("duyệt đơn" in x for x in ls))
        self.assertTrue(any("xác nhận" in x for x in ls))
        self.assertTrue(any("hủy đơn" in x for x in ls))


# =============================================================================
# D — IDEMPOTENCY, GỬI ĐỒNG THỜI, KẾT QUẢ KHÔNG RÕ, ĐỐI SOÁT
# =============================================================================
class D_IdemVaDoiSoat(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_chung()
        ap_ddl()
        cls.n = dung_nen("DS")

    def test_d01_UNIQUE_tenant_idem_key_do_CSDL_cuong_che(self):
        """Idempotency do CSDL cưỡng chế, KHÔNG bằng `if`. Đo hai cách, cố ý.

        Cách 1 đọc câu CREATE TABLE thật trong sqlite_master — không đọc `csdl.SCHEMA` trong
        mã nguồn, vì hằng số trong mã có thể đúng mà CSDL đang chạy lại là bản cũ.
        Cách 2 là phép đo ĐỘC LẬP với toàn bộ mã `don_hang`: INSERT thẳng vào bảng, đi vòng
        qua mọi lớp kiểm của Python. Nếu ràng buộc bị gỡ, cách 2 sẽ KHÔNG ném lỗi — còn cách 1
        vẫn đạt nếu ai đó chỉ sửa chuỗi SCHEMA. Một cách thôi là chưa đủ (§12.1).
        """
        import sqlite3 as _sq
        ddl = csdl.mot("SELECT sql FROM sqlite_master WHERE type='table' AND name='don_hang'")["sql"]
        self.assertRegex(" ".join(ddl.split()), r"UNIQUE\s*\(\s*tenant_id\s*,\s*idem_key\s*\)",
                         "CSDL đang chạy KHÔNG có UNIQUE(tenant_id, idem_key)")
        n = self.n
        d, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(), idem_key="CUONG-CHE-1")
        with self.assertRaises(_sq.IntegrityError,
                               msg="CSDL KHÔNG chặn idem_key trùng — idempotency chỉ còn là `if`"):
            csdl.ghi("INSERT INTO don_hang (tenant_id, ma_don, idem_key, nguoi_gui_ten,"
                     " nguoi_gui_sdt, nguoi_gui_dia_chi, nguoi_nhan_ten, nguoi_nhan_sdt,"
                     " nguoi_nhan_dia_chi, hang_hoa, khoi_luong_gram, nguoi_tao, tao_luc,"
                     " cap_nhat_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                     (n["tid"], "TRUNG-TAY-1", "CUONG-CHE-1", "a", "0901111111", "x",
                      "b", "0902222222", "y", "z", 100, n["u"]["staff"],
                      csdl.bay_gio(), csdl.bay_gio()))
        self.assertEqual(csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=? AND idem_key=?",
                                  (n["tid"], "CUONG-CHE-1"))["c"], 1)
        self.assertIsNotNone(d["id"])

    def test_d02_idem_key_trung_tra_don_cu(self):
        n = self.n
        d1, t1 = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(), idem_key="K-1")
        d2, t2 = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(hang_hoa="Khác"),
                                  idem_key="K-1")
        self.assertFalse(t1)
        self.assertTrue(t2)
        self.assertEqual(d1["id"], d2["id"])
        self.assertEqual(d2["hang_hoa"], "Áo thử", "đơn cũ bị ghi đè bởi lượt trùng")

    def test_d03_idem_key_cung_ten_o_hai_tenant_la_hai_don(self):
        """idem_key chỉ duy nhất TRONG tenant. Trùng chéo tenant phải là hai đơn khác nhau."""
        n2 = dung_nen("DS2")
        a, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi(), idem_key="CHUNG")
        b, _ = don_hang.tao_don(n2["tid"], n2["u"]["staff"], don_moi(), idem_key="CHUNG")
        self.assertNotEqual(a["id"], b["id"])

    def test_d04_tao_don_song_song_cung_idem_key_chi_ra_mot_don(self):
        n = self.n
        ket, loi = [], []

        def chay():
            try:
                ket.append(don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(),
                                            idem_key="SONG-SONG-1"))
            except Exception as e:                      # noqa: BLE001
                loi.append(e)
            finally:
                csdl.dong()

        ts = [threading.Thread(target=chay) for _ in range(6)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(loi, [], f"lượt song song ném lỗi: {loi}")
        ids = {d["id"] for d, _ in ket}
        self.assertEqual(len(ids), 1, f"6 lượt song song sinh {len(ids)} đơn khác nhau")
        so = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=? AND idem_key=?",
                      (n["tid"], "SONG-SONG-1"))["c"]
        self.assertEqual(so, 1)

    def test_d05_GUI_DONG_THOI_khong_sinh_hai_van_don(self):
        """Ca quan trọng nhất của O04.

        Trước bản này `gui_don` ĐỌC trạng thái rồi mới GHI, nên hai lượt song song đều thấy
        `da_duyet` và cả hai đều gọi createOrder ⇒ hai vận đơn cho một đơn, mất tiền thật và
        KHÔNG có gì báo. Bản này chiếm đơn bằng một câu UPDATE có điều kiện `trang_thai='da_duyet'`.
        """
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi())
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        hang_rao = threading.Barrier(4)
        xong, loi = [], []
        # Đếm số lần hãng THẬT SỰ bị gọi — đây mới là thứ quyết định có vận đơn trùng hay không.
        so_lan_goi_hang = [0]
        import adapter_vtp
        goc_createOrder = adapter_vtp.AdapterVTP.createOrder

        def dem_createOrder(self_ad, d):
            so_lan_goi_hang[0] += 1
            return goc_createOrder(self_ad, d)

        adapter_vtp.AdapterVTP.createOrder = dem_createOrder
        self.addCleanup(setattr, adapter_vtp.AdapterVTP, "createOrder", goc_createOrder)

        def chay():
            try:
                hang_rao.wait(timeout=5)
                xong.append(don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"]))
            except don_hang.LoiNghiepVu as e:
                loi.append(e)
            finally:
                csdl.dong()

        ts = [threading.Thread(target=chay) for _ in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        # Bất biến THẬT cần giữ: hãng chỉ được gọi ĐÚNG MỘT LẦN và đơn chỉ có MỘT mã vận đơn.
        # KHÔNG đếm "số lượt trả về thành công": luồng thua đến SAU khi luồng thắng đã xong thì
        # gui_don trả về đơn đã gửi theo đúng nghĩa idempotent — không gọi hãng, không sinh vận
        # đơn mới. Đếm nó là lỗi làm ca thử chập chờn ~1/8 lượt (AG-00 đo 15 lượt × 4 luồng:
        # hãng bị gọi đúng 15 lần, 0 lượt gọi 2 lần).
        self.assertEqual(so_lan_goi_hang[0], 1,
                         f"hãng bị gọi {so_lan_goi_hang[0]} lần — phải đúng 1 (vận đơn trùng!)")
        self.assertGreaterEqual(len(xong), 1, "không lượt nào gửi được")
        ma_vd = {d["ma_van_don"] for d in xong if d.get("ma_van_don")}
        self.assertEqual(len(ma_vd), 1, f"sinh {len(ma_vd)} mã vận đơn — phải đúng 1: {ma_vd}")
        self.assertEqual(len(xong) + len(loi), 4, "thiếu lượt")
        for e in loi:
            self.assertEqual(e.ma, 409, f"lượt thua trả mã {e.ma}, phải là 409")
        d = don_hang.lay_don(n["tid"], don["id"])
        self.assertEqual(d["trang_thai"], "da_gui")
        self.assertIsNotNone(d["ma_van_don"])
        # đúng MỘT dòng lịch sử nói hãng xác nhận ⇒ đúng một lượt gọi createOrder
        xn = [r for r in csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=?", (don["id"],))
              if "xác nhận" in r["noi_dung"]]
        self.assertEqual(len(xn), 1, f"có {len(xn)} lượt hãng xác nhận — nghi tạo vận đơn trùng")

    def test_d06_gui_lai_don_da_gui_khong_goi_hang_khong_tang_usage(self):
        n = self.n
        don = _don_da_gui(n, "vtp")
        u1 = csdl.mot("SELECT so_don FROM usage_thang WHERE tenant_id=? AND thang=?",
                      (n["tid"], csdl.thang_nay()))["so_don"]
        d2 = don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        u2 = csdl.mot("SELECT so_don FROM usage_thang WHERE tenant_id=? AND thang=?",
                      (n["tid"], csdl.thang_nay()))["so_don"]
        self.assertEqual(d2["ma_van_don"], don["ma_van_don"])
        self.assertEqual(u1, u2, "gửi lại đơn đã gửi vẫn tăng usage")

    def test_d07_timeout_giu_dang_gui_va_bat_co(self):
        """Bất biến hợp đồng: 'không rõ' KHÔNG phải thành công, cũng KHÔNG phải thất bại."""
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        d = don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        self.assertEqual(d["trang_thai"], "dang_gui")
        self.assertEqual(d["can_doi_soat_ket_qua"], 1)
        self.assertIsNone(d["ma_van_don"])
        self.assertEqual(don_hang.trang_thai_mo_rong(d), "SUBMIT_UNKNOWN")
        self.assertIn(don["id"], [x["id"] for x in don_hang.don_can_doi_soat(n["tid"])])

    def test_d08_khong_gui_lai_khi_chua_doi_soat(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        self.assertEqual(e.exception.ma, 409)
        self.assertIn("đối soát", str(e.exception))
        # hủy cũng bị chặn: hủy khi chưa biết là có thể bỏ lại vận đơn sống ở hãng
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.huy_don(n["tid"], n["u"]["owner"], don["id"])

    def test_d09_doi_soat_hang_da_nhan_thi_sang_da_gui(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        kq = don_hang.doi_soat_don(n["tid"], n["u"]["owner"], don["id"])
        self.assertEqual(kq["ket_luan"], "da_vao")
        self.assertEqual(kq["thao_tac"], "getOrder", "VTP khai getOrder=True mà lại dùng đường khác")
        self.assertTrue(kq["la_mock"], "kết quả đối soát mock phải tự nhận là mock")
        self.assertEqual(kq["don"]["trang_thai"], "da_gui")
        self.assertEqual(kq["don"]["can_doi_soat_ket_qua"], 0)
        self.assertIsNotNone(kq["don"]["ma_van_don"])

    def test_d10_doi_soat_jt_dung_trackOrder_vi_getOrder_False(self):
        """Không được GIẢ ĐỊNH hãng có getOrder. J&T khai getOrder=False → phải dùng trackOrder."""
        n = self.n
        ad = adapter.tao_adapter("jt", {"customerCode": "c"}, "mock")
        self.assertFalse(ad.capability("getOrder"))
        self.assertEqual(don_hang.thao_tac_doi_soat(ad), "trackOrder")
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["jt"])
        kq = don_hang.doi_soat_don(n["tid"], n["u"]["owner"], don["id"])
        self.assertEqual(kq["thao_tac"], "trackOrder")
        self.assertEqual(kq["ket_luan"], "da_vao")

    def test_d11_ton_trong_co_KHOA_CHONG_TRUNG_cua_tung_hang(self):
        """Cờ khóa chống trùng là của HÃNG, không phải thứ Order Service tự quyết."""
        ds = adapter.danh_sach_hang()
        self.assertTrue(ds["jt"]["khoa_chong_trung"], "J&T có txlogisticId — cờ phải True")
        self.assertFalse(ds["vtp"]["khoa_chong_trung"], "VTP chưa có tài liệu — cờ phải False")
        import transport
        self.assertFalse(transport.chinh_sach_cho("createOrder", False).duoc_thu_lai)
        self.assertTrue(transport.chinh_sach_cho("createOrder", True).duoc_thu_lai)

    def test_d12_hang_noi_KHONG_TIM_THAY_thi_moi_cho_gui_lai(self):
        """Canh TÊN KHOÁ: `don_hang` phải đọc `ma_chuan` (hợp đồng §5), không phải `ma`.

        Bản trước dựng adapter giả với khoá `ma` — đúng cái tên mà `don_hang` thời đó đọc, nên
        ca thử chỉ chứng minh "bộ dò khớp với chính bộ dò" và che mất chỗ lệch với
        `NormalizedCarrierError.nhu_dict()`. Nay gói lỗi được dựng BẰNG `nhu_dict()`: nếu ai
        đổi tên khoá ở một trong hai đầu, ca này đỏ ngay.
        """
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        goi_y = loi_hang.NormalizedCarrierError(
            loi_hang.KHONG_TIM_THAY, ma_goc_hang="999002000", hang="vtp", thao_tac="getOrder")
        self.assertIn("ma_chuan", goi_y.nhu_dict(), "hợp đồng §5 dùng `ma_chuan`")
        goc = adapter.CarrierAdapter.getOrder
        try:
            adapter.CarrierAdapter.getOrder = lambda self, mvd: adapter.KetQuaHang(
                False, loi="không có đơn", tho={"loi_chuan": goi_y.nhu_dict()})
            import adapter_vtp
            goc_vtp = adapter_vtp.AdapterVTP.getOrder
            adapter_vtp.AdapterVTP.getOrder = adapter.CarrierAdapter.getOrder
            kq = don_hang.doi_soat_don(n["tid"], n["u"]["owner"], don["id"])
        finally:
            adapter.CarrierAdapter.getOrder = goc
            adapter_vtp.AdapterVTP.getOrder = goc_vtp
        self.assertEqual(kq["ket_luan"], "chua_vao")
        self.assertEqual(kq["don"]["trang_thai"], "da_duyet")
        self.assertEqual(kq["don"]["can_doi_soat_ket_qua"], 0)
        # giờ mới được gửi lại
        d = don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        self.assertIn(d["trang_thai"], ("da_gui", "dang_gui"))

    def test_d12b_adapter_that_JT_bao_khong_tim_thay_thi_di_het_duong_doi_soat(self):
        """ĐỐI CHỨNG của d12: dùng adapter THẬT `adapter_jt`, không giả, không dict tự chế.

        `MOCK-KHONGCO…` là kịch bản có sẵn của mock J&T ⇒ hãng trả `999002000` ⇒ adapter phát
        `loi_chuan` với `ma_chuan=KHONG_TIM_THAY`. Trạng thái "lượt trước không rõ kết quả" được
        dựng bằng chính `gui_don` (ép timeout) rồi đặt `ma_van_don` = mã tra có tiền tố kịch bản,
        vì `ma_don` do hệ sinh nên không điều khiển được tiền tố.
        """
        import adapter_jt  # noqa: F401 — bảo đảm adapter J&T đã đăng ký
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["jt"])
        csdl.ghi("UPDATE don_hang SET ma_van_don=? WHERE id=? AND tenant_id=?",
                 ("MOCK-KHONGCO-1", don["id"], n["tid"]))
        u_truoc = _suat_don(n)
        kq = don_hang.doi_soat_don(n["tid"], n["u"]["owner"], don["id"])
        self.assertEqual(kq["thao_tac"], "trackOrder", "J&T: getOrder=False ⇒ phải tra bằng trackOrder")
        self.assertEqual(kq["ket_luan"], "chua_vao",
                         "adapter THẬT trả KHONG_TIM_THAY mà Order Service không nhận ra —"
                         " nhánh `chua_vao` chết im lặng (lệch tên khoá `ma`/`ma_chuan`)")
        self.assertEqual(kq["don"]["trang_thai"], "da_duyet")
        self.assertEqual(kq["don"]["can_doi_soat_ket_qua"], 0)
        self.assertEqual(_suat_don(n), u_truoc - 1,
                         "đối soát ra 'chưa vào' thì phải HOÀN 1 suất cho lượt gửi timeout trước")

    def test_d13_loi_LA_khong_phai_khong_tim_thay_thi_VAN_CHUA_RO(self):
        """Ca an toàn nhất của mục này: lỗi lạ KHÔNG được suy thành 'hãng chưa nhận'.

        Suy như vậy là mở đường gửi lại một đơn có thể đã vào hãng ⇒ vận đơn trùng.
        """
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        import adapter_vtp
        goc = adapter_vtp.AdapterVTP.getOrder
        try:
            adapter_vtp.AdapterVTP.getOrder = lambda self, mvd: adapter.KetQuaHang(
                False, loi="sai chữ ký",
                # Fixture dựng BẰNG `nhu_dict()` — hình dạng THẬT của hợp đồng §5 (khoá
                # `ma_chuan`). Tự gõ tay `{"ma": …}` là cách ca kiểm cũ tự làm mù chính nó.
                tho={"loi_chuan": loi_hang.NormalizedCarrierError(
                    loi_hang.XAC_THUC_HONG, ma_goc_hang="145003030", hang="vtp",
                    thao_tac="getOrder").nhu_dict()})
            kq = don_hang.doi_soat_don(n["tid"], n["u"]["owner"], don["id"])
        finally:
            adapter_vtp.AdapterVTP.getOrder = goc
        self.assertEqual(kq["ket_luan"], "van_chua_ro")
        self.assertEqual(kq["don"]["trang_thai"], "dang_gui")
        self.assertEqual(kq["don"]["can_doi_soat_ket_qua"], 1, "cờ bị tắt dù vẫn chưa rõ")
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])

    def test_d14_hang_khong_tra_duoc_thi_doi_soat_bang_NGUOI(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_timeout"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.doi_soat_tay(n["tid"], n["u"]["owner"], don["id"], "da_vao")  # thiếu mã vận đơn
        kq = don_hang.doi_soat_tay(n["tid"], n["u"]["owner"], don["id"], "da_vao",
                                   ma_van_don="VTP-NGUOI-1", ghi_chu="gọi tổng đài hãng")
        self.assertEqual(kq["nguon"], "nguoi")
        self.assertEqual(kq["don"]["ma_van_don"], "VTP-NGUOI-1")
        ls = csdl.nhieu("SELECT * FROM don_lich_su WHERE don_id=? ORDER BY id", (don["id"],))
        self.assertTrue(any("NGƯỜI kết luận" in r["noi_dung"] for r in ls),
                        "vết không nói rõ đây là kết luận của NGƯỜI, không phải của hệ")

    def test_d15_doi_soat_don_khong_can_thi_noi_thang(self):
        don = _don_da_gui(self.n, "vtp")
        kq = don_hang.doi_soat_don(self.n["tid"], self.n["u"]["owner"], don["id"])
        self.assertEqual(kq["ket_luan"], "khong_can")

    def test_d16_hang_tu_choi_thi_lui_ve_da_duyet_khong_mat_don(self):
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(ghi_chu="demo_force_fail"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["vtp"])
        self.assertEqual(e.exception.ma, 502)
        d = don_hang.lay_don(n["tid"], don["id"])
        self.assertEqual(d["trang_thai"], "da_duyet")
        self.assertEqual(d["can_doi_soat_ket_qua"], 0)

    def test_d17_hang_bao_don_DA_TON_TAI_thi_giu_dang_gui_va_KHONG_hoan_suat(self):
        """F2 (AG-00 chốt 15/10/2026): `DON_TRUNG` KHÔNG phải "hãng từ chối".

        J&T `145003204 — 订单重复` nghĩa là **lượt trước ĐÃ VÀO hãng**: vận đơn ĐANG Ở HÃNG.
        Trả đơn về `da_duyet` + hoàn suất là nói sai sự thật (nói "không có vận đơn nào"), và
        mở đường gửi lại cùng `txlogisticId` ⇒ lại DON_TRUNG ⇒ **mắc vòng**.
        Cùng mức an toàn như timeout (§10): giữ `dang_gui` + cờ đối soát, KHÔNG hoàn suất.
        """
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_trung"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        u_truoc = _suat_don(n)
        d = don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["jt"])  # KHÔNG ném
        self.assertEqual(d["trang_thai"], "dang_gui",
                         "đơn trùng KHÔNG được lùi về da_duyet — vận đơn đang ở hãng")
        self.assertEqual(d["can_doi_soat_ket_qua"], 1)
        self.assertIsNone(d["ma_van_don"], "chưa đối soát thì chưa biết mã vận đơn")
        self.assertEqual(_suat_don(n), u_truoc + 1,
                         "suất ứng với một vận đơn CÓ THẬT ⇒ KHÔNG được hoàn")
        self.assertIn(don["id"], [x["id"] for x in don_hang.don_can_doi_soat(n["tid"])],
                      "đơn phải nằm trong danh sách chờ đối soát")
        ls = csdl.nhieu("SELECT noi_dung FROM don_lich_su WHERE don_id=? ORDER BY id", (don["id"],))
        vet = " | ".join(r["noi_dung"] for r in ls)
        self.assertIn("ĐÃ TỒN TẠI", vet, f"vết không nói rõ hãng báo đơn đã tồn tại: {vet}")
        self.assertIn("KHÔNG gửi lại mù", vet)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:      # chưa đối soát thì không gửi lại
            don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["jt"])
        self.assertEqual(e.exception.ma, 409)

    def test_d18_DOI_CHUNG_hang_tu_choi_that_thi_VAN_hoan_suat(self):
        """ĐỐI CHỨNG của d17: nếu bản vá chỉ đơn giản là "giữ tất cả ở `dang_gui`" thì ca d17
        vẫn xanh mà hành vi đúng đã mất. Ca này khẳng định hãng TỪ CHỐI THẬT (mã khác DON_TRUNG)
        vẫn đi đường cũ: lùi `da_duyet`, tắt cờ đối soát, HOÀN 1 suất, và báo lỗi 502.
        """
        n = self.n
        don, _ = don_hang.tao_don(n["tid"], n["u"]["staff"],
                                  don_moi(ghi_chu="demo_force_fail"))
        don_hang.duyet_don(n["tid"], n["u"]["owner"], don["id"])
        u_truoc = _suat_don(n)
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.gui_don(n["tid"], n["u"]["owner"], don["id"], n["tk"]["jt"])
        self.assertEqual(e.exception.ma, 502)
        d = don_hang.lay_don(n["tid"], don["id"])
        self.assertEqual(d["trang_thai"], "da_duyet")
        self.assertEqual(d["can_doi_soat_ket_qua"], 0)
        self.assertEqual(_suat_don(n), u_truoc,
                         "hãng từ chối THẬT thì phải hoàn suất — nếu không, gửi lại mất suất oan")


# =============================================================================
# E — CÁCH LY TENANT + RBAC
# =============================================================================
class E_CachLyVaQuyen(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_chung()
        ap_ddl()
        cls.a = dung_nen("QA")
        cls.b = dung_nen("QB")

    def test_e01_don_cua_A_khong_lot_sang_B(self):
        a, b = self.a, self.b
        don, _ = don_hang.tao_don(a["tid"], a["u"]["staff"], don_moi())
        self.assertIsNotNone(don_hang.lay_don(a["tid"], don["id"]))
        self.assertIsNone(don_hang.lay_don(b["tid"], don["id"]), "đơn của A lọt sang B")
        self.assertNotIn(don["id"], [x["id"] for x in don_hang.tim_don(b["tid"])["don"]])
        for ham, dt in ((don_hang.duyet_don, ()), (don_hang.sua_don, ({"hang_hoa": "X"},)),
                        (don_hang.huy_don, ()), (don_hang.tu_choi_don, ("x",)),
                        (don_hang.gui_don, (b["tk"]["vtp"],))):
            with self.assertRaises(don_hang.LoiNghiepVu,
                                   msg=f"B gọi được {ham.__name__} lên đơn của A") as e:
                ham(b["tid"], b["u"]["owner"], don["id"], *dt)
            self.assertEqual(e.exception.ma, 404)

    def test_e02_mat_hang_khong_lot_cheo_tenant(self):
        a, b = self.a, self.b
        don, _ = don_hang.tao_don(a["tid"], a["u"]["staff"], don_moi())
        don_hang.luu_mat_hang(a["tid"], a["u"]["staff"], don["id"],
                              [{"ten": "Bí mật của A", "so_luong": 1, "khoi_luong_gram": 10}])
        self.assertEqual(don_hang.lay_mat_hang(b["tid"], don["id"]), [],
                         "mặt hàng của A đọc được từ B")
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.luu_mat_hang(b["tid"], b["u"]["owner"], don["id"], [{"ten": "X"}])

    def test_e03_khong_dung_duoc_tai_khoan_hang_cua_tenant_khac(self):
        a, b = self.a, self.b
        don, _ = don_hang.tao_don(a["tid"], a["u"]["staff"], don_moi())
        don_hang.duyet_don(a["tid"], a["u"]["owner"], don["id"])
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.gui_don(a["tid"], a["u"]["owner"], don["id"], b["tk"]["vtp"])
        self.assertEqual(e.exception.ma, 404)
        self.assertEqual(don_hang.lay_don(a["tid"], don["id"])["trang_thai"], "da_duyet",
                         "đơn bị đổi trạng thái dù tài khoản hãng không hợp lệ")

    def test_e04_viewer_khong_ghi_duoc(self):
        a = self.a
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.tao_don(a["tid"], a["u"]["viewer"], don_moi())
        self.assertEqual(e.exception.ma, 403)

    def test_e05_staff_khong_duyet_khong_gui_khong_tu_choi(self):
        """TENANT_STAFF có tenant.don.ghi nhưng KHÔNG có tenant.don.duyet."""
        a = self.a
        self.assertFalse(quyen.co_quyen("TENANT_STAFF", "tenant.don.duyet"))
        don, _ = don_hang.tao_don(a["tid"], a["u"]["staff"], don_moi())
        for ham, dt in ((don_hang.duyet_don, ()), (don_hang.huy_don, ()),
                        (don_hang.tu_choi_don, ("x",)), (don_hang.gui_don, (a["tk"]["vtp"],)),
                        (don_hang.doi_soat_don, ()), (don_hang.doi_soat_tay, ("da_vao",))):
            with self.assertRaises(don_hang.LoiNghiepVu,
                                   msg=f"staff làm được {ham.__name__}") as e:
                ham(a["tid"], a["u"]["staff"], don["id"], *dt)
            self.assertEqual(e.exception.ma, 403, f"{ham.__name__} trả {e.exception.ma}")

    def test_e06_nguoi_khong_co_membership_bi_chan_o_TANG_NGHIEP_VU(self):
        """Quyền phải được cưỡng chế ở tầng nghiệp vụ, không chỉ ở route HTTP: import engine,
        polling và mọi người gọi sau này đi thẳng vào đây."""
        a = self.a
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.tao_don(a["tid"], a["u"]["ngoai"], don_moi())
        self.assertEqual(e.exception.ma, 403)
        self.assertIsNone(don_hang.vai_tro_trong_tenant(a["tid"], a["u"]["ngoai"]))

    def test_e07_membership_vo_hieu_mat_quyen(self):
        a = self.a
        csdl.ghi("UPDATE tenant_memberships SET trang_thai='vo_hieu' WHERE user_id=? AND tenant_id=?",
                 (a["u"]["staff"], a["tid"]))
        try:
            with self.assertRaises(don_hang.LoiNghiepVu) as e:
                don_hang.tao_don(a["tid"], a["u"]["staff"], don_moi())
            self.assertEqual(e.exception.ma, 403)
        finally:
            csdl.ghi("UPDATE tenant_memberships SET trang_thai='hoat_dong'"
                     " WHERE user_id=? AND tenant_id=?", (a["u"]["staff"], a["tid"]))

    def test_e08_moi_cau_sql_cua_file_nay_deu_co_dieu_kien_tenant(self):
        """Soát TĨNH chính don_hang.py: câu SQL nào chạm `don_hang`/`don_mat_hang` mà thiếu
        `tenant_id` thì phải nằm trong danh sách được miễn CÓ LÝ DO.

        Phạm vi đã đo (§12.1 luật 5): CHỈ file app/don_hang.py; CHỈ chuỗi SQL viết thẳng
        (f-string dựng động KHÔNG nằm trong phạm vi — `tim_don` dựng động và luôn đặt
        `tenant_id=?` làm điều kiện đầu, có ca E_01 kiểm bằng hành vi thật).
        """
        import re as _re
        with open(os.path.join(GOC_APP, "don_hang.py"), encoding="utf-8") as f:
            nguon = f.read()
        mien = {
            # ap_trang_thai_giao: AG-00 đã đưa tenant_id vào chữ ký (G04-L2, 15/10) — nay hàm
            # tự lọc theo tenant, không còn dựa vào lời cam kết của người gọi.
            # Rủi ro cấu trúc đã ghi nhận ở thu_qa_soat.py (Q-10) — không phải chỗ này vá.
            "SELECT * FROM don_hang WHERE id=?",
            "UPDATE don_hang SET trang_thai_giao=?, hang_trang_thai_giao=?, cap_nhat_luc=?"
            " WHERE id=?",
        }
        mien = {" ".join(x.split()) for x in mien}
        thieu = []
        for m in _re.finditer(r"csdl\.(?:mot|nhieu|ghi)\(\s*((?:\s*\"[^\"]*\"|\s*'[^']*')+)", nguon):
            cac = _re.findall(r"\"([^\"]*)\"|'([^']*)'", m.group(1))
            sql = " ".join(x or y for x, y in cac)
            nen = " ".join(sql.split())
            if not any(b in nen for b in ("don_hang", "don_mat_hang")):
                continue
            if nen.upper().startswith(("PRAGMA", "INSERT")):
                continue
            if "tenant_id" in nen or nen in mien:
                continue
            thieu.append(nen[:140])
        self.assertEqual(thieu, [], f"câu SQL thiếu điều kiện tenant và chưa có lý do: {thieu}")


# =============================================================================
# F — TÌM KIẾM, HÀNH TRÌNH, NHÃN VẬN ĐƠN
# =============================================================================
class F_TimKiemVaTraCuu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_chung()
        ap_ddl()
        cls.n = dung_nen("TK")
        n = cls.n
        cls.ds = []
        for i in range(5):
            d, _ = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(
                nguoi_nhan_ten=f"Khách {i}", cod=10000 * (i + 1),
                external_reference=f"EXT-{i}", hang_hoa=f"Hàng {i}"))
            cls.ds.append(d)
        don_hang.duyet_don(n["tid"], n["u"]["owner"], cls.ds[0]["id"])
        cls.da_gui = don_hang.gui_don(n["tid"], n["u"]["owner"], cls.ds[0]["id"], n["tk"]["vtp"])
        don_hang.tu_choi_don(n["tid"], n["u"]["owner"], cls.ds[1]["id"], "sai địa chỉ")

    def test_f01_loc_theo_trang_thai_mot_hoac_nhieu(self):
        n = self.n
        self.assertEqual([x["id"] for x in
                          don_hang.tim_don(n["tid"], {"trang_thai": "da_gui"})["don"]],
                         [self.ds[0]["id"]])
        kq = don_hang.tim_don(n["tid"], {"trang_thai": ["nhap", "da_gui"]})
        self.assertEqual(len(kq["don"]), 5)

    def test_f02_loc_theo_trang_thai_mo_rong_va_dong_nghia(self):
        n = self.n
        kq = don_hang.tim_don(n["tid"], {"trang_thai_mo_rong": "REJECTED"})
        self.assertEqual([x["id"] for x in kq["don"]], [self.ds[1]["id"]])
        a = don_hang.tim_don(n["tid"], {"trang_thai_mo_rong": "VALIDATED"})
        b = don_hang.tim_don(n["tid"], {"trang_thai_mo_rong": "PENDING_APPROVAL"})
        self.assertEqual([x["id"] for x in a["don"]], [x["id"] for x in b["don"]],
                         "VALIDATED và PENDING_APPROVAL phải là đồng nghĩa")
        self.assertTrue(kq["ghi_chu_tong"], "phải nói rõ `tong` chưa trừ phần lọc ở Python")

    def test_f03_loc_khoang_cod_va_tim_mo(self):
        n = self.n
        kq = don_hang.tim_don(n["tid"], {"cod_tu": 20000, "cod_den": 40000})
        self.assertEqual(sorted(x["cod"] for x in kq["don"]), [20000, 30000, 40000])
        kq = don_hang.tim_don(n["tid"], {"q": "Khách 3"})
        self.assertEqual([x["id"] for x in kq["don"]], [self.ds[3]["id"]])
        kq = don_hang.tim_don(n["tid"], {"q": "Hàng 4"})
        self.assertEqual([x["id"] for x in kq["don"]], [self.ds[4]["id"]])

    def test_f04_sap_xep_chi_nhan_gia_tri_trong_danh_sach_trang(self):
        """Tên cột không tham số hóa được, nên nhận tên tự do là mở cửa SQL injection."""
        n = self.n
        for xau in ("id; DROP TABLE don_hang", "cod DESC", "lung tung"):
            with self.assertRaises(don_hang.LoiNghiepVu, msg=f"{xau!r} lọt vào ORDER BY"):
                don_hang.tim_don(n["tid"], {"sap_xep": xau})
        kq = don_hang.tim_don(n["tid"], {"sap_xep": "cod_cao"})
        cods = [x["cod"] for x in kq["don"]]
        self.assertEqual(cods, sorted(cods, reverse=True))
        self.assertIsNotNone(csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?",
                                      (n["tid"],)), "bảng don_hang còn nguyên")

    def test_f05_phan_trang_va_tran_gioi_han(self):
        n = self.n
        t1 = don_hang.tim_don(n["tid"], {"gioi_han": 2, "lech": 0, "sap_xep": "cu_nhat"})
        t2 = don_hang.tim_don(n["tid"], {"gioi_han": 2, "lech": 2, "sap_xep": "cu_nhat"})
        self.assertEqual(t1["tong"], 5)
        self.assertEqual(len(t1["don"]), 2)
        self.assertFalse({x["id"] for x in t1["don"]} & {x["id"] for x in t2["don"]})
        self.assertEqual(don_hang.tim_don(n["tid"], {"gioi_han": 99999})["gioi_han"],
                         don_hang.GIOI_HAN_TOI_DA, "không chặn trần giới hạn")

    def test_f06_loc_ngay_sai_dinh_dang_bi_chan(self):
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.tim_don(self.n["tid"], {"tu_ngay": "15/10/2026"})
        hom_nay = csdl.bay_gio()[:10]
        kq = don_hang.tim_don(self.n["tid"], {"tu_ngay": hom_nay, "den_ngay": hom_nay})
        self.assertEqual(kq["tong"], 5)

    def test_f07_hanh_trinh_co_du_hai_truc_va_khong_goi_hang(self):
        n = self.n
        don = self.da_gui
        don_hang.ap_trang_thai_giao(don["tenant_id"], don["id"], "lay_hang", "webhook:9")
        ht = don_hang.dong_thoi_gian(n["tid"], don["id"])
        self.assertEqual(ht["trang_thai_giao"], "lay_hang")
        self.assertEqual(ht["trang_thai_mo_rong"], "PICKED_UP")
        truc = {m["truc"] for m in ht["moc"]}
        self.assertEqual(truc, {"nghiep_vu", "giao_van"}, f"thiếu một trục: {truc}")
        gv = [m for m in ht["moc"] if m["truc"] == "giao_van"]
        self.assertEqual(gv[-1]["trang_thai_giao"], "lay_hang")
        self.assertEqual(gv[-1]["hang"], 2)
        self.assertIn("KHÔNG gọi hãng", ht["nguon_du_lieu"])

    def test_f08_hanh_trinh_ghi_ca_su_kien_den_muon_bi_bo(self):
        n = self.n
        don = self.da_gui
        don_hang.ap_trang_thai_giao(don["tenant_id"], don["id"], "dang_giao", "webhook:10")
        ap, ly_do = don_hang.ap_trang_thai_giao(don["tenant_id"], don["id"], "cho_lay", "webhook:11")
        self.assertEqual((ap, ly_do), (0, "out-of-order"))
        ht = don_hang.dong_thoi_gian(n["tid"], don["id"])
        self.assertTrue(any("out-of-order" in m["noi_dung"] for m in ht["moc"]),
                        "sự kiện bị bỏ không để lại vết — người xem không biết đã có nó")
        self.assertEqual(ht["trang_thai_giao"], "dang_giao")

    def test_f09_nhan_van_don_tu_nhan_la_mock(self):
        n = self.n
        md = don_hang.sieu_du_lieu_nhan_van_don(n["tid"], n["u"]["owner"], self.da_gui["id"])
        self.assertTrue(md["ho_tro_nhan"])
        self.assertTrue(md["la_mock"])
        self.assertFalse(md["nhan_that"], "nhãn mock không được nhận là nhãn thật")
        self.assertTrue(any("MOCK" in c for c in md["canh_bao"]))
        self.assertEqual(md["ma_van_don"], self.da_gui["ma_van_don"])

    def test_f10_chua_gui_thi_khong_co_nhan(self):
        n = self.n
        with self.assertRaises(don_hang.LoiNghiepVu) as e:
            don_hang.sieu_du_lieu_nhan_van_don(n["tid"], n["u"]["owner"], self.ds[2]["id"])
        self.assertEqual(e.exception.ma, 409)

    def test_f11_lay_don_day_du_gom_du_thu(self):
        n = self.n
        kq = don_hang.lay_don_day_du(n["tid"], self.ds[2]["id"])
        self.assertEqual(set(kq), {"don", "mat_hang", "hanh_trinh", "kiem",
                                   "chuyen_duoc_sang", "co_tinh_nang_mat_hang"})
        self.assertEqual(kq["don"]["trang_thai_mo_rong"], "PENDING_APPROVAL")
        self.assertEqual(kq["chuyen_duoc_sang"], sorted(don_hang.CHUYEN_DUOC["nhap"]))
        self.assertTrue(kq["kiem"]["hop_le"])


# =============================================================================
# G — O06: IMPORT → ĐƠN NHÁP
# =============================================================================
class G_ImportSangDon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        seed_chung()
        ap_ddl()
        cls.n = dung_nen("IM")

    TIEU_DE = "Người nhận,SĐT,Địa chỉ,Sản phẩm,Trọng lượng,Thu hộ"
    NGUOI_GUI = {"ten": "Shop Thử", "sdt": "0901111111", "dia_chi": "1 Đường Thử"}

    def _batch(self, *hang):
        n = self.n
        noi_dung = ("\n".join((self.TIEU_DE,) + hang) + "\n").encode()
        bid = nhap_file.tao_batch(n["tid"], n["u"]["owner"], "don.csv", noi_dung)
        dong = csdl.nhieu("SELECT * FROM import_dong WHERE batch_id=? ORDER BY stt", (bid,))
        return bid, [dict(d) for d in dong]

    def test_g01_duyet_batch_chi_sinh_don_NHAP_khong_tu_gui_hang(self):
        n = self.n
        bid, dong = self._batch("Lê Nhập,0904444444,\"4 Hẻm Nhập, HN\",Áo demo,500,150000")
        kq = nhap_file.duyet_batch(n["tid"], n["u"]["owner"], bid, [d["id"] for d in dong],
                                   self.NGUOI_GUI)
        self.assertEqual(kq["SUCCESS"], 1)
        d = csdl.mot("SELECT * FROM import_dong WHERE batch_id=?", (bid,))
        don = don_hang.lay_don(n["tid"], d["don_id"])
        self.assertEqual(don["trang_thai"], "nhap", "import TỰ GỬI hãng — cấm")
        self.assertIsNone(don["ma_van_don"])
        self.assertIsNone(don["carrier_account_id"])
        self.assertEqual(don_hang.trang_thai_mo_rong(don), "PENDING_APPROVAL")

    def test_g02_duyet_lai_cung_batch_khong_nhan_doi_don(self):
        """Chống trùng theo batch: idem_key = import-<batch>-<dong>, do UNIQUE CSDL cưỡng chế."""
        n = self.n
        bid, dong = self._batch("Trần Hai,0905555555,\"5 Ngõ Hai, HN\",Quần demo,600,0")
        ids = [d["id"] for d in dong]
        nhap_file.duyet_batch(n["tid"], n["u"]["owner"], bid, ids, self.NGUOI_GUI)
        truoc = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (n["tid"],))["c"]
        try:
            nhap_file.duyet_batch(n["tid"], n["u"]["owner"], bid, ids, self.NGUOI_GUI)
        except don_hang.LoiNghiepVu:
            pass          # máy trạng thái batch có thể chặn duyệt lại — chặn được thì càng tốt
        sau = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (n["tid"],))["c"]
        self.assertEqual(truoc, sau, "duyệt lại batch sinh thêm đơn — chống trùng hỏng")
        # và gọi thẳng tao_don với đúng idem_key cũng không sinh thêm
        d = csdl.mot("SELECT * FROM import_dong WHERE batch_id=?", (bid,))
        _, trung = don_hang.tao_don(n["tid"], n["u"]["owner"], don_moi(),
                                    idem_key=f"import-{bid}-{d['id']}")
        self.assertTrue(trung, "idem_key của import không chặn được lượt tạo trùng")

    def test_g03_idem_key_import_dung_dinh_dang_batch_dong(self):
        """Canh ĐỊNH DẠNG khóa, vì nó là thứ duy nhất chống trùng giữa hai lượt duyệt batch."""
        with open(os.path.join(GOC_APP, "nhap_file.py"), encoding="utf-8") as f:
            nguon = f.read()
        self.assertIn('idem_key=f"import-{batch_id}-{dong_id}"', nguon,
                      "định dạng idem_key của import đã đổi — chống trùng theo batch có thể hỏng")

    def test_g04_dong_loi_khong_sinh_don(self):
        n = self.n
        bid, dong = self._batch("Hợp Lệ,0906666666,\"6 Đường Sáu\",Hàng,400,0",
                                ",012,Thiếu tên,Hàng lỗi,-5,-1")
        self.assertEqual([d["trang_thai"] for d in dong], ["VALID", "INVALID"])
        kq = nhap_file.duyet_batch(n["tid"], n["u"]["owner"], bid, [d["id"] for d in dong],
                                   self.NGUOI_GUI)
        self.assertEqual(kq["SUCCESS"], 1)
        self.assertEqual(kq["bo_qua"], 1, "dòng INVALID vẫn được tạo đơn")


# =============================================================================
# H — TRACKING 23 MÃ + PHÍ HÃNG BÁO + TOÀN VẸN ĐƠN/MẶT HÀNG
# =============================================================================
class H_TrackingVaPhi(unittest.TestCase):
    """Canh phần GHÉP giữa Order Service và dữ liệu hãng:

    - bảng 23 mã BEST phải phủ đúng danh sách đã đối chiếu và ánh xạ vào ĐÚNG trục giao vận;
    - đơn đã hủy không được nhận thêm trạng thái giao (mọi webhook/polling đều đi qua đây);
    - phí hãng trả là tiền NGOÀI: không được ghi float/âm vào cột INTEGER (§16);
    - tạo đơn kèm mặt hàng hỏng không được để lại đơn mồ côi.
    """

    @classmethod
    def setUpClass(cls):
        seed_chung()
        ap_ddl()
        cls.n = dung_nen("TRK")

    def test_h01_bang_23_ma_BEST_phu_dung_danh_sach_va_anh_xa_vao_truc_giao(self):
        """23 mã là hợp đồng với hãng. Thiếu một mã = một trạng thái không ai đọc; thừa một
        mã = một mã chưa có tài liệu. Cả hai đều là bịa/ bỏ im lặng, nên đo bằng TẬP."""
        import best_hop_dong
        import cau_hinh
        ma_de_bai = (211, 203, 202, 301, 302, 303, 304, 309, 601, 604, 666, 605, 606,
                     701, 702, 703, 704, 705, 707, 708, 777, 1000, 2)
        self.assertEqual(len(best_hop_dong.BANG_MA), 23)
        self.assertEqual(set(best_hop_dong.BANG_MA), set(ma_de_bai),
                         "bảng mã BEST lệch danh sách 23 mã đã đối chiếu")
        hop_le = set(cau_hinh.HANG_TRANG_THAI_GIAO) | {"da_huy"}
        for ma, (mo_ta, chung, _can_soat) in best_hop_dong.BANG_MA.items():
            self.assertIn(chung, hop_le, f"mã {ma} ({mo_ta}) ánh xạ ra trạng thái lạ {chung!r}")
        self.assertEqual(best_hop_dong.MA_MO_LAI, 606, "mã mở lại chiều giao phải là 606")
        self.assertEqual(best_hop_dong.BANG_MA[606][1], "dang_giao")
        for ma in (777, 1000):
            self.assertNotEqual(best_hop_dong.BANG_MA[ma][1], "giao_thanh_cong",
                                f"mã {ma} là SỰ CỐ, không được coi là giao thành công")

    def test_h02_moi_trang_thai_chung_cua_23_ma_deu_di_qua_duoc_truc_giao_va_chan_lui(self):
        """Duyệt trục giao vận theo đúng thứ hạng tăng dần — chứng minh rank guard KHÔNG chặn
        oan một mã nào trong 6 trạng thái chung, và CHẶN sự kiện đến muộn."""
        import best_hop_dong
        import cau_hinh
        don = _don_da_gui(self.n, "vtp")
        da_ap = []
        for chung, hang in sorted(((d[1], cau_hinh.HANG_TRANG_THAI_GIAO[d[1]])
                                   for d in best_hop_dong.BANG_MA.values()
                                   if d[1] in cau_hinh.HANG_TRANG_THAI_GIAO),
                                  key=lambda x: x[1]):
            hien_tai = don_hang.lay_don(self.n["tid"], don["id"])["hang_trang_thai_giao"]
            if hang <= hien_tai:
                # cùng hạng (nhiều mã cùng một trạng thái chung) hoặc thấp hơn: phải bị chặn
                ap, ly_do = don_hang.ap_trang_thai_giao(self.n["tid"], don["id"], chung,
                                                         "thu:23ma")
                self.assertEqual(ap, 0, f"{chung} (hạng {hang}) lọt qua khi đang ở {hien_tai}")
                self.assertEqual(ly_do, "out-of-order")
            else:
                ap, ly_do = don_hang.ap_trang_thai_giao(self.n["tid"], don["id"], chung,
                                                         "thu:23ma")
                self.assertEqual((ap, ly_do), (1, ""), f"không áp được {chung} (hạng {hang})")
                da_ap.append(chung)
        d = don_hang.lay_don(self.n["tid"], don["id"])
        self.assertEqual((d["trang_thai_giao"], d["hang_trang_thai_giao"]), ("hoan_hang", 6))
        # `cho_lay` đã có sẵn từ lúc gửi (rank 1), nên tập "đã đi qua" là phần còn lại + nó.
        self.assertEqual(set(da_ap) | {"cho_lay"}, set(cau_hinh.HANG_TRANG_THAI_GIAO),
                         f"thiếu trạng thái chưa đi qua được: "
                         f"{set(cau_hinh.HANG_TRANG_THAI_GIAO) - set(da_ap) - {'cho_lay'}}")
        # mã 2 = đã hủy: tầng webhook ghi nhận, KHÔNG đổi trục giao vận
        ap, _ = don_hang.ap_trang_thai_giao(self.n["tid"], don["id"], "da_huy", "thu:23ma")
        self.assertEqual(ap, 0)

    def test_h03_don_da_huy_khong_nhan_trang_thai_giao(self):
        """Hủy là quyết định NGHIỆP VỤ; sự kiện giao đến sau không được đẩy đơn đã hủy đi tiếp.
        `webhook_best` đã tự chặn, nhưng `webhook.py` và `polling.py` gọi thẳng tầng này."""
        don = _don_da_gui(self.n, "vtp")
        don_hang.huy_don(self.n["tid"], self.n["u"]["owner"], don["id"])
        ap, ly_do = don_hang.ap_trang_thai_giao(self.n["tid"], don["id"], "lay_hang", "webhook:99")
        self.assertEqual((ap, ly_do), (0, "đơn đã hủy ở trục nghiệp vụ"))
        d = don_hang.lay_don(self.n["tid"], don["id"])
        self.assertEqual((d["trang_thai"], d["trang_thai_giao"]), ("huy", "cho_lay"),
                         "đơn đã hủy vẫn bị đổi trục giao vận")
        ls = csdl.nhieu("SELECT noi_dung FROM don_lich_su WHERE don_id=? ORDER BY id", (don["id"],))
        self.assertTrue(any("sau khi đơn đã hủy" in r["noi_dung"] for r in ls),
                        "sự kiện bị chặn không để lại vết")

    def _gui_voi_phi(self, phi):
        """Gửi một đơn mới với `getShippingFee` trả đúng `phi` (adapter thật, chỉ thay phí)."""
        import adapter_vtp
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        don_hang.duyet_don(self.n["tid"], self.n["u"]["owner"], don["id"])
        goc = adapter_vtp.AdapterVTP.getShippingFee
        adapter_vtp.AdapterVTP.getShippingFee = \
            lambda self, d: adapter.KetQuaHang(True, phi=phi, tho={})
        try:
            d = don_hang.gui_don(self.n["tid"], self.n["u"]["owner"], don["id"], self.n["tk"]["vtp"])
        finally:
            adapter_vtp.AdapterVTP.getShippingFee = goc
        return d

    def test_h04_phi_hang_bao_float_hoac_am_KHONG_duoc_vao_cot_tien_INTEGER(self):
        """§16: tiền là INTEGER đồng. Đo bằng `typeof()` của SQLite — không đọc lời khai."""
        truoc = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (self.n["tid"],))["c"]
        for phi_xau in (22000.5, -1500):
            d = self._gui_voi_phi(phi_xau)
            r = csdl.mot("SELECT phi_van_chuyen p, typeof(phi_van_chuyen) t FROM don_hang"
                         " WHERE id=?", (d["id"],))
            self.assertIsNone(r["p"], f"phí {phi_xau!r} đã vào đơn: {r['p']!r}")
            self.assertNotEqual(r["t"], "real", f"cột tiền thành REAL vì phí {phi_xau!r}")
            ls = csdl.nhieu("SELECT noi_dung FROM don_lich_su WHERE don_id=? ORDER BY id",
                            (d["id"],))
            self.assertTrue(any("CẢNH BÁO" in r["noi_dung"] for r in ls),
                            "phí hỏng bị bỏ im lặng — người đối soát không biết vì sao thiếu phí")
        # Đối chứng dương: số thực NGUYÊN (JSON hay gửi 22000.0) phải được nhận thành INTEGER
        d = self._gui_voi_phi(22000.0)
        r = csdl.mot("SELECT phi_van_chuyen p, typeof(phi_van_chuyen) t FROM don_hang WHERE id=?",
                     (d["id"],))
        self.assertEqual((r["p"], r["t"]), (22000, "integer"))

    def test_h05_tao_don_voi_mat_hang_hong_KHONG_de_lai_don_mo_coi(self):
        """Lỗi đo 2026-10-19: đơn được ghi trước, `luu_mat_hang` hỏng sau ⇒ đơn mồ côi. Lượt
        thử lại cùng `idem_key` còn nhận đúng cái đơn không có mặt hàng nào."""
        n = self.n
        truoc = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (n["tid"],))["c"]
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.tao_don(n["tid"], n["u"]["staff"],
                             don_moi(mat_hang=[{"ten": "", "so_luong": 1}]), idem_key="K-MO-COI")
        sau = csdl.mot("SELECT COUNT(*) c FROM don_hang WHERE tenant_id=?", (n["tid"],))["c"]
        self.assertEqual(sau, truoc, "tạo đơn hỏng mặt hàng vẫn để lại đơn mồ côi")
        d, trung = don_hang.tao_don(n["tid"], n["u"]["staff"], don_moi(mat_hang=[
            {"ten": "Áo", "so_luong": 1, "don_gia": 1000, "khoi_luong_gram": 100}]),
            idem_key="K-MO-COI")
        self.assertFalse(trung, "lượt thử lại nhận đơn mồ côi của lượt hỏng")
        self.assertEqual(len(don_hang.lay_mat_hang(n["tid"], d["id"])), 1)

    def test_h06_luu_mat_hang_dong_bo_tong_ke_ca_khi_tong_bang_0(self):
        """Docstring `luu_mat_hang` cam kết tổng của đơn = tổng mặt hàng. Bản cũ bỏ qua lần
        đồng bộ khi tổng khối lượng = 0, để đơn giữ khối lượng/giá trị CŨ."""
        don, _ = don_hang.tao_don(self.n["tid"], self.n["u"]["staff"], don_moi())
        don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"],
                              [{"ten": "A", "so_luong": 1, "don_gia": 1000,
                                "khoi_luong_gram": 300}])
        kq = don_hang.luu_mat_hang(self.n["tid"], self.n["u"]["staff"], don["id"],
                                   [{"ten": "B", "so_luong": 2, "don_gia": 2000,
                                     "khoi_luong_gram": 0}])
        d = don_hang.lay_don(self.n["tid"], don["id"])
        self.assertEqual((d["khoi_luong_gram"], d["gia_tri_khai"]),
                         (kq["tong_khoi_luong_gram"], kq["tong_gia_tri_dong"]),
                         "tổng của đơn lệch tổng mặt hàng — hai con số nói hai chuyện")
        self.assertEqual((d["khoi_luong_gram"], d["gia_tri_khai"]), (0, 4000))
        # Hệ quả đúng: đơn chưa hợp lệ thì KHÔNG duyệt được — không có đường ship số cũ
        with self.assertRaises(don_hang.LoiNghiepVu):
            don_hang.duyet_don(self.n["tid"], self.n["u"]["owner"], don["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
