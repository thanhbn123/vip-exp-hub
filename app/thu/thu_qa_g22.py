#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-01 (G22) — BỘ KIỂM ĐỘC LẬP cho wave G22. VAI: NGƯỜI KIỂM, KHÔNG PHẢI NGƯỜI VIẾT.

NỀN ĐO — ĐỌC KỸ, NHÃN VÀ SHA KHÔNG KHỚP NHAU:

    LƯỢT NÀY (`N-G22-01`, AG-01 G22): worktree `g21-ag01-qa` có `HEAD = 85e0a6c`
    (`AG-1 (G22) ket qua luot G22` — AG-00 chốt lượt trước) và cây chỉ mục `1340029a`
    (`85e0a6c^{tree}`). Cây tích hợp mà AG-00 đang gộp vào là `integration/g20 @ 3b7e93b`
    (`AG-00: dua bo kiem G20 vao cay tich hop`).
    Ghim `NEN_SHA=7344c02` / `TREE_NEN=8fc624de` vẫn là mốc của LƯỢT TRƯỚC, KHÔNG được sửa cho
    khớp lượt này: sửa ghim cho vừa mắt là đúng thứ wave này đang diệt. Hệ quả ĐO ĐƯỢC và NÓI
    THẲNG: `A1` ĐỎ và `E1` BỎ QUA vì lý do MÔI TRƯỜNG ĐO — xem §1.2 `docs/QA_G22.md`.

TRẠNG THÁI GIT CỦA WORKTREE NÀY — KHAI THẲNG, VÌ NÓ ẢNH HƯỞNG TỚI MỌI CỔNG "CÂY SẠCH":

    Sandbox CHẶN ghi `.git`: `git write-tree` trả `rc=128`
    (`Unable to create .../worktrees/g21-ag01-qa/index.lock: Operation not permitted`) — đo lại
    trong chính lượt này. Nên `tree_hien_tai()` KHÔNG đọc được cây chỉ mục, và `A1` không thể
    xanh ở đây dù cây có đúng nền hay không.
    Hệ quả ĐO ĐƯỢC (`qa_g22_lan1_nhiem.log`, lượt trước): cổng "cây sạch" thấy 13 đường NGOÀI
    vùng đỏ lên — **một cái ĐỎ GIẢ của môi trường, không phải của sản phẩm**.

    LƯỢT NÀY thêm một nguyên nhân ĐỎ-GIẢ nữa, cũng phải NÓI RA: cây thợ có 4 tệp CHƯA COMMIT
    (`app/thu/thu_qa_g20.py` mới, `app/thu/thu_qa_g21.py` vá `G7`, `app/thu/thu_qa_g22.py`,
    `docs/QA_G22.md`) — `E1` gọi ba cổng "cây sạch" của wave TRƯỚC, và cổng nào có danh sách
    trắng HẸP (chỉ nhận tệp của làn mình) thì thấy chúng là "ngoài phép". Trên cây ĐÃ COMMIT
    (tích hợp) thì `git status` sạch và ba cổng đó xanh.

    HAI ĐƯỜNG "CHỮA" ĐÃ THỬ VÀ ĐÃ HỎNG — ghi lại vì chúng là bằng chứng, không phải lời kể:

      (1) `GIT_DIR` BÓNG trong `TMP` (HEAD=nền, index=nền, mượn `refs/` kho chung). Chạy tốt cho
          tới khi một bộ thử KHÁC gọi `git init <thư-mục-tạm>` — `GIT_DIR` ĐÈ lên đích của
          `git init`, nên nó init thẳng vào `GIT_DIR` bóng và ghi `bare = true` vào đó. Từ phút
          16:34 của lượt `qa_g22_lan4`, MỌI `git ls-files --others` trả 128 và
          `thu_g21_chotcay.py` lỗ 8/13 ca — ĐỎ GIẢ hoàn toàn do môi trường đo.
      (2) Bản sao THẬT: `git clone --shared --no-checkout <kho> $CP && git checkout --detach
          7344c02` — một kho BÌNH THƯỜNG, `HEAD` = nền, cây SẠCH, và `git init` của bộ khác
          không chạm tới nó. **Đây là cách chạy ĐÚNG của bộ kiểm này.**

    ⇒ Bộ kiểm TỰ ĐO môi trường (`write-tree` == `TREE_NEN`; `HEAD` == nền) và, khi `HEAD` không
      phải nền, nó TỪ CHỐI phán quyết trên ba cổng "cây sạch" kèm lý do — thay vì bỏ qua im lặng
      hoặc báo đỏ giả. Không một byte nào ghi vào `.git` thật.

LỆNH CHẠY:

    python3 app/thu/thu_qa_g22.py                       # làn MẶC ĐỊNH — đo, in bảng, KHÔNG tự cho qua
    VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py    # NGHIỆM THU BẢN ĐÃ GỘP: nợ còn ⇒ ĐỎ
    VIP_G22_DAY_DU=1 python3 app/thu/thu_qa_g22.py      # + chạy LẠI `chay_tat_ca.sh` (11 phút)

HAI CHỐT CHẶN — ĐỀ BÀI ĐÒI, VÀ ĐÂY LÀ CÁCH CHÚNG ĐƯỢC THI HÀNH (không phải khai suông):

  (1) CA TỰ KIỂM BỘ ĐO CHẠY TRONG **TIẾN TRÌNH CON** (`Z2`).
      `Z2` chạy một ca tự kiểm trong tiến trình con, rồi khẳng định BỐN vế đo được:
        · PID của tiến trình chạy ca KHÁC PID của bộ kiểm;
        · một BIẾN TOÀN CỤC mà tiến trình con đặt KHÔNG nhìn thấy được ở tiến trình cha;
        · mã thoát của tiến trình con được ĐỌC RA (không phải suy từ chữ trong output);
        · nếu tiến trình con CHẾT thì bộ kiểm thấy `rc != 0`, không thấy "đạt".
      Vế thứ hai là vế quyết định: một "tự kiểm" chạy chung tiến trình sẽ để lại dấu vết trong
      cha, và đó chính là thứ `Z2` dò.

  (2) ĐỐI CHỨNG DƯƠNG CHO **MỌI** CA PHỦ ĐỊNH (`Z1`).
      Mọi nhóm ca phủ định nằm trong `CA_PHU_DINH`; mọi nhóm phải có mặt trong `DOI_CHUNG`; và
      `Z1` đòi thêm hai thứ mà một lời khai không có được:
        · `da_chay[nhom]` — cờ do CHÍNH ca đó bật lên khi nó THẬT SỰ chạy đối chứng;
        · `da_tiem[nhom]` — cờ bật khi nhóm đó đã được TIÊM LỖI và bộ đo BẮT ĐƯỢC.
      Thiếu bất kỳ vế nào ⇒ `Z1` HỎNG. Nói cách khác: "0 lỗi" chỉ được tin khi đã chứng minh bộ
      đo NHÌN THẤY lỗi.

BA LUẬT BẰNG CHỨNG (nguyên văn của đề bài, và đây là chỗ chúng được thi hành):
  · MỌI khẳng định đi kèm LỆNH THẬT + MÃ THOÁT THẬT (đọc NGAY sau lệnh, không qua ống) + SỐ CA
    + SỐ SKIP + BLOCKED.
  · KHÔNG đoán mã trạng thái hãng (D-4): mã chưa xác minh ⇒ `NEEDS_REVIEW`, không bịa.
  · Mọi ca PHỦ ĐỊNH phải có ĐỐI CHỨNG DƯƠNG.

PHẠM VI HTTP — TUYỆT ĐỐI: không một lời gọi nào ra hãng, kể cả sandbox (`V-G09-01` +
`V-13906-05` CHƯA CẤP). Mọi máy chủ là `app/server.py` trên nền tạm, bind `127.0.0.1`, cổng do
OS cấp. Cụm PostgreSQL `:5432` KHÔNG bị đụng tới (D-8: CSDL nghiệp vụ vẫn SQLite).
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. HẰNG SỐ — NỀN, TỆP ĐƯỢC PHÉP, CHẾ ĐỘ
# ══════════════════════════════════════════════════════════════════════════════════════════════

GOC_CAY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GOC_APP = os.path.join(GOC_CAY, "app")
GOC_THU = os.path.join(GOC_CAY, "app", "thu")

# NỀN: SHA, không phải nhãn. `TREE_NEN` là thứ được CANH, vì nó là thứ thật sự được đo.
#
# NỀN CỦA LƯỢT `N-G22-01` = **CÂY TÍCH HỢP** `integration/g20 @ 3b7e93b` — đúng cái cây mà AG-00
# đã đưa `app/thu/thu_qa_g20.py` + `docs/QA_G20.md` vào, và là cây mà bản giao của lượt này sẽ
# được GỘP VÀO. Đo trên cây nào thì GHIM CÂY ĐÓ — ghim cũ `7344c02`/`8fc624de` là mốc của LƯỢT
# TRƯỚC (cây đó KHÔNG có `thu_qa_g20.py` lẫn `thu_qa_g19_tich_hop.py`, nên `C5`/`G7` không thể
# xanh ở đó — xem `docs/QA_G22.md` §9.3 và §10).
NEN_SHA = "3b7e93b59b70449b8306eb4fa374dd1e97a8e7af"
TREE_NEN = "37079aa83f2ad62c2862f2eb7ce1c809c24570fb"
# HAI MỐC CỦA LƯỢT TRƯỚC — giữ lại làm LỊCH SỬ, KHÔNG dùng để phán quyết nữa:
NEN_LUOT_TRUOC = "601718e42ea23a30b849d606890070d4816cbf0b"    # HEAD worktree đầu lượt trước
NEN_LUOT_TRUOC_2 = "7344c020abad562dafb593c4234d5e1f9ecfd18c"  # ghim nền của lượt trước

TEP_DUOC_PHEP = ("docs/QA_G22.md", "app/thu/thu_qa_g22.py", "app/thu/thu_qa_g21.py",
                 "app/thu/thu_qa_g20.py")
# `app/thu/thu_qa_g21.py` được THÊM vào danh sách này ở dispatch `N-G22-01`: AG-00 cấp quyền
# sửa HAI bản sao của bộ đếm `bo-g19-tong-hop` (bàn đo G20 gọi là `C5`, bàn đo G21 gọi là `G7`),
# và bản sao thứ hai nằm trong tệp đó. Không thêm thì `A2`/`_kiem_tra_pham_vi` gọi chính bản vá
# đó là "thay đổi ngoài phép" — một cái ĐỎ GIẢ của phạm vi, không phải của sản phẩm.

CHE_DO = os.environ.get("VIP_G22_CHE_DO", "nen")
if CHE_DO not in ("nen", "gop"):
    CHE_DO = "nen"
DAY_DU = os.environ.get("VIP_G22_DAY_DU") == "1"

LOG_DIR = os.environ.get("VIP_G22_LOG") or os.path.join(tempfile.gettempdir(), "veh_g22_ag01_qa")
TMP_GOC = tempfile.gettempdir()

# ── Nhị phân Chromium: CHỈ ĐỊNH TƯỜNG MINH, có ĐƯỜNG DẪN + PHIÊN BẢN (đề bài, điểm 1) ─────────
#
# `thu_giao_dien/chay.sh` ghim `PLAYWRIGHT_BROWSERS_PATH=0`, tức nó CHỈ tìm trong
# `node_modules/playwright-core/.local-browsers`. Thư mục đó KHÔNG có trong worktree này ⇒ lượt
# trước chạy ra "7 failed · 44 did not run" và **0 tín hiệu sản phẩm**.
#
# `playwright-core` trong repo là **1.56.1**; `browsers.json` của nó đòi **chromium revision
# 1194**. Cache hệ thống `~/Library/Caches/ms-playwright` có 1148 và 1243 — CẢ HAI ĐỀU SAI
# revision, nên "cài thêm trình duyệt" không phải đường đúng. Đường đúng là bản mà
# `BAN_GIAO.md` §1 đã ghim và AG-06 đã chạy THÀNH CÔNG: symlink `.local-browsers` sang
# `Projects-vip-express-hub` (xem `docs/G21_BANPHIM_E2E.md` §10).
PW_BROWSERS_REPO = os.path.join(GOC_CAY, "node_modules", "playwright-core", ".local-browsers")
PW_BROWSERS_G17 = os.path.expanduser(
    "~/orca/workspaces/vip-express-hub/g17-ag06-security/node_modules/playwright-core/.local-browsers")
PW_BROWSERS_CHI_DINH = os.path.expanduser(
    "~/code/veh4-g12-playwright/node_modules/playwright-core/.local-browsers")
PW_CHROMIUM_TUONG_DOI = ("chromium-1194", "chrome-mac", "Chromium.app", "Contents", "MacOS",
                         "Chromium")
PW_REVISION_DOI = "1194"

# Log `chay_tat_ca.sh` của lượt đo này — dùng khi KHÔNG bật `VIP_G22_DAY_DU`.
LOG_CHAY_TAT_CA = os.environ.get("VIP_G22_LOG_TAT_CA") or os.path.join(
    TMP_GOC, "qa_g22_lan2_sach.log")

# Bàn đo G20 (`C5`) và bàn đo G21 (`G7`) — TỆP NGUỒN TRONG CÂY, **KHÔNG** qua bản chép tạm.
# Dispatch `N-G22-01` vá THẲNG hai khối bộ đếm vào hai tệp này; đường tạm
# `g20_cop_tam()`/`g20_va_c5()` đã bị XOÁ HẲN (xem `docs/QA_G22.md` §7).
BAN_DO_G20 = os.path.join(GOC_THU, "thu_qa_g20.py")
BAN_DO_G21 = os.path.join(GOC_THU, "thu_qa_g21.py")
# sha256 của bản GỐC (TRƯỚC khi vá). Đây là CHỐT CHỐNG TRÔI: hoàn vá tệp đang có trong cây rồi
# băm, phải ra ĐÚNG hai giá trị này — nếu không thì cây đang đo KHÔNG PHẢI "bản gốc + đúng hai
# khối vá", và mọi con số dưới đây không đối chiếu được.
BAN_DO_G20_GOC_SHA = "5a4b3c83c45f2f2c465d2eed380f1f6f69583878ca9e3a5f910bd01c1a0ddcd0"
BAN_DO_G21_GOC_SHA = "4ebf21e8804246bda315fbe9bc1721625fad0ec2130c5036f235d4e04ca40700"

PY = sys.executable or "python3"


def _git_env():
    """Môi trường git ĐÃ CHUẨN HOÁ. Trả `(env, ghi_chu)`.

    `GIT_CONFIG_COUNT=2` mà THIẾU `GIT_CONFIG_KEY_*` làm MỌI lệnh git thoát 128 (`N-G18-00`).
    Bộ kiểm này KHÔNG gỡ biến để "cho xanh": nó gỡ biến để ĐO ĐƯỢC, và ca `C3` của bàn đo G20
    mới là ca đo chính môi trường NGUYÊN BẢN.
    """
    e = dict(os.environ)
    ghi_chu = []
    n = e.get("GIT_CONFIG_COUNT")
    if n and n.isdigit() and int(n) > 0:
        thieu = [i for i in range(int(n)) if not e.get("GIT_CONFIG_KEY_%d" % i)]
        if thieu:
            for k in [k for k in e if k.startswith("GIT_CONFIG_")]:
                e.pop(k, None)
            ghi_chu.append("GỠ gia đình GIT_CONFIG_* dị dạng (thiếu KEY_%s) — N-G18-00"
                           % ",".join(map(str, thieu)))
    return e, ghi_chu


def chay(lenh, giay=1800, env_them=None, cwd=None):
    """Chạy lệnh THẬT, trả `(rc, out)`. `rc` đọc NGAY sau lệnh, KHÔNG qua ống."""
    e, _ = _git_env()
    if env_them:
        e.update(env_them)
    p = subprocess.run(lenh, capture_output=True, text=True, cwd=cwd or GOC_CAY, env=e,
                       timeout=giay, shell=isinstance(lenh, str))
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def chay_con(ma, giay=900, env_them=None):
    """Chạy một đoạn mã Python trong TIẾN TRÌNH CON. Trả `(rc, out, pid_con)`.

    `pid_con` lấy từ chính tiến trình con in ra — đó là BẰNG CHỨNG nó chạy ở tiến trình khác,
    không phải một lời khai trong tài liệu.
    """
    e, _ = _git_env()
    e["VIP_G22_PID_CHA"] = str(os.getpid())
    if env_them:
        e.update(env_them)
    p = subprocess.run([PY, "-c", ma], capture_output=True, text=True, cwd=GOC_CAY, env=e,
                       timeout=giay)
    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"__PID_CON__=(\d+)", out)
    return p.returncode, out, (int(m.group(1)) if m else None)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. SỔ GIÁ TRỊ — HAI Ô, VÀ "NỬA VỜI" LUÔN ĐỎ
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# "nen" = giá trị ĐO ĐƯỢC trên `a3400a8` (lượt G21 của tôi, `docs/QA_G21.md`).
# "dong" = giá trị phải có khi khoản nợ đã đóng.
# Giá trị KHÁC CẢ HAI ⇒ NUA_VOI ⇒ ĐỎ ở MỌI chế độ. Ở chế độ `gop` thì "nen" CŨNG ĐỎ.

SO_DO = {
    # Điểm 1 Supervisor giao — tầng 3 Chromium. Bộ ba (ĐẠT, HỎNG, KHÔNG CHẠY).
    # Nền: (0, 7, 44) — `browserType.launch` chết vì THIẾU NHỊ PHÂN. Đóng: (51, 0, 0).
    #
    # HAI CỔNG, KHÔNG PHẢI MỘT — và đây KHÔNG phải "chạy lại cho xanh":
    #   · `e2e-ban-phim-7` = `06_ban_phim.spec.js` (ĐÚNG 7 ca) — đây là "E2E 7/7" mà Supervisor
    #     giao, và là thứ AG-06 đã chạy. ĐO ĐƯỢC: 3/3 lượt riêng đều (7, 0, 0), TẤT ĐỊNH.
    #   · `e2e-toan-bo` = cả bộ 51 ca. ĐO ĐƯỢC: 4 lượt ⇒ 3 lượt (51,0,0,0) + 1 lượt (49,1,1,0)
    #     ⇒ **CHẬP CHỜN**, xem `N-G22-01`. Giữ nó làm cổng RIÊNG để chỗ chập chờn không bị
    #     trộn lẫn với chỗ tất định.
    "e2e-ban-phim-7": {"nen": (0, 7, 0), "dong": (7, 0, 0)},
    "e2e-toan-bo": {"nen": (0, 7, 44), "dong": (51, 0, 0)},

    # Điểm 2 — cổng "cây sạch" của wave TRƯỚC. Số cổng XANH trên cây chỉ có tệp AG-01 hợp lệ.
    # Nền: 0/3 (cả ba ĐỎ). Đóng: 3/3.
    "cay-sach-3-ban-sao": {"nen": 0, "dong": 3},

    # E3 (điểm 3) — số bản cất `hub-truoc-rollback-*.db` sau BA lượt `khoi_phuc()` trong CÙNG
    # MỘT GIÂY, đo bằng ĐỒNG HỒ ĐÓNG BĂNG (không phụ thuộc tốc độ máy). Nền: 1. Đóng: ≥ 3.
    "e3-ba-luot-cung-giay": {"nen": 1, "dong": 3},

    # N-G21-03 (điểm 4) — `thu_g20_dahang.py::CaGanChat::test_c2a` có còn GHIM hành vi RÒ không.
    # Nền: 1 (còn ghim). Đóng: 0.
    "ng21-03-ca-ghim-ro": {"nen": 1, "dong": 0},
}

# Năm cổng C1..C5 của bàn đo G20 — nguyên văn `SO_DO` của nó, KHÔNG sửa.
SO_DO_G20 = {
    "C1 cổng cây sạch wave trước": {"nen": 0, "dong": 2, "ten_do": "cong-cay-sach"},
    "C2 bàn phím TRONG màn (tầng 3)": {"nen": (3, 1, 3), "dong": (7, 0, 0),
                                       "ten_do": "tang3-ban-phim"},
    "C3 git với môi trường NGUYÊN BẢN": {"nen": 128, "dong": 0, "ten_do": "git-tho"},
    "C4 route truy_van + migration v9": {"nen": (True, False), "dong": (True, True),
                                         "ten_do": "truy-van-C6"},
    "C5 có bộ G19-tổng-hợp chạy được": {"nen": 0, "dong": 1, "ten_do": "bo-g19-tong-hop"},
}


def phan_quyet(ten_cong, do_duoc):
    """'NEN' | 'DONG' | 'NUA_VOI'. Giá trị lửng lơ KHÔNG rơi vào ô nào ⇒ NUA_VOI."""
    o = SO_DO[ten_cong]
    if do_duoc == o["dong"]:
        return "DONG"
    if do_duoc == o["nen"]:
        return "NEN"
    return "NUA_VOI"


def dat_cong(ten_cong, do_duoc):
    """Cổng có ĐẠT không. Ở chế độ `gop` thì chỉ ô 'dong' mới đạt."""
    pq = phan_quyet(ten_cong, do_duoc)
    if pq == "DONG":
        return True, "ĐÓNG"
    if pq == "NUA_VOI":
        return False, ("NỬA VỜI: đo được %r, sổ ghi nền=%r đóng=%r"
                       % (do_duoc, SO_DO[ten_cong]["nen"], SO_DO[ten_cong]["dong"]))
    return (CHE_DO != "gop"), ("còn NỢ (nền=%r, đo được %r)" % (SO_DO[ten_cong]["nen"], do_duoc))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. HAI CHỐT CHẶN — SỔ ĐỐI CHỨNG DƯƠNG + SỔ TIÊM LỖI
# ══════════════════════════════════════════════════════════════════════════════════════════════

# Nhóm ca PHỦ ĐỊNH → tên các ca. Một ca phủ định là ca khẳng định "hệ TỪ CHỐI / KHÔNG làm gì".
CA_PHU_DINH = {
    "e2e-ban-phim-7": ("C_BanPhim.test_b3_e2e_bay_ca_ban_phim_chay_that",),
    "e2e-toan-bo": ("C_BanPhim.test_b2_chay_e2e_toan_bo_that",),
    "cay-sach-3-ban-sao": ("E_CaySach.test_e1_ba_cong_cay_sach_chay_that"),
    "e3-ba-luot-cung-giay": ("F_DongHo.test_f1_do_that_bang_dong_ho_dong_bang",),
    "ng21-03-ca-ghim-ro": ("G_NG2103.test_g1_ca_thu_con_ghim_ro",),
    "g20-c1-cay-sach": ("D_BanDoG20.test_d1_nam_cong_g20",),
    "nua-voi": ("Z_ChotChan.test_z4_gia_tri_nua_voi_luon_la_DO",),
    "cay-sach-bo-do": ("Z_ChotChan.test_z3_bo_do_bat_duoc_khi_bi_tiem",),
    "tien-trinh-con": ("Z_ChotChan.test_z2_tu_kiem_chay_trong_tien_trinh_con",),
    "c5-tru-bo-qua": ("I_TiemLoiC5.test_i1_nam_di_dang_tiem_loi",),
}

# ĐỐI CHỨNG DƯƠNG: mỗi nhóm phủ định PHẢI có một ca chạy ĐÚNG đường đó và cho kết quả KHÁC.
DOI_CHUNG = {
    "e2e-ban-phim-7":
        "chính bảy ca đó phải ĐẠT HẾT; nếu 0 đạt thì 'hỏng' không phân biệt được "
        "với 'KHÔNG CHẠY ĐƯỢC vì thiếu nhị phân' — đúng thứ đã xảy ra ở lượt G21 (7 hỏng + "
        "44 không chạy, 0 tín hiệu).",
    "e2e-toan-bo":
        "cùng `chay.sh` phải ĐẠT ≥1 ca; nếu 0 đạt thì 'hỏng' không phân biệt được với 'không "
        "chạy được' (đúng thứ đã xảy ra ở lượt G21: 7 hỏng + 44 không chạy, 0 tín hiệu).",
    "cay-sach-3-ban-sao":
        "TIÊM: đặt một tệp bẩn NGOÀI vùng thử (`admin/__tiem_g22.js`) rồi chạy lại cổng — cổng "
        "phải ĐỎ. Không có vế này thì '3/3 xanh' có thể chỉ là cổng mù.",
    "e3-ba-luot-cung-giay":
        "chạy CÙNG kịch bản với `G21_APP_DIR` trỏ vào bản `migrate.py` ĐÃ VÁ (thêm hậu số): số "
        "bản cất phải ≥3. Không có vế này thì 'đỏ' không phân biệt được với 'bộ đo hỏng'.",
    "ng21-03-ca-ghim-ro":
        "chạy `thu_qa_g21.py` nhóm `G5_CredentialNgan` — một bộ đo ĐỘC LẬP với ca kia: nó phải "
        "báo >0 tổ hợp RÒ. Không có vế này thì 'ca xanh' không phân biệt được với 'hết rò'.",
    "g20-c1-cay-sach":
        "C2 của cùng bàn đo G20 phải ĐO ĐƯỢC (7 ca tầng 3 chạy thật) — chứng minh bàn đo không "
        "chết toàn bộ khi C1 đỏ.",
    "nua-voi":
        "bơm giá trị nằm GIỮA nền và đóng; `phan_quyet` phải trả NUA_VOI và cổng phải ĐỎ.",
    "cay-sach-bo-do":
        "TIÊM một giá trị SAI vào bộ phân loại; bộ phân loại phải gọi nó là ĐỎ-THẬT.",
    "tien-trinh-con":
        "cùng ca tự kiểm chạy ở tiến trình CHA: biến toàn cục PHẢI nhìn thấy được (đối chứng âm "
        "của vế 'không nhìn thấy ở cha').",
    "c5-tru-bo-qua":
        "DỰNG THẬT cả năm dị dạng rồi chạy CHÍNH hai cổng của HAI TỆP NGUỒN (`C5` trong "
        "`thu_qa_g20.py`, `G7` trong `thu_qa_g21.py`) trên cây gương: bốn dị dạng đầu ĐỎ ở CẢ HAI "
        "cột, dị dạng thứ năm (`MOI CA BO QUA o muc PHUONG THUC`) XANH ở cột TRƯỚC và ĐỎ ở cột "
        "SAU — ở CẢ HAI cổng. Không có vế 'TRƯỚC' thì không chứng minh được lỗ hổng CÓ THẬT; "
        "không có vế SAU thì không chứng minh được nó ĐÃ ĐÓNG — và `I2` chứng minh bản vá không "
        "quá tay (vẫn XANH trước một bộ CHẠY THẬT).",
}

DA_CHAY = {}     # nhóm → True khi đối chứng dương THẬT SỰ chạy
DA_TIEM = {}     # nhóm → True khi đã TIÊM LỖI và bộ đo BẮT ĐƯỢC


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. GIT — MÔI TRƯỜNG ĐO, VÀ CÁCH NÓ ĐƯỢC KHAI RA THAY VÌ ĐƯỢC GIẤU
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# MỘT SỰ THẬT CỦA MÔI TRƯỜNG NÀY, ĐO ĐƯỢC VÀ PHẢI KHAI:
#
#   Sandbox CHẶN ghi `.git`:
#       $ git checkout 7344c02
#       fatal: Unable to create '…/.git/worktrees/g21-ag01-qa/index.lock': Operation not permitted
#   ⇒ trong worktree `g21-ag01-qa`, `HEAD` đứng ở `601718e` trong khi CÂY đã là `7344c02`.
#
# Hệ quả ĐÃ ĐO ĐƯỢC (`qa_g22_lan1_nhiem.log`): mọi cổng "cây sạch" chạy `git diff HEAD` thấy
# **13 đường bẩn NGOÀI vùng thử** — nhưng đó là delta GIỮA HAI COMMIT, không phải thay đổi của
# người đo. Một cái ĐỎ GIẢ của môi trường.
#
# Tôi đã thử hai đường "chữa", và GHI LẠI CẢ HAI vì chúng đều HỎNG — đây là bằng chứng, không
# phải lời kể:
#
#   (1) `GIT_DIR` BÓNG trong `TMP` (HEAD=7344c02, index=7344c02, mượn `refs/` của kho chung).
#       Chạy tốt cho tới khi một bộ thử KHÁC gọi `git init <thư-mục-tạm>` — mà `GIT_DIR` thì ĐÈ
#       lên đích của `git init`, nên nó `init` thẳng vào `GIT_DIR` bóng và ghi `bare = true` vào
#       đó. Sau phút 16:34 của lượt `qa_g22_lan4`, MỌI lệnh `git ls-files --others` trả 128
#       (`fatal: unable to set up work tree using invalid config`) và `thu_g21_chotcay.py` lỗ
#       8/13 ca — ĐỎ GIẢ hoàn toàn do môi trường đo.
#   (2) Bản sao THẬT: `git clone --shared --no-checkout <kho> $CP && git checkout --detach
#       7344c02`. Đây là một kho BÌNH THƯỜNG có `HEAD` = nền và cây SẠCH, nên `git init` của
#       bộ khác không chạm tới nó, và mọi cổng "cây sạch" đo được ĐÚNG cái chúng định đo.
#
# ⇒ CÁCH CHẠY ĐÚNG CỦA BỘ KIỂM NÀY LÀ TRONG MỘT CÂY CÓ `HEAD` = `NEN_SHA`. Bộ kiểm TỰ ĐO điều
#   đó (`git rev-parse HEAD`) và, khi nó KHÔNG đúng, nói thẳng ra và TỪ CHỐI phán quyết trên
#   những cổng bị môi trường làm nhiễu — thay vì bỏ qua im lặng hoặc báo đỏ giả.

def _git(*tham_so, **kw):
    return chay(["git"] + list(tham_so), **kw)


def head_hien_tai():
    rc, out = _git("rev-parse", "HEAD")
    return out.strip() if rc == 0 else ""


def tree_hien_tai():
    rc, out = _git("write-tree")
    return out.strip() if rc == 0 else "LỖI(rc=%d)" % rc


def delta_head_voi_nen():
    """Các đường KHÁC NHAU giữa HEAD hiện tại và nền — TỰ TÍNH, không viết cứng.

    Khi `HEAD == NEN_SHA` thì hàm này trả `[]`, nên ở môi trường bình thường KHÔNG có gì được
    miễn trừ. Khi `HEAD != NEN_SHA` (chỉ xảy ra trong worktree bị sandbox chặn ghi `.git`), nó
    trả ĐÚNG delta của hai commit — và đó là căn cứ ĐO ĐƯỢC để miễn trừ, không phải một ngoại lệ
    ai đó dán vào cho xanh.
    """
    h = head_hien_tai()
    if not h or h == NEN_SHA:
        return []
    rc, out = _git("diff", "--name-only", h, NEN_SHA)
    return [d.strip() for d in out.splitlines() if d.strip()] if rc == 0 else []


def van_tay(env_git_dir=None):
    """Vân tay cây: HEAD, tree, và băm danh sách tệp theo dõi. Trả dict."""
    env_them = {"GIT_DIR": env_git_dir} if env_git_dir else {}
    ra = {}
    for ten, tham in (("head", ("rev-parse", "HEAD")), ("tree", ("write-tree",)),
                      ("so_tep", ("ls-files",))):
        rc, out = chay(["git"] + list(tham), env_them=env_them)
        ra[ten] = out.strip() if rc == 0 else "LỖI(rc=%d)" % rc
    rc, out = chay(["git", "ls-files", "-s"], env_them=env_them)
    ra["bam_danh_sach"] = hashlib.sha256(out.encode()).hexdigest() if rc == 0 else "LỖI"
    ra["so_tep"] = str(len([x for x in ra["so_tep"].splitlines() if x.strip()]))
    return ra


def trang_thai(env_git_dir=None):
    env_them = {"GIT_DIR": env_git_dir} if env_git_dir else {}
    rc, out = chay(["git", "status", "--porcelain", "-uall"], env_them=env_them)
    return rc, [d for d in out.splitlines() if d.strip()]


def duong_cua_dong_status(dong):
    """`' M admin/admin.js'` → `'admin/admin.js'` (bỏ trạng thái, xử lý cả `R  a -> b`)."""
    p = dong[3:].strip().strip('"')
    if " -> " in p:
        p = p.split(" -> ", 1)[1]
    return p


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. CÁC PHÉP ĐO DÙNG LẠI
# ══════════════════════════════════════════════════════════════════════════════════════════════

def dem_playwright(text):
    """→ (đạt, hỏng, bỏ_qua, KHÔNG_CHẠY). `did not run` là phán quyết RIÊNG, không gộp ĐẠT."""
    def _so(mau):
        m = re.search(mau, text)
        return int(m.group(1)) if m else 0
    return (_so(r"(\d+) passed"), _so(r"(\d+) failed"), _so(r"(\d+) skipped"),
            _so(r"(\d+) did not run"))


def chromium_duong_dan():
    """→ (đường_dẫn, nguồn) của nhị phân Chromium CHỈ ĐỊNH. `None` nếu không có."""
    ung_vien = [
        (os.path.join(PW_BROWSERS_REPO, *PW_CHROMIUM_TUONG_DOI),
         "trong repo (chay.sh ghim PLAYWRIGHT_BROWSERS_PATH=0)"),
        (os.path.join(PW_BROWSERS_G17, *PW_CHROMIUM_TUONG_DOI),
         "BAN_GIAO §1 / AG-06 đã chạy thành công"),
        (os.path.join(PW_BROWSERS_CHI_DINH, *PW_CHROMIUM_TUONG_DOI),
         "cùng nhị phân qua worktree g12-playwright"),
    ]
    for p, nguon in ung_vien:
        if os.path.exists(p):
            return p, nguon
    return None, None


def phien_ban_chromium(p):
    rc, out = chay([p, "--version"], giay=60)
    return rc, out.strip()


def revision_playwright_doi():
    p = os.path.join(GOC_CAY, "node_modules", "playwright-core", "browsers.json")
    if not os.path.exists(p):
        return None, None
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    pb = None
    pp = os.path.join(GOC_CAY, "node_modules", "playwright-core", "package.json")
    if os.path.exists(pp):
        with open(pp, encoding="utf-8") as f:
            pb = json.load(f).get("version")
    for b in d.get("browsers", []):
        if b.get("name") == "chromium":
            return str(b.get("revision")), pb
    return None, pb


def chay_e2e(bo_loc=None, giay=900):
    """Chạy `sh thu_giao_dien/chay.sh [bo_loc]` — BỘ CHẠY CHÍNH THỨC của dự án."""
    lenh = ["sh", "thu_giao_dien/chay.sh"] + ([bo_loc] if bo_loc else [])
    t0 = time.time()
    rc, out = chay(lenh, giay=giay)
    return {"rc": rc, "out": out, "giay": round(time.time() - t0, 1),
            "dem": dem_playwright(out), "lenh": " ".join(lenh)}


def doc_so_chay_tat_ca(text):
    """Bóc số từ BẢNG TỔNG KẾT của `chay_tat_ca.sh`. Trả dict hoặc None nếu không thấy bảng."""
    ra = {}
    m = re.search(r"python:\s+(\d+) ca · (\d+) bộ chạy thật", text)
    if m:
        ra["ca"] = int(m.group(1))
        ra["bo_chay_that"] = int(m.group(2))
    m = re.search(r"\+\s*(\d+) bộ BỎ QUA \(0 ca\)", text)
    ra["bo_bo_qua"] = int(m.group(1)) if m else 0
    m = re.search(r"E2E:\s+(\S+)", text)
    ra["e2e"] = m.group(1) if m else ""
    m = re.search(r"bộ hỏng:\s*(.*)", text)
    ra["bo_hong"] = (m.group(1).strip() if m else "").strip()
    ds = [x for x in re.findall(r"^  ([✓✗⊘]) (\S+)", text, re.M)]
    ra["so_dong_ket_qua"] = len(ds)
    ra["hong"] = [t for k, t in ds if k == "✗"]
    ra["bo_qua"] = [t for k, t in ds if k == "⊘"]
    ra["dat"] = [t for k, t in ds if k == "✓"]
    return ra if "ca" in ra else None


def _bam(duong):
    with open(duong, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _hoan_va(than, cap):
    """Thay NGƯỢC: khối SAU khi vá → khối TRƯỚC khi vá. `None` nếu có khối không khớp đúng 1 lần."""
    for cu, moi in cap:
        if than.count(moi) != 1:
            return None
        than = than.replace(moi, cu)
    return than


def nguon_goc(duong, cap, sha_goc):
    """Nội dung GỐC (trước khi vá) của tệp nguồn `duong`, KIỂM BẰNG sha256. Trả `(nội_dung, ghi_chú)`.

    `nội_dung is None` nghĩa là KHÔNG chứng minh được "bản gốc đã ghim + ĐÚNG hai khối vá" ⇒ người
    gọi DỪNG, chứ không đo bằng một bàn đo đã trôi. Đây là chốt thay cho `BAN_DO_G20_SHA` cũ: bản
    vá nay nằm TRONG tệp nguồn, nên "gốc" được dựng lại bằng HOÀN VÁ rồi băm — không cần bản sao.
    """
    if not os.path.exists(duong):
        return None, "KHÔNG có tệp nguồn `%s`" % duong
    with open(duong, encoding="utf-8") as f:
        than = f.read()
    goc = _hoan_va(than, cap)
    if goc is None:
        return None, ("KHÔNG hoàn vá được `%s`: khối vá không còn khớp nguyên văn ⇒ tệp trong cây "
                      "KHÔNG PHẢI 'bản gốc + đúng hai khối vá'" % os.path.basename(duong))
    ra = hashlib.sha256(goc.encode("utf-8")).hexdigest()
    if ra != sha_goc:
        return None, ("hoàn vá xong, sha256 = %s ≠ ghim %s ⇒ tệp nguồn `%s` đã TRÔI khỏi bản gốc "
                      "(không đo bằng một bàn đo đã trôi)"
                      % (ra[:16], sha_goc[:16], os.path.basename(duong)))
    return goc, ("`%s`: gốc ghim %s ✓ + đúng %d khối vá"
                 % (os.path.basename(duong), sha_goc[:12], len(cap)))


def nguon_da_va(duong, cap, sha_goc):
    """Xác nhận tệp TRONG CÂY = bản gốc đã ghim + đúng hai khối vá. Trả `(ok, ghi_chú)`."""
    goc, ghi_chu = nguon_goc(duong, cap, sha_goc)
    if goc is None:
        return False, ghi_chu
    with open(duong, encoding="utf-8") as f:
        than = f.read()
    if "nc > 0" not in than or "skipped=(\\d+)" not in than:
        return False, "`%s` thiếu dấu vết bản vá (`skipped=`/`nc > 0`)" % os.path.basename(duong)
    if cap[1][0] in than:
        return False, "`%s` còn nguyên văn CŨ của khối quyết định" % os.path.basename(duong)
    return True, ghi_chu + " · bản trong cây ĐÃ VÁ"


# ── BẢN VÁ `N-G22-01` — HAI KHỐI BỘ ĐẾM, VÁ **THẲNG Ở TỆP NGUỒN** ─────────────────────────────
#
# BÀI HỌC (giữ nguyên — nó là lý do bộ đếm này tồn tại): bàn đo G20 kiểm "có bộ G19-tổng-hợp CHẠY
# THẬT" bằng `Ran N tests` với `N > 0`. Nhưng `unittest` KỂ CẢ ca BỎ QUA trong `N`: một bộ mà MỌI
# ca đều `@unittest.skip` in `Ran 3 tests` + `OK (skipped=3)` rồi thoát 0 — ĐÚNG khuôn một lượt
# chạy tốt — nên `C5` báo `1/2 · ĐÓNG` (XANH) dù KHÔNG ca nào chạy. Bốn dị dạng khác thì `C5` bắt
# được; dị dạng thứ NĂM này thì không. Xem `docs/QA_G22.md` §7 `N-G22-01`.
#
# LƯỢT NÀY VÁ Ở ĐÂU: **THẲNG trong `app/thu/thu_qa_g20.py` (`C5`) và `app/thu/thu_qa_g21.py`
# (`G7`)**. KHÔNG còn `g20_cop_tam()`/`g20_va_c5()`: một bản chép tạm có thể XANH trong khi NGUỒN
# vẫn lỗ, và đó đúng là loại lỗi wave này đang diệt.
#
# Hai tuple dưới đây là ĐỊNH NGHĨA của bản vá, dùng theo cả HAI CHIỀU:
#   · chiều thuận (cũ → mới) để biết bản trong cây ĐÃ VÁ đúng chưa;
#   · chiều NGƯỢC (mới → cũ) để dựng lại BẢN GỐC cho cột "TRƯỚC" của bảng §7 — rồi BĂM, phải ra
#     đúng `BAN_DO_G20_GOC_SHA`/`BAN_DO_G21_GOC_SHA`. Không khớp ⇒ DỪNG, không đo.
G20_C5_VA = (
    # (nguyên văn trong bản gốc, nguyên văn sau khi vá)
    ('            m = re.findall(r"Ran (\\d+) tests?", ra)\n'
     '            n = int(m[-1]) if m else 0\n'
     '            chi_tiet.append((t, ma, n))\n'
     '            print("       %s → mã thoát %s · %d ca" % (t, ma, n))\n',

     '            m = re.findall(r"Ran (\\d+) tests?", ra)\n'
     '            n = int(m[-1]) if m else 0\n'
     '            # VÁ `N-G22-01`: `Ran N` KỂ ca BỎ QUA ⇒ phải TRỪ ra mới biết có ca nào CHẠY.\n'
     '            bq = int((re.findall(r"skipped=(\\d+)", ra) or ["0"])[-1])\n'
     '            chi_tiet.append((t, ma, n, bq, max(n - bq, 0)))\n'
     '            print("       %s → mã thoát %s · %d ca · %d BỎ QUA · %d CHẠY THẬT"\n'
     '                  % (t, ma, n, bq, max(n - bq, 0)))\n'),

    ('        chay = min(sum(1 for _, ma, n in chi_tiet if ma == 0 and n > 0), 1)\n',

     '        # XANH chỉ khi có ca THẬT SỰ CHẠY và ĐẠT: `nc > 0` (ĐÃ TRỪ bỏ qua), không phải `n > 0`.\n'
     '        chay = min(sum(1 for _, ma, n, bq, nc in chi_tiet\n'
     '                       if ma == 0 and n > 0 and nc > 0), 1)\n'),
)


# Cổng `G7` của bàn đo G21 (`app/thu/thu_qa_g21.py`) là BẢN SAO của cùng bộ đếm đó. Khối 1 KHÁC
# đúng một chỗ: vòng lặp của `G7` không in trong vòng lặp (nó in ở cuối). Hai khối CÒN LẠI GIỐNG
# HỆT TỪNG KÝ TỰ — và điều đó được BẢO ĐẢM BẰNG MÃ chứ không bằng lời khai: `G21_G7_VA` lấy thẳng
# hai khối của `G20_C5_VA`.
_C1_CU_G21 = ('            m = re.findall(r"Ran (\\d+) tests?", ra)\n'
              '            n = int(m[-1]) if m else 0\n'
              '            chi_tiet.append((t, ma, n))\n')
_C3_CU_G21 = ('        for t, ma, n in chi_tiet:\n'
              '            print("       %s → mã thoát %s · %d ca" % (t, ma, n))\n')
_C3_MOI_G21 = ('        for t, ma, n, bq, nc in chi_tiet:\n'
               '            print("       %s → mã thoát %s · %d ca · %d BỎ QUA · %d CHẠY THẬT"\n'
               '                  % (t, ma, n, bq, nc))\n')

G21_G7_VA = (
    (_C1_CU_G21, G20_C5_VA[0][1]),   # khối ĐẾM — nguyên văn SAU khi vá GIỐNG HỆT khối của `C5`
    G20_C5_VA[1],                    # khối QUYẾT ĐỊNH — GIỐNG HỆT từng ký tự
    (_C3_CU_G21, _C3_MOI_G21),       # khối TRÌNH BÀY — chỉ `G7` có, vì nó in ở vòng riêng
)


# ── E3: ĐỒNG HỒ ĐÓNG BĂNG + ĐỐI CHỨNG ĐƯỜNG BẰNG BẢN ĐÃ VÁ ───────────────────────────────────
#
# VÌ SAO PHẢI ĐÓNG BĂNG ĐỒNG HỒ: `khoi_phuc()` đặt tên bản cất theo GIÂY
# (`hub-truoc-rollback-%Y%m%d-%H%M%S.db`). Ba lượt gọi liền nhau trong CÙNG một giây ⇒ cùng
# tên ⇒ lượt sau ĐÈ lượt trước. Nhưng nếu ba lượt đó VÔ TÌNH rơi vào HAI giây khác nhau thì
# phép đếm ra ≥2 và ca thử XANH **dù lỗi còn nguyên** — một cái XANH GIẢ phụ thuộc TỐC ĐỘ MÁY.
# Đó là "xanh khi chung, đỏ khi riêng" mà Supervisor giao kiểm chứng.
#
# Cách đo ở đây KHÔNG dựa vào may rủi và KHÔNG che bằng retry: nó TIÊM một `migrate` có
# `datetime.now()` ĐÓNG BĂNG, nên ba lượt gọi CHẮC CHẮN cùng một giây. Kết quả vì thế TẤT ĐỊNH.

MA_E3 = r'''
import hashlib, json, os, shutil, sqlite3, sys
APP = os.environ["G22_APP"]
sys.path.insert(0, APP)
import datetime as _dt

class _DongBang(_dt.datetime):
    _T = _dt.datetime(2026, 10, 16, 12, 0, 0)
    @classmethod
    def now(cls, tz=None):
        return cls._T
    @classmethod
    def utcnow(cls):
        return cls._T
    @classmethod
    def today(cls):
        return cls._T

import migrate
migrate.datetime = _DongBang          # `datetime.now()` trong `migrate` nay ĐÓNG BĂNG

D = os.environ["VIP_HUB_DATA"]
os.makedirs(D, exist_ok=True)
TL = os.path.join(D, "sao-luu")
os.makedirs(TL, exist_ok=True)
DB = os.path.join(D, "hub.db")
c = sqlite3.connect(DB)
c.execute("CREATE TABLE t (x INTEGER)")
c.execute("INSERT INTO t VALUES (1)")
c.commit(); c.close()

def dem():
    return sorted(f for f in os.listdir(TL) if "rollback" in f and f.endswith(".db"))

# (A) ĐỐI CHỨNG DƯƠNG NGAY TRONG CÙNG TIẾN TRÌNH: `sao_luu()` ĐÃ ĐƯỢC VÁ (thêm hậu số).
#     Với CÙNG đồng hồ đóng băng, nó PHẢI ra ≥ 2 tệp khác nhau. Vế này chứng minh
#     (i) đồng hồ đóng băng THẬT SỰ có hiệu lực, và (ii) phép đếm NHÌN THẤY được sự khác nhau.
sl = [migrate.sao_luu() for _ in range(3)]
so_sao_luu = len(set(sl))

# (B) PHÉP ĐO: ba lượt `khoi_phuc()` với CÙNG đồng hồ đóng băng.
ban = os.path.join(D, "nguon.db")
shutil.copy2(DB, ban)
for _ in range(3):
    migrate.khoi_phuc(ban)
ds = dem()
print("__JSON__=" + json.dumps({
    "so_sao_luu_khac_nhau": so_sao_luu,
    "so_ban_cat_rollback": len(ds),
    "ten_ban_cat": ds,
    "luc_dong_bang": _DongBang.now().strftime("%Y%m%d-%H%M%S"),
}))
'''


def _app_tam(ten, va_khoi_phuc=False):
    """Dựng một bản `app/` trong thư mục TẠM; tuỳ chọn VÁ `khoi_phuc()` để làm ĐỐI CHỨNG ĐƯỜNG.

    Đây là đường TIÊM LỖI/ĐỐI CHỨNG mà `trien_khai/g20-saoluu/kich_ban.py` đã mở sẵn qua
    `G21_APP_DIR` — không sửa một byte nào của cây thật.
    """
    d = tempfile.mkdtemp(prefix="g22-app-%s-" % ten)
    shutil.copytree(GOC_APP, d, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    mg = os.path.join(d, "migrate.py")
    with open(mg, encoding="utf-8") as f:
        nguon = f.read()
    if va_khoi_phuc:
        cu = ('    cat_di = os.path.join(THU_MUC_SAO_LUU,\n'
              '                          "hub-truoc-rollback-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".db")')
        moi = ('    _goc = os.path.join(THU_MUC_SAO_LUU,\n'
               '                           "hub-truoc-rollback-" + datetime.now().strftime("%Y%m%d-%H%M%S"))\n'
               '    cat_di, _n = _goc + ".db", 1\n'
               '    while os.path.exists(cat_di):\n'
               '        cat_di = "%s-%d.db" % (_goc, _n)\n'
               '        _n += 1')
        if cu not in nguon:
            raise RuntimeError("không vá được `khoi_phuc`: đoạn gốc không khớp nguyên văn")
        nguon = nguon.replace(cu, moi, 1)
    with open(mg, "w", encoding="utf-8") as f:
        f.write(nguon)
    return d


def do_e3(app_dir):
    """Chạy phép đo E3 với một `app/` cho trước. Trả dict số đo THẬT."""
    nen = tempfile.mkdtemp(prefix="g22-e3-")
    rc, out, _ = chay_con(MA_E3, giay=300, env_them={"VIP_HUB_DATA": nen, "G22_APP": app_dir})
    m = re.search(r"__JSON__=(\{.*\})", out)
    shutil.rmtree(nen, ignore_errors=True)
    if rc != 0 or not m:
        return {"rc": rc, "loi": out.strip()[-600:], "so_sao_luu_khac_nhau": None,
                "so_ban_cat_rollback": None}
    d = json.loads(m.group(1))
    d["rc"] = rc
    return d


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. CÁC LỚP CA
# ══════════════════════════════════════════════════════════════════════════════════════════════

class A_Nen(unittest.TestCase):
    """NỀN — cây nào đang được đo. Sai nền thì mọi số dưới đây vô nghĩa."""

    def test_a1_cay_dung_bang_cay_cua_nen(self):
        """CÂY (không phải nhãn) phải bằng cây `7344c02`.

        Đây là ca trả lời đúng câu hỏi "anh đo trên cái gì", và nó trả lời bằng `write-tree`,
        một giá trị nội dung — không bằng tên nhánh.
        """
        vt = van_tay()
        print("\n  [A1] HEAD=%s · write-tree=%s · %s tệp theo dõi · băm danh sách=%s"
              % (vt["head"][:12], vt["tree"][:12], vt["so_tep"], vt["bam_danh_sach"][:16]))
        print("       nền đề bài: SHA=%s · tree=%s" % (NEN_SHA[:12], TREE_NEN[:12]))
        self.assertEqual(
            vt["tree"], TREE_NEN,
            "CÂY ĐANG ĐO KHÔNG PHẢI CÂY CỦA `%s`. Mọi con số của bộ kiểm này chỉ có nghĩa trên "
            "đúng cây đó." % NEN_SHA[:12])

    def test_a2_khong_sua_ma_san_pham(self):
        """Chỉ được có ĐÚNG hai tệp mới của AG-01 G22; không sửa mã sản phẩm.

        Miễn trừ duy nhất — và nó được TÍNH RA, không được dán vào: khi `HEAD != NEN_SHA` (chỉ
        xảy ra trong worktree bị sandbox chặn ghi `.git`), `git status` so cây với HEAD CŨ nên nó
        kể ra delta của HAI COMMIT. Delta đó lấy từ `git diff --name-only HEAD NEN_SHA`.
        Ở môi trường bình thường (`HEAD == NEN_SHA`) delta RỖNG, nên không có gì được tha.
        """
        rc, ds = trang_thai()
        self.assertEqual(rc, 0, "`git status` hỏng (rc=%d) — không đo được cây" % rc)
        la = [d for d in ds if d.strip()]
        delta = set(delta_head_voi_nen())
        duoc_phep = [d for d in la
                     if any(duong_cua_dong_status(d).endswith(t) for t in TEP_DUOC_PHEP)]
        mien_tru = [d for d in la if duong_cua_dong_status(d) in delta and d not in duoc_phep]
        ngoai = [d for d in la if d not in duoc_phep and d not in mien_tru]
        print("\n  [A2] `status --porcelain -uall`: %d đường = %d tệp được phép + %d delta HEAD↔nền "
              "+ %d NGOÀI phép" % (len(la), len(duoc_phep), len(mien_tru), len(ngoai)))
        for d in ngoai:
            print("       %s" % d)
        if delta:
            print("       ⚠ HEAD=%s ≠ nền=%s ⇒ miễn trừ %d đường là DELTA HAI COMMIT (đo được: "
                  "`git diff --name-only HEAD %s`). Chạy trong cây có HEAD=nền thì delta RỖNG."
                  % (head_hien_tai()[:8], NEN_SHA[:8], len(delta), NEN_SHA[:8]))
        else:
            print("       HEAD == nền ⇒ delta RỖNG, KHÔNG đường nào được miễn trừ ngoài hai tệp "
                  "AG-01 G22")
        self.assertEqual(ngoai, [], "có thay đổi NGOÀI hai tệp được phép")

    def test_a3_csdl_nghiep_vu_van_la_sqlite_D8(self):
        """D-8: CSDL nghiệp vụ vẫn SQLite. Không một kết nối nào tới `:5432`."""
        rc, out = chay([PY, "-c",
                        "import sys; sys.path.insert(0,'app'); import csdl;"
                        " print(csdl.PHIEN_BAN_SCHEMA)"])
        self.assertEqual(rc, 0, "không nạp được `csdl`: %s" % out[-300:])
        self.assertRegex(out.strip(), r"^\d+$")
        print("\n  [A3] `PHIEN_BAN_SCHEMA`=%s · CSDL nghiệp vụ = SQLite (D-8 giữ nguyên)"
              % out.strip())

    def test_a4_cum_5432_khong_bi_dung_toi(self):
        """Đối chứng dương: cổng 5432 CÓ tồn tại trên máy (nên phép đo không rỗng), và bộ kiểm
        này KHÔNG mở kết nối nào tới nó."""
        import socket
        s = socket.socket()
        s.settimeout(0.6)
        try:
            s.connect(("127.0.0.1", 5432))
            co = True
        except OSError:
            co = False
        finally:
            s.close()
        print("\n  [A4] cổng 5432 trên máy: %s · bộ kiểm này mở 0 kết nối tới nó"
              % ("CÓ người nghe" if co else "không ai nghe"))
        self.assertTrue(True)


class C_BanPhim(unittest.TestCase):
    """ĐIỂM 1 Supervisor giao — tầng 3 Chromium PHẢI chạy, KHÔNG được bỏ qua."""

    def test_b1_chi_dinh_dung_nhi_phan_chromium(self):
        """Ghim ĐƯỜNG DẪN + PHIÊN BẢN của nhị phân đã dùng thành công ở AG-06."""
        rev, pb = revision_playwright_doi()
        p, nguon = chromium_duong_dan()
        print("\n  [B1] playwright-core=%s · `browsers.json` đòi chromium revision=%s" % (pb, rev))
        if p is None:
            self.fail("KHÔNG CHẠY ĐƯỢC: không có nhị phân Chromium ở bất kỳ đường chỉ định nào. "
                      "Đây là KẾT QUẢ, không phải chỗ để bỏ qua.")
        rc, ver = phien_ban_chromium(p)
        self.assertEqual(rc, 0, "nhị phân không thi hành được (rc=%d): %s" % (rc, ver))
        print("       ĐƯỜNG DẪN: %s" % p)
        print("       realpath : %s" % os.path.realpath(p))
        print("       PHIÊN BẢN: %s" % ver)
        print("       NGUỒN    : %s" % nguon)
        self.assertRegex(ver, r"Chromium \d+\.\d+\.\d+\.\d+", "không đọc được phiên bản Chromium")
        self.assertEqual(rev, PW_REVISION_DOI,
                         "`browsers.json` đổi revision ⇒ nhị phân chỉ định có thể đã lạc hậu")

    def test_b2_chay_e2e_toan_bo_that(self):
        """CHẠY THẬT `sh thu_giao_dien/chay.sh`. HỎNG nếu không chạy được — KHÔNG bỏ qua."""
        DA_CHAY["e2e-toan-bo"] = True
        kq = chay_e2e(giay=1200)
        dat, hong, bo, khong_chay = kq["dem"]
        print("\n  [B2] LỆNH: %s" % kq["lenh"])
        print("       mã thoát THẬT = %d · %.1f giây" % (kq["rc"], kq["giay"]))
        print("       (đạt, hỏng, bỏ qua, KHÔNG CHẠY) = (%d, %d, %d, %d)" % (dat, hong, bo, khong_chay))
        with open(os.path.join(LOG_DIR, "e2e_lan_nay.txt"), "w", encoding="utf-8") as f:
            f.write(kq["out"])
        if dat == 0:
            self.fail("KHÔNG CHẠY ĐƯỢC: 0 ca ĐẠT. Đây là KẾT QUẢ (thiếu nhị phân / máy chủ không "
                      "lên), KHÔNG phải chỗ để `skipTest`. 60 dòng cuối:\n%s"
                      % "\n".join(kq["out"].splitlines()[-60:]))
        # ĐỐI CHỨNG DƯƠNG: ≥1 ca đạt ⇒ "hỏng" phân biệt được với "không chạy được".
        self.assertGreater(dat, 0)
        _dc_duong("e2e-toan-bo")
        do_duoc = (dat, hong, khong_chay)
        dat_cong_, vi = dat_cong("e2e-toan-bo", do_duoc)
        print("       phân quyết: %s" % phan_quyet("e2e-toan-bo", do_duoc))
        self.assertTrue(dat_cong_, "CỔNG `e2e-toan-bo` ĐỎ: %s" % vi)


    def test_b3_e2e_bay_ca_ban_phim_chay_that(self):
        """ĐIỂM 1 SUPERVISOR GIAO, ĐO RIÊNG: `06_ban_phim.spec.js` — ĐÚNG 7 CA.

        Vì sao tách khỏi `test_b2`: bộ 51 ca **CHẬP CHỜN** (đo được: 4 lượt ⇒ 3 lượt 51/0/0/0 và
        1 lượt 49/1/1/0 — xem `N-G22-01`). Trộn hai phép đo vào một cổng là để chỗ chập chờn che
        chỗ tất định. Đây **KHÔNG** phải "chạy lại cho xanh": đây là **một phép đo KHÁC** — đúng
        bảy ca mà AG-06 đã chạy và đúng cái "E2E 7/7" mà đề bài hỏi.
        """
        DA_CHAY["e2e-ban-phim-7"] = True
        kq = chay_e2e("06_ban_phim.spec.js", giay=600)
        dat, hong, bo, khong_chay = kq["dem"]
        print("\n  [B3] LỆNH: %s" % kq["lenh"])
        print("       mã thoát THẬT = %d · %.1f giây" % (kq["rc"], kq["giay"]))
        print("       (đạt, hỏng, bỏ qua, KHÔNG CHẠY) = (%d, %d, %d, %d)" % (dat, hong, bo, khong_chay))
        with open(os.path.join(LOG_DIR, "e2e_ban_phim_7.txt"), "w", encoding="utf-8") as f:
            f.write(kq["out"])
        self.assertGreater(dat, 0,
                           "KHÔNG CHẠY ĐƯỢC: 0 ca ĐẠT. Đây là KẾT QUẢ, KHÔNG phải chỗ để "
                           "`skipTest`. 40 dòng cuối:\n%s"
                           % "\n".join(kq["out"].splitlines()[-40:]))
        _dc_duong("e2e-ban-phim-7")
        do_duoc = (dat, hong, khong_chay)
        dat_cong_, vi = dat_cong("e2e-ban-phim-7", do_duoc)
        print("       phân quyết: %s" % phan_quyet("e2e-ban-phim-7", do_duoc))
        self.assertTrue(dat_cong_, "CỔNG `e2e-ban-phim-7` ĐỎ: %s" % vi)


class D_BanDoG20(unittest.TestCase):
    """VIỆC (b) — chạy `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py` và ghi C1..C5."""

    _kq = None

    @classmethod
    def setUpClass(cls):
        cls._kq = {"chay_duoc": False}

    def test_d1_nam_cong_g20(self):
        DA_CHAY["g20-c1-cay-sach"] = True
        # KHÔNG chép, KHÔNG vá một bản sao: TỆP NGUỒN trong cây phải ĐÃ VÁ, và phải CHỨNG MINH được
        # nó là "bản gốc đã ghim + đúng hai khối vá" — bằng cách HOÀN VÁ rồi băm (`nguon_da_va`).
        ok, ghi_chu = nguon_da_va(BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA)
        print("\n  [D1] bàn đo G20 = TỆP NGUỒN trong cây `app/thu/thu_qa_g20.py`: %s" % ghi_chu)
        if not ok:
            self.fail("TỆP NGUỒN `app/thu/thu_qa_g20.py` KHÔNG PHẢI 'bản gốc đã ghim + đúng hai "
                      "khối vá': %s. Đây là KẾT QUẢ, không phải chỗ bỏ qua." % ghi_chu)
        env = {"VIP_G20_CHE_DO": "gop"}
        t0 = time.time()
        rc, out = chay([PY, "app/thu/thu_qa_g20.py"], giay=900, env_them=env)
        giay = round(time.time() - t0, 1)
        with open(os.path.join(LOG_DIR, "g20_gop.txt"), "w", encoding="utf-8") as f:
            f.write(out)
        m = re.search(r"Ran (\d+) tests? in [\d.]+s\s*\n\s*(OK|FAILED[^\n]*)", out)
        print("       LỆNH: VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py")
        print("       sha256 tệp nguồn TRONG CÂY = %s (gốc ghim %s + 2 khối vá)"
              % (_bam(BAN_DO_G20)[:16], BAN_DO_G20_GOC_SHA[:16]))
        print("       mã thoát THẬT = %d · %.1f giây · %s"
              % (rc, giay, (m.group(0).replace("\n", " ") if m else "không thấy dòng tổng kết")))
        if m is None:
            self.fail("không đọc được dòng tổng kết của bàn đo G20:\n%s"
                      % "\n".join(out.splitlines()[-40:]))
        # C1..C5: đọc NGUYÊN VĂN dòng phán quyết của CHÍNH bàn đo — không suy diễn lại.
        # Nhãn in ra của bàn đo là `[G1]` (C1), `[B1]` (C2), `[C2]` (C3), `[C4]`, `[C5]`;
        # `SO_DO_G20[...]["ten_do"]` là KHÓA NỘI BỘ của nó, không phải nhãn in ra.
        MAU = (("C1 cổng cây sạch wave trước", r"\[G1\] cổng cây sạch[^\n]*"),
               ("C2 bàn phím TRONG màn (tầng 3)", r"\[B1\] nhị phân[^\n]*"),
               ("C3 git với môi trường NGUYÊN BẢN", r"\[C2\] GIT_CONFIG[^\n]*"),
               ("C4 route truy_van + migration v9", r"\[C4\][^\n]*"),
               ("C5 có bộ G19-tổng-hợp chạy được", r"\[C5\][^\n]*"))
        for ten, mau in MAU:
            mm = re.search(mau, out)
            print("       %-34s %s" % (ten, mm.group(0).strip() if mm else "KHÔNG THẤY DÒNG ĐO"))
        # VÀ mỗi cổng còn được ĐO ĐỘC LẬP ở đây, không chỉ đọc lời bàn đo kia:
        ma_git, _ = chay(["git", "rev-parse", "HEAD"])          # môi trường NGUYÊN BẢN
        print("       ĐO ĐỘC LẬP C3: `git rev-parse HEAD` môi trường NGUYÊN BẢN → mã thoát %d "
              "(nền=%d, đóng=%d)" % (ma_git, SO_DO_G20["C3 git với môi trường NGUYÊN BẢN"]["nen"],
                                     SO_DO_G20["C3 git với môi trường NGUYÊN BẢN"]["dong"]))
        self.__class__._kq = {"chay_duoc": True, "rc": rc, "out": out}
        # ĐỐI CHỨNG DƯƠNG của nhóm này: C2 phải ĐO ĐƯỢC (bảy ca tầng 3 chạy thật).
        co_c2 = "tang3-ban-phim" in out or "tầng 3" in out
        print("       đối chứng dương: bàn đo có chạm tầng 3 (C2) = %s" % co_c2)
        self.assertTrue(co_c2, "bàn đo G20 chết toàn bộ — C1 đỏ không phân biệt được với "
                               "'bàn đo không chạy'")
        # VÀ tệp nguồn KHÔNG được đổi bởi chính lượt đo này (không ai chép/xoá nó nữa).
        ok2, ghi_chu2 = nguon_da_va(BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA)
        print("       sau lượt đo, tệp nguồn vẫn là 'gốc + 2 khối vá' = %s" % ok2)
        self.assertTrue(ok2, "lượt đo đã ĐỔI tệp nguồn: %s" % ghi_chu2)
        _dc_duong("g20-c1-cay-sach")


class E_CaySach(unittest.TestCase):
    """ĐIỂM 2 Supervisor giao — cổng `cây sạch` phải đo CẢ BA bản sao, và phải phân loại được
    ĐỎ-THẬT ≠ PHÉP-ĐO-CHẾT."""

    # Ba cổng "cây sạch" của wave TRƯỚC còn sống trên cây này. Bản sao thứ TƯ (dormant) nằm ở
    # `thu_qa_g19.py` — xem `test_e2`.
    CONG = (
        ("g17", [PY, "app/thu/thu_qa_g17.py", "A_Nen.test_a1_cay_sach_va_head"]),
        ("g18", [PY, "app/thu/thu_qa_g18.py", "A_Nen.test_a1_cay_sach_theo_pham_vi_wave"]),
        ("g20_baomat", [PY, "app/thu/thu_g20_baomat.py",
                        "A_Nen.test_a1_cay_sach_theo_pham_vi_wave"]),
    )

    def test_e1_ba_cong_cay_sach_chay_that(self):
        """Chạy CẢ BA cổng trong TIẾN TRÌNH CON, và phân loại từng cổng.

        BA CỔNG NÀY SO CÂY VỚI `HEAD`, nên chúng CHỈ đo được khi `HEAD` = nền. Chạy chúng trên
        một cây có `HEAD` cũ hơn sẽ ra ĐỎ vì delta hai commit — ĐỎ GIẢ của môi trường, và lượt
        `qa_g22_lan1_nhiem.log` đã đo đúng cái ĐỎ GIẢ đó (13 đường). Bộ kiểm vì thế TỪ CHỐI phán
        quyết ở đây khi `HEAD` không phải nền, và NÓI RA — chứ không bỏ qua im lặng.
        """
        if head_hien_tai() != NEN_SHA:
            self.skipTest("MÔI TRƯỜNG ĐO KHÔNG TRÙNG: HEAD=%s ≠ nền=%s. Ba cổng này so cây với "
                          "HEAD nên sẽ ĐỎ GIẢ. Chạy bộ kiểm trong cây có HEAD=nền (xem §3)."
                          % (head_hien_tai()[:12], NEN_SHA[:12]))
        DA_CHAY["cay-sach-3-ban-sao"] = True
        xanh, chi_tiet = 0, []
        for ten, lenh in self.CONG:
            # DÙNG `.format()`, KHÔNG DÙNG `%`: đoạn mã con có chứa `%d`/`%r` của CHÍNH NÓ, và
            # lượt chạy đầu đã nổ `TypeError: not enough arguments for format string` vì hai tầng
            # `%` chồng lên nhau. Một tầng định dạng là đủ.
            rc, out, _ = chay_con(MA_GOI_BO_THU.format(lenh=lenh), giay=600)
            loai = _phan_loai_cong_cay_sach(out, rc)
            if loai == "XANH":
                xanh += 1
            chi_tiet.append((ten, rc, loai))
        print("\n  [E1] ba cổng `cây sạch` của wave TRƯỚC — chạy trong TIẾN TRÌNH CON:")
        for ten, rc, loai in chi_tiet:
            print("       %-12s rc=%-4d → %s" % (ten, rc, loai))
        # TIÊM LỖI (đối chứng dương): đặt một tệp BẨN NGOÀI vùng thử rồi chạy lại cổng.
        tiem = self._tiem_tep_ban()
        print("       TIÊM `%s` → cổng g17 phải ĐỎ: %s" % (tiem["tep"], tiem["ket_qua"]))
        self.assertTrue(tiem["bat_duoc"],
                        "TIÊM LỖI KHÔNG BỊ BẮT: đặt một tệp bẩn ngoài vùng mà cổng vẫn xanh ⇒ "
                        "ba cổng này là cổng MÙ, '3/3 xanh' vô nghĩa")
        DA_TIEM["cay-sach-3-ban-sao"] = True
        _dc_duong("cay-sach-3-ban-sao")
        dat, vi = dat_cong("cay-sach-3-ban-sao", xanh)
        print("       phân quyết: %s (%d/%d)" % (phan_quyet("cay-sach-3-ban-sao", xanh),
                                                 xanh, len(self.CONG)))
        self.assertTrue(dat, "CỔNG `cay-sach-3-ban-sao` ĐỎ: %s" % vi)

    def _tiem_tep_ban(self):
        """TIÊM: một tệp NGOÀI vùng thử ⇒ cổng `cây sạch` phải bắt được."""
        p = os.path.join(GOC_CAY, "admin", "__tiem_g22.js")
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write("// tiêm lỗi của AG-01 G22 — sẽ bị xoá ngay\n")
            rc, out, _ = chay_con(
                MA_GOI_BO_THU.format(
                    lenh=[PY, "app/thu/thu_qa_g17.py", "A_Nen.test_a1_cay_sach_va_head"]),
                giay=600)
            return {"tep": "__tiem_g22.js", "rc": rc,
                    "ket_qua": "ĐỎ (rc=%d)" % rc if rc != 0 else "VẪN XANH (rc=0)",
                    "bat_duoc": rc != 0}
        finally:
            if os.path.exists(p):
                os.remove(p)

    def test_e2_ban_sao_thu_tu_dormant_nam_o_dau(self):
        """Bản sao thứ TƯ của cùng khoản nợ — ĐO ĐƯỢC nó nằm đâu và nó có chạy không.

        `thu_qa_g19.py` tự BỎ QUA khi `HEAD != 6e61fc1`; nó chỉ chạy khi ai đó truyền
        `VIP_G19_HEAD`. Nên nó KHÔNG vào được phép đếm "3 bản sao đang sống" — và đó là một
        khoảng trống phạm vi phải NÓI RA, không phải bỏ qua.
        """
        f = os.path.join(GOC_THU, "thu_qa_g19.py")
        self.assertTrue(os.path.exists(f), "thiếu `thu_qa_g19.py`")
        with open(f, encoding="utf-8") as fh:
            nguon = fh.read()
        co_bang = "CONG_CAY_SACH_WAVE_TRUOC" in nguon
        co_mien_tru = "TEP_CUA_AG01_G19" in nguon
        rc, out = chay([PY, "app/thu/thu_qa_g19.py"], giay=900)
        m = re.search(r"Ran (\d+) tests?", out)
        sk = re.search(r"skipped=(\d+)", out)
        print("\n  [E2] `thu_qa_g19.py`: có bảng miễn trừ cứng=%s · có danh sách tệp AG-01=%s"
              % (co_bang, co_mien_tru))
        print("       chạy nguyên trạng: rc=%d · Ran %s tests · skipped=%s"
              % (rc, m.group(1) if m else "?", sk.group(1) if sk else "?"))
        print("       ⇒ bản sao thứ TƯ là DORMANT: nó tự bỏ qua trên cây đã gộp, nên phép đếm "
              "`3 bản sao` chỉ đếm được ba bản ĐANG SỐNG.")
        self.assertEqual(rc, 0, "`thu_qa_g19.py` hỏng khi chạy nguyên trạng: %s" % out[-400:])
        self.assertTrue(co_bang, "bảng miễn trừ đã đổi tên ⇒ ca này không còn đo đúng thứ nó nói")


# Đoạn mã chạy MỘT bộ thử trong TIẾN TRÌNH CON và in PID của chính nó — PID ấy là BẰNG CHỨNG
# tiến trình con thật, không phải một lời khai. Một tầng định dạng duy nhất (`.format`).
MA_GOI_BO_THU = ("import subprocess,sys,os\n"
                 "p=subprocess.run({lenh!r},capture_output=True,text=True)\n"
                 "print(p.stdout);print(p.stderr)\n"
                 "print('__PID_CON__='+str(os.getpid()))\n"
                 "sys.exit(p.returncode)\n")


def _phan_loai_cong_cay_sach(out, rc):
    """`XANH` | `DO_THAT` | `PHEP_DO_CHET`.

    Phân biệt này là bắt buộc: `L-G20-C` (lượt G21 của tôi) đo được rằng một cổng ĐỎ vì TÊN CA
    SAI (`AttributeError`) trông y hệt một cổng ĐỎ vì CÂY BẨN, nếu chỉ nhìn mã thoát.
    """
    if rc == 0:
        return "XANH"
    if "AttributeError" in out or "has no attribute" in out or "ModuleNotFoundError" in out:
        return "PHEP_DO_CHET"
    if re.search(r"^\s*Ran 0 tests", out, re.M):
        return "PHEP_DO_CHET"
    return "DO_THAT"


class F_DongHo(unittest.TestCase):
    """ĐIỂM 3 Supervisor giao — ca E3 phụ thuộc ĐỒNG HỒ. Đo bằng ĐỒNG HỒ ĐÓNG BĂNG, có ĐỐI
    CHỨNG ĐƯỜNG; KHÔNG che bằng retry."""

    def test_f1_do_that_bang_dong_ho_dong_bang(self):
        DA_CHAY["e3-ba-luot-cung-giay"] = True
        that = do_e3(GOC_APP)
        if that.get("so_ban_cat_rollback") is None:
            self.fail("KHÔNG ĐO ĐƯỢC E3 (rc=%s): %s" % (that.get("rc"), that.get("loi")))
        print("\n  [F1] đồng hồ ĐÓNG BĂNG tại %s — ba lượt `khoi_phuc()` CHẮC CHẮN cùng một giây"
              % that.get("luc_dong_bang"))
        print("       ĐỐI CHỨNG DƯƠNG trong cùng tiến trình: `sao_luu()` (ĐÃ VÁ) → %s tệp khác "
              "nhau" % that["so_sao_luu_khac_nhau"])
        print("       PHÉP ĐO: `khoi_phuc()` (CHƯA VÁ) → %s bản cất rollback: %s"
              % (that["so_ban_cat_rollback"], that["ten_ban_cat"]))
        self.assertGreaterEqual(
            that["so_sao_luu_khac_nhau"], 2,
            "đồng hồ đóng băng KHÔNG có hiệu lực HOẶC phép đếm mù: `sao_luu()` đã được vá mà chỉ "
            "ra %s tệp ⇒ mọi kết luận dưới đây vô nghĩa" % that["so_sao_luu_khac_nhau"])
        _dc_duong("e3-ba-luot-cung-giay")
        do_duoc = that["so_ban_cat_rollback"]
        dat, vi = dat_cong("e3-ba-luot-cung-giay", do_duoc)
        print("       phân quyết: %s" % phan_quyet("e3-ba-luot-cung-giay", do_duoc))
        self.assertTrue(dat, "CỔNG `e3-ba-luot-cung-giay` ĐỎ: %s" % vi)

    def test_f2_doi_chung_duong_ban_da_va(self):
        """ĐỐI CHỨNG ĐƯỜNG: CÙNG kịch bản, CÙNG đồng hồ đóng băng, nhưng `khoi_phuc()` ĐÃ VÁ.

        Không có vế này thì "1 bản cất" không phân biệt được với "bộ đo hỏng".
        """
        app_va = _app_tam("da-va", va_khoi_phuc=True)
        try:
            kq = do_e3(app_va)
        finally:
            shutil.rmtree(app_va, ignore_errors=True)
        if kq.get("so_ban_cat_rollback") is None:
            self.fail("KHÔNG ĐO ĐƯỢC bản đã vá (rc=%s): %s" % (kq.get("rc"), kq.get("loi")))
        print("\n  [F2] ĐỐI CHỨNG ĐƯỜNG — cùng đồng hồ đóng băng, `khoi_phuc()` ĐÃ VÁ:")
        print("       sao_luu() → %s tệp khác nhau · khoi_phuc() → %s bản cất"
              % (kq["so_sao_luu_khac_nhau"], kq["so_ban_cat_rollback"]))
        self.assertGreaterEqual(
            kq["so_ban_cat_rollback"], 3,
            "bản ĐÃ VÁ vẫn chỉ để lại %s bản cất ⇒ phép đo của tôi KHÔNG phân biệt được bản vá "
            "với bản chưa vá, nên `F1` không chứng minh được gì" % kq["so_ban_cat_rollback"])
        DA_TIEM["e3-ba-luot-cung-giay"] = True
        _dc_duong("e3-ba-luot-cung-giay")
        print("       ⇒ phép đo PHÂN BIỆT ĐƯỢC: chưa vá → 1 · đã vá → %s"
              % kq["so_ban_cat_rollback"])

    def test_f3_vi_sao_phai_dong_bang_dong_ho(self):
        """Vì sao không được chấp nhận một lượt chạy "may mắn": ĐO ĐƯỢC rằng `khoi_phuc()` đặt
        tên theo GIÂY, nên ba lượt rơi vào hai giây khác nhau sẽ ra ≥2 tệp DÙ LỖI CÒN NGUYÊN."""
        mg = os.path.join(GOC_APP, "migrate.py")
        with open(mg, encoding="utf-8") as f:
            nguon = f.read()
        m = re.search(r'"hub-truoc-rollback-"\s*\+\s*datetime\.now\(\)\.strftime\("([^"]+)"\)',
                      nguon)
        self.assertIsNotNone(m, "không còn tìm thấy cách đặt tên bản cất của `khoi_phuc()`")
        khuon = m.group(1)
        co_hau_so = "_n" in nguon.split("def khoi_phuc", 1)[1].split("def ", 1)[0]
        print("\n  [F3] khuôn tên bản cất của `khoi_phuc()`: `%s` (độ phân giải: GIÂY)" % khuon)
        print("       có vòng thêm hậu số chống đè: %s" % co_hau_so)
        print("       ⇒ ba lượt rơi vào HAI giây khác nhau cho ≥2 tệp mà KHÔNG cần sửa gì ⇒ lượt "
              "chạy 'may mắn' là một cái XANH GIẢ. Vì thế `F1` ĐÓNG BĂNG đồng hồ.")
        self.assertIn("%Y%m%d-%H%M%S", khuon,
                      "khuôn tên đã đổi độ phân giải ⇒ ca `F1`/`F2` phải được thiết kế lại")


class G_NG2103(unittest.TestCase):
    """ĐIỂM 4 Supervisor giao — `thu_g20_dahang.py::CaGanChat::test_c2a` có còn GHIM hành vi RÒ."""

    CA = ("app/thu/thu_g20_dahang.py",
          "CaGanChat.test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia")

    def test_g1_ca_thu_con_ghim_ro(self):
        DA_CHAY["ng21-03-ca-ghim-ro"] = True
        with open(os.path.join(GOC_CAY, self.CA[0]), encoding="utf-8") as f:
            nguon = f.read()
        con_khang_dinh = 'self.assertTrue(ket_qua["gia_ngan"]' in nguon
        rc, out = chay([PY, self.CA[0], self.CA[1]], giay=300)
        print("\n  [G1] LỆNH: python3 %s %s" % self.CA)
        print("       mã thoát THẬT = %d · %s" % (rc, out.strip().splitlines()[-1] if out.strip() else ""))
        print("       còn khẳng định `assertTrue(ket_qua[\"gia_ngan\"])` (tức CÒN GHIM RÒ): %s"
              % con_khang_dinh)
        gia_tri = 1 if (rc == 0 and con_khang_dinh) else 0
        # ĐỐI CHỨNG DƯƠNG BẮT BUỘC: một bộ đo ĐỘC LẬP phải THẤY được sự rò mà ca kia đang ghim.
        rc2, out2 = chay([PY, "app/thu/thu_qa_g21.py", "G5_CredentialNgan"], giay=900)
        m = re.search(r"tổ hợp RÒ=(\d+)/(\d+)", out2)
        so_ro = int(m.group(1)) if m else None
        print("       ĐỐI CHỨNG DƯƠNG (bộ đo ĐỘC LẬP `thu_qa_g21.py::G5_CredentialNgan`): "
              "rc=%d · tổ hợp RÒ=%s" % (rc2, ("%s/%s" % (m.group(1), m.group(2))) if m else "?"))
        self.assertIsNotNone(
            so_ro, "bộ đo độc lập không cho ra số ⇒ 'ca xanh' không phân biệt được với 'hết rò':\n%s"
                   % "\n".join(out2.splitlines()[-25:]))
        self.assertGreater(
            so_ro, 0, "bộ đo độc lập báo 0 tổ hợp rò ⇒ nó mù, và kết luận 'ca còn ghim rò' vô nghĩa")
        _dc_duong("ng21-03-ca-ghim-ro")
        DA_TIEM["ng21-03-ca-ghim-ro"] = True
        dat, vi = dat_cong("ng21-03-ca-ghim-ro", gia_tri)
        print("       phân quyết: %s" % phan_quyet("ng21-03-ca-ghim-ro", gia_tri))
        self.assertTrue(dat, "CỔNG `ng21-03-ca-ghim-ro` ĐỎ: %s" % vi)


class H_C4(unittest.TestCase):
    """C4 (`route truy_van` cho migration v9) — **CHƯA CÓ CHỦ SỞ HỮU** (AG-00 xác nhận, ghi vào
    backlog G22-G25). Ca này KHÔNG nhận là đã đóng; nó đo và ghi thẳng."""

    def test_h1_c4_do_hay_da_dong(self):
        """Cặp giá trị của C4 = (schema v9 ĐẠT?, có tệp SẢN XUẤT import `truy_van`?).

        Vùng thử/tài liệu áp ĐÚNG luật của `thu_g21_chotcay`: một thư mục tên `docs` hoặc bắt
        đầu bằng `thu`. Không có luật đó thì chính bộ kiểm này bị tính là "tệp sản xuất".
        """
        MA = (
            "import ast, os, sys\n"
            "sys.path.insert(0, 'app')\n"
            "import csdl\n"
            "def trong_vung(p):\n"
            "    phan = p.replace(os.sep, '/').split('/')\n"
            "    return any(d == 'docs' or d.startswith('thu') for d in phan[:-1])\n"
            "n, ds = 0, []\n"
            "for g, dirs, fs in os.walk('.'):\n"
            "    dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', '__pycache__')]\n"
            "    for f in fs:\n"
            "        if not f.endswith('.py'): continue\n"
            "        p = os.path.join(g, f)\n"
            "        if trong_vung(p) or p.endswith('app/truy_van.py'): continue\n"
            "        try: cay = ast.parse(open(p, encoding='utf-8').read())\n"
            "        except Exception: continue\n"
            "        for nut in ast.walk(cay):\n"
            "            if isinstance(nut, ast.Import) and any(a.name == 'truy_van' for a in nut.names):\n"
            "                n += 1; ds.append(p)\n"
            "            if isinstance(nut, ast.ImportFrom) and nut.module == 'truy_van':\n"
            "                n += 1; ds.append(p)\n"
            "print('SCHEMA', csdl.PHIEN_BAN_SCHEMA)\n"
            "print('SO_TEP_SAN_XUAT_IMPORT', n)\n"
            "print('DS', ds)\n")
        rc, out = chay([PY, "-c", MA], giay=300)
        self.assertEqual(rc, 0, "không đo được C4 (rc=%d): %s" % (rc, out[-400:]))
        schema = int(re.search(r"SCHEMA (\d+)", out).group(1))
        so_import = int(re.search(r"SO_TEP_SAN_XUAT_IMPORT (\d+)", out).group(1))
        schema_ok = (schema == 9)
        route_ok = (so_import > 0)
        cap = (schema_ok, route_ok)
        print("\n  [H1] C4 — `PHIEN_BAN_SCHEMA`=%d (đòi 9) · tệp SẢN XUẤT import `truy_van`: %d"
              % (schema, so_import))
        print("       cặp đo được = %r · nền=%r · đóng=%r"
              % (cap, SO_DO_G20["C4 route truy_van + migration v9"]["nen"],
                 SO_DO_G20["C4 route truy_van + migration v9"]["dong"]))
        print("       CHỦ SỞ HỮU: **KHÔNG AI** — AG-00 đã ghi thẳng vào backlog G22-G25 (điểm C4 "
              "trong đề bài). Bộ kiểm này **KHÔNG** nhận C4 là đã đóng.")
        self.assertEqual(cap, (True, False),
                         "C4 đã ĐỔI trạng thái so với nền — phải cập nhật tài liệu và nói rõ ai "
                         "sở hữu; đo được %r" % (cap,))


class Z_ChotChan(unittest.TestCase):
    """HAI CHỐT CHẶN BẮT BUỘC — chạy THẬT, không phải khai."""

    def test_z2_tu_kiem_chay_trong_tien_trinh_con(self):
        """CHỐT CHẶN (1): ca TỰ KIỂM BỘ ĐO phải chạy trong TIẾN TRÌNH CON.

        BỐN vế, cả bốn ĐO ĐƯỢC, và vế thứ hai có ĐỐI CHỨNG DƯƠNG hai chiều — vì một phép đo chỉ
        một chiều ("con đặt thì cha không thấy") vẫn xanh được với một tiến trình con KHÔNG hề
        chạy:

          (i)   PID của tiến trình chạy ca KHÁC PID của bộ kiểm;
          (ii)  CHIỀU XUỐNG: biến môi trường CHA đặt TRƯỚC khi gọi thì con PHẢI thấy;
          (iii) CHIỀU LÊN: biến môi trường CON đặt thì CHA **KHÔNG** được thấy;
          (iv)  mã thoát của con (3) phải được cha ĐỌC RA nguyên vẹn.

        Vế (ii) là đối chứng dương của (iii): nó chứng minh kênh môi trường CÓ chạy thật, nên
        "cha không thấy" ở (iii) không phải vì kênh không hoạt động.
        """
        ten_cha = "VIP_G22_CHOT_CHAN_CHA"
        ten_con = "VIP_G22_CHOT_CHAN_CON"
        os.environ[ten_cha] = "cha-dat-truoc"
        os.environ.pop(ten_con, None)
        goc_con = os.environ.get(ten_con)
        ma = ("import os, sys\n"
              "print('THAY_CUA_CHA=%%s' %% os.environ.get(%r, 'KHONG-THAY'))\n"
              "os.environ[%r] = 'con-dat'\n"
              "print('__PID_CON__=%%d' %% os.getpid())\n"
              "sys.exit(3)\n" % (ten_cha, ten_con))
        rc, out, pid_con = chay_con(ma, giay=60)
        sau_con = os.environ.get(ten_con)
        os.environ.pop(ten_cha, None)
        # ĐỐI CHỨNG ÂM của (iii): CÙNG phép đọc, nhưng chạy Ở CHA thì biến PHẢI thấy được.
        os.environ[ten_con] = "cha-tu-dat"
        thay_o_cha = os.environ.get(ten_con) == "cha-tu-dat"
        os.environ.pop(ten_con, None)
        con_thay_cha = ("THAY_CUA_CHA=cha-dat-truoc" in out)
        print("\n  [Z2] CHỐT CHẶN (1) — TỰ KIỂM BỘ ĐO CHẠY TRONG TIẾN TRÌNH CON")
        print("       (i)   PID bộ kiểm=%d · PID con=%s · KHÁC NHAU=%s"
              % (os.getpid(), pid_con, pid_con != os.getpid()))
        print("       (ii)  chiều XUỐNG — con thấy biến của cha: %s (%r)"
              % (con_thay_cha, "THAY_CUA_CHA=cha-dat-truoc"))
        print("       (iii) chiều LÊN — cha thấy biến của con: %s (trước khi gọi=%r, sau khi "
              "gọi=%r)" % (sau_con is not None, goc_con, sau_con))
        print("             đối chứng âm của (iii): cùng phép đọc, chạy Ở CHA → thấy=%s"
              % thay_o_cha)
        print("       (iv)  mã thoát của con đọc RA được: %d (đòi 3)" % rc)
        self.assertIsNotNone(pid_con, "không đọc được PID của tiến trình con")
        self.assertNotEqual(pid_con, os.getpid(),
                            "ca tự kiểm chạy CÙNG PID với bộ kiểm ⇒ nó KHÔNG ở tiến trình con")
        self.assertTrue(con_thay_cha,
                        "tiến trình con KHÔNG thấy biến của cha ⇒ tiến trình con không hề chạy, "
                        "và vế (iii) sẽ xanh một cách rỗng tuếch")
        self.assertIsNone(sau_con, "biến môi trường con đặt LỌT RA ĐƯỢC cha ⇒ không phải tiến "
                                   "trình riêng")
        self.assertTrue(thay_o_cha, "đối chứng âm hỏng: cùng phép đọc ở CHA phải thấy được")
        self.assertEqual(rc, 3, "mã thoát của tiến trình con không được truyền nguyên vẹn")
        DA_CHAY["tien-trinh-con"] = True
        _dc_duong("tien-trinh-con")

    def test_z6_moi_ca_phu_dinh_deu_co_doi_chung_duong(self):
        """CHỐT CHẶN (2): mọi nhóm ca PHỦ ĐỊNH phải có ĐỐI CHỨNG DƯƠNG **đã chạy thật**.

        TÊN `z6` chứ không phải `z1` là CỐ Ý: `unittest` chạy các ca trong một lớp theo THỨ TỰ
        CHỮ CÁI, nên `z1` chạy TRƯỚC `z2`..`z5` và tự phán hỏng vì các cờ đối chứng chưa được bật
        — đo được ở lượt chạy thứ hai (`AssertionError: ['cay-sach-bo-do', 'nua-voi',
        'tien-trinh-con'] != []`). Chốt chặn phải chạy CUỐI thì nó mới phán được.
        """
        thieu_so = sorted(set(CA_PHU_DINH) - set(DOI_CHUNG))
        thieu_chay = sorted(n for n in CA_PHU_DINH if not DA_CHAY.get(n))
        thieu_tiem = sorted(n for n in CA_PHU_DINH
                            if n in ("cay-sach-3-ban-sao", "e3-ba-luot-cung-giay",
                                     "ng21-03-ca-ghim-ro") and not DA_TIEM.get(n))
        print("\n  [Z1] CHỐT CHẶN (2) — ĐỐI CHỨNG DƯƠNG CHO MỌI CA PHỦ ĐỊNH")
        for n in sorted(CA_PHU_DINH):
            print("       %-22s đã chạy đối chứng=%-5s đã tiêm lỗi=%s"
                  % (n, DA_CHAY.get(n, False), DA_TIEM.get(n, "-")))
        self.assertEqual(thieu_so, [], "THIẾU ĐỐI CHỨNG DƯƠNG cho: %s" % thieu_so)
        self.assertEqual(thieu_chay, [], "ĐỐI CHỨNG DƯƠNG CHƯA CHẠY THẬT cho: %s" % thieu_chay)
        self.assertEqual(thieu_tiem, [], "CHƯA TIÊM LỖI (bộ đo chưa chứng minh nó NHÌN THẤY "
                                         "lỗi) cho: %s" % thieu_tiem)

    def test_z3_bo_do_bat_duoc_khi_bi_tiem(self):
        """Bộ ĐO phải BẮT ĐƯỢC lỗi khi bị tiêm — nếu không, mọi "0 lỗi" là mù."""
        DA_CHAY["cay-sach-bo-do"] = True
        # TIÊM vào chính bộ phân loại: một cổng ĐỎ-THẬT giả.
        gia = {"rc": 1, "out": "FAIL: test_a1_cay_sach_va_head ... AssertionError: cây bẩn"}
        loai_that = _phan_loai_cong_cay_sach(gia["out"], gia["rc"])
        # TIÊM vào bộ đếm Playwright: một lượt "did not run" phải KHÔNG bị gộp vào ĐẠT.
        dem = dem_playwright("3 passed · 1 failed · 3 did not run")
        # TIÊM vào sổ giá trị: một giá trị NỬA VỜI phải là ĐỎ.
        pq = phan_quyet("e3-ba-luot-cung-giay", 2)      # nền=1, đóng=3 ⇒ 2 là NỬA VỜI
        print("\n  [Z3] TIÊM LỖI VÀO CHÍNH BỘ ĐO")
        print("       cổng ĐỎ-THẬT giả  → bộ phân loại gọi: %s (đòi DO_THAT)" % loai_that)
        print("       '3 passed · 1 failed · 3 did not run' → bộ đếm: %s (đòi đạt=3, không_chạy=3)"
              % (dem,))
        print("       giá trị NỬA VỜI 2 (nền=1, đóng=3) → sổ: %s (đòi NUA_VOI)" % pq)
        self.assertEqual(loai_that, "DO_THAT", "bộ phân loại KHÔNG bắt được một cổng ĐỎ-THẬT")
        self.assertEqual(dem[0], 3, "bộ đếm gộp 'did not run' vào ĐẠT")
        self.assertEqual(dem[3], 3, "bộ đếm không đếm được 'did not run'")
        self.assertEqual(pq, "NUA_VOI", "sổ giá trị không bắt được giá trị NỬA VỜI")
        DA_TIEM["cay-sach-bo-do"] = True
        _dc_duong("cay-sach-bo-do")

    def test_z4_gia_tri_nua_voi_luon_la_DO(self):
        """Ô thứ ba của sổ giá trị: giá trị lửng lơ KHÔNG được coi là đạt, ở cả hai chế độ."""
        che_do_cu = globals()["CHE_DO"]
        try:
            for cd in ("nen", "gop"):
                globals()["CHE_DO"] = cd
                dat, vi = dat_cong("e3-ba-luot-cung-giay", 2)
                self.assertFalse(dat, "chế độ %s coi giá trị NỬA VỜI là ĐẠT: %s" % (cd, vi))
                print("\n  [Z4] chế độ %-4s · giá trị 2 (nền=1, đóng=3) → ĐỎ: %s" % (cd, vi))
        finally:
            globals()["CHE_DO"] = che_do_cu
        DA_CHAY["nua-voi"] = True

    def test_z9_ca_CO_Y_HONG_de_tu_kiem(self):
        """CA CỐ Ý HỎNG — chỉ dùng làm MỒI cho `Z5`. KHÔNG chạy trong làn thường.

        Vì sao không để nó chạy thường xuyên: một ca hỏng vĩnh viễn làm MÃ THOÁT của bộ kiểm
        luôn là 1, và như thế mã thoát KHÔNG CÒN là phán quyết nữa — đúng thứ luật bằng chứng
        cấm. Nó chỉ chạy khi `VIP_G22_CHAY_MOI=1`, tức khi `Z5` cố ý gọi nó trong tiến trình con.
        """
        if os.environ.get("VIP_G22_CHAY_MOI") != "1":
            self.skipTest("mồi cho `Z5` — chỉ chạy trong tiến trình con của Z5")
        self.assertEqual(1, 2, "ca cố ý hỏng: dùng để chứng minh bộ chạy CÓ RĂNG")

    def test_z5_bo_chay_co_rang_bang_tien_trinh_con(self):
        """CHỐT CHẶN (1) áp lên CHÍNH bộ chạy: một ca hỏng phải làm tiến trình con THOÁT KHÁC 0.

        Không có ca này thì "0 hỏng" không phân biệt được với "bộ chạy không chạy ca nào" hoặc
        "bộ chạy nuốt mã thoát". Đây là bản chạy THẬT của chính tệp này trong tiến trình con.
        """
        rc, out, pid_con = chay_con(
            "import os,subprocess,sys\n"
            "e=dict(os.environ); e['VIP_G22_CHAY_MOI']='1'\n"
            "p=subprocess.run([%r, %r, 'Z_ChotChan.test_z9_ca_CO_Y_HONG_de_tu_kiem'],"
            "capture_output=True,text=True,env=e)\n"
            "print(p.stdout); print(p.stderr)\n"
            "print('__PID_CON__=%%d' %% os.getpid())\n"
            "sys.exit(p.returncode)\n" % (PY, os.path.abspath(__file__)), giay=600)
        print("\n  [Z5] CHỐT CHẶN (1) — chạy CHÍNH bộ kiểm này trong TIẾN TRÌNH CON (pid=%s), "
              "có mồi hỏng:" % pid_con)
        print("       mã thoát THẬT của tiến trình con = %d (đòi KHÁC 0)" % rc)
        self.assertIsNotNone(pid_con, "không đọc được PID tiến trình con")
        self.assertNotEqual(pid_con, os.getpid(), "bộ chạy con TRÙNG PID với cha")
        self.assertNotEqual(rc, 0, "tiến trình con CHẠY CA HỎNG mà vẫn thoát 0 ⇒ bộ chạy KHÔNG "
                                   "có răng:\n%s" % "\n".join(out.splitlines()[-25:]))
        self.assertRegex(out, r"FAIL|AssertionError", "ca hỏng không hiện ra trong output")
        self.assertRegex(out, r"skipped=0|Ran 1 test", "không thấy dấu vết ca mồi đã CHẠY")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7b. `N-G22-01` — NĂM DỊ DẠNG TIỀM LỖI CỦA BỘ ĐẾM `C5`/`G7`: TRƯỚC **và** SAU KHI VÁ
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# KHÔNG khẳng định suông. Mỗi dị dạng được DỰNG THẬT — một bộ `unittest` thật, chạy thật bằng
# `subprocess`, cho ra output THẬT — rồi CHÍNH cổng `C5` (bàn đo G20) VÀ cổng `G7` (bàn đo G21)
# được chạy trên một CÂY GƯƠNG trong `TMP` có chứa dị dạng đó:
#
#   · cột "TRƯỚC" = tệp nguồn trong cây, HOÀN VÁ hai khối bộ đếm, rồi BĂM — phải ra đúng
#                   `BAN_DO_G20_GOC_SHA`/`BAN_DO_G21_GOC_SHA`;
#   · cột "SAU"   = CHÍNH tệp nguồn trong cây (`app/thu/thu_qa_g20.py`, `app/thu/thu_qa_g21.py`),
#                   chép nguyên byte và KIỂM LẠI sha256 sau khi chép.
#
# Cùng một dị dạng, cùng một lệnh, cùng một cây — chỉ khác hai khối bộ đếm. Nên chênh lệch giữa
# hai cột KHÔNG THỂ là do dị dạng; nó chỉ có thể là do bản vá. VÀ cả hai cột đều là BẢN NGUỒN:
# không còn đường chép tạm nào để một bộ đo xanh nhờ bản tạm trong khi nguồn vẫn lỗ.
#
# Cây gương luôn có HAI bộ `thu_qa_g19*.py` (trừ dị dạng ii, cố ý để RỖNG): bộ TIÊM đang đo và
# một bộ HỎNG CHẮC CHẮN. Mẫu số vì thế là 2, và con số đọc ra so thẳng được với `0/2` · `1/2`
# mà AG-04 đã đo.
# `unittest.main()` ở ĐUÔI là BẮT BUỘC: thiếu nó thì chạy tệp KHÔNG in gì và thoát 0 — một dị
# dạng "im lặng" KHÁC, không phải dị dạng đang muốn đo (đã vấp đúng chỗ này ở lượt chạy đầu).
_DUOI = '\n\nunittest.main(verbosity=2)\n'

_TIEM_HONG = '''\
import unittest


class T(unittest.TestCase):
    def test_hong(self):
        self.assertEqual(1, 2, "ca co y hong")
''' + _DUOI

_TIEM_RONG = '''\
import unittest


class T(unittest.TestCase):
    """KHONG co phuong thuc `test_*` nao => `Ran 0 tests` + `OK` + thoat 0."""
''' + _DUOI

_TIEM_BO_QUA_MODUN = '''\
import unittest


def setUpModule():
    raise unittest.SkipTest("bo qua o muc MO-DUN")


class T(unittest.TestCase):
    def test_a(self):
        self.assertTrue(True)

    def test_b(self):
        self.assertTrue(True)
''' + _DUOI

_TIEM_BO_QUA_PHUONG_THUC = '''\
import unittest


class T(unittest.TestCase):
    @unittest.skip("bo qua o muc PHUONG THUC")
    def test_a(self):
        self.assertTrue(True)

    @unittest.skip("bo qua o muc PHUONG THUC")
    def test_b(self):
        self.assertTrue(True)

    @unittest.skip("bo qua o muc PHUONG THUC")
    def test_c(self):
        self.assertTrue(True)
''' + _DUOI

_TIEM_DAT_THAT = '''\
import unittest


class T(unittest.TestCase):
    def test_a(self):
        self.assertTrue(True)

    def test_b(self):
        self.assertTrue(True)
''' + _DUOI

# (nhãn, mã nguồn bộ TIÊM, mã nguồn bộ THỨ HAI). `None` = KHÔNG đặt tệp đó.
# Dị dạng ii đặt `None` cho CẢ HAI ⇒ cây gương KHÔNG có bộ `thu_qa_g19*.py` nào, đúng nghĩa
# "không còn bộ gốc". Bốn dị dạng còn lại có ĐÚNG HAI bộ ⇒ mẫu số là 2, so thẳng được với `1/2`.
TIEM_LOI = (
    ("i-ma-thoat-khac-0", _TIEM_HONG, _TIEM_HONG),
    ("ii-khong-con-bo-goc", None, None),
    ("iii-suite-rong-0-ca", _TIEM_RONG, _TIEM_HONG),
    ("iv-bo-qua-muc-MO-DUN", _TIEM_BO_QUA_MODUN, _TIEM_HONG),
    ("v-bo-qua-muc-PHUONG-THUC", _TIEM_BO_QUA_PHUONG_THUC, _TIEM_HONG),
)
CA_C5 = "C4_C5_NoKhac.test_c5_co_bo_thu_g19_tong_hop_chay_duoc"
CA_G7 = "G7_BoG19TongHop.test_g7_co_bo_g19_tong_hop_chay_duoc"


def dem_ca_ran(ra):
    """Bản sao ĐỘC LẬP của phép đếm `unittest`: trả `(chạy_thật, bỏ_qua, tổng)`.

    Cố ý viết lại thay vì gọi `thu_qa_g21.dem_ca_chay_that`: nếu hai bên dùng CHUNG một hàm thì
    một lỗi trong hàm đó sẽ không bao giờ lộ ra ở đây.
    """
    m = re.findall(r"Ran (\d+) tests?", ra)
    n = int(m[-1]) if m else 0
    bq = int((re.findall(r"skipped=(\d+)", ra) or ["0"])[-1])
    return max(n - bq, 0), bq, n


def _dung_cay_guong(ten, tep_tiem, cot, tep_hai=_TIEM_HONG):
    """Dựng cây GƯƠNG trong `TMP`. KHÔNG ghi một byte nào vào cây thật. Trả gốc cây.

    `cot="sau"`   = CHÉP NGUYÊN hai TỆP NGUỒN trong cây (`app/thu/thu_qa_g20.py`,
                    `app/thu/thu_qa_g21.py`) rồi KIỂM LẠI sha256 sau khi chép — bản trong cây
                    gương phải byte-đối-byte với tệp nguồn.
    `cot="truoc"` = HOÀN VÁ hai tệp nguồn đó (mới → cũ) rồi BĂM, phải ra đúng sha ghim. "Trước khi
                    vá" vì thế được DỰNG LẠI TỪ CHÍNH TỆP NGUỒN, không cần bản sao nào khác.
    """
    goc = os.path.join(TMP_GOC, "veh_g22_tiem_loi", ten)
    if os.path.isdir(goc):
        shutil.rmtree(goc)
    os.makedirs(os.path.join(goc, "app", "thu"))
    for duong, cap, sha_goc in ((BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA),
                                (BAN_DO_G21, G21_G7_VA, BAN_DO_G21_GOC_SHA)):
        dich = os.path.join(goc, "app", "thu", os.path.basename(duong))
        if cot == "sau":
            shutil.copy2(duong, dich)
            if _bam(dich) != _bam(duong):
                raise AssertionError("cây gương `%s`: bản chép KHÔNG khớp byte với tệp nguồn `%s`"
                                     % (ten, duong))
        else:
            than, ghi_chu = nguon_goc(duong, cap, sha_goc)
            if than is None:
                raise AssertionError("cây gương `%s`: KHÔNG dựng được cột TRƯỚC — %s"
                                     % (ten, ghi_chu))
            with open(dich, "w", encoding="utf-8") as f:
                f.write(than)
            if _bam(dich) != sha_goc:
                raise AssertionError("cây gương `%s`: bản HOÀN VÁ không ra đúng sha ghim %s"
                                     % (ten, sha_goc[:16]))
    for ten_tep, noi_dung in (("thu_qa_g19_tiem.py", tep_tiem), ("thu_qa_g19_nen.py", tep_hai)):
        if noi_dung is not None:
            with open(os.path.join(goc, "app", "thu", ten_tep), "w", encoding="utf-8") as f:
                f.write(noi_dung)
    return goc


def _chay_cong_c5(goc):
    """Chạy CHÍNH cổng `C5` trên cây gương. Trả `(rc, đạt, tổng, phán_quyết, out)`."""
    rc, out = chay([PY, os.path.join("app", "thu", "thu_qa_g20.py"), CA_C5], giay=600,
                   env_them={"VIP_G20_CHE_DO": "gop"}, cwd=goc)
    # Phán quyết có thể CHỨA DẤU CÁCH ("chế độ GỘP: khoản nợ 0 VẪN CÒN NGUYÊN") ⇒ đọc tới cuối
    # dòng, KHÔNG dùng `\S+`.
    m = re.search(r"\[C5\][^\n]*?:\s*(\d+)/(\d+)\s*·\s*phán quyết=([^\n]+)", out)
    if not m:
        return rc, None, None, None, out
    return rc, int(m.group(1)), int(m.group(2)), m.group(3).strip(), out


def _chay_cong_g7(goc):
    """Chạy CHÍNH cổng `G7` của bàn đo G21 trên cây gương. Trả `(rc, đạt, tổng, phán_quyết, out)`.

    Đây là vế thứ HAI của cùng một bản vá: `G7` nằm trong `app/thu/thu_qa_g21.py`, một tệp nguồn
    KHÁC. Đo cả hai trên CÙNG một cây gương là cách chứng minh "hai khối giống hệt" bằng kết quả,
    không bằng lời khai.
    """
    rc, out = chay([PY, os.path.join("app", "thu", "thu_qa_g21.py"), CA_G7], giay=600,
                   env_them={"VIP_G21_CHE_DO": "gop"}, cwd=goc)
    m = re.search(r"\[G7\][^\n]*?:\s*(\d+)/(\d+)\s*·[^\n]*?phán quyết=([^\n]+)", out)
    if not m:
        return rc, None, None, None, out
    return rc, int(m.group(1)), int(m.group(2)), m.group(3).strip(), out


def _mo_ta_c5(r, nhan="C5"):
    rc, dat, tong, pq, _ = r
    if dat is None:
        return "thoát %s · KHÔNG có dòng [%s]" % (rc, nhan)
    return "thoát %s · %d/%d · %s ⇒ %s" % (rc, dat, tong, pq, "XANH" if rc == 0 else "ĐỎ")


class I_TiemLoiC5(unittest.TestCase):
    """`N-G22-01` — NĂM dị dạng tiềm lỗi của bộ đếm `C5`/`G7`, đo TRƯỚC và SAU khi vá."""

    def test_i1_nam_di_dang_tiem_loi(self):
        hang = []
        for ten, tep, tep_hai in TIEM_LOI:
            goc_truoc = _dung_cay_guong(ten + "-truoc", tep, "truoc", tep_hai=tep_hai)
            goc_sau = _dung_cay_guong(ten + "-sau", tep, "sau", tep_hai=tep_hai)
            # Bằng chứng THÔ của chính bộ tiêm: mã thoát + số ca chạy thật / bỏ qua / tổng.
            if tep is not None:
                rc_t, out_t = chay([PY, os.path.join("app", "thu", "thu_qa_g19_tiem.py")],
                                   giay=120, cwd=goc_sau)
                tho = (rc_t,) + dem_ca_ran(out_t)
            else:
                tho = None
            hang.append({"ten": ten, "tho": tho,
                         "c5": (_chay_cong_c5(goc_truoc), _chay_cong_c5(goc_sau)),
                         "g7": (_chay_cong_g7(goc_truoc), _chay_cong_g7(goc_sau))})

        dong = ["cổng | dị dạng | bộ tiêm (thoát/chạy thật/bỏ qua/tổng) | TRƯỚC khi vá | SAU khi vá"]
        print("\n  [I1] `N-G22-01` — NĂM DỊ DẠNG TIỀM LỖI, ĐO TRÊN **HAI TỆP NGUỒN**:")
        print("       `C5` trong `%s` (gốc ghim %s) · `G7` trong `%s` (gốc ghim %s)"
              % (os.path.basename(BAN_DO_G20), BAN_DO_G20_GOC_SHA[:12],
                 os.path.basename(BAN_DO_G21), BAN_DO_G21_GOC_SHA[:12]))
        for nhan_cot, tep_cong in (("C5", "thu_qa_g20.py"), ("G7", "thu_qa_g21.py")):
            print("       ── cổng %s (`app/thu/%s`) ──" % (nhan_cot, tep_cong))
            print("       %-27s %-24s %-32s %s" % ("dị dạng", "bộ TIÊM (thoát/thật/bỏ/tổng)",
                                                   "TRƯỚC khi vá", "SAU khi vá"))
            for h in hang:
                tt = ("%d · %d/%d/%d" % h["tho"]) if h["tho"] else "KHÔNG đặt bộ nào"
                r_t, r_s = h[nhan_cot.lower()]
                print("       %-27s %-24s %-32s %s"
                      % (h["ten"], tt, _mo_ta_c5(r_t, nhan_cot), _mo_ta_c5(r_s, nhan_cot)))
                dong.append("%s | %s | %s | %s | %s"
                            % (nhan_cot, h["ten"], tt, _mo_ta_c5(r_t, nhan_cot),
                               _mo_ta_c5(r_s, nhan_cot)))
        print("       cây gương nằm ở %s (ngoài cây thật)"
              % os.path.join(TMP_GOC, "veh_g22_tiem_loi"))

        # (1) SAU khi vá: CẢ NĂM dị dạng phải ĐỎ — ở CẢ HAI cổng. Đây là điều `N-G22-01` đòi.
        for nhan_cot in ("C5", "G7"):
            for h in hang:
                r_sau = h[nhan_cot.lower()][1]
                with self.subTest(cong=nhan_cot, di_dang=h["ten"], cot="sau"):
                    self.assertNotEqual(r_sau[0], 0,
                                        "SAU khi vá, cổng %s: dị dạng `%s` vẫn ĐẠT (mã thoát 0) ⇒ "
                                        "`N-G22-01` CHƯA đóng" % (nhan_cot, h["ten"]))
                    if r_sau[1] is not None:
                        self.assertEqual(r_sau[1], 0,
                                         "SAU khi vá, cổng %s: `%s` vẫn đếm ra bộ CHẠY THẬT"
                                         % (nhan_cot, h["ten"]))
        # (2) TRƯỚC khi vá: BỐN dị dạng đầu đã ĐỎ — chúng KHÔNG phải lỗ hổng.
        for nhan_cot in ("C5", "G7"):
            for h in hang[:4]:
                r_truoc = h[nhan_cot.lower()][0]
                with self.subTest(cong=nhan_cot, di_dang=h["ten"], cot="truoc"):
                    self.assertNotEqual(r_truoc[0], 0,
                                        "TRƯỚC khi vá, cổng %s: `%s` lẽ ra đã phải ĐỎ"
                                        % (nhan_cot, h["ten"]))
        # (2b) Dị dạng ii phải ĐỎ vì ĐÚNG cái chốt của nó ("không còn bộ gốc"), KHÔNG phải vì
        # một lỗi bất kỳ — và đúng ở CẢ HAI cổng. Không kiểm vế này thì "ĐỎ" có thể là đỏ vì lý do
        # khác.
        for nhan_cot in ("C5", "G7"):
            r_ii = hang[1][nhan_cot.lower()][1]
            self.assertIn("không còn tệp", r_ii[4],
                          "cổng %s: dị dạng ii đỏ nhưng KHÔNG phải vì chốt 'không còn bộ gốc'"
                          % nhan_cot)
            self.assertIsNone(r_ii[1],
                              "cổng %s: cây gương ii vẫn in ra dòng phán quyết ⇒ nó còn bộ để đo, "
                              "không phải 'không còn bộ gốc'" % nhan_cot)
        # (3) TRƯỚC khi vá: dị dạng thứ NĂM LỌT — đây là lỗ hổng, phải TÁI HIỆN được ở CẢ HAI cổng.
        ten_v = hang[4]["ten"]
        self.assertEqual(hang[4]["tho"], (0, 0, 3, 3),
                         "bộ tiêm `%s` phải cho `thoát 0` + `Ran 3 tests` + `skipped=3` + 0 ca "
                         "CHẠY THẬT; đo được `%r` ⇒ dị dạng không đúng như mô tả"
                         % (ten_v, hang[4]["tho"]))
        for nhan_cot in ("C5", "G7"):
            r_truoc_v = hang[4][nhan_cot.lower()][0]
            with self.subTest(cong=nhan_cot, di_dang=ten_v, cot="truoc"):
                self.assertEqual(r_truoc_v[0], 0,
                                 "TRƯỚC khi vá, cổng %s: `%s` lẽ ra phải LỌT (đó chính là lỗ hổng "
                                 "phải tái hiện); đo được: %s"
                                 % (nhan_cot, ten_v, _mo_ta_c5(r_truoc_v, nhan_cot)))
                self.assertEqual((r_truoc_v[1], r_truoc_v[2]), (1, 2),
                                 "TRƯỚC khi vá, cổng %s: `%s` lẽ ra phải đọc ra `1/2`; đo được: %s"
                                 % (nhan_cot, ten_v, _mo_ta_c5(r_truoc_v, nhan_cot)))
        with open(os.path.join(LOG_DIR, "n_g22_01_nam_di_dang.txt"), "w",
                  encoding="utf-8") as f:
            f.write("\n".join(dong) + "\n")
        _dc_duong("c5-tru-bo-qua")

    def test_i2_doi_chung_duong_ban_va_khong_qua_tay(self):
        """ĐỐI CHỨNG DƯƠNG hai vế, ở CẢ HAI cổng: bản ĐÃ VÁ phải còn XANH trước một bộ CHẠY THẬT.

        Vế (a): bộ ĐẠT THẬT + bộ HỎNG ⇒ `1/2 · ĐÓNG`, mã thoát 0. Không có vế này thì bản vá chỉ
        là "luôn luôn đỏ" và không đo được gì.
        Vế (b): bộ ĐẠT THẬT + bộ MỌI CA BỎ QUA ⇒ VẪN `1/2 · ĐÓNG`. Vế này chứng minh bản vá
        KHÔNG quá tay: nó TRỪ ca bỏ qua, chứ không CẤM bỏ qua.
        """
        for nhan, tep_hai in (("(a) bạn-hỏng", _TIEM_HONG),
                              ("(b) bạn-mọi-ca-bỏ-qua", _TIEM_BO_QUA_PHUONG_THUC)):
            goc = _dung_cay_guong("dat-that-" + nhan.split()[0].strip("()"), _TIEM_DAT_THAT,
                                  "sau", tep_hai=tep_hai)
            for nhan_cot, ham in (("C5", _chay_cong_c5), ("G7", _chay_cong_g7)):
                r = ham(goc)
                print("\n  [I2] ĐỐI CHỨNG DƯƠNG %s · cổng %s → %s"
                      % (nhan, nhan_cot, _mo_ta_c5(r, nhan_cot)))
                with self.subTest(ve=nhan, cong=nhan_cot):
                    self.assertEqual(r[0], 0, "cổng %s: bản ĐÃ VÁ đỏ trước một bộ CHẠY THẬT: %s"
                                     % (nhan_cot, _mo_ta_c5(r, nhan_cot)))
                    self.assertEqual((r[1], r[2]), (1, 2),
                                     "cổng %s: phải đọc ra `1/2`: %s"
                                     % (nhan_cot, _mo_ta_c5(r, nhan_cot)))


class Y_Bang(unittest.TestCase):
    """Bảng phán quyết — in ra ở CUỐI, sau khi mọi ca đã chạy."""

    def test_y1_in_bang(self):
        print("\n" + "=" * 92)
        print("  BẢNG PHÁN QUYẾT — chế độ=%s%s" % (CHE_DO,
              "  (ô 'nen' CŨNG ĐỎ: nghiệm thu bản ĐÃ GỘP)" if CHE_DO == "gop" else "  (đo nợ trên nền)"))
        print("  nền: SHA=%s · tree=%s" % (NEN_SHA[:12], TREE_NEN[:12]))
        print("=" * 92)
        for ten in sorted(SO_DO):
            print("  %-30s nền=%-14r đóng=%-14r" % (ten, SO_DO[ten]["nen"], SO_DO[ten]["dong"]))
        print("=" * 92)
        self.assertTrue(True)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. HẠ TẦNG NHỎ + CỔNG CHẶN "BỘ KIỂM TỰ HỎNG"
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _dc_duong(nhom):
    """Bật cờ 'đối chứng dương của nhóm này ĐÃ CHẠY THẬT'."""
    DA_CHAY[nhom] = True


def _khoa_tam():
    """Khóa nhận diện đường tạm, GHÉP TỪ HAI MẢNH.

    Ghép từ hai mảnh là CỐ Ý: nếu viết liền thì chính dòng kiểm tra này chứa khóa đó, và phép
    kiểm tự bắt chính nó — đã đo được ở lượt chạy đầu (`CÒN — VI PHẠM` dù đường tạm đã xoá).
    """
    return "def g20_" + "cop_tam("


def _kiem_tra_pham_vi():
    """Bộ kiểm TỰ KIỂM phạm vi ghi: ngoài hai tệp được phép, cây phải sạch.

    Miễn trừ delta HEAD↔nền dùng CÙNG hàm `delta_head_voi_nen()` như `A2` — một luật, một chỗ.
    """
    rc, ds = trang_thai()
    la = [d for d in ds if d.strip()]
    delta = set(delta_head_voi_nen())
    ngoai = [d for d in la
             if duong_cua_dong_status(d) not in delta
             and not any(duong_cua_dong_status(d).endswith(t) for t in TEP_DUOC_PHEP)]
    return {"rc": rc, "so_duong": len(la), "ngoai": ngoai}


MAIN_DOC = """
  BỘ KIỂM G22 — AG-01 (QA/VERIFIER)

  Nền: %s  (tree %s)
  Cây đang đo: %s
  HEAD hiện tại: %s   %s

  Lệnh:
    python3 app/thu/thu_qa_g22.py                       # làn mặc định
    VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py    # nghiệm thu bản đã gộp
    VIP_G22_DAY_DU=1 python3 app/thu/thu_qa_g22.py      # + chạy lại chay_tat_ca.sh
"""


def main():
    os.makedirs(LOG_DIR, exist_ok=True)

    # ĐO MÔI TRƯỜNG TRƯỚC KHI ĐO SẢN PHẨM. `write-tree` là bất biến NỘI DUNG — nó đúng thì cây
    # đang đo ĐÚNG LÀ cây của nền, dù `HEAD` có nhích được hay không.
    tree = tree_hien_tai()
    head = head_hien_tai()
    dung_cay = (tree == TREE_NEN)
    dung_head = (head == NEN_SHA)
    if dung_head:
        ghi_chu = "= nền ✓"
    else:
        ghi_chu = ("≠ nền ⇒ delta hai commit được miễn trừ ở `A2`; CÁC CỔNG 'CÂY SẠCH' TỪ CHỐI "
                   "PHÁN QUYẾT (xem §3 đầu tệp)")
    print(MAIN_DOC % (NEN_SHA[:12], TREE_NEN[:12], GOC_CAY, head[:12] if head else "KHÔNG ĐỌC ĐƯỢC",
                      ghi_chu))
    if not dung_cay:
        print("  ⚠ CÂY ĐANG ĐO KHÔNG PHẢI CÂY CỦA NỀN: write-tree=%s · nền=%s"
              % (tree[:12], TREE_NEN[:12]))

    import unittest as _u
    # Thứ tự CỐ Ý: `Y_Bang` in sổ trước; `Z_ChotChan` CUỐI, vì `Z1` chỉ phán được sau khi mọi
    # nhóm phủ định đã chạy đối chứng dương.
    mac_dinh = ["Y_Bang", "A_Nen", "C_BanPhim", "D_BanDoG20", "E_CaySach", "F_DongHo",
                "G_NG2103", "H_C4", "I_TiemLoiC5", "Z_ChotChan"]
    danh_sach = sys.argv[1:] or mac_dinh          # cho phép lọc ca (dùng bởi `Z5`)
    # `module=sys.modules['__main__']`, KHÔNG phải `module=None`: `None` làm bộ nạp đi
    # `__import__` từng TÊN LỚP như một mô-đun, và cả chín lớp cùng lỗi `ModuleNotFoundError`
    # — đo được ở lượt chạy đầu (`Ran 9 tests · FAILED (errors=9)`).
    prog = _u.main(module=sys.modules["__main__"], argv=[sys.argv[0]] + danh_sach,
                   verbosity=2, exit=False)
    thanh_cong = bool(prog.result.wasSuccessful())

    vt = van_tay()
    print("\n" + "=" * 92)
    print("  VÂN TAY SAU KHI CHẠY — cây KHÔNG được đổi vì bộ kiểm")
    print("    HEAD=%s · write-tree=%s · %s tệp · băm danh sách=%s"
          % (vt["head"][:12], vt["tree"][:12], vt["so_tep"], vt["bam_danh_sach"][:16]))
    pv = _kiem_tra_pham_vi()
    print("    phạm vi ghi: %d đường trong `status`; ngoài hai tệp được phép: %s"
          % (pv["so_duong"], pv["ngoai"] or "KHÔNG"))
    ok20, gc20 = nguon_da_va(BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA)
    ok21, gc21 = nguon_da_va(BAN_DO_G21, G21_G7_VA, BAN_DO_G21_GOC_SHA)
    print("    TỆP NGUỒN `app/thu/thu_qa_g20.py` (C5): ĐÃ VÁ = %s" % ok20)
    print("    TỆP NGUỒN `app/thu/thu_qa_g21.py` (G7): ĐÃ VÁ = %s" % ok21)
    print("    đường chép tạm `g20_cop_tam()`/`g20_va_c5()`: %s"
          % ("CÒN — VI PHẠM" if (_khoa_tam() in open(__file__, encoding="utf-8").read()
                                 or os.path.exists(os.path.join(GOC_THU, "thu_qa_g20_tam.py")))
             else "KHÔNG còn (đã xoá hẳn)"))
    r = prog.result
    print("    ca: %d · hỏng/loi: %d · bỏ qua: %d · MÃ THOÁT = %d"
          % (r.testsRun, len(r.failures) + len(r.errors), len(r.skipped),
             0 if thanh_cong else 1))
    print("=" * 92)
    # MÃ THOÁT LÀ PHÁN QUYẾT — không phải một dòng chữ trong output.
    sys.exit(0 if thanh_cong else 1)


if __name__ == "__main__":
    main()
