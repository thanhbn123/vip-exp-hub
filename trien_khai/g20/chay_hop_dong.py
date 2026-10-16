#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""G20 — HARNESS HỢP ĐỒNG LỚP HTTP (AG-03). Chạy HẾT năm harness con, gom về MỘT bảng.

====== KHOẢNG TRỐNG NÓ ĐÓNG ======
Trước lượt này có NĂM harness rời rạc cho lớp HTTP — `trien_khai/g16`, `g17`, `g18`,
`g18-crash`, `g19` — mỗi cái một kiểu tham số, một kiểu báo cáo, một kiểu chốt an toàn. Không
có chỗ nào chạy HẾT chúng, nên không có chỗ nào trả lời được câu: *"hợp đồng lớp HTTP của dự
án này đang giữ được gì, và đang hở gì?"* Hệ quả ĐO ĐƯỢC, không phải giả thuyết: G19/AG-02
(`f04de21`) chuyển kho đếm tần suất từ bộ nhớ tiến trình sang bảng CSDL dùng chung; harness
G18 (`8d58117`) viết trước đó vẫn tưởng `gioi_han.xoa_het()` chỉ xoá bộ nhớ của chính nó. Hai
lượt ấy không bao giờ gặp nhau trong một lần chạy — cho tới khi G20 chạy chúng cạnh nhau.

====== NÓ LÀM GÌ ======
1. Đọc hợp đồng từ `hop_dong.json` — DỮ LIỆU máy đọc được, không phải văn xuôi.
2. Tự kiểm bảy chốt an toàn CỦA CHÍNH NÓ (`chot_an_toan.py`) trước khi chạy bất cứ thứ gì.
3. Với TỪNG chặng: đối chiếu `chot_can` với bảy chốt. Thiếu một chốt ⇒ chặng TỪ CHỐI CHẠY và
   ghi `KHONG_CHAY_DUOC` kèm ĐÚNG tên chốt còn thiếu. Chặng `cham_hang` ⇒ ghi `BLOCKED` kèm
   đúng mã giấy phép còn thiếu, và **KHÔNG BAO GIỜ được tính là đạt**.
4. Chạy chặng theo ĐÚNG cách của nó (mỗi chặng khai `buoc` riêng), ghi mã thoát THẬT của TỪNG
   bước, rồi đối chiếu báo cáo với `mong_doi`.
5. In MỘT bảng: chạy được · không chạy được · BLOCKED · HỎNG.

====== BỐN TRẠNG THÁI, VÀ VÌ SAO PHẢI LÀ BỐN ======
    CHAY_DUOC        chạy xong, mã thoát khớp, báo cáo khớp mọi khai báo trong `mong_doi`
    KHONG_CHAY_DUOC  KHÔNG chạy được: thiếu chốt an toàn, hoặc thiếu điều kiện môi trường
    BLOCKED          khai báo là bị chặn (thiếu giấy phép / ngoài phạm vi). KHÔNG tính là đạt.
    HONG             ĐÃ CHẠY nhưng kết quả VI PHẠM khai báo. Đây là thứ duy nhất bắt được
                     một chặng bị tiêm lỗi — thiếu nó thì một chặng hỏng vẫn "xanh".

Ba trạng thái đầu là ba câu hỏi của đề bài. Trạng thái thứ tư tồn tại vì câu hỏi 4 của đề bài:
*tiêm một chặng hỏng vào bản sao ⇒ harness PHẢI báo đỏ*. `BLOCKED` KHÔNG phải `HONG`: một
chặng bị chặn đúng như đã khai là hợp đồng ĐANG ĐÚNG, không phải hợp đồng bị vi phạm.

====== BẰNG CHỨNG ======
Mã thoát của TỪNG bước được in ra TRƯỚC mọi ống lệnh. Nhật ký đầy đủ của từng chặng nằm ở
`<nền>/nhat-ky/<mã>.log`. Báo cáo gom: `--json <đường>`.

CHẠY
----
    sh trien_khai/g20/chay_tat_ca.sh
    python3 trien_khai/g20/chay_hop_dong.py --danh-sach
    python3 trien_khai/g20/chay_hop_dong.py --chi-chang G19
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time

THU_MUC_G20 = os.path.dirname(os.path.abspath(__file__))
DU_AN = os.path.dirname(os.path.dirname(THU_MUC_G20))
GOC_APP = os.path.join(DU_AN, "app")
for _d in (THU_MUC_G20, GOC_APP):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import chot_an_toan                                                          # noqa: E402

HOP_DONG_MAC_DINH = os.path.join(THU_MUC_G20, "hop_dong.json")
CONG_PG_MAC_DINH = 55718
HET_GIO_MAC_DINH = 900

CHAY_DUOC = "CHAY_DUOC"
KHONG_CHAY_DUOC = "KHONG_CHAY_DUOC"
BLOCKED = "BLOCKED"
HONG = "HONG"
KY_HIEU = {CHAY_DUOC: "✓", KHONG_CHAY_DUOC: "✗", BLOCKED: "⊘", HONG: "✗"}
NHAN = {CHAY_DUOC: "CHẠY ĐƯỢC", KHONG_CHAY_DUOC: "KHÔNG CHẠY ĐƯỢC",
        BLOCKED: "BLOCKED", HONG: "HỎNG"}

#: Biến môi trường thuộc "gia đình git dị dạng": `GIT_CONFIG_COUNT=N` mà thiếu `GIT_CONFIG_KEY_i`
#: làm MỌI lệnh git thoát 128. Bộ chạy tự chuẩn hoá thay vì dặn người gọi nhớ gỡ (N-G18-00).
GIT_DI_DANG = ("GIT_CONFIG_COUNT",)


# ===========================================================================
# Tiện ích
# ===========================================================================
def chuan_hoa_git(env):
    """Gỡ gia đình `GIT_CONFIG_*` dị dạng khỏi env của tiến trình con. Trả (env, đã_gỡ)."""
    env = dict(env)
    count = str(env.get("GIT_CONFIG_COUNT", "") or "").strip()
    if not count.isdigit() or int(count) <= 0:
        return env, False
    thieu = False
    for i in range(int(count)):
        if not str(env.get("GIT_CONFIG_KEY_%d" % i, "") or "").strip():
            thieu = True
    if not thieu:
        return env, False
    for k in [k for k in env if k.startswith("GIT_CONFIG_")]:
        env.pop(k, None)
    return env, True


def _thay_the(gia_tri, nen, cong_pg):
    if not isinstance(gia_tri, str):
        return gia_tri
    return gia_tri.replace("${NEN}", nen).replace("${CONG_PG}", str(cong_pg))


def _thay_the_sau(obj, nen, cong_pg):
    if isinstance(obj, str):
        return _thay_the(obj, nen, cong_pg)
    if isinstance(obj, list):
        return [_thay_the_sau(x, nen, cong_pg) for x in obj]
    if isinstance(obj, dict):
        return {k: _thay_the_sau(v, nen, cong_pg) for k, v in obj.items()}
    return obj


def doc_json(duong):
    """(đọc_được, đối_tượng, lỗi). Tệp thiếu và JSON hỏng là HAI lỗi khác nhau."""
    if not duong:
        return False, None, "không khai báo báo cáo"
    if not os.path.isfile(duong):
        return False, None, "KHÔNG có tệp báo cáo tại %s" % duong
    try:
        with open(duong, encoding="utf-8") as f:
            return True, json.load(f), ""
    except Exception as e:                                                  # noqa: BLE001
        return False, None, "báo cáo không đọc được (%s: %s)" % (type(e).__name__, e)


def _dem_blocked(bc):
    """Số BLOCKED của một báo cáo con. Ba harness khai ba kiểu — G20 phải bắc cầu.

    G16/G17: `dem.BLOCKED` + danh sách `blocked`. G18: CHỈ có `dem.BLOCKED`, KHÔNG có `blocked`.
    Trả (đọc_được, số).
    """
    if isinstance(bc.get("dem"), dict) and "BLOCKED" in bc["dem"]:
        return True, int(bc["dem"]["BLOCKED"])
    if isinstance(bc.get("blocked"), list):
        return True, len(bc["blocked"])
    return False, 0


# ===========================================================================
# Chạy một bước — và DỌN THEO ĐÚNG PID
# ===========================================================================
class BoChay(object):
    """Chạy tiến trình con, ghi PID, và dọn theo ĐÚNG PID. KHÔNG `pkill`, KHÔNG `killall`.

    Vì sao theo NHÓM tiến trình của chính PID mình spawn: `start_new_session=True` cho tiến
    trình con một nhóm riêng, nên nhóm ấy CHỈ chứa hậu duệ của nó. Giết theo nhóm đó vẫn là
    giết theo ĐÚNG PID đã ghi — khác hẳn `pkill -f ten`, thứ giết mọi tiến trình khớp TÊN trên
    máy, kể cả của làn khác đang chạy song song.
    """

    def __init__(self, nen):
        self.nen = nen
        self.pid_file = os.path.join(nen, "pid.txt")
        self.da_spawn = []

    def _ghi_pid(self, pid):
        self.da_spawn.append(pid)
        try:
            with open(self.pid_file, "a", encoding="utf-8") as f:
                f.write("%d\n" % pid)
        except OSError:
            pass

    def chay(self, lenh, env, het_gio):
        """Trả (mã_thoát, stdout, pid, hết_giờ?, lỗi_khởi_động)."""
        try:
            p = subprocess.Popen(lenh, cwd=DU_AN, env=env, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as e:
            return None, "", None, False, "không khởi động được %r (%s: %s)" % (lenh[0],
                                                                              type(e).__name__, e)
        self._ghi_pid(p.pid)
        het = False
        try:
            tho, _ = p.communicate(timeout=het_gio)
        except subprocess.TimeoutExpired:
            het = True
            self._giet(p.pid)
            try:
                tho, _ = p.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                tho = b""
        return p.returncode, (tho or b"").decode("utf-8", "replace"), p.pid, het, ""

    @staticmethod
    def _giet(pid):
        """TERM rồi KILL, theo ĐÚNG PID (và nhóm do chính PID ấy tạo).

        Chờ bằng vòng hỏi `kill -0` chứ không `sleep` cứng: chờ cứng thì lượt dọn nào cũng tốn
        đủ 8 giây kể cả khi tiến trình chết ngay, và một bộ thử chậm là một bộ thử bị người sau
        bỏ qua.
        """
        for sig, cho in ((signal.SIGTERM, 8.0), (signal.SIGKILL, 3.0)):
            try:
                os.killpg(os.getpgid(pid), sig)
            except (ProcessLookupError, PermissionError, OSError):
                try:
                    os.kill(pid, sig)
                except (ProcessLookupError, PermissionError, OSError):
                    return
            t0 = time.time()
            while time.time() - t0 < cho:
                try:
                    os.kill(pid, 0)
                except OSError:
                    return
                time.sleep(0.05)

    def con_song(self):
        """PID nào của lượt này còn sống — để ca tự kiểm đòi 0 tiến trình mồ côi."""
        ra = []
        for pid in self.da_spawn:
            try:
                os.kill(pid, 0)
                ra.append(pid)
            except OSError:
                pass
        return ra


# ===========================================================================
# Phán một chặng
# ===========================================================================
def _kiem_bao_cao(chang, bc, mong_doi):
    """Đối chiếu báo cáo JSON với `mong_doi`. Trả (đạt, [lý do], dữ kiện)."""
    ly, dk = [], {}
    for khoa in mong_doi.get("khoa_bat_buoc", []):
        if khoa not in bc:
            ly.append("báo cáo thiếu khoá bắt buộc %r" % khoa)
    if isinstance(bc.get("buoc"), list):
        dk["so_buoc"] = len(bc["buoc"])
        toi_thieu = mong_doi.get("so_buoc_toi_thieu")
        if toi_thieu is not None and dk["so_buoc"] < toi_thieu:
            ly.append("báo cáo chỉ có %d bước, hợp đồng đòi ≥ %d" % (dk["so_buoc"], toi_thieu))
    if isinstance(bc.get("route"), list):
        dk["so_route"] = len(bc["route"])
        toi_thieu = mong_doi.get("so_route_toi_thieu")
        if toi_thieu is not None and dk["so_route"] < toi_thieu:
            ly.append("chỉ thấy %d route, hợp đồng đòi ≥ %d" % (dk["so_route"], toi_thieu))
    dem = bc.get("dem") if isinstance(bc.get("dem"), dict) else {}
    if dem:
        dk["dem"] = {k: int(v) for k, v in dem.items()}
        toi_da = mong_doi.get("dem_hong_toi_da")
        if toi_da is not None and int(dem.get("HONG", 0)) > toi_da:
            ly.append("báo cáo có %d ca HỎNG (hợp đồng cho tối đa %d)"
                      % (int(dem.get("HONG", 0)), toi_da))
        for k, v in (mong_doi.get("dem_toi_thieu") or {}).items():
            if int(dem.get(k, 0)) < int(v):
                ly.append("báo cáo có %s=%d, hợp đồng đòi ≥ %d" % (k, int(dem.get(k, 0)), int(v)))
    doc_duoc, so_blocked = _dem_blocked(bc)
    dk["doc_duoc_so_blocked"] = doc_duoc
    dk["so_blocked"] = so_blocked
    mong_blocked = mong_doi.get("so_blocked")
    if mong_blocked is not None:
        if not doc_duoc:
            ly.append("hợp đồng khai %d BLOCKED nhưng báo cáo KHÔNG có `dem.BLOCKED` lẫn `blocked`"
                      " — không đối chiếu được thì không được coi là khớp" % mong_blocked)
        elif so_blocked != int(mong_blocked):
            ly.append("báo cáo khai %d chặng BLOCKED, hợp đồng khai %d" % (so_blocked, mong_blocked))
    return (not ly), ly, dk


def phan_quyet_chang(chang, do_chot, bo_chay, nen, cong_pg, log_dir, chi_chay):
    """Phán MỘT chặng. Trả dict kết quả. Không ném ngoại lệ ra ngoài."""
    ma = chang.get("ma", "?")
    loai = chang.get("loai", "harness")
    mong_doi_trang_thai = chang.get("trang_thai_mong_doi", CHAY_DUOC)
    kq = {"ma": ma, "ten": chang.get("ten", ""), "loai": loai, "nhom": chang.get("nhom", ""),
          "trang_thai_mong_doi": mong_doi_trang_thai, "ly_do": [], "buoc": [],
          "giay_phep_can": list(chang.get("giay_phep_can", [])),
          "chot_can": list(chang.get("chot_can", [])), "du_kien": {}}

    # ---- chặng KHAI là bị chặn: KHÔNG chạy, và KHÔNG BAO GIỜ tính là đạt
    if loai in ("cham-hang", "ngoai-pham-vi"):
        thieu = [g for g in kq["giay_phep_can"]]
        kq["trang_thai"] = BLOCKED
        kq["ly_do"].append(chang.get("ly_do_blocked", "khai báo là bị chặn"))
        if thieu:
            kq["ly_do"].append("giấy phép còn thiếu: %s" % " · ".join(thieu))
        if loai == "cham-hang" and not chang.get("giay_phep_can"):
            kq["trang_thai"] = HONG
            kq["ly_do"].append("chặng CHẠM HÃNG nhưng KHÔNG khai mã giấy phép — một chặng chạm"
                               " hãng không khai giấy phép là một chặng sẽ bị 'đạt' lặng lẽ.")
        kq["du_kien"]["nguon_khai"] = chang.get("nguon_khai", "")
        return kq

    # ---- chốt an toàn: thiếu một chốt ⇒ TỪ CHỐI CHẠY
    thieu_chot = [c for c in kq["chot_can"] if c in do_chot]
    if thieu_chot:
        kq["trang_thai"] = KHONG_CHAY_DUOC
        for c in thieu_chot:
            kq["ly_do"].append("THIẾU CHỐT %s (%s): %s"
                               % (c, chot_an_toan.TEN_CHOT.get(c, "?"),
                                  " / ".join(do_chot.get(c, []))))
        return kq

    if chi_chay is not None and ma not in chi_chay:
        kq["trang_thai"] = KHONG_CHAY_DUOC
        kq["ly_do"].append("--chi-chang: chặng này không nằm trong danh sách chạy")
        return kq

    # ---- chạy TỪNG bước, ghi mã thoát THẬT
    env = dict(os.environ)
    for k, v in (chang.get("bien_moi_truong") or {}).items():
        env[k] = str(_thay_the(v, nen, cong_pg))
    if "VIP_HUB_DATA" not in env:
        env["VIP_HUB_DATA"] = nen
    env.setdefault("VHG18_CONG_PG", str(cong_pg))
    env["PYTHONUNBUFFERED"] = "1"

    # Chốt an toàn được kiểm LẦN HAI trên env THẬT SẮP ĐƯA CHO TIẾN TRÌNH CON. Một chốt chỉ
    # kiểm env của chính harness điều phối là một chốt có khe hở ngay ở tầng nó sinh ra.
    do_con = chot_an_toan.kiem_tat_ca({"nen": env.get("VIP_HUB_DATA"), "env": env})
    thieu_con = [c for c in kq["chot_can"] if c in do_con]
    if thieu_con:
        kq["trang_thai"] = KHONG_CHAY_DUOC
        for c in thieu_con:
            kq["ly_do"].append("THIẾU CHỐT %s trên MÔI TRƯỜNG CỦA TIẾN TRÌNH CON: %s"
                               % (c, " / ".join(do_con[c])))
        return kq

    os.makedirs(log_dir, exist_ok=True)
    duong_log = os.path.join(log_dir, "%s.log" % ma)
    het_gio = int(chang.get("het_gio", HET_GIO_MAC_DINH))
    toan_bo = []
    hong = []
    for i, buoc in enumerate(chang.get("buoc", []), 1):
        lenh = [_thay_the(x, nen, cong_pg) for x in buoc.get("lenh", [])]
        if not lenh:
            hong.append("bước %d không có lệnh" % i)
            continue
        ma_thoai, tho, pid, het, loi = bo_chay.chay(lenh, env, het_gio)
        toan_bo.append("\n" + "═" * 78 + "\n[%s · bước %d/%d] %s\n  argv: %s\n  PID: %s\n"
                       "  MÃ THOÁT: %s\n%s\n" % (ma, i, len(chang.get("buoc", [])),
                                                buoc.get("ten", ""), " ".join(lenh), pid,
                                                "HẾT GIỜ (%ds)" % het_gio if het else ma_thoai, "═" * 78))
        toan_bo.append(tho)
        kq["buoc"].append({"ten": buoc.get("ten", ""), "argv": lenh, "pid": pid,
                           "ma_thoai": ma_thoai, "ma_thoai_mong_doi": buoc.get("ma_thoai"),
                           "het_gio": het, "loi_khoi_dong": loi})
        print("    · [%s] bước %d/%d · PID %s · MÃ THOÁT = %s%s"
              % (ma, i, len(chang.get("buoc", [])), pid,
                 "HẾT GIỜ" if het else ma_thoai, "  ← %s" % loi if loi else ""))
        if loi:
            hong.append("bước %d: %s" % (i, loi))
            continue
        if het:
            hong.append("bước %d HẾT GIỜ sau %ds (đã tắt theo ĐÚNG PID %s)" % (i, het_gio, pid))
        if ma_thoai != buoc.get("ma_thoai"):
            hong.append("bước %d: mã thoát THẬT = %s, hợp đồng đòi %s"
                        % (i, ma_thoai, buoc.get("ma_thoai")))

    van_ban = "".join(toan_bo)
    try:
        with open(duong_log, "w", encoding="utf-8") as f:
            f.write(van_ban)
    except OSError as e:
        hong.append("không ghi được nhật ký %s (%s)" % (duong_log, e))
    kq["du_kien"]["nhat_ky"] = duong_log

    for mau in (chang.get("mong_doi") or {}).get("stdout_bat_buoc", []):
        if mau not in van_ban:
            hong.append("nhật ký THIẾU dấu vết bắt buộc %r — chặng có thể chưa thật sự chạy" % mau)
    for mau in (chang.get("mong_doi") or {}).get("stdout_cam", []):
        if mau in van_ban:
            hong.append("nhật ký CÓ dấu vết bị cấm %r" % mau)

    duong_bc = _thay_the(chang.get("bao_cao_json", ""), nen, cong_pg)
    if duong_bc:
        ok, bc, loi = doc_json(duong_bc)
        kq["du_kien"]["bao_cao_json"] = duong_bc
        if not ok:
            hong.append(loi)
        else:
            dat, ly_bc, dk = _kiem_bao_cao(chang, bc, chang.get("mong_doi") or {})
            kq["du_kien"].update(dk)
            if not dat:
                hong.extend(ly_bc)
    elif (chang.get("mong_doi") or {}).get("so_blocked") is not None:
        hong.append("hợp đồng khai `so_blocked` nhưng chặng KHÔNG có báo cáo máy đọc được")

    kq["trang_thai"] = CHAY_DUOC if not hong else HONG
    kq["ly_do"].extend(hong)
    return kq


# ===========================================================================
# Điều phối
# ===========================================================================
_DEM_NEN = [0]


def dung_nen(nen_goc=None, nen=None):
    """Dựng nền TẠM RIÊNG cho lượt này để hai làn (hoặc hai lượt) không giẫm lên nhau.

    Tên nền có PID + mốc thời gian + SỐ ĐẾM, và `os.makedirs` chạy ở chế độ KHÔNG `exist_ok`
    để việc giành nền là NGUYÊN TỬ: hai tiến trình cùng giây, cùng PID-không-thể-trùng vẫn
    không thể nhận chung một thư mục — bên thua `FileExistsError` và thử tên kế tiếp.

    Vì sao cần số đếm: bản đầu chỉ dùng PID + `int(time.time())`, nên HAI lượt trong CÙNG một
    giây nhận CHUNG một nền. Bộ thử `test_e01` bắt được điều đó, và nó là lỗi thật: nền chung
    nghĩa là lượt sau xoá dữ liệu của lượt trước.
    """
    if nen:
        os.makedirs(nen, exist_ok=True)
        return os.path.realpath(nen)
    goc = nen_goc or "/tmp/veh_g20_ag03"
    os.makedirs(goc, exist_ok=True)
    for _ in range(200):
        _DEM_NEN[0] += 1
        d = os.path.join(goc, "lan-%d-%d-%d" % (os.getpid(), int(time.time()), _DEM_NEN[0]))
        try:
            os.makedirs(d)                     # KHÔNG exist_ok: giành nền phải là nguyên tử
            return os.path.realpath(d)
        except FileExistsError:
            continue
    raise RuntimeError("không dựng được nền riêng dưới %s sau 200 lần thử" % goc)


def in_bang(ket_qua):
    rong = max([len(k["ma"]) for k in ket_qua] + [4])
    rong_loai = max([len(k["loai"]) for k in ket_qua] + [4])
    print("")
    print("═" * 118)
    print("BẢNG HỢP ĐỒNG LỚP HTTP — %d chặng" % len(ket_qua))
    print("  ✓ CHẠY ĐƯỢC · ✗ KHÔNG CHẠY ĐƯỢC · ⊘ BLOCKED (KHÔNG tính là đạt) ·"
          " ✗ HỎNG (đã chạy nhưng vi phạm hợp đồng)")
    print("═" * 118)
    print("  %-*s  %-*s  %-16s  %-8s  %s" % (rong, "CHẶNG", rong_loai, "LOẠI", "TRẠNG THÁI",
                                               "MÃ THOÁT", "GHI CHÚ"))
    print("  " + "─" * 114)
    for k in ket_qua:
        ma_thoai = " · ".join(str(b["ma_thoai"]) for b in k["buoc"]) or "—"
        if k["buoc"] and any(b["ma_thoai"] != b["ma_thoai_mong_doi"] for b in k["buoc"]):
            ma_thoai += " (đòi %s)" % " · ".join(str(b["ma_thoai_mong_doi"]) for b in k["buoc"])
        note = k["ly_do"][0] if k["ly_do"] else k.get("du_kien", {}).get("nguon_khai", "")
        if len(note) > 56:
            note = note[:53] + "..."
        print("  %-*s  %-*s  %s %-14s  %-8s  %s"
              % (rong, k["ma"], rong_loai, k["loai"], KY_HIEU[k["trang_thai"]],
                 NHAN[k["trang_thai"]], ma_thoai, note))
    print("═" * 118)


def main(argv=None):
    ap = argparse.ArgumentParser(description="G20 — harness hợp đồng lớp HTTP")
    ap.add_argument("--hop-dong", default=HOP_DONG_MAC_DINH)
    ap.add_argument("--nen", default="")
    ap.add_argument("--json", default="")
    ap.add_argument("--chi-chang", default="", help="chỉ CHẠY các chặng này (vẫn phán hết)")
    ap.add_argument("--khong-chay", action="store_true", help="chỉ phán hợp đồng, không chạy gì")
    ap.add_argument("--danh-sach", action="store_true", help="in hợp đồng rồi thoát")
    ap.add_argument("--giu-nen", action="store_true")
    a = ap.parse_args(argv)

    if not os.path.isfile(a.hop_dong):
        print("KHÔNG có hợp đồng tại %s — không có hợp đồng thì không phán được gì." % a.hop_dong)
        return 2
    ok, hd, loi = doc_json(a.hop_dong)
    if not ok:
        print("Hợp đồng không đọc được: %s" % loi)
        return 2
    chang = hd.get("chang") or []
    if not chang:
        print("Hợp đồng RỖNG (0 chặng) — một bộ chạy 0 chặng mà báo 'đạt' là bộ chạy hỏng.")
        return 2
    toi_thieu = int(hd.get("so_chang_toi_thieu", 0))
    if len(chang) < toi_thieu:
        print("Hợp đồng chỉ có %d chặng, khai báo đòi ≥ %d — thiếu chặng nghĩa là có chặng bị"
              " BỎ IM LẶNG, không phải là đạt." % (len(chang), toi_thieu))
        return 2

    if a.danh_sach:
        print("HỢP ĐỒNG: %s (phiên bản %s) — %d chặng"
              % (hd.get("ten", ""), hd.get("phien_ban", "?"), len(chang)))
        for c in chang:
            print("  [%s] %-16s %-11s chốt=%s giấy phép=%s"
                  % (c.get("trang_thai_mong_doi", "?"), c.get("ma", ""), c.get("loai", ""),
                     ",".join(c.get("chot_can", [])) or "—",
                     ",".join(c.get("giay_phep_can", [])) or "—"))
            print("        %s" % c.get("ten", ""))
        return 0

    nen = dung_nen(hd.get("nen_goc"), a.nen or None)
    cong_pg = CONG_PG_MAC_DINH + (os.getpid() % 500)

    env_sach, da_go = chuan_hoa_git(os.environ)
    if da_go:
        print("[chuẩn hoá] gỡ gia đình GIT_CONFIG_* dị dạng (nếu không, MỌI lệnh git thoát 128).")
        os.environ.clear()
        os.environ.update(env_sach)

    print("═" * 78)
    print(" G20 — HARNESS HỢP ĐỒNG LỚP HTTP (AG-03)")
    print("═" * 78)
    print(" dự án     = %s" % DU_AN)
    print(" hợp đồng  = %s" % a.hop_dong)
    print(" nền       = %s  (TẠM, riêng cho lượt này)" % nen)
    print(" cổng PG   = %s  (cụm RIÊNG; CẤM 5432)" % cong_pg)
    print(" gọi hãng  = KHÔNG, kể cả sandbox (V-G09-01 + V-13906-05 CHƯA CẤP)")
    print(" dọn dẹp   = theo ĐÚNG PID; nguồn làn không chứa pkill/killall (chốt N6)")
    print("")

    so_ca_chot = len(chot_an_toan.bo_ca_tu_kiem())
    print("── 0. TỰ KIỂM BỘ DÒ CHỐT AN TOÀN (%d cấu hình tổng hợp) ───────────────" % so_ca_chot)
    tong, so_hong_chot, _ = chot_an_toan.tu_kiem()
    print("   TỰ KIỂM: %d/%d ca đạt · %d hỏng" % (tong - so_hong_chot, tong, so_hong_chot))
    if so_hong_chot:
        print("   BỘ DÒ HỎNG ⇒ mọi lời khai 'đã từ chối chạy' ở lượt này KHÔNG có giá trị.")
        return 3
    print("")

    print("── 1. BẢY CHỐT AN TOÀN CỦA CHÍNH HARNESS NÀY ──────────────────────────")
    do_chot = chot_an_toan.kiem_tat_ca({"nen": nen})
    if do_chot:
        print("TỪ CHỐI CHẠY — mất ít nhất một chốt:")
        for c in sorted(do_chot):
            print("  · [%s] %s" % (c, chot_an_toan.TEN_CHOT.get(c, "?")))
            for x in do_chot[c]:
                print("      %s" % x)
        return 4
    print("   BẢY CHỐT: ĐỦ. %s" % chot_an_toan.bao_cao_moi_truong())
    print("")

    chi_chay = {x.strip() for x in a.chi_chang.split(",") if x.strip()} if a.chi_chang else None
    if chi_chay is not None and a.khong_chay:
        chi_chay = set()

    print("── 2. CHẠY TỪNG CHẶNG THEO ĐÚNG CÁCH CỦA NÓ ───────────────────────────")
    bo_chay = BoChay(nen)
    log_dir = os.path.join(nen, "nhat-ky")
    ket_qua = []
    t0 = time.time()
    for c in chang:
        print("  ▸ %s — %s" % (c.get("ma", "?"), c.get("ten", "")))
        if a.khong_chay and c.get("loai", "harness") == "harness":
            ket_qua.append({"ma": c.get("ma", "?"), "ten": c.get("ten", ""),
                            "loai": c.get("loai", "harness"), "nhom": c.get("nhom", ""),
                            "trang_thai_mong_doi": c.get("trang_thai_mong_doi", CHAY_DUOC),
                            "trang_thai": KHONG_CHAY_DUOC,
                            "ly_do": ["--khong-chay: chỉ phán hợp đồng"],
                            "buoc": [], "giay_phep_can": list(c.get("giay_phep_can", [])),
                            "chot_can": list(c.get("chot_can", [])), "du_kien": {}})
            print("    · --khong-chay: không thực thi")
            continue
        ket_qua.append(phan_quyet_chang(c, do_chot, bo_chay, nen, cong_pg, log_dir, chi_chay))
    giay = time.time() - t0

    con_song = bo_chay.con_song()
    if con_song:
        print("\n  [dọn] còn %d PID của lượt này đang sống — tắt theo ĐÚNG PID: %s"
              % (len(con_song), ", ".join(str(p) for p in con_song)))
        for pid in con_song:
            BoChay._giet(pid)

    in_bang(ket_qua)

    dem = {t: 0 for t in NHAN}
    for k in ket_qua:
        dem[k["trang_thai"]] += 1
    lech = [k for k in ket_qua if k["trang_thai"] != k["trang_thai_mong_doi"]]
    dat_hop_dong = (not lech) and dem[HONG] == 0 and dem[KHONG_CHAY_DUOC] == 0

    print("")
    print("TỔNG KẾT — %d chặng · %.1fs" % (len(ket_qua), giay))
    print("  ✓ CHẠY ĐƯỢC        : %d" % dem[CHAY_DUOC])
    print("  ✗ KHÔNG CHẠY ĐƯỢC  : %d" % dem[KHONG_CHAY_DUOC])
    print("  ⊘ BLOCKED          : %d   (KHÔNG được tính là đạt)" % dem[BLOCKED])
    print("  ✗ HỎNG             : %d   (đã chạy nhưng vi phạm hợp đồng)" % dem[HONG])
    print("  tổng ca ĐẠT của các chặng con: %d · ca HỎNG: %d"
          % (sum(k.get("du_kien", {}).get("dem", {}).get("DAT", 0) for k in ket_qua),
             sum(k.get("du_kien", {}).get("dem", {}).get("HONG", 0) for k in ket_qua)))
    if lech:
        print("  LỆCH KHAI BÁO (thực tế ≠ hợp đồng mong đợi):")
        for k in lech:
            print("    · %s: mong đợi %s, thực tế %s" % (k["ma"], k["trang_thai_mong_doi"],
                                                        k["trang_thai"]))
    for k in ket_qua:
        if k["trang_thai"] in (BLOCKED, KHONG_CHAY_DUOC, HONG):
            print("")
            print("  %s [%s] %s" % (KY_HIEU[k["trang_thai"]], k["ma"], k["ten"]))
            for x in k["ly_do"]:
                print("      %s" % x)
    print("")
    print("NẰM NGOÀI PHẠM VI CỦA CẢ LƯỢT NÀY (đã đo là KHÔNG đo được):")
    for k in ket_qua:
        if k["loai"] == "cham-hang":
            print("  · %s — thiếu %s" % (k["ma"], " · ".join(k["giay_phep_can"]) or "(không khai)"))
    print("  · mọi phép đo lớp HTTP đều qua loopback; KHÔNG có lượt nào ra ngoài Internet")
    print("  · KHÔNG gọi API hãng, kể cả sandbox — đây là giới hạn CỦA GIẤY PHÉP, không phải của mã")
    print("")

    bao_cao = {
        "goc": "G20-AG03-HOP-DONG-LOP-HTTP",
        "hop_dong": {"duong": a.hop_dong, "phien_ban": hd.get("phien_ban"),
                     "so_chang_khai": len(chang), "so_chang_toi_thieu": toi_thieu},
        "nen": nen, "cong_pg": cong_pg, "giay": round(giay, 1),
        "chot_an_toan": {"so_chot": len(chot_an_toan.THU_TU_CHOT),
                         "tu_kiem_dat": tong - so_hong_chot, "tu_kiem_tong": tong,
                         "moi_truong": chot_an_toan.bao_cao_moi_truong()},
        "chang": ket_qua,
        "dem": {"CHAY_DUOC": dem[CHAY_DUOC], "KHONG_CHAY_DUOC": dem[KHONG_CHAY_DUOC],
                "BLOCKED": dem[BLOCKED], "HONG": dem[HONG], "TONG": len(ket_qua)},
        "lech_khai_bao": [{"ma": k["ma"], "mong_doi": k["trang_thai_mong_doi"],
                           "thuc_te": k["trang_thai"]} for k in lech],
        "pid_da_spawn": bo_chay.da_spawn,
        "pid_con_song": con_song,
        "hop_dong_dat": bool(dat_hop_dong),
        "ket_luan": ("MỌI chặng khớp khai báo của hợp đồng." if dat_hop_dong else
                     "HỢP ĐỒNG CHƯA ĐẠT — xem `lech_khai_bao` và các chặng HỎNG/BLOCKED."),
        "pham_vi": {
            "trong": ["chạy năm harness con theo đúng cách của từng cái · gom về một bảng · "
                      "đối chiếu báo cáo với khai báo máy đọc được · tự kiểm bộ dò chốt · "
                      "dọn theo ĐÚNG PID"],
            "ngoai": ["gọi API hãng kể cả sandbox", "TLS/tunnel/VPS/deploy",
                      "chuyển CSDL nghiệp vụ sang PostgreSQL (D-8)",
                      "đoán mã trạng thái hãng (D-4)", "ánh xạ city/area ngoài mock (D-9)"],
        },
    }
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(bao_cao, f, ensure_ascii=False, indent=2)
        print("báo cáo máy đọc được: %s" % a.json)
    if a.giu_nen:
        print("--giu-nen: giữ nền %s" % nen)
    print("KẾT LUẬN: %s" % bao_cao["ket_luan"])
    return 0 if dat_hop_dong else 1


if __name__ == "__main__":
    sys.exit(main())
