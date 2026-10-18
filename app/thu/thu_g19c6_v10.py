# -*- coding: utf-8 -*-
"""G19/C6 — MIGRATION v10: `DDL_G12Q` (9 chỉ mục của lớp truy vấn G12) CHO CSDL ĐÃ Ở v9.

VÌ SAO BỘ NÀY TỒN TẠI
=====================
Route `GET /api/v2/don` đã nối vào `app/truy_van.py`, nhưng `csdl.PHIEN_BAN_SCHEMA` vẫn là 9
và chưa có `nang_len_v10`. Hệ quả ĐO ĐƯỢC, không phải suy đoán: một CSDL **ĐANG Ở v9** đã chạy
xong `nang_len_v9`; `migrate.chay()` chỉ chạy các bước có `pb < n`, nên bước v9 sẽ KHÔNG BAO GIỜ
chạy lại. Nhét `DDL_G12Q` vào thân `nang_len_v9` chỉ giúp CSDL MỚI (đi qua cả thang) — CSDL đã ở
v9 thì 9 chỉ mục KHÔNG BAO GIỜ được tạo, và **không có gì báo**: truy vấn vẫn trả đúng kết quả,
chỉ chậm. Đó đúng là hỏng im lặng của §12.2.

Bộ này là ĐỐI CHỨNG ÂM/DƯƠNG BẮT BUỘC cho bản vá:
  (a) CSDL MỚI 0 → 10                : đủ 9/9 chỉ mục `ix_g12q_%`.
  (b) CSDL ĐÃ Ở v9 nâng lên 10       : đủ 9/9 chỉ mục — TRƯỜNG HỢP mà cách cắm vào v9 KHÔNG
      giải được, nên phải có ca riêng chứng minh. Kèm chốt: trước khi nâng, CSDL v9 có **0**
      chỉ mục G12Q; sau khi nâng chỉ có ĐÚNG MỘT bước chạy (v10), và một dòng `audit` có sẵn
      được bảo toàn.
  (c) CSDL ĐÃ Ở v10 chạy lại         : không lỗi, không nhân đôi chỉ mục; gọi THẲNG
      `nang_len_v10` hai lượt cũng chỉ tạo đối tượng ở lượt đầu (DDL toàn `IF NOT EXISTS`).
  (d) GỠ MỘT chỉ mục khỏi hằng DDL   : cả (a) và (b) PHẢI ĐỎ — nếu vẫn xanh thì phép đếm của
      chúng không phụ thuộc vào việc migration áp ĐỦ 9 chỉ mục, tức là phép đo MÙ.
  (e) `nang_len_v10` chạy ĐÚNG HẰNG của module: THÊM một chỉ mục đánh dấu vào
      `truy_van.DDL_G12Q` trong tiến trình con thì CSDL nhận đúng chỉ mục đánh dấu đó (không
      phải bản DDL chép).

PHẠM VI — ĐỌC KỸ, ĐÂY LÀ RANH GIỚI CỐ Ý
========================================
  · CHỈ FIXTURE SQLITE TẠM (`tempfile.mkdtemp`), mỗi ca một thư mục riêng.
  · **KHÔNG** PostgreSQL. **KHÔNG** CSDL nghiệp vụ thật. **KHÔNG** cổng `:5432`.
  · `OWNER_ACTIONS C4` / `D-8` (chuyển PostgreSQL) giữ nguyên **BLOCKED** — bộ này không liên
    quan và không mở khóa gì.
  · Không mạng, không hãng vận chuyển, không push/deploy.

CÁCH CHẠY
=========
    python3 app/thu/thu_g19c6_v10.py

Mỗi ca chạy trong MỘT TIẾN TRÌNH CON riêng (một tiến trình `python3` thật) để không ca nào
dùng chung trạng thái mô-đun (`_da_khoi_tao`, kết nối theo thread, `cau_hinh.DUONG_DAN_CSDL`)
với ca khác. Cuối lượt in BẢNG CHỨNG + mã thoát.
"""
import ast
import inspect
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

GOC_APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOC_DA = os.path.dirname(GOC_APP)
sys.path.insert(0, GOC_APP)

# Đặt TRƯỚC khi nạp `cau_hinh`/`csdl`: chúng đọc biến môi trường MỘT LẦN lúc nạp.
# `VIP_HUB_DATA` là thư mục TẠM NGOÀI cây repo — không bao giờ là `app/du-lieu`.
GOC_TAM = tempfile.mkdtemp(prefix="vip-hub-g19c6-v10-")
os.environ["VIP_HUB_DATA"] = GOC_TAM
# `migrate.sao_luu()` fail-closed khi chưa khai kho (chốt G22). Bộ thử khai SQLite cho MÔI
# TRƯỜNG TẠM của chính nó — cùng một dòng mà 8 bộ thử khác đã phải khai.
os.environ["VIP_KHO_DANG_CHAY"] = "sqlite"

import csdl      # noqa: E402
import migrate   # noqa: E402
import truy_van  # noqa: E402

# Bằng chứng in ra theo ĐÚNG thứ tự chạy, không bị đệm ống dẫn đẩy xuống cuối.
try:
    sys.stdout.reconfigure(line_buffering=True)
except AttributeError:      # py < 3.7 — không có reconfigure; không ảnh hưởng kết quả
    pass

# ============================================================================
# HỢP ĐỒNG ĐẾM — DANH SÁCH VIẾT CỨNG, KHÔNG SUY TỪ `DDL_G12Q`
# ============================================================================
# Vì sao không suy từ chính hằng DDL: ca (d) gỡ một câu khỏi hằng. Nếu "9" cũng suy từ hằng
# thì gỡ một câu sẽ thành "8/8 ĐẠT" — phép đo tự nới theo lỗi nó phải bắt, đúng kiểu phép đo
# MÙ. Danh sách dưới đây là HỢP ĐỒNG của G19/C6, viết độc lập với nguồn thi hành.
CHI_MUC_G12Q = (
    "ix_g12q_don_tenant_tao",
    "ix_g12q_don_tenant_id_desc",
    "ix_g12q_don_tenant_ttgiao",
    "ix_g12q_don_tenant_cod",
    "ix_g12q_don_tenant_tk_hang",
    "ix_g12q_don_tenant_doisoat",
    "ix_g12q_don_tenant_khach",
    "ix_g12q_don_tenant_madon",
    "ix_g12q_tkhang_tenant_hang",
)
SO_CHI_MUC = len(CHI_MUC_G12Q)          # 9 — con số của hợp đồng, không phải của DDL

BANG_CHUNG = []                          # (nhãn, số chỉ mục đếm được, ghi chú)


# ============================================================================
# HẠ TẦNG: tiến trình con + đọc fixture
# ============================================================================
BO_TRO = r'''
# -*- coding: utf-8 -*-
"""Tiến trình con của `thu_g19c6_v10.py` — mỗi lượt một CSDL TẠM riêng, không dùng chung
trạng thái mô-đun với ca khác. In kết quả bằng MỘT dòng `__KQ__<json>`."""
import json
import sys

sys.path.insert(0, {goc_app!r})

import csdl
import migrate
import truy_van

LOC = "ix_g12q_%"


def _ds_chi_muc(kn):
    return {{r[0] for r in kn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE ?", (LOC,))}}


def _in(kq):
    print("__KQ__" + json.dumps(kq, ensure_ascii=False, default=str))


def _chay_migrate():
    return migrate.chay(im_lang=True)


def dung_v9():
    """Dựng CSDL ĐÚNG TRẠNG THÁI v9 bằng CHÍNH các bước thật v2..v9 của `migrate`.

    Đây là mô phỏng trung thực nhất của "CSDL đã ở v9 trước khi bản vá này ra đời": cùng
    `csdl.mo()` tạo lõi + seed, cùng thứ tự bước, cùng một transaction. Bước v10 KHÔNG được
    gọi, nên trạng thái cuối thiếu ĐÚNG phần mà bản vá thêm vào — đó là điều kiện của ca (b).
    """
    csdl.mo()
    kn = csdl.ket_noi(timeout=migrate.KHOA_CHO_GIAY, tuong_minh=True)
    try:
        kn.execute("PRAGMA foreign_keys=OFF")
        kn.execute("BEGIN IMMEDIATE")
        buoc = []
        for ten in ("nang_len_v2", "nang_len_v3", "nang_len_v4", "nang_len_v5",
                    "nang_len_v6", "nang_len_v7", "nang_len_v8", "nang_len_v9"):
            buoc += getattr(migrate, ten)(kn)
        kn.execute("INSERT OR REPLACE INTO schema_version"
                   " (phien_ban, ap_dung_luc, ghi_chu) VALUES (9,?,?)",
                   (csdl.bay_gio(), "fixture v9 của thu_g19c6_v10: " + "; ".join(buoc)))
        kn.execute("COMMIT")
    except BaseException:
        try:
            kn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        kn.close()
        csdl.dong()
    return {{"phien_ban": 9, "so_buoc": len(buoc),
             "buoc_cuoi": buoc[-1] if buoc else ""}}


def go_mot_chi_muc():
    """ĐỐI CHỨNG ÂM: bỏ ĐÚNG MỘT câu khỏi hằng DDL của module rồi để migration chạy thật."""
    cau = [c.strip() for c in truy_van.DDL_G12Q.split(";") if c.strip()]
    rut = cau[-1]
    truy_van.DDL_G12Q = ";\n".join(cau[:-1]) + ";"
    return rut.split()[5]          # CREATE INDEX IF NOT EXISTS <tên> ON …


def them_chi_muc_danh_dau():
    """DƯƠNG: thêm một chỉ mục đánh dấu vào hằng của module. Nó xuất hiện trong CSDL nghĩa là
    `nang_len_v10` đọc hằng LÚC CHẠY, không phải một bản DDL chép sẵn."""
    ten = "ix_g19c6_thu_bang_chung"
    truy_van.DDL_G12Q += ("\nCREATE INDEX IF NOT EXISTS " + ten
                          + " ON don_hang(tenant_id, ma_don);\n")
    return ten


mode = sys.argv[1]
if mode == "moi":
    _in(_chay_migrate())
elif mode == "dung_v9":
    _in(dung_v9())
elif mode == "nang":
    _in(_chay_migrate())
elif mode == "v10_lai":
    # CSDL v9 KHÔNG có chỉ mục G12Q. Gọi THẲNG `nang_len_v10` hai lượt: lượt đầu phải tạo 9,
    # lượt sau phải tạo 0. Đây là phép đo idempotent của CHÍNH bước v10, không phải của
    # `chay()` (chạy `chay()` trên v10 thì nó về sớm và không chạm bước nào).
    kn = csdl.ket_noi(tuong_minh=True)
    try:
        kn.execute("BEGIN IMMEDIATE")
        truoc = _ds_chi_muc(kn)
        migrate.nang_len_v10(kn)
        giua = _ds_chi_muc(kn)
        migrate.nang_len_v10(kn)
        sau = _ds_chi_muc(kn)
        kn.execute("COMMIT")
    except BaseException:
        try:
            kn.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        kn.close()
    _in({{"truoc": len(truoc), "sau_lan1": len(giua), "sau_lan2": len(sau),
          "them_lan1": len(giua - truoc), "them_lan2": len(sau - giua)}})
elif mode == "ddl_go":
    ten = go_mot_chi_muc()
    kq = _chay_migrate()
    kq["rut"] = ten
    _in(kq)
elif mode == "ddl_them":
    ten = them_chi_muc_danh_dau()
    kq = _chay_migrate()
    kq["danh_dau"] = ten
    _in(kq)
else:
    raise SystemExit("mode lạ: " + mode)
'''.format(goc_app=GOC_APP)

TEP_BO_TRO = os.path.join(GOC_TAM, "_bo_tro.py")
with open(TEP_BO_TRO, "w", encoding="utf-8") as _f:
    _f.write(BO_TRO)


def _thu_muc(ten):
    duong = os.path.join(GOC_TAM, ten)
    os.makedirs(duong, exist_ok=True)
    return duong


def _chay_con(thu_muc, mode):
    """Chạy helper trong tiến trình con với `VIP_HUB_DATA` = thư mục TẠM của ca."""
    mt = dict(os.environ, VIP_HUB_DATA=thu_muc, VIP_KHO_DANG_CHAY="sqlite")
    kq = subprocess.run([sys.executable, TEP_BO_TRO, mode], cwd=GOC_DA, env=mt,
                        capture_output=True, text=True, timeout=180)
    if kq.returncode != 0:
        raise AssertionError(
            "tiến trình con `%s` hỏng (rc=%d):\n--- stdout ---\n%s\n--- stderr ---\n%s"
            % (mode, kq.returncode, kq.stdout[-2000:], kq.stderr[-3000:]))
    dong = [d for d in kq.stdout.splitlines() if d.startswith("__KQ__")]
    if len(dong) != 1:
        raise AssertionError("không thấy đúng một dòng __KQ__ (mode %s):\n%s\n%s"
                             % (mode, kq.stdout[-2000:], kq.stderr[-1000:]))
    return json.loads(dong[0][len("__KQ__"):])


def _duong_db(thu_muc):
    return os.path.join(thu_muc, "hub.db")


def _phien_ban(duong):
    kn = sqlite3.connect(duong)
    try:
        return kn.execute("SELECT MAX(phien_ban) FROM schema_version").fetchone()[0]
    finally:
        kn.close()


def _ds_chi_muc(duong):
    kn = sqlite3.connect(duong)
    try:
        return {r[0] for r in kn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_g12q_%'")}
    finally:
        kn.close()


def _dem_chi_muc(duong):
    kn = sqlite3.connect(duong)
    try:
        return kn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'ix_g12q_%'"
        ).fetchone()[0]
    finally:
        kn.close()


def _co_bang(duong, ten):
    kn = sqlite3.connect(duong)
    try:
        return kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name=?",
                          (ten,)).fetchone()[0] == 1
    finally:
        kn.close()


def _kiem_va_doi(ds_co):
    """CỔNG của ca (a)/(b): thiếu dù CHỈ MỘT chỉ mục là NÉM. Ca (d) gọi chính cổng này và
    đòi nó ném — nếu nó không ném thì phép đếm không thật sự bắt lỗi thiếu chỉ mục."""
    thieu = sorted(set(CHI_MUC_G12Q) - set(ds_co))
    if thieu:
        raise AssertionError("THIẾU %d/%d chỉ mục G12Q: %s"
                             % (len(thieu), SO_CHI_MUC, ", ".join(thieu)))
    return True


def _ghi(nhan, so, ghi_chu):
    BANG_CHUNG.append((nhan, so, ghi_chu))


# ============================================================================
# (a) CSDL MỚI 0 → 10
# ============================================================================
class A_CsdlMoi(unittest.TestCase):

    def test_a1_csdl_moi_0_len_10_co_du_9_chi_muc(self):
        tm = _thu_muc("a-csdl-moi")
        kq = _chay_con(tm, "moi")
        duong = _duong_db(tm)

        self.assertTrue(kq["da_nang"], f"CSDL mới phải được nâng cấp: {kq}")
        self.assertEqual(kq["phien_ban"], 10)
        self.assertEqual(_phien_ban(duong), 10, "schema_version phải là 10")
        self.assertIn("G12", kq["buoc"][-1], "bước CUỐI của thang phải là bước v10")

        ds = _ds_chi_muc(duong)
        _kiem_va_doi(ds)
        self.assertEqual(ds, set(CHI_MUC_G12Q), f"tên chỉ mục khác hợp đồng: {sorted(ds)}")
        self.assertEqual(_dem_chi_muc(duong), SO_CHI_MUC)
        # "Giữ `nang_len_v9` nguyên": DDL cũ vẫn phải được áp trên đường 0 → 10.
        self.assertTrue(_co_bang(duong, "gioi_han_luot"),
                        "bảng của v9 biến mất — nang_len_v9 bị đụng")

        _ghi("0 → 10 (CSDL MỚI)", len(ds), "đủ 9/9 chỉ mục")
        print(f"\n  [a] 0 → 10: schema v{_phien_ban(duong)} · {len(ds)}/9 chỉ mục G12Q · "
              f"gioi_han_luot (v9) còn nguyên · nguồn: {duong}")


# ============================================================================
# (b) CSDL ĐÃ Ở v9 → 10 — trường hợp mà cách cắm vào v9 KHÔNG giải được
# ============================================================================
class B_CsdlDaOV9(unittest.TestCase):

    def test_b1_v9_nang_len_10_co_du_9_chi_muc(self):
        tm = _thu_muc("b-v9-len-10")
        _chay_con(tm, "dung_v9")
        duong = _duong_db(tm)

        # TIỀN ĐỀ: đây đúng là trạng thái bẫy — CSDL đã ở v9 và KHÔNG có một chỉ mục G12Q nào.
        self.assertEqual(_phien_ban(duong), 9)
        self.assertEqual(_dem_chi_muc(duong), 0,
                         "fixture v9 không được có sẵn chỉ mục G12Q, nếu không ca (b) vô nghĩa")

        # Một dòng dữ liệu nghiệp vụ có sẵn để đo bảo toàn qua lượt nâng cấp.
        kn = sqlite3.connect(duong)
        try:
            kn.execute("INSERT INTO audit (luc, hanh_dong, doi_tuong) VALUES (?,?,?)",
                       ("2026-10-18 09:00:00+0700", "truoc_nang_v10", "don:1"))
            kn.commit()
        finally:
            kn.close()

        kq = _chay_con(tm, "nang")
        self.assertTrue(kq["da_nang"], f"CSDL v9 phải được nâng lên: {kq}")
        self.assertEqual(kq["phien_ban"], 10)
        self.assertEqual(_phien_ban(duong), 10)
        # pb=9 nên CHỈ bước v10 được chạy — đây là bằng chứng đường nâng cấp v9→10 thật sự đi
        # qua bước mới, chứ không phải may mắn vì một bước cũ chạy lại.
        self.assertEqual(len(kq["buoc"]), 1, f"phải chỉ có bước v10, thực tế: {kq['buoc']}")
        self.assertIn("G12", kq["buoc"][0])

        ds = _ds_chi_muc(duong)
        _kiem_va_doi(ds)
        self.assertEqual(ds, set(CHI_MUC_G12Q))
        self.assertEqual(_dem_chi_muc(duong), SO_CHI_MUC)

        # Bảo toàn dữ liệu: bước v10 chỉ tạo chỉ mục, không đụng dòng nào.
        self.assertEqual(kq["truoc"].get("audit"), 1)
        self.assertEqual(kq["sau"].get("audit"), 1)
        kn = sqlite3.connect(duong)
        try:
            self.assertEqual(kn.execute(
                "SELECT COUNT(*) FROM audit WHERE hanh_dong='truoc_nang_v10'").fetchone()[0], 1)
        finally:
            kn.close()

        _ghi("v9 → 10", len(ds), "đủ 9/9 chỉ mục · chỉ bước v10 chạy · audit còn nguyên")
        print(f"\n  [b] v9 → 10: trước nâng 0 chỉ mục · sau nâng {len(ds)}/9 · "
              f"bước chạy = {kq['buoc'][0][:70]}… · nguồn: {duong}")


# ============================================================================
# (c) CSDL ĐÃ Ở v10 chạy lại — idempotent
# ============================================================================
class C_Idempotent(unittest.TestCase):

    def test_c1_chay_lai_v10_khong_loi_khong_nhan_doi(self):
        tm = _thu_muc("c-chay-lai-v10")
        _chay_con(tm, "moi")
        duong = _duong_db(tm)
        self.assertEqual(_dem_chi_muc(duong), SO_CHI_MUC)

        kq = _chay_con(tm, "nang")       # chạy `migrate.chay()` trên CSDL ĐÃ ở v10
        self.assertFalse(kq["da_nang"], f"không được nâng cấp lại: {kq}")
        self.assertEqual(kq["phien_ban"], 10)
        self.assertEqual(_phien_ban(duong), 10)
        self.assertEqual(_dem_chi_muc(duong), SO_CHI_MUC, "chỉ mục bị nhân đôi")

        kn = sqlite3.connect(duong)
        try:
            trung = kn.execute(
                "SELECT name, COUNT(*) c FROM sqlite_master WHERE type='index'"
                " AND name LIKE 'ix_g12q_%' GROUP BY name HAVING c > 1").fetchall()
        finally:
            kn.close()
        self.assertEqual(trung, [], f"tên chỉ mục trùng: {trung}")

        _ghi("v10 chạy lại", _dem_chi_muc(duong), "da_nang=False · không nhân đôi")
        print(f"\n  [c1] v10 chạy lại: da_nang={kq['da_nang']} · "
              f"{_dem_chi_muc(duong)}/9 chỉ mục · không tên trùng")

    def test_c2_goi_thang_nang_len_v10_hai_luot(self):
        """Đo idempotent của CHÍNH bước v10 (không phải `chay()` về sớm): trên fixture v9,
        lượt đầu +9, lượt hai +0."""
        tm = _thu_muc("c2-goi-thang-v10")
        _chay_con(tm, "dung_v9")
        duong = _duong_db(tm)
        self.assertEqual(_dem_chi_muc(duong), 0)

        kq = _chay_con(tm, "v10_lai")
        self.assertEqual(kq["truoc"], 0)
        self.assertEqual(kq["them_lan1"], SO_CHI_MUC, f"lượt đầu phải tạo 9: {kq}")
        self.assertEqual(kq["them_lan2"], 0, f"lượt hai phải tạo 0: {kq}")
        self.assertEqual(kq["sau_lan1"], SO_CHI_MUC)
        self.assertEqual(kq["sau_lan2"], SO_CHI_MUC)
        self.assertEqual(_dem_chi_muc(duong), SO_CHI_MUC)

        _ghi("v10 gọi thẳng 2 lượt (trên v9)", _dem_chi_muc(duong), "lượt 1 +9 · lượt 2 +0")
        print(f"\n  [c2] gọi thẳng nang_len_v10: lượt 1 +{kq['them_lan1']} · "
              f"lượt 2 +{kq['them_lan2']} · còn {_dem_chi_muc(duong)}/9")


# ============================================================================
# (d) ĐỐI CHỨNG ÂM — gỡ một chỉ mục thì (a) và (b) PHẢI ĐỎ
# ============================================================================
class D_DoiChungAm(unittest.TestCase):

    def test_d1_go_mot_cau_DDL_thi_ca_a_va_b_phai_do(self):
        # ── (a) đường CSDL MỚI, DDL bị gỡ ĐÚNG MỘT câu ─────────────────────
        tm_a = _thu_muc("d1a-ddl-go-moi")
        kq_a = _chay_con(tm_a, "ddl_go")
        duong_a = _duong_db(tm_a)
        rut = kq_a["rut"]
        self.assertIn(rut, CHI_MUC_G12Q, "câu bị gỡ phải là một chỉ mục trong hợp đồng")
        # Migration VẪN thành công và vẫn ghi v10 — đúng kiểu hỏng im lặng cần bắt.
        self.assertEqual(_phien_ban(duong_a), 10)
        ds_a = _ds_chi_muc(duong_a)
        self.assertEqual(len(ds_a), SO_CHI_MUC - 1, f"phải thiếu đúng 1, thực: {sorted(ds_a)}")
        self.assertEqual(sorted(set(CHI_MUC_G12Q) - ds_a), [rut])
        with self.assertRaises(AssertionError, msg="CỔNG (a) KHÔNG ĐỎ khi thiếu một chỉ mục"):
            _kiem_va_doi(ds_a)

        # ── (b) đường v9 → 10, cùng DDL bị gỡ ───────────────────────────────
        tm_b = _thu_muc("d1b-ddl-go-v9")
        _chay_con(tm_b, "dung_v9")
        kq_b = _chay_con(tm_b, "ddl_go")
        duong_b = _duong_db(tm_b)
        self.assertEqual(kq_b["rut"], rut)
        self.assertEqual(_phien_ban(duong_b), 10)
        ds_b = _ds_chi_muc(duong_b)
        self.assertEqual(len(ds_b), SO_CHI_MUC - 1)
        self.assertEqual(sorted(set(CHI_MUC_G12Q) - ds_b), [rut])
        with self.assertRaises(AssertionError, msg="CỔNG (b) KHÔNG ĐỎ khi thiếu một chỉ mục"):
            _kiem_va_doi(ds_b)

        _ghi("ĐỐI CHỨNG ÂM — gỡ 1 chỉ mục (0 → 10)", len(ds_a),
             f"thiếu {rut} → cổng (a) ĐỎ")
        _ghi("ĐỐI CHỨNG ÂM — gỡ 1 chỉ mục (v9 → 10)", len(ds_b),
             f"thiếu {rut} → cổng (b) ĐỎ")
        print(f"\n  [d1] gỡ `{rut}` khỏi DDL: 0→10 còn {len(ds_a)}/9 · v9→10 còn {len(ds_b)}/9 "
              f"→ CẢ HAI cổng đều ném AssertionError (ĐỎ đúng như phải đỏ)")

    def test_d2_xoa_chi_muc_vat_ly_thi_cong_phat_hien_duoc(self):
        """Vế thứ hai của cùng bất biến: chỉ mục BIẾN MẤT khỏi CSDL (không phải khỏi DDL)
        cũng phải bị cổng bắt — cổng đọc `sqlite_master`, không đọc lời khai."""
        tm = _thu_muc("d2-xoa-vat-ly")
        _chay_con(tm, "moi")
        duong = _duong_db(tm)
        mat = "ix_g12q_tkhang_tenant_hang"
        kn = sqlite3.connect(duong)
        try:
            kn.execute("DROP INDEX " + mat)
            kn.commit()
        finally:
            kn.close()
        ds = _ds_chi_muc(duong)
        self.assertEqual(sorted(set(CHI_MUC_G12Q) - ds), [mat])
        with self.assertRaises(AssertionError):
            _kiem_va_doi(ds)
        print(f"\n  [d2] DROP INDEX `{mat}` → còn {len(ds)}/9 · cổng vẫn ĐỎ")


# ============================================================================
# (e) BẰNG CHỨNG CẤU TRÚC — chạy ĐÚNG hằng của module, không chép DDL
# ============================================================================
class E_BangChungCauTruc(unittest.TestCase):

    def test_e1_migration_doc_hang_DDL_cua_module_luc_chay(self):
        tm = _thu_muc("e1-danh-dau-ddl")
        kq = _chay_con(tm, "ddl_them")
        duong = _duong_db(tm)
        self.assertEqual(kq["danh_dau"], "ix_g19c6_thu_bang_chung")
        kn = sqlite3.connect(duong)
        try:
            co = kn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name=?",
                            (kq["danh_dau"],)).fetchone()[0]
        finally:
            kn.close()
        self.assertEqual(co, 1,
                         "chỉ mục đánh dấu KHÔNG vào CSDL ⇒ migration chạy một bản DDL chép, "
                         "không phải `truy_van.DDL_G12Q`")
        # 9 chỉ mục hợp đồng vẫn đủ (chỉ mục đánh dấu là cộng thêm, không thay thế).
        _kiem_va_doi(_ds_chi_muc(duong))
        self.assertEqual(_dem_chi_muc(duong), SO_CHI_MUC)
        print(f"\n  [e1] thêm `{kq['danh_dau']}` vào hằng của module → CSDL nhận đúng nó ⇒ "
              f"nang_len_v10 đọc hằng LÚC CHẠY")

    def test_e2_ma_nguon_v10_khong_chep_DDL(self):
        """Đọc AST của `nang_len_v10` (bỏ docstring): phải gọi
        `chay_ddl_trong_giao_dich(kn, truy_van.DDL_G12Q)` và KHÔNG chứa chuỗi `CREATE INDEX`."""
        with open(migrate.__file__, encoding="utf-8") as f:
            cay = ast.parse(f.read())
        ham = next((n for n in cay.body
                    if isinstance(n, ast.FunctionDef) and n.name == "nang_len_v10"), None)
        self.assertIsNotNone(ham, "migrate.nang_len_v10 KHÔNG tồn tại")
        self.assertTrue(ast.get_docstring(ham), "nang_len_v10 phải có docstring giải thích")

        than = ast.Module(body=ham.body[1:], type_ignores=[])   # bỏ docstring
        goi = [n for n in ast.walk(than)
               if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "chay_ddl_trong_giao_dich"]
        self.assertTrue(goi, "nang_len_v10 phải chạy DDL qua `chay_ddl_trong_giao_dich`")
        self.assertEqual(len(goi[0].args), 2)
        tham_so = goi[0].args[1]
        self.assertIsInstance(tham_so, ast.Attribute)
        self.assertEqual(tham_so.attr, "DDL_G12Q")
        self.assertIsInstance(tham_so.value, ast.Name)
        self.assertEqual(tham_so.value.id, "truy_van",
                         "DDL phải lấy từ `truy_van.DDL_G12Q` — không được chép sang migrate")
        chuoi = [n.value for n in ast.walk(than)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        self.assertFalse([s for s in chuoi if "create index" in s.lower()],
                         f"nang_len_v10 có chuỗi DDL chép tay: {chuoi}")

        self.assertEqual(csdl.PHIEN_BAN_SCHEMA, 10, "PHIEN_BAN_SCHEMA phải bump lên 10")
        self.assertTrue(hasattr(migrate, "nang_len_v9"), "nang_len_v9 phải còn")
        self.assertNotIn("DDL_G12Q", inspect.getsource(migrate.nang_len_v9),
                         "không được nhét G12Q vào thân nang_len_v9")
        self.assertNotIn("truy_van", inspect.getsource(migrate.nang_len_v9))

    def test_e3_hop_dong_DDL_dung_9_chi_muc(self):
        cau = [c.strip() for c in truy_van.DDL_G12Q.split(";") if c.strip()]
        self.assertEqual(len(cau), SO_CHI_MUC, f"DDL_G12Q phải có đúng 9 câu: {len(cau)}")
        ten = []
        for c in cau:
            self.assertTrue(c.upper().startswith("CREATE INDEX IF NOT EXISTS"), c)
            ten.append(c.split()[5])
        self.assertEqual(set(ten), set(CHI_MUC_G12Q), "tên chỉ mục khác hợp đồng G19/C6")
        for cam in ("DROP", "ALTER", "DELETE", "UPDATE"):
            self.assertNotIn(cam, truy_van.DDL_G12Q.upper())

    def test_e4_v9_giu_nguyen_tren_fixture(self):
        """Fixture v9 (dựng bằng chính các bước v2..v9) có bảng của v9 và 0 chỉ mục G12Q."""
        tm = _thu_muc("e4-v9-giu-nguyen")
        _chay_con(tm, "dung_v9")
        duong = _duong_db(tm)
        self.assertEqual(_phien_ban(duong), 9)
        self.assertTrue(_co_bang(duong, "gioi_han_luot"))
        self.assertTrue(_co_bang(duong, "gioi_han_chan"))
        self.assertEqual(_dem_chi_muc(duong), 0)
        print("\n  [e4] fixture v9: gioi_han_luot + gioi_han_chan có mặt (v9 chạy), 0 chỉ mục G12Q")


# ============================================================================
# BẢNG CHỨNG + MÃ THOÁT
# ============================================================================
if __name__ == "__main__":
    print("=" * 78)
    print("[G19/C6 v10] PHẠM VI: SQLite TẠM — %s" % GOC_TAM)
    print("             KHÔNG PostgreSQL · KHÔNG CSDL nghiệp vụ thật · KHÔNG cổng :5432")
    print("=" * 78)
    chuong_trinh = unittest.main(exit=False, verbosity=2)
    ok = chuong_trinh.result.wasSuccessful()

    print("\n" + "=" * 78)
    print("BẢNG CHỨNG — số chỉ mục `ix_g12q_%` đếm được trong sqlite_master")
    print("-" * 78)
    print("%-45s %8s  %s" % ("ca", "chỉ mục", "ghi chú"))
    for nhan, so, ghi_chu in BANG_CHUNG:
        print("%-45s %8s  %s" % (nhan, so, ghi_chu))
    print("-" * 78)
    print("Tổng số ca: %d · hỏng: %d · bỏ qua: %d"
          % (chuong_trinh.result.testsRun, len(chuong_trinh.result.failures)
             + len(chuong_trinh.result.errors), len(chuong_trinh.result.skipped)))
    print("Kết quả: %s · exit code: %d" % ("ĐẠT" if ok else "HỎNG", 0 if ok else 1))
    sys.exit(0 if ok else 1)
