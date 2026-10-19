#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""R27 — BẰNG CHỨNG CÔ LẬP FIXTURE cho G21 bí mật và G22 chốt cây.

VÌ SAO CÓ TỆP NÀY
-----------------
`docs/QA_NGUYENNHAN.md` §5 đo được hai lỗi **fixture**, không phải lỗi sản phẩm:

  · `thu_g21_bimat.py` (33 ca): `Z4` quét **toàn bộ** thư mục tạm hệ thống theo tiền tố, nên nó
    thấy thư mục của LƯỢT KHÁC và phán "bộ thử để lại rác". Chỉ đổi `TMPDIR` sang thư mục sạch
    thì exit 0 / 33 ca — nghĩa là fixture không cô lập, không phải sản phẩm rò.
  · `thu_g22_chotcay.py` (11 ca): `D2` đòi **cây thật** phải có tệp mới của làn khác; `D4` lấy
    "bản khác gần nhất" rồi đòi nó hỏng, nhưng bản ấy đã ĐẠT quy tắc.

Tệp này KHÔNG sửa sản phẩm và KHÔNG sửa hai bộ kia. Nó CHẠY CHÚNG và đo đúng ba việc:

  1. **HAI LƯỢT G21 SONG SONG trên CÙNG một TMPDIR**: mỗi lượt tạo gốc tạm RIÊNG, cả hai exit 0
     với 33 ca; hai gốc cùng tồn tại trong lúc chạy; sau khi xong mỗi lượt dọn gốc CỦA MÌNH.
     Một thư mục "của lượt khác" dựng sẵn trong TMPDIR phải được **NHÌN THẤY mà KHÔNG bị xoá**
     (bản cũ vừa ĐỎ vì nó, vừa có nguy cơ xoá nó).
  2. **ĐỐI CHỨNG ÂM của G21**: đưa gốc tạm DÙNG CHUNG (đặt `VIP_G21_TAM_GOC` + một thư mục lạ
     bên trong) ⇒ `Z4` PHẢI ĐỎ. Không có ca này thì "xanh" có thể chỉ là một `Z4` đã bị bịt mắt.
  3. **G22 chạy 11/11 exit 0**, `D2` trên BẢN SAO không đổi cây thật; và hai ĐỐI CHỨNG ÂM:
     bản sao KHÔNG có tệp của làn khác ⇒ phép canh chống rỗng của D2 PHẢI báo lỗi; cách chọn cũ
     của D4 ("bản khác gần nhất") ĐẠT quy tắc trong khi bản lịch sử gần nhất BỊ BẮT mới là bản
     đúng để kiểm.

CHẠY
----
    python3 app/thu/thu_r27_fixture.py -v

Không mạng · không gọi hãng · không credentials · không sửa CSDL nghiệp vụ · không đụng cây thật
(G22 D2 dựng bản sao trong thư mục tạm).
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

GOC_CAY = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THU = os.path.dirname(os.path.abspath(__file__))
G21 = os.path.join(THU, "thu_g21_bimat.py")
G22 = os.path.join(THU, "thu_g22_chotcay.py")

if THU not in sys.path:
    sys.path.insert(0, THU)

TEN_GOC_G21 = "vh-g21bimat-luot-"
TEN_CUA_LUOT_KHAC = "vh-g21bimat-cua-luot-khac"
MOC_LUOT_KHAC = "moc-cua-luot-khac.txt"
NOI_DUNG_MOC = b"THU MUC NAY KHONG PHAI CUA LUOT DANG CHAY\n"


def dem_ca(out):
    """Đọc số ca từ output unittest: `Ran N`, `skipped=`, `failures=`, `errors=`."""
    m = re.findall(r"Ran (\d+)", out)
    ca = int(m[-1]) if m else 0
    sk = re.search(r"skipped=(\d+)", out)
    that = re.search(r"failures=(\d+)", out)
    loi = re.search(r"errors=(\d+)", out)
    return {"ca": ca, "bo_qua": int(sk.group(1)) if sk else 0,
            "hong": int(that.group(1)) if that else 0,
            "loi": int(loi.group(1)) if loi else 0}


def _env_tmp(tmpdir):
    return {"TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir,
            "PYTHONDONTWRITEBYTECODE": "1"}


def chay_g21(tmpdir, run_root=None, timeout=600):
    """Chạy MỘT lượt G21 với TMPDIR chỉ định; trả dict kết quả + mốc thời gian."""
    env = dict(os.environ, **_env_tmp(tmpdir))
    if run_root is not None:
        env["VIP_G21_TAM_GOC"] = run_root
    t0 = time.monotonic()
    p = subprocess.run([sys.executable, G21], cwd=GOC_CAY, env=env,
                       capture_output=True, text=True, timeout=timeout)
    t1 = time.monotonic()
    out = (p.stdout or "") + (p.stderr or "")
    kq = dem_ca(out)
    kq.update({"ma": p.returncode, "out": out, "bat_dau": t0, "ket_thuc": t1})
    return kq


def _mo_luot_g21(tmpdir, run_root=None):
    env = dict(os.environ, **_env_tmp(tmpdir))
    if run_root is not None:
        env["VIP_G21_TAM_GOC"] = run_root
    p = subprocess.Popen([sys.executable, G21], cwd=GOC_CAY, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return {"p": p, "bat_dau": time.monotonic()}


def _dong_luot_g21(lan):
    out = lan["p"].communicate(timeout=600)[0] or ""
    lan["ket_thuc"] = time.monotonic()
    lan["out"] = out
    lan.update(dem_ca(out))
    lan["ma"] = lan["p"].returncode
    return lan


def chay_g22(tmpdir, timeout=900):
    env = dict(os.environ, **_env_tmp(tmpdir))
    t0 = time.monotonic()
    p = subprocess.run([sys.executable, G22], cwd=GOC_CAY, env=env,
                       capture_output=True, text=True, timeout=timeout)
    t1 = time.monotonic()
    out = (p.stdout or "") + (p.stderr or "")
    kq = dem_ca(out)
    kq.update({"ma": p.returncode, "out": out, "bat_dau": t0, "ket_thuc": t1})
    return kq


def _moc_phai_con(arena):
    """Mốc của "lượt khác" phải còn NGUYÊN (không bị lượt nào xoá/sửa)."""
    p = os.path.join(arena, TEN_CUA_LUOT_KHAC, MOC_LUOT_KHAC)
    if not os.path.isfile(p):
        return False, "thư mục/mốc của lượt khác đã BIẾN MẤT: %s" % p
    with open(p, "rb") as f:
        if f.read() != NOI_DUNG_MOC:
            return False, "mốc của lượt khác bị SỬA: %s" % p
    return True, ""


class R27_Fixture(unittest.TestCase):
    """Bốn phép đo; mỗi phép in bảng riêng để báo cáo chép nguyên số."""

    def _arena(self, ten):
        d = tempfile.mkdtemp(prefix="r27-%s-" % ten)
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def test_1_g21_hai_luot_song_song_tren_cung_tmpdir(self):
        """HAI lượt G21 SONG SONG trên CÙNG TMPDIR: cả hai 33/33, không xoá của nhau."""
        arena = self._arena("song-song")
        thu_muc_khac = os.path.join(arena, TEN_CUA_LUOT_KHAC)
        os.makedirs(thu_muc_khac)
        with open(os.path.join(thu_muc_khac, MOC_LUOT_KHAC), "wb") as f:
            f.write(NOI_DUNG_MOC)

        a = _mo_luot_g21(arena)
        b = _mo_luot_g21(arena)
        goc_dong_thoi = []
        try:
            # Quan sát HAI gốc tạm cùng tồn tại trong lúc cả hai lượt còn chạy.
            while a["p"].poll() is None or b["p"].poll() is None:
                goc = [d for d in os.listdir(arena)
                       if d.startswith(TEN_GOC_G21) and d != TEN_CUA_LUOT_KHAC]
                if len(goc) >= 2:
                    goc_dong_thoi = sorted(goc)
                    break
                time.sleep(0.02)
            a = _dong_luot_g21(a)
            b = _dong_luot_g21(b)
        finally:
            for lan in (a, b):
                if lan["p"].poll() is None:
                    lan["p"].kill()
                    lan["p"].communicate()

        con_lai = sorted(d for d in os.listdir(arena)
                         if d.startswith(TEN_GOC_G21) and d != TEN_CUA_LUOT_KHAC)
        con_moc, ly_do_moc = _moc_phai_con(arena)
        print("\nBẢNG R27.1 — HAI LƯỢT G21 SONG SONG TRÊN CÙNG TMPDIR")
        print("  %-4s %-9s %-9s %-8s %-5s %-6s %-6s %-7s"
              % ("lượt", "bắt đầu", "kết thúc", "mã thoát", "ca", "bỏ qua", "hỏng", "lỗi"))
        for nhan, lan in (("A", a), ("B", b)):
            print("  %-4s %-9.3f %-9.3f %-8d %-5d %-6d %-6d %-7d"
                  % (nhan, lan["bat_dau"] - a["bat_dau"], lan["ket_thuc"] - a["bat_dau"],
                     lan["ma"], lan["ca"], lan["bo_qua"], lan["hong"], lan["loi"]))
        print("  gốc tạm RIÊNG quan sát ĐỒNG THỜI: %d %s" % (len(goc_dong_thoi), goc_dong_thoi))
        print("  thư mục của lượt khác: %s" % ("CÒN NGUYÊN" if con_moc else ly_do_moc))
        print("  gốc tạm còn lại sau 2 lượt: %d %s" % (len(con_lai), con_lai))

        for nhan, lan in (("A", a), ("B", b)):
            self.assertEqual(lan["ma"], 0, "lượt %s ĐỎ:\n%s" % (nhan, lan["out"][-2500:]))
            self.assertEqual(lan["ca"], 33, "lượt %s không chạy đủ 33 ca" % nhan)
            self.assertEqual(lan["bo_qua"], 0, "lượt %s có ca bỏ qua" % nhan)
            self.assertEqual(lan["hong"] + lan["loi"], 0,
                             "lượt %s có ca hỏng/lỗi:\n%s" % (nhan, lan["out"][-2500:]))
        self.assertEqual(len(goc_dong_thoi), 2,
                         "không quan sát được HAI gốc tạm cùng tồn tại ⇒ hai lượt không thật "
                         "song song: %r" % (goc_dong_thoi,))
        self.assertLess(max(a["bat_dau"], b["bat_dau"]),
                        min(a["ket_thuc"], b["ket_thuc"]),
                        "hai lượt không chồng lấn thời gian ⇒ chưa chứng minh được song song")
        self.assertTrue(con_moc, ly_do_moc)
        self.assertEqual(con_lai, [], "lượt chạy để lại gốc tạm: %r" % (con_lai,))

    def test_2_g21_doi_chung_am_goc_tam_dung_chung(self):
        """ĐỐI CHỨNG ÂM: gốc tạm DÙNG CHUNG (có thư mục lạ bên trong) ⇒ Z4 PHẢI ĐỎ."""
        root = self._arena("g21-dung-chung")
        thu_muc_khac = os.path.join(root, TEN_CUA_LUOT_KHAC)
        os.makedirs(thu_muc_khac)
        with open(os.path.join(thu_muc_khac, MOC_LUOT_KHAC), "wb") as f:
            f.write(NOI_DUNG_MOC)
        kq = chay_g21(self._arena("g21-tmpdir"), run_root=root)
        con_moc, ly_do_moc = _moc_phai_con(root)
        print("\nBẢNG R27.2 — ĐỐI CHỨNG ÂM G21: GỐC TẠM DÙNG CHUNG")
        print("  mã thoát=%d · ca=%d · hỏng=%d · lỗi=%d · Z4_FAIL=%s"
              % (kq["ma"], kq["ca"], kq["hong"], kq["loi"],
                 "test_z4_khong_con_thu_muc_tam_cua_bo_thu" in kq["out"]
                 and "FAIL: test_z4" in kq["out"]))
        print("  thư mục của lượt khác: %s" % ("CÒN NGUYÊN" if con_moc else ly_do_moc))
        self.assertNotEqual(kq["ma"], 0, "gốc tạm DÙNG CHUNG mà bộ thử vẫn XANH ⇒ Z4 MÙ:\n%s"
                            % kq["out"][-2500:])
        self.assertIn("FAIL: test_z4_khong_con_thu_muc_tam_cua_bo_thu", kq["out"],
                      "bộ thử ĐỎ nhưng KHÔNG phải vì Z4 — đối chứng âm không đúng chỗ:\n%s"
                      % kq["out"][-2500:])
        self.assertEqual(kq["ca"], 33, "lượt đối chứng âm không chạy đủ 33 ca")
        self.assertTrue(con_moc, ly_do_moc)

    def test_3_g22_chotcay_exit_0_11_ca(self):
        """G22 chạy THẬT: exit 0 · 11 ca · 0 bỏ qua (D2 trên bản sao, D4 chọn đúng bản)."""
        arena = self._arena("g22-chay")
        kq = chay_g22(arena)
        print("\nBẢNG R27.3 — G22 CHỐT CÂY")
        print("  mã thoát=%d · ca=%d · bỏ qua=%d · hỏng=%d · lỗi=%d"
              % (kq["ma"], kq["ca"], kq["bo_qua"], kq["hong"], kq["loi"]))
        for dong in kq["out"].splitlines():
            if dong.startswith("  [D2]") or dong.startswith("  [D4]"):
                print("  " + dong.strip())
        self.assertEqual(kq["ma"], 0, "G22 ĐỎ:\n%s" % kq["out"][-3000:])
        self.assertEqual(kq["ca"], 11, "G22 không chạy đủ 11 ca")
        self.assertEqual(kq["bo_qua"], 0, "G22 có ca bỏ qua")
        self.assertEqual(kq["hong"] + kq["loi"], 0, "G22 có ca hỏng/lỗi")
        self.assertIn("trên BẢN SAO", kq["out"], "D2 không chạy trên bản sao")
        self.assertIn("bản bị bắt", kq["out"], "D4 không in bản lịch sử bị bắt")

    def test_4_g22_doi_chung_am_d2_rong_va_d4_chon_ban(self):
        """ĐỐI CHỨNG ÂM cấp HÀM: D2 trên bản sao SẠCH phải báo rỗng; D4 phải bỏ bản đã ĐẠT."""
        import thu_g22_chotcay as G

        # (a) D2 trên bản sao KHÔNG có tệp của làn khác ⇒ phép canh chống rỗng PHẢI báo lỗi.
        ban = G.tao_ban_sao_d2(co_lan_khac=False)
        try:
            self.assertEqual(G._dong_porcelain(goc=ban["cay"]), [],
                             "bản sao không có làn khác phải SẠCH")
            loi, tds, dong = G.do_d2_tren_cay(ban["cay"], G.bo_ung_vien(), tmpdir=ban["tmp"])
        finally:
            shutil.rmtree(ban["goc"], ignore_errors=True)
        self.assertEqual(dong, [], "bản sao sạch lại có `git status`: %r" % (dong,))
        self.assertTrue(any("SẠCH TRƠN" in x for x in loi),
                        "D2 KHÔNG bắt được cây sạch trơn ⇒ phép canh chống rỗng MÙ: %r" % (loi,))
        self.assertGreaterEqual(len(loi), 1 + len(tds),
                                "D2 không báo lỗi riêng cho từng bản sao: %r" % (loi,))

        # (b) D4: "bản khác gần nhất" của ít nhất một bản sao đã ĐẠT; bản bị bắt gần nhất mới đúng.
        mau = G.chotcay.mau_vung_chuan(goc=G.GOC_CAY)
        so_ban_gan_nhat_dat, dong_bang = 0, []
        for b in G.bo_ung_vien():
            sha_gan, nguon_gan = G.nguon_truoc_khi_va(b["duong"])
            kq_gan = G.kiem_quy_tac(nguon_gan, mau) if nguon_gan is not None else None
            if kq_gan is not None and kq_gan["dat"]:
                so_ban_gan_nhat_dat += 1
            sha, nguon_cu, kq_cu = G.nguon_cu_hong(b["duong"], mau)
            self.assertIsNotNone(sha, "%s: không có bản lịch sử nào bị bắt" % b["duong"])
            self.assertFalse(kq_cu["dat"], "%s: bản được chọn lại ĐẠT: %s"
                             % (b["duong"], kq_cu["ly_do"]))
            dong_bang.append((b["duong"], sha_gan,
                              (kq_gan or {}).get("dat"), sha, kq_cu["dat"]))
        print("\nBẢNG R27.4 — ĐỐI CHỨNG ÂM G22")
        print("  D2 bản sao sạch: %d lỗi (gồm 'SẠCH TRƠN') · %d bản sao được báo riêng"
              % (len(loi), len(tds)))
        print("  %-30s %-10s %-8s %-10s %-6s"
              % ("BẢN SAO", "GẦN NHẤT", "ĐẠT?", "BỊ BẮT", "ĐẠT?"))
        for duong, sha_gan, dat_gan, sha_cu, dat_cu in dong_bang:
            print("  %-30s %-10s %-8s %-10s %-6s"
                  % (duong, (sha_gan or "-")[:8], bool(dat_gan),
                     (sha_cu or "-")[:8], bool(dat_cu)))
        print("  bản 'khác gần nhất' ĐẠT quy tắc: %d/%d ⇒ cách chọn CŨ sai tiền đề"
              % (so_ban_gan_nhat_dat, len(dong_bang)))
        self.assertGreaterEqual(so_ban_gan_nhat_dat, 1,
                                "không tái hiện được tiền đề sai của D4 trên nền này")


if __name__ == "__main__":
    print("=== R27 · CÔ LẬP FIXTURE: G21 SONG SONG · G22 BẢN SAO · ĐỐI CHỨNG ÂM ===")
    unittest.main(verbosity=2)
