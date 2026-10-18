#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G22 — PHÂN LOẠI 20 BỘ ĐỎ: BỘ ĐO NỀN HAY LỖI THẬT.

Bộ thử này KHÔNG sửa sản phẩm và KHÔNG sửa bộ thử khác. Nó làm ba việc:

  1. GHI BẢNG: 20 bộ đỏ + số ca + dòng FAIL/ERROR + lần chạy lại ở chế độ thay thế,
     kèm nhãn (N)/(S)/(L)/(C) và lý do. Bảng là dữ liệu của `docs/G22_PHAN_LOAI_DO.md`.
  2. MÃ HOÁ TIÊU CHÍ: `chan_doan()` biến bằng chứng thô thành nhãn. Bảng phải TỰ NHẤT
     QUÁN với `chan_doan()` — nếu không, nhãn chỉ là ý kiến.
  3. TỰ KIỂM CÓ RĂNG (đối chứng tiêm lỗi): sao `app/` sang thư mục TẠM, chạy
     `thu_han_muc_nguyen_tu.py` trên bản sao:
       · bản SẠCH, KHÔNG khai kho  → ĐỎ vì `migrate` fail-closed  ⇒ phải xếp (S);
       · cùng bản sạch, khai kho   → XANH (đối chứng đường)      ⇒ (S) là đúng;
       · TIÊM một lỗi THẬT vào `billing._cong_bo_dem_co_tran` của bản sao, khai kho
         y như trên               → ĐỎ vì hạn mức không còn nguyên tử ⇒ phải xếp (L).
     Phép tiêm chỉ chạm bản sao. Cây thật được băm trước/sau để chứng minh.

Vì sao cần đối chứng tiêm lỗi: một bảng toàn nhãn (S) rất dễ đúng vì mọi thứ đỏ đều
bị gọi là "bộ đo cũ". Muốn chứng minh phép phân loại KHÔNG mù với lỗi sản phẩm, phải
tạo một lỗi sản phẩm thật rồi xem nó có bị xếp (L) hay không.

PHẠM VI: chỉ đọc cây + chạy tiến trình con trên thư mục TẠM. Không mạng, không CSDL
thật, không git write. Mọi lượt chạy lại dùng `VIP_KHO_DANG_CHAY=sqlite` — đây là
"chế độ thay thế" cho các bộ KHÔNG có `VIP_*_CHE_DO`; xem docs/G22_PHAN_LOAI_DO.md §1.

CHẠY
    python3 app/thu/thu_g22_phanloai.py          # bảng tóm tắt + 6 ca tự kiểm
    python3 app/thu/thu_g22_phanloai.py -v       # chi tiết từng ca
    python3 app/thu/thu_g22_phanloai.py --chi-bang   # chỉ in bảng, không tự kiểm
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC = os.path.dirname(os.path.abspath(__file__))                 # app/thu
APP = os.path.dirname(GOC)                                       # app
DU_AN = os.path.dirname(APP)
BO_TU_KIEM = "thu_han_muc_nguyen_tu.py"                          # bộ thử tự chứa, 5 ca, 0,2s
TEP_TIEM = "billing.py"                                          # tệp sản phẩm bị tiêm (BẢN SAO)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. DẤU HIỆU — ánh xạ văn bản lỗi sang NGUYÊN NHÂN, không ánh xạ sang nhãn
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# Mỗi dấu hiệu là một SỰ THẬT ĐO ĐƯỢC, không phải một phỏng đoán:
#   · khai_kho        — `migrate.py` TỪ CHỐI vì chưa khai `KHO_DANG_CHAY` (G22 fail-closed).
#   · migrate_race    — `.dang-ghi` / `disk I/O error` khi nhiều tiến trình cùng `sao_luu()`.
#   · tut_schema      — `migrate.py --rollback` TỪ CHỐI TỤT SCHEMA (G21/G22 fail-closed).
#   · schema_cu       — kỳ vọng cứng "schema = 9" trong khi `PHIEN_BAN_SCHEMA = 10`.
#   · so_route_cu     — ghim 103 route / khoảng trống 31; G22 thêm 1 route.
#   · so_dem_cu       — ghim số hàm / số dòng trong `http_jt.py`; mã đã dài ra.
#   · tham_so_moi     — lớp truy vấn G22 TỪ CHỐI (400) tham số lạ thay vì bỏ qua.
#   · cay_sach        — ca cần cây BẨN; trên cây sạch phép đo rỗng.
#   · bang_route_cu   — bảng khai route của bộ thử thiếu route MỚI của G22.
#   · ung_vien_cu     — kỳ vọng C5 chỉ có 1 ứng viên; nay có 2 nên tiêm 1 không đủ đỏ.
#   · kien_truc       — `migrate.py` nạp thẳng `sqlite3`, vi phạm biên driver.
DAU_HIEU = (
    ("khai_kho", re.compile(r"TỪ CHỐI: CHƯA KHAI kho đang chạy|DỪNG: CSDL ở schema v0")),
    ("migrate_race", re.compile(r"\.dang-ghi|disk I/O error|No such file or directory.*sao-luu")),
    ("tut_schema", re.compile(r"TỪ CHỐI: TỤT SCHEMA")),
    ("schema_cu", re.compile(r"khác 9|!=\s*9\b|VẪN CHẠY được.*schema cũ|schema 9")),
    ("so_route_cu", re.compile(r"31 != 32|103 != 104|phải là 103|khoảng trống AG-06")),
    ("so_dem_cu", re.compile(r"\{'CHUNG': 38|831 not found in|\[285, 311, 344, 946\] != ")),
    ("tham_so_moi", re.compile(r"KeyError: 'don'|400 != 200")),
    ("cay_sach", re.compile(r"cây SẠCH TRƠN")),
    ("bang_route_cu", re.compile(r"/api/v2/don/loc-mo-ta")),
    ("ung_vien_cu", re.compile(r"1/2 · phán quyết=DONG|C5 ĐỎ LẠI")),
    ("kien_truc", re.compile(r"nạp trực tiếp sqlite3|migrate\.py dòng")),
)
STALE = {"khai_kho", "tut_schema", "schema_cu", "so_route_cu", "so_dem_cu", "tham_so_moi",
         "cay_sach", "bang_route_cu", "ung_vien_cu"}
LOI = {"migrate_race", "kien_truc"}


def nhan_dien(van_ban):
    """Trả TÊN NGUYÊN NHÂN đầu tiên khớp, hoặc 'khac'."""
    for ten, mau in DAU_HIEU:
        if mau.search(van_ban or ""):
            return ten
    return "khac"


def chan_doan(ban_ghi):
    """Suy nhãn từ bằng chứng. KHÔNG đọc nhãn đã ghi.

    Thứ tự luật (mỗi luật có đối chứng riêng ở lớp `TuKiem`):
      1. exit 0                       → XANH.
      2. có `VIP_*_CHE_DO`, nền ĐỎ, gộp XANH, sản phẩm không đổi → (N).
      3. đã tiêm lỗi vào BẢN SAO, đối chứng sạch XANH, bản tiêm ĐỎ → (L).
      4. chạy lại sau khi sửa THIẾT LẬP (khai kho) mà XANH               → (S).
      5. mọi dấu hiệu còn lại đều thuộc nhóm "ghim sự thật cũ"           → (S).
      6. có dấu hiệu lỗi sản phẩm thật (race/kiến trúc)                  → (L).
      7. còn lại                                                          → (C).
    """
    if ban_ghi["exit"] == 0:
        return "XANH"
    if (ban_ghi.get("che_do") and (ban_ghi.get("gop") or {}).get("exit") == 0
            and not ban_ghi.get("san_pham_doi")):
        return "N"
    if ban_ghi.get("san_pham_doi") and (ban_ghi.get("doi_chung") or {}).get("exit") == 0:
        return "L"
    do_lai = ban_ghi.get("do_lai")
    if do_lai is not None:
        if do_lai.get("exit") == 0 and not ban_ghi.get("san_pham_doi"):
            return "S"
        van_ban = do_lai.get("fails") or []
    else:
        van_ban = ban_ghi.get("fails") or []
    loai = {nhan_dien(t) for t in van_ban}
    if van_ban and loai and loai <= STALE:
        return "S"
    if loai & LOI:
        return "L"
    return "C"


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. BẢNG 20 BỘ — dữ liệu của docs/G22_PHAN_LOAI_DO.md
# ══════════════════════════════════════════════════════════════════════════════════════════════
# `exit`/`ran`/`fails` = lượt MẶC ĐỊNH. `do_lai` = lượt chạy lại ở chế độ THAY THẾ
# (khai kho; hoặc gộp với bộ có CHE_DO). `nhan` do `chan_doan` kiểm lại ở test_01.
BANG = [
    {
        "so": 1, "bo": "thu_bao_mat.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 57,
        "fails": ["FAIL: test_e1_migrate_v4_dua_moi_secret_sang_v3 — AssertionError: 1 != 0 : "
                  "[migrate] Phiên bản hiện tại: 3 → đích: 10 · TỪ CHỐI: CHƯA KHAI kho đang chạy"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 57, "fails": []},
        "nhan": "S",
        "vi_sao": "Ca dựng CSDL v3 rồi gọi migrate THẬT trong tiến trình con; G22 bắt buộc khai "
                  "kho nên migrate từ chối TRƯỚC khi nâng cấp. Không phải lỗi sản phẩm: cùng "
                  "một dòng khai, 57/57 ca xanh.",
        "de_xuat": "Khai VIP_KHO_DANG_CHAY=sqlite trong chay_tat_ca.sh (một dòng) hoặc gọi "
                   "cau_hinh.khai_kho_kiem_thu() trong tiến trình con của ca e1.",
    },
    {
        "so": 2, "bo": "thu_g01_g02.py", "nhom": "B. API/tham số mới + fail-closed",
        "exit": 1, "ran": 21,
        "fails": ["ERROR: test_010_doi_tenant_id_trong_request_khong_vuot_quyen — KeyError: 'don' "
                  "(GET /api/v2/don?tenant_id=… bị lớp truy vấn TỪ CHỐI 400)",
                  "FAIL: test_014_migration_bao_toan_du_lieu — 1 != 0 : [migrate] TỪ CHỐI: CHƯA KHAI "
                  "kho đang chạy"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 21,
                   "fails": ["ERROR: test_010… — KeyError: 'don' (400 vì tham số lạ)",
                             "FAIL: test_014… — 1 != 0 : [migrate] TỪ CHỐI: TỤT SCHEMA "
                             "(bản sao lưu v0, CSDL v10)"]},
        "nhan": "S",
        "vi_sao": "Hai kỳ vọng cũ: (a) tham số `tenant_id` lạ trong query từng được BỎ QUA IM LẶNG, "
                  "nay bị 400 — bất biến 'không đổi được ngữ cảnh' vẫn đúng, chỉ đổi cách từ chối; "
                  "(b) rollback về schema cũ từng được phép, nay fail-closed đòi "
                  "`toi_da_biet_chua_kiem_duoc=True`.",
        "de_xuat": "Ca 010 nhận 400 là ĐẠT (hoặc kiểm bằng body — đã có); ca 014 gọi rollback kèm "
                   "cờ `--toi-da-biet-chua-kiem-duoc` và khẳng định TỪ CHỐI mặc định là ĐẠT.",
    },
    {
        "so": 3, "bo": "thu_g19_route.py", "nhom": "A. migrate + ghim số route",
        "exit": 1, "ran": 14,
        "fails": ["ERROR: test_a1_tang_tinh_va_tang_thi_hanh_deu_lam_viec — RuntimeError: may_chu_do "
                  "thất bại (exit 1) · TỪ CHỐI: CHƯA KHAI kho đang chạy",
                  "… 13 ERROR cùng gốc (a1,a2,a4–a8,b1,b3–b5,C_DoCachLy,d1)"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 49,
                   "fails": ["FAIL: test_a6_bo_trich_ba_phu_31_muc_con_thieu_cua_AG01 — 31 != 32",
                             "FAIL: test_d1_con_so_phu — 103 != 104"]},
        "nhan": "S",
        "vi_sao": "Thiếu khai kho làm máy chủ đo không dựng được (13 ERROR); khai kho xong chạy 49 ca, "
                  "còn 2 ghim số cũ: G22 thêm route `/api/v2/don/loc-mo-ta` nên 103→104 và khoảng "
                  "trống AG-06−AG-01 31→32.",
        "de_xuat": "Khai kho; cập nhật 103→104 và 31→32 (tốt hơn: đọc số từ baseline trong docs thay "
                   "vì ghim literal).",
    },
    {
        "so": 4, "bo": "thu_g19_tich_hop.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 8,
        "fails": ["EXIT_BO_DO=1 · PHÁN QUYẾT CỔNG: ĐỎ — runner HỎNG: mã thoát 1; log: "
                  "RuntimeError: migrate.py hỏng (mã 1) · TỪ CHỐI: CHƯA KHAI kho đang chạy"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 8, "fails": []},
        "nhan": "S",
        "vi_sao": "Bộ uỷ quyền chạy `trien_khai/g21-gioihan/chay.sh`; runner dựng nền bằng migrate "
                  "nên chết trước khi đo. Khai kho: 8/8 ca xanh.",
        "de_xuat": "Khai kho trong môi trường của runner (một dòng).",
    },
    {
        "so": 5, "bo": "thu_g20_baomat.py", "nhom": "A. migrate fail-closed (bộ con)",
        "exit": 1, "ran": 28,
        "fails": ["FAIL: test_b1_hai_bo_thu_cu_deu_xanh_tren_cay_co_tep_cua_wave — 1 != 0 : "
                  "app/thu/thu_qa_g17.py::A_Nen ĐỎ · ERROR: test_a6_khong_co_ket_noi_ra_ngoai "
                  "(migrate TỪ CHỐI)"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 28, "fails": []},
        "nhan": "S",
        "vi_sao": "Bộ này đo gián tiếp: nó chạy `thu_qa_g17.py` và đòi bộ đó xanh. qa_g17 đỏ vì "
                  "migrate chưa khai kho — cùng một gốc, không phải lỗi bảo mật.",
        "de_xuat": "Khai kho; không sửa gì trong thu_g20_baomat.",
    },
    {
        "so": 6, "bo": "thu_g20_dahang.py", "nhom": "C. ghim số hàm/số dòng",
        "exit": 1, "ran": 27,
        "fails": ["FAIL: test_a2_hai_ham_giu_chot_chan_hang_bi_gan_nhan_dung — "
                  "{'CHUNG': 38, 'DAC_THU_JT': 7} != {'CHUNG': 30, 'DAC_THU_JT': 7}",
                  "FAIL: test_a6_nhan_hieu_hang_trong_thong_diep… — 831 not found in "
                  "[108, 115, 116, 1035]",
                  "FAIL: test_a7_bon_nhanh_ma_bi_rang_buoc_hang — [285, 311, 344, 946] != "
                  "[285, 311, 343, 742]"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 27,
                   "fails": ["FAIL: test_a2… — {'CHUNG': 38, 'DAC_THU_JT': 7} != "
                             "{'CHUNG': 30, 'DAC_THU_JT': 7}",
                             "FAIL: test_a6… — 831 not found in [108, 115, 116, 1035]",
                             "FAIL: test_a7… — [285, 311, 344, 946] != [285, 311, 343, 742]"]},
        "nhan": "S",
        "vi_sao": "Ba con số ghim (30 hàm CHUNG, dòng 831, các dòng 344/742) là ảnh chụp `http_jt.py` "
                  "trước G22. Mã đã dài ra (38 hàm CHUNG; nhãn J&T ở dòng 1035; nhánh ở 343/946) — "
                  "bộ dò vẫn bắt đúng, chỉ kỳ vọng là ảnh cũ.",
        "de_xuat": "Cập nhật 3 ghim theo docs/G20_DA_HANG.md mới, hoặc bỏ ghim literal và đối chiếu "
                   "với chính bảng phân loại đọc từ tệp.",
    },
    {
        "so": 7, "bo": "thu_g20_saoluu.py", "nhom": "C. ghim schema = 9",
        "exit": 1, "ran": 41,
        "fails": ["FAIL: test_a5_ban_sao_luu_co_byte_va_mo_duoc — AssertionError: 10 != 9 : "
                  "phiên bản schema sau khôi phục khác 9"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 41,
                   "fails": ["FAIL: test_a5… — 10 != 9 : phiên bản schema sau khôi phục khác 9"]},
        "nhan": "S",
        "vi_sao": "`PHIEN_BAN_SCHEMA` nay là 10 (G22), ca vẫn ghim 9. Sản phẩm khôi phục đúng phiên "
                  "bản hiện hành; con số 9 là sự thật cũ.",
        "de_xuat": "So với `csdl.PHIEN_BAN_SCHEMA` thay vì literal 9.",
    },
    {
        "so": 8, "bo": "thu_g21_bimat.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 33,
        "fails": ["FAIL: test_e1/e2/e3_bi_mat_trong_{THAN,QUERY,DUONG_DAN}_khong_lot_vao_tep_nao — "
                  "máy chủ thật không mở cổng · [hub] DỪNG: CSDL ở schema v0, mã nguồn cần v10",
                  "FAIL: test_g2_tiem_lai_loi_D4_D5… (E2,E3) · FAIL: test_z1… (nhóm E)"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 33, "fails": []},
        "nhan": "S",
        "vi_sao": "`dung_nen_tam()` gọi migrate để dựng CSDL; thiếu khai kho ⇒ migrate từ chối ⇒ "
                  "schema v0 ⇒ máy chủ dừng. Các ca bí mật không hề đo được vì nền không dựng được. "
                  "Khai kho: 33/33 xanh.",
        "de_xuat": "Khai kho trong `dung_nen_tam()` (một dòng).",
    },
    {
        "so": 9, "bo": "thu_g21_saoluu.py", "nhom": "C. ghim schema = 9 (trong bộ đo)",
        "exit": 1, "ran": 23,
        "fails": ["FAIL: test_a5_khoi_phuc_ban_schema_thap_hon — Lists differ: "
                  "'(c) sau khi tụt schema, hệ VẪN CHẠY được (rc=0) trên schema cũ' != []",
                  "FAIL: test_c4_ban_va_lam_moi_kich_ban_chuyen_sang_FAIL_CLOSED — cùng S5"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 23,
                   "fails": ["FAIL: test_a5_khoi_phuc_ban_schema_thap_hon — Lists differ: "
                             "'(c) sau khi tụt schema, hệ VẪN CHẠY được (rc=0) trên schema cũ — "
                             "không một lời cảnh báo' != []"]},
        "nhan": "S",
        "vi_sao": "Bộ ĐO `trien_khai/g20-saoluu/fail_closed.py:329` ghim "
                  "`phien_ban_sau_khoi_phuc != 9`; nay schema đích là 10 nên điều kiện luôn đúng và "
                  "báo 'hệ vẫn chạy trên schema cũ' dù sản phẩm đã TỪ CHỐI khôi phục (không tụt "
                  "schema). Đây là ghim 9 trong BỘ ĐO, không phải lỗi migrate.",
        "de_xuat": "Thay literal 9 bằng `csdl.PHIEN_BAN_SCHEMA`/tham số trong fail_closed.py:329; "
                   "đổi tên kịch bản 'v6 đè lên v9' thành 'v6 đè lên bản hiện hành'.",
    },
    {
        "so": 10, "bo": "thu_g22_bimat.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 23,
        "fails": ["FAIL: test_a2_D4… / test_a3_D5… — máy chủ thật không mở cổng · [hub] DỪNG: CSDL "
                  "ở schema v0, mã nguồn cần v10",
                  "FAIL: test_b2_tiem_lai_loi… (A2,A3) · test_b4_doi_chung_DUONG… (A2)"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 23, "fails": []},
        "nhan": "S",
        "vi_sao": "Cùng gốc với thu_g21_bimat: nền dựng bằng migrate, thiếu khai kho ⇒ schema v0 ⇒ "
                  "không có máy chủ để đo rò rỉ. Khai kho: 23/23 xanh.",
        "de_xuat": "Khai kho trong `dung_nen_tam()` (một dòng).",
    },
    {
        "so": 11, "bo": "thu_g22_chotcay.py", "nhom": "D. cần cây BẨN",
        "exit": 1, "ran": 11,
        "fails": ["FAIL: test_d2_moi_ban_sao_xanh_tren_cay_co_tep_moi_cua_lan_khac — "
                  "AssertionError: 0 not greater than or equal to 1 : cây SẠCH TRƠN ⇒ phép đo rỗng"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 11,
                   "fails": ["… cùng 1 FAIL: cây SẠCH TRƠN"]},
        "nhan": "S",
        "vi_sao": "Ca đòi `git status` có ≥1 dòng của làn KHÁC để chứng minh cổng không đỏ vì tệp mới "
                  "hợp lệ. Trên cây nghiệm thu SẠCH (0 dòng), phép đo rỗng — đúng như chính nó cảnh "
                  "báo. Đây là tiền điều kiện của phép đo, không phải hành vi sản phẩm. Lượt đo "
                  "chạy TRƯỚC khi tạo 2 tệp của dispatch này; đo lại trên cây có 2 dòng mới: exit 0 · "
                  "Ran 11 · OK — đó chính là bằng chứng nó đo CÂY, không đo sản phẩm.",
        "de_xuat": "Tự tạo tệp mới trong BẢN SAO của phép đo (như test_d3 đã làm với tệp sản phẩm tạm) "
                   "thay vì đòi cây thật bẩn; hoặc skip kèm lý do 'cây sạch — chưa đo được'.",
    },
    {
        "so": 12, "bo": "thu_migrate_dong_thoi.py", "nhom": "F. LỖI THẬT — race `sao_luu()`",
        "exit": 1, "ran": 8,
        "fails": ["FAIL: test_a1_dung_mot_tien_trinh_nang_cap — 8 != 0 : tiến trình hỏng: "
                  "TỪ CHỐI: CHƯA KHAI kho đang chạy (cả 8 tiến trình)",
                  "ERROR: test_a2_csdl_sau_cung_dung_mot_ban — cùng gốc chưa khai"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 8,
                   "fails": ["FAIL: test_a1… — 6–7 != 0 : FileNotFoundError … "
                             "hub-truoc-migrate-…db.dang-ghi / sqlite3.OperationalError: disk I/O "
                             "error (7/8 tiến trình)"]},
        "nhan": "L",
        "vi_sao": "Khai kho chỉ bỏ được lỗi ĐẦU TIÊN; lỗi thật còn lại: 8 tiến trình cùng gọi "
                  "`migrate.chay()` → cả 8 gọi `sao_luu()` TRƯỚC khi lấy khoá `BEGIN IMMEDIATE`; "
                  "tên bản sao chỉ có độ phân giải GIÂY nên cả 8 tính CÙNG một tên + CÙNG tệp "
                  "`.dang-ghi`; một tiến trình `os.replace` xong thì 7 tiến trình còn lại mở tệp "
                  "không còn → FileNotFoundError/disk I/O. Tái hiện 4/4 lượt, traceback đầy đủ ở "
                  "docs/G22_PHAN_LOAI_DO.md §3-F.1.",
        "de_xuat": "Chuyển `sao_luu()` vào TRONG khoá `BEGIN IMMEDIATE` (chỉ một tiến trình sao lưu), "
                   "hoặc đặt tên duy nhất bằng pid/uuid + `O_EXCL` và không dùng chung `.dang-ghi`. "
                   "KHÔNG sửa ở lượt này.",
    },
    {
        "so": 13, "bo": "thu_qa_g17.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 56,
        "fails": ["ERROR: test_a6_khong_co_ket_noi_ra_ngoai — migrate.chay() → sao_luu() → "
                  "TỪ CHỐI: CHƯA KHAI kho đang chạy",
                  "ERROR: test_b0…b9, c1–c8, d1–d7 (25 lỗi) — cùng gốc: `moi_truong()` gọi migrate",
                  "FAIL: test_f7_dot_bien_M4… — driver in ra thông điệp TỪ CHỐI thay vì KETQUA"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 56, "fails": []},
        "nhan": "S",
        "vi_sao": "25 FAIL/ERROR đều đi qua một dòng `migrate.chay()` trong `moi_truong()`. Khai kho: "
                  "56/56 xanh — không có lỗi cách ly tenant nào bị bỏ qua.",
        "de_xuat": "Khai kho trong `moi_truong()` (một dòng).",
    },
    {
        "so": 14, "bo": "thu_qa_g18_tich_hop.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 26,
        "fails": ["FAIL: test_c3_http_mot_tien_trinh_bang_goi_thang_ham — máy chủ cổng 59996 không "
                  "lên được",
                  "FAIL: test_c4_HAI_tien_trinh_thi_tran_KHONG_NHAN — máy chủ cổng 60345 không lên được",
                  "FAIL: test_c5_mot_ket_luan_nhat_quan — 12 != None : HTTP != gọi thẳng hàm"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 26, "fails": []},
        "nhan": "S",
        "vi_sao": "Máy chủ đo không lên vì migrate trong lúc dựng nền bị TỪ CHỐI. Khai kho: 26/26 xanh.",
        "de_xuat": "Khai kho trong môi trường dựng máy chủ của bộ thử.",
    },
    {
        "so": 15, "bo": "thu_qa_g18.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 47,
        "fails": ["ERROR: test_a6_khong_co_luot_ket_noi_ra_ngoai_loopback — migrate.chay() → "
                  "TỪ CHỐI: CHƯA KHAI kho đang chạy",
                  "ERROR: test_e2…e9, f1…f3 (20 lỗi) — cùng gốc `moi_truong()`; FAIL: b1/c2/d1, "
                  "j3…j7 — driver con in thông điệp TỪ CHỐI"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 47, "fails": []},
        "nhan": "S",
        "vi_sao": "20 FAIL/ERROR đều có cùng một dòng migrate trong `moi_truong()` hoặc trong driver "
                  "con. Khai kho: 47/47 xanh — không còn lỗi E2E nào khác trong môi trường này.",
        "de_xuat": "Khai kho trong `moi_truong()` và các driver con (một dòng, kế thừa env).",
    },
    {
        "so": 16, "bo": "thu_qa_g19_tich_hop.py", "nhom": "A. migrate fail-closed",
        "exit": 1, "ran": 8,
        "fails": ["mã thoát bộ gốc = 1 · TỰ KIỂM KHUÔN: 8 ca · PHÁN QUYẾT CỔNG: ĐỎ — runner HỎNG "
                  "(thu_g19_tich_hop → migrate.py hỏng: TỪ CHỐI: CHƯA KHAI kho)"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 0, "ran": 8, "fails": []},
        "nhan": "S",
        "vi_sao": "Bản uỷ quyền chuyển NGUYÊN VĂN mã thoát của bộ gốc; bộ gốc đỏ vì migrate chưa khai "
                  "kho. Khai kho: 8/8 xanh.",
        "de_xuat": "Khai kho (một dòng) — không sửa bản uỷ quyền.",
    },
    {
        "so": 17, "bo": "thu_qa_soat.py", "nhom": "B. API/tham số mới",
        "exit": 1, "ran": 30,
        "fails": ["FAIL: test_q09f_ANTOAN_tenant_id_trong_body_khong_doi_duoc_ngu_canh — "
                  "AssertionError: 400 != 200 (GET /api/v2/don?tenant_id=…)"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 30,
                   "fails": ["FAIL: test_q09f… — 400 != 200"]},
        "nhan": "S",
        "vi_sao": "Ca kiểm đúng bất biến (tenant_id trong body/query không đổi ngữ cảnh) nhưng dòng "
                  "cuối đòi máy chủ trả 200. Lớp truy vấn G22 TỪ CHỐI tham số `tenant_id` lạ bằng 400 "
                  "— an toàn hơn, không kém.",
        "de_xuat": "Nhận `(200 với danh sách không lộ B, hoặc 400)` là ĐẠT; giữ nguyên vế POST/body.",
    },
    {
        "so": 18, "bo": "thu_qa_g22.py", "nhom": "E. nền/gộp — KHÔNG đo được vế E2E",
        "exit": 1, "ran": 24,
        "fails": ["FAIL: test_b2_chay_e2e_toan_bo_that — chay.sh rc=1 (3 đạt, 10 hỏng, 52 không chạy)",
                  "FAIL: test_b3_e2e_tam_ca_ban_phim_chay_that — 0 ca ĐẠT: Executable doesn't exist: "
                  "… chromium_headless_shell-1194/…/headless_shell"],
        "che_do": True,
        "gop": {"nhan": "VIP_G22_CHE_DO=gop", "exit": 1, "ran": 24,
                "fails": ["FAIL: test_b2_chay_e2e_toan_bo_that — chay.sh rc=1",
                          "FAIL: test_b3_e2e_tam_ca_ban_phim_chay_that — thiếu chromium-1194"]},
        "nhan": "C",
        "vi_sao": "Đây là bộ DUY NHẤT trong 21 bộ đỏ có `VIP_G22_CHE_DO`; nhưng cả HAI chế độ đều đỏ "
                  "vì cùng một lý do MÔI TRƯỜNG: bản playwright trong repo đòi "
                  "`chromium_headless_shell-1194`, máy này chỉ có 1148/1243. Vế quyết định của giả "
                  "thuyết (gộp XANH) KHÔNG đo được trong sandbox này ⇒ (C), không phải (N).",
        "de_xuat": "Cài đúng chromium-1194 (hoặc ghim phiên bản bản playwright có sẵn) rồi chạy lại "
                   "`VIP_G22_CHE_DO=gop`; nếu vẫn đỏ thì mới kết luận được N/S/L.",
    },
    {
        "so": 19, "bo": "thu_bien_driver.py", "nhom": "F. LỖI THẬT — biên driver",
        "exit": 1, "ran": 0,
        "fails": ["AssertionError: tệp nạp trực tiếp sqlite3 (phải dùng csdl.Row/LoiToanVen/ket_noi): "
                  "migrate.py dòng [26]"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 0,
                   "fails": ["AssertionError: … migrate.py dòng [26]"]},
        "nhan": "L",
        "vi_sao": "`migrate.py` nạp thẳng `sqlite3` từ commit bf8696d (G22 S8/do2b). Biên driver "
                  "được ghim từ 15/10: chỉ `csdl.py` được nạp driver; bộ thử bắt đúng chỗ nợ kiến "
                  "trúc mọc lại. Đây là vi phạm THẬT (mức kiến trúc), không phải bộ đo cũ.",
        "de_xuat": "Đưa bốn chỗ dùng driver của migrate.py (`connect` chỉ-đọc, `OperationalError`, "
                   "`DatabaseError`, `complete_statement`) vào csdl.py; hoặc khai ngoại lệ có lý do "
                   "và cập nhật danh sách CHO PHÉP của bộ thử. KHÔNG sửa ở lượt này.",
    },
    {
        "so": 20, "bo": "thu_g22_gioihan.py", "nhom": "D. kỳ vọng C5 còn 1 ứng viên",
        "exit": 1, "ran": 32,
        "fails": ["✗ B3.a_bo_goc_tra_ma_khac_0 — C5 vẫn 1/2 · phán quyết=DONG (tiêm vào 1 ứng viên)",
                  "✗ B3.b_bo_goc_khong_ton_tai · ✗ B3.c_suite_rong_0_ca — cùng 1/2 DONG",
                  "✗ B5.thu_g19_tich_hop · ✗ B5.thu_qa_g19_tich_hop — 8 ca · thoát 1 (thiếu khai kho)"],
        "do_lai": {"nhan": "VIP_KHO_DANG_CHAY=sqlite", "exit": 1, "ran": 32,
                   "fails": ["✗ B3.a/b/c — C5 vẫn 1/2 · phán quyết=DONG"]},
        "nhan": "S",
        "vi_sao": "B3 giả định C5 chỉ có MỘT ứng viên nên tiêm lỗi vào ứng viên đó là cổng phải đỏ. "
                  "Nay `thu_qa_g19*.py` khớp HAI tệp và cả hai đều chạy thật: tiêm vào "
                  "`thu_qa_g19_tich_hop.py` còn `thu_qa_g19.py` xanh ⇒ C5 = 1/2 · DONG. Kỳ vọng cũ, "
                  "không phải cổng hỏng.",
        "de_xuat": "B3 vô hiệu hoá CẢ HAI ứng viên (hoặc chạy trên bản sao chỉ còn 1 ứng viên); ghi "
                   "rõ C5 yêu cầu 'ít nhất 1 ứng viên chạy thật', không phải 'mọi ứng viên'.",
    },
]

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. TỰ KIỂM — đối chứng tiêm lỗi thật trên BẢN SAO
# ══════════════════════════════════════════════════════════════════════════════════════════════
# Câu SQL của `_cong_bo_dem_co_tran`. Đây là bản SAO của chuỗi; nếu tệp thật đổi, phép tiêm
# phải HỎNG to (assert đếm == 1) chứ không được lặng lẽ tiêm vào chỗ khác — §12.1 luật 5.
THAN_CU = (
    '    thang = csdl.thang_nay()\n'
    '    with csdl.khoa_ghi:\n'
    '        kn = csdl.mo()\n'
    '        kn.execute("INSERT OR IGNORE INTO usage_thang (tenant_id, thang) VALUES (?,?)",\n'
    '                   (tenant_id, thang))\n'
    '        cur = kn.execute(\n'
    '            f"UPDATE usage_thang SET {cot}={cot}+1"\n'
    '            f" WHERE tenant_id=? AND thang=? AND {cot}+1 <= ?", (tenant_id, thang, tran))\n'
    '        duoc = cur.rowcount == 1\n'
    '    return duoc'
)
THAN_TIEM = '    return True  # TIÊM LỖI (bản sao): bỏ chốt trần, luôn cho qua'


def _bam_cay(goc_ban_sao):
    """Băm từng tệp nguồn của bản sao (app/*.py + bộ thử). Dùng để chứng minh chỉ 1 tệp đổi."""
    ra = {}
    for ten in sorted(os.listdir(os.path.join(goc_ban_sao, "app"))):
        p = os.path.join(goc_ban_sao, "app", ten)
        if os.path.isfile(p) and ten.endswith(".py"):
            with open(p, "rb") as f:
                ra["app/" + ten] = hashlib.sha256(f.read()).hexdigest()
    p = os.path.join(goc_ban_sao, "app", "thu", BO_TU_KIEM)
    with open(p, "rb") as f:
        ra["app/thu/" + BO_TU_KIEM] = hashlib.sha256(f.read()).hexdigest()
    return ra


def _chep_ban_sao(dich):
    """Sao TỐI THIỂU: app/*.py + đúng một bộ thử. Không chép dữ liệu, docs, .git."""
    os.makedirs(os.path.join(dich, "app", "thu"))
    for ten in os.listdir(APP):
        p = os.path.join(APP, ten)
        if os.path.isfile(p) and ten.endswith(".py"):
            shutil.copy2(p, os.path.join(dich, "app", ten))
    shutil.copy2(os.path.join(GOC, BO_TU_KIEM), os.path.join(dich, "app", "thu", BO_TU_KIEM))


def _tiem_loi(dich):
    p = os.path.join(dich, "app", TEP_TIEM)
    with open(p, encoding="utf-8") as f:
        nguon = f.read()
    assert nguon.count(THAN_CU) == 1, (
        "khuôn tiêm phải xuất hiện ĐÚNG MỘT lần trong %s, thấy %d — bộ thử đã trôi"
        % (TEP_TIEM, nguon.count(THAN_CU)))
    with open(p, "w", encoding="utf-8") as f:
        f.write(nguon.replace(THAN_CU, THAN_TIEM))


def _chay_bo_thu(ban_sao, env_them=None):
    """Chạy bộ thử tự kiểm trên bản sao. Trả exit · ran · fails · output."""
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("VIP_") and not k.startswith("GIT_CONFIG_")
           and k not in ("PYTHONPATH", "PYTHONHOME")}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.update(env_them or {})
    p = subprocess.run([sys.executable, "-u", "app/thu/" + BO_TU_KIEM],
                       cwd=ban_sao, env=env, capture_output=True, text=True, timeout=180)
    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"Ran (\d+) tests?", out)
    ran = int(m.group(1)) if m else 0
    fails = []
    for doan in re.split(r"\n={20,}\n", out):
        if re.search(r"^(FAIL|ERROR): ", doan, re.M):
            fails.append(doan.strip()[:1000])
    if not fails:
        fails = [out.strip()[-1500:]]        # migrate từ chối TRƯỚC unittest: không có dòng FAIL
    return {"exit": p.returncode, "ran": ran, "fails": fails, "out": out}


class TuKiem(unittest.TestCase):
    """Bốn nhãn đều có đối chứng; (S) và (L) có đối chứng TIÊM LỖI THẬT trên bản sao."""

    @classmethod
    def setUpClass(cls):
        cls.goc_tam = tempfile.mkdtemp(prefix="g22-phanloai-")
        cls.ban_sach = os.path.join(cls.goc_tam, "sach")
        cls.ban_tiem = os.path.join(cls.goc_tam, "tiem")
        _chep_ban_sao(cls.ban_sach)
        _chep_ban_sao(cls.ban_tiem)
        cls.bam_truoc = _bam_cay(cls.ban_tiem)
        # 1) Bản sạch, KHÔNG khai kho → ĐỎ vì migrate fail-closed.
        cls.kq_mac_dinh = _chay_bo_thu(cls.ban_sach, {})
        # 2) Cùng bản sạch, khai kho → XANH: đối chứng "chỉ thiếu thiết lập".
        cls.kq_khai = _chay_bo_thu(cls.ban_sach, {"VIP_KHO_DANG_CHAY": "sqlite"})
        # 3) Bản TIÊM LỖI THẬT (cùng thiết lập) → ĐỎ: chỉ khác byte sản phẩm.
        _tiem_loi(cls.ban_tiem)
        cls.kq_tiem = _chay_bo_thu(cls.ban_tiem, {"VIP_KHO_DANG_CHAY": "sqlite"})
        cls.bam_sau = _bam_cay(cls.ban_tiem)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.goc_tam, ignore_errors=True)

    def test_01_bang_20_bo_tu_nhat_quan_voi_chan_doan(self):
        lech = [(r["bo"], r["nhan"], chan_doan(r)) for r in BANG if chan_doan(r) != r["nhan"]]
        self.assertEqual(lech, [], "nhãn trong bảng KHÔNG khớp bằng chứng: %s" % (lech,))
        self.assertEqual(len(BANG), 20)

    def test_02_khong_bo_nao_trong_17_bo_ten_co_che_do_nen_gop(self):
        """17 bộ đề bài nêu tên KHÔNG có công tắc nền/gộp — nên (N) không thể có trong nhóm đó.

        Trong 20 bộ, chỉ `thu_qa_g22.py` có công tắc RIÊNG (`VIP_G22_CHE_DO`); nó được xếp (C)
        vì cả hai chế độ đều đỏ do thiếu trình duyệt. `thu_g22_gioihan.py` chỉ CHUYỀN
        `VIP_G20_CHE_DO` cho tiến trình con, không có chế độ riêng.
        """
        ten_17 = {r["bo"] for r in BANG if r["so"] <= 17}
        for bo in sorted(ten_17):
            with open(os.path.join(GOC, bo), encoding="utf-8") as f:
                nguon = f.read()
            self.assertEqual(re.findall(r"VIP_[A-Z0-9_]*CHE_DO", nguon), [],
                             "%s có biến nền/gộp — phải đo lại nhãn (N)" % bo)
        # Công tắc RIÊNG của chính bộ (khớp số G trong tên tệp).
        co_rieng = {}
        for r in BANG:
            m = re.search(r"thu_(?:qa_)?g(\d+)", r["bo"])
            if not m:
                continue
            with open(os.path.join(GOC, r["bo"]), encoding="utf-8") as f:
                nguon = f.read()
            bien = sorted(set(re.findall(r"VIP_G%s_CHE_DO" % m.group(1), nguon)))
            if bien:
                co_rieng[r["bo"]] = bien
        self.assertEqual(co_rieng, {"thu_qa_g22.py": ["VIP_G22_CHE_DO"]},
                         "bộ có công tắc nền/gộp riêng đã đổi: %s" % (co_rieng,))
        # Ba bộ QA của G20/G21/G22 thật sự có công tắc — đây mới là "bộ đo nền" theo nghĩa repo.
        for bo, bien in (("thu_qa_g20.py", "VIP_G20_CHE_DO"),
                         ("thu_qa_g21.py", "VIP_G21_CHE_DO"),
                         ("thu_qa_g22.py", "VIP_G22_CHE_DO")):
            with open(os.path.join(GOC, bo), encoding="utf-8") as f:
                nguon = f.read()
            self.assertIn(bien, nguon, "%s mất công tắc %s" % (bo, bien))

    def test_03_ban_sao_sach_do_vi_thieu_khai_va_duoc_xep_S(self):
        truoc = _bam_cay(self.ban_sach)
        self.assertNotEqual(self.kq_mac_dinh["exit"], 0, "bản sạch KHÔNG đỏ — phép đo mất răng")
        self.assertIn("TỪ CHỐI: CHƯA KHAI kho đang chạy", self.kq_mac_dinh["out"],
                      "đỏ không phải vì cổng khai kho: %s" % self.kq_mac_dinh["out"][-800:])
        self.assertEqual(self.kq_khai["exit"], 0,
                         "khai kho KHÔNG làm bản sạch xanh: %s" % self.kq_khai["out"][-1200:])
        self.assertEqual(self.kq_khai["ran"], 5)
        self.assertEqual(_bam_cay(self.ban_sach), truoc, "lượt chạy đã SỬA bản sao")
        ban_ghi = {
            "exit": self.kq_mac_dinh["exit"], "ran": self.kq_mac_dinh["ran"],
            "fails": self.kq_mac_dinh["fails"],
            "do_lai": {"exit": self.kq_khai["exit"], "ran": self.kq_khai["ran"], "fails": []},
        }
        self.assertEqual(chan_doan(ban_ghi), "S")
        print("    [S] bản sạch: exit=%d · %d ca · %s" %
              (self.kq_mac_dinh["exit"], self.kq_mac_dinh["ran"],
               "TỪ CHỐI: CHƯA KHAI kho đang chạy"))
        print("        khai kho : exit=%d · %d ca (đối chứng đường) ⇒ (S): thiếu THIẾT LẬP, "
              "không phải lỗi sản phẩm" % (self.kq_khai["exit"], self.kq_khai["ran"]))

    def test_04_tiem_loi_vao_ban_sao_duoc_xep_L(self):
        da_doi = sorted(k for k in self.bam_truoc if self.bam_truoc[k] != self.bam_sau.get(k))
        self.assertEqual(da_doi, ["app/billing.py"],
                         "phép tiêm phải đổi ĐÚNG MỘT tệp sản phẩm, thấy %s" % (da_doi,))
        self.assertNotEqual(self.kq_tiem["exit"], 0,
                            "bản bị tiêm KHÔNG đỏ — bộ thử KHÔNG bắt được lỗi thật")
        self.assertIn("FAIL: test_a1_so_don_nguyen_tu", self.kq_tiem["out"],
                      "bộ thử đỏ vì lý do khác, không phải lỗi hạn mức: %s"
                      % self.kq_tiem["out"][-1200:])
        ban_ghi = {
            "exit": self.kq_tiem["exit"], "ran": self.kq_tiem["ran"],
            "fails": self.kq_tiem["fails"], "san_pham_doi": True,
            "doi_chung": {"exit": self.kq_khai["exit"]},
            "do_lai": {"exit": self.kq_tiem["exit"], "ran": self.kq_tiem["ran"],
                       "fails": self.kq_tiem["fails"]},
        }
        self.assertEqual(chan_doan(ban_ghi), "L")
        print("    [L] bản tiêm: exit=%d · %d ca · tệp sản phẩm đổi: %s" %
              (self.kq_tiem["exit"], self.kq_tiem["ran"], da_doi))
        print("        đối chứng sạch (cùng thiết lập): exit=%d ⇒ lỗi do SẢN PHẨM, không do "
              "thiết lập ⇒ (L)" % self.kq_khai["exit"])

    def test_05_bon_nhan_deu_co_doi_chung(self):
        """(N) và (C) không có trong 20, nhưng luật phải phân biệt được — nếu không là luật rỗng."""
        n = {"exit": 1, "fails": ["bất kỳ"], "che_do": True,
             "gop": {"exit": 0, "ran": 29}, "san_pham_doi": False}
        c = {"exit": 1, "fails": ["AssertionError: một hiện tượng chưa phân loại"], "san_pham_doi": False}
        self.assertEqual(chan_doan(n), "N")
        self.assertEqual(chan_doan(c), "C")

    def test_06_bang_tong_hop_N_S_L_C(self):
        dem = {"N": 0, "S": 0, "L": 0, "C": 0}
        for r in BANG:
            dem[r["nhan"]] += 1
        self.assertEqual(dem, {"N": 0, "S": 17, "L": 2, "C": 1},
                         "tổng hợp lệch: %s" % (dem,))
        self.assertEqual(sum(dem.values()), 20)
        self.assertEqual(sorted(r["bo"] for r in BANG if r["nhan"] == "L"),
                         ["thu_bien_driver.py", "thu_migrate_dong_thoi.py"])


def _in_bang():
    print("=" * 100)
    print("G22 — PHÂN LOẠI 20 BỘ ĐỎ (mặc định → chế độ thay thế)")
    print("=" * 100)
    print("%-3s %-28s %-14s %-16s %-4s %s" %
          ("#", "Bộ", "Mặc định", "Chạy lại", "Nhãn", "Nguyên nhân"))
    for r in BANG:
        md = "exit=%d · %d ca" % (r["exit"], r["ran"])
        dl = r.get("do_lai")
        if dl:
            dls = "exit=%d · %d ca" % (dl["exit"], dl["ran"])
        elif r.get("gop"):
            dls = "gộp: exit=%d" % r["gop"]["exit"]
        else:
            dls = "—"
        print("%-3d %-28s %-14s %-16s %-4s %s" % (r["so"], r["bo"], md, dls, r["nhan"], r["nhom"]))
    dem = {"N": 0, "S": 0, "L": 0, "C": 0}
    for r in BANG:
        dem[r["nhan"]] += 1
    print("-" * 100)
    print("TỔNG: N=%d · S=%d · L=%d · C=%d · tổng=%d"
          % (dem["N"], dem["S"], dem["L"], dem["C"], len(BANG)))
    print("=" * 100)


if __name__ == "__main__":
    if "--chi-bang" in sys.argv:
        _in_bang()
        sys.exit(0)
    _in_bang()
    argv = [a for a in sys.argv if a != "--chi-bang"]
    unittest.main(argv=argv, verbosity=2 if "-v" in argv else 1)
