#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G21 / AG-02 — CHẠY LẠI **TOÀN BỘ** BẰNG CHỨNG CỦA LƯỢT NÀY BẰNG MỘT LỆNH.

    python3 trien_khai/g20-saoluu/chay_do.py            # chạy hết, in bảng
    python3 trien_khai/g20-saoluu/chay_do.py --nhanh    # bỏ mọi bước cần PostgreSQL

Mỗi bước ghi lại BA thứ, không thiếu thứ nào: **LỆNH THẬT**, **MÃ THOÁT THẬT**, và **SỐ CA**
(nếu bước đó có ca). Kết quả thô để ở `trien_khai/g20-saoluu/ket_qua/`.

====== VÌ SAO PHẢI CÓ BƯỚC "TRƯỚC" CHẠY LẠI, CHỨ KHÔNG CHỈ ĐỌC LẠI SỐ CŨ ======
Lượt trước bản vá chỉ nằm trong thư mục tạm. Lượt này nó đã nằm trong `app/migrate.py`, nên
không còn cách nào đo "TRƯỚC" trên cây thật. Bước `B2` vì thế chạy trên bản ĐÓNG BĂNG
(`ban_va.MIGRATE_NGUYENBAN`, md5 đã ghim) — và cặp `B2`/`B3` chỉ có nghĩa khi cả hai chạy
CÙNG một bộ đo, cùng tiêu chí, trong cùng một lượt. Đó là lý do phải chạy lại, không đọc lại.

====== G22 — HAI BƯỚC ĐỔI NGHĨA, VÀ VÌ SAO ======
  * `B4` nay có thêm `D5`: nới lại CHÍNH SÁCH CŨ (chưa khai ⇒ coi kho là SQLite) và đòi `S8` bắt
    được. Bước `B5` cũ (đo biến thể `chinh_sach_tu_choi`) bị BỎ cùng biến thể đó — quyết định ấy
    nay là mặc định của tệp thật, nên vế cần chứng minh là vế NGƯỢC LẠI.
  * `B5` nay là CA E3 CHẠY RIÊNG (ba lượt), và `B7` là CA E3 CHẠY CHUNG (trong cả bộ thử AG-04).
    Hai bước này trả lời trực tiếp VIỆC 2: cùng một ca, chạy riêng và chạy chung, phải cho CÙNG
    kết quả. Số dùng để so được ĐỌC TỪ LOG (`_doc_e3`), không chép tay.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

DAY = os.path.dirname(os.path.abspath(__file__))
GOC = os.path.dirname(os.path.dirname(DAY))
sys.path.insert(0, DAY)

import ban_va     # noqa: E402

PY = sys.executable or "python3"
KQ = os.path.join(DAY, "ket_qua")
NHANH = "--nhanh" in sys.argv[1:]
BUOC = []


def _ghi(ten, lenh, rc, ghi_chu, so_ca=None, so_skip=None, tep=None):
    d = {"buoc": ten, "lenh": lenh, "rc": rc, "ghi_chu": ghi_chu,
         "so_ca": so_ca, "so_skip": so_skip, "tep": tep}
    BUOC.append(d)
    print("[%s] rc=%-3s %s" % (ten, rc, ghi_chu))
    return d


def _chay(ten, lenh, env_them=None, ghi_chu="", dem_ca=False):
    env = dict(os.environ)
    env.update(env_them or {})
    p = subprocess.run(lenh, cwd=GOC, env=env, capture_output=True, text=True)
    so_ca = so_skip = None
    if dem_ca:
        import re
        m = re.search(r"Ran (\d+) tests?", p.stderr + p.stdout)
        so_ca = int(m.group(1)) if m else None
        m = re.search(r"skipped=(\d+)", p.stderr + p.stdout)
        # `unittest` CHỈ in `skipped=N` khi N > 0. Vắng nó nghĩa là 0 skip, KHÔNG phải "không
        # đọc được" — để `None` ở đây là tự tạo ra một chỗ trống trong bảng bằng chứng.
        so_skip = int(m.group(1)) if m else 0
    _ghi(ten, " ".join(lenh), p.returncode, ghi_chu or (p.stdout + p.stderr).strip()[-200:],
         so_ca, so_skip)
    return p


def _doc_e3(text):
    """Số của ca E3 ĐỌC RA TỪ LOG, không chép tay: `1 lượt → N bản cất · 3 lượt cùng giây → M`.

    Vì sao đọc từ log: đây là hai con số mà kết luận VIỆC 2 dựa vào, và chép tay chúng vào bảng
    là tự tạo ra một chỗ để sai mà không ai thấy.
    """
    import re
    ra = {}
    m = re.search(r"1 lượt khôi phục → (\d+) bản cất · 3 lượt cùng giây → (\d+) bản cất", text)
    if m:
        ra["ban_cat_sau_1_lan"] = int(m.group(1))
        ra["ban_cat_sau_3_lan"] = int(m.group(2))
    return ra


def _ket_luan_json(duong, nhan):
    """Đọc JSON của `fail_closed.py`, trả `(so_FAIL_CLOSED, so_ca, so_skip, danh_sach_ma_xanh)`."""
    import fail_closed as fc
    kq = json.load(open(duong, encoding="utf-8"))
    xanh, do = [], []
    for ma in kq["thu_tu"]:
        (xanh if not fc.phan_quyet(kq["ban_ghi"][ma]) else do).append(ma)
    print("      %s: %d/%d FAIL_CLOSED · còn ĐỎ: %s · bỏ qua: %s"
          % (nhan, len(xanh), len(kq["thu_tu"]), do or "(không)", kq["bo_qua"] or "(không)"))
    return xanh, len(kq["thu_tu"]), len(kq["bo_qua"]), do, kq


def main():
    os.makedirs(KQ, exist_ok=True)
    nen = tempfile.mkdtemp(prefix="g21-chaydo-")
    try:
        # ------------------------------------------------------------------ B0
        tep_doi = ["app/migrate.py", "app/cau_hinh.py", "app/thu/thu_g21_saoluu.py",
                   "app/thu/thu_g22_saoluu.py", "trien_khai/g20-saoluu/ban_va.py",
                   "trien_khai/g20-saoluu/fail_closed.py", "trien_khai/g20-saoluu/do_postgres.py",
                   "trien_khai/g20-saoluu/kich_ban.py", "trien_khai/g20-saoluu/chay_do.py"]
        ma = ("import ast,sys\n"
              "for t in %r: ast.parse(open(t, encoding='utf-8').read()); print('OK', t)\n"
              % tep_doi)
        p = subprocess.run([PY, "-c", ma], cwd=GOC, capture_output=True, text=True)
        _ghi("B0", "python3 -c ast.parse(6 tệp)", p.returncode,
             "cú pháp %d tệp" % len(tep_doi), so_ca=len(tep_doi), so_skip=0)

        # ------------------------------------------------------------------ B1
        p = _chay("B1", [PY, "trien_khai/g20-saoluu/ban_va.py"],
                  ghi_chu="tự xác nhận bản vá ĐÃ ÁP đủ mảnh + mốc tiêm còn nguyên")
        tt = json.loads(p.stdout) if p.returncode == 0 else {}
        print("      migrate.py THẬT: %s dòng · sha256[:16]=%s"
              % (tt.get("migrate_that", {}).get("so_dong"),
                 tt.get("migrate_that", {}).get("sha256_16")))
        print("      bản ĐÓNG BĂNG   : %s dòng · sha256[:16]=%s"
              % (tt.get("migrate_nguyenban", {}).get("so_dong"),
                 tt.get("migrate_nguyenban", {}).get("sha256_16")))

        # ---- dựng các `app/` ứng viên: goc · ban_va (= tệp THẬT) · tiem_d1..d4 · chính sách
        bt = ban_va.dung_bien_the(nen)
        print("      biến thể: %s" % sorted(bt))

        # ------------------------------------------------------------------ B2/B3
        for ten, nhan, app_dir, ten_json in (
                ("B2", "goc", bt["goc"], "truoc.json"),
                ("B3", "ban_va", bt["ban_va"], "sau.json")):
            bo = ["S8"] if NHANH else []
            l = [PY, "trien_khai/g20-saoluu/fail_closed.py", "--json", os.path.join(KQ, ten_json)]
            l += ["--nhanh"] if NHANH else []
            p = _chay(ten, l, {"G21_APP_DIR": app_dir},
                      ghi_chu="10 kịch bản trên %s (%s)" % (nhan, app_dir))
            xanh, n, skip, do, _ = _ket_luan_json(os.path.join(KQ, ten_json), ten + "/" + nhan)
            BUOC[-1].update({"so_ca": n, "so_skip": skip, "so_fail_closed": len(xanh),
                             "con_do": do, "bien_the": nhan,
                             "bien_the_duong": app_dir})

        # ------------------------------------------------------------------ B4
        # ĐỐI CHỨNG ÂM BẮT BUỘC: gỡ ĐÚNG MỘT chốt khỏi TỆP THẬT ⇒ bộ đo PHẢI đỏ ở ĐÚNG kịch bản.
        # G22 thêm `D5` — nới lại CHÍNH SÁCH CŨ (chưa khai ⇒ coi là SQLite): `S8` PHẢI bắt được.
        # Đây là vế thay cho bước `B5` cũ (đo biến thể `chinh_sach_tu_choi`): quyết định đó nay là
        # MẶC ĐỊNH của tệp thật, nên thứ cần chứng minh không còn là "nó đóng được S8" mà là
        # "nới nó ra thì S8 ĐỎ" — mạnh hơn, vì nó chứng minh bộ đo PHÂN BIỆT ĐƯỢC.
        for nhan in ("D1", "D2", "D3", "D4", "D5"):
            import fail_closed as _fc
            nhan_day_du = ban_va.phai_bat(nhan)
            phai = nhan_day_du.replace("PHẢI bị ", "").replace(" bắt", "")
            chi = tuple(x.strip() for x in phai.split("và"))
            # CHỐT CHỐNG NHÃN KHÔNG PHÂN TÍCH ĐƯỢC. Đo được ngay lượt chạy đầu của G22: nhãn
            # `"PHẢI bị S8 bắt (vế do2b và do1b)"` tách ra thành hai MÃ KHÔNG TỒN TẠI, bộ đo lọc
            # còn 0 ca, và bước đó báo "KHÔNG bắt được phép tiêm" — một ĐỎ vì phép đo rỗng, không
            # phải vì sản phẩm. Ném ra ở đây thì lượt chạy DỪNG ngay tại chỗ hỏng, thay vì để
            # người đọc đi tìm một phép tiêm trượt.
            if not chi or any(c not in _fc.THU_TU for c in chi):
                raise AssertionError(
                    "NHÃN TIÊM KHÔNG PHÂN TÍCH ĐƯỢC (%s): %r → %r. Nhãn phải có dạng "
                    "'PHẢI bị <MÃ> [và <MÃ>] bắt'; mọi chữ thêm vào sẽ bị đọc thành mã kịch bản."
                    % (nhan, nhan_day_du, list(chi)))
            ten = "B4." + nhan
            # `fail_closed.py` không có tham số "chỉ chạy mã này" ở dòng lệnh — dùng tiến trình
            # con gọi thẳng `chay_tat_ca(chi=...)` để vẫn chạy ĐÚNG bộ đo, không viết lại phép đo.
            duong_json = os.path.join(KQ, "tiem_%s.json" % nhan.lower())
            ma = ("import os,sys,json\n"
                  "os.environ['G21_APP_DIR']=%r\n"
                  "sys.path.insert(0, %r)\n"
                  "import fail_closed as fc\n"
                  "kq=fc.chay_tat_ca(chi=tuple(%r))\n"
                  "json.dump(kq, open(%r,'w'), ensure_ascii=False, indent=1, default=str)\n"
                  % (bt["tiem_" + nhan.lower()], DAY, list(chi), duong_json))
            p = _chay(ten, [PY, "-c", ma], {},
                      ghi_chu="tiêm %s ⇒ %s PHẢI đỏ" % (nhan, phai))
            xanh, n, skip, do, _ = _ket_luan_json(duong_json, ten)
            dat = all(m in do for m in chi)
            BUOC[-1].update({"so_ca": n, "so_skip": skip, "phai_bat": list(chi),
                             "da_bat": [m for m in chi if m in do], "dat": dat,
                             "bien_the_duong": bt["tiem_" + nhan.lower()]})
            if not dat:
                print("      *** ĐỐI CHỨNG ÂM HỎNG: %s KHÔNG bắt được phép tiêm %s ***"
                      % (chi, nhan))

        # ------------------------------------------------------------------ B5
        # G22 / VIỆC 2 — CA E3 PHỤ THUỘC ĐỒNG HỒ: CHẠY RIÊNG vs CHẠY CHUNG.
        # Bước `B5` cũ (đo biến thể `chinh_sach_tu_choi`) đã bị bỏ cùng với biến thể đó — vế thay
        # thế của nó là `B4.D5`. Chỗ này nay đo ĐÚNG câu hỏi của VIỆC 2: ca `E3` (ba lượt khôi
        # phục cùng một mốc) phải cho CÙNG kết quả khi chạy RIÊNG và khi chạy CHUNG.
        #   * RIÊNG  — `python3 app/thu/thu_g20_saoluu.py E_KhoiPhucDeLenCsdlDangChay`, ba lượt;
        #   * CHUNG  — cả tệp (`B7`), và số của `E3` được ĐỌC RA TỪ CHÍNH LOG ĐÓ, không chép tay.
        # KHÔNG retry: chạy lại cho tới khi XANH là che mất đúng thứ ca này sinh ra để đo. Ba lượt
        # ở đây là ba lượt ĐỘC LẬP CÓ CHỦ Ý (đo tính tất định), không phải ba lần thử lại.
        for lan in (1, 2, 3):
            p = _chay("B5.E3-rieng-%d" % lan,
                      [PY, "app/thu/thu_g20_saoluu.py", "E_KhoiPhucDeLenCsdlDangChay"],
                      ghi_chu="E3 chạy RIÊNG, lượt %d" % lan, dem_ca=True)
            BUOC[-1].update(_doc_e3(p.stdout + p.stderr))
            if p.returncode != 0:
                print("      *** E3 CHẠY RIÊNG ĐỎ (lượt %d) — ca phụ thuộc gì đó ngoài đầu vào ***"
                      % lan)

        # ------------------------------------------------------------------ B6
        l = [PY, "app/thu/thu_g21_saoluu.py"]
        p = _chay("B6", l, ghi_chu="bộ thử fail-closed (vào lượt hồi quy chung)", dem_ca=True)

        # ------------------------------------------------------------------ B7
        # BỘ THỬ CỦA AG-04 (G20) — TỆP AG-02 KHÔNG ĐƯỢC SỬA, nhưng PHẢI ĐO: nó là bộ thử mà
        # tài liệu G20 trích con số "41 ca OK".
        # G22: ca `test_k4` của nó PIN khoảng hở `do2b` — và khoảng hở đó đã đóng, nên lượt này
        # `B7` phải là **41/41 · rc 0**. Đó cũng là vế CHẠY CHUNG của ca `E3` (số của `E3` được
        # đọc từ chính log này). Trước G22 nó ĐỎ đúng một ca, và lý do được ghi ở đây.
        p = _chay("B7", [PY, "app/thu/thu_g20_saoluu.py"],
                  ghi_chu="bộ thử AG-04 (G20) trên tệp ĐÃ VÁ — CHẠY CHUNG", dem_ca=True)
        BUOC[-1].update(_doc_e3(p.stdout + p.stderr))

        # ------------------------------------------------------------------ B9
        # BỘ THỬ G22 (mới): hai bất biến của lượt này — kho đang chạy phải KHAI (chưa khai ⇒ TỪ
        # CHỐI) và MỐC THỜI GIAN phải là ĐẦU VÀO (tên bản cất mang mốc đã truyền, không mang giờ
        # hệ thống). Tệp này do AG-02 viết, nên nó được phép đỏ ⇒ nó PHẢI rc 0.
        p = _chay("B9", [PY, "app/thu/thu_g22_saoluu.py"],
                  ghi_chu="bộ thử G22 (kho đang chạy + đồng hồ là đầu vào)", dem_ca=True)

        # ------------------------------------------------------------------ B8
        # BẢNG SỐ DÒNG + TỔNG TIỀN TỪNG BẢNG, sinh THẲNG từ JSON số đo — không chép tay.
        for nhan, ten_json in (("TRƯỚC", "truoc.json"), ("SAU", "sau.json")):
            ra_md = os.path.join(KQ, "bang_tung_bang_%s.md" % nhan.lower())
            p = _chay("B8." + nhan,
                      [PY, "trien_khai/g20-saoluu/bang_tung_bang.py",
                       os.path.join(KQ, ten_json), "--md", ra_md],
                      ghi_chu="bảng từng bảng (%s) → %s" % (nhan, os.path.basename(ra_md)))

        # ------------------------------------------------------------------ kết
        with open(os.path.join(KQ, "chay_do.json"), "w", encoding="utf-8") as f:
            json.dump(BUOC, f, ensure_ascii=False, indent=1)
        print("\n" + "=" * 100)
        print("%-7s %-6s %-6s %-6s %s" % ("BƯỚC", "RC", "SỐ CA", "SKIP", "GHI CHÚ"))
        for d in BUOC:
            print("%-7s %-6s %-6s %-6s %s" % (d["buoc"], d["rc"], d["so_ca"], d["so_skip"],
                                              d["ghi_chu"][:58]))
        print("=" * 100)
        # `rc` của B2/B3/B4 KHÔNG phải "phải bằng 0": cả ba đều chạy những kịch bản HỎNG mà
        # mã thoát ĐẠT của chúng là "bộ đo KẾT LUẬN ĐỎ" ⇒ rc 1 là KẾT QUẢ ĐÚNG. B0, B1, B6, B7,
        # B9 là các BỘ THỬ (mọi khẳng định đã viết thành `assert`) nên phải rc 0; B5.E3 cũng vậy
        # — nó chạy đúng một lớp ca và kết quả ĐẠT của lớp đó là `OK`.
        phai_0 = ("B0", "B1", "B6", "B7", "B9", "B8.TRƯỚC", "B8.SAU",
                  "B5.E3-rieng-1", "B5.E3-rieng-2", "B5.E3-rieng-3")
        hong = [d["buoc"] for d in BUOC if d["buoc"] in phai_0 and d["rc"] != 0]
        # VIỆC 2 — CÙNG KẾT QUẢ KHI CHẠY RIÊNG VÀ KHI CHẠY CHUNG. Không so "rc" không thôi: phải
        # so SỐ BẢN CẤT của ca `E3`, vì đó mới là thứ ca này khẳng định. Lệch ⇒ CÓ BƯỚC HỎNG.
        rieng = [d for d in BUOC if d["buoc"].startswith("B5.E3-rieng-")]
        chung = [d for d in BUOC if d["buoc"] == "B7"]
        so_rieng = {d.get("ban_cat_sau_3_lan") for d in rieng}
        if len(rieng) != 3 or len(so_rieng) != 1 or None in so_rieng:
            hong.append("B5(E3 chạy riêng KHÔNG tất định: %s)" % sorted(map(str, so_rieng)))
        elif chung and chung[0].get("ban_cat_sau_3_lan") not in so_rieng:
            hong.append("B7(E3 chạy CHUNG cho %s bản cất, chạy RIÊNG cho %s)"
                        % (chung[0].get("ban_cat_sau_3_lan"), sorted(so_rieng)))
        for d in BUOC:
            if d.get("dat") is False:
                hong.append(d["buoc"] + "(đối chứng âm KHÔNG bắt được phép tiêm)")
        print("KẾT LUẬN: %s" % ("CÓ BƯỚC HỎNG: %s" % hong if hong else
                                "mọi bước đạt; E3 riêng/chung đều %s bản cất"
                                % sorted(so_rieng)))
        return 1 if hong else 0
    finally:
        if "--giu-lai" not in sys.argv[1:]:
            shutil.rmtree(nen, ignore_errors=True)
        else:
            print("giữ lại: %s" % nen)


if __name__ == "__main__":
    sys.exit(main())
