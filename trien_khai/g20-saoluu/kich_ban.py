#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 / AG-04 — CÁC KỊCH BẢN ĐO cho vòng tròn SAO LƯU → KHÔI PHỤC.

Mô-đun này là NGUỒN DUY NHẤT của các kịch bản. Hai vỏ gọi nó:
  * `trien_khai/g20-saoluu/do_vong_tron.py` — chạy tay, in bảng cho người đọc;
  * `app/thu/thu_g20_saoluu.py`            — bộ thử tự động, vào lượt hồi quy chung.

====== BA LUẬT CỦA MÔ-ĐUN NÀY ======
1. MỌI khẳng định đi kèm MÃ THOÁT THẬT của lệnh đã sinh ra nó. Không có chỗ nào viết
   "đã chạy thành công" mà không có `returncode` nằm cạnh.
2. Mọi ca PHỦ ĐỊNH (hệ từ chối / hệ không làm gì) đều phải có ĐỐI CHỨNG ĐƯỜNG: một ca anh em
   chạy đúng đường đó và cho kết quả KHÁC. Thiếu đối chứng thì "không thấy lỗi" và "không đo
   được lỗi" là một.
3. Không tự bịa mã trạng thái hãng (D-4) và không gọi mạng. Mọi lệnh con chạy với
   `VIP_HUB_DATA` trỏ vào thư mục TẠM; `chot_an_toan()` chặn vùng dữ liệu thật.
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

import khung_do  # noqa: E402

PY = sys.executable or "python3"
VUNG_CAM = os.path.expanduser("~/Projects/vip-express-hub")

# Thư mục `app/` cấp cho MỌI tiến trình con. `G21_APP_DIR` cho phép chạy CÙNG bộ kịch bản này
# trên một `migrate.py` ỨNG VIÊN (bản đã vá, hoặc bản bị tiêm lỗi) mà KHÔNG sửa cây thật —
# xem `trien_khai/g20-saoluu/fail_closed.py` và `app/thu/thu_g21_saoluu.py`.
APP = os.environ.get("G21_APP_DIR") or os.path.join(GOC, "app")


# --------------------------------------------------------------------- hạ tầng chạy con
def chot_an_toan(duong):
    d = os.path.abspath(duong)
    if d == VUNG_CAM or d.startswith(VUNG_CAM + os.sep):
        raise SystemExit("DỪNG: đường đo nằm trong vùng dữ liệu THẬT: %s" % d)
    if not any(d.startswith(c) for c in ("/tmp/", "/var/folders/", "/private/var/folders/",
                                         "/var/tmp/")):
        raise SystemExit("DỪNG: đường đo không nằm trong vùng tạm: %s" % d)
    return d


def moi_truong(data_dir, **them):
    e = dict(os.environ)
    e["VIP_HUB_DATA"] = data_dir
    e.pop("VIP_HUB_RESET_TOKEN", None)
    e.update(them)
    return e


def chay_con(ma, data_dir, timeout=900, env_them=None, stdin=None):
    """Chạy một đoạn mã trong TIẾN TRÌNH RIÊNG với `VIP_HUB_DATA` riêng.

    Tiến trình riêng là BẮT BUỘC, không phải cho gọn: `cau_hinh` đọc `VIP_HUB_DATA` MỘT LẦN
    lúc nạp mô-đun, nên trong cùng tiến trình thì lượt đo thứ hai vẫn dùng đường dẫn của lượt
    đầu — và mọi phép so sau đó chỉ đang so một CSDL với chính nó.
    """
    p = subprocess.run([PY, "-c", ma], capture_output=True, text=True, cwd=GOC,
                       env=moi_truong(data_dir, **(env_them or {})), timeout=timeout,
                       input=stdin)
    return p.returncode, p.stdout, p.stderr


def gieo(data_dir, timeout=900):
    p = subprocess.run([PY, os.path.join(DAY, "gieo.py"), "--khong-in"], capture_output=True,
                       text=True, cwd=GOC, env=moi_truong(data_dir), timeout=timeout)
    return p.returncode, p.stdout, p.stderr


_MA_SAO_LUU = ("import sys; sys.path.insert(0, %r); import migrate; print(migrate.sao_luu())"
               % APP)
_MA_KHOI_PHUC = ("import os, sys; sys.path.insert(0, %r); import migrate;"
                 " migrate.khoi_phuc(os.environ['G20_SAO_LUU'])"
                 % APP)


def sao_luu(data_dir):
    rc, out, err = chay_con(_MA_SAO_LUU, data_dir)
    duong = out.strip().splitlines()[-1] if out.strip() else None
    return {"rc": rc, "duong": duong, "out": out.strip(), "err": err.strip()}


def khoi_phuc(data_dir, duong_backup):
    rc, out, err = chay_con(_MA_KHOI_PHUC, data_dir, env_them={"G20_SAO_LUU": duong_backup})
    return {"rc": rc, "out": out.strip(), "err": err.strip()}


def db(data_dir):
    return os.path.join(data_dir, "hub.db")


def thu_muc_sao_luu(data_dir):
    return os.path.join(data_dir, "sao-luu")


def liet_ke_sao_luu(data_dir):
    d = thu_muc_sao_luu(data_dir)
    if not os.path.isdir(d):
        return []
    return sorted(os.listdir(d))


class Nen(object):
    """Một thư mục tạm cho một kịch bản. Tự dọn khi dùng xong (`with`)."""

    def __init__(self, ten):
        self.goc = chot_an_toan(tempfile.mkdtemp(prefix="g20-%s-" % ten))
        self.ten = ten

    def duong(self, *p):
        d = os.path.join(self.goc, *p)
        os.makedirs(d, exist_ok=True)
        return d

    def __enter__(self):
        return self

    def __exit__(self, *a):
        shutil.rmtree(self.goc, ignore_errors=True)
        return False


# ============================================================================
# KỊCH BẢN 1 — VÒNG TRÒN ĐẦY ĐỦ trên dữ liệu thật, khôi phục vào CSDL MỚI
# ============================================================================
def ca_vong_tron():
    """sao_luu() ở CSDL gốc → khoi_phuc() vào một thư mục dữ liệu TRỐNG.

    Đối chiếu TỪNG BẢNG cả SỐ DÒNG lẫn TỔNG TIỀN. Đây là câu hỏi "bản sao lưu có dựng lại
    được đúng dữ liệu không" — khác hẳn "sao lưu chạy không lỗi".
    """
    with Nen("vongtron") as n:
        A, B = n.duong("A"), n.duong("B")
        rc_gieo, _, err_gieo = gieo(A)
        truoc = khung_do.chup(db(A))
        rong_vt = khung_do.kiem_khong_rong(truoc, "vòng tròn")
        sl = sao_luu(A)
        sau_khi_sao_luu = khung_do.chup(db(A))
        # CSDL gốc KHÔNG được đổi vì một lượt sao lưu. Đây là phép đo rẻ nhất và hay bị bỏ:
        # một `sao_luu()` ghi vào chính CSDL nguồn thì "bản sao" đúng mà CSDL thì hỏng.
        lech_goc = khung_do.so_sanh(truoc, sau_khi_sao_luu)
        kp = khoi_phuc(B, sl["duong"] or "")
        sau = khung_do.chup(db(B))
        lech = khung_do.so_sanh(truoc, sau)
        return {
            "ten": "1. Vòng tròn đầy đủ → CSDL MỚI (từng bảng: số dòng + tổng tiền)",
            "rc_gieo": rc_gieo, "rc_sao_luu": sl["rc"], "rc_khoi_phuc": kp["rc"],
            "loi_gieo": err_gieo.strip()[-500:], "loi_khoi_phuc": kp["err"][-500:],
            "ban_sao_luu": sl["duong"],
            "so_byte_ban_sao": os.path.getsize(sl["duong"]) if sl["duong"] else None,
            "so_bang": truoc.get("so_bang"), "tong_tien_truoc": truoc.get("tong_tien_toan_kho"),
            "tong_tien_sau": sau.get("tong_tien_toan_kho"),
            "bam_truoc": truoc.get("bam_toan_kho"), "bam_sau": sau.get("bam_toan_kho"),
            "integrity_sau": sau.get("integrity_check"), "phien_ban_sau": sau.get("phien_ban"),
            "cot_tien_rong_da_khai": rong_vt,
            "lech_sau_khi_sao_luu_goc": lech_goc,
            "lech_sau_khoi_phuc": lech,
            "dat": (rc_gieo == 0 and sl["rc"] == 0 and kp["rc"] == 0
                    and not lech_goc and not lech),
            "_truoc": truoc, "_sau": sau,
        }


# ============================================================================
# KỊCH BẢN 2 — ĐỐI CHỨNG ĐƯỜNG: khôi phục NGƯỢC LẠI CHÍNH CSDL GỐC
# ============================================================================
def ca_doi_chung_duong():
    """sao_luu() gốc → ghi thêm dữ liệu → khoi_phuc() trở lại chính CSDL gốc.

    Phải ra Y NGUYÊN trạng thái lúc chụp. Đây là ca ĐỐI CHỨNG ĐƯỜNG cho mọi khẳng định
    "khôi phục khớp": nếu phép so không làm ĐỎ được thì nó không chứng minh gì. Nên trong
    cùng ca này có HAI vế:
      (a) sau khi ghi thêm, phép so PHẢI thấy lệch (chứng minh phép so còn sống);
      (b) sau khi khôi phục, phép so PHẢI hết lệch và khớp `truoc` từng bảng.
    """
    with Nen("doichung") as n:
        A = n.duong("A")
        rc_gieo, _, _ = gieo(A)
        truoc = khung_do.chup(db(A))
        khung_do.kiem_khong_rong(truoc, "đối chứng đường")
        sl = sao_luu(A)
        # Ghi thêm dữ liệu SAU mốc sao lưu — cả một tenant mới lẫn tiền.
        rc_them, out_them, err_them = chay_con(
            "import sys; sys.path.insert(0, %r); import csdl, tai_chinh, don_hang;"
            " csdl.mo();"
            " tid=csdl.ghi(\"INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,?,?)\","
            " ('sau-backup','Tenant SAU moc backup','free','2026-10-16T00:00:00+07:00')).lastrowid;"
            " u=csdl.mot('SELECT id FROM users LIMIT 1')['id'];"
            " csdl.ghi(\"INSERT INTO don_hang (tenant_id,ma_don,nguoi_gui_ten,nguoi_gui_sdt,"
            " nguoi_gui_dia_chi,nguoi_nhan_ten,nguoi_nhan_sdt,nguoi_nhan_dia_chi,hang_hoa,"
            " khoi_luong_gram,cod,gia_tri_khai,nguoi_tao,tao_luc,cap_nhat_luc)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)\","
            " (tid,'SAU-BACKUP-001','a','0','x','b','0','y','h',100,999000,999000,u,"
            " '2026-10-16T00:00:00+07:00','2026-10-16T00:00:00+07:00'));"
            " tai_chinh.ghi_but_toan(tid,'cod_du_kien',999000,'he_thong','don sau moc backup',"
            " tao_boi=u); print('them-xong')" % APP, A)
        giua = khung_do.chup(db(A))
        lech_giua = khung_do.so_sanh(truoc, giua)          # (a) phép so PHẢI đỏ
        kp = khoi_phuc(A, sl["duong"] or "")
        sau = khung_do.chup(db(A))
        lech = khung_do.so_sanh(truoc, sau)                # (b) phải hết lệch
        con_dong_sau = None
        try:
            import sqlite3
            k = sqlite3.connect(db(A))
            con_dong_sau = k.execute("SELECT COUNT(*) FROM tenants WHERE code='sau-backup'"
                                     ).fetchone()[0]
            k.close()
        except Exception as e:                             # noqa: BLE001
            con_dong_sau = "loi: %s" % e
        return {
            "ten": "2. ĐỐI CHỨNG ĐƯỜNG — khôi phục NGƯỢC LẠI chính CSDL gốc",
            "rc_gieo": rc_gieo, "rc_sao_luu": sl["rc"], "rc_them": rc_them,
            "rc_khoi_phuc": kp["rc"], "them_out": out_them.strip()[-200:],
            "loi_them": err_them.strip()[-400:], "loi_khoi_phuc": kp["err"][-400:],
            "so_lech_giua": len(lech_giua), "vi_du_lech_giua": lech_giua[:4],
            "so_lech_sau_khoi_phuc": len(lech), "lech_sau_khoi_phuc": lech,
            "tenant_sau_backup_con_lai": con_dong_sau,
            "ban_truoc_khoi_phuc": [f for f in liet_ke_sao_luu(A) if "rollback" in f],
            "dat": (rc_gieo == 0 and sl["rc"] == 0 and rc_them == 0 and kp["rc"] == 0
                    and len(lech_giua) > 0 and not lech and con_dong_sau == 0),
            "_truoc": truoc, "_sau": sau,
        }


# ============================================================================
# KỊCH BẢN 3 — SAO LƯU BỊ CẮT GIỮA ĐƯỜNG
# ============================================================================
# Cách cắt: `RLIMIT_FSIZE`. Đây là mô phỏng ĐÚNG cơ chế của sự cố thật (đĩa đầy / tác vụ bị
# giết giữa lúc ghi): tệp đích được tạo, ghi được một phần, rồi hết chỗ. Khác với "cắt tệp
# bằng tay sau khi ghi xong" ở chỗ tệp bị cắt TRONG LÚC ĐANG GHI — không có bước nào dọn dẹp.
_MA_CAT = """import os, resource, sys
sys.path.insert(0, %r)
import migrate
gioi_han = int(os.environ['G20_GIOI_HAN'])
resource.setrlimit(resource.RLIMIT_FSIZE, (gioi_han, gioi_han))
try:
    print(migrate.sao_luu())
except BaseException as e:
    print('NGOAI-LE: %%s: %%s' %% (type(e).__name__, e))
    raise
""" % APP

_MA_PHINH = """import os, sys
sys.path.insert(0, %r)
import csdl
csdl.mo()
kn = csdl.ket_noi()
n = int(sys.argv[1]) if len(sys.argv) > 1 else 400
# Dữ liệu lớn để cửa sổ ghi đủ rộng cho một lượt cắt thật.
for i in range(n):
    kn.execute("INSERT INTO wh_su_kien (carrier_account_id,event_id,payload_tho,headers_json,"
               "nhan_luc) VALUES (1,?,?,?,'2026-10-16T00:00:00+07:00')",
               ('phinh-%%d' %% i, os.urandom(200000), '{}'))
kn.commit()
print('phinh-xong', kn.execute('SELECT COUNT(*) FROM wh_su_kien').fetchone()[0])
""" % APP


_MA_SAO_LUU_CHAM = """import sys, time
sys.path.insert(0, %r)
import migrate
print('BAT-DAU', flush=True)
p = migrate.sao_luu()
print('XONG', p, flush=True)
time.sleep(30)
""" % APP


def _tep_moi_sau(thu_muc, truoc):
    """Các tệp XUẤT HIỆN THÊM trong `thu_muc` so với danh sách `truoc`."""
    return sorted(set(liet_ke_sao_luu(thu_muc) if False else _ds_truc_tiep(thu_muc)) - set(truoc))


def _ds_truc_tiep(d):
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


def ca_sao_luu_cat_giua_duong():
    """Sao lưu bị cắt GIỮA ĐƯỜNG. Ba cách cắt, ba kích thước tệp dở khác nhau:

      (a) HẾT CHỖ GHI (`RLIMIT_FSIZE`) — mô phỏng đĩa đầy đúng cơ chế: ghi được một phần rồi
          lệnh ghi trả lỗi;
      (b) BỊ GIẾT giữa lúc ghi (`SIGKILL`) — mô phỏng tác vụ bị kill / máy mất điện;
      (c) TỆP CẮT CỤT sau khi ghi xong (`truncate` 40%) — mô phỏng tệp bị hỏng khi sao chép
          sang ổ ngoài, ca hay gặp nhất khi người trực chép tay bản sao lưu đi nơi khác.

    Câu hỏi chung: người trực thấy một tệp trong `sao-luu/`. `khoi_phuc()` có NHẬN nó làm
    đường lùi không, và CSDL sau đó ra sao? `sao_luu()` đã có chốt `so_byte <= 0` — chốt đó
    nằm ở ĐƯỜNG SAO LƯU; ở ĐƯỜNG KHÔI PHỤC thì chưa ai đo.
    """
    import time
    with Nen("catgiua") as n:
        A = n.duong("A")
        rc_gieo, _, _ = gieo(A)
        rc_phinh, out_phinh, err_phinh = chay_con(_MA_PHINH, A)
        co_goc = os.path.getsize(db(A))
        truoc = khung_do.chup(db(A))

        # Đo thời gian một lượt sao lưu TRỌN VẸN trước, rồi mới chọn mức cắt — cắt mù thì
        # hoặc không cắt được gì, hoặc cắt trước cả khi tệp kịp sinh ra.
        co_san = set(_ds_truc_tiep(thu_muc_sao_luu(A)))
        t0 = time.time()
        sl_tron = sao_luu(A)
        giay_tron = time.time() - t0
        co_tron = os.path.getsize(sl_tron["duong"]) if sl_tron["duong"] else 0
        ban_tron = sl_tron["duong"]

        ket = []

        # ---------------- (a) hết chỗ ghi ----------------
        co_a = set(_ds_truc_tiep(thu_muc_sao_luu(A)))
        gioi_han = max(4096, int(co_tron * 0.4))
        rc_cat, out_cat, err_cat = chay_con(_MA_CAT, A,
                                            env_them={"G20_GIOI_HAN": str(gioi_han)})
        moi_a = _tep_moi_sau(thu_muc_sao_luu(A), co_a)
        p_a = os.path.join(thu_muc_sao_luu(A), moi_a[0]) if moi_a else None
        ket.append({"cach": "a-het-cho-ghi", "rc_luot_cat": rc_cat,
                    "out": out_cat.strip()[-200:], "err": err_cat.strip()[-200:],
                    "tep_de": moi_a, "co_tep_de": os.path.getsize(p_a) if p_a else None,
                    "tep_de_duong": p_a})

        # ---------------- (b) bị giết giữa lúc ghi ----------------
        # ====== VÌ SAO GIẾT THEO **KÍCH THƯỚC**, KHÔNG THEO **THỜI GIAN** ======
        # Bản G20 ngủ `giay_tron * f` rồi giết, với `giay_tron` đo được từ MỘT lượt sao lưu
        # trọn vẹn TRƯỚC ĐÓ. Đo lại 16/10/2026 thấy nó KHÔNG TẤT ĐỊNH: lượt đo đầu chịu chi phí
        # khởi động tiến trình + đệm đĩa, các lượt sau nhanh hơn hẳn, nên ngủ `0.4 * giay_tron`
        # có thể đã MUỘN hơn lúc ghi xong — cả ba lượt giết cho ra tệp ĐỦ BYTE, chốt chống
        # phép-đo-rỗng `so_cach_tep_de_that_su_cut >= 3` báo **2** và cả kịch bản đỏ vì một lý do
        # không liên quan gì tới sản phẩm.
        # Nay: GIỠ TỚI KHI TỆP ĐỦ LỚN rồi mới giết. Cùng một mốc kích thước trên mọi máy, mọi
        # tốc độ đĩa. Lượt nào giết quá muộn (tệp đã đủ byte) được đánh dấu `cat_truot` và
        # KHÔNG tính là tệp dở — khai ra, không giấu.
        import signal
        import subprocess as sp
        for ti_le in (0.4, 0.7, 0.9):
            co_b = set(_ds_truc_tiep(thu_muc_sao_luu(A)))
            pr = sp.Popen([PY, "-c", _MA_SAO_LUU_CHAM], cwd=GOC,
                          env=moi_truong(A), stdout=sp.PIPE, stderr=sp.PIPE, text=True)
            moc = max(4096, int(co_tron * ti_le))
            t0, da_giet, co_luc_giet = time.time(), False, 0
            while time.time() - t0 < max(10.0, giay_tron * 20):
                moi = _tep_moi_sau(thu_muc_sao_luu(A), co_b)
                if moi:
                    try:
                        co_luc_giet = os.path.getsize(
                            os.path.join(thu_muc_sao_luu(A), moi[0]))
                    except OSError:
                        co_luc_giet = 0
                    if co_luc_giet >= moc:
                        break
                if pr.poll() is not None:
                    break
                time.sleep(0.002)
            if pr.poll() is None:
                pr.send_signal(signal.SIGKILL)
                da_giet = True
            pr.wait()
            moi_b = _tep_moi_sau(thu_muc_sao_luu(A), co_b)
            p_b = os.path.join(thu_muc_sao_luu(A), moi_b[0]) if moi_b else None
            co_b_that = os.path.getsize(p_b) if p_b else None
            ket.append({"cach": "b-bi-giet-%.0f%%" % (ti_le * 100.0),
                        "moc_giet_byte": moc, "co_luc_giet": co_luc_giet,
                        "giay_cho": round(time.time() - t0, 3),
                        "con_song_luc_giet": da_giet,
                        "ma_thoat": pr.returncode, "tep_de": moi_b,
                        "co_tep_de": co_b_that,
                        # Giết quá muộn ⇒ tệp đã ghi xong ⇒ ĐÂY KHÔNG PHẢI ca hỏng.
                        "cat_truot": co_b_that is not None and co_b_that >= co_tron,
                        "tep_de_duong": p_b})

        # ---------------- (c) tệp cắt cụt sau khi ghi xong ----------------
        p_c = os.path.join(n.goc, "ban-cat-cut.db")
        shutil.copy2(ban_tron, p_c)
        co_day = os.path.getsize(p_c)
        with open(p_c, "r+b") as f:
            f.truncate(max(4096, int(co_day * 0.4)))
        ket.append({"cach": "c-cat-cut-40%", "co_day": co_day,
                    "co_tep_de": os.path.getsize(p_c), "tep_de_duong": p_c})

        # -------- thử `khoi_phuc()` với TỪNG tệp dở, mỗi lượt vào một thư mục trống --------
        for i, k in enumerate(ket):
            k["chup_tep_de"] = khung_do.chup(k["tep_de_duong"]) if k["tep_de_duong"] else None
            B = n.duong("B%d" % i)
            kp = khoi_phuc(B, k["tep_de_duong"] or "")
            sau = khung_do.chup(db(B))
            k["rc_khoi_phuc"] = kp["rc"]
            k["err_khoi_phuc"] = kp["err"][-200:]
            k["out_khoi_phuc"] = kp["out"][-200:]
            k["khoi_phuc_NHAN"] = kp["rc"] == 0
            k["csdl_sau"] = {"so_byte": sau.get("so_byte"), "so_bang": sau.get("so_bang"),
                             "integrity": sau.get("integrity_check"), "loi": sau.get("loi"),
                             "tong_tien": sau.get("tong_tien_toan_kho")}
            k["cut_that"] = (k["co_tep_de"] is None or k["co_tep_de"] < co_tron
                             or (k.get("chup_tep_de") or {}).get("integrity_check") != "ok")

        # -------- ĐỐI CHỨNG ĐƯỜNG: tệp TRỌN VẸN phải khôi phục ĐẠT và khớp gốc --------
        Bc = n.duong("B-tron")
        kp_c2 = khoi_phuc(Bc, ban_tron)
        chup_c2 = khung_do.chup(db(Bc))
        lech_c2 = khung_do.so_sanh(truoc, chup_c2)

        return {
            "ten": "3. SAO LƯU BỊ CẮT GIỮA ĐƯỜNG — ba cách cắt, tệp dở có bị nhận không",
            "rc_gieo": rc_gieo, "rc_phinh": rc_phinh, "phinh_out": out_phinh.strip()[-120:],
            "loi_phinh": err_phinh.strip()[-300:],
            "co_csdl_goc": co_goc, "giay_sao_luu_tron": round(giay_tron, 3),
            "co_ban_sao_tron": co_tron, "gioi_han_cat_a": gioi_han,
            "so_bang_goc": truoc.get("so_bang"), "tong_tien_goc": truoc.get("tong_tien_toan_kho"),
            "cac_cach_cat": ket,
            "so_cach_bi_NHAN": sum(1 for k in ket if k["khoi_phuc_NHAN"]),
            # ====== ĐẾM "LƯỢT CẮT THẬT SỰ" — VÀ VÌ SAO PHẢI ĐẾM CẢ LƯỢT KHÔNG ĐỂ LẠI TỆP ======
            # Đo được 16/10/2026: trên một bản vá fail-closed, lượt cắt vì hết chỗ ghi DỌN tệp
            # tạm nên `co_tep_de` là `None`. Nếu chỉ đếm `co_tep_de < co_tron` thì chốt chống
            # phép-đo-rỗng (cần >= 3) báo "kịch bản không chạy" — một ĐỎ GIẢ, và nó trừng phạt
            # đúng cái hành vi tốt lên. Nên `cut_that` = lượt cắt KHÔNG sinh ra một bản sao lưu
            # TRỌN VẸN: hoặc không để lại tệp nào, hoặc để lại tệp ngắn hơn / đọc không được.
            "so_cach_tep_de_that_su_cut": sum(
                1 for k in ket if k["co_tep_de"] is None or k["co_tep_de"] < co_tron),
            "so_luot_cat_khong_de_lai_tep": sum(1 for k in ket if k["co_tep_de"] is None),
            "so_luot_cat_truot": sum(1 for k in ket if k.get("cat_truot")),
            "doi_chung_duong": {"rc_khoi_phuc": kp_c2["rc"], "so_lech": len(lech_c2),
                                "tong_tien": chup_c2.get("tong_tien_toan_kho")},
            "doi_chung_duong_dat": kp_c2["rc"] == 0 and not lech_c2,
            # "dat" ở đây nghĩa là KỊCH BẢN ĐO chạy đúng: gieo được, làm phình được, có ít
            # nhất BA tệp dở THẬT SỰ ngắn hơn bản trọn vẹn, và ĐỐI CHỨNG ĐƯỜNG (tệp lành)
            # khôi phục khớp gốc. Hai lượt SIGKILL ở 70%/90% ra tệp ĐỦ BYTE là chuyện bình
            # thường — giết quá muộn — nên chúng KHÔNG vào điều kiện đạt; khai ra, không giấu.
            "dat": (rc_gieo == 0 and rc_phinh == 0 and len(ket) == 5
                    and sum(1 for k in ket if k["co_tep_de"] is None
                            or k["co_tep_de"] < co_tron) >= 3
                    and kp_c2["rc"] == 0 and not lech_c2),
        }


# ============================================================================
# KỊCH BẢN 4 — TỆP SAO LƯU BỊ SỬA 1 BYTE
# ============================================================================
def _lat_mot_byte(duong, vi_tri, gia_tri_moi):
    with open(duong, "r+b") as f:
        f.seek(vi_tri)
        cu = f.read(1)
        f.seek(vi_tri)
        f.write(bytes([gia_tri_moi]))
    return cu[0]


def ca_sua_mot_byte():
    """Sửa ĐÚNG MỘT byte trong tệp sao lưu, ở BỐN chỗ khác nhau, rồi khôi phục từ mỗi bản.

      (a) 25% · (b) 50% · (c) 75% tệp — vẫn là SQLite hợp lệ về HÌNH THỨC;
      (d) byte 0 — magic "SQLite format 3" của phần đầu tệp, tệp KHÔNG còn là SQLite.

    Câu hỏi: `khoi_phuc()` có phát hiện không, và nếu không thì CSDL sau khôi phục ra sao.
    `khoi_phuc()` hiện chỉ `shutil.copy2` — dự đoán là nó nhận tất. Dự đoán đó phải được ĐO.

    Vì sao BỐN chỗ chứ không một: một byte lật vào vùng trang TRỐNG thì không đổi gì cả, và
    lượt đo sẽ kết luận "sửa 1 byte vô hại" — một kết luận SAI rút ra từ một phép đo may rủi.
    Đo bốn chỗ rồi báo CẢ BỐN, kể cả chỗ không đổi gì.
    """
    import sqlite3
    with Nen("suabyte") as n:
        A = n.duong("A")
        rc_gieo, _, _ = gieo(A)
        truoc = khung_do.chup(db(A))
        sl = sao_luu(A)
        goc_byte = os.path.getsize(sl["duong"])

        ket_qua = []
        # (e) TRƯỚC TIÊN: một byte nằm trong TRANG DỮ LIỆU ĐANG DÙNG.
        # Bốn chỗ theo tỉ lệ ở dưới là may rủi: lật vào vùng trống thì không đổi gì, và lượt
        # đo sẽ kết luận "sửa 1 byte vô hại" — kết luận SAI rút từ phép đo may rủi. Nên phải
        # có một ca CHẮC CHẮN trúng dữ liệu: tìm mã đơn `SHOP-A-002` trong tệp rồi lật byte
        # đầu của nó. Đó là chữ trong `don_hang.ma_don`, tức chắc chắn nằm trong trang có dữ liệu.
        vi_tri_e = None
        with open(sl["duong"], "rb") as f:
            tho = f.read()
        tim = tho.find(b"SHOP-A-002")
        if tim >= 0:
            vi_tri_e = tim
        if vi_tri_e is not None:
            p = "%s.%s" % (sl["duong"], "e-trang-dung")
            shutil.copy2(sl["duong"], p)
            cu = _lat_mot_byte(p, vi_tri_e, ord("X"))
            own = khung_do.integrity_cua_tep(p)
            B = n.duong("B-e")
            kp = khoi_phuc(B, p)
            chup = khung_do.chup(db(B))
            lech = khung_do.so_sanh(truoc, chup)
            ket_qua.append({
                "nhan": "e-trang-dung", "vi_tri": vi_tri_e, "byte_cu": cu, "byte_moi": ord("X"),
                "sqlite_tu_bao": own,
                "rc_khoi_phuc": kp["rc"], "err_khoi_phuc": kp["err"][-200:],
                "integrity": chup.get("integrity_check"), "loi": chup.get("loi"),
                "so_bang": chup.get("so_bang"), "tong_tien": chup.get("tong_tien_toan_kho"),
                "bam_khop_goc": chup.get("bam_toan_kho") == truoc.get("bam_toan_kho"),
                "so_lech": len(lech), "vi_du_lech": lech[:3],
                "khoi_phuc_NHAN": kp["rc"] == 0,
            })
        for nhan, vi_tri, gia_tri in (("a-25%", goc_byte // 4, 0xFF),
                                      ("b-50%", goc_byte // 2, 0xFF),
                                      ("c-75%", (goc_byte * 3) // 4, 0xFF),
                                      ("d-byte0", 0, 0x00)):
            p = "%s.%s" % (sl["duong"], nhan)
            shutil.copy2(sl["duong"], p)
            cu = _lat_mot_byte(p, vi_tri, gia_tri)
            # ĐO ĐỘC LẬP trước: SQLite có tự thấy hỏng không? Nếu nó thấy, hệ CÓ SẴN cớ để
            # kiểm — và việc `khoi_phuc()` không kiểm là một lựa chọn, không phải bất khả.
            try:
                k = sqlite3.connect(p)
                own = k.execute("PRAGMA integrity_check").fetchone()[0]
                k.close()
            except sqlite3.Error as e:
                own = "NGOAI-LE %s: %s" % (type(e).__name__, e)
            B = n.duong("B-" + nhan)
            kp = khoi_phuc(B, p)
            chup = khung_do.chup(db(B))
            lech = khung_do.so_sanh(truoc, chup)
            ket_qua.append({
                "nhan": nhan, "vi_tri": vi_tri, "byte_cu": cu, "byte_moi": gia_tri,
                "sqlite_tu_bao": own,
                "rc_khoi_phuc": kp["rc"], "err_khoi_phuc": kp["err"][-200:],
                "integrity": chup.get("integrity_check"), "loi": chup.get("loi"),
                "so_bang": chup.get("so_bang"), "tong_tien": chup.get("tong_tien_toan_kho"),
                "bam_khop_goc": chup.get("bam_toan_kho") == truoc.get("bam_toan_kho"),
                "so_lech": len(lech), "vi_du_lech": lech[:3],
                "khoi_phuc_NHAN": kp["rc"] == 0,
            })

        # ĐỐI CHỨNG ĐƯỜNG: cùng đường đó, nhưng tệp KHÔNG bị sửa → phải khôi phục ĐẠT và khớp.
        Bc = n.duong("B-sach")
        kp_c = khoi_phuc(Bc, sl["duong"])
        chup_c = khung_do.chup(db(Bc))
        lech_c = khung_do.so_sanh(truoc, chup_c)
        return {
            "ten": "4. TỆP SAO LƯU BỊ SỬA 1 BYTE — có phát hiện được không",
            "rc_gieo": rc_gieo, "rc_sao_luu": sl["rc"], "so_byte": goc_byte,
            "so_byte_truoc_bam": truoc.get("bam_toan_kho"),
            "cac_lan_sua": ket_qua,
            "so_lan_khoi_phuc_NHAN_tat_ca": sum(1 for k in ket_qua if k["khoi_phuc_NHAN"]),
            "byte_trang_dung_bi_phat_hien": (
                None if not ket_qua or ket_qua[0]["nhan"] != "e-trang-dung"
                else not ket_qua[0]["bam_khop_goc"]),
            "doi_chung_duong": {"rc_khoi_phuc": kp_c["rc"], "so_lech": len(lech_c),
                                "lech": lech_c[:3]},
            "doi_chung_duong_dat": kp_c["rc"] == 0 and not lech_c,
            "dat": (rc_gieo == 0 and sl["rc"] == 0 and kp_c["rc"] == 0 and not lech_c),
        }


# ============================================================================
# KỊCH BẢN 5 — KHÔI PHỤC VÀO CSDL ĐÃ CÓ DỮ LIỆU
# ============================================================================
def ca_khoi_phuc_de_len_csdl_dang_chay():
    """Khôi phục ĐÈ lên một CSDL đang có dữ liệu MỚI HƠN bản sao lưu.

    Ba câu hỏi, cả ba đều là câu hỏi vận hành:
      (a) dữ liệu mới hơn có mất không (phải mất — đó là ý nghĩa của khôi phục) và có ĐƯỢC
          CẤT đi không (bản `hub-truoc-rollback-*.db`)?
      (b) bản cất đó có MỞ ĐƯỢC và có đúng dữ liệu vừa mất không?
      (c) hai lượt khôi phục trong CÙNG MỘT GIÂY thì còn mấy bản cất? Tên bản cất đặt theo
          GIÂY (`%Y%m%d-%H%M%S`) — đúng khuôn mà `sao_luu()` đã bị bắt lỗi và đã sửa; ở
          `khoi_phuc()` chưa ai đo.
    """
    import sqlite3
    with Nen("delencsdl") as n:
        A = n.duong("A")
        rc_gieo, _, _ = gieo(A)
        truoc = khung_do.chup(db(A))
        sl = sao_luu(A)
        # Ghi thêm dữ liệu (mốc "mới hơn bản sao lưu").
        rc_them, _, err_them = chay_con(
            "import sys; sys.path.insert(0, %r); import csdl, tai_chinh; csdl.mo();"
            " csdl.ghi(\"INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,?,?)\","
            " ('moi-hon','Tenant MOI HON ban sao luu','free','2026-10-16T00:00:00+07:00'));"
            " print('ok')" % APP, A)
        day = khung_do.chup(db(A))
        truoc_kp = liet_ke_sao_luu(A)

        kp1 = khoi_phuc(A, sl["duong"])
        sau1 = khung_do.chup(db(A))
        giua = liet_ke_sao_luu(A)
        # CHỈ đếm tệp `.db`. Đo được 16/10/2026: một bản vá fail-closed cất bản hiện tại KÈM
        # `-wal`/`-shm` của nó, nên bộ lọc `"rollback" in f` đếm luôn hai tệp phụ và trả về 3
        # thay vì 1 — một ĐỎ GIẢ do chính phép đếm, không phải do sản phẩm.
        ban_cat = [f for f in giua if "rollback" in f and f.endswith(".db")]
        # (b) bản cất có mở được và có đúng dữ liệu vừa mất không?
        noi_dung_ban_cat = None
        if ban_cat:
            p = os.path.join(thu_muc_sao_luu(A), sorted(ban_cat)[-1])
            c = khung_do.chup(p)
            noi_dung_ban_cat = {"integrity": c.get("integrity_check"),
                                "so_bang": c.get("so_bang"),
                                "bam": c.get("bam_toan_kho"),
                                "khop_dung_luc_chup_day": c.get("bam_toan_kho") == day.get("bam_toan_kho")}

        # (c) hai lượt khôi phục LIÊN TIẾP trong cùng một giây
        ban_cat_1 = sorted(ban_cat)[-1] if ban_cat else None
        bam_cat_1 = None
        if ban_cat_1:
            bam_cat_1 = khung_do.chup(os.path.join(thu_muc_sao_luu(A), ban_cat_1)).get("bam_toan_kho")
        kp2 = khoi_phuc(A, sl["duong"])
        kp3 = khoi_phuc(A, sl["duong"])
        cuoi = liet_ke_sao_luu(A)
        ban_cat_cuoi = [f for f in cuoi if "rollback" in f and f.endswith(".db")]
        # Câu hỏi quyết định: bản cất của lượt ĐẦU (thứ duy nhất chứa dữ liệu vừa mất) còn
        # nguyên không, hay đã bị lượt SAU ghi đè im lặng?
        bam_cat_cuoi = None
        if ban_cat_cuoi:
            bam_cat_cuoi = khung_do.chup(
                os.path.join(thu_muc_sao_luu(A), sorted(ban_cat_cuoi)[-1])).get("bam_toan_kho")
        # ====== VÌ SAO PHẢI BĂM **MỌI** BẢN CẤT, KHÔNG CHỈ BẢN CUỐI ======
        # Đo được 16/10/2026: sau khi `khoi_phuc()` được vá cho tên-bản-cất-không-đè, ba lượt
        # khôi phục để lại BA tệp `hub-truc-rollback-*`. Bản GIỮ DỮ LIỆU VỪA MẤT là bản của
        # lượt ĐẦU; `sorted(...)[-1]` lại chọn bản của lượt CUỐI. Nếu chỉ băm bản cuối thì một
        # bản vá ĐÚNG vẫn bị đọc thành "bản cất đã bị ghi đè" — một cái ĐỎ GIẢ. Nên phải hỏi
        # đúng câu hỏi vận hành: CÒN ÍT NHẤT MỘT bản cất giữ được dữ liệu lúc chụp hay không.
        bam_moi_ban_cat_cuoi = {}
        for _f in ban_cat_cuoi:
            bam_moi_ban_cat_cuoi[_f] = khung_do.chup(
                os.path.join(thu_muc_sao_luu(A), _f)).get("bam_toan_kho")
        so_ban_cat_giu_du_lieu_goc = sum(
            1 for _b in bam_moi_ban_cat_cuoi.values() if _b == day.get("bam_toan_kho"))
        return {
            "ten": "5. KHÔI PHỤC ĐÈ lên CSDL đã có dữ liệu — bản cất có an toàn không",
            "rc_gieo": rc_gieo, "rc_sao_luu": sl["rc"], "rc_them": rc_them,
            "loi_them": err_them.strip()[-300:],
            "rc_kp1": kp1["rc"], "rc_kp2": kp2["rc"], "rc_kp3": kp3["rc"],
            "sao_luu_truoc_kp": truoc_kp, "sao_luu_sau_kp1": giua, "sao_luu_sau_3_lan_kp": cuoi,
            "so_ban_cat_sau_1_lan": len(ban_cat),
            "so_ban_cat_sau_3_lan": len(ban_cat_cuoi),
            "ban_cat": ban_cat_cuoi,
            "noi_dung_ban_cat": noi_dung_ban_cat,
            "bam_ban_cat_sau_1_lan": bam_cat_1,
            "bam_ban_cat_sau_3_lan": bam_cat_cuoi,
            "bam_moi_ban_cat_cuoi": bam_moi_ban_cat_cuoi,
            "so_ban_cat_giu_du_lieu_goc": so_ban_cat_giu_du_lieu_goc,
            "bam_du_lieu_luc_chup_day": day.get("bam_toan_kho"),
            "ban_cat_con_giu_duoc_du_lieu_goc": bam_cat_cuoi == day.get("bam_toan_kho"),
            "lech_truoc_kp1": khung_do.so_sanh(truoc, sau1),
            "dat": (rc_gieo == 0 and rc_them == 0 and kp1["rc"] == 0 and kp2["rc"] == 0
                    and kp3["rc"] == 0),
        }


# ============================================================================
# KỊCH BẢN 6 — KHÔI PHỤC BẢN SAO LƯU CÓ PHIÊN BẢN SCHEMA THẤP HƠN
# ============================================================================
_MA_DUNG_V6 = """import sys
sys.path.insert(0, %r)
import csdl, migrate, cau_hinh
csdl.mo()
kn = csdl.ket_noi(tuong_minh=True)
kn.execute('BEGIN IMMEDIATE')
for ham, pb in ((migrate.nang_len_v2, 2), (migrate.nang_len_v3, 3), (migrate.nang_len_v4, 4),
                (migrate.nang_len_v5, 5), (migrate.nang_len_v6, 6)):
    ham(kn)
kn.execute("INSERT OR REPLACE INTO schema_version (phien_ban, ap_dung_luc, ghi_chu)"
           " VALUES (?,?,'dung thu cong o v6 cho phep do G20')", (6, '2026-10-16'))
kn.execute('COMMIT')
kn.close()
print('phien-ban:', csdl.phien_ban_hien_tai())
""" % APP


def ca_khoi_phuc_schema_thap_hon():
    """Khôi phục một bản sao lưu ở schema v6 lên một CSDL đang ở v9.

    Không có gì sai khi khôi phục bản cũ — đó chính là việc của khôi phục. Câu hỏi là: hệ có
    NÓI RA rằng schema vừa TỤT không? Một CSDL tụt phiên bản mà không ai báo thì lượt ghi đầu
    tiên sẽ hỏng ở một cột không tồn tại (hoặc tệ hơn: chạy theo đường lùi và trả kết quả của
    schema cũ — `migrate.chay()` viết rõ đúng kịch bản đó).
    """
    import sqlite3
    with Nen("schemav6") as n:
        C = n.duong("C")
        rc_v6, out_v6, err_v6 = chay_con(_MA_DUNG_V6, C)
        # Gieo dữ liệu lên CSDL v6 đó (dùng chính gieo.py — nó tự chạy migrate.chay() lên đích
        # của MÃ NGUỒN, nên KHÔNG dùng được ở đây; thay bằng dữ liệu tối thiểu qua csdl.ghi).
        rc_seed6, out_seed6, err_seed6 = chay_con(
            "import sys; sys.path.insert(0, %r); import csdl; csdl.mo();"
            " csdl.ghi(\"INSERT INTO tenants (code,ten,goi_id,tao_luc) VALUES (?,?,?,?)\","
            " ('v6-a','Tenant tren schema v6','free','2026-10-16T00:00:00+07:00'));"
            " print('seed-v6-ok')" % APP, C)
        sl_v6 = sao_luu(C)
        chup_v6 = khung_do.chup(db(C))

        A = n.duong("A")
        rc_gieo, _, _ = gieo(A)
        truoc = khung_do.chup(db(A))
        kp = khoi_phuc(A, sl_v6["duong"] or "")
        sau = khung_do.chup(db(A))
        # CSDL đích có tự báo không? Đọc thẳng `schema_version` bằng sqlite3 trần.
        pb_sau = None
        try:
            k = sqlite3.connect(db(A))
            pb_sau = k.execute("SELECT COALESCE(MAX(phien_ban),0) FROM schema_version").fetchone()[0]
            k.close()
        except Exception as e:                                  # noqa: BLE001
            pb_sau = "loi: %s" % e
        # Và một lượt ghi vào cột chỉ có ở schema MỚI: hệ có từ chối ỒN ÀO không?
        rc_ghi, out_ghi, err_ghi = chay_con(
            "import sys; sys.path.insert(0, %r); import csdl; csdl.mo();"
            " print('cot:', [r[1] for r in csdl.mo().execute('PRAGMA table_info(don_hang)')]);"
            " print('phien-ban-nhin-tu-ma:', csdl.phien_ban_hien_tai())"
            % APP, A)
        # ĐƯỜNG RA: sau khi tụt về v6, `migrate.chay()` có nâng lại được lên v9 không, và dữ
        # liệu của bản v6 có sống sót qua lượt nâng đó không. Đây là câu hỏi tiếp theo người
        # trực sẽ hỏi ngay; đo luôn thì báo cáo mới nói được "tụt rồi thì làm gì".
        rc_nang, out_nang, err_nang = chay_con(
            "import sys; sys.path.insert(0, %r); import csdl, migrate;"
            " kq = migrate.chay(im_lang=True); csdl.dong();"
            " import json; print(json.dumps(kq, ensure_ascii=False, default=str))"
            % APP, A)
        sau_nang = khung_do.chup(db(A))
        return {
            "ten": "6. KHÔI PHỤC bản sao lưu SCHEMA THẤP HƠN (v6 đè lên v9)",
            "rc_dung_v6": rc_v6, "out_dung_v6": out_v6.strip()[-200:], "loi_v6": err_v6[-300:],
            "rc_seed_v6": rc_seed6, "out_seed6": out_seed6.strip()[-120:], "loi_seed6": err_seed6[-300:],
            "rc_sao_luu_v6": sl_v6["rc"], "ban_sao_luu_v6": sl_v6["duong"],
            "phien_ban_v6": chup_v6.get("phien_ban"), "so_bang_v6": chup_v6.get("so_bang"),
            # `integrity` + số bảng của CHÍNH bản sao lưu v6. Cần để phân biệt hai câu rất khác
            # nhau: "bị từ chối vì TỤT PHIÊN BẢN" và "bị từ chối vì TỆP HỎNG". Thiếu nó thì một
            # lời từ chối ĐÚNG vẫn có thể bị đọc thành một lời từ chối SAI.
            "integrity_ban_sao_luu_v6": khung_do.integrity_cua_tep(sl_v6["duong"])
            if sl_v6["duong"] else None,
            "so_bang_ban_sao_luu_v6": khung_do.chup(sl_v6["duong"]).get("so_bang")
            if sl_v6["duong"] else None,
            "rc_gieo_v9": rc_gieo, "phien_ban_v9_truoc": truoc.get("phien_ban"),
            "so_bang_v9_truoc": truoc.get("so_bang"),
            "rc_khoi_phuc": kp["rc"], "out_khoi_phuc": kp["out"][-300:],
            # STDERR là chỗ `SystemExit` in thông báo TỪ CHỐI. Thiếu nó thì một bản vá
            # fail-closed (từ chối ĐÚNG cách) trông y hệt một lượt im lặng — đo sai.
            "err_khoi_phuc": kp["err"][-500:],
            "phien_ban_sau_khoi_phuc": pb_sau, "chup_sau": {
                "phien_ban": sau.get("phien_ban"), "so_bang": sau.get("so_bang"),
                "bam": sau.get("bam_toan_kho"), "integrity": sau.get("integrity_check"),
                "tong_tien": sau.get("tong_tien_toan_kho")},
            "tong_tien_v6": chup_v6.get("tong_tien_toan_kho"),
            "tong_tien_v9_truoc": truoc.get("tong_tien_toan_kho"),
            "bam_v6": chup_v6.get("bam_toan_kho"),
            "khoi_phuc_ra_dung_v6": sau.get("bam_toan_kho") == chup_v6.get("bam_toan_kho"),
            "rc_ghi_tren_v6": rc_ghi, "out_ghi": out_ghi.strip()[-400:], "loi_ghi": err_ghi[-300:],
            "rc_nang_lai": rc_nang, "out_nang_lai": out_nang.strip()[-300:],
            "loi_nang_lai": err_nang.strip()[-300:],
            "chup_sau_khi_nang": {"phien_ban": sau_nang.get("phien_ban"),
                                  "so_bang": sau_nang.get("so_bang"),
                                  "tong_tien": sau_nang.get("tong_tien_toan_kho"),
                                  "integrity": sau_nang.get("integrity_check")},
            "du_lieu_v6_con_nguyen_sau_nang": sau_nang.get("bam_toan_kho") == chup_v6.get("bam_toan_kho"),
            "dat": (rc_v6 == 0 and rc_seed6 == 0 and sl_v6["rc"] == 0 and rc_gieo == 0
                    and kp["rc"] == 0),
            "_lech": khung_do.so_sanh(chup_v6, sau),
        }


# ============================================================================
# KỊCH BẢN 7 — TỆP KHÔI PHỤC KHÔNG PHẢI SQLITE (nhầm bản dump PostgreSQL)
# ============================================================================
def ca_khoi_phuc_nham_ban_dump_pg():
    """Đưa `khoi_phuc()` một tệp KHÔNG phải SQLite — đúng thứ một bản `pg_dump -Fc` sinh ra.

    Kịch bản vận hành: người trực có hai loại tệp trong cùng thư mục (`hub-*.db` của SQLite và
    `*.dump` của PostgreSQL), gõ nhầm một cái. `khoi_phuc()` không hỏi tệp là gì.
    """
    import sqlite3
    with Nen("nhamdump") as n:
        A = n.duong("A")
        rc_gieo, _, _ = gieo(A)
        truoc = khung_do.chup(db(A))
        # Một tệp GIẢ có phần đầu đúng như pg_dump -Fc (magic "PGDMP"), đủ để phân biệt rõ ràng.
        gia = os.path.join(n.goc, "sao_luu_pg.dump")
        with open(gia, "wb") as f:
            f.write(b"PGDMP\x01\x0f\x00" + os.urandom(65536))
        # ĐỐI CHỨNG ĐƯỜNG lấy TRƯỚC khi phá: một bản sao lưu SQLITE THẬT của cùng CSDL đó.
        sl_dung = sao_luu(A)
        B_dung = n.duong("B-dung")
        kp_dung = khoi_phuc(B_dung, sl_dung["duong"] or "")
        chup_dung = khung_do.chup(db(B_dung))
        lech_dung = khung_do.so_sanh(truoc, chup_dung)

        kp = khoi_phuc(A, gia)
        sau = khung_do.chup(db(A))
        return {
            "ten": "7. KHÔI PHỤC NHẦM tệp KHÔNG phải SQLite (bản dump PostgreSQL)",
            "rc_gieo": rc_gieo, "rc_sao_luu_dung": sl_dung["rc"],
            "rc_khoi_phuc_nham": kp["rc"],
            "out_khoi_phuc_nham": kp["out"][-300:], "err_khoi_phuc_nham": kp["err"][-300:],
            "khoi_phuc_NHAN_tep_la": kp["rc"] == 0,
            "csdl_sau_khi_nham": {"integrity": sau.get("integrity_check"),
                                  "loi": sau.get("loi"), "so_bang": sau.get("so_bang"),
                                  "so_byte": sau.get("so_byte")},
            "bam_truoc": truoc.get("bam_toan_kho"),
            "rc_khoi_phuc_dung": kp_dung["rc"], "so_lech_duong_dung": len(lech_dung),
            "lech_duong_dung": lech_dung[:3],
            "doi_chung_duong_dat": kp_dung["rc"] == 0 and not lech_dung,
            "so_byte_csdl_truoc": truoc.get("so_byte"), "so_byte_csdl_sau": sau.get("so_byte"),
            "dat": (rc_gieo == 0 and sl_dung["rc"] == 0 and kp_dung["rc"] == 0 and not lech_dung),
        }


# ============================================================================
# KỊCH BẢN 8 — KHÔI PHỤC CSDL MÀ THIẾU KHÓA NỘI BỘ
# ============================================================================
# `sao_luu()` chỉ sao lưu `hub.db`. Khóa mã hóa credentials nằm ở tệp KHÁC trong cùng thư mục
# dữ liệu (`cau_hinh.DUONG_DAN_KHOA`). Câu hỏi: một bản sao lưu CSDL có TỰ ĐỦ không?
#
# Đây không phải câu hỏi lý thuyết. Số dòng khớp, tổng tiền khớp, `integrity_check = ok` — tất
# cả đều ĐẠT — mà credentials thì không giải mã được. Nếu hệ chỉ báo lúc gọi hãng thì hỏng đó
# nằm im cho tới lượt gọi thật đầu tiên, tức đúng lúc không được phép hỏng.
_MA_GIAI_MA = """import sys
sys.path.insert(0, %r)
import bao_mat
import csdl
csdl.mo()
r = csdl.mot("SELECT id,tenant_id,hang,credentials_ma_hoa,webhook_ma,webhook_secret_ma_hoa"
             " FROM carrier_accounts ORDER BY id LIMIT 1")
if r is None:
    print("KHONG-CO-BAN-GHI")
    raise SystemExit(0)
try:
    c = bao_mat.giai_ma_cred(r["credentials_ma_hoa"], r["tenant_id"], r["hang"])
    print("CRED-DAT", sorted(c))
except Exception as e:
    print("CRED-HONG", type(e).__name__, str(e)[:200])
try:
    w = bao_mat.giai_ma_wh(r["webhook_secret_ma_hoa"], r["webhook_ma"])
    print("WH-DAT", len(w))
except Exception as e:
    print("WH-HONG", type(e).__name__, str(e)[:200])
""" % APP


def ca_khoa_khong_di_kem():
    """Sao lưu CSDL → khôi phục vào thư mục MỚI (không có khóa) → credentials còn đọc được không.

    `khoi_phuc()` chỉ chép `hub.db`. Không có bước nào kiểm khóa có đi kèm hay không, và không
    có bước nào báo. Đo cả hai vế: bản gốc (có khóa) phải giải mã ĐẠT — nếu không thì phép đo
    vô nghĩa; bản khôi phục (thiếu khóa) mới là vế cần biết.
    """
    with Nen("khoa") as n:
        A, B = n.duong("A"), n.duong("B")
        rc_gieo, _, _ = gieo(A)
        truoc = khung_do.chup(db(A))
        sl = sao_luu(A)
        kp = khoi_phuc(B, sl["duong"] or "")
        sau = khung_do.chup(db(B))
        lech = khung_do.so_sanh(truoc, sau)

        tep_b_truoc = sorted(os.listdir(B))
        rc_a, out_a, err_a = chay_con(_MA_GIAI_MA, A)
        rc_b, out_b, err_b = chay_con(_MA_GIAI_MA, B)
        tep_a = sorted(os.listdir(A))
        tep_b = sorted(os.listdir(B))
        return {
            "ten": "8. KHÔI PHỤC CSDL MÀ THIẾU KHÓA NỘI BỘ — credentials còn đọc được không",
            "rc_gieo": rc_gieo, "rc_sao_luu": sl["rc"], "rc_khoi_phuc": kp["rc"],
            "so_lech_csdl": len(lech), "lech": lech[:3],
            "so_bang_khoi_phuc": sau.get("so_bang"),
            "tong_tien_khoi_phuc": sau.get("tong_tien_toan_kho"),
            "integrity_khoi_phuc": sau.get("integrity_check"),
            "tep_thu_muc_goc": tep_a, "tep_thu_muc_khoi_phuc": tep_b,
            "co_khoa_o_goc": any("khoa" in t for t in tep_a),
            "co_khoa_o_ban_khoi_phuc": any("khoa" in t for t in tep_b),
            "rc_giai_ma_o_goc": rc_a, "out_giai_ma_o_goc": out_a.strip()[-300:],
            "err_giai_ma_o_goc": err_a.strip()[-200:],
            "rc_giai_ma_o_khoi_phuc": rc_b, "out_giai_ma_o_khoi_phuc": out_b.strip()[-300:],
            "err_giai_ma_o_khoi_phuc": err_b.strip()[-200:],
            "goc_giai_ma_dat": "CRED-DAT" in out_a,
            "khoi_phuc_giai_ma_dat": "CRED-DAT" in out_b,
            "tep_khoi_phuc_truoc_khi_giai_ma": tep_b_truoc,
            # Vế ĐỐI CHỨNG cho chất lượng hỏng: hệ có TỰ SINH khóa mới rồi giải mã ra rác
            # không, hay từ chối ỒN ÀO? Tự sinh khóa mới là ca tệ nhất — credentials cũ thành
            # rác vĩnh viễn mà không ai biết.
            "tu_sinh_khoa_moi_khi_thieu": sorted(set(tep_b) - set(tep_b_truoc)),
            "dat": (rc_gieo == 0 and sl["rc"] == 0 and kp["rc"] == 0 and not lech
                    and "CRED-DAT" in out_a),
        }
