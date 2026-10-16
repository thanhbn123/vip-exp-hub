#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 / AG-04 — GIEO dữ liệu nghiệp vụ THẬT vào CSDL tại `VIP_HUB_DATA`.

Chạy:
    VIP_HUB_DATA=/tmp/x python3 trien_khai/g20-saoluu/gieo.py            # gieo + in phép chụp
    VIP_HUB_DATA=/tmp/x python3 trien_khai/g20-saoluu/gieo.py --khong-in # gieo, im

====== VÌ SAO DÙNG HÀM SẢN PHẨM CHỨ KHÔNG `INSERT` THẲNG ======
`tc_but_toan` có hai TRIGGER chặn UPDATE/DELETE và ba `CHECK`; `ghi_but_toan()` mở một
`giao_dich()` bọc cả bút toán LẪN cập nhật công nợ. `INSERT` thẳng sẽ bỏ qua đúng những bất
biến đó — và khi ấy phép đo "khôi phục ra đúng dữ liệu" chỉ đang đo dữ liệu do chính bộ đo
viết ra, không phải dữ liệu hệ thống tạo ra. Nên: bút toán qua `tai_chinh.ghi_but_toan`,
phí qua `tai_chinh.ghi_phi`, COD qua `tai_chinh.mo_so_cod`/`chuyen_cod`.

Dữ liệu CỐ Ý TẤT ĐỊNH (không `random`, không `secrets`): mọi lượt gieo ra cùng số tiền, nên
một con số lệch ở lượt sau là LỆCH THẬT, không phải "chắc tại ngẫu nhiên".

PHẠM VI: gieo vào ĐÚNG thư mục `VIP_HUB_DATA` mà biến môi trường trỏ tới. `chot_an_toan()`
TỪ CHỐI ghi vào vùng dữ liệu thật của dự án.
"""
import json
import os
import sys

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(GOC, "app"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VUNG_CAM = os.path.expanduser("~/Projects/vip-express-hub")


def chot_an_toan():
    """TỪ CHỐI gieo/xoá nếu `VIP_HUB_DATA` trỏ vào vùng dữ liệu thật của dự án.

    Chốt là CẤU TRÚC chứ không phải lời dặn: bộ đo này có nhánh XOÁ tệp CSDL (ca thảm hoạ),
    và một biến môi trường đặt nhầm là đủ để nó xoá nhầm nhà người khác.
    """
    d = os.path.abspath(os.environ.get("VIP_HUB_DATA") or "")
    if not d:
        raise SystemExit("DỪNG: chưa đặt VIP_HUB_DATA — bộ đo này không bao giờ ghi vào mặc định.")
    if d == VUNG_CAM or d.startswith(VUNG_CAM + os.sep):
        raise SystemExit("DỪNG: VIP_HUB_DATA trỏ vào vùng dữ liệu THẬT: %s" % d)
    for cam in ("/tmp/", "/var/folders/", "/private/var/folders/", "/var/tmp/"):
        if d.startswith(cam):
            return d
    raise SystemExit("DỪNG: VIP_HUB_DATA không nằm trong vùng tạm (được: /tmp, /var/folders): %s" % d)


def _chay():
    import adapter
    import bao_mat
    import csdl
    import migrate
    import tai_chinh as tc

    csdl.mo()
    import goi_dich_vu
    import usage
    goi_dich_vu.nap_lai_bang()
    tc._dam_bao_bang()

    # Phiên bản schema đi qua CHÍNH đường sản phẩm (`migrate.chay()`), không tự đặt số.
    migrate.chay(im_lang=True)
    luc = "2026-10-16T00:00:00+07:00"

    # ---------- hãng + gói ----------
    for ma, h in adapter.danh_sach_hang().items():
        csdl.ghi("INSERT INTO carrier_providers (ma,ten,capabilities_json,live_mo,cap_nhat_luc)"
                 " VALUES (?,?,?,?,?) ON CONFLICT(ma) DO UPDATE SET ten=excluded.ten",
                 (ma, h["ten"], json.dumps(h["capabilities"]), 1 if h["live_mo"] else 0, luc))

    # ---------- người dùng ----------
    uid_owner = csdl.ghi(
        "INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,platform_role,tao_luc)"
        " VALUES (?,?,?,?,?)",
        ("platform-owner", bao_mat.bam_mat_khau("demo-khong-phai-mat-khau-that"), "Chủ nền tảng",
         "PLATFORM_OWNER", luc)).lastrowid

    TENANT = [("shop-a", "Shop A", "basic"), ("shop-b", "Shop B", "pro"), ("shop-c", "Shop C", "free")]
    # COD cố ý KHÁC NHAU giữa các tenant: khôi phục lẫn tenant này sang tenant kia thì tổng
    # toàn kho vẫn khớp, chỉ có tổng TỪNG BẢNG và từng tenant là lộ ra.
    COD = {1: (100000, 200000, 300000, 400000, 500000),
           2: (111000, 222000, 333000, 444000, 555000),
           3: (1000, 2000, 3000, 4000, 5000)}
    PHI = 22000

    for idx, (code, ten, goi) in enumerate(TENANT, start=1):
        tid = csdl.ghi("INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,?,?)",
                       (code, ten, goi, luc)).lastrowid
        assert tid == idx, "thứ tự tenant không như dự kiến: %s" % tid
        uid = csdl.ghi("INSERT INTO users (ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
                       " VALUES (?,?,?,?)",
                       ("owner-%s" % code, bao_mat.bam_mat_khau("x" * 12), "Chủ %s" % ten,
                        luc)).lastrowid
        csdl.ghi("INSERT INTO tenant_memberships (user_id,tenant_id,role,tao_luc)"
                 " VALUES (?,?,?,?)", (uid, tid, "TENANT_OWNER", luc))
        csdl.ghi("INSERT INTO usage_thang (tenant_id,thang,so_don,so_ai) VALUES (?,?,?,?)",
                 (tid, "2026-10", 5 * idx, 3 * idx))

        # ---------- tài khoản hãng, credentials MÃ HOÁ bằng khoá nội bộ ----------
        acc = {}
        for hang in (("vtp", "jt") if idx < 3 else ("vtp",)):
            ban_ma, duoi = bao_mat.ma_hoa_cred(
                {"api_key": "KEY-%s-%s" % (code, hang), "secret": "SEC-%s-%s" % (code, hang)},
                tid, hang)
            wh_ma = "wh-%s-%s" % (code, hang)
            acc[hang] = csdl.ghi(
                "INSERT INTO carrier_accounts (tenant_id,hang,ten,moi_truong,credentials_ma_hoa,"
                " credentials_duoi,webhook_ma,webhook_secret_ma_hoa,tao_luc)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (tid, hang, "TK %s %s" % (hang.upper(), ten), "mock", ban_ma, duoi, wh_ma,
                 bao_mat.ma_hoa_wh("HMAC-%s-%s" % (code, hang), wh_ma), luc)).lastrowid
            for k in (1, 2):
                csdl.ghi("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,"
                         " headers_json,nhan_luc) VALUES (?,?,?,?,?)",
                         (acc[hang], "ev-%s-%s-%d" % (code, hang, k),
                          bytes([(idx * 40 + k * 7 + i) % 256 for i in range(64)]),
                          json.dumps({"x-hang": hang}), luc))

        kh = [csdl.ghi("INSERT INTO khach_hang (tenant_id,ten,sdt,dia_chi,tao_luc)"
                       " VALUES (?,?,?,?,?)",
                       (tid, "Khách %s %d" % (code, i), "090000000%d" % i,
                        "Địa chỉ %s %d" % (code, i), luc)).lastrowid for i in (1, 2)]
        # ---------- đơn hàng ----------
        for i, cod in enumerate(COD[idx], start=1):
            hang = "vtp" if i % 2 else "jt"
            don_id = csdl.ghi(
                "INSERT INTO don_hang (tenant_id,ma_don,khach_hang_id,nguoi_gui_ten,nguoi_gui_sdt,"
                " nguoi_gui_dia_chi,nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,"
                " khoi_luong_gram,cod,gia_tri_khai,phi_van_chuyen,carrier_account_id,nguoi_tao,"
                " tao_luc,cap_nhat_luc) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (tid, "%s-%03d" % (code.upper(), i), kh[i % 2],
                 "Người gửi %s %d" % (code, i), "091000000%d" % i, "ĐC gửi %s %d" % (code, i),
                 "Người nhận %s %d" % (code, i), "092000000%d" % i, "ĐC nhận %s %d" % (code, i),
                 "Hàng hoá %d" % i, 500 * i, cod, cod * 2, PHI,
                 acc.get(hang, acc["vtp"]), uid, luc, luc)).lastrowid
            for b in (1, 2):
                csdl.ghi("INSERT INTO don_lich_su (don_id,luc,nguon,noi_dung) VALUES (?,?,?,?)",
                         (don_id, luc, "he_thong", "bước %d của %s" % (b, code)))

            # ---------- sổ tiền: bút toán + công nợ (hàm sản phẩm, có bất biến) ----------
            tc.mo_so_cod(tid, don_id, cod, tao_boi=uid)
            tc.ghi_but_toan(tid, "cod_du_kien", cod, "he_thong",
                            "dự kiến thu COD đơn %s-%03d" % (code.upper(), i), tao_boi=uid,
                            don_id=don_id, carrier_account_id=acc.get(hang, acc["vtp"]))
            tc.ghi_but_toan(tid, "cod_hang_bao_thu", cod, "hang",
                            "hãng báo đã thu COD đơn %s-%03d" % (code.upper(), i), tao_boi=uid,
                            don_id=don_id, carrier_account_id=acc.get(hang, acc["vtp"]))
            tc.ghi_phi(tid, don_id, "thuc_te_hang", PHI, "hang",
                       "phí hãng tính đơn %s-%03d" % (code.upper(), i), tao_boi=uid,
                       carrier_account_id=acc.get(hang, acc["vtp"]), ghi_nhan_luc=luc)
            if i % 2 == 0:
                tc.chuyen_cod(tid, don_id, "COD_COLLECTED", "hang",
                              "hãng xác nhận đã thu đơn %s-%03d" % (code.upper(), i),
                              nguoi=uid, so_tien_hang_bao=cod)
                # Đối soát xong rồi mới nhận được tiền — đó là bất biến của §18, không phải
                # một bước tuỳ ý. Đi đúng hai bước ấy để `tc_dot_tt`/`tc_dot_tt_dong` có dữ
                # liệu THẬT; bỏ qua thì hai cột tiền đó luôn bằng 0 ở cả hai vế và phép so
                # TIỀN của chúng là phép so RỖNG (khớp vì cả hai đều không có gì).
                tc.chuyen_cod(tid, don_id, "COD_RECONCILED", "hang",
                              "đối soát xong đơn %s-%03d" % (code.upper(), i),
                              nguoi=uid, so_tien_hang_bao=cod)
                if i == 2:
                    dot = tc.tao_dot_thanh_toan(
                        tid, uid, hang, "DOT-%s-%03d" % (code.upper(), idx),
                        so_tien_hang_bao=cod, carrier_account_id=acc.get(hang, acc["vtp"]),
                        kiem_quyen=False)
                    # Trả MỘT PHẦN: giữ đơn ở COD_RECONCILED và để `so_tien_da_tt` khác 0 —
                    # một bản khôi phục làm mất cột này vẫn khớp `so_tien_du_kien` nên chỉ
                    # tổng tiền riêng của nó mới lộ ra.
                    tc.ghi_nhan_thanh_toan(tid, uid, dot, don_id, cod // 2, kiem_quyen=False)
            if i == 1:
                tc.dieu_chinh(tid, uid, "cod", -1000,
                              "điều chỉnh giảm COD đơn %s-%03d (hàng lỗi)" % (code.upper(), i),
                              don_id=don_id)

    # ---------- phiên bản gói + dự thảo hoá đơn (hai bảng có CỘT TIỀN riêng) ----------
    # Bỏ qua hai bảng này thì `goi_phien_ban.gia_thang_dong` và `du_thao_hoa_don.tien_*` bằng 0
    # ở CẢ HAI vế, và phép so "khôi phục khớp tiền" cho chúng là phép so RỖNG — khớp vì không
    # có gì để khớp. `kiem_khong_rong()` của khung đo NÉM đúng ở chỗ đó.
    goi_dich_vu.phat_hanh_phien_ban(
        "pro", {"han_muc_don_thang": 12000, "han_muc_ai_thang": 6000, "so_nhan_vien": 25,
                "so_tai_khoan_hang": 12}, gia_thang_dong=1299000,
        ghi_chu="phiên bản pro giá mới — dựng cho phép đo G20", boi=1)
    for tid_ in (1, 2):
        goi_dich_vu.kich_hoat(tid_, "basic", boi=1, ly_do="kích hoạt để lập dự thảo hoá đơn")
        # Số đơn vượt hạn mức gói. CHÚ Ý: việc này KHÔNG làm `tien_vuot_dong` khác 0 —
        # `usage.tinh_phi()` trả cứng 0 cho cột đó (hệ chặn khi hết hạn mức, xem
        # `khung_do.TIEN_RONG_CHAP_NHAN`). Đẩy số ở đây để `usage_thang` và `chi_tiet_json`
        # của dự thảo có dữ liệu THẬT, không phải để nhồi một cột tiền.
        # Ghi thẳng `usage_thang` là sửa số đo của bộ đếm dùng tháng — chấp nhận được ở một
        # fixture, vì mục đích là tạo dự thảo có phần vượt, không phải kiểm bộ đếm đó.
        csdl.ghi("UPDATE usage_thang SET so_don=? WHERE tenant_id=? AND thang='2026-10'",
                 (1500 if tid_ == 1 else 1200, tid_))
        usage.lap_du_thao(tid_, ky="2026-10", boi=1)

    # ---------- bảng kê đối soát của hãng (nguồn của `ds_dot` + `ds_dong`) ----------
    # Đi qua `doi_soat.nap_bang_ke()` chứ không INSERT thẳng: ánh xạ cột, vân tay dòng chống
    # trùng, và chuyển trạng thái đợt đều nằm trong hàm đó. `ds_dong.phi_hang_bao` là cột tiền
    # duy nhất của nhóm đối soát — bỏ bước này thì phép so TIỀN cho nó là phép so RỖNG.
    import doi_soat
    for idx, (code, _ten, _goi) in enumerate(TENANT, start=1):
        rows = csdl.nhieu("SELECT ma_don, cod FROM don_hang WHERE tenant_id=? ORDER BY id", (idx,))
        csv_bytes = ("ma van don,ma don,tien cod,cuoc chinh,ky doi soat\n" + "".join(
            '%s-%03d,%s,%d,%d,2026-10\n' % (code.upper(), n, r["ma_don"], r["cod"], PHI)
            for n, r in enumerate(rows, start=1))).encode("utf-8")
        doi_soat.nap_bang_ke(idx, 1, "vtp", "bang-ke-%s.csv" % code, csv_bytes,
                             ky_thanh_toan="2026-10", kiem_quyen=False)

    # ---------- lô nhập tệp ----------
    b = csdl.ghi("INSERT INTO import_batch (tenant_id,ten_file,loai_file,trang_thai,nguoi_tao,"
                 " tao_luc) VALUES (?,?,?,?,?,?)",
                 (1, "lo-hang-a.csv", "csv", "COMPLETED", uid, luc)).lastrowid
    for i in (1, 2, 3):
        csdl.ghi("INSERT INTO import_dong (batch_id,stt,du_lieu_json,trang_thai) VALUES (?,?,?,?)",
                 (b, i, json.dumps({"ma_don": "SHOP-A-%03d" % i}, ensure_ascii=False), "SUCCESS"))

    # ---------- nhật ký kiểm toán ----------
    for i in (1, 2, 3, 4):
        csdl.ghi("INSERT INTO audit (luc,tenant_id,user_id,hanh_dong,doi_tuong,resource_type,"
                 " resource_id,ket_qua,chi_tiet) VALUES (?,?,?,?,?,?,?,?,?)",
                 (luc, (i % 3) + 1, uid_owner, "gieo-du-lieu-%d" % i, "tenant:%d" % i,
                  "tenant", str(i), "thanh_cong", "dòng kiểm toán gieo sẵn để đo khôi phục"))

    # Chốt: công nợ tổng hợp phải khớp sổ bút toán NGAY SAU KHI GIEO. Không có chốt này thì
    # một lượt gieo hỏng có thể để lại dữ liệu tự-mâu-thuẫn, và mọi phép so sau đó chỉ đang
    # so hai bản sao của cùng một thứ hỏng.
    for tid in (1, 2, 3):
        a, b2 = tc.cong_no(tid), tc.tinh_lai_cong_no(tid)
        for k in ("tong_phai_thu", "tong_phai_tra"):
            if a.get(k) != b2.get(k):
                raise AssertionError("gieo xong mà công nợ tenant %d đã lệch: %s vs %s"
                                     % (tid, a.get(k), b2.get(k)))
    csdl.dong()


def main():
    chot_an_toan()
    _chay()
    if "--khong-in" in sys.argv:
        return 0
    import cau_hinh
    import khung_do
    print(json.dumps(khung_do.chup(cau_hinh.DUONG_DAN_CSDL), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
