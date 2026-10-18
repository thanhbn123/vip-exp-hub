#!/usr/bin/env python3
# ============================================================================
# VIP Express Hub — SEED DỮ LIỆU MẪU CHO UAT LOCAL
# ----------------------------------------------------------------------------
# Chạy tự động bởi `khoi_dong.sh`, sau `app/migrate.py` + `app/khoi_tao.py`.
#
# Nguyên tắc:
#   · CHỈ ghi vào thư mục UAT có dấu `.veh-uat-fixture.json` đúng dự án;
#   · TỪ CHỐI nếu VIP_HUB_DATA trỏ vào repo / app/du-lieu / /du-lieu;
#   · TẤT CẢ tên, SĐT, địa chỉ, mã đơn là HƯ CẤU (fixture);
#   · KHÔNG gọi adapter hãng, KHÔNG tạo vận đơn thật — chỉ ghi CSDL local;
#   · Idempotent: CSDL đã có đơn thì bỏ qua, không nhân đôi dữ liệu.
# ============================================================================
import json
import os
import sys
from datetime import datetime, timedelta

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def tu_choi(thong_diep):
    sys.exit("[uat-seed] TỪ CHỐI: " + thong_diep)


def kiem_tra_duong_dan():
    raw = os.environ.get("VIP_HUB_DATA")
    if not raw:
        tu_choi("thiếu VIP_HUB_DATA — script này chỉ chạy trên thư mục UAT riêng.")
    data = os.path.realpath(os.path.expanduser(raw))
    repo = os.path.realpath(GOC)

    if data == repo or data.startswith(repo + os.sep):
        tu_choi("VIP_HUB_DATA=%s nằm trong CÂY REPO — đó không phải thư mục UAT." % data)
    if data == "/du-lieu" or data.startswith("/du-lieu" + os.sep):
        tu_choi("VIP_HUB_DATA=%s là volume triển khai /du-lieu — đó là DỮ LIỆU THẬT." % data)
    if os.path.basename(data) == "du-lieu":
        tu_choi("VIP_HUB_DATA=%s có tên 'du-lieu' — quy ước dữ liệu sản phẩm, không phải UAT." % data)

    p = data
    while p and p != "/":
        if os.path.exists(os.path.join(p, ".git")):
            tu_choi("VIP_HUB_DATA=%s nằm trong cây git (%s/.git) — dữ liệu UAT phải ở ngoài repo."
                    % (data, p))
        p = os.path.dirname(p)

    if not os.path.isdir(data):
        tu_choi("thư mục UAT không tồn tại: %s" % data)
    marker = os.path.join(data, ".veh-uat-fixture.json")
    if not os.path.isfile(marker):
        tu_choi("thiếu dấu UAT %s — không ghi vào thư mục không rõ nguồn gốc." % marker)
    try:
        with open(marker, encoding="utf-8") as f:
            dau = json.load(f)
    except Exception as e:
        tu_choi("không đọc được dấu UAT %s: %r" % (marker, e))
    if dau.get("loai") != "VEH-UAT-FIXTURE":
        tu_choi("dấu UAT sai loại: %r" % (dau.get("loai"),))
    if os.path.realpath(str(dau.get("du_an") or "")) != repo:
        tu_choi("dấu UAT thuộc dự án khác: %r" % (dau.get("du_an"),))

    moi_truong = (os.environ.get("VIP_JT_MOI_TRUONG") or "mock").strip().lower()
    if moi_truong != "mock":
        tu_choi("VIP_JT_MOI_TRUONG=%r — UAT local chỉ cho phép mock, không gọi API hãng."
                % (moi_truong,))
    return data


def main():
    data = kiem_tra_duong_dan()
    sys.path.insert(0, os.path.join(GOC, "app"))

    import cau_hinh          # noqa: E402
    import csdl              # noqa: E402

    if os.path.realpath(cau_hinh.THU_MUC_DU_LIEU) != data:
        tu_choi("cau_hinh.THU_MUC_DU_LIEU=%s khác thư mục UAT %s"
                % (cau_hinh.THU_MUC_DU_LIEU, data))
    csdl.mo()
    pb = csdl.phien_ban_hien_tai()
    if pb < csdl.PHIEN_BAN_SCHEMA:
        tu_choi("schema v%d < cần v%d — chạy migrate trước." % (pb, csdl.PHIEN_BAN_SCHEMA))

    so_don = csdl.mot("SELECT COUNT(*) AS n FROM don_hang")["n"]
    if so_don:
        print("[uat-seed] CSDL UAT đã có %d đơn — không seed lại (idempotent)." % so_don)
        return

    hang_that = csdl.nhieu("SELECT ma FROM carrier_providers WHERE live_mo<>0")
    if hang_that:
        tu_choi("carrier_providers có live_mo<>0: %r" % ([dict(x) for x in hang_that],))
    tk_that = csdl.nhieu("SELECT id FROM carrier_accounts WHERE moi_truong<>'mock'")
    if tk_that:
        tu_choi("carrier_accounts khác mock: %r" % ([dict(x) for x in tk_that],))

    tenants = {r["code"]: r for r in csdl.nhieu("SELECT * FROM tenants")}
    for code in ("shop-a", "shop-b"):
        if code not in tenants:
            tu_choi("thiếu tenant %r — seed cơ bản chưa chạy đúng." % code)

    def user_id(ten):
        r = csdl.mot("SELECT id FROM users WHERE ten_dang_nhap=?", (ten,))
        if not r:
            tu_choi("thiếu tài khoản fixture %r." % ten)
        return r["id"]

    uid_a = user_id("shopa-owner")
    uid_b = user_id("shopb-owner")

    def tai_khoan_hang(tenant_id, hang):
        r = csdl.mot(
            "SELECT id FROM carrier_accounts WHERE tenant_id=? AND hang=? AND kich_hoat=1"
            " ORDER BY id LIMIT 1", (tenant_id, hang))
        if not r:
            tu_choi("thiếu tài khoản hãng mock %r của tenant %d." % (hang, tenant_id))
        return r["id"]

    tk_a_vtp = tai_khoan_hang(tenants["shop-a"]["id"], "vtp")
    tk_a_jt = tai_khoan_hang(tenants["shop-a"]["id"], "jt")
    tk_b_vtp = tai_khoan_hang(tenants["shop-b"]["id"], "vtp")
    tk_b_jt = tai_khoan_hang(tenants["shop-b"]["id"], "jt")

    now = datetime.now(csdl.MUI_GIO_VN)
    thang = csdl.thang_nay()

    def luc(days_ago):
        return (now - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M:%S%z")

    def tao_khach(tenant_id, ten, sdt, dia_chi):
        kid = csdl.ghi(
            "INSERT INTO khach_hang (tenant_id, ten, sdt, dia_chi, ghi_chu, tao_luc)"
            " VALUES (?,?,?,?,?,?)",
            (tenant_id, ten, sdt, dia_chi, "Khách FIXTURE của UAT — không phải người thật.",
             luc(7))).lastrowid
        return kid, ten, sdt, dia_chi

    # Danh sách đơn mẫu. `khach` là chỉ số trong danh sách khách của tenant.
    # Trạng thái dùng đúng hai trục của sản phẩm (trang_thai + trang_thai_giao),
    # không bịa thêm cột/enum mới.
    DON_MAU = [
        # code, tenant, khach, ma_don, trang_thai, trang_thai_giao, hang, cod, phi, ngay
        ("A", "shop-a", 0, "UAT-A-001", "nhap", None, None, 0, None, 0),
        ("A", "shop-a", 1, "UAT-A-002", "da_duyet", None, "vtp", 199000, None, 1),
        ("A", "shop-a", 0, "UAT-A-003", "dang_gui", None, "vtp", 320000, None, 1),
        ("A", "shop-a", 1, "UAT-A-004", "da_gui", "cho_lay", "vtp", 250000, 30000, 2),
        ("A", "shop-a", 0, "UAT-A-005", "da_gui", "dang_giao", "jt", 0, 35000, 3),
        ("A", "shop-a", 1, "UAT-A-006", "da_gui", "giao_thanh_cong", "jt", 450000, 40000, 4),
        ("A", "shop-a", 0, "UAT-A-007", "huy", None, None, 0, None, 5),
        ("B", "shop-b", 0, "UAT-B-001", "da_gui", "lay_hang", "vtp", 120000, 25000, 2),
        ("B", "shop-b", 1, "UAT-B-002", "da_gui", "giao_that_bai", "jt", 0, 30000, 3),
        ("B", "shop-b", 0, "UAT-B-003", "da_gui", "hoan_hang", "vtp", 0, 30000, 6),
    ]

    with csdl.giao_dich():
        khach_a = [
            tao_khach(tenants["shop-a"]["id"], "Khách UAT A1", "0900000001",
                      "Số 1 Đường Fixture, Phường UAT, TP. Hồ Chí Minh"),
            tao_khach(tenants["shop-a"]["id"], "Khách UAT A2", "0900000002",
                      "Số 2 Đường Fixture, Phường UAT, TP. Hồ Chí Minh"),
        ]
        khach_b = [
            tao_khach(tenants["shop-b"]["id"], "Khách UAT B1", "0900000003",
                      "Số 3 Đường Fixture, Phường UAT, Hà Nội"),
            tao_khach(tenants["shop-b"]["id"], "Khách UAT B2", "0900000004",
                      "Số 4 Đường Fixture, Phường UAT, Đà Nẵng"),
        ]
        khach = {"shop-a": khach_a, "shop-b": khach_b}
        nguoi_tao = {"shop-a": uid_a, "shop-b": uid_b}
        tai_khoan = {
            ("shop-a", "vtp"): tk_a_vtp, ("shop-a", "jt"): tk_a_jt,
            ("shop-b", "vtp"): tk_b_vtp, ("shop-b", "jt"): tk_b_jt,
        }

        so_lich_su = 0
        for (nhom, code_tenant, i_khach, ma_don, trang_thai, trang_thai_giao,
             hang, cod, phi, ngay) in DON_MAU:
            tid = tenants[code_tenant]["id"]
            kh_id, kh_ten, kh_sdt, kh_dia_chi = khach[code_tenant][i_khach]
            tao_luc = luc(ngay)
            cap_nhat = luc(max(0, ngay - 1))
            da_gui = trang_thai == "da_gui"
            da_duyet_tro_len = trang_thai in ("da_duyet", "dang_gui", "da_gui")
            ma_van_don = ("MOCK-UAT-%s-%03d" % (nhom, int(ma_don[-3:]))) if da_gui else None
            hang_so = {"cho_lay": 1, "lay_hang": 2, "dang_giao": 3,
                       "giao_that_bai": 4, "giao_thanh_cong": 5, "hoan_hang": 6}
            carrier_id = tai_khoan.get((code_tenant, hang)) if (da_duyet_tro_len and hang) else None

            cur = csdl.ghi(
                "INSERT INTO don_hang ("
                " tenant_id, ma_don, khach_hang_id,"
                " nguoi_gui_ten, nguoi_gui_sdt, nguoi_gui_dia_chi,"
                " nguoi_nhan_ten, nguoi_nhan_sdt, nguoi_nhan_dia_chi,"
                " hang_hoa, khoi_luong_gram, cod, gia_tri_khai, phi_van_chuyen, ghi_chu,"
                " carrier_account_id, ma_van_don, trang_thai, can_doi_soat_ket_qua,"
                " trang_thai_giao, hang_trang_thai_giao, approved_by, approved_luc,"
                " nguoi_tao, tao_luc, cap_nhat_luc"
                ") VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    tid, ma_don, kh_id,
                    "Shop Demo %s (fixture)" % nhom, "0900000000",
                    "Số 10 Đường Fixture, Phường UAT, TP. Hồ Chí Minh",
                    kh_ten, kh_sdt, kh_dia_chi,
                    "Hàng mẫu UAT %s (fixture)" % nhom, 500 + 100 * i_khach,
                    cod, cod, phi,
                    "Dữ liệu mẫu UAT — KHÔNG phải đơn thật, KHÔNG gửi hãng.",
                    carrier_id, ma_van_don, trang_thai,
                    1 if trang_thai == "dang_gui" else 0,
                    trang_thai_giao, hang_so.get(trang_thai_giao, 0) if da_gui else 0,
                    nguoi_tao[code_tenant] if da_duyet_tro_len else None,
                    cap_nhat if da_duyet_tro_len else None,
                    nguoi_tao[code_tenant], tao_luc, cap_nhat,
                ))
            don_id = cur.lastrowid

            csdl.ghi(
                "INSERT INTO don_lich_su (don_id, luc, nguon, noi_dung) VALUES (?,?,?,?)",
                (don_id, tao_luc, "uat-seed",
                 "Tạo đơn mẫu UAT (fixture) — KHÔNG gửi hãng, KHÔNG tạo vận đơn thật."))
            so_lich_su += 1
            if trang_thai != "nhap":
                csdl.ghi(
                    "INSERT INTO don_lich_su (don_id, luc, nguon, noi_dung) VALUES (?,?,?,?)",
                    (don_id, cap_nhat, "uat-seed",
                     "Trạng thái mẫu: %s%s — dữ liệu fixture."
                     % (trang_thai,
                        (" / " + trang_thai_giao) if trang_thai_giao else "")))
                so_lich_su += 1

        # Nhật ký + usage để màn Tổng quan/Nhật ký/Gói & usage có dữ liệu.
        for code_tenant in ("shop-a", "shop-b"):
            tid = tenants[code_tenant]["id"]
            csdl.ghi(
                "INSERT INTO audit (luc, tenant_id, user_id, hanh_dong, doi_tuong,"
                " resource_type, resource_id, ket_qua, chi_tiet, dia_chi)"
                " VALUES (?,?,?,?,?,?,?,?,?,?)",
                (luc(0), tid, nguoi_tao[code_tenant], "uat_seed", "tenant:%d" % tid,
                 "tenant", str(tid), "thanh_cong",
                 "Seed dữ liệu mẫu UAT — 100% fixture, không gọi hãng, không tạo đơn thật.",
                 "127.0.0.1"))
            so_gui = csdl.mot(
                "SELECT COUNT(*) AS n FROM don_hang WHERE tenant_id=? AND trang_thai='da_gui'",
                (tid,))["n"]
            csdl.ghi(
                "INSERT OR REPLACE INTO usage_thang (tenant_id, thang, so_don, so_ai)"
                " VALUES (?,?,?,0)", (tid, thang, so_gui))

    print("[uat-seed] Đã tạo: 4 khách hàng, %d đơn mẫu, %d dòng lịch sử, 2 audit, 2 usage."
          % (len(DON_MAU), so_lich_su))
    print("[uat-seed] Mã đơn: %s" % ", ".join(d[3] for d in DON_MAU))
    print("[uat-seed] TẤT CẢ là FIXTURE: tên/SĐT/địa chỉ hư cấu, mã vận đơn MOCK-UAT-*,"
          " không gửi hãng, không tạo đơn thật.")


if __name__ == "__main__":
    main()
