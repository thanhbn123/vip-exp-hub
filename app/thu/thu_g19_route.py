#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G19 / AG-04 — PHỦ 31 ROUTE CÒN THIẾU BẰNG PHÉP ĐO CÁCH LY TENANT.

BỐI CẢNH (đo được, không suy đoán)
----------------------------------
Lượt nghiệm thu G18 (`docs/QA_G18_INTEGRATED.md`, dòng 223-259) đo được: hai dụng cụ đo V5
(cách ly tenant) **ĐỒNG Ý ở 73 route** và **lệch PHẠM VI ở 31 route** — AG-06 phủ **104** route,
AG-01 phủ **73**. Nghĩa là **31 route chưa từng được đo cách ly tenant bằng bộ của AG-01**.

Tệp này làm BA việc, và KHÔNG thêm tính năng nào vào sản phẩm:

  A. DỰNG BỘ TRÍCH ROUTE **THỨ BA** (`trien_khai/g19/bot_route_thi_hanh.py`), nguyên lý
     **THI HÀNH**: không gian ứng viên moi từ **hằng số đã biên dịch** của `server.py`, rồi
     quyết định "có route hay không" bằng **phản hồi THẬT** của máy chủ đang chạy. Khác AG-06
     (đi cây cú pháp `ast`) và khác AG-01 (`re` trên từng dòng nguồn).
  B. CHỨNG MINH bộ trích **CÓ RĂNG** bằng ĐỘT BIẾN trên BẢN SAO: tiêm route giả (phải THẤY),
     tiêm hai loại bịa (phải KHÔNG thấy), xoá route thật (phải MẤT).
  C. ĐO CÁCH LY TENANT cho **31 mục còn thiếu**: mỗi mục phải có **ĐỐI CHỨNG DƯƠNG** (chính
     route đó với chủ sở hữu hợp lệ trả 200 kèm dữ liệu CỦA CHÍNH MÌNH) và **ĐỐI CHỨNG ĐƯỜNG**
     cho vế phủ định (tenant B trả dữ liệu CỦA B) — nếu không thì "B không thấy dữ liệu A" có
     thể chỉ vì B chẳng nhận được gì. Mục nào không đo được thì ghi thẳng **CHƯA ĐO**.

RÀNG BUỘC ĐÃ GIỮ
----------------
* KHÔNG gọi hãng kể cả sandbox: máy chủ đo bind `127.0.0.1` cổng `0`; `may_chu_do.py` ghi lại
  MỌI lượt `socket.connect()` và ca C0 khẳng định **0 lượt ra ngoài loopback**.
* KHÔNG push/deploy/tunnel; không mở cổng ra ngoài; không đọc `.env`; không credential thật
  (mật khẩu trong CSDL TẠM là chuỗi thử, xem `may_chu_do.MK`).
* KHÔNG sửa `app/`, KHÔNG sửa `cau_hinh.py`, KHÔNG chuyển sang PostgreSQL, KHÔNG mở
  `CHO_PHEP_LIVE`. Mọi đột biến chạy trên **bản sao** trong thư mục tạm.
* Mã trạng thái 110 (D-4) KHÔNG được đoán: nó chỉ xuất hiện trong nghiệm thu `NEEDS_REVIEW`
  gốc của G09, không phải thứ tệp này khẳng định.

CHẠY
----
    python3 app/thu/thu_g19_route.py            # chạy toàn bộ (unittest)
    python3 app/thu/thu_g19_route.py --do       # chỉ ĐO, in JSON thô để soi
"""

import json
import os
import sys
import unittest

GOC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(GOC, "app")
sys.path.insert(0, os.path.join(GOC, "trien_khai", "g19"))
import bot_route_thi_hanh as BOT  # noqa: E402

# 31 mục = 104 (AG-06) − 73 (AG-01). Danh sách này CHÉP LẠI từ phép so ở ca A6, không gõ tay.
HAI_MUOI_MOT = [
    "/api/v2/ai/su-kien", "/api/v2/ai/thong-ke", "/api/v2/audit", "/api/v2/auth/dang-nhap",
    "/api/v2/auth/dat-lai-mat-khau", "/api/v2/auth/quen-mat-khau", "/api/v2/auth/toi",
    "/api/v2/billing", "/api/v2/billing/du-thao", "/api/v2/dang-ky", "/api/v2/doi-soat/dot",
    "/api/v2/don/can-doi-soat", "/api/v2/don/xuat-csv", "/api/v2/g09/can-soat",
    "/api/v2/g09/suc-khoe-hang", "/api/v2/goi", "/api/v2/hang", "/api/v2/platform/",
    "/api/v2/san-sang", "/api/v2/suc-khoe", "/api/v2/tai-chinh/cod", "/api/v2/tai-chinh/cong-no",
    "/api/v2/tai-chinh/kiem-nhat-ky", "/api/v2/tai-chinh/tong-so", "/api/v2/usage",
    "/api/v2/usage/bao-cao", "/api/v2/usage/doi-soat", "/api/v2/usage/su-kien",
    "/api/v2/usage/tinh-phi", "/api/v2/webhook/nhan/{ma}", "/api/v2/webhook/su-kien",
]

# `/api/v2/platform/` KHÔNG phải route — nó là HẰNG SỐ TIỀN TỐ của cổng chặn platform
# (`duong.startswith("/api/v2/platform/")`, server.py:566) mà bộ AST của AG-06 đếm nhầm thành
# route. Ca A7 và C31 đo lại điều đó bằng THI HÀNH, không bằng lập luận.
KHONG_PHAI_ROUTE = ["/api/v2/platform/"]


def T(duong, **k):
    """Một ca đo cách ly. `kieu`: tenant | toan_cuc (dùng chung cho cả 3 loại dưới)."""
    k.setdefault("method", "GET")
    k.setdefault("kieu", "tenant")
    k["duong"] = duong
    return k


# ═════════════════════════════════════════════════════════════════════════════════════════════
# DANH SÁCH CA CÁCH LY — 31 mục, mỗi mục có ĐỐI CHỨNG DƯƠNG riêng
# ═════════════════════════════════════════════════════════════════════════════════════════════
CAC_CA = [
    T("/api/v2/ai/su-kien", ten="ai/su-kien — sổ sự kiện AI",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="ai_su_kien.chi_tiet mang dấu A/B"),
    T("/api/v2/ai/thong-ke", ten="ai/thong-ke — thống kê dùng AI",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="ai_job.loai mang dấu A/B, đếm theo tenant"),
    T("/api/v2/audit", ten="audit — nhật ký kiểm toán của tenant",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="audit.hanh_dong mang dấu A/B; route KHÔNG kiểm phương thức"),
    T("/api/v2/auth/dang-nhap", ten="auth/dang-nhap — không lấy được phiên của người khác",
      method="POST", kieu="dang-nhap",
      ghi_chu="A đúng mật khẩu ⇒ 200 + cookie; A sai mật khẩu ⇒ 401 KHÔNG cookie; B vào ĐÚNG tenant B"),
    T("/api/v2/auth/dat-lai-mat-khau", ten="auth/dat-lai-mat-khau — token của B không đụng được A",
      method="POST", kieu="dat-lai-mat-khau",
      ghi_chu="token hợp lệ của A ⇒ 200; token của B KHÔNG đổi băm mật khẩu A; token bịa ⇒ 400"),
    T("/api/v2/auth/quen-mat-khau", ten="auth/quen-mat-khau — không dò được tài khoản",
      method="POST", kieu="quen-mat-khau",
      ghi_chu="thân phản hồi cho tên CÓ THẬT phải TRÙNG thân cho tên KHÔNG có"),
    T("/api/v2/auth/toi", ten="auth/toi — danh tính theo phiên",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="tenants.ten mang dấu A/B; đây là chỗ duy nhất khai ngữ cảnh đang thao tác"),
    T("/api/v2/billing", ten="billing — gói và mức dùng của tenant",
      khang_dinh_a=['"so_don": 7'], khang_dinh_b=['"so_don": 23'],
      ghi_chu="usage_thang.so_don A=7 vs B=23 — số PHÂN BIỆT được, không phải chuỗi"),
    T("/api/v2/billing/du-thao", ten="billing/du-thao — dự thảo hoá đơn",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="du_thao_hoa_don.chi_tiet_json mang dấu A/B"),
    T("/api/v2/dang-ky", ten="dang-ky — đăng ký gói của tenant",
      khang_dinh_a=['"tenant_id": {tid_a}'], khang_dinh_b=['"tenant_id": {tid_b}'],
      ghi_chu="han_muc.tenant_id là số định danh tenant, luôn có mặt"),
    T("/api/v2/doi-soat/dot", ten="doi-soat/dot — đợt đối soát của tenant",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="ds_dot.ten_file mang dấu A/B"),
    T("/api/v2/don/can-doi-soat", ten="don/can-doi-soat — đơn cần đối soát",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="don_hang.ma_don mang dấu A/B"),
    T("/api/v2/don/xuat-csv", ten="don/xuat-csv — xuất CSV đơn hàng",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="KHÔNG phải JSON: thân là CSV, phép so chạy trên văn bản thô"),
    T("/api/v2/g09/can-soat", ten="g09/can-soat — mã trạng thái cần người xem",
      kieu="toan_cuc", khang_dinh_a=['"ma": 110'], khang_dinh_b=['"ma": 110'],
      ghi_chu="KHÔNG đọc CSDL (bảng tĩnh trang_thai_hang) ⇒ hai tenant phải nhận GIỐNG NHAU. "
              "Mã 110 ở đây là DỮ LIỆU có sẵn của G09, KHÔNG phải phán quyết D-4 của tệp này"),
    T("/api/v2/g09/suc-khoe-hang", ten="g09/suc-khoe-hang — sức khoẻ tầng hãng",
      kieu="toan_cuc", khang_dinh_a=['"G09 SANDBOX"'], khang_dinh_b=['"G09 SANDBOX"'],
      ghi_chu="thanh phần cấu hình toàn cục; phải giống nhau và KHÔNG chứa dấu tenant nào"),
    T("/api/v2/goi", ten="goi — danh mục gói dịch vụ (toàn cục)",
      kieu="toan_cuc", khang_dinh_a=['"goi": [', '"goi_id": "free"'],
      khang_dinh_b=['"goi": [', '"goi_id": "free"'],
      ghi_chu="danh mục TOÀN CỤC: hai tenant nhận giống nhau, không dấu tenant nào"),
    T("/api/v2/hang", ten="hang — danh mục hãng vận chuyển (toàn cục)",
      kieu="toan_cuc", khang_dinh_a=['"ma": "jt"'], khang_dinh_b=['"ma": "jt"'],
      ghi_chu="carrier_providers KHÔNG có cột tenant; route KHÔNG kiểm phương thức"),
    T("/api/v2/san-sang", ten="san-sang — readiness (công khai)",
      kieu="toan_cuc", khang_dinh_a=['"ok": true'], khang_dinh_b=['"ok": true'],
      ghi_chu="trả chi tiết cho người ĐÃ đăng nhập; phải 200 — worker webhook do bộ đo bật"),
    T("/api/v2/suc-khoe", ten="suc-khoe — health (công khai, vô danh)",
      kieu="toan_cuc", phien_a="voda", phien_b="voda",
      khang_dinh_a=['"song_giay"'], khang_dinh_b=['"song_giay"'],
      ghi_chu="không đọc CSDL, không đọc đĩa; vô danh vẫn 200"),
    T("/api/v2/tai-chinh/cod", ten="tai-chinh/cod — sổ COD",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="tc_cod ⋈ don_hang, cả hai đều lọc theo c.tenant_id"),
    T("/api/v2/tai-chinh/cong-no", ten="tai-chinh/cong-no — công nợ",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="tc_cong_no.doi_tac là KHOÁ của dict trả về ⇒ dấu A/B nhìn thấy được"),
    T("/api/v2/tai-chinh/kiem-nhat-ky", ten="tai-chinh/kiem-nhat-ky — kiểm sổ bất biến",
      khang_dinh_a=['"so_dong": {so_dong_nk_a}'], khang_dinh_b=['"so_dong": {so_dong_nk_b}'],
      ghi_chu="thân phản hồi KHÔNG có trường chuỗi nào ⇒ phép so phải dùng SỐ DÒNG (A=1, B=2)"),
    T("/api/v2/tai-chinh/tong-so", ten="tai-chinh/tong-so — tổng hợp tài chính",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="cong_no lồng bên trong mang dấu A/B"),
    T("/api/v2/usage", ten="usage — mức dùng kỳ này",
      khang_dinh_a=['"tenant_id": {tid_a}'], khang_dinh_b=['"tenant_id": {tid_b}'],
      ghi_chu="trang_thai.tenant_id là số định danh; tham số `ky` bị route BỎ QUA"),
    T("/api/v2/usage/bao-cao", ten="usage/bao-cao — báo cáo mức dùng",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="su_kien_dung.idem_key mang dấu A/B"),
    T("/api/v2/usage/doi-soat", ten="usage/doi-soat — đối chiếu sổ với bộ đếm",
      khang_dinh_a=['"so_su_kien": {so_luong_a}'], khang_dinh_b=['"so_su_kien": {so_luong_b}'],
      ghi_chu="KHÔNG có trường chuỗi ⇒ dùng số sự kiện (A=2, B=5)"),
    T("/api/v2/usage/su-kien", ten="usage/su-kien — sổ sự kiện dùng",
      khang_dinh_a=["{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="su_kien_dung.idem_key mang dấu A/B"),
    T("/api/v2/usage/tinh-phi", ten="usage/tinh-phi — tính phí kỳ này",
      khang_dinh_a=['"tenant_id": {tid_a}'], khang_dinh_b=['"tenant_id": {tid_b}'],
      ghi_chu="tenant_id là khoá mức cao nhất; phép tính thuần đọc, không ghi"),
    T("/api/v2/webhook/nhan/{wh_ma_a}", ten="webhook/nhan — chữ ký của B không mở được cửa A",
      method="POST", than={"event_id": "EVT-{canary_a}"}, tu_ky_a="a", tu_ky_b="b",
      doi_chung_a=[202], doi_chung_b=[401],
      khang_dinh_a=['"code": 1'], khang_dinh_b=["chữ ký"],
      ghi_chu="A: mã webhook A + bí mật A ⇒ 202. B: đúng mã webhook A nhưng ký bằng bí mật B ⇒ 401"),
    T("/api/v2/webhook/nhan/{wh_ma_b}", ten="webhook/nhan — chiều ngược lại (đối chứng đường)",
      method="POST", than={"event_id": "EVT-{canary_b}"}, tu_ky_a="b", tu_ky_b="a",
      doi_chung_a=[202], doi_chung_b=[401],
      khang_dinh_a=['"code": 1'], khang_dinh_b=["chữ ký"],
      ghi_chu="B: mã webhook B + bí mật B ⇒ 202. A: mã webhook B nhưng ký bằng bí mật A ⇒ 401"),
    # Hợp đồng của cửa webhook: lượt ĐẦU của một `event_id` mới là **202**, lượt GỬI LẠI CÙNG
    # `event_id` là **200** (`da_nhan_truoc_do`). Ca này đo vế 200 để đối chứng dương của mục
    # webhook có ĐÚNG mã mà đề bài yêu cầu, không phải một mã khác được miễn trừ.
    T("/api/v2/webhook/nhan/{wh_ma_a}", ten="webhook/nhan — gửi lại cùng event_id ⇒ 200",
      method="POST", than={"event_id": "EVT-{canary_a}"}, tu_ky_a="a", tu_ky_b="b",
      doi_chung_a=[200], doi_chung_b=[401],
      khang_dinh_a=['"da_nhan_truoc_do"'], khang_dinh_b=["chữ ký"],
      ghi_chu="cùng event_id đã đẩy ở ca trước ⇒ 200 chống trùng; ký bằng bí mật B vẫn 401"),
    T("/api/v2/webhook/su-kien", ten="webhook/su-kien — sổ sự kiện webhook của tenant",
      khang_dinh_a=["{canary_a}", "EVT-{canary_a}"], khang_dinh_b=["{canary_b}"],
      ghi_chu="sự kiện do ca webhook/nhan vừa đẩy vào A phải HIỆN ở đây và VẮNG ở lượt của B"),
]


# ═════════════════════════════════════════════════════════════════════════════════════════════
# 0. TIỆN ÍCH
# ═════════════════════════════════════════════════════════════════════════════════════════════
def chay_liet_ke(app_dir=None, giay=900):
    return BOT.liet_ke(app_dir or APP, giay=giay)


def chay_cach_ly(app_dir=None, ca=None, giay=900):
    return BOT.chay_may_chu(app_dir or APP, "cach-ly", {"ca": ca if ca is not None else CAC_CA},
                            giay=giay)


_NHO = {}


def liet_ke_goc():
    if "goc" not in _NHO:
        _NHO["goc"] = chay_liet_ke(APP)
    return _NHO["goc"]


def cach_ly_goc():
    if "cl" not in _NHO:
        _NHO["cl"] = chay_cach_ly(APP)
    return _NHO["cl"]


def dem_ca(ra):
    """Đọc số ca / số skip từ đầu ra unittest — CÙNG cách đọc của các bộ G16-G18."""
    import re
    m = re.search(r"Ran (\d+) test", ra)
    s = re.search(r"skipped=(\d+)", ra)
    return (int(m.group(1)) if m else 0, int(s.group(1)) if s else 0)


# ═════════════════════════════════════════════════════════════════════════════════════════════
# A. BỘ TRÍCH THỨ BA — TỰ KIỂM
# ═════════════════════════════════════════════════════════════════════════════════════════════
class A_BoTrichThuBa(unittest.TestCase):

    def test_a1_tang_tinh_va_tang_thi_hanh_deu_lam_viec(self):
        """TỰ KIỂM BỘ DÒ: một bộ trích trả rỗng làm mọi phép so dưới đây xanh vô nghĩa."""
        kq = liet_ke_goc()
        self.assertGreater(len(kq["hang_so"]), 50, "moi được quá ít hằng số /api/v2")
        self.assertGreater(len(kq["ung_vien"]), 80, "không gian ứng viên quá nhỏ")
        self.assertGreater(len(kq["route"]), 80, "đo được quá ít route")
        print("\n  [A1] hằng số biên dịch=%d · ứng viên(tĩnh)=%d · CÓ ROUTE(thi hành)=%d"
              % (len(kq["hang_so"]), len(kq["ung_vien"]), len(kq["route"])))

    def test_a2_tang_thi_hanh_THUC_SU_loai_bot(self):
        """TẦNG THI HÀNH PHẢI LÀM VIỆC THẬT, không phải vật trang trí.

        Ứng viên tĩnh là SIÊU TẬP; nếu số route cuối bằng số ứng viên thì tầng thi hành chưa
        loại được gì, và "đo bằng thi hành" chỉ là lời nói.
        """
        kq = liet_ke_goc()
        self.assertLess(len(kq["route"]), len(kq["ung_vien"]),
                        "tầng thi hành không loại ứng viên nào ⇒ nó không có răng")
        # Đường bị loại ở MỌI 4 phương thức mới là "không phải route"; một đường chỉ bị loại ở
        # vài phương thức thì vẫn là route thật. Phải tách hai thứ đó ra, nếu không con số
        # "đã loại" sẽ đếm cả những đường đang phục vụ.
        self.assertEqual(["/api/v2/platform/", "/api/v2/webhook/nhan/"],
                         kq["khong_phai_route"],
                         "danh sách đường KHÔNG PHẢI route đã đổi ⇒ đọc lại kết luận A7")
        print("  [A2] tĩnh %d → thi hành %d; loại %d lượt, trong đó %d đường bị loại ở MỌI "
              "phương thức: %s"
              % (len(kq["ung_vien"]), len(kq["route"]), len(kq["roi"]),
                 len(kq["khong_phai_route"]), kq["khong_phai_route"]))

    def test_a3_cau_chu_nhanh_roi_dung_la_cau_chu_cua_router(self):
        """Phép phân loại bám vào ĐÚNG CÂU CHỮ của nhánh rơi — phải tự kiểm câu đó còn đúng.

        Nếu ai đó sửa câu chữ trong `server.py`, bộ đếm sẽ im lặng đếm sai. Ca này làm nó ĐỎ.
        """
        nguon = BOT.doc_ma(os.path.join(APP, "server.py"))
        self.assertEqual(nguon.count('{"loi": "%s"}' % BOT.CAU_ROI), BOT.SO_NHANH_ROI,
                         "số nhánh rơi trong server.py đã đổi ⇒ phép phân loại phải xem lại")
        print("  [A3] server.py có ĐÚNG %d nhánh rơi \"%s\"" % (BOT.SO_NHANH_ROI, BOT.CAU_ROI))

    def test_a4_giam_sat_mang_zero_luot_ra_ngoai_loopback(self):
        """BAN 1: mọi phép đo lớp HTTP chỉ chạm 127.0.0.1. Đo, không hứa."""
        kq = liet_ke_goc()
        self.assertEqual([], kq["giam_sat"]["host_ngoai_loopback"],
                         "có lượt connect RA NGOÀI loopback ⇒ vi phạm BAN 1")
        self.assertGreater(kq["giam_sat"]["so_luot_connect"], 100,
                           "quá ít lượt connect ⇒ lưới giám sát không thật sự chạy")
        print("  [A4] %d lượt connect · 0 lượt ra ngoài loopback"
              % kq["giam_sat"]["so_luot_connect"])

    def test_a5_bo_trich_ba_khong_co_route_la(self):
        """INVARIANT: mọi route bộ ba đo được phải nằm trong tập của AG-06 (sau khi bỏ artefact).

        Lệch ở đây nghĩa là bộ ba đang BỊA route — chứ không phải "khác phạm vi".
        """
        import re
        kq = liet_ke_goc()
        ag06 = _ag06_route()
        chuan = lambda p: re.sub(r"/\d+", "/{id}", p.replace("g19-khong-co", "{ma}"))
        la = sorted({chuan(r) for r in kq["route"]} - ag06)
        self.assertEqual([], la, "bộ ba đo route mà AG-06 KHÔNG thấy: %s" % la)
        print("  [A5] 0 route lạ: cả %d route của bộ ba đều nằm trong tập AG-06" % len(kq["route"]))

    def test_a6_bo_trich_ba_phu_31_muc_con_thieu_cua_AG01(self):
        """PHÉP SO QUYẾT ĐỊNH: 104 (AG-06) − 73 (AG-01) = 31 mục.

        Bộ ba phải THẤY **30 route thật** trong khoảng trống đó; mục thứ 31
        (`/api/v2/platform/`) KHÔNG phải route và ca A7 đo riêng điều đó. Nói cách khác: bộ ba
        không "bỏ quên" mục nào — nó chỉ nói mục thứ 31 không phải route, và nói có bằng chứng.
        """
        import re
        kq = liet_ke_goc()
        ag06 = _ag06_route()
        ag01 = _ag01_route()
        thieu = sorted(ag06 - ag01)
        self.assertEqual(31, len(thieu), "khoảng trống AG-06 − AG-01 KHÔNG còn là 31 mục")
        self.assertEqual(sorted(HAI_MUOI_MOT), thieu,
                         "danh sách 31 mục ghim trong tệp KHÁC phép so thật")
        that = [m for m in thieu if m not in KHONG_PHAI_ROUTE]
        chuan = lambda p: re.sub(r"/\d+", "/{id}", p.replace("g19-khong-co", "{ma}"))
        cua_toi = {chuan(r) for r in kq["route"]} | set(kq["route"])
        mat = [m for m in that if m not in cua_toi and chuan(m) not in cua_toi]
        self.assertEqual([], mat, "bộ ba KHÔNG thấy các mục còn thiếu: %s" % mat)
        print("  [A6] AG-06=%d · AG-01=%d · khoảng trống=%d = %d route thật + %d artefact tiền tố"
              % (len(ag06), len(ag01), len(thieu), len(that), len(thieu) - len(that)))
        print("       bộ ba thấy đủ %d/%d route thật (mục còn lại do ca A7 đo riêng)"
              % (len(that) - len(mat), len(that)))

    def test_a7_RAM_platform_khong_phai_route(self):
        """`/api/v2/platform/` là hằng số TIỀN TỐ của cổng chặn, không phải route.

        Phép đo: phiên CÓ quyền nền tảng gọi đúng đường đó ⇒ phải rơi vào nhánh rơi. Nếu nó
        trả bất cứ thứ gì khác thì kết luận này SAI và phải rút lại.
        """
        kq = chay_cach_ly(APP, ca=[T("/api/v2/platform/", ten="platform/ — KHÔNG phải route",
                                     kieu="toan_cuc", phien_a="do", phien_b="do",
                                     doi_chung_a=[404], doi_chung_b=[404],
                                     khang_dinh_a=[BOT.CAU_ROI], khang_dinh_b=[BOT.CAU_ROI])])
        ca = kq["ca"][0]
        self.assertTrue(ca["A"]["dat"] and ca["B"]["dat"],
                        "phiên nền tảng gọi /api/v2/platform/ KHÔNG rơi vào nhánh rơi ⇒ "
                        "kết luận 'không phải route' phải rút lại")
        print("  [A7] /api/v2/platform/ → %s (nhánh rơi) ⇒ KHÔNG phải route" % ca["A"]["ma"])

    def test_a8_noi_ro_gioi_han_cap_phuong_thuc(self):
        """NÓI THẲNG GIỚI HẠN ĐÃ ĐO: ở cấp (đường, phương thức) bộ ba lệch AG-06 đúng 8 cặp.

        Hai nguyên nhân, và chúng KHÁC nhau về phía ai đúng:

        * **Bộ ba ĐÚNG, AG-06 thừa 7 cặp.** `re.fullmatch` khớp mà không có nhánh `method ==`
          nào thì router vẫn trả 404 RIÊNG CỦA ROUTE (hoặc 403 do `_can` chạy TRƯỚC khi kiểm
          phương thức) — bộ phân loại theo phản hồi không phân biệt được "có handler cho phương
          thức này" với "khớp mẫu nhưng không có handler". 4 cặp thuộc `/api/v2/platform/`
          (không phải route) và 3 cặp thuộc `/api/v2/webhook/nhan/{ma}` (thật ra chỉ POST).
        * **AG-06 ĐÚNG, bộ ba thừa 1 cặp**: `DELETE /api/v2/platform/tenants/{id}` — `_can` chạy
          trước khi kiểm phương thức nên trả 403, và 403 bị bộ ba tính là "có route".

        Đây là GIỚI HẠN, không phải sai số giấu. Vì thế mọi KHẲNG ĐỊNH ĐỘ PHỦ của tệp này ở cấp
        ĐƯỜNG, không ở cấp phương thức.
        """
        import re
        kq = liet_ke_goc()
        chuan = lambda p: re.sub(r"/\d+", "/{id}", p.replace("g19-khong-co", "{ma}"))
        toi = {(chuan(a), b) for a, b in kq["cap"]}
        ag06 = _ag06_cap_mo_rong()
        thua_cua_toi = sorted(toi - ag06)
        thua_cua_ag06 = sorted(ag06 - toi)
        self.assertEqual(8, len(thua_cua_toi) + len(thua_cua_ag06),
                         "số cặp lệch ở cấp phương thức đã đổi ⇒ đọc lại kết luận của ca này")
        self.assertEqual(1, len(thua_cua_toi), "bộ ba thừa ĐÚNG 1 cặp (DELETE platform/tenants/{id})")
        print("  [A8] cấp (đường, phương thức): bộ ba=%d · AG-06(mở rộng)=%d" % (len(toi), len(ag06)))
        print("       bộ ba thừa %d cặp: %s" % (len(thua_cua_toi), thua_cua_toi))
        print("       AG-06 thừa %d cặp: %s" % (len(thua_cua_ag06), thua_cua_ag06))


def _ve_ag06(p):
    """Quy ước hoá đường của CA ĐO về cách viết của AG-06 để so tập hợp.

    Ca webhook dùng HAI mã webhook cụ thể (`{wh_ma_a}`, `{wh_ma_b}`) để đo cả hai chiều chữ ký,
    nhưng AG-06 chỉ có MỘT mục `/api/v2/webhook/nhan/{ma}`. Khi ĐẾM ĐỘ PHỦ phải gộp chúng lại,
    nếu không thì một route được đếm hai lần và con số cuối sẽ sai.
    """
    if p.startswith("/api/v2/webhook/nhan/"):
        return "/api/v2/webhook/nhan/{ma}"
    return p


def _ag06_cap_mo_rong():
    """Cặp (đường, phương thức) của AG-06, mở rộng mục "không có nhánh `method`" ra 4 phương thức.

    AG-06 ghi `None` khi trong mã nguồn KHÔNG có nhánh kiểm phương thức — nghĩa là MỌI phương
    thức đều tới được handler. Muốn so với bộ ba (vốn thử cả 4) thì phải mở rộng như vậy.
    """
    _ag06_route()
    import re

    def chuan(p):
        return re.sub(r"/\d+", "/{id}", p)

    ra = set()
    for (p, me) in _NHO["ag06_cap_tho"]:
        if me:
            ra.add((chuan(p), me))
        else:
            for m in ("GET", "POST", "PUT", "DELETE"):
                ra.add((chuan(p), m))
    return ra


def _ag06_route():
    """Tập route của AG-06 — chạy CHÍNH hàm của họ, không chép tay."""
    if "ag06" not in _NHO:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "g17b_g19", os.path.join(APP, "thu", "thu_g17_baomat.py"))
        m = importlib.util.module_from_spec(spec)
        sys.modules["g17b_g19"] = m
        spec.loader.exec_module(m)
        cua = m._cua_tu_nguon(os.path.join(APP, "server.py"))
        _NHO["ag06"] = {p for (p, _me) in cua}
        _NHO["ag06_cap_tho"] = set(cua)
    return _NHO["ag06"]


def _ag01_route():
    """Tập route của AG-01 — chạy CHÍNH các hàm trích của họ, không chép tay."""
    if "ag01" not in _NHO:
        import importlib.util
        import re
        spec = importlib.util.spec_from_file_location(
            "q18_g19", os.path.join(APP, "thu", "thu_qa_g18.py"))
        m = importlib.util.module_from_spec(spec)
        sys.modules["q18_g19"] = m
        spec.loader.exec_module(m)
        nguon = m._doc_app("server.py")
        ra = set()
        for (d, _me) in m.duong_ghi_tinh():
            ra.add(d)
        for d in m.duong_ghi_dong():
            ra.add(d)
        for d in m.RE_STATIC_PLATFORM.findall(nguon):
            ra.add(d)
        for mau in m.RE_FULLMATCH.findall(nguon):
            if mau.startswith("/api/v2/platform/"):
                ra.add(mau)

        def chuan_hoa(p):
            return p.replace(r"(\d+)", "{id}").replace(r"([A-Za-z0-9_-]+)", "{ma}")

        def mo_rong(p):
            mm = re.search(r"\(([^()]*\|[^()]*)\)", p)
            if not mm:
                return [p]
            o = []
            for phan in mm.group(1).split("|"):
                o += mo_rong(p[:mm.start()] + phan + p[mm.end():])
            return o

        _NHO["ag01"] = {x for d in ra for x in mo_rong(chuan_hoa(d))}
    return _NHO["ag01"]


# ═════════════════════════════════════════════════════════════════════════════════════════════
# B. ĐỘT BIẾN — CHỨNG MINH BỘ TRÍCH CÓ RĂNG (chạy trên BẢN SAO, không sửa tệp thật)
# ═════════════════════════════════════════════════════════════════════════════════════════════
class B_DotBien(unittest.TestCase):

    def test_b1_tiem_route_gia_thi_PHAI_thay(self):
        """ĐỘT BIẾN DƯƠNG: tiêm một route THẬT SỰ được phục vụ ⇒ bộ trích phải thấy nó.

        Ca này còn kiểm chính lượt HTTP của route giả: phải 200 và ĐÚNG thân đã tiêm — nếu
        không thì "thấy" chỉ là thấy một cái tên, chứ không phải thấy một route chạy được.
        """
        goc = liet_ke_goc()
        nguon, than = BOT.tiem_route(BOT.doc_ma(os.path.join(APP, "server.py")),
                                     "/api/v2/g19-tiem-route")
        kq = BOT.liet_ke(BOT.ban_sao_app(APP, nguon))
        self.assertIn("/api/v2/g19-tiem-route", kq["route"], "bộ trích KHÔNG thấy route giả")
        self.assertEqual(len(goc["route"]) + 1, len(kq["route"]),
                         "số route phải tăng ĐÚNG 1")
        hit = [m for m in kq["chi_tiet"]
               if m["duong"] == "/api/v2/g19-tiem-route" and m["method"] == "GET"][0]
        self.assertEqual(200, hit["ma"], "route giả không phục vụ được")
        self.assertEqual(than, hit["than"], "thân phản hồi của route giả KHÁC thân đã tiêm")
        print("  [B1] tiêm route giả: %d → %d route; lượt GET trả 200 đúng thân đã tiêm"
              % (len(goc["route"]), len(kq["route"])))

    def test_b2_bia_dang_CHU_THICH_thi_tang_tinh_phai_tu_choi(self):
        """ĐỘT BIẾN ÂM (tầng tĩnh): chú thích `#` chứa `/api/v2/...` KHÔNG được biên dịch.

        Chứng minh tầng tĩnh đọc BẢNG HẰNG SỐ chứ không `grep` văn bản.
        """
        nguon = BOT.tiem_bia(BOT.doc_ma(os.path.join(APP, "server.py")),
                             "/api/v2/g19-bia-chu-thich", "chu_thich")
        uv, _ = BOT.ung_vien(nguon)
        self.assertNotIn("/api/v2/g19-bia-chu-thich", uv,
                         "chuỗi trong CHÚ THÍCH lọt được vào không gian ứng viên ⇒ tầng tĩnh "
                         "đang đọc văn bản, không đọc mã đã biên dịch")
        print("  [B2] bịa dạng CHÚ THÍCH: không vào nổi không gian ứng viên (đúng)")

    def test_b3_bia_dang_CHUOI_THAT_thi_tang_thi_hanh_phai_loai(self):
        """ĐỘT BIẾN ÂM (tầng thi hành): hằng số chuỗi THẬT thì tầng tĩnh SẼ nhận.

        Đây là ca chứng minh tầng THI HÀNH có răng: nếu chỉ có tầng tĩnh, bộ trích sẽ báo
        "/api/v2/g19-bia-chuoi" là route, và đó là route BỊA.
        """
        nguon = BOT.tiem_bia(BOT.doc_ma(os.path.join(APP, "server.py")),
                             "/api/v2/g19-bia-chuoi", "chuoi")
        uv, _ = BOT.ung_vien(nguon)
        self.assertIn("/api/v2/g19-bia-chuoi", uv,
                      "hằng số THẬT phải vào không gian ứng viên — nếu không, ca này vô hiệu")
        kq = BOT.liet_ke(BOT.ban_sao_app(APP, nguon))
        self.assertNotIn("/api/v2/g19-bia-chuoi", kq["route"],
                         "tầng thi hành KHÔNG loại được chuỗi bịa ⇒ nó không có răng")
        loai = {m["method"]: m["ma"] for m in kq["chi_tiet"]
                if m["duong"] == "/api/v2/g19-bia-chuoi"}
        self.assertEqual({"GET": 404, "POST": 404, "PUT": 404, "DELETE": 404}, loai,
                         "chuỗi bịa phải rơi vào 404 nhánh rơi ở MỌI phương thức")
        print("  [B3] bịa dạng CHUỖI: tĩnh NHẬN (đúng) → thi hành LOẠI bằng 404 nhánh rơi (đúng)")

    def test_b4_xoa_route_that_thi_PHAI_mat(self):
        """ĐỘT BIẾN ÂM: xoá một route THẬT khỏi bản sao ⇒ bộ trích phải MẤT ĐÚNG nó.

        Nếu vẫn báo "có", bộ trích đang đọc danh sách ghim cứng chứ không đo.
        """
        goc = liet_ke_goc()
        dich = "/api/v2/suc-khoe"
        nguon = BOT.xoa_route(BOT.doc_ma(os.path.join(APP, "server.py")), dich, "GET")
        kq = BOT.liet_ke(BOT.ban_sao_app(APP, nguon))
        self.assertNotIn(dich, kq["route"], "xoá route thật mà bộ trích vẫn thấy ⇒ ghim cứng")
        self.assertEqual([dich], sorted(set(goc["route"]) - set(kq["route"])),
                         "phải mất ĐÚNG route đã xoá, không mất thêm route nào khác")
        print("  [B4] xoá %s: %d → %d route, mất đúng 1 và đúng route đó"
              % (dich, len(goc["route"]), len(kq["route"])))

    def test_b5_dot_bien_RO_RI_thi_phep_do_cach_ly_PHAI_do(self):
        """TỰ KIỂM BỘ ĐO CÁCH LY: phá cách ly ở `/api/v2/audit` ⇒ phép đo C phải bắt được.

        Không có ca này thì mọi ca C xanh đều vô nghĩa: một bộ đo không thể đỏ là bộ đo không đo.
        Đột biến: bỏ `WHERE tenant_id=?` khỏi truy vấn audit ⇒ lượt của B sẽ mang dấu của A.
        """
        nguon = BOT.doc_ma(os.path.join(APP, "server.py"))
        moc = ('SELECT * FROM audit WHERE tenant_id=? ORDER BY id DESC LIMIT 200", (tenant_id,)')
        self.assertIn(moc, nguon, "truy vấn audit đã đổi ⇒ ca đột biến phải viết lại")
        nguon_ro = nguon.replace(
            moc, 'SELECT * FROM audit ORDER BY id DESC LIMIT 200", ()')
        self.assertNotEqual(nguon, nguon_ro)
        ca = [c for c in CAC_CA if c["duong"] == "/api/v2/audit"]
        kq = chay_cach_ly(BOT.ban_sao_app(APP, nguon_ro), ca=ca)
        c = kq["ca"][0]
        self.assertTrue(c["ro_ri"], "bộ đo cách ly KHÔNG bắt được rò rỉ đã tiêm ⇒ nó không đo")
        self.assertFalse(c["dat"], "ca phải ĐỎ khi có rò rỉ")
        print("  [B5] tiêm rò rỉ vào /api/v2/audit ⇒ bộ đo báo rò_ri=True, ca ĐỎ (đúng)")


# ═════════════════════════════════════════════════════════════════════════════════════════════
# C. ĐO CÁCH LY TENANT CHO 31 MỤC CÒN THIẾU
# ═════════════════════════════════════════════════════════════════════════════════════════════
class C_DoCachLy(unittest.TestCase):
    """MỘT tiến trình đo cho cả 31 ca; mỗi ca là một test riêng để nhìn được ca nào hỏng."""

    @classmethod
    def setUpClass(cls):
        cls.kq = cach_ly_goc()
        cls.theo_ten = {}
        for c in cls.kq["ca"]:
            cls.theo_ten.setdefault(c["mau"], []).append(c)
        cls.ngoai_loopback = cls.kq["giam_sat"]["host_ngoai_loopback"]

    def test_c0_giam_sat_mang_zero_luot_ra_ngoai(self):
        """BAN 1 áp cho CẢ phép đo cách ly: 0 lượt connect ra ngoài loopback."""
        self.assertEqual([], self.ngoai_loopback, "có lượt connect ra ngoài loopback")
        print("\n  [C0] %d lượt connect · 0 lượt ra ngoài loopback"
              % self.kq["giam_sat"]["so_luot_connect"])

    def test_c1_moi_ca_deu_co_doi_chung_duong_va_khong_ro_ri(self):
        """TỔNG HỢP: đếm ĐẠT / CHƯA ĐO / RÒ RỈ trên toàn bộ 31 mục.

        Đồng thời TỰ KIỂM TÍNH KHÔNG-RỖNG: một ca có danh sách khẳng định RỖNG thì `all([])` là
        True, tức là nó "đạt" mà không hề khẳng định gì. Ca này làm chuyện đó thành ĐỎ.
        """
        rong = [(c["mau"], phia) for c in self.kq["ca"] for phia in ("A", "B")
                if not c[phia]["khang_dinh"]]
        self.assertEqual([], rong, "ca có khẳng định RỖNG (đạt rỗng, vô nghĩa): %s" % rong)
        dat = [c for c in self.kq["ca"] if c["dat"]]
        chua = [c for c in self.kq["ca"] if not c["dat"]]
        ro = [c for c in self.kq["ca"] if c["ro_ri"]]
        self.assertEqual([], ro, "có mục RÒ RỈ: %s" % [c["mau"] for c in ro])
        print("  [C1] ĐẠT %d/%d · CHƯA ĐO %d · RÒ RỈ %d · khẳng định rỗng 0"
              % (len(dat), len(self.kq["ca"]), len(chua), len(ro)))
        for c in chua:
            print("       CHƯA ĐO: %-34s A=%s(%s) B=%s(%s)"
                  % (c["mau"], c["A"]["ma"], "đạt" if c["A"]["dat"] else "KHÔNG",
                     c["B"]["ma"], "đạt" if c["B"]["dat"] else "KHÔNG"))

    def test_c2_khong_route_that_nao_bi_bo_quen(self):
        """31 MỤC phải được đo HẾT: 30 route thật + 1 mục chứng minh không phải route.

        Số CA nhiều hơn số MỤC là chuyện bình thường: một mục có thể cần nhiều lượt đo (ví dụ
        cửa webhook cần cả 202 lượt-đầu, 200 lượt-gửi-lại, và 401 khi ký sai). Điều phải khớp là
        **tập MỤC**, không phải số ca.

        Mục `/api/v2/platform/` không nằm trong danh sách ca C vì nó KHÔNG phải route — nó được
        đo bằng ca A7 (phiên nền tảng gọi vào ⇒ 404 nhánh rơi).
        """
        self.assertEqual(31, len(HAI_MUOI_MOT), "danh sách mục ghim phải là 31")
        do = {_ve_ag06(c["mau"]) for c in self.kq["ca"]}
        thieu = [m for m in HAI_MUOI_MOT if m not in do and m not in KHONG_PHAI_ROUTE]
        self.assertEqual([], thieu, "mục chưa được đo: %s" % thieu)
        self.assertEqual(30, len(do - set(KHONG_PHAI_ROUTE)),
                         "phải đo đủ 30 route THẬT (các ca webhook là nhiều CHIỀU của MỘT route)")
        print("  [C2] đã đo đủ 31/31 MỤC = 30 route thật (ca C) + 1 artefact (ca A7); "
              "dùng %d ca" % len(self.kq["ca"]))


def _sinh_ca_theo_route():
    """Sinh một test cho MỖI CA — để ca hỏng hiện đích danh, không lẫn vào một test tổng.

    Tên test phải kèm SỐ THỨ TỰ: một mục có thể có NHIỀU ca (cửa webhook cần cả lượt-đầu 202,
    lượt-gửi-lại 200, và chiều ngược lại). Đặt tên chỉ theo đường thì hai ca trùng tên và
    `setattr` sau ghi đè ca trước — ca thứ hai mất tích mà không ai thấy.
    """
    for i, ca in enumerate(CAC_CA):
        nhan = "%02d_%s" % (i, ca["duong"].strip("/").replace("/", "_").replace(
            "{", "").replace("}", "").replace("-", "_"))

        def _t(self, duong=ca["duong"], ca=ca):
            c = self.theo_ten.get(duong)
            c = [x for x in (c if isinstance(c, list) else [c]) if x["ten"] == ca["ten"]]
            self.assertTrue(c, "mục %s / ca %r không có kết quả đo" % (duong, ca["ten"]))
            c = c[0]
            self.assertTrue(c["A"]["dat"],
                            "%s: ĐỐI CHỨNG DƯƠNG hỏng — chủ sở hữu hợp lệ nhận %s, "
                            "thiếu %s" % (ca["ten"], c["A"]["ma"], c["A"]["khang_dinh"]))
            self.assertTrue(c["B"]["dat"],
                            "%s: ĐỐI CHỨNG ĐƯỜNG hỏng — lượt của tenant B nhận %s, "
                            "thiếu %s" % (ca["ten"], c["B"]["ma"], c["B"]["khang_dinh"]))
            self.assertFalse(c["ro_ri"], "%s: RÒ RỈ dữ liệu của A sang lượt của B" % ca["ten"])

        _t.__name__ = "test_c3_" + nhan
        _t.__doc__ = ca.get("ten", ca["duong"])
        setattr(C_DoCachLy, _t.__name__, _t)


_sinh_ca_theo_route()


# ═════════════════════════════════════════════════════════════════════════════════════════════
# D. CON SỐ CUỐI
# ═════════════════════════════════════════════════════════════════════════════════════════════
class D_ConSoCuoi(unittest.TestCase):

    def test_d1_con_so_phu(self):
        """X/104 — con số cuối, và nó phải KHỚP GIỮA HAI ĐƯỜNG ĐO ĐỘC LẬP.

        Đường 1: phép so tập hợp (bộ ba ↔ AG-06 ↔ AG-01). Đường 2: đếm số ca cách ly ĐẠT.
        Hai đường phải ra CÙNG một con số; lệch nghĩa là một trong hai đang nói dối.
        """
        import re
        kq = liet_ke_goc()
        ag06, ag01 = _ag06_route(), _ag01_route()
        chuan = lambda p: re.sub(r"/\d+", "/{id}", p.replace("g19-khong-co", "{ma}"))
        cua_toi = {chuan(r) for r in kq["route"]}
        that = ag06 - set(KHONG_PHAI_ROUTE)
        phu_ag01 = ag01 & that
        cl = cach_ly_goc()
        dat_that = {_ve_ag06(c["mau"]) for c in cl["ca"]
                    if c["dat"] and c["mau"] not in KHONG_PHAI_ROUTE}
        khong_dat = [c for c in cl["ca"] if not c["dat"]]

        self.assertEqual(103, len(that), "số route THẬT của AG-06 phải là 103")
        self.assertEqual(103, len(cua_toi & that), "bộ ba phải phủ đủ 103/103 route thật")
        self.assertEqual(len(that), len(phu_ag01) + len(dat_that),
                         "hai đường đếm độ phủ KHÔNG khớp nhau")
        print("\n  [D1] ================= CON SỐ CUỐI =================")
        print("       AG-06 đếm                 : %d mục" % len(ag06))
        print("         trong đó route THẬT     : %d" % len(that))
        print("         artefact tiền tố        : %d  (%s — ca A7 chứng minh không phải route)"
              % (len(ag06) - len(that), KHONG_PHAI_ROUTE[0]))
        print("       AG-01 phủ                 : %d route" % len(ag01))
        print("       Khoảng trống G18          : %d mục = %d route thật + 1 artefact"
              % (len(ag06 - ag01), len(ag06 - ag01) - len(KHONG_PHAI_ROUTE)))
        print("       Lượt này ĐO ĐƯỢC         : %d/%d mục khoảng trống (%d route thật + A7)"
              % (len(cl["ca"]) - len(khong_dat), len(cl["ca"]),
                 len(dat_that)))
        print("       CHƯA ĐO                   : %d" % len(khong_dat))
        print("       ⇒ ĐÃ CÓ BẰNG CHỨNG CÁCH LY TENANT: %d/%d route THẬT"
              % (len(phu_ag01) + len(dat_that), len(that)))
        print("         = %d (AG-01) + %d (AG-04, lượt này)" % (len(phu_ag01), len(dat_that)))
        print("       ⇒ Còn thiếu                : %d route"
              % (len(that) - len(phu_ag01) - len(dat_that)))
        for c in khong_dat:
            print("         CHƯA ĐO: %s" % c["mau"])

    @classmethod
    def kq_cach_ly(cls):
        return cach_ly_goc()


if __name__ == "__main__":
    if "--do" in sys.argv:
        kq = chay_cach_ly(APP)
        print(json.dumps(kq, ensure_ascii=False, indent=1))
        sys.exit(0)
    unittest.main(verbosity=2)
