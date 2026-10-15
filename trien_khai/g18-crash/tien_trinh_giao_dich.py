#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TIẾN TRÌNH CON BỊ GIẾT GIỮA GIAO DỊCH — làn G18/AG-06.

Đây là **tiến trình THẬT** chạy **mã nghiệp vụ THẬT** (`tai_chinh.chuyen_cod`) rồi tự
`os.kill(os.getpid(), SIGKILL)` tại đúng một câu ghi. Không có `sys.exit`, không có ngoại lệ,
không có `finally`: SIGKILL không chạy được `finally` nào, và đó chính là điều cần đo.

====== NĂM CHỖ GHI CỦA MỘT LƯỢT CHUYỂN COD ======
`tai_chinh.chuyen_cod` chuyển `COD_EXPECTED → COD_COLLECTED` ghi NĂM chỗ trong MỘT
`csdl.giao_dich()`:

    1. UPDATE tc_cod          (trạng thái COD)
    2. INSERT tc_cod_chuyen   (vết chuyển trạng thái)
    3. INSERT tc_but_toan     (bút toán — BẤT BIẾN theo §17)
    4. UPSERT tc_cong_no      (số dư công nợ)
    5. INSERT tc_nhat_ky      (nhật ký bất biến, móc băm)

Kịch bản hỏng mà §18 mô tả: chết sau chỗ 2 thì `tc_cod` nói "hãng đã thu tiền" mà
`tc_but_toan` KHÔNG có dòng nào — hệ báo tiền đã về trong khi sổ cái trống.

====== HAI CHẾ ĐỘ, VÀ VÌ SAO PHẢI CÓ CHẾ ĐỘ THỨ HAI ======
`--che-do that`            — mã ĐANG CHẠY (đã bọc `csdl.giao_dich()`).
`--che-do khong_giao_dich` — **cùng năm câu ghi ấy, KHÔNG bọc giao dịch**: bản dựng lại
                             đúng mã TRƯỚC bản vá V-13912 (mỗi `csdl.ghi()` tự chốt ngay).

Chế độ thứ hai tồn tại vì một lý do duy nhất: **làm cho bộ đo ĐỎ ĐƯỢC**. Một bộ đo chưa từng
kêu "NỬA VỜI" thì lời khai "mọi ca đều NGUYÊN VẸN" không có giá trị — nó chỉ nói rằng bộ đo
chưa bao giờ chạy đúng chỗ. Chế độ này là ĐỐI CHỨNG ÂM của chính bộ đo.

CHẠY (do `app/thu/thu_g18_crash.py` spawn, không chạy tay):
    VIP_HUB_DATA=<nền tạm> python3 tien_trinh_giao_dich.py \
        --db-dir <nền tạm> --diem sau_ghi_2 --che-do that --vet <tệp vết>
"""
import argparse
import json
import os
import sys

GOC_CRASH = os.path.dirname(os.path.abspath(__file__))
GOC_DU_AN = os.path.dirname(os.path.dirname(GOC_CRASH))
GOC_APP = os.path.join(GOC_DU_AN, "app")
for p in (GOC_APP, GOC_CRASH):
    if p not in sys.path:
        sys.path.insert(0, p)

import do_giet                                                          # noqa: E402


def _ghi_vet(duong, su_kien, du_lieu):
    ban = {"su_kien": su_kien, "pid": os.getpid()}
    ban.update(du_lieu)
    with open(duong, "a", encoding="utf-8") as f:
        f.write(json.dumps(ban, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _dung_nen(csdl, tai_chinh):
    """Dựng dữ liệu nền: một tenant, một người dùng, một đơn, một sổ COD ở `COD_EXPECTED`.

    Mọi câu ở đây CHỐT XONG trước khi móc giết được gắn — nếu không, phép đo sẽ lẫn "chết
    giữa lượt dựng nền" với "chết giữa giao dịch cần đo".
    """
    csdl.mo()
    bgio = csdl.bay_gio()
    csdl.ghi("INSERT INTO tenants (id,code,ten,goi_id,tao_luc) VALUES (1,'t1','T1','free',?)",
             (bgio,))
    csdl.ghi("INSERT INTO users (id,ten_dang_nhap,mat_khau_hash,ho_ten,tao_luc)"
             " VALUES (1,'u1','x','Nguoi dung 1',?)", (bgio,))
    csdl.ghi("INSERT INTO don_hang (id,tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,"
             "nguoi_gui_dia_chi,nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,"
             "khoi_luong_gram,cod,nguoi_tao,tao_luc,cap_nhat_luc)"
             " VALUES (1,1,'D1','Nguoi gui','0900','dia chi gui','Nguoi nhan','0901',"
             "'dia chi nhan','hang mau',500,250000,1,?,?)", (bgio, bgio))
    tai_chinh._dam_bao_bang()
    tai_chinh.mo_so_cod(1, 1)


def _chay_khong_giao_dich(csdl, tai_chinh, tenant_id, don_id):
    """BẢN DỰNG LẠI mã TRƯỚC V-13912 — năm câu ghi, KHÔNG có `giao_dich()` bao ngoài.

    Chép nguyên hình dạng cũ (đọc `tai_chinh.py` trước bản vá): hai câu đầu dưới `khoa_ghi`
    TRẦN, mỗi `csdl.ghi()` tự chốt ngay; ba chỗ còn lại (bút toán, công nợ, nhật ký) nằm
    ngoài giao dịch. Giữ nguyên thứ tự để phép so với chế độ `that` là so cùng một việc.
    """
    nguon, can_cu, nguoi = "hang", "doi chung am cua bo do", 1
    cur = tai_chinh.cod_cua_don(tenant_id, don_id)
    stb = 250000
    with csdl.khoa_ghi:
        csdl.ghi("UPDATE tc_cod SET trang_thai=?, cap_nhat_luc=?, so_tien_hang_bao=?"
                 " WHERE don_id=? AND tenant_id=? AND trang_thai=?",
                 ("COD_COLLECTED", csdl.bay_gio(), stb, don_id, tenant_id, cur["trang_thai"]))
        csdl.ghi("INSERT INTO tc_cod_chuyen (tenant_id, don_id, tu, den, nguon, can_cu, nguoi, luc)"
                 " VALUES (?,?,?,?,?,?,?,?)",
                 (tenant_id, don_id, cur["trang_thai"], "COD_COLLECTED", nguon, can_cu, nguoi,
                  csdl.bay_gio()))
    tai_chinh.ghi_but_toan(tenant_id, "cod_hang_bao_thu", stb, nguon, can_cu, tao_boi=nguoi,
                           don_id=don_id)
    tai_chinh.ghi_nhat_ky(tenant_id, "chuyen_cod", "don:%d" % don_id,
                          "%s → COD_COLLECTED: %s" % (cur["trang_thai"], can_cu), nguoi)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--db-dir", required=True, help="thư mục dữ liệu TẠM của lượt đo")
    ap.add_argument("--diem", default="khong", choices=list(do_giet.DIEM_GIET) + ["khong"])
    ap.add_argument("--che-do", default="that", choices=["that", "khong_giao_dich"])
    ap.add_argument("--vet", required=True, help="tệp ghi vết (JSON mỗi dòng)")
    ap.add_argument("--don-id", type=int, default=1)
    ap.add_argument("--tenant-id", type=int, default=1)
    a = ap.parse_args(argv)

    # Chốt chặn của CHÍNH tiến trình con: không bao giờ chạy lên một thư mục không phải nền
    # tạm của lượt này. Tiến trình này SẼ BỊ GIẾT; để nó chết giữa `app/du-lieu/hub.db` thật
    # là biến một phép đo thành một sự cố.
    if not os.path.isdir(a.db_dir):
        sys.stderr.write("TỪ CHỐI: --db-dir %r không phải thư mục\n" % a.db_dir)
        return 3
    _that = os.path.realpath(os.path.join(GOC_APP, "du-lieu"))
    _nen = os.path.realpath(a.db_dir)
    if _nen == _that or _nen.startswith(os.path.realpath(GOC_DU_AN) + os.sep):
        sys.stderr.write("TỪ CHỐI: --db-dir %r nằm trong cây dự án (dữ liệu THẬT: %r)\n"
                         % (_nen, _that))
        return 3
    if os.environ.get("VIP_HUB_DATA") != a.db_dir:
        sys.stderr.write("TỪ CHỐI: VIP_HUB_DATA=%r phải bằng --db-dir=%r\n"
                         % (os.environ.get("VIP_HUB_DATA"), a.db_dir))
        return 3

    import csdl
    import cau_hinh
    import tai_chinh
    if os.path.realpath(cau_hinh.DUONG_DAN_CSDL) != os.path.realpath(
            os.path.join(a.db_dir, "hub.db")):
        sys.stderr.write("TỪ CHỐI: csdl trỏ tới %r, ngoài nền tạm\n" % cau_hinh.DUONG_DAN_CSDL)
        return 3

    _dung_nen(csdl, tai_chinh)
    kn = csdl.mo()
    truoc = do_giet.vet_trang_thai(kn, a.tenant_id, a.don_id)
    _ghi_vet(a.vet, "TRUOC", {"che_do": a.che_do, "diem": a.diem, "vet": truoc,
                              "csdl": cau_hinh.DUONG_DAN_CSDL})
    sys.stderr.write("[con] pid=%d che_do=%s diem=%s — nền đã chốt, bắt đầu giao dịch\n"
                     % (os.getpid(), a.che_do, a.diem))
    sys.stderr.flush()

    bo = do_giet.cai_bo_giet(kn, a.diem, a.vet,
                             them={"che_do": a.che_do, "don_id": a.don_id}) \
        if a.diem != "khong" else None

    if a.che_do == "that":
        tai_chinh.chuyen_cod(a.tenant_id, a.don_id, "COD_COLLECTED", "hang",
                             "do G18 AG-06: giet giua giao dich", nguoi=1,
                             so_tien_hang_bao=250000)
    else:
        _chay_khong_giao_dich(csdl, tai_chinh, a.tenant_id, a.don_id)

    if bo is not None:
        kn.set_trace_callback(None)
    sau = do_giet.vet_trang_thai(kn, a.tenant_id, a.don_id)
    _ghi_vet(a.vet, "SAU", {"vet": sau, "cau_ghi": bo.cau_ghi if bo else None,
                            "so_cau": bo.so_cau if bo else None})
    print("XONG khong bi giet — diem=%s che_do=%s" % (a.diem, a.che_do))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
