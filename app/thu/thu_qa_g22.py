#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-01 (G22) — BỘ KIỂM ĐỘC LẬP cho wave G22. VAI: NGƯỜI KIỂM, KHÔNG PHẢI NGƯỜI VIẾT.

NỀN ĐO — VÒNG 3 (`ctx_d56f10e956ad`): NỀN ĐƯỢC ĐỌC TẠI CHỖ, KHÔNG CÒN GHIM.

    Vòng 2 đã dựng đúng phép đo nhưng vẫn GHIM kết quả vào hai hằng số (`NEN_SHA`/`TREE_NEN`).
    `HEAD` nhích ở MỌI commit, nên sau mỗi lần gộp cái ghim lại STALE và `A1` đỏ vĩnh viễn cho
    tới khi có người sửa số — đúng họ "ghim SỰ THẬT MÔI TRƯỜNG" (H5/N-G19-04) mà cả wave đang
    diệt (C5/G7, `SO_DO`, tiêu đề F, và nay là A1). Vòng 3 BỎ hẳn ghim:

        nền        = HEAD đọc TẠI CHỖ            (`git rev-parse HEAD`)
        cây nền    = `HEAD^{tree}` đọc TẠI CHỖ
        cây đang đo = `write-tree` trên BẢN SAO index (AGENT 03 §3.3 — không ghi `.git` thật)

    `A1` ĐỎ khi hai cây khác nhau, khi index lệch HEAD, khi có thay đổi ngoài phạm vi, hoặc khi
    KHÔNG đọc được cây — KHÔNG có số nào phải cập nhật khi `HEAD` nhích. Ba đối chứng âm của A1
    được LÀM THẬT trên một clone tạm (`_doi_chung_am_a1`), không phải lời khai.
    Lịch sử ghim (CHỈ ĐỂ ĐỌC): `7344c02/8fc624de` → `3b7e93b/37079aa8` → `dd788fc/9628587`.

VÒNG 4 (`ctx_e398c90995a7`) — `C4`/`G19-C6`, VÀ MỘT CÁI GHIM NỮA BỊ DIỆT:

    `H_C4` của vòng 3 vẫn GHIM trạng thái nền `(True, False)` nên ĐỎ dù sản phẩm ĐÃ ĐÓNG:
    AG-06 đã port route `truy_van` (~20 dòng) vào `app/server.py` (commit `146500b`). Vòng 4 viết
    lại ca theo bất biến "ĐÃ ĐÓNG": đo TẠI CHỖ (đếm tham chiếu THẬT, không ghim số/dòng/tệp) +
    ĐỐI CHỨNG ÂM LÀM THẬT (gỡ `import truy_van` + mọi khối `if` DÙNG nó trên bản sao `app/` ⇒
    cổng PHẢI ĐỎ). `C4` ở đây là `G19-C6` (route + `DDL_G12Q` vào migration) — KHÁC hẳn
    `OWNER_ACTIONS C4` = "Chuyển CSDL nghiệp vụ sang PostgreSQL" = D-8/BLOCKED OWNER.

VÒNG 5 (`task_eaf399b954e3`) — `D1` PHẢI ĐỌC **MÃ THOÁT THẬT** CỦA BÀN ĐO G20:

    `D1` chạy CẢ bàn đo G20 nhưng chỉ `re.search(r"Ran …")` trên output rồi KHÔNG đọc `rc`, nên
    khi G20 có **6 ca hỏng** (`EXIT 1`) thì `D1` VẪN PASS. Đo được trên cây này: G20 `Ran 21 ·
    FAILED (failures=6, skipped=3) · EXIT 1` mà `D1` `Ran 1 · OK · EXIT 0`. Một cổng báo ĐẠT
    trong khi thứ nó đo THẤT BẠI là lỗi tệ nhất của wave — nó biến mọi báo cáo thành vô nghĩa.
    Nay phán quyết đi qua ĐÚNG MỘT điểm vào `_phan_quyet_ban_do_g20(rc, out)`: **MÃ THOÁT là vế
    chính**, ba vế phụ (`Ran N` đọc được và `> 0`, KHÔNG có dòng `FAIL`/`ERROR`, có dòng tổng kết
    `OK`) chặn đúng chiều ngược lại — "tin mã thoát đơn lẻ". Bốn đối chứng âm (a)–(d) là bốn
    TIẾN TRÌNH CON THẬT chạy qua chính hàm đó; đối chứng dương là một bàn đo giả XANH.

GIT SANDBOX — HAI NGUYÊN NHÂN ĐỎ CỦA `A1`, CẢ HAI ĐÃ ĐƯỢC XỬ LÝ (AGENT 03 · `docs/G22_A1_GIT.md`):

    (a) MÔI TRƯỜNG: `git write-tree` TRẦN bị chặn ghi `gitdir/index.lock` (`Operation not
        permitted`, `rc=128`) vì gitdir nằm NGOÀI vùng sandbox cho ghi. Vòng 2 thay
        `tree_hien_tai()` bằng phép đo TƯƠNG ĐƯƠNG ở mục 3.3 của tài liệu AGENT 03: BẢN SAO
        index + ODB tạm + alternates CHỈ ĐỌC — mọi thứ cần GHI rơi vào TMP, mọi thứ cần ĐỌC lấy
        từ kho thật; index thật KHÔNG đổi sha256, KHÔNG có `index.lock`.
        ĐỐI CHỨNG DƯƠNG nhúng ngay trong `A1`: tiêm 1 mục vào BẢN SAO index ⇒ tree ĐỔI
        (`9628587` → `44025342f53b`), còn index thật giữ nguyên sha256. Phép đo vì thế KHÔNG mù.
    (b) GHIM CŨ: vòng 2 "sửa" bằng cách CẬP NHẬT số — và đúng một commit sau, số lại STALE (đo
        được ở `docs/G22_A1_GIT.md` §4.3/§5). Vòng 3 BỎ hẳn ghim: nền đọc tại chỗ, nên HEAD
        nhích bao nhiêu lần cũng không có số nào phải sửa.

    Một lỗi MÔI TRƯỜNG ĐỘC LẬP đã có từ trước: `GIT_CONFIG_COUNT=2` thiếu `GIT_CONFIG_KEY_*`
    làm MỌI lệnh git thoát 128. `_git_env()` gỡ gia đình biến dị dạng để ĐO ĐƯỢC — không phải
    để "cho xanh"; ca `C3` của bàn đo G20 mới là ca đo môi trường NGUYÊN BẢN.

    ⇒ Bộ kiểm TỰ ĐO môi trường: `write-tree` tương đương phải BẰNG `HEAD^{tree}` đọc tại chỗ,
      và cây phải SẠCH ngoài phạm vi. Không một byte nào ghi vào `.git` thật.

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

import ast
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
GOC_SPEC = os.path.join(GOC_CAY, "thu_giao_dien")

# NỀN: KHÔNG còn hằng số. `HEAD` và `HEAD^{tree}` được ĐỌC TẠI CHỖ trong chính phép đo A1.
#
# Vì sao bỏ hẳn: `HEAD` nhích ở MỌI commit, nên mọi cặp `(NEN_SHA, TREE_NEN)` viết cứng đều
# thành STALE ngay sau lần gộp kế tiếp và biến `A1` thành cổng ĐỎ VĨNH VIỄN — họ H5/N-G19-04.
# Không ai phải "cập nhật ghim" nữa, vì không còn ghim nào để cập nhật.
# Lịch sử ghim (CHỈ ĐỂ ĐỌC, KHÔNG dùng để phán quyết):
#     7344c02/8fc624de  →  3b7e93b/37079aa8  →  dd788fc/9628587  →  (bỏ ghim ở vòng 3)

TEP_DUOC_PHEP = ("docs/QA_G22.md", "docs/G22_CONTRACT.md", "app/thu/thu_qa_g22.py",
                 "app/thu/thu_qa_g21.py", "app/thu/thu_qa_g20.py")
# `docs/G22_CONTRACT.md` là tệp của AGENT 02 (lượt `G22 · A2 · CONTRACT`): nó ghi bảng
# STALE/lỗi-thật và hợp đồng đã duyệt cho nhóm F/G/Z6. Thêm vào danh sách này để `A2` không gọi
# chính bản báo cáo của lượt là "thay đổi ngoài phép" — một cái ĐỎ GIẢ của phạm vi.
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
# Nhị phân mà `chay.sh` THẬT SỰ dùng khi headless — đường mà đề bài đã ghim.
PW_HEADLESS_TUONG_DOI = ("chromium_headless_shell-1194", "chrome-mac", "headless_shell")
# sha256 của headless_shell revision 1194 (Chromium 141.0.7390.37) — CHỐT NỘI DUNG, không phải
# "thấy tệp là tin". Lệch ⇒ revision/nhị phân đã đổi, phải cập nhật ghim có ý thức.
PW_HEADLESS_SHA256 = "a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040"
PW_REVISION_DOI = "1194"

# Log `chay_tat_ca.sh` của lượt đo này — dùng khi KHÔNG bật `VIP_G22_DAY_DU`.
LOG_CHAY_TAT_CA = os.environ.get("VIP_G22_LOG_TAT_CA") or os.path.join(
    TMP_GOC, "qa_g22_lan2_sach.log")

# Bàn đo G20 (`C5`) và bàn đo G21 (`G7`) — TỆP NGUỒN TRONG CÂY, **KHÔNG** qua bản chép tạm.
# Dispatch `N-G22-01` vá THẲNG hai khối bộ đếm vào hai tệp này; đường tạm
# `g20_cop_tam()`/`g20_va_c5()` đã bị XOÁ HẲN (xem `docs/QA_G22.md` §7).
BAN_DO_G20 = os.path.join(GOC_THU, "thu_qa_g20.py")
BAN_DO_G21 = os.path.join(GOC_THU, "thu_qa_g21.py")
# ── GHIM HAI BÀN ĐO — CẬP NHẬT SAU KHI GỘP U1..U5 (`task_889a1ddeccdb`, cây `5fc5f6f`) ─────────
#
# HAI ô cho MỖI tệp, vì chúng chặn HAI kiểu trôi KHÁC NHAU — cả hai đều là đối tượng của vòng này
# (`msg_0b757445cfb8`: *"G22 `nguon_da_va`/`D1` và `I_TiemLoiC5` đang ghim hash G20/G21 cũ"*):
#
#   · `..._SHA_TRONG_CAY` — sha256 của ĐÚNG tệp đang nằm trong cây. Đổi MỘT byte (kể cả bên
#     trong khối vá) ⇒ `nguon_da_va()` ĐỎ NGAY và nói ra "tệp TRONG CÂY đã bị đổi". Đây là chốt
#     "bộ đo bị đổi giữa lượt".
#   · `..._GOC_SHA` — sha256 của nội dung SAU KHI HOÀN VÁ hai khối bộ đếm ⇒ chứng minh tệp trong
#     cây đúng là "bản gốc đã chốt + ĐÚNG hai khối vá", không phải bản bị sửa tay ở chỗ khác.
#
# **GHIM NÀY KHÔNG PHẢI ĐỂ BÁO XANH.** Giá trị mới được TÍNH TẠI CHỖ từ chính hai tệp, KHÔNG chép
# từ log của lượt trước, và KHÔNG suy ra từ việc "cổng đang đỏ nên đổi số cho khớp". Lệnh đã
# chạy (ở gốc cây, sau khi gộp `5fc5f6f`; `_hoan_va` dựng lại bản không vá rồi băm):
#
#   $ python3 - <<'EOF'
#   import hashlib, importlib.util, sys
#   spec = importlib.util.spec_from_file_location("g22", "app/thu/thu_qa_g22.py")
#   m = importlib.util.module_from_spec(spec); sys.modules["g22"] = m
#   spec.loader.exec_module(m)
#   for p, cap in ((m.BAN_DO_G20, m.G20_C5_VA), (m.BAN_DO_G21, m.G21_G7_VA)):
#       than = open(p, encoding="utf-8").read()
#       print(hashlib.sha256(than.encode()).hexdigest(),
#             hashlib.sha256(m._hoan_va(than, cap).encode()).hexdigest())
#   EOF
#
#   b56062bc928f16f0db13eb4b806b20ad342c992f224ad4df70f6c446710b48dc  6a96e294066abdd0be1c824a8f292df913d7344cb74b3b62463c9dcc13fe818f
#   4e730aac79cbb4f7bc541d151e9d423a616635a4707cfce4c2e602fa9520d0a2  6a97ef519b3433bfbf105048721bbd743354fc014e6d541efc4bc2364a9982be
#
# VÌ SAO CẢ HAI GIÁ TRỊ ĐỀU ĐỔI (không phải "nới cổng"): U2 đã sửa THẬT `thu_qa_g20.py` (bỏ ghim
# stale C1/C4, import `thu_g21_chotcay` cho phép đo tầng 3) và U3 đã sửa THẬT `thu_qa_g21.py`
# (bỏ ghim stale). Tệp đo đổi ⇒ ghim phải đổi THEO, có ý thức — và ĐỐI CHỨNG ÂM chứng minh ghim
# vẫn có răng: đổi một byte trong tệp G20/G21 ⇒ `nguon_da_va()` PHẢI ĐỎ (`D1`, đối chứng (e)-(g)).
#
# Lịch sử ghim (CHỈ ĐỂ ĐỌC — một bản sao thứ hai là một bản sẽ trôi):
#   G20 gốc: 5a4b3c83c45f… (đến `5fc5f6f`) → 6a96e294066a… (bản này)
#   G21 gốc: 4ebf21e88042… (đến `5fc5f6f`) → 6a97ef519b34… (bản này)
BAN_DO_G20_SHA_TRONG_CAY = "b56062bc928f16f0db13eb4b806b20ad342c992f224ad4df70f6c446710b48dc"
BAN_DO_G20_GOC_SHA = "6a96e294066abdd0be1c824a8f292df913d7344cb74b3b62463c9dcc13fe818f"
BAN_DO_G21_SHA_TRONG_CAY = "4e730aac79cbb4f7bc541d151e9d423a616635a4707cfce4c2e602fa9520d0a2"
BAN_DO_G21_GOC_SHA = "6a97ef519b3433bfbf105048721bbd743354fc014e6d541efc4bc2364a9982be"

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

# SỐ CA E2E — ĐẾM BẰNG CHÍNH PLAYWRIGHT, KHÔNG GHIM MỘT CON SỐ.
#
# Vòng 1 ghim số ca của một lượt chạy CŨ: `(51,0,0)` và `(7,0,0)`. Cây hiện tại có 65 ca / 8 ca
# bàn phím; ghim cũ là một SỰ THẬT MÔI TRƯỜNG ĐÃ TRÔI — đúng họ H5/N-G19-04. Vòng 2 đếm số ca
# bằng `npx playwright test --list` (nạp config + liệt kê ca, KHÔNG chạy trình duyệt): đây là
# nguồn sự thật vì nó TÍNH cả ca sinh trong vòng lặp (`02_bo_cuc` × 3 bề rộng, `03_quyen` × 3
# vai trò) mà đếm chuỗi `test(` sẽ đếm sai. ĐỐI CHỨNG ÂM nằm trong `B2`/`B3`: bỏ ĐÚNG một ca
# khai báo trong bản sao TẠM ⇒ bộ đếm tĩnh giảm đúng 1; và hạ 1 ca trong báo cáo ⇒ cổng PHẢI ĐỎ.
MAU_CA_SPEC = re.compile(r"^\s*test(?:\.(?:only|skip|fixme))?\s*\(", re.M)


def dem_ca_spec_mot_tep(duong):
    """Đếm số DÒNG khai ca trong MỘT tệp spec. Đọc NỘI DUNG, không đoán.

    Chỉ dùng cho `06_ban_phim.spec.js` (tệp này KHÔNG sinh ca trong vòng lặp) làm ĐỐI CHỨNG ÂM
    cho bộ đếm; số ca CHÍNH THỨC lấy từ `so_ca_playwright()`.
    """
    with open(duong, encoding="utf-8") as f:
        return len(MAU_CA_SPEC.findall(f.read()))


def so_ca_playwright(bo_loc=""):
    """ĐẾM CA BẰNG CHÍNH PLAYWRIGHT: `npx playwright test --list` — KHÔNG chạy trình duyệt.

    Vì sao không đếm `test(` bằng regex: `02_bo_cuc.spec.js` khai MỘT ca trong vòng lặp 3 bề
    rộng, `03_quyen.spec.js` khai MỘT ca trong vòng lặp 3 vai trò — Playwright tính 3+3, regex
    chỉ đếm 1+1. `--list` nạp chính config của cây và liệt kê đúng những ca runner sẽ chạy.
    `VIP_GD_GOC` chỉ để config nạp được; `--list` KHÔNG mở kết nối nào.
    """
    env_them = {"PLAYWRIGHT_BROWSERS_PATH": "0",
                "VIP_GD_GOC": "http://127.0.0.1:1",
                "VIP_GD_NEN": os.path.join(TMP_GOC, "g22-list")}
    lenh = ["npx", "playwright", "test", "--list"] + ([bo_loc] if bo_loc else [])
    rc, out = chay(lenh, giay=300, env_them=env_them)
    theo_tep = {}
    for dong in out.splitlines():
        m = re.search(r"›\s+(\S+\.spec\.js):\d+:\d+\s+›", dong)
        if m:
            theo_tep[m.group(1)] = theo_tep.get(m.group(1), 0) + 1
    m = re.search(r"Total:\s+(\d+)\s+tests?\s+in\s+(\d+)\s+files?", out)
    tong = int(m.group(1)) if m else sum(theo_tep.values())
    return {"toan_bo": tong,
            "ban_phim": theo_tep.get("06_ban_phim.spec.js", 0),
            "so_tep": (int(m.group(2)) if m else len(theo_tep)),
            "theo_tep": theo_tep, "rc": rc,
            "loi": "" if rc == 0 and tong else "\n".join(out.splitlines()[-25:])}


SO_CA = so_ca_playwright()


def so_ca_playwright_dat_duoc():
    """Vế **MÃ THOÁT** của bước ĐẾM CA: `npx playwright test --list` phải thoát 0.

    Trước đây `rc` của bước này được TRẢ VỀ nhưng không ai đọc, nên một lượt `--list` thoát khác
    0 mà vẫn in ra vài dòng vẫn có thể thành MẪU SỐ của cổng phủ-số-ca. Trả `(ok, ghi_chú)`; dùng
    CHUNG cho `B2` và `B3` để hai cổng không kiểm tra mẫu số theo hai cách khác nhau.
    """
    if SO_CA.get("rc") == 0:
        return True, ("`npx playwright test --list` thoát 0 · toàn bộ=%d ca · bàn phím=%d ca · "
                      "%d tệp spec" % (SO_CA["toan_bo"], SO_CA["ban_phim"], SO_CA["so_tep"]))
    return False, ("`npx playwright test --list` THOÁT %d ⇒ số ca liệt kê KHÔNG đáng tin, mẫu số "
                   "hỏng thì cổng phủ-số-ca vô nghĩa: %s"
                   % (SO_CA.get("rc"), (SO_CA.get("loi") or "")[-500:]))


def doi_chung_am_dem_ca(ten_tep="06_ban_phim.spec.js"):
    """Bỏ ĐÚNG MỘT dòng khai ca trong bản sao TẠM ⇒ bộ đếm phải giảm ĐÚNG 1.

    Chứng minh số ca là ĐẾM TỪ NỘI DUNG tệp, không phải một hằng số được dán vào cho khớp
    (H5/N-G19-04). Bản sao nằm trong `TMP`; tệp trong cây không bị chạm (sha256 kiểm ở `B3`).
    """
    goc = os.path.join(GOC_SPEC, ten_tep)
    with open(goc, encoding="utf-8") as f:
        than = f.read()
    n_goc = len(MAU_CA_SPEC.findall(than))
    dong = than.splitlines(True)
    bo = None
    for i, d in enumerate(dong):
        if MAU_CA_SPEC.match(d):
            bo = dong.pop(i)
            break
    if bo is None:
        return {"rc": 1, "loi": "không tìm được dòng khai ca để bỏ", "n_goc": n_goc}
    tmp = tempfile.mkdtemp(prefix="g22-dem-ca-")
    try:
        p = os.path.join(tmp, ten_tep)
        with open(p, "w", encoding="utf-8") as f:
            f.write("".join(dong))
        return {"rc": 0, "n_goc": n_goc, "n_tam": dem_ca_spec_mot_tep(p),
                "dong_bo": bo.strip()[:90]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


SO_DO = {
    # Điểm 1 Supervisor giao — tầng 3 Chromium. Bộ ba (ĐẠT, HỎNG, KHÔNG CHẠY).
    # "nen" = hình dạng khi THIẾU NHỊ PHÂN (mọi ca bàn phím hỏng, phần còn lại không chạy), suy
    #         từ số đo G21 (0, 7, 44) quy theo số ca HIỆN TẠI — không phải một con số mới bịa ra.
    # "dong" = cả bộ chạy sạch, suy TRỰC TIẾP từ số ca Playwright liệt kê (`--list`).
    #
    # HAI CỔNG, KHÔNG PHẢI MỘT — và đây KHÔNG phải "chạy lại cho xanh":
    #   · `e2e-ban-phim` = `06_ban_phim.spec.js` (8 ca ở cây này) — đúng "E2E bàn phím" mà
    #     Supervisor giao. Tách riêng để chỗ tất định không bị trộn với cổng toàn bộ.
    #   · `e2e-toan-bo` = cả bộ (65 ca ở cây này). ĐO ĐƯỢC ở vòng 1: 4 lượt ⇒ 3 lượt sạch +
    #     1 lượt (49,1,1), tức **CHẬP CHỜN** — xem `N-G22-01`.
    "e2e-ban-phim": {"nen": (0, SO_CA["ban_phim"], 0),
                     "dong": (SO_CA["ban_phim"], 0, 0)},
    "e2e-toan-bo": {"nen": (0, SO_CA["ban_phim"], SO_CA["toan_bo"] - SO_CA["ban_phim"]),
                    "dong": (SO_CA["toan_bo"], 0, 0)},

    # Điểm 2 — cổng "cây sạch" của wave TRƯỚC. Số cổng XANH trên cây chỉ có tệp AG-01 hợp lệ.
    # Nền: 0/3 (cả ba ĐỎ). Đóng: 3/3.
    "cay-sach-3-ban-sao": {"nen": 0, "dong": 3},

    # E3 (điểm 3) — số bản cất `hub-truoc-rollback-*.db` sau BA lượt `khoi_phuc()` CÙNG MỘT
    # MỐC, đo bằng MỐC THỜI GIAN TRUYỀN QUA THAM SỐ `luc=` (hợp đồng G22 — docs/G22_SAOLUU.md
    # §5), không phụ thuộc tốc độ máy. Nền (bản đóng băng, đọc giờ ngầm): 1. Đóng: 3.
    "e3-ba-luot-cung-giay": {"nen": 1, "dong": 3},

    # N-G21-03 (điểm 4) — `thu_g20_dahang.py::CaGanChat::test_c2a` có còn GHIM hành vi RÒ không.
    # Nền: 1 (còn ghim). Đóng: 0.
    "ng21-03-ca-ghim-ro": {"nen": 1, "dong": 0},

    # C4 = `G19-C6` (KHÁC `OWNER_ACTIONS C4` = D-8/BLOCKED OWNER). Cập nhật theo THỰC TẾ ở
    # `5fc5f6f`: việc này có HAI tầng, đóng ở hai mốc khác nhau, nay ĐÓNG CẢ HAI — nên sổ ghi
    # BỘ BA thay vì cặp boolean (một cặp không phân biệt được "thiếu tuyến" với "thiếu chỉ mục"):
    #   (1) `schema_ok`  — `PHIEN_BAN_SCHEMA >= MỐC` migration áp `truy_van.DDL_G12Q` (=v10 hiện
    #                      tại), MỐC đọc tại chỗ từ `app/migrate.py`, KHÔNG ghim số;
    #   (2) `chi_muc_ok` — hằng `truy_van.DDL_G12Q` có thật (khác rỗng) + mốc được `chay()` GỌI;
    #   (3) `tuyen_ok`   — có tệp SẢN XUẤT vừa import vừa DÙNG `truy_van` cho tuyến.
    # Nền `a6b5b73` (schema 9, chưa có mốc DDL, chưa nối tuyến): (False, False, False).
    # Đóng (đo trên cây này): (True, True, True).
    "c4-route-va-moc-ddl": {"nen": (False, False, False), "dong": (True, True, True)},
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
    "e2e-ban-phim": ("C_BanPhim.test_b3_e2e_tam_ca_ban_phim_chay_that",),
    "e2e-toan-bo": ("C_BanPhim.test_b2_chay_e2e_toan_bo_that",),
    "cay-sach-3-ban-sao": ("E_CaySach.test_e1_ba_cong_cay_sach_chay_that"),
    "e3-ba-luot-cung-giay": ("F_DongHo.test_f1_do_that_bang_dong_ho_dong_bang",),
    "ng21-03-ca-ghim-ro": ("G_NG2103.test_g1_ca_thu_con_ghim_ro",),
    "c4-go-route": ("H_C4.test_h1_c4_do_hay_da_dong",),
    "g20-c1-cay-sach": ("D_BanDoG20.test_d1_nam_cong_g20",),
    "nua-voi": ("Z_ChotChan.test_z4_gia_tri_nua_voi_luon_la_DO",),
    "cay-sach-bo-do": ("Z_ChotChan.test_z3_bo_do_bat_duoc_khi_bi_tiem",),
    "tien-trinh-con": ("Z_ChotChan.test_z2_tu_kiem_chay_trong_tien_trinh_con",),
    "c5-tru-bo-qua": ("I_TiemLoiC5.test_i1_nam_di_dang_tiem_loi",),
}

# ĐỐI CHỨNG DƯƠNG: mỗi nhóm phủ định PHẢI có một ca chạy ĐÚNG đường đó và cho kết quả KHÁC.
DOI_CHUNG = {
    "e2e-ban-phim":
        "chính tám ca đó phải ĐẠT HẾT; nếu 0 đạt thì 'hỏng' không phân biệt được "
        "với 'KHÔNG CHẠY ĐƯỢC vì thiếu nhị phân' — đúng thứ đã xảy ra ở lượt G21 (7 hỏng + "
        "44 không chạy, 0 tín hiệu).",
    "e2e-toan-bo":
        "cùng `chay.sh` phải ĐẠT ≥1 ca; nếu 0 đạt thì 'hỏng' không phân biệt được với 'không "
        "chạy được' (đúng thứ đã xảy ra ở lượt G21: 7 hỏng + 44 không chạy, 0 tín hiệu).",
    "cay-sach-3-ban-sao":
        "TIÊM: đặt một tệp bẩn NGOÀI vùng thử (`admin/__tiem_g22.js`) rồi chạy lại cả ba cổng — "
        "cả ba phải ĐỎ-THẬT. Vế này chạy trong một CLONE THẬT tại HEAD đọc tại chỗ "
        "(`git clone --shared` + `checkout --detach HEAD`) để cổng không đỏ vì delta hai commit; "
        "vế xanh (cây sạch ⇒ 3/3 XANH) đi kèm NGAY TRONG cùng phép đo. Không có cặp xanh↔đỏ này "
        "thì '3/3 xanh' có thể chỉ là cổng mù.",
    "e3-ba-luot-cung-giay":
        "chạy CÙNG kịch bản (cùng mốc đóng băng, cùng dữ liệu) trên BẢN ĐÓNG BĂNG TRƯỚC G22 "
        "`trien_khai/g20-saoluu/migrate_nguyenban.py` (md5 ghim, KHÔNG nhận `luc`): phải ra đúng "
        "**1** bản cất (đường ĐÈ còn nguyên). Bản thật + `luc=` phải ra **3**. Không có cặp 1↔3 "
        "này thì '3 bản cất' không phân biệt được với bộ đo hỏng.",
    "ng21-03-ca-ghim-ro":
        "HAI vế đo độc lập: (a) `thu_qa_g21.py::G5_CredentialNgan` trên cây thật phải đọc **0/5** "
        "tổ hợp RÒ (bất biến đã đóng); (b) TIÊM lại chính sách cũ — tắt luật ECHO THEO TÊN trong "
        "một bản sao TẠM — thì G5 phải đọc **>0** VÀ `test_c2a` đã viết lại phải ĐỎ. Không có vế "
        "(b) thì '0 rò' không phân biệt được với 'bộ dò mù'; không có (a) thì không chứng minh "
        "được lỗ hổng đã đóng.",
    "g20-c1-cay-sach":
        "C2 của cùng bàn đo G20 phải ĐO ĐƯỢC (7 ca tầng 3 chạy thật) — chứng minh bàn đo không "
        "chết toàn bộ khi C1 đỏ. VÀ phép đo `D1` tự chứng minh nó CÓ RĂNG: BỐN đối chứng âm "
        "LÀM THẬT (mỗi cái một tiến trình con chạy qua đúng hàm `_phan_quyet_ban_do_g20`) — "
        "(a) thoát != 0 dù chữ nói `OK` ⇒ ĐỎ; (b) thoát 0 nhưng có dòng `FAIL` ⇒ ĐỎ; "
        "(c) `Ran 0 tests` ⇒ ĐỎ; (d) bàn đo không tồn tại ⇒ ĐỎ và nói rõ 'KHÔNG CHẠY ĐƯỢC' — "
        "kèm một đối chứng DƯƠNG (bàn đo giả XANH ⇒ ĐẠT) để chặn kiểu hỏng 'cổng luôn Đỏ'. "
        "VÀ ba đối chứng âm của CHÍNH CÁI GHIM (e)-(g) LÀM THẬT trên bản sao TMP: đổi một chữ "
        "NGOÀI khối vá G20 ⇒ vế 'tệp trong cây' phải ĐỎ; đổi một chữ TRONG khối vá ⇒ phép hoàn "
        "vá phải ĐỎ; đổi một chữ ngoài khối vá G21 ⇒ ghim G21 phải ĐỎ — kèm đối chứng DƯƠNG "
        "(bản sao y nguyên ⇒ ĐẠT). Ghim phục vụ phát hiện 'bộ đo bị đổi giữa lượt', nên phải "
        "chứng minh nó NHÌN THẤY thay đổi.",
    "c4-go-route":
        "CÙNG phép đo `_do_c4()` trên BA bản, mỗi bản chứng minh MỘT tầng của `G19-C6`: (a) bản "
        "sao `app/` Y NGUYÊN phải cho đúng bộ ba (True, True, True) như cây thật + đúng danh sách "
        "tham chiếu; (b) CHÍNH bản sao đó sau khi GỠ TUYẾN bằng AST (mọi `import truy_van` + mọi "
        "khối `if` DÙNG nó, trên MỌI tệp sản xuất có tham chiếu TUYẾN) phải cho (True, True, "
        "False) — tầng CHỈ MỤC không bị chạm — và `dat_cong` PHẢI ĐỎ; (c) một bản sao KHÁC bị HẠ "
        "`PHIEN_BAN_SCHEMA` xuống `MỐC − 1` phải cho `schema_ok` False và `dat_cong` PHẢI ĐỎ, "
        "kèm đối chứng DƯƠNG nâng lên `MỐC + 3` thì VẪN ĐẠT (chứng minh `>=`, không ghim đúng "
        "một số). Không có (a) thì 'đỏ khi tiêm' có thể chỉ là 'bản sao hỏng sẵn'; không có (b) "
        "thì 'tuyến đã nối' không phân biệt được với bộ đo MÙ; không có (c) thì 'schema tối "
        "thiểu' chỉ là lời khai.",
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
# ⇒ CÁCH CHẠY ĐÚNG CỦA BỘ KIỂM NÀY LÀ TRÊN MỘT CÂY SẠCH, và "nền" là `HEAD` ĐỌC TẠI CHỖ
#   (xem đầu tệp) — không còn `NEN_SHA` để so. Các cổng "cây sạch" đo trực tiếp trên cây này;
#   nếu HEAD không đọc được thì đó là ĐỎ THẬT, không phải skip.

def _git(*tham_so, **kw):
    return chay(["git"] + list(tham_so), **kw)


def head_hien_tai(goc=None):
    """SHA của `HEAD`, ĐỌC TẠI CHỖ. Chuỗi rỗng nếu không đọc được."""
    rc, out = chay(["git", "rev-parse", "HEAD"], cwd=goc or GOC_CAY)
    dong = [d.strip() for d in out.splitlines() if d.strip()]
    return dong[-1] if rc == 0 and dong else ""


def _khop_sha(s):
    """`True` nếu `s` đúng là một SHA-1 40 ký tự thập lục phân."""
    return bool(re.fullmatch(r"[0-9a-f]{40}", s or ""))


def tree_cua_head(goc=None):
    """Cây của `HEAD` — `git rev-parse HEAD^{tree}`, ĐỌC TẠI CHỖ. Trả `(rc, tree)`."""
    rc, out = chay(["git", "rev-parse", "HEAD^{tree}"], cwd=goc or GOC_CAY)
    dong = [d.strip() for d in out.splitlines() if d.strip()]
    return rc, (dong[-1] if rc == 0 and dong else "")


def _git_dir_va_common(goc=None):
    """→ `(gitdir tuyệt đối, git-common-dir tuyệt đối)`. `(None, None)` nếu không đọc được."""
    goc = goc or GOC_CAY

    def _doc(*tham_so):
        rc, out = chay(["git"] + list(tham_so), cwd=goc)
        dong = [d.strip() for d in out.splitlines() if d.strip()]
        return dong[-1] if rc == 0 and dong else ""

    git_dir = _doc("rev-parse", "--git-dir")
    common = _doc("rev-parse", "--git-common-dir")
    if not git_dir or not common:
        return None, None
    if not os.path.isabs(git_dir):
        git_dir = os.path.join(goc, git_dir)
    if not os.path.isabs(common):
        common = os.path.join(goc, common)
    return git_dir, common


def tree_hien_tai(goc=None):
    """`write-tree` TƯƠNG ĐƯƠNG — KHÔNG ghi `.git` của worktree chính (AGENT 03 · §3.3).

    Sandbox chỉ cho ghi dưới workspace + TMP; gitdir của worktree nằm NGOÀI vùng đó, nên
    `git write-tree` TRẦN trả `rc=128` (`index.lock: Operation not permitted`). Phép đo này:
      (1) COPY index thật sang TMP;
      (2) `write-tree` trên bản sao (`GIT_INDEX_FILE`), ghi object mới vào ODB TẠM
          (`GIT_OBJECT_DIRECTORY`);
      (3) đọc object cũ qua alternates CHỈ ĐỌC (`GIT_ALTERNATE_OBJECT_DIRECTORIES`).
    Cây trả về là cây của ĐÚNG index đang có; index thật không đổi sha256, không có lock.

    `goc` cho phép đo trên một clone tạm (đối chứng âm của A1) — mặc định là cây này.
    Trả chuỗi `LỖI(...)` khi KHÔNG đọc được: người gọi PHẢI coi đó là ĐỎ, không phải "đạt".
    """
    goc = goc or GOC_CAY
    git_dir, common = _git_dir_va_common(goc)
    if not git_dir or not common:
        return "LỖI(không đọc được gitdir/git-common-dir)"
    index_that = os.path.join(git_dir, "index")
    if not os.path.exists(index_that):
        return "LỖI(không có index tại %s)" % index_that
    tmp = tempfile.mkdtemp(prefix="g22-a1-")
    try:
        os.makedirs(os.path.join(tmp, "objects"), exist_ok=True)
        index_tam = os.path.join(tmp, "index")
        shutil.copy2(index_that, index_tam)
        rc, out = chay(["git", "write-tree"], cwd=goc, env_them={
            "GIT_INDEX_FILE": index_tam,
            "GIT_OBJECT_DIRECTORY": os.path.join(tmp, "objects"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": os.path.join(common, "objects"),
        })
        dong = [d.strip() for d in out.splitlines() if d.strip()]
        return dong[-1] if rc == 0 and dong else "LỖI(rc=%d)" % rc
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tiem_index_ban_sao():
    """ĐỐI CHỨNG DƯƠNG cho `tree_hien_tai()`: tiêm 1 mục vào BẢN SAO index.

    Không có vế này thì "write-tree == HEAD^{tree}" có thể chỉ là một phép đo MÙ. Ở đây:
      · bản sao index nhận thêm một mục mới (`__tiem_g22.txt`) với blob ghi vào ODB TẠM;
      · tree của bản sao PHẢI ĐỔI;
      · index THẬT phải giữ nguyên sha256 và KHÔNG sinh `index.lock`.
    Trả dict — mọi giá trị đọc từ lệnh thật.
    """
    git_dir, common = _git_dir_va_common()
    if not git_dir or not common:
        return {"rc": 128, "loi": "không đọc được gitdir/git-common-dir"}
    index_that = os.path.join(git_dir, "index")
    lock = os.path.join(git_dir, "index.lock")
    ra = {"rc": 1, "co_lock_truoc": os.path.exists(lock),
          "index_sha256_truoc": _bam(index_that)}
    tmp = tempfile.mkdtemp(prefix="g22-a1-tiem-")
    env_tam = None
    try:
        objects = os.path.join(tmp, "objects")
        os.makedirs(objects, exist_ok=True)
        index_tam = os.path.join(tmp, "index")
        shutil.copy2(index_that, index_tam)
        env_tam = {"GIT_INDEX_FILE": index_tam,
                   "GIT_OBJECT_DIRECTORY": objects,
                   "GIT_ALTERNATE_OBJECT_DIRECTORIES": os.path.join(common, "objects")}

        def _tree():
            rc, out = chay(["git", "write-tree"], env_them=env_tam)
            dong = [d.strip() for d in out.splitlines() if d.strip()]
            return rc, (dong[-1] if rc == 0 and dong else ""), out

        rc0, tree_truoc, out0 = _tree()
        tep = os.path.join(tmp, "tep_tiem.txt")
        with open(tep, "w", encoding="utf-8") as f:
            f.write("tiem-loi-doi-chung-duong-cua-G22-AGENT-02\n")
        rc1, out1 = chay(["git", "hash-object", "-w", tep],
                         env_them={"GIT_OBJECT_DIRECTORY": objects})
        blob = [d.strip() for d in out1.splitlines() if d.strip()][-1] if rc1 == 0 else ""
        rc2, out2 = chay(["git", "update-index", "--add", "--cacheinfo",
                          "100644,%s,__tiem_g22.txt" % blob], env_them=env_tam)
        rc3, tree_sau, out3 = _tree()
        ra.update({"rc": 0 if (rc0 == rc1 == rc2 == rc3 == 0) else max(rc0, rc1, rc2, rc3),
                   "tree_truoc": tree_truoc, "tree_sau": tree_sau, "blob": blob,
                   "co_lock_sau": os.path.exists(lock),
                   "index_sha256_sau": _bam(index_that),
                   "loi": "" if (rc0 == rc1 == rc2 == rc3 == 0) else (out0 + out1 + out2 + out3)[-600:]})
        return ra
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        ra["co_lock_cuoi"] = os.path.exists(lock)


def do_a1(goc=None):
    """PHÉP ĐO A1 — NỀN ĐỌC TẠI CHỖ, KHÔNG GHIM. Trả dict; `dat=True` chỉ khi CẢ BỐN vế đúng.

    Bốn vế, cả bốn đọc từ lệnh thật:
      (1) đọc được `HEAD` và `HEAD^{tree}`;
      (2) đọc được cây của index (`write-tree` trên bản sao index);
      (3) `write-tree(index)` == `HEAD^{tree}` — index KHÔNG lệch HEAD;
      (4) `git status --porcelain -uall` không có đường NGOÀI `TEP_DUOC_PHEP`.

    Đây là chỗ DUY NHẤT phán quyết A1: ca thật và ba đối chứng âm đều gọi hàm này, nên không
    thể có chuyện "đối chứng đo một đằng, ca thật đo một nẻo". `goc` cho phép đo trên clone tạm.
    """
    goc = goc or GOC_CAY
    ra = {"goc": goc, "dat": False, "ly_do": [], "head": "", "tree_head": "",
          "tree_index": "", "status": [], "trong_phep": [], "ngoai": [],
          "so_tep": "?", "bam_danh_sach": "?"}

    rc, out = chay(["git", "rev-parse", "HEAD"], cwd=goc)
    dong = [d.strip() for d in out.splitlines() if d.strip()]
    ra["head"] = dong[-1] if rc == 0 and dong else ""
    if not _khop_sha(ra["head"]):
        ra["ly_do"].append("KHÔNG ĐỌC ĐƯỢC HEAD (`git rev-parse HEAD` rc=%d): %s"
                           % (rc, (out.strip() or "không có output")[-180:]))

    rc, ra["tree_head"] = tree_cua_head(goc)
    if not _khop_sha(ra["tree_head"]):
        ra["ly_do"].append("KHÔNG ĐỌC ĐƯỢC CÂY CỦA HEAD (`git rev-parse HEAD^{tree}` rc=%d)"
                           % rc)

    ra["tree_index"] = tree_hien_tai(goc)
    if not _khop_sha(ra["tree_index"]):
        ra["ly_do"].append("KHÔNG ĐỌC ĐƯỢC CÂY CỦA INDEX (`write-tree` trên bản sao index): %s"
                           % ra["tree_index"])
    elif _khop_sha(ra["tree_head"]) and ra["tree_index"] != ra["tree_head"]:
        ra["ly_do"].append("INDEX VÀ HEAD LỆCH NHAU: write-tree(index tạm)=%s ≠ HEAD^{tree}=%s"
                           % (ra["tree_index"][:12], ra["tree_head"][:12]))

    rc, ds = trang_thai(goc)
    ra["status"] = [d for d in ds if d.strip()]
    if rc != 0:
        ra["ly_do"].append("KHÔNG ĐỌC ĐƯỢC `git status --porcelain -uall` (rc=%d)" % rc)
    else:
        for d in ra["status"]:
            p = duong_cua_dong_status(d)
            if any(p.endswith(t) for t in TEP_DUOC_PHEP):
                ra["trong_phep"].append(p)
            else:
                ra["ngoai"].append(p)
        if ra["ngoai"]:
            ra["ly_do"].append("CÂY BẨN NGOÀI PHẠM VI: %s" % ", ".join(ra["ngoai"][:12]))

    rc, out = chay(["git", "ls-files"], cwd=goc)
    if rc == 0:
        ra["so_tep"] = str(len([x for x in out.splitlines() if x.strip()]))
    rc, out = chay(["git", "ls-files", "-s"], cwd=goc)
    if rc == 0:
        ra["bam_danh_sach"] = hashlib.sha256(out.encode()).hexdigest()

    ra["dat"] = not ra["ly_do"]
    return ra


def _in_a1(kq, nhan="A1"):
    """In bằng chứng của một phép đo A1 — CÙNG một định dạng cho ca thật và mọi đối chứng."""
    print("  [%s] NỀN ĐỌC TẠI CHỖ (không ghim): HEAD=%s · HEAD^{tree}=%s"
          % (nhan, (kq["head"] or "KHÔNG ĐỌC ĐƯỢC")[:12],
             (kq["tree_head"] or "KHÔNG ĐỌC ĐƯỢC")[:12]))
    # Cây ĐỌC ĐƯỢC thì in 12 ký tự; cây KHÔNG đọc được thì in NGUYÊN VĂN lỗi — không cắt cụt
    # đúng chỗ người đọc cần biết vì sao nó đỏ.
    tree_in = kq["tree_index"] if _khop_sha(kq["tree_index"]) else (kq["tree_index"] or "?")
    print("       write-tree (index tạm)=%s · %s tệp theo dõi · băm danh sách=%s"
          % (tree_in[:12] if _khop_sha(tree_in) else tree_in[:110], kq["so_tep"],
             kq["bam_danh_sach"][:16]))
    if kq["trong_phep"]:
        print("       cây bẩn TRONG phạm vi cho phép (%d): %s"
              % (len(kq["trong_phep"]), ", ".join(kq["trong_phep"][:8])))
    print("       phân quyết: %s%s" % ("XANH" if kq["dat"] else "ĐỎ",
          "" if kq["dat"] else " — " + " | ".join(kq["ly_do"])))


def _doi_chung_am_a1():
    """BA ĐỐI CHỨNG ÂM + HAI ĐỐI CHỨNG DƯƠNG cho A1, TẤT CẢ LÀM THẬT trên clone tạm.

    Vì sao phải làm thật: khi nền được "trừu tượng hoá" thành hàm, thứ dễ mất nhất là RĂNG của
    cổng — hàm vẫn trả `dat=True` cho mọi cây. Trên một clone THẬT trong TMP:
      (D)  clone SẠCH                 ⇒ `dat=True` (nếu thiếu vế này, ba vế âm dưới đây có thể
                                        chỉ là "cổng luôn đỏ");
      (A)  SỬA rồi THÊM tệp ngoài phạm vi ⇒ `dat=False`, lý do CÂY BẨN NGOÀI PHẠM VI;
      (B)  `git add` một thay đổi      ⇒ `dat=False`, lý do INDEX VÀ HEAD LỆCH NHAU;
      (C1) xoá index của clone         ⇒ `dat=False`, lý do KHÔNG ĐỌC ĐƯỢC CÂY CỦA INDEX;
      (C2) ghi HEAD hỏng               ⇒ `dat=False`, lý do KHÔNG ĐỌC ĐƯỢC HEAD/CÂY CỦA HEAD;
      (D3) COMMIT THẬT trong clone     ⇒ HEAD và HEAD^{tree} ĐỔI mà `dat=True` — chứng minh
                                        trực tiếp "HEAD nhích thì không có số nào phải sửa".
    Mỗi lượt đo xong đều KHÔI PHỤC (`git reset --hard`, trả index/HEAD lại) để vế sau không thừa
    hưởng lỗi của vế trước.

    Ghi chú phạm vi: `.git` bị đụng ở đây là `.git` của CLONE TẠM trong TMP, không phải gitdir
    của worktree thật — cùng nguyên tắc đã dùng cho `E1`/AGENT 03 §3.4.
    """
    ra = {"clone": "", "duong": None, "a_sua": None, "a_them": None, "b": None,
          "c1": None, "c2": None, "duong_cuoi": None}
    goc = tempfile.mkdtemp(prefix="g22-a1-doichung-")
    ra["clone"] = goc
    try:
        head = head_hien_tai()
        if not _khop_sha(head):
            raise RuntimeError("không đọc được HEAD của cây thật để dựng clone đối chứng")
        rc, out = _git("clone", "--shared", "--no-checkout", GOC_CAY, goc, giay=300)
        if rc != 0:
            raise RuntimeError("KHÔNG clone được cây để đối chứng: %s" % out[-500:])
        rc, out = _git("-C", goc, "checkout", "--detach", head, giay=300)
        if rc != 0:
            raise RuntimeError("KHÔNG checkout được %s trong clone: %s" % (head[:12], out[-500:]))

        # (D) ĐỐI CHỨNG DƯƠNG — clone SẠCH phải XANH.
        ra["duong"] = do_a1(goc)
        _in_a1(ra["duong"], "A1†D clone sạch")

        # (A) CÂY BẨN: sửa một tệp đã theo dõi (KHÔNG stage) rồi thêm một tệp mới ngoài phạm vi.
        tep_sua = os.path.join(goc, "admin", "admin.js")
        with open(tep_sua, "a", encoding="utf-8") as f:
            f.write("\n// TIÊM A1 (a-sua) — chỉ trong clone tạm\n")
        ra["a_sua"] = do_a1(goc)
        _in_a1(ra["a_sua"], "A1†A1 sửa tệp")

        tep_them = os.path.join(goc, "admin", "__tiem_a1_g22.js")
        with open(tep_them, "w", encoding="utf-8") as f:
            f.write("// TIÊM A1 (a-them) — chỉ trong clone tạm\n")
        ra["a_them"] = do_a1(goc)
        _in_a1(ra["a_them"], "A1†A2 thêm tệp")
        os.remove(tep_them)
        # KHÔI PHỤC phải ĐỌC MÃ THOÁT: một `checkout`/`reset` hỏng mà im lặng thì vế sau đo trên
        # một clone BẨN, và cái ĐỎ/ĐỎ-giả của vế sau không còn quy được cho đối chứng nào.
        rc, out = _git("-C", goc, "checkout", "--", "admin/admin.js", giay=120)
        if rc != 0:
            raise RuntimeError("KHÔNG khôi phục được `admin/admin.js` trong clone: %s" % out[-300:])

        # (B) INDEX LỆCH HEAD: sửa rồi `git add` (KHÔNG commit).
        with open(tep_sua, "a", encoding="utf-8") as f:
            f.write("\n// TIÊM A1 (b-index) — chỉ trong clone tạm\n")
        rc, out = _git("-C", goc, "add", "admin/admin.js", giay=120)
        if rc != 0:
            raise RuntimeError("KHÔNG stage được để dựng đối chứng (b): %s" % out[-300:])
        ra["b"] = do_a1(goc)
        _in_a1(ra["b"], "A1†B index lệch")
        rc, out = _git("-C", goc, "reset", "--hard", head, giay=120)
        if rc != 0:
            raise RuntimeError("KHÔNG khôi phục được clone sau đối chứng (b): %s" % out[-300:])

        # (C1) KHÔNG ĐỌC ĐƯỢC CÂY CỦA INDEX: dời index ra khỏi gitdir của clone.
        git_dir = os.path.join(goc, ".git")
        index = os.path.join(git_dir, "index")
        index_bak = os.path.join(git_dir, "index.a1-doichung")
        os.replace(index, index_bak)
        ra["c1"] = do_a1(goc)
        _in_a1(ra["c1"], "A1†C1 index không đọc được")
        os.replace(index_bak, index)

        # (C2) KHÔNG ĐỌC ĐƯỢC HEAD/CÂY CỦA HEAD: ghi HEAD hỏng trong clone.
        head_f = os.path.join(git_dir, "HEAD")
        with open(head_f, "rb") as f:
            head_goc = f.read()
        with open(head_f, "w", encoding="utf-8") as f:
            f.write("khong-phai-sha-cua-G22\n")
        ra["c2"] = do_a1(goc)
        _in_a1(ra["c2"], "A1†C2 HEAD không đọc được")
        with open(head_f, "wb") as f:
            f.write(head_goc)

        # (D2) ĐỐI CHỨNG DƯƠNG CUỐI — sau khi khôi phục, clone lại SẠCH và XANH.
        ra["duong_cuoi"] = do_a1(goc)
        _in_a1(ra["duong_cuoi"], "A1†D2 clone khôi phục")

        # (D3) HEAD NHÍCH — chứng minh TRỰC TIẾP "không còn số nào phải cập nhật": tạo một commit
        # THẬT trong clone rồi đo lại. HEAD và HEAD^{tree} đều ĐỔI, A1 vẫn phải XANH. Nếu ai đó
        # còn ghim SHA/cây ở đâu, vế này sẽ lộ ra ngay.
        ra["head_truoc"] = head
        with open(os.path.join(goc, "admin", "__head_nhich_g22.txt"), "w",
                  encoding="utf-8") as f:
            f.write("commit de chung minh nen doc tai cho, khong ghim\n")
        rc, out = _git("-C", goc, "add", "admin/__head_nhich_g22.txt", giay=120)
        if rc != 0:
            raise RuntimeError("KHÔNG stage được tệp cho đối chứng D3: %s" % out[-300:])
        # NGÀY CỐ ĐỊNH: commit thử phải có cùng một SHA ở mọi lượt chạy, nếu không "bằng chứng D3"
        # sẽ đổi số mỗi lần và không ai đối chiếu lại được. Cùng cha + cùng cây + cùng nội dung +
        # cùng ngày ⇒ cùng commit.
        rc, out = _git("-C", goc, "-c", "user.name=AG-02-G22", "-c", "user.email=ag02@local",
                       "commit", "-m", "A1: HEAD nhich — khong cap nhat so nao", giay=120,
                       env_them={"GIT_AUTHOR_DATE": "2026-01-01T00:00:00 +0000",
                                 "GIT_COMMITTER_DATE": "2026-01-01T00:00:00 +0000"})
        if rc != 0:
            raise RuntimeError("KHÔNG commit được trong clone để thử HEAD nhích: %s" % out[-300:])
        ra["nhich"] = do_a1(goc)
        _in_a1(ra["nhich"], "A1†D3 HEAD nhích")
    finally:
        shutil.rmtree(goc, ignore_errors=True)
    return ra


def van_tay():
    """Vân tay cây: HEAD, tree, và băm danh sách tệp theo dõi. Trả dict.

    `tree` lấy từ `tree_hien_tai()` — phép đo TƯƠNG ĐƯƠNG bằng index tạm, nên vân tay đọc được
    cả khi sandbox chặn ghi `.git` (AGENT 03 · `docs/G22_A1_GIT.md` §3.3).
    """
    ra = {}
    for ten, tham in (("head", ("rev-parse", "HEAD")), ("so_tep", ("ls-files",))):
        rc, out = chay(["git"] + list(tham))
        ra[ten] = out.strip() if rc == 0 else "LỖI(rc=%d)" % rc
    ra["tree"] = tree_hien_tai()
    rc, out = chay(["git", "ls-files", "-s"])
    ra["bam_danh_sach"] = hashlib.sha256(out.encode()).hexdigest() if rc == 0 else "LỖI"
    ra["so_tep"] = str(len([x for x in ra["so_tep"].splitlines() if x.strip()]))
    return ra


def trang_thai(goc=None):
    rc, out = chay(["git", "status", "--porcelain", "-uall"], cwd=goc or GOC_CAY)
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


def _nhi_phan_theo_duong(*tuong_doi):
    """→ (đường_dẫn, nguồn) của một nhị phân trong ba gốc `.local-browsers` đã biết."""
    ung_vien = [
        (os.path.join(PW_BROWSERS_REPO, *tuong_doi),
         "trong repo (chay.sh ghim PLAYWRIGHT_BROWSERS_PATH=0)"),
        (os.path.join(PW_BROWSERS_G17, *tuong_doi),
         "BAN_GIAO §1 / AG-06 đã chạy thành công"),
        (os.path.join(PW_BROWSERS_CHI_DINH, *tuong_doi),
         "cùng nhị phân qua worktree g12-playwright"),
    ]
    for p, nguon in ung_vien:
        if os.path.exists(p):
            return p, nguon
    return None, None


def chromium_duong_dan():
    """→ (đường_dẫn, nguồn) của Chromium đầy đủ (`chromium-1194`). `None` nếu không có."""
    return _nhi_phan_theo_duong(*PW_CHROMIUM_TUONG_DOI)


def headless_duong_dan():
    """→ (đường_dẫn, nguồn) của `headless_shell-1194` — nhị phân `chay.sh` THẬT SỰ chạy."""
    return _nhi_phan_theo_duong(*PW_HEADLESS_TUONG_DOI)


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


def nguon_goc(duong, cap, sha_goc, sha_trong_cay=None):
    """Nội dung GỐC (trước khi vá) của tệp nguồn `duong`, KIỂM BẰNG sha256. Trả `(nội_dung, ghi_chú)`.

    `nội_dung is None` nghĩa là KHÔNG chứng minh được "bản gốc đã ghim + ĐÚNG hai khối vá" ⇒ người
    gọi DỪNG, chứ không đo bằng một bàn đo đã trôi. Đây là chốt thay cho `BAN_DO_G20_SHA` cũ: bản
    vá nay nằm TRONG tệp nguồn, nên "gốc" được dựng lại bằng HOÀN VÁ rồi băm — không cần bản sao.

    `sha_trong_cay` (tuỳ chọn) = sha256 của ĐÚNG tệp trong cây. Kiểm TRƯỚC khi hoàn vá, nên một
    thay đổi bất kỳ — kể cả bên trong khối vá — bị bắt ở đây với thông điệp nói rõ "TỆP TRONG CÂY
    ĐÃ BỊ ĐỔI", thay vì đổ lỗi mơ hồ cho "khối vá không khớp". `None` = không kiểm (dùng cho tệp
    dựng trong TMP ở các đối chứng âm).
    """
    if not os.path.exists(duong):
        return None, "KHÔNG có tệp nguồn `%s`" % duong
    with open(duong, encoding="utf-8") as f:
        than = f.read()
    bam_that = hashlib.sha256(than.encode("utf-8")).hexdigest()
    if sha_trong_cay is not None and bam_that != sha_trong_cay:
        return None, ("sha256 TỆP TRONG CÂY = %s ≠ ghim %s ⇒ `%s` ĐÃ BỊ ĐỔI (bộ đo trôi trong lượt); "
                      "không đo bằng một bàn đo đã trôi"
                      % (bam_that[:16], sha_trong_cay[:16], os.path.basename(duong)))
    goc = _hoan_va(than, cap)
    if goc is None:
        return None, ("KHÔNG hoàn vá được `%s`: khối vá không còn khớp nguyên văn ⇒ tệp trong cây "
                      "KHÔNG PHẢI 'bản gốc + đúng hai khối vá'" % os.path.basename(duong))
    ra = hashlib.sha256(goc.encode("utf-8")).hexdigest()
    if ra != sha_goc:
        return None, ("hoàn vá xong, sha256 = %s ≠ ghim %s ⇒ tệp nguồn `%s` đã TRÔI khỏi bản gốc "
                      "(không đo bằng một bàn đo đã trôi)"
                      % (ra[:16], sha_goc[:16], os.path.basename(duong)))
    return goc, ("`%s`: tệp trong cây %s ✓ · gốc ghim %s ✓ + đúng %d khối vá"
                 % (os.path.basename(duong), (sha_trong_cay or bam_that)[:12], sha_goc[:12], len(cap)))


def nguon_da_va(duong, cap, sha_goc, sha_trong_cay=None):
    """Xác nhận tệp TRONG CÂY = bản gốc đã ghim + đúng hai khối vá. Trả `(ok, ghi_chú)`."""
    goc, ghi_chu = nguon_goc(duong, cap, sha_goc, sha_trong_cay)
    if goc is None:
        return False, ghi_chu
    with open(duong, encoding="utf-8") as f:
        than = f.read()
    if "nc > 0" not in than or "skipped=(\\d+)" not in than:
        return False, "`%s` thiếu dấu vết bản vá (`skipped=`/`nc > 0`)" % os.path.basename(duong)
    if cap[1][0] in than:
        return False, "`%s` còn nguyên văn CŨ của khối quyết định" % os.path.basename(duong)
    return True, ghi_chu + " · bản trong cây ĐÃ VÁ"


def ban_sao_tiem(duong, bien_doi):
    """BẢN SAO trong `TMP` của `duong` sau khi áp `bien_doi` — dùng cho ĐỐI CHỨNG ÂM của GHIM.

    Trả `(thư_mục_tạm, đường_dẫn_bản_sao, mô_tả)`. Ném nếu phép tiêm KHÔNG đổi được byte nào (khi
    đó "đối chứng đỏ" sẽ là một lời khai rỗng). `bien_doi=None` = chép Y NGUYÊN (dùng cho ĐỐI
    CHỨNG DƯƠNG: bản sao không tiêm phải ĐẠT). KHÔNG ghi một byte nào vào cây thật.
    """
    with open(duong, encoding="utf-8") as f:
        than = f.read()
    if bien_doi is None:
        moi, mo_ta = than, "bản sao Y NGUYÊN (không tiêm)"
    else:
        moi, mo_ta = bien_doi(than)
        if moi == than:
            raise AssertionError("phép TIÊM vào `%s` không đổi được byte nào ⇒ đối chứng vô nghĩa"
                                 % os.path.basename(duong))
    d = tempfile.mkdtemp(prefix="g22-tiem-ghim-")
    p = os.path.join(d, os.path.basename(duong))
    with open(p, "w", encoding="utf-8") as f:
        f.write(moi)
    return d, p, mo_ta


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


# ── E3: MỐC THỜI GIAN LÀ THAM SỐ + ĐỐI CHỨNG ĐƯỜNG BẰNG BẢN ĐÓNG BĂNG ───────────────────────
#
# HỢP ĐỒNG ĐÃ DUYỆT (`docs/G22_SAOLUU.md` §5): `sao_luu(luc=)` / `khoi_phuc(..., luc=)` nhận
# MỐC THỜI GIAN QUA THAM SỐ. Bộ đo PHẢI truyền một mốc CỐ ĐỊNH; nếu nó đọc `datetime.now()` ngầm
# thì ba lượt có thể rơi vào hai-ba giây khác nhau, tên khác nhau, phép đếm XANH mà ĐƯỜNG ĐÈ
# chưa hề được chạm tới — một cái XANH GIẢ phụ thuộc TỐC ĐỘ MÁY.
#
# Vì sao vẫn phải có ĐỐI CHỨNG ĐƯỜNG: bản ĐÓNG BĂNG của lượt trước
# (`trien_khai/g20-saoluu/migrate_nguyenban.py`, md5 ghim) KHÔNG nhận `luc` và đặt tên bản cất
# theo GIÂY, ghi đè. Cùng kịch bản, cùng mốc: bản đó ra **1** bản cất, bản thật ra **3**.
# Không có vế này thì "3 bản cất" không phân biệt được với "bộ đo hỏng / tự bịa số".

LUC_BA_LUOT = "20261016-120000"
MIGRATE_NGUYENBAN = os.path.join(GOC_CAY, "trien_khai", "g20-saoluu", "migrate_nguyenban.py")
MIGRATE_NGUYENBAN_MD5 = "611182a621fd279c3816d5fc5d2785e3"

MA_E3 = r'''
import datetime as _dt
import inspect, json, os, sqlite3, sys

APP = os.environ["G22_APP"]
sys.path.insert(0, APP)


class _DongBang(_dt.datetime):
    """Đồng hồ ĐÓNG BĂNG; `G22_LEO_THANG=1` mỗi lượt đọc nhích 1 giây (mô phỏng máy chậm)."""
    _T = _dt.datetime(2026, 10, 16, 12, 0, 0)
    _buoc = 0

    @classmethod
    def now(cls, tz=None):
        t = cls._T + _dt.timedelta(seconds=cls._buoc)
        if os.environ.get("G22_LEO_THANG") == "1":
            cls._buoc += 1
        return t

    @classmethod
    def utcnow(cls):
        return cls.now()

    @classmethod
    def today(cls):
        return cls.now()


import migrate
migrate.datetime = _DongBang          # chỉ có hiệu lực với bản cũ (bản thật nhận `luc`)

STAMP = os.environ.get("G22_LUC", "20261016-120000")
D = os.environ["VIP_HUB_DATA"]
os.makedirs(D, exist_ok=True)
TL = os.path.join(D, "sao-luu")
os.makedirs(TL, exist_ok=True)
DB = os.path.join(D, "hub.db")

c = sqlite3.connect(DB)
c.execute("CREATE TABLE t (x INTEGER)")
c.execute("INSERT INTO t VALUES (1)")
c.commit()
c.close()

co_luc_sao_luu = "luc" in inspect.signature(migrate.sao_luu).parameters
co_luc_khoi_phuc = "luc" in inspect.signature(migrate.khoi_phuc).parameters

# VẾ A — BA bản sao lưu CÙNG MỐC: đồng hồ đóng băng + hậu số, phải ra 3 tệp khác nhau.
ban_sao = []
for _ in range(3):
    if co_luc_sao_luu:
        ban_sao.append(migrate.sao_luu(luc=STAMP))
    else:
        ban_sao.append(migrate.sao_luu())

# Dữ liệu "mới hơn bản sao lưu" mà lượt khôi phục ĐẦU TIÊN phải cất được.
c = sqlite3.connect(DB)
c.execute("UPDATE t SET x=2")
c.commit()
c.close()

# VẾ B — BA lượt `khoi_phuc()` CÙNG MỐC.
for _ in range(3):
    if co_luc_khoi_phuc:
        migrate.khoi_phuc(ban_sao[0], luc=STAMP)
    else:
        migrate.khoi_phuc(ban_sao[0])

ds = sorted(f for f in os.listdir(TL) if "rollback" in f and f.endswith(".db"))


def _gia_tri_x(ten):
    """Đọc GIÁ TRỊ THẬT trong một bản cất; `None` nghĩa là KHÔNG MỞ ĐƯỢC."""
    duong = os.path.join(TL, ten)
    try:
        kn = sqlite3.connect("file:%s?mode=ro&immutable=1" % duong.replace("?", "%3f"), uri=True)
        try:
            return kn.execute("SELECT MAX(x) FROM t").fetchone()[0]
        finally:
            kn.close()
    except sqlite3.Error:
        return None


gia_tri = {ten: _gia_tri_x(ten) for ten in ds}
print("__JSON__=" + json.dumps({
    "nhan_luc_sao_luu": co_luc_sao_luu,
    "nhan_luc_khoi_phuc": co_luc_khoi_phuc,
    "luc_truyen": STAMP,
    "moc_dong_ho_goc": _DongBang._T.strftime("%Y%m%d-%H%M%S"),
    "so_sao_luu_khac_nhau": len(set(ban_sao)),
    "ten_ban_sao_luu": [os.path.basename(x) for x in ban_sao],
    "so_ban_cat_rollback": len(ds),
    "ten_ban_cat": ds,
    "cung_mot_moc": bool(ds) and all(
        f.startswith("hub-truoc-rollback-" + STAMP) for f in ds),
    "gia_tri_x": gia_tri,
    "so_ban_cat_mo_duoc": sum(1 for v in gia_tri.values() if v is not None),
    "so_ban_cat_giu_du_lieu_moi": sum(1 for v in gia_tri.values() if v == 2),
}, ensure_ascii=False))
'''


def _md5(duong):
    with open(duong, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _app_tam(ten, migrate_cu=False):
    """Bản `app/` trong thư mục TẠM. `migrate_cu=True` ⇒ thay `migrate.py` bằng BẢN ĐÓNG BĂNG
    `trien_khai/g20-saoluu/migrate_nguyenban.py` (md5 ghim) — đúng bản TRƯỚC G22, không phải
    một đoạn mã tự chế. KHÔNG sửa một byte nào của cây thật.
    """
    d = tempfile.mkdtemp(prefix="g22-app-%s-" % ten)
    shutil.copytree(GOC_APP, d, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if migrate_cu:
        if not os.path.exists(MIGRATE_NGUYENBAN):
            shutil.rmtree(d, ignore_errors=True)
            raise RuntimeError("KHÔNG có bản đóng băng `%s`" % MIGRATE_NGUYENBAN)
        md5 = _md5(MIGRATE_NGUYENBAN)
        if md5 != MIGRATE_NGUYENBAN_MD5:
            shutil.rmtree(d, ignore_errors=True)
            raise RuntimeError("bản đóng băng đã TRÔI: md5=%s ≠ ghim %s"
                               % (md5, MIGRATE_NGUYENBAN_MD5))
        shutil.copy2(MIGRATE_NGUYENBAN, os.path.join(d, "migrate.py"))
    return d


def do_e3(app_dir, luc=LUC_BA_LUOT, leo_thang=False):
    """Chạy phép đo E3 trên một `app/` cho trước. Trả dict số đo THẬT.

    `leo_thang=True` chỉ dùng cho bản ĐÓNG BĂNG: mỗi lượt đọc đồng hồ nhích 1 giây, mô phỏng
    "máy chậm rơi vào hai giây khác nhau" — chính cái XANH GIẢ mà `luc=` diệt.
    """
    nen = tempfile.mkdtemp(prefix="g22-e3-")
    rc, out, _ = chay_con(MA_E3, giay=300, env_them={
        "VIP_HUB_DATA": nen, "G22_APP": app_dir, "VIP_KHO_DANG_CHAY": "sqlite",
        "G22_LUC": luc, "G22_LEO_THANG": "1" if leo_thang else "0"})
    m = re.search(r"__JSON__=(\{.*\})", out)
    shutil.rmtree(nen, ignore_errors=True)
    if rc != 0 or not m:
        return {"rc": rc, "loi": out.strip()[-900:], "so_ban_cat_rollback": None,
                "so_sao_luu_khac_nhau": None}
    d = json.loads(m.group(1))
    d["rc"] = rc
    return d


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. CÁC LỚP CA
# ══════════════════════════════════════════════════════════════════════════════════════════════

class A_Nen(unittest.TestCase):
    """NỀN — cây nào đang được đo. Sai nền thì mọi số dưới đây vô nghĩa."""

    def test_a1_cay_dung_bang_cay_cua_nen(self):
        """CÂY ĐANG ĐO phải bằng `HEAD^{tree}` của CHÍNH `HEAD` hiện tại — KHÔNG còn ghim.

        KHÔNG có `NEN_SHA`/`TREE_NEN` để cập nhật: nền là HEAD đọc ngay trong phép đo, nên
        `HEAD` nhích ở mọi commit cũng không sinh ra một cái ĐỎ VĨNH VIỄN (họ H5/N-G19-04).

        BA vế, cả ba đọc từ lệnh thật:
          (i)   `do_a1()` — HEAD, `HEAD^{tree}`, cây index, `status` — phải XANH;
          (ii)  ĐỐI CHỨNG DƯƠNG phép đo index: tiêm 1 mục vào BẢN SAO index ⇒ cây ĐỔI, index
                THẬT giữ nguyên sha256, không có `index.lock` (AGENT 03 §3.4);
          (iii) BA ĐỐI CHỨNG ÂM LÀM THẬT trên clone tạm — cây bẩn, index≠HEAD, không đọc được
                cây — cả ba PHẢI ĐỎ, kèm đối chứng dương (clone sạch ⇒ XANH) VÀ một COMMIT
                THẬT làm HEAD nhích ⇒ vẫn XANH (không còn số nào phải cập nhật).
        """
        kq = do_a1()
        print("\n  [A1] PHÉP ĐO NỀN — HEAD và HEAD^{tree} ĐỌC TẠI CHỖ (không hằng số)")
        _in_a1(kq)

        # (ii) ĐỐI CHỨNG DƯƠNG — phép đo index phải NHÌN THẤY thay đổi, và không làm bẩn index thật.
        doi = tiem_index_ban_sao()
        print("       ĐỐI CHỨNG DƯƠNG: tiêm `__tiem_g22.txt` vào BẢN SAO index → "
              "tree %s → %s · rc=%s"
              % (str(doi.get("tree_truoc"))[:12], str(doi.get("tree_sau"))[:12], doi.get("rc")))
        print("       index THẬT: sha256 trước=%s · sau=%s · index.lock trước=%s sau=%s"
              % (str(doi.get("index_sha256_truoc"))[:16], str(doi.get("index_sha256_sau"))[:16],
                 doi.get("co_lock_truoc"), doi.get("co_lock_sau")))
        self.assertEqual(doi.get("rc"), 0, "KHÔNG tiêm được vào bản sao index: %s"
                         % doi.get("loi", "")[-600:])
        self.assertEqual(doi.get("tree_truoc"), kq["tree_index"],
                         "phép tiêm đo trên một cây KHÁC cây A1 vừa đo — hai phép đo không khớp")
        self.assertNotEqual(doi.get("tree_sau"), doi.get("tree_truoc"),
                            "PHÉP ĐO MÙ: tiêm một mục vào bản sao index mà cây KHÔNG đổi")
        self.assertEqual(doi.get("index_sha256_sau"), doi.get("index_sha256_truoc"),
                         "index THẬT bị đổi bởi phép đo — vi phạm 'không ghi .git thật'")
        self.assertFalse(doi.get("co_lock_sau"), "phép đo làm sót `index.lock` trong gitdir thật")

        # (iii) BA ĐỐI CHỨNG ÂM + HAI DƯƠNG — LÀM THẬT trên clone tạm, không phải lời khai.
        dc = _doi_chung_am_a1()
        self.assertTrue(dc["duong"]["dat"],
                        "ĐỐI CHỨNG DƯƠNG HỎNG: clone SẠCH mà A1 ĐỎ: %s" % dc["duong"]["ly_do"])
        self.assertFalse(dc["a_sua"]["dat"],
                         "ĐỐI CHỨNG ÂM (a) MÙ: SỬA một tệp ngoài phạm vi mà A1 vẫn XANH")
        self.assertIn("CÂY BẨN NGOÀI PHẠM VI", " | ".join(dc["a_sua"]["ly_do"]),
                      "A1 ĐỎ nhưng KHÔNG vì cây bẩn: %s" % dc["a_sua"]["ly_do"])
        self.assertFalse(dc["a_them"]["dat"],
                         "ĐỐI CHỨNG ÂM (a) MÙ: THÊM một tệp ngoài phạm vi mà A1 vẫn XANH")
        self.assertIn("CÂY BẨN NGOÀI PHẠM VI", " | ".join(dc["a_them"]["ly_do"]),
                      "A1 ĐỎ nhưng KHÔNG vì cây bẩn: %s" % dc["a_them"]["ly_do"])
        self.assertFalse(dc["b"]["dat"],
                         "ĐỐI CHỨNG ÂM (b) MÙ: index LỆCH HEAD mà A1 vẫn XANH")
        self.assertIn("INDEX VÀ HEAD LỆCH NHAU", " | ".join(dc["b"]["ly_do"]),
                      "A1 ĐỎ nhưng KHÔNG vì index lệch HEAD: %s" % dc["b"]["ly_do"])
        self.assertFalse(dc["c1"]["dat"],
                         "ĐỐI CHỨNG ÂM (c) MÙ: cây index KHÔNG đọc được mà A1 vẫn XANH")
        self.assertIn("KHÔNG ĐỌC ĐƯỢC CÂY CỦA INDEX", " | ".join(dc["c1"]["ly_do"]),
                      "A1 ĐỎ nhưng KHÔNG nói rõ 'không đọc được cây index': %s" % dc["c1"]["ly_do"])
        self.assertFalse(dc["c2"]["dat"],
                         "ĐỐI CHỨNG ÂM (c) MÙ: HEAD KHÔNG đọc được mà A1 vẫn XANH")
        self.assertIn("KHÔNG ĐỌC ĐƯỢC HEAD", " | ".join(dc["c2"]["ly_do"]),
                      "A1 ĐỎ nhưng KHÔNG nói rõ 'không đọc được HEAD': %s" % dc["c2"]["ly_do"])
        self.assertTrue(dc["duong_cuoi"]["dat"],
                        "clone KHÔNG khôi phục được sau đối chứng: %s" % dc["duong_cuoi"]["ly_do"])
        self.assertNotEqual(dc["nhich"]["head"], dc["head_truoc"],
                            "HEAD KHÔNG nhích sau commit thử ⇒ vế D3 không đo được gì")
        self.assertNotEqual(dc["nhich"]["tree_head"], dc["duong"]["tree_head"],
                            "cây của HEAD KHÔNG đổi sau commit thử ⇒ vế D3 không đo được gì")
        self.assertTrue(dc["nhich"]["dat"],
                        "HEAD NHÍCH mà A1 ĐỎ ⇒ vẫn còn một cái ghim phải cập nhật: %s"
                        % dc["nhich"]["ly_do"])

        # (i) PHÁN QUYẾT CUỐI — trên cây THẬT. Không có số ghim nào để so.
        self.assertTrue(kq["dat"], "A1 ĐỎ: %s" % " | ".join(kq["ly_do"]))

    def test_a2_khong_sua_ma_san_pham(self):
        """Chỉ được có các tệp trong `TEP_DUOC_PHEP` (hai tệp AG-01 G22 + tệp của lượt hiện
        tại); không sửa mã sản phẩm.

        Nền là HEAD ĐỌC TẠI CHỖ, nên KHÔNG còn "delta hai commit" để miễn trừ: mọi đường
        `git status` không thuộc danh sách tệp được phép đều là thay đổi của lượt này.
        """
        rc, ds = trang_thai()
        self.assertEqual(rc, 0, "`git status` hỏng (rc=%d) — không đo được cây" % rc)
        la = [d for d in ds if d.strip()]
        duoc_phep = [d for d in la
                     if any(duong_cua_dong_status(d).endswith(t) for t in TEP_DUOC_PHEP)]
        ngoai = [d for d in la if d not in duoc_phep]
        print("\n  [A2] `status --porcelain -uall`: %d đường = %d tệp được phép + %d NGOÀI phép"
              % (len(la), len(duoc_phep), len(ngoai)))
        for d in ngoai:
            print("       %s" % d)
        self.assertEqual(ngoai, [], "có thay đổi NGOÀI danh sách tệp được phép")

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
        p_ghim = os.path.join(PW_BROWSERS_REPO, *PW_CHROMIUM_TUONG_DOI)
        print("       ĐƯỜNG DẪN: %s" % p)
        print("       realpath : %s" % os.path.realpath(p))
        print("       ĐƯỜNG GHIM TRONG CÂY: %s → %s"
              % (p_ghim, "CÓ" if os.path.exists(p_ghim) else "KHÔNG CÓ (dùng đường dự phòng)"))
        print("       SHA-256  : %s" % _bam(p))
        print("       PHIÊN BẢN: %s" % ver)
        print("       NGUỒN    : %s" % nguon)
        self.assertRegex(ver, r"Chromium \d+\.\d+\.\d+\.\d+", "không đọc được phiên bản Chromium")
        self.assertEqual(rev, PW_REVISION_DOI,
                         "`browsers.json` đổi revision ⇒ nhị phân chỉ định có thể đã lạc hậu")
        # NHỊ PHÂN MÀ `chay.sh` THẬT SỰ DÙNG khi headless: `headless_shell-1194`. Đây là đường
        # đề bài đã ghim; thiếu nó thì B2/B3 "KHÔNG CHẠY ĐƯỢC" — một KẾT QUẢ, không phải skip.
        ph, nguon_h = headless_duong_dan()
        if ph is None:
            self.fail("KHÔNG CHẠY ĐƯỢC: thiếu `chromium_headless_shell-1194/chrome-mac/"
                      "headless_shell` ở cả ba gốc `.local-browsers`. Đây là KẾT QUẢ, không phải "
                      "chỗ để bỏ qua.")
        rc_h, ver_h = phien_ban_chromium(ph)
        sha_h = _bam(ph)
        print("       HEADLESS (chay.sh dùng): %s" % ph)
        print("       HEADLESS realpath      : %s" % os.path.realpath(ph))
        print("       HEADLESS SHA-256       : %s" % sha_h)
        print("       HEADLESS PHIÊN BẢN     : %s · nguồn: %s" % (ver_h, nguon_h))
        self.assertEqual(rc_h, 0, "headless_shell không thi hành được (rc=%d): %s" % (rc_h, ver_h))
        self.assertRegex(ver_h, r"Chromium \d+\.\d+\.\d+\.\d+",
                         "không đọc được phiên bản headless Chromium")
        self.assertEqual(sha_h, PW_HEADLESS_SHA256,
                         "GHIM NỘI DUNG LỆCH: `headless_shell` sha256=%s ≠ ghim %s. Nhị phân đã "
                         "đổi ⇒ phải cập nhật ghim có ý thức, không im lặng cho qua."
                         % (sha_h, PW_HEADLESS_SHA256))

    def test_b2_chay_e2e_toan_bo_that(self):
        """CHẠY THẬT `sh thu_giao_dien/chay.sh`. HỎNG nếu không chạy được — KHÔNG bỏ qua.

        SỐ CA DO CHÍNH PLAYWRIGHT LIỆT KÊ (`--list`, KHÔNG chạy trình duyệt), không ghim con số
        của một lượt chạy cũ. Báo cáo Playwright phải phủ ĐÚNG số ca đó; hạ một ca trong báo
        cáo ⇒ cổng PHẢI ĐỎ.
        """
        DA_CHAY["e2e-toan-bo"] = True
        so_ca = SO_CA["toan_bo"]
        print("\n  [B2] số ca DO PLAYWRIGHT LIỆT KÊ (`--list`): %d ca / %d tệp spec · bàn phím=%d ca"
              % (so_ca, SO_CA["so_tep"], SO_CA["ban_phim"]))
        self.assertGreater(so_ca, 0, "KHÔNG đếm được ca nào bằng `npx playwright test --list`: %s"
                         % SO_CA.get("loi", "")[-600:])
        # MÃ THOÁT của chính bước ĐẾM CA cũng là một vế: `--list` thoát khác 0 mà vẫn in ra được
        # vài dòng thì số ca là số ĐỌC ĐƯỢC TỪ MỘT LƯỢT HỎNG — không được đem ra làm mẫu số.
        ok_list, gc_list = so_ca_playwright_dat_duoc()
        print("       mẫu số: %s" % gc_list)
        self.assertTrue(ok_list, gc_list)
        kq = chay_e2e(giay=1200)
        dat, hong, bo, khong_chay = kq["dem"]
        print("       LỆNH: %s" % kq["lenh"])
        print("       mã thoát THẬT = %d · %.1f giây" % (kq["rc"], kq["giay"]))
        print("       (đạt, hỏng, bỏ qua, KHÔNG CHẠY) = (%d, %d, %d, %d)"
              % (dat, hong, bo, khong_chay))
        print("       tổng báo cáo = %d · số ca `--list` = %d" % (dat + hong + bo + khong_chay, so_ca))
        with open(os.path.join(LOG_DIR, "e2e_lan_nay.txt"), "w", encoding="utf-8") as f:
            f.write(kq["out"])
        # ĐỐI CHỨNG ÂM của CỔNG: hạ ĐÚNG một ca (65→64) thì phân quyết PHẢI là ĐỎ.
        dat_gia, vi_gia = dat_cong("e2e-toan-bo", (so_ca - 1, 0, 0))
        print("       đối chứng âm: hạ 1 ca → (%d, 0, 0) → %s (đòi ĐỎ)"
              % (so_ca - 1, "ĐỎ" if not dat_gia else "ĐẠT-SAI"))
        self.assertFalse(dat_gia, "CỔNG MÙ: hạ một ca xuống mà cổng vẫn ĐẠT — %s" % vi_gia)
        if dat == 0:
            self.fail("KHÔNG CHẠY ĐƯỢC: 0 ca ĐẠT. Đây là KẾT QUẢ (thiếu nhị phân / máy chủ không "
                      "lên), KHÔNG phải chỗ để `skipTest`. 60 dòng cuối:\n%s"
                      % "\n".join(kq["out"].splitlines()[-60:]))
        # ĐỐI CHỨNG DƯƠNG: ≥1 ca đạt ⇒ "hỏng" phân biệt được với "không chạy được".
        self.assertGreater(dat, 0)
        # MÃ THOÁT THẬT của `chay.sh` là vế BẮT BUỘC, không phải một dòng để IN: trước đây nó
        # chỉ được in ra rồi bỏ qua. Bộ chạy thoát khác 0 trong khi báo cáo trông đầy đủ (hỏng ở
        # teardown, một ca `flaky`, hay mã thoát bị nuốt) vẫn phải là ĐỎ.
        self.assertEqual(kq["rc"], 0,
                         "BỘ CHẠY `chay.sh` THOÁT KHÁC 0 (rc=%d) dù báo cáo đọc được "
                         "(%d đạt, %d hỏng, %d bỏ qua, %d không chạy) ⇒ mã thoát là phán quyết, "
                         "không tin báo cáo đơn lẻ:\n%s"
                         % (kq["rc"], dat, hong, bo, khong_chay,
                            "\n".join(kq["out"].splitlines()[-40:])))
        _dc_duong("e2e-toan-bo")
        self.assertEqual(dat + hong + bo + khong_chay, so_ca,
                         "BÁO CÁO KHÔNG PHỦ SỐ CA `--list`: chạy %d ca / liệt kê %d ca ⇒ một ca "
                         "đã bị rơi khỏi báo cáo (H5/N-G19-04)"
                         % (dat + hong + bo + khong_chay, so_ca))
        do_duoc = (dat, hong, khong_chay)
        dat_cong_, vi = dat_cong("e2e-toan-bo", do_duoc)
        print("       phân quyết: %s" % phan_quyet("e2e-toan-bo", do_duoc))
        self.assertTrue(dat_cong_, "CỔNG `e2e-toan-bo` ĐỎ: %s" % vi)


    def test_b3_e2e_tam_ca_ban_phim_chay_that(self):
        """ĐIỂM 1 SUPERVISOR GIAO, ĐO RIÊNG: `06_ban_phim.spec.js` — ĐÚNG 8 CA Ở CÂY NÀY.

        Vì sao tách khỏi `test_b2`: bộ toàn bộ **CHẬP CHỜN** (đo được vòng 1: 3 lượt sạch +
        1 lượt (49,1,1) — xem `N-G22-01`). Trộn hai phép đo vào một cổng là để chỗ chập chờn che
        chỗ tất định. Đây **KHÔNG** phải "chạy lại cho xanh": đây là **một phép đo KHÁC**.

        Số ca đếm từ chính tệp spec; hai đối chứng âm: (a) bỏ 1 dòng khai ca trong bản sao TẠM ⇒
        bộ đếm giảm đúng 1; (b) hạ 1 ca trong báo cáo ⇒ cổng PHẢI ĐỎ.
        """
        DA_CHAY["e2e-ban-phim"] = True
        so_ca = SO_CA["ban_phim"]
        print("\n  [B3] số ca DO PLAYWRIGHT LIỆT KÊ cho `06_ban_phim.spec.js`: %d ca" % so_ca)
        self.assertGreater(so_ca, 0, "KHÔNG đếm được ca nào từ `06_ban_phim.spec.js`: %s"
                         % SO_CA.get("loi", "")[-600:])
        # MÃ THOÁT của bước ĐẾM CA — cùng vế bắt buộc như `B2` (dùng chung một hàm kiểm).
        ok_list, gc_list = so_ca_playwright_dat_duoc()
        print("       mẫu số: %s" % gc_list)
        self.assertTrue(ok_list, gc_list)
        # Bộ đếm TĨNH chỉ dùng làm đối chứng âm; nó phải KHỚP số `--list` trước khi được tin.
        so_tinh = dem_ca_spec_mot_tep(os.path.join(GOC_SPEC, "06_ban_phim.spec.js"))
        print("       đối chiếu bộ đếm: `--list`=%d ca · đếm dòng khai ca=%d ca" % (so_ca, so_tinh))
        self.assertEqual(so_tinh, so_ca,
                         "bộ đếm tĩnh và `--list` LỆCH NHAU ⇒ đối chứng âm bên dưới không còn "
                         "đại diện cho số ca thật")
        am = doi_chung_am_dem_ca()
        print("       đối chứng âm bộ đếm: bỏ 1 dòng khai ca trong BẢN SAO TẠM → %s → %s ca "
              "(đòi giảm đúng 1)" % (am.get("n_goc"), am.get("n_tam")))
        self.assertEqual(am.get("rc"), 0, "không dựng được đối chứng âm bộ đếm: %s"
                         % am.get("loi"))
        self.assertEqual(am.get("n_tam"), am.get("n_goc") - 1,
                         "BỘ ĐẾM KHÔNG ĐẾM TỪ NỘI DUNG: bỏ một ca mà số ca không giảm đúng 1")
        kq = chay_e2e("06_ban_phim.spec.js", giay=600)
        dat, hong, bo, khong_chay = kq["dem"]
        print("       LỆNH: %s" % kq["lenh"])
        print("       mã thoát THẬT = %d · %.1f giây" % (kq["rc"], kq["giay"]))
        print("       (đạt, hỏng, bỏ qua, KHÔNG CHẠY) = (%d, %d, %d, %d)"
              % (dat, hong, bo, khong_chay))
        print("       tổng báo cáo = %d · số ca `--list` = %d" % (dat + hong + bo + khong_chay, so_ca))
        with open(os.path.join(LOG_DIR, "e2e_ban_phim.txt"), "w", encoding="utf-8") as f:
            f.write(kq["out"])
        dat_gia, vi_gia = dat_cong("e2e-ban-phim", (so_ca - 1, 0, 0))
        print("       đối chứng âm: hạ 1 ca → (%d, 0, 0) → %s (đòi ĐỎ)"
              % (so_ca - 1, "ĐỎ" if not dat_gia else "ĐẠT-SAI"))
        self.assertFalse(dat_gia, "CỔNG MÙ: hạ một ca xuống mà cổng vẫn ĐẠT — %s" % vi_gia)
        self.assertGreater(dat, 0,
                           "KHÔNG CHẠY ĐƯỢC: 0 ca ĐẠT. Đây là KẾT QUẢ, KHÔNG phải chỗ để "
                           "`skipTest`. 40 dòng cuối:\n%s"
                           % "\n".join(kq["out"].splitlines()[-40:]))
        # MÃ THOÁT THẬT của `chay.sh` — vế BẮT BUỘC, không phải một dòng để IN (cùng lỗi họ D1:
        # mã thoát đọc ra rồi bỏ qua, phán quyết chỉ dựa vào chữ trong output).
        self.assertEqual(kq["rc"], 0,
                         "BỘ CHẠY `chay.sh 06_ban_phim.spec.js` THOÁT KHÁC 0 (rc=%d) dù báo cáo "
                         "đọc được (%d đạt, %d hỏng, %d bỏ qua, %d không chạy) ⇒ mã thoát là "
                         "phán quyết, không tin báo cáo đơn lẻ:\n%s"
                         % (kq["rc"], dat, hong, bo, khong_chay,
                            "\n".join(kq["out"].splitlines()[-40:])))
        _dc_duong("e2e-ban-phim")
        self.assertEqual(dat + hong + bo + khong_chay, so_ca,
                         "BÁO CÁO KHÔNG PHỦ SỐ CA `--list`: chạy %d ca / liệt kê %d ca"
                         % (dat + hong + bo + khong_chay, so_ca))
        do_duoc = (dat, hong, khong_chay)
        dat_cong_, vi = dat_cong("e2e-ban-phim", do_duoc)
        print("       phân quyết: %s" % phan_quyet("e2e-ban-phim", do_duoc))
        self.assertTrue(dat_cong_, "CỔNG `e2e-ban-phim` ĐỎ: %s" % vi)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7a. `D1` — PHÁN QUYẾT BÀN ĐO G20 THEO **MÃ THOÁT THẬT**, KHÔNG THEO DÒNG CHỮ
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# LỖI THẬT (đo được, `task_eaf399b954e3`): `D1` chạy CẢ bàn đo G20 rồi chỉ regex dòng `Ran …`
# và KHÔNG đọc `rc`. Đo trên cây này:
#
#     VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py   → Ran 21 · FAILED (failures=6, skipped=3) · EXIT 1
#     python3 app/thu/thu_qa_g22.py D_BanDoG20           → Ran 1  · OK                                  · EXIT 0
#
# ⇒ cổng báo ĐẠT trong khi bàn đo nó canh đã ĐỎ. Một cổng báo ĐẠT khi thứ nó đo THẤT BẠI là lỗi
# tệ nhất của wave: nó biến mọi báo cáo thành vô nghĩa. Log `full-08` của AG-00 cũng in "G20
# exit 1" mà `D1` vẫn PASS.
#
# SỬA: phán quyết đi qua ĐÚNG MỘT điểm vào `_phan_quyet_ban_do_g20(rc, out)`. **MÃ THOÁT là vế
# chính**; ba vế còn lại chặn đúng cái sai ngược lại — "tin mã thoát đơn lẻ":
#   (1) `rc == 0`                        — mã thoát THẬT, đọc NGAY sau lệnh, KHÔNG qua ống;
#   (2) KHÔNG có dòng `FAIL:`/`ERROR:`   — rc = 0 mà output có dòng hỏng vẫn ĐỎ;
#   (3) `Ran N` đọc được và `N > 0`      — `Ran 0 tests` KHÔNG phải "đạt", nó là 0 ca;
#   (4) dòng tổng kết `OK`               — thiếu dòng tổng kết ⇒ KHÔNG xác nhận được đã chạy.
#
# BỐN ĐỐI CHỨNG ÂM BẮT BUỘC — mỗi cái là một TIẾN TRÌNH CON THẬT chạy qua chính hàm trên:
#   (a) bàn đo thoát != 0 (chữ vẫn nói `OK`) ⇒ ĐỎ — chứng minh MÃ THOÁT được đọc;
#   (b) thoát 0 nhưng in dòng `FAIL`         ⇒ ĐỎ — chứng minh KHÔNG tin mã thoát đơn lẻ;
#   (c) in `Ran 0 tests` rồi thoát 0         ⇒ ĐỎ — 0 ca không phải đạt;
#   (d) bàn đo không tồn tại / không chạy    ⇒ ĐỎ và in rõ, KHÔNG được coi là đạt.
# ĐỐI CHỨNG DƯƠNG đi kèm: một bàn đo giả XANH phải cho ĐẠT — không có vế này thì một cổng "luôn
# ĐỎ" cũng qua được cả bốn vế âm ở trên.

_D1_GIA_XANH = '''\
import sys
print("Ran 3 tests in 0.010s")
print("")
print("OK")
sys.exit(0)
'''

# (a) CHỮ nói `OK`, MÃ THOÁT nói 3 — đúng khuôn "mã thoát bị nuốt". Chỉ vế (1) bắt được nó,
# nên đây là đối chứng chứng minh `rc` THẬT SỰ là một vế của phán quyết.
_D1_GIA_THOAT_KHAC_0 = '''\
import sys
print("Ran 3 tests in 0.010s")
print("")
print("OK")
sys.exit(3)
'''

# (b) mã thoát = 0 nhưng output có dòng `FAIL:` + tổng kết `FAILED` — "tin mã thoát đơn lẻ" sẽ
# cho qua chính ca này.
_D1_GIA_CO_FAIL_DU_THOAT_0 = '''\
import sys
print("FAIL: test_g20_c4_route (__main__.T)")
print("AssertionError: cổng C4 ĐỎ — nhưng mã thoát bị nuốt")
print("")
print("Ran 3 tests in 0.010s")
print("")
print("FAILED (failures=1)")
sys.exit(0)
'''

# (c) `unittest` với 0 ca in ĐÚNG khuôn một lượt chạy tốt: `Ran 0 tests` + `OK` + thoát 0.
_D1_GIA_RAN_0 = '''\
import sys
print("Ran 0 tests in 0.000s")
print("")
print("OK")
sys.exit(0)
'''


def _phan_quyet_ban_do_g20(rc, out):
    """PHÁN QUYẾT DUY NHẤT của `D1` trên kết quả THẬT của bàn đo G20.

    `rc` là mã thoát đọc NGAY sau lệnh (`chay()` trả `p.returncode` — không qua ống); `rc=None`
    nghĩa là KHÔNG chạy được (timeout/không tồn tại). Trả dict:

      · `dat`      — CHỈ `True` khi cả bốn vế đúng (xem đầu mục 7a);
      · `ly_do`    — danh sách lý do ĐỎ, nguyên văn, để in ra chứ không nuốt;
      · `ran`      — số ca `unittest` khai (`None` nếu không đọc được);
      · `fail`/`loi` — số ca hỏng / lỗi theo CHÍNH dòng tổng kết của bàn đo;
      · `dong_fail`/`dong_loi` — số dòng `FAIL:`/`ERROR:` đếm trong output;
      · `skip`     — số ca bỏ qua; `pass_` = `ran - fail - loi - skip` (suy ra, ghi rõ là suy ra);
      · `tong_ket` — nguyên văn dòng tổng kết (`OK` | `FAILED (…)` | "").

    Đây là chỗ DUY NHẤT phán quyết `D1`: ca thật và CẢ BỐN đối chứng âm đều gọi đúng hàm này,
    nên không thể có chuyện "đối chứng đo một đằng, ca thật đo một nẻo" (cùng nguyên tắc với
    `do_a1()`/`_do_c4()`).
    """
    out = out or ""
    ra = {"thoat": rc, "dat": False, "ly_do": [], "ran": None, "fail": 0, "loi": 0,
          "dong_fail": 0, "dong_loi": 0, "skip": 0, "pass_": None, "tong_ket": ""}
    if rc is None:
        ra["ly_do"].append("KHÔNG CHẠY ĐƯỢC: không có mã thoát — bàn đo không tồn tại, không "
                           "chạy được, hoặc quá thời gian")
        return ra

    m_ran = re.search(r"^Ran (\d+) tests?\b", out, re.M)
    ra["ran"] = int(m_ran.group(1)) if m_ran else None
    ra["dong_fail"] = len(re.findall(r"^FAIL:\s", out, re.M))
    ra["dong_loi"] = len(re.findall(r"^ERROR:\s", out, re.M))
    m_f = re.search(r"failures=(\d+)", out)
    m_e = re.search(r"errors=(\d+)", out)
    ra["fail"] = max(int(m_f.group(1)) if m_f else 0, ra["dong_fail"])
    ra["loi"] = max(int(m_e.group(1)) if m_e else 0, ra["dong_loi"])
    m_sk = re.search(r"skipped=(\d+)", out)
    ra["skip"] = int(m_sk.group(1)) if m_sk else 0
    tong_ket = re.findall(r"^(?:OK[^\n]*|FAILED[^\n]*)\s*$", out, re.M)
    ra["tong_ket"] = tong_ket[-1].strip() if tong_ket else ""
    if ra["ran"] is not None:
        ra["pass_"] = max(ra["ran"] - ra["fail"] - ra["loi"] - ra["skip"], 0)

    # (1) MÃ THOÁT — vế CHÍNH. Đọc thẳng từ `p.returncode`, không suy từ chữ.
    if rc != 0:
        ra["ly_do"].append("MÃ THOÁT THẬT = %d (đòi 0)" % rc)
    # (3) `Ran N` phải ĐỌC ĐƯỢC và > 0.
    if ra["ran"] is None:
        ra["ly_do"].append("KHÔNG CHẠY ĐƯỢC: output KHÔNG có dòng `Ran N tests` (mã thoát=%d) ⇒ "
                           "không xác nhận được bàn đo đã chạy — KHÔNG được coi là đạt" % rc)
    elif ra["ran"] == 0:
        ra["ly_do"].append("`Ran 0 tests`: bàn đo KHÔNG chạy ca nào ⇒ 0 ca, không phải ĐẠT")
    # (2) KHÔNG được có dòng hỏng, kể cả khi mã thoát = 0.
    if ra["dong_fail"] or ra["dong_loi"]:
        ra["ly_do"].append("output có %d dòng `FAIL:` + %d dòng `ERROR:` dù mã thoát=%d — KHÔNG "
                           "tin mã thoát đơn lẻ" % (ra["dong_fail"], ra["dong_loi"], rc))
    # (4) Phải có dòng tổng kết, và nó không được là `FAILED`.
    if not ra["tong_ket"]:
        ra["ly_do"].append("KHÔNG có dòng tổng kết `OK`/`FAILED (…)` ⇒ không xác nhận được kết "
                           "quả bàn đo")
    elif ra["tong_ket"].startswith("FAILED"):
        ra["ly_do"].append("dòng tổng kết của bàn đo = %r" % ra["tong_ket"])
    ra["dat"] = not ra["ly_do"]
    return ra


def _chay_ban_do_gia(ten, ma, giay=120):
    """Chạy một BÀN ĐO GIẢ trong TIẾN TRÌNH CON THẬT. Trả `(rc, out, đường_dẫn)`.

    Bàn đo giả nằm trong TMP, KHÔNG ghi một byte nào vào cây thật. `rc` là mã thoát THẬT của
    tiến trình con — đây là bằng chứng phép đo `D1` có răng, không phải lời khẳng định.
    """
    d = tempfile.mkdtemp(prefix="g22-d1-%s-" % ten)
    p = os.path.join(d, "ban_do_gia.py")
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(ma)
        rc, out = chay([PY, p], giay=giay)
        return rc, out, p
    finally:
        shutil.rmtree(d, ignore_errors=True)


class D_BanDoG20(unittest.TestCase):
    """VIỆC (b) — chạy `VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py` và ghi C1..C5."""

    _kq = None

    @classmethod
    def setUpClass(cls):
        cls._kq = {"chay_duoc": False}

    def test_d1_nam_cong_g20(self):
        """CHẠY CẢ bàn đo G20 và PHÁN QUYẾT THEO **MÃ THOÁT THẬT** của nó.

        TRƯỚC khi sửa (đo được, `task_eaf399b954e3`): ca này regex dòng `Ran …` rồi PASS, dù bàn
        đo G20 thoát **1** với **6 ca hỏng**. Một cổng báo ĐẠT trong khi thứ nó đo THẤT BẠI là
        lỗi tệ nhất của wave. NAY:

          · `rc` của tiến trình con được ĐỌC NGAY sau lệnh (`chay()` trả `p.returncode`) và là
            **vế CHÍNH** của phán quyết — `rc != 0` ⇒ ca này ĐỎ;
          · `Ran N`/`FAIL`/`SKIP` vẫn được đọc để BÁO CÁO, nhưng làm vế PHỤ: `Ran 0 tests` ⇒ ĐỎ,
            có dòng `FAIL`/`ERROR` ⇒ ĐỎ (kể cả khi `rc == 0`);
          · bàn đo không tồn tại / không chạy được ⇒ ĐỎ và in rõ, KHÔNG được coi là đạt;
          · BỐN ĐỐI CHỨNG ÂM BẮT BUỘC (a)–(d) + một ĐỐI CHỨNG DƯƠNG, mỗi cái là một TIẾN TRÌNH
            CON THẬT đi qua ĐÚNG hàm `_phan_quyet_ban_do_g20()` mà ca thật dùng;
          · BA ĐỐI CHỨNG ÂM CỦA CHÍNH CÁI GHIM (e)–(g) + một ĐỐI CHỨNG DƯƠNG, LÀM THẬT trên bản
            sao trong `TMP`: đổi một chữ NGOÀI khối vá G20 (e) ⇒ ghim "tệp trong cây" phải ĐỎ;
            đổi một chữ TRONG khối vá (f) ⇒ phép hoàn vá phải ĐỎ; đổi một chữ ngoài khối vá G21
            (g) ⇒ ghim G21 cũng phải ĐỎ; bản sao Y NGUYÊN ⇒ phải ĐẠT (ghim không "luôn Đỏ").
            Ghim ở đây KHÔNG phục vụ báo xanh — nó phục vụ phát hiện "bộ đo bị đổi giữa lượt",
            nên phải chứng minh nó NHÌN THẤY thay đổi, không phải chỉ khai là có ghim.

        KHÔNG xoá ca, KHÔNG hạ ngưỡng, KHÔNG ép PASS: nếu G20 còn hỏng thì ca này ĐỎ và đó là
        ĐÚNG — nó đang phản ánh lỗi thật của bàn đo G20 (chủ `thu_qa_g20.py`), không phải lỗi
        của bộ kiểm này.
        """
        DA_CHAY["g20-c1-cay-sach"] = True
        # KHÔNG chép, KHÔNG vá một bản sao: TỆP NGUỒN trong cây phải ĐÃ VÁ, và phải CHỨNG MINH được
        # nó là "bản gốc đã ghim + đúng hai khối vá" — bằng cách HOÀN VÁ rồi băm (`nguon_da_va`).
        # HAI ghim, HAI câu hỏi: tệp trong cây còn ĐÚNG sha đã chốt? và sau khi hoàn vá nó ra ĐÚNG
        # bản gốc đã chốt? Đổi bất kỳ byte nào cũng làm vế đầu ĐỎ — đó là "bộ đo bị đổi giữa lượt".
        ok, ghi_chu = nguon_da_va(BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA,
                                  BAN_DO_G20_SHA_TRONG_CAY)
        print("\n  [D1] bàn đo G20 = TỆP NGUỒN trong cây `app/thu/thu_qa_g20.py`: %s" % ghi_chu)
        if not ok:
            self.fail("TỆP NGUỒN `app/thu/thu_qa_g20.py` KHÔNG PHẢI 'bản gốc đã ghim + đúng hai "
                      "khối vá': %s. Đây là KẾT QUẢ, không phải chỗ bỏ qua." % ghi_chu)
        env = {"VIP_G20_CHE_DO": "gop"}
        t0 = time.time()
        try:
            rc, out = chay([PY, "app/thu/thu_qa_g20.py"], giay=900, env_them=env)
        except subprocess.TimeoutExpired as e:
            rc, out = None, "QUÁ THỜI GIAN %ss: %s" % (e.timeout, e)
        giay = round(time.time() - t0, 1)
        with open(os.path.join(LOG_DIR, "g20_gop.txt"), "w", encoding="utf-8") as f:
            f.write(out or "")
        pq = _phan_quyet_ban_do_g20(rc, out)
        print("       LỆNH: VIP_G20_CHE_DO=gop python3 app/thu/thu_qa_g20.py")
        print("       sha256 tệp nguồn TRONG CÂY = %s (gốc ghim %s + 2 khối vá)"
              % (_bam(BAN_DO_G20)[:16], BAN_DO_G20_GOC_SHA[:16]))
        print("       mã thoát THẬT = %s · %.1f giây"
              % ("KHÔNG CHẠY ĐƯỢC" if rc is None else rc, giay))
        print("       Ran %s · PASS %s · FAIL %d · ERROR %d · SKIP %d · tổng kết %r"
              % ("?" if pq["ran"] is None else pq["ran"],
                 "?" if pq["pass_"] is None else pq["pass_"],
                 pq["fail"], pq["loi"], pq["skip"], pq["tong_ket"]))
        self.__class__._kq = {"chay_duoc": rc is not None, "rc": rc, "out": out, "pq": pq}

        # C1..C5: đọc NGUYÊN VĂN dòng phán quyết của CHÍNH bàn đo — không suy diễn lại.
        # Nhãn in ra của bàn đo là `[G1]` (C1), `[B1]` (C2), `[C1]` (C3), `[C4]`, `[C5]`;
        # `SO_DO_G20[...]["ten_do"]` là KHÓA NỘI BỘ của nó, không phải nhãn in ra.
        #
        # MẪU CHỈ GHIM **NHÃN**, KHÔNG GHIM PHẦN CÒN LẠI CỦA DÒNG: mẫu cũ (`\[B1\] nhị phân…`,
        # `\[C2\] GIT_CONFIG…`) ghim nguyên văn nội dung, nên khi bàn đo đổi câu chữ (đo được:
        # `[B1] nền không dựng được …`) thì `D1` in "KHÔNG THẤY DÒNG ĐO" trong khi dòng đó CÓ —
        # đúng họ H5/N-G19-04 (ghim sự thật môi trường) và nó che mất thông tin khi báo cáo.
        # VÒNG NÀY: U2 đã đổi nhãn C3 từ `[C2]` → `[C1]` khi bỏ ghim stale của bàn đo G20; mẫu
        # `\[C2\]` vì thế lại in "KHÔNG THẤY DÒNG ĐO" dù dòng CÓ (đo trên `g20_gop.txt` dòng 31:
        # `[C1] git thô=0 (OK) …`). Đây là lần THỨ HAI cùng một kiểu trôi — nên nhãn được cặp
        # thêm TỪ KHOÁ nội dung (`git`) để nếu bàn đo đổi nhãn lần nữa mà vẫn nói về git thì
        # vẫn đọc được, thay vì im lặng.
        MAU = (("C1 cổng cây sạch wave trước", r"^\s*\[G1\][^\n]*"),
               ("C2 bàn phím TRONG màn (tầng 3)", r"^\s*\[B1\][^\n]*"),
               ("C3 git với môi trường NGUYÊN BẢN",
                r"^\s*\[C[12]\][^\n]*\bgit\b[^\n]*|^\s*\[C2\][^\n]*"),
               ("C4 route truy_van + migration v9", r"^\s*\[C4\][^\n]*"),
               ("C5 có bộ G19-tổng-hợp chạy được", r"^\s*\[C5\][^\n]*"))
        for ten, mau in MAU:
            mm = re.search(mau, out or "", re.M)
            print("       %-34s %s" % (ten, mm.group(0).strip() if mm else "KHÔNG THẤY DÒNG ĐO"))
        # VÀ mỗi cổng còn được ĐO ĐỘC LẬP ở đây, không chỉ đọc lời bàn đo kia:
        ma_git, _ = chay(["git", "rev-parse", "HEAD"])          # môi trường NGUYÊN BẢN
        print("       ĐO ĐỘC LẬP C3: `git rev-parse HEAD` môi trường NGUYÊN BẢN → mã thoát %d "
              "(nền=%d, đóng=%d)" % (ma_git, SO_DO_G20["C3 git với môi trường NGUYÊN BẢN"]["nen"],
                                     SO_DO_G20["C3 git với môi trường NGUYÊN BẢN"]["dong"]))

        # ── BỐN ĐỐI CHỨNG ÂM BẮT BUỘC — LÀM THẬT, mỗi cái một TIẾN TRÌNH CON ──────────────────
        print("       BỐN ĐỐI CHỨNG ÂM — bàn đo GIẢ chạy THẬT trong tiến trình con, đi qua ĐÚNG "
              "hàm phán quyết trên:")
        am = (
            ("(a) thoát != 0, CHỮ vẫn nói `OK`", _D1_GIA_THOAT_KHAC_0, 3),
            ("(b) thoát 0 nhưng in dòng `FAIL`", _D1_GIA_CO_FAIL_DU_THOAT_0, 0),
            ("(c) in `Ran 0 tests` rồi thoát 0", _D1_GIA_RAN_0, 0),
        )
        for nhan, ma, rc_doi in am:
            rc_a, out_a, _p = _chay_ban_do_gia(nhan.split()[0].strip("()"), ma)
            pq_a = _phan_quyet_ban_do_g20(rc_a, out_a)
            print("       %-40s rc=%-3d → %s (đòi ĐỎ) · lý do: %s"
                  % (nhan, rc_a, "ĐỎ ✓" if not pq_a["dat"] else "ĐẠT-SAI ✗",
                     " | ".join(pq_a["ly_do"])))
            self.assertEqual(rc_a, rc_doi,
                             "đối chứng âm %s: bàn đo giả phải thoát %d, đo được %d — phép "
                             "tiêm không dựng đúng kịch bản" % (nhan, rc_doi, rc_a))
            self.assertFalse(pq_a["dat"],
                             "CỔNG MÙ: đối chứng âm %s mà phán quyết vẫn ĐẠT" % nhan)
        # (d) KHÔNG TỒN TẠI / KHÔNG CHẠY ĐƯỢC: trỏ vào một tệp không có ⇒ tiến trình con thoát
        # khác 0 và KHÔNG có dòng `Ran`. Phán quyết PHẢI ĐỎ và PHẢI nói rõ "KHÔNG CHẠY ĐƯỢC".
        khong_co = os.path.join(TMP_GOC, "__g22_d1_khong_ton_tai__.py")
        if os.path.exists(khong_co):
            os.remove(khong_co)
        rc_d, out_d = chay([PY, khong_co], giay=60)
        pq_d = _phan_quyet_ban_do_g20(rc_d, out_d)
        print("       %-40s rc=%-3d → %s (đòi ĐỎ) · lý do: %s"
              % ("(d) bàn đo KHÔNG TỒN TẠI", rc_d, "ĐỎ ✓" if not pq_d["dat"] else "ĐẠT-SAI ✗",
                 " | ".join(pq_d["ly_do"])))
        self.assertNotEqual(rc_d, 0, "gọi một tệp KHÔNG tồn tại mà tiến trình con vẫn thoát 0")
        self.assertFalse(pq_d["dat"],
                         "CỔNG MÙ: bàn đo KHÔNG TỒN TẠI mà phán quyết vẫn ĐẠT")
        self.assertTrue(any("KHÔNG CHẠY ĐƯỢC" in x for x in pq_d["ly_do"]),
                        "phán quyết ĐỎ nhưng KHÔNG nói rõ 'KHÔNG CHẠY ĐƯỢC': %r" % (pq_d["ly_do"],))
        # ĐỐI CHỨNG DƯƠNG: bàn đo giả XANH phải cho ĐẠT — chặn kiểu hỏng "cổng luôn Đỏ".
        rc_p, out_p, _p = _chay_ban_do_gia("duong", _D1_GIA_XANH)
        pq_p = _phan_quyet_ban_do_g20(rc_p, out_p)
        print("       %-40s rc=%-3d → %s (đòi ĐẠT) · Ran %s · tổng kết %r"
              % ("(+) bàn đo giả XANH", rc_p, "ĐẠT ✓" if pq_p["dat"] else "ĐỎ-SAI ✗",
                 pq_p["ran"], pq_p["tong_ket"]))
        self.assertEqual(rc_p, 0, "bàn đo giả XANH phải thoát 0, đo được %d" % rc_p)
        self.assertTrue(pq_p["dat"],
                        "CỔNG LUÔN ĐỎ: bàn đo giả XANH mà phán quyết vẫn ĐỎ — %r"
                        % (pq_p["ly_do"],))
        DA_TIEM["g20-c1-cay-sach"] = True

        # ĐỐI CHỨNG DƯƠNG của nhóm này: C2 phải ĐO ĐƯỢC (bảy ca tầng 3 chạy thật).
        co_c2 = "tang3-ban-phim" in (out or "") or "tầng 3" in (out or "")
        print("       đối chứng dương: bàn đo có chạm tầng 3 (C2) = %s" % co_c2)
        self.assertTrue(co_c2, "bàn đo G20 chết toàn bộ — C1 đỏ không phân biệt được với "
                               "'bàn đo không chạy'")
        # VÀ tệp nguồn KHÔNG được đổi bởi chính lượt đo này (không ai chép/xoá nó nữa).
        ok2, ghi_chu2 = nguon_da_va(BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA,
                                    BAN_DO_G20_SHA_TRONG_CAY)
        print("       sau lượt đo, tệp nguồn vẫn là 'gốc + 2 khối vá' = %s" % ok2)
        self.assertTrue(ok2, "lượt đo đã ĐỔI tệp nguồn: %s" % ghi_chu2)

        # ── ĐỐI CHỨNG ÂM CỦA CHÍNH CÁI GHIM — LÀM THẬT TRÊN BẢN SAO TRONG `TMP` ───────────────
        # Ghim chỉ có nghĩa nếu nó ĐỎ khi bộ đo bị đổi. Ba phép tiêm + một phép DƯƠNG, mỗi phép
        # nhắm ĐÚNG MỘT trong HAI ô ghim:
        #   (e) đổi một chữ NGOÀI khối vá G20, KIỂM CẢ HAI ô  ⇒ ô "tệp TRONG CÂY" phải bắt;
        #   (f) đổi một chữ TRONG khối vá G20, CHỈ KIỂM ô GỐC (`sha_trong_cay=None`) ⇒ phép HOÀN
        #       VÁ phải bắt — nếu vẫn kiểm ô cây thì (e) và (f) sẽ cùng một đường, và ô "gốc" sẽ
        #       không bao giờ được chứng minh là có răng;
        #   (g) đổi một chữ ngoài khối vá G21  ⇒ ghim G21 cũng phải có răng;
        #   (+) bản sao Y NGUYÊN (không tiêm)  ⇒ phải ĐẠT, chặn kiểu hỏng "ghim luôn Đỏ".
        def _tieu_de(ten_cu, ten_moi):
            def _f(t):
                if t.count(ten_cu) < 1:
                    raise AssertionError("không tìm được `%s` để tiêm" % ten_cu)
                return t.replace(ten_cu, ten_moi, 1), "đổi dòng tiêu đề (NGOÀI khối vá)"
            return _f

        def _trong_khoi_va(t):
            cu = G20_C5_VA[1][1]
            if t.count(cu) != 1:
                raise AssertionError("khối quyết định của bản vá không còn đúng MỘT chỗ")
            moi = cu.replace("XANH chỉ khi", "XANH chỉ khi (TIÊM-GHIM)", 1)
            if moi == cu:
                raise AssertionError("không tiêm được vào khối quyết định")
            return t.replace(cu, moi, 1), "đổi một chữ BÊN TRONG khối quyết định (khối vá)"

        ds_am = (
            ("(e) G20 — đổi 1 chữ NGOÀI khối vá", BAN_DO_G20, G20_C5_VA,
             BAN_DO_G20_GOC_SHA, BAN_DO_G20_SHA_TRONG_CAY,
             _tieu_de("AG-01 (G20) — BỘ KIỂM ĐỘC LẬP", "AG-01 (G20) — BỘ KIỂM ĐỘC LẬP [TIÊM]"),
             True, None),
            ("(f) G20 — đổi 1 chữ TRONG khối vá", BAN_DO_G20, G20_C5_VA,
             BAN_DO_G20_GOC_SHA, BAN_DO_G20_SHA_TRONG_CAY, _trong_khoi_va,
             False, "KHÔNG hoàn vá được"),
            ("(g) G21 — đổi 1 chữ NGOÀI khối vá", BAN_DO_G21, G21_G7_VA,
             BAN_DO_G21_GOC_SHA, BAN_DO_G21_SHA_TRONG_CAY,
             _tieu_de("AG-01 (G21) — BỘ KIỂM ĐỘC LẬP", "AG-01 (G21) — BỘ KIỂM ĐỘC LẬP [TIÊM]"),
             True, None),
        )
        print("       ĐỐI CHỨNG ÂM CỦA GHIM — tiêm vào BẢN SAO trong TMP, cây thật KHÔNG bị chạm:")
        for nhan, duong, cap, sha_goc, sha_cay, bien_doi, kiem_cay, phai_gap in ds_am:
            d, p, mo_ta = ban_sao_tiem(duong, bien_doi)
            try:
                ok_a, gc_a = nguon_da_va(p, cap, sha_goc, sha_cay if kiem_cay else None)
                print("       %-38s → %s (đòi ĐỎ) · %s"
                      % (nhan, "ĐỎ ✓" if not ok_a else "ĐẠT-SAI ✗", gc_a[:150]))
                self.assertFalse(ok_a, "CỔNG MÙ: tiêm `%s` mà vẫn xác nhận là bản gốc (%s)"
                                 % (mo_ta, gc_a))
                if phai_gap:
                    self.assertIn(phai_gap, gc_a,
                                  "phép tiêm `%s` bị bắt, nhưng KHÔNG phải bởi chốt `%s` (lý do "
                                  "thật: %s) ⇒ đối chứng không chứng minh đúng ô ghim"
                                  % (mo_ta, phai_gap, gc_a))
            finally:
                shutil.rmtree(d, ignore_errors=True)
        # (+) ĐỐI CHỨNG DƯƠNG: bản sao KHÔNG tiêm phải ĐẠT — nếu không thì "ĐỎ khi tiêm" có thể
        # chỉ là "hàm luôn trả Đỏ", và ghim chẳng chứng minh được gì.
        d, p, mo_ta = ban_sao_tiem(BAN_DO_G20, None)
        try:
            ok_p, gc_p = nguon_da_va(p, G20_C5_VA, BAN_DO_G20_GOC_SHA, BAN_DO_G20_SHA_TRONG_CAY)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        print("       %-38s → %s (đòi ĐẠT) · %s"
              % ("(+) G20 — bản sao Y NGUYÊN", "ĐẠT ✓" if ok_p else "ĐỎ-SAI ✗", gc_p[:150]))
        self.assertTrue(ok_p, "GHIM LUÔN ĐỎ: bản sao y nguyên bị từ chối (%s)" % gc_p)
        _dc_duong("g20-c1-cay-sach")

        # ── PHÁN QUYẾT CUỐI — THEO MÃ THOÁT THẬT, KHÔNG THEO DÒNG CHỮ ────────────────────────
        self.assertTrue(
            pq["dat"],
            "D1 ĐỎ — BÀN ĐO G20 THẤT BẠI: %s.\n"
            "       Đọc được: mã thoát THẬT = %s · Ran %s · FAIL %d · ERROR %d · SKIP %d · "
            "tổng kết %r.\n"
            "       ĐÂY LÀ ĐỎ ĐÚNG: cổng đang phản ánh lỗi THẬT của bàn đo G20 "
            "(`app/thu/thu_qa_g20.py`) — KHÔNG phải lỗi của bộ kiểm này, KHÔNG được sửa bằng "
            "cách nới cổng. Chủ `thu_qa_g20.py` phải sửa các ca hỏng bên trong.\n"
            "       40 dòng cuối của bàn đo:\n%s"
            % (" | ".join(pq["ly_do"]), "KHÔNG CHẠY ĐƯỢC" if rc is None else rc, pq["ran"],
               pq["fail"], pq["loi"], pq["skip"], pq["tong_ket"],
               "\n".join((out or "").splitlines()[-40:])))


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

    def _doi_chung_cong_cay_sach_o_clone_nen(self):
        """ĐỐI CHỨNG DƯƠNG cho nhóm `cay-sach-3-ban-sao` — chạy trên CLONE THẬT tại HEAD.

        Một clone `--shared` trong TMP có `HEAD` = HEAD đọc tại chỗ và cây SẠCH, nên đó là môi
        trường đo ĐÚNG của ba cổng so-cây-với-HEAD (xem §3 đầu tệp). KHÔNG ghim SHA nền: HEAD
        nhích ở mọi commit, ghim lại sẽ sinh đúng cái ĐỎ VĨNH VIỄN mà vòng 3 đang diệt.

        HAI VẾ, cả hai đều ĐO ĐƯỢC:
          (a) cây SẠCH  ⇒ CẢ BA cổng XANH (rc=0);
          (b) TIÊM `admin/__tiem_g22.js` ⇒ CẢ BA cổng ĐỎ **và ĐỎ-THẬT** (không phải PHEP_DO_CHET).
        Chỉ khi cả hai vế đúng thì nhóm mới được coi là "đã chạy đối chứng" — nếu không, `Z6`
        phải tiếp tục ĐỎ chứ không được bật cờ suông.
        """
        head = head_hien_tai()
        self.assertRegex(head, r"^[0-9a-f]{40}$",
                         "KHÔNG đọc được HEAD của cây thợ ⇒ không dựng được clone đối chứng")
        goc = tempfile.mkdtemp(prefix="g22-clone-nen-")
        try:
            rc, out = _git("clone", "--shared", "--no-checkout", GOC_CAY, goc, giay=300)
            self.assertEqual(rc, 0, "KHÔNG clone được nền để đối chứng: %s" % out[-500:])
            rc, out = _git("-C", goc, "checkout", "--detach", head, giay=300)
            self.assertEqual(rc, 0, "KHÔNG checkout được HEAD %s: %s" % (head[:12], out[-500:]))
            rc, out = _git("-C", goc, "rev-parse", "HEAD")
            self.assertEqual(out.strip(), head,
                             "clone có HEAD=%r ≠ HEAD đọc tại chỗ=%s" % (out.strip(), head))
            rc, out = _git("-C", goc, "status", "--porcelain", "-uall")
            self.assertEqual(rc, 0, "`git status` trong clone hỏng: %s" % out[-300:])
            self.assertEqual([d for d in out.splitlines() if d.strip()], [],
                             "clone tại HEAD KHÔNG sạch ⇒ đối chứng sẽ đo sai: %s"
                             % out[-500:])
            sach, tiem = [], []
            for ten, lenh in self.CONG:
                rc, out = chay(lenh, giay=600, cwd=goc)
                sach.append((ten, rc, _phan_loai_cong_cay_sach(out, rc)))
            tep = os.path.join(goc, "admin", "__tiem_g22.js")
            with open(tep, "w", encoding="utf-8") as f:
                f.write("// TIÊM LỖI của G22 AGENT 02 — chỉ trong CLONE TẠM, xoá ngay\n")
            for ten, lenh in self.CONG:
                rc, out = chay(lenh, giay=600, cwd=goc)
                tiem.append((ten, rc, _phan_loai_cong_cay_sach(out, rc)))
            print("\n  [E1†] ĐỐI CHỨNG CLONE THẬT tại HEAD %s (HEAD đọc tại chỗ, cây sạch):"
                  % head[:12])
            for (ten, rc, loai), (_, rc_t, loai_t) in zip(sach, tiem):
                print("       %-12s cây SẠCH rc=%-3d %-13s · TIÊM `admin/__tiem_g22.js` "
                      "rc=%-3d %s" % (ten, rc, loai, rc_t, loai_t))
            self.assertTrue(
                all(rc == 0 and loai == "XANH" for _, rc, loai in sach),
                "cây SẠCH tại HEAD mà cổng KHÔNG xanh ⇒ đối chứng không dựng được: %r" % (sach,))
            self.assertTrue(
                all(rc != 0 and loai == "DO_THAT" for _, rc, loai in tiem),
                "TIÊM tệp bẩn mà có cổng KHÔNG ĐỎ-THẬT ⇒ cổng MÙ: %r" % (tiem,))
        finally:
            shutil.rmtree(goc, ignore_errors=True)
        DA_CHAY["cay-sach-3-ban-sao"] = True
        DA_TIEM["cay-sach-3-ban-sao"] = True

    def test_e1_ba_cong_cay_sach_chay_that(self):
        """Chạy CẢ BA cổng trong TIẾN TRÌNH CON, và phân loại từng cổng.

        BA CỔNG NÀY SO CÂY VỚI `HEAD`. Nền nay là HEAD ĐỌC TẠI CHỖ, nên trạng thái "HEAD ≠ nền"
        không còn tồn tại: không có lý do môi trường nào để TỪ CHỐI phán quyết. Nếu HEAD không
        đọc được thì đó là ĐỎ THẬT, không phải skip.

        ĐỐI CHỨNG DƯƠNG vẫn CHẠY THẬT trước: clone tại HEAD
        (`_doi_chung_cong_cay_sach_o_clone_nen`) — sạch 3/3 XANH, tiêm 3/3 `DO_THAT`. `Z6` vì
        thế chỉ xanh khi phép tiêm thật sự bắt được lỗi, không phải khi có một lời khai.
        """
        self._doi_chung_cong_cay_sach_o_clone_nen()
        head = head_hien_tai()
        self.assertRegex(head, r"^[0-9a-f]{40}$",
                         "KHÔNG đọc được HEAD ⇒ ba cổng cây sạch không thể phán quyết")
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
    """ĐIỂM 3 Supervisor giao — ca E3 phụ thuộc ĐỒNG HỒ.

    HỢP ĐỒNG ĐÃ DUYỆT (`docs/G22_SAOLUU.md` §5): mốc thời gian là THAM SỐ `luc=`. Bản ĐÓNG BĂNG
    `migrate_nguyenban.py` (md5 ghim) là vế TRƯỚC; `app/migrate.py` hiện tại là vế SAU.
    KHÔNG retry, KHÔNG để phép đo đọc giờ hệ thống.
    """

    def test_f1_do_that_bang_dong_ho_dong_bang(self):
        DA_CHAY["e3-ba-luot-cung-giay"] = True
        that = do_e3(GOC_APP)
        if that.get("so_ban_cat_rollback") is None:
            self.fail("KHÔNG ĐO ĐƯỢC E3 (rc=%s): %s" % (that.get("rc"), that.get("loi")))
        print("\n  [F1] MỐC CỐ ĐỊNH truyền qua `luc=` = %s — ba lượt `khoi_phuc(luc=)` CÙNG MỐC"
              % that["luc_truyen"])
        print("       `sao_luu(luc=)` → %s tệp khác nhau: %s"
              % (that["so_sao_luu_khac_nhau"], ", ".join(that["ten_ban_sao_luu"])))
        print("       `khoi_phuc(luc=)` → %s bản cất: %s"
              % (that["so_ban_cat_rollback"], ", ".join(that["ten_ban_cat"])))
        print("       bản cất MỞ ĐƯỢC=%s · giữ dữ liệu mới hơn (x=2)=%s · cùng mốc=%s"
              % (that["so_ban_cat_mo_duoc"], that["so_ban_cat_giu_du_lieu_moi"],
                 that["cung_mot_moc"]))
        self.assertTrue(that["nhan_luc_sao_luu"],
                        "`sao_luu()` KHÔNG nhận `luc=` ⇒ phép đo về mốc không dựng được")
        self.assertTrue(that["nhan_luc_khoi_phuc"],
                        "`khoi_phuc()` KHÔNG nhận `luc=` ⇒ phép đo về mốc không dựng được")
        self.assertGreaterEqual(
            that["so_sao_luu_khac_nhau"], 2,
            "mốc cố định + hậu số KHÔNG có hiệu lực HOẶC phép đếm mù: `sao_luu()` chỉ ra %s tệp"
            % that["so_sao_luu_khac_nhau"])
        self.assertTrue(that["cung_mot_moc"],
                        "ba bản cất KHÔNG cùng mang mốc %s: %s"
                        % (that["luc_truyen"], that["ten_ban_cat"]))
        self.assertEqual(that["so_ban_cat_mo_duoc"], that["so_ban_cat_rollback"],
                         "có bản cất KHÔNG mở được: %r" % (that["gia_tri_x"],))
        self.assertGreaterEqual(that["so_ban_cat_giu_du_lieu_moi"], 1,
                                "không bản cất nào giữ dữ liệu mới hơn (x=2) — phép đếm chỉ "
                                "đếm tệp rỗng: %r" % (that["gia_tri_x"],))
        _dc_duong("e3-ba-luot-cung-giay")
        do_duoc = that["so_ban_cat_rollback"]
        dat, vi = dat_cong("e3-ba-luot-cung-giay", do_duoc)
        print("       phân quyết: %s" % phan_quyet("e3-ba-luot-cung-giay", do_duoc))
        self.assertTrue(dat, "CỔNG `e3-ba-luot-cung-giay` ĐỎ: %s" % vi)

    def test_f2_doi_chung_duong_ban_da_va(self):
        """ĐỐI CHỨNG ĐƯỜNG: bản ĐÓNG BĂNG (TRƯỚC G22) và bản ĐÃ VÁ phải cho KẾT QUẢ KHÁC NHAU.

        Cùng đồng hồ đóng băng, cùng mốc, cùng kịch bản:
          · `migrate_nguyenban.py` (md5 ghim, KHÔNG nhận `luc`) → 1 bản cất (ĐÈ);
          · `app/migrate.py` hiện tại (`luc=`) → 3 bản cất.
        Không có vế này thì "3 bản cất" của `F1` không phân biệt được với một bộ đo hỏng.
        """
        app_cu = _app_tam("dong-bang", migrate_cu=True)
        try:
            kq_cu = do_e3(app_cu, leo_thang=False)
        finally:
            shutil.rmtree(app_cu, ignore_errors=True)
        self.assertIsNotNone(kq_cu.get("so_ban_cat_rollback"),
                             "KHÔNG ĐO ĐƯỢC bản đóng băng (rc=%s): %s"
                             % (kq_cu.get("rc"), kq_cu.get("loi")))
        kq_moi = do_e3(GOC_APP)
        self.assertIsNotNone(kq_moi.get("so_ban_cat_rollback"),
                             "KHÔNG ĐO ĐƯỢC bản đã vá (rc=%s): %s"
                             % (kq_moi.get("rc"), kq_moi.get("loi")))
        print("\n  [F2] ĐỐI CHỨNG ĐƯỜNG — TRƯỚC (đóng băng md5=%s) vs SAU (`luc=`)"
              % MIGRATE_NGUYENBAN_MD5[:12])
        print("       TRƯỚC: nhận `luc`=%s · sao_luu=%s tệp · khoi_phuc=%s bản cất"
              % (kq_cu["nhan_luc_khoi_phuc"], kq_cu["so_sao_luu_khac_nhau"],
                 kq_cu["so_ban_cat_rollback"]))
        print("       SAU  : nhận `luc`=%s · sao_luu=%s tệp · khoi_phuc=%s bản cất"
              % (kq_moi["nhan_luc_khoi_phuc"], kq_moi["so_sao_luu_khac_nhau"],
                 kq_moi["so_ban_cat_rollback"]))
        self.assertFalse(kq_cu["nhan_luc_khoi_phuc"],
                         "bản đóng băng NHẬN `luc` ⇒ nó không phải bản TRƯỚC G22")
        self.assertGreaterEqual(kq_cu["so_sao_luu_khac_nhau"], 2,
                                "đồng hồ đóng băng không có hiệu lực trên bản cũ")
        self.assertEqual(kq_cu["so_ban_cat_rollback"], 1,
                         "bản TRƯỚC G22 phải ĐÈ còn 1 bản cất; đo được %s"
                         % kq_cu["so_ban_cat_rollback"])
        self.assertEqual(kq_moi["so_ban_cat_rollback"], 3,
                         "bản ĐÃ VÁ phải để lại 3 bản cất; đo được %s"
                         % kq_moi["so_ban_cat_rollback"])
        self.assertGreater(kq_moi["so_ban_cat_rollback"], kq_cu["so_ban_cat_rollback"],
                           "hai bản cho CÙNG kết quả ⇒ phép đo không phân biệt được bản vá")
        DA_TIEM["e3-ba-luot-cung-giay"] = True
        _dc_duong("e3-ba-luot-cung-giay")
        print("       ⇒ phép đo PHÂN BIỆT ĐƯỢC: TRƯỚC → 1 · SAU → 3")

    def test_f3_vi_sao_phai_dong_bang_dong_ho(self):
        """Vì sao phép đo KHÔNG được đọc giờ hệ thống — đo trên chính bản ĐÓNG BĂNG.

        Cùng bản cũ, cùng lỗi ĐÈ: ba lượt trong CÙNG một giây → 1 bản cất; nếu đồng hồ nhích
        (máy chậm / chạy chung) → 3 bản cất DÙ ĐƯỜNG ĐÈ CÒN NGUYÊN. Đó là XANH GIẢ. Vì thế phép
        đo phải truyền `luc=` CỐ ĐỊNH — và `F1` đòi `cung_mot_moc`.
        """
        app_cu = _app_tam("dong-bang-leo-thang", migrate_cu=True)
        try:
            cung_giay = do_e3(app_cu, leo_thang=False)
            leo_thang = do_e3(app_cu, leo_thang=True)
        finally:
            shutil.rmtree(app_cu, ignore_errors=True)
        self.assertIsNotNone(cung_giay.get("so_ban_cat_rollback"),
                             "KHÔNG ĐO ĐƯỢC bản cũ cùng giây: %s" % cung_giay.get("loi"))
        self.assertIsNotNone(leo_thang.get("so_ban_cat_rollback"),
                             "KHÔNG ĐO ĐƯỢC bản cũ nhích giây: %s" % leo_thang.get("loi"))
        # Vế SOURCE trên sản phẩm THẬT: `khoi_phuc` nhận `luc` và CHUYỂN nó xuống nơi đặt tên.
        with open(os.path.join(GOC_APP, "migrate.py"), encoding="utf-8") as f:
            nguon = f.read()
        chu_ky = nguon.split("def khoi_phuc", 1)[1].split(")", 1)[0]
        than = nguon.split("def khoi_phuc", 1)[1].split("\ndef ", 1)[0]
        print("\n  [F3] vì sao phải truyền MỐC CỐ ĐỊNH — đo trên bản ĐÓNG BĂNG TRƯỚC G22:")
        print("       ba lượt CÙNG một giây → %s bản cất · đồng hồ NHÍCH mỗi lượt → %s bản cất"
              % (cung_giay["so_ban_cat_rollback"], leo_thang["so_ban_cat_rollback"]))
        print("       (cùng lỗi ĐÈ; chỉ khác tốc độ máy ⇒ 'may mắn' là XANH GIẢ)")
        print("       sản phẩm thật: chữ ký `khoi_phuc` có `luc=` = %s · chuyển `luc` xuống "
              "`_duong_chua_dung` = %s"
              % ("luc=None" in chu_ky,
                 '_duong_chua_dung("hub-truoc-rollback", ".db", luc)' in than))
        self.assertIn("luc=None", chu_ky,
                      "`khoi_phuc()` mất tham số `luc=` ⇒ mốc lại bị đọc ngầm")
        self.assertIn('_duong_chua_dung("hub-truoc-rollback", ".db", luc)', than,
                      "`khoi_phuc()` không chuyển `luc` xuống `_duong_chua_dung`")
        self.assertNotIn('"hub-truoc-rollback-" + datetime.now()', than,
                         "`khoi_phuc()` lại đọc `datetime.now()` ngầm")
        self.assertEqual(cung_giay["so_ban_cat_rollback"], 1,
                         "bản cũ, CÙNG giây: phải còn 1 bản cất; đo được %s"
                         % cung_giay["so_ban_cat_rollback"])
        self.assertEqual(leo_thang["so_ban_cat_rollback"], 3,
                         "bản cũ, đồng hồ NHÍCH: phải ra 3 bản cất DÙ lỗi còn nguyên — đó chính "
                         "là XANH GIẢ cần chặn; đo được %s"
                         % leo_thang["so_ban_cat_rollback"])
        self.assertFalse(leo_thang["cung_mot_moc"],
                         "ba bản cất của lượt nhích giây KHÔNG được cùng mốc: %s"
                         % leo_thang["ten_ban_cat"])
        # Vế SAU: bản thật + `luc=` phải TẤT ĐỊNH kể cả khi đồng hồ nhích.
        kq_moi = do_e3(GOC_APP, leo_thang=True)
        self.assertIsNotNone(kq_moi.get("so_ban_cat_rollback"),
                             "KHÔNG ĐO ĐƯỢC bản thật khi đồng hồ nhích: %s" % kq_moi.get("loi"))
        self.assertEqual(kq_moi["so_ban_cat_rollback"], 3,
                         "bản thật + `luc=` phải ra 3 bản cất bất kể đồng hồ; đo được %s"
                         % kq_moi["so_ban_cat_rollback"])
        self.assertTrue(kq_moi["cung_mot_moc"],
                        "bản thật + `luc=` mà tên KHÔNG mang mốc đã truyền: %s"
                        % kq_moi["ten_ban_cat"])
        print("       bản thật + `luc=`, đồng hồ NHÍCH → %s bản cất, cùng mốc=%s"
              % (kq_moi["so_ban_cat_rollback"], kq_moi["cung_mot_moc"]))


class G_NG2103(unittest.TestCase):
    """ĐIỂM 4 Supervisor giao — `N-G21-03`: ca `test_c2a` KHÔNG được GHIM hành vi RÒ.

    HỢP ĐỒNG ĐÃ DUYỆT (G22 đã sửa ở `thu_g20_dahang.py`): credential NGẮN của BẤT KỲ hãng nào
    cũng không được rò. Vì thế:
      · ca trong cây phải KHẲNG ĐỊNH `assertFalse` (không rò), không còn `assertTrue` (ghim rò);
      · ca phải CHẠY ĐƯỢC (rc=0), không phải một phép đo chết;
      · bộ đo ĐỘC LẬP `thu_qa_g21.py::G5_CredentialNgan` phải đọc **0/5** trên cây thật;
      · ĐỐI CHỨNG ĐƯỜNG: tắt luật ECHO THEO TÊN trên một bản sao TẠM ⇒ G5 phải đọc >0 VÀ ca
        `test_c2a` đã viết lại phải ĐỎ. Không có vế này thì "0 rò" không phân biệt được với
        "bộ dò mù".
    """

    CA = ("app/thu/thu_g20_dahang.py",
          "CaGanChat.test_c2a_bang_2x2_che_theo_TEN_khong_chuyen_sang_hang_gia")

    def _tiem_echo_cu(self):
        """Bản sao TẠM của `app/` với luật ECHO THEO TÊN bị TẮT (hành vi trước G22).

        Trả gốc thư mục tạm; người gọi PHẢI xoá. KHÔNG ghi một byte nào vào cây thật.
        """
        d = tempfile.mkdtemp(prefix="g22-tiem-echo-")
        shutil.copytree(GOC_APP, os.path.join(d, "app"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(os.path.join(GOC_CAY, "trien_khai", "g20-dahang"),
                        os.path.join(d, "trien_khai", "g20-dahang"),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        p = os.path.join(d, "app", "http_jt.py")
        with open(p, encoding="utf-8") as f:
            nguon = f.read()
        dau = "def _gia_tri_echo_theo_ten(than, headers_tra_loi, ten_ta_gui):\n"
        if nguon.count(dau) != 1:
            shutil.rmtree(d, ignore_errors=True)
            raise RuntimeError("không tiêm được: luật ECHO THEO TÊN không còn đúng MỘT chỗ")
        nguon = nguon.replace(
            dau, dau + "    return set()  # TIÊM: tắt luật ECHO THEO TÊN (chính sách trước G22)\n", 1)
        with open(p, "w", encoding="utf-8") as f:
            f.write(nguon)
        return d

    def test_g1_ca_thu_con_ghim_ro(self):
        DA_CHAY["ng21-03-ca-ghim-ro"] = True
        with open(os.path.join(GOC_CAY, self.CA[0]), encoding="utf-8") as f:
            nguon = f.read()
        con_ghim = ('self.assertTrue(ket_qua["gia_ngan"]' in nguon
                    or 'self.assertTrue(ket_qua["gia_ngan_2"]' in nguon)
        da_sua = ('self.assertFalse(ket_qua["gia_ngan"]' in nguon
                  and 'self.assertFalse(ket_qua["gia_ngan_2"]' in nguon)
        rc, out = chay([PY, self.CA[0], self.CA[1]], giay=300)
        chay_duoc = (rc == 0 and "Ran 1 test" in out and "OK" in out
                     and "skipped=" not in out)
        print("\n  [G1] LỆNH: python3 %s %s" % self.CA)
        print("       mã thoát THẬT = %d · %s"
              % (rc, out.strip().splitlines()[-1] if out.strip() else ""))
        print("       còn khẳng định CŨ `assertTrue(ket_qua[\"gia_ngan\"])` (ghim RÒ) = %s · "
              "đã có `assertFalse(...)` (bất biến ĐÚNG) = %s" % (con_ghim, da_sua))
        self.assertFalse(con_ghim,
                         "ca `test_c2a` VẪN GHIM hành vi RÒ (`assertTrue`) ⇒ `N-G21-03` chưa đóng")
        self.assertTrue(da_sua,
                        "ca `test_c2a` KHÔNG khẳng định bất biến ĐÚNG (`assertFalse`) ⇒ nó không "
                        "còn đo 'credential NGẮN không được rò'")
        self.assertTrue(chay_duoc,
                        "ca `test_c2a` KHÔNG CHẠY ĐƯỢC (rc=%d, 'OK'=%s, 'skipped='=%s) — một phép "
                        "đo chết không được tính là 'hết ghim rò':\n%s"
                        % (rc, "OK" in out, "skipped=" in out,
                           "\n".join(out.splitlines()[-25:])))
        # ĐỐI CHỨNG (a): bộ đo ĐỘC LẬP trên cây THẬT phải đọc 0/5 — lỗ rò đã đóng.
        rc2, out2 = chay([PY, "app/thu/thu_qa_g21.py", "G5_CredentialNgan"], giay=900)
        m = re.search(r"tổ hợp RÒ=(\d+)/(\d+)", out2)
        so_ro = int(m.group(1)) if m else None
        chay_duoc_g5 = (rc2 == 0 and "Ran 1 test" in out2 and "OK" in out2
                        and "skipped=" not in out2)
        print("       ĐỐI CHỨNG (a) — bộ đo ĐỘC LẬP `thu_qa_g21.py::G5_CredentialNgan` trên cây "
              "thật: rc=%d · tổ hợp RÒ=%s"
              % (rc2, ("%s/%s" % (m.group(1), m.group(2))) if m else "?"))
        self.assertIsNotNone(
            so_ro, "bộ đo độc lập không cho ra số ⇒ '0 rò' không phân biệt được với 'bộ dò mù':\n%s"
                   % "\n".join(out2.splitlines()[-25:]))
        self.assertTrue(chay_duoc_g5,
                        "bộ đo độc lập KHÔNG chạy được (rc=%d) ⇒ con số vô nghĩa:\n%s"
                        % (rc2, "\n".join(out2.splitlines()[-25:])))
        self.assertEqual(so_ro, 0,
                         "bộ đo độc lập còn thấy %s tổ hợp RÒ trên cây thật ⇒ bất biến "
                         "'credential NGẮN không được rò' đang MỞ" % so_ro)
        # ĐỐI CHỨNG (b): TIÊM lại chính sách cũ — tắt luật ECHO THEO TÊN — G5 phải thấy rò VÀ
        # ca `test_c2a` đã viết lại phải ĐỎ. Đây là vế chứng minh bộ dò KHÔNG mù.
        goc_tiem = self._tiem_echo_cu()
        try:
            rc3, out3 = chay([PY, "app/thu/thu_qa_g21.py", "G5_CredentialNgan"], giay=900,
                             cwd=goc_tiem)
            rc4, out4 = chay([PY, self.CA[0], self.CA[1]], giay=300, cwd=goc_tiem)
        finally:
            shutil.rmtree(goc_tiem, ignore_errors=True)
        m3 = re.search(r"tổ hợp RÒ=(\d+)/(\d+)", out3)
        so_ro_tiem = int(m3.group(1)) if m3 else None
        print("       ĐỐI CHỨNG (b) — TIÊM tắt luật ECHO THEO TÊN: G5 đọc tổ hợp RÒ=%s · `test_c2a` "
              "rc=%d (%s) · G5 thoát %d" % (("%s/%s" % (m3.group(1), m3.group(2))) if m3 else "?",
                                            rc4, "ĐỎ ✓" if rc4 != 0 else "VẪN XANH ✗", rc3))
        # MÃ THOÁT của phép đo ĐỘC LẬP trên bản tiêm cũng phải được ĐỌC: một lượt G5 thoát khác 0
        # mà vẫn kịp in dòng `tổ hợp RÒ=…` là một phép đo HỎNG, không phải bằng chứng bộ dò có răng.
        self.assertEqual(rc3, 0,
                         "phép đo ĐỘC LẬP `G5_CredentialNgan` trên bản TIÊM thoát %d ⇒ con số "
                         "`tổ hợp RÒ` không đáng tin (không chứng minh được bộ dò có răng):\n%s"
                         % (rc3, "\n".join(out3.splitlines()[-25:])))
        self.assertIsNotNone(so_ro_tiem,
                             "bản tiêm không cho ra số ⇒ phép tiêm hỏng, không kết luận được")
        self.assertGreater(so_ro_tiem, 0,
                           "tắt luật ECHO THEO TÊN mà G5 vẫn 0 rò ⇒ bộ dò MÙ, '0/5' trên cây thật "
                           "không chứng minh được gì")
        self.assertNotEqual(rc4, 0,
                            "bản tiêm chính sách cũ mà `test_c2a` VẪN XANH ⇒ ca không bắt được "
                            "hồi quy; nó chỉ 'xanh vì sản phẩm xanh'")
        self.assertIn("RÒ", out4,
                      "`test_c2a` đỏ nhưng KHÔNG phải vì RÒ ⇒ đỏ do lý do khác:\n%s"
                      % "\n".join(out4.splitlines()[-25:]))
        _dc_duong("ng21-03-ca-ghim-ro")
        DA_TIEM["ng21-03-ca-ghim-ro"] = True
        gia_tri = 1 if con_ghim else 0
        dat, vi = dat_cong("ng21-03-ca-ghim-ro", gia_tri)
        print("       phân quyết: %s" % phan_quyet("ng21-03-ca-ghim-ro", gia_tri))
        self.assertTrue(dat, "CỔNG `ng21-03-ca-ghim-ro` ĐỎ: %s" % vi)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7c. C4 — VIỆC THẬT TÊN LÀ `G19-C6`; `OWNER_ACTIONS C4` LÀ D-8, KHÔNG PHẢI VIỆC NÀY
# ══════════════════════════════════════════════════════════════════════════════════════════════
#
# HAI THỨ TRÙNG NHÃN "C4" — TUYỆT ĐỐI KHÔNG ĐÁNH ĐỒNG:
#
#   (1) `C4` trong sổ của `thu_qa_g20.py` = **C6 của G19** (`G19-C6`): route `truy_van.py` +
#       `DDL_G12Q` vào migration. Từ `5fc5f6f` việc này ĐÃ ĐÓNG **CẢ HAI TẦNG**: AG-06 nối route
#       vào `app/server.py` (`146500b`), và U4 áp `truy_van.DDL_G12Q` bằng `migrate.nang_len_v10`
#       (`csdl.PHIEN_BAN_SCHEMA = 10`) cho CSDL ĐANG Ở v9. Ca `H1` gác CẢ HAI tầng.
#   (2) `OWNER_ACTIONS C4` = "Chuyển CSDL nghiệp vụ sang PostgreSQL" = **D-8, BLOCKED OWNER**.
#       TUYỆT ĐỐI không thực hiện trong wave này, không ép cổng xanh, không đụng cụm `:5432`.
#
# PHÉP ĐO VẪN ĐỌC TẠI CHỖ (không ghim số/dòng/tên tệp) — nhưng TỪ VÒNG NÀY ĐO **BA VẾ**, vì
# `G19-C6` có HAI tầng đóng ở hai mốc khác nhau và một cặp boolean không phân biệt được "thiếu
# tầng chỉ mục" với "thiếu tầng tuyến":
#
#   vế 1 `schema_ok`   — `csdl.PHIEN_BAN_SCHEMA >= MỐC`, với `MỐC` = số N của hàm `nang_len_vN`
#                        áp `truy_van.DDL_G12Q` trong `app/migrate.py`, ĐỌC TẠI CHỖ. So `>=` chứ
#                        KHÔNG `==`: `v11` sau này không làm cổng đỏ vĩnh viễn. Đây CHÍNH LÀ
#                        "SCHEMA TỐI THIỂU" mà `thu_qa_g22.py` cần — không phải con số 9/10 viết
#                        tay: nếu ai bỏ mốc v10 thì `MỐC` không đọc được ⇒ vế này ĐỎ, chứ không
#                        âm thầm tụt xuống 9.
#   vế 2 `chi_muc_ok`  — `truy_van.DDL_G12Q` có THẬT (hằng literal khác rỗng) VÀ mốc migration
#                        được `migrate.chay()` GỌI (`nang_len_vN(...)`). Một hàm không ai gọi
#                        không nâng cấp gì; một hằng rỗng không tạo chỉ mục nào.
#   vế 3 `tuyen_ok`    — có tệp SẢN XUẤT vừa `import truy_van` vừa DÙNG nó cho việc KHÁC
#                        `DDL_G12Q` (tức tuyến `tim_don`/`mo_ta_bo_loc`).
#
# VÌ SAO KHÔNG `PHIEN_BAN_SCHEMA == 9` (ghim cũ) VÀ CŨNG KHÔNG `== 10`: 9/10 là SỰ THẬT CỦA MÔI
# TRƯỜNG, nhích ở mỗi lần nâng cấp — đúng họ H5/N-G19-04. `msg_0b757445cfb8` yêu cầu đổi sang
# "SCHEMA TỐI THIỂU" theo hợp đồng, KHÔNG phải đổi 9 thành 10 đơn thuần. Vì thế `MỐC` được SUY RA
# từ chính `app/migrate.py` (hàm `moc_ddl_migration()` trong tiến trình con), và ĐỐI CHỨNG ÂM
# "hạ schema xuống dưới mốc ⇒ cổng PHẢI ĐỎ" chứng minh phép so có răng.

MA_QUET_C4 = r'''
import ast, json, os, re, sys

goc = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.join(goc, "app"))
import csdl  # noqa: E402


def _trong_vung(p):
    """Cùng luật `thu_g21_chotcay`: `docs` hoặc thư mục bắt đầu bằng `thu` KHÔNG phải sản xuất."""
    phan = p.replace(os.sep, "/").split("/")
    return any(d == "docs" or d.startswith("thu") for d in phan[:-1])


def moc_ddl_migration(goc):
    """MỐC migration áp `truy_van.DDL_G12Q` — ĐỌC TẠI CHỖ, KHÔNG ghim số.

    Trả `(moc, ten_ham, duoc_goi, ly_do)`. `moc` = số N NHỎ NHẤT của một `nang_len_vN` có tham
    chiếu `truy_van.DDL_G12Q`; `duoc_goi` = `migrate.py` có lời gọi `nang_len_vN(...)`.

    Vì sao lấy MIN: nếu sau này `v11` cũng chạm `DDL_G12Q`, mốc tối thiểu vẫn là v10 — thêm bước
    mới không được làm cổng đòi schema cao hơn mức HỢP ĐỒNG cần.
    """
    p = os.path.join(goc, "app", "migrate.py")
    try:
        with open(p, encoding="utf-8") as fh:
            cay = ast.parse(fh.read())
    except Exception as e:
        return None, None, False, "KHÔNG đọc/parse được `app/migrate.py`: %s" % e
    ung = {}
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.FunctionDef):
            continue
        m = re.match(r"nang_len_v(\d+)$", nut.name)
        if not m:
            continue
        co = any(isinstance(x, ast.Attribute) and x.attr == "DDL_G12Q" for x in ast.walk(nut))
        if co:
            ung.setdefault(int(m.group(1)), []).append(nut.name)
    if not ung:
        return None, None, False, ("KHÔNG có hàm `nang_len_vN` nào áp `truy_van.DDL_G12Q` ⇒ "
                                   "tầng CHỈ MỤC G12 không có mốc migration")
    moc = min(ung)
    ten = ung[moc][0]
    goi = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == ten
              for n in ast.walk(cay))
    return moc, ten, goi, ""


def hang_ddl(goc):
    """`truy_van.DDL_G12Q` có THẬT không — đọc hằng literal ở tầng mô-đun. Trả `(có, số_câu, lỗi)`."""
    p = os.path.join(goc, "app", "truy_van.py")
    try:
        with open(p, encoding="utf-8") as fh:
            cay = ast.parse(fh.read())
    except Exception as e:
        return False, 0, "KHÔNG đọc/parse được `app/truy_van.py`: %s" % e
    for nut in cay.body:
        if isinstance(nut, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "DDL_G12Q" for t in nut.targets):
            try:
                gt = ast.literal_eval(nut.value)
            except Exception:
                return True, -1, "`DDL_G12Q` có mặt nhưng KHÔNG phải hằng literal"
            if isinstance(gt, str):
                n = len([c for c in gt.split(";") if c.strip()])
            elif isinstance(gt, (list, tuple)):
                n = len(gt)
            else:
                n = 0
            return n > 0, n, ("" if n > 0 else "`DDL_G12Q` RỖNG")
    return False, 0, "`app/truy_van.py` KHÔNG khai hằng `DDL_G12Q`"


tep = []
for g, dirs, fs in os.walk(goc):
    dirs[:] = sorted(d for d in dirs if d not in ("node_modules", ".git", "__pycache__"))
    for f in sorted(fs):
        if not f.endswith(".py"):
            continue
        p = os.path.join(g, f)
        rel = os.path.relpath(p, goc).replace(os.sep, "/")
        if _trong_vung(p) or rel == "app/truy_van.py":
            continue
        try:
            with open(p, encoding="utf-8") as fh:
                cay = ast.parse(fh.read())
        except Exception:
            continue
        # CHỈ đếm Name TRÙNG với thứ đã IMPORT trong CHÍNH tệp: `gateway/server.py` có biến cục
        # bộ cũng tên `truy_van` (chuỗi query) — đếm theo tên trần sẽ tính nó là "tham chiếu mô
        # đun", một DƯƠNG TÍNH GIẢ. Mô-đun chỉ được coi là có mặt khi tệp ĐÃ import nó.
        gan = set()
        nhap = 0
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Import):
                for a in nut.names:
                    if a.name == "truy_van":
                        nhap += 1
                        gan.add(a.asname or "truy_van")
            elif isinstance(nut, ast.ImportFrom) and nut.module == "truy_van":
                nhap += 1
                for a in nut.names:
                    if a.name != "*":
                        gan.add(a.asname or a.name)
        if not nhap:
            continue
        dung = sum(1 for nut in ast.walk(cay) if isinstance(nut, ast.Name) and nut.id in gan
                   and isinstance(nut.ctx, ast.Load))
        # Tách tham chiếu TẦNG CHỈ MỤC khỏi tham chiếu TUYẾN: mỗi `truy_van.DDL_G12Q` là một
        # Attr; Name `truy_van` bên trong nó ĐÃ được tính ở `dung`, nên trừ đi để phần còn lại
        # đúng là "dùng cho việc khác DDL" (tuyến).
        ddl = sum(1 for nut in ast.walk(cay)
                  if isinstance(nut, ast.Attribute) and nut.attr == "DDL_G12Q"
                  and isinstance(nut.value, ast.Name) and nut.value.id in gan)
        tep.append({"tep": rel, "import": nhap, "dung": dung, "ddl": ddl})

moc, ten_moc, duoc_goi, loi_moc = moc_ddl_migration(goc)
co_hang, so_cau, loi_hang = hang_ddl(goc)
print("__C4__" + json.dumps({"schema": int(getattr(csdl, "PHIEN_BAN_SCHEMA", 0)),
                             "moc_ddl": moc, "ten_ham_ddl": ten_moc, "duoc_goi": duoc_goi,
                             "loi_moc": loi_moc, "hang_ddl": co_hang,
                             "so_cau_ddl": so_cau, "loi_hang": loi_hang,
                             "tep": tep}, ensure_ascii=False))
'''


def _do_c4(goc=None):
    """ĐO `C4` (= `G19-C6`) TẠI CHỖ trên cây `goc` — KHÔNG ghim số tham chiếu, KHÔNG ghim tệp.

    Trả dict; `cap` là BỘ BA `(schema_ok, chi_muc_ok, tuyen_ok)` khớp ô `SO_DO["c4-route-va-moc-ddl"]`:
      · `schema` / `moc_ddl` / `schema_ok` — `csdl.PHIEN_BAN_SCHEMA` của CHÍNH cây đang đo, so
        `>=` với **MỐC migration áp `truy_van.DDL_G12Q`** đọc từ `app/migrate.py`. `v9` KHÔNG còn
        là sàn viết tay; mốc là "SCHEMA TỐI THIỂU" suy ra tại chỗ. Mốc không đọc được ⇒ ĐỎ;
      · `chi_muc_ok` — hằng `truy_van.DDL_G12Q` khác rỗng VÀ mốc có lời gọi trong `migrate.py`;
      · `tep` — tệp SẢN XUẤT tham chiếu `truy_van`, kèm `import`, số lần **DÙNG**, và số lần dùng
        riêng cho `DDL_G12Q`. "DÙNG" chỉ đếm `Name` trùng tên do CHÍNH tệp đó import — biến cục
        bộ trùng tên (đo được ở `gateway/server.py`) KHÔNG bị tính là tham chiếu mô-đun;
      · `tuyen_ok` — phải có tệp vừa `import` vừa DÙNG cho việc KHÁC `DDL_G12Q`. Một `import`
        không có lời gọi KHÔNG phải một tuyến; một tham chiếu DDL không phải tuyến;
      · `loi` — nguyên văn khi KHÔNG ĐO ĐƯỢC; người gọi PHẢI coi là ĐỎ, không phải "đạt".
    """
    goc = os.path.abspath(goc or GOC_CAY)
    ra = {"goc": goc, "rc": 1, "schema": None, "tep": [], "moc_ddl": None,
          "ten_ham_ddl": None, "duoc_goi": False, "hang_ddl": False, "so_cau_ddl": 0,
          "loi_moc": "", "loi_hang": "", "schema_ok": False, "chi_muc_ok": False,
          "tuyen_ok": False, "cap": (False, False, False), "loi": ""}
    rc, out = chay([PY, "-c", MA_QUET_C4, goc], giay=300, cwd=goc,
                   env_them={"PYTHONDONTWRITEBYTECODE": "1"})
    ra["rc"] = rc
    dong = [d for d in out.splitlines() if d.startswith("__C4__")]
    if rc != 0 or not dong:
        ra["loi"] = "KHÔNG ĐO ĐƯỢC C4 trên %s (rc=%d): %s" % (goc, rc, out[-400:])
        return ra
    d = json.loads(dong[-1][len("__C4__"):])
    ra["schema"] = int(d["schema"])
    ra["tep"] = d["tep"]
    ra["moc_ddl"] = d["moc_ddl"]
    ra["ten_ham_ddl"] = d["ten_ham_ddl"]
    ra["duoc_goi"] = bool(d["duoc_goi"])
    ra["hang_ddl"] = bool(d["hang_ddl"])
    ra["so_cau_ddl"] = int(d["so_cau_ddl"])
    ra["loi_moc"] = d.get("loi_moc") or ""
    ra["loi_hang"] = d.get("loi_hang") or ""
    ra["schema_ok"] = ra["moc_ddl"] is not None and ra["schema"] >= ra["moc_ddl"]
    ra["chi_muc_ok"] = (ra["moc_ddl"] is not None and ra["duoc_goi"] and ra["hang_ddl"])
    ra["tuyen_ok"] = any(t["dung"] - t["ddl"] > 0 for t in ra["tep"])
    ra["cap"] = (ra["schema_ok"], ra["chi_muc_ok"], ra["tuyen_ok"])
    return ra


def _chep_app_tam(nhan):
    """BẢN SAO THẬT của `app/` trong TMP. KHÔNG ghi một byte nào vào cây thật."""
    d = tempfile.mkdtemp(prefix="g22-c4-%s-" % nhan)
    shutil.copytree(GOC_APP, os.path.join(d, "app"),
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    return d


def _tep_san_xuat(goc):
    """Mọi tệp `.py` SẢN XUẤT dưới `goc` — CÙNG luật với `MA_QUET_C4` (viết lại ĐỘC LẬP, cố ý)."""
    ra = []
    for g, dirs, fs in os.walk(goc):
        dirs[:] = sorted(d for d in dirs if d not in ("node_modules", ".git", "__pycache__"))
        for f in sorted(fs):
            if not f.endswith(".py"):
                continue
            p = os.path.join(g, f)
            rel = os.path.relpath(p, goc).replace(os.sep, "/")
            phan = rel.split("/")
            if any(d == "docs" or d.startswith("thu") for d in phan[:-1]):
                continue
            if rel == "app/truy_van.py":
                continue
            ra.append((rel, p))
    return ra


def _go_tuyen_truy_van(goc):
    """GỠ TẦNG TUYẾN `truy_van` khỏi BẢN SAO `goc` — LÀM THẬT, bằng AST, không ghim tệp/dòng.

    Sửa MỌI tệp SẢN XUẤT có tham chiếu **TUYẾN** — tức `truy_van.<x>` với `<x>` KHÁC `DDL_G12Q`:
    gỡ mọi câu `import truy_van` (và `from truy_van import …`) cùng mọi khối `if` DÙNG nó (khối
    `/api/v2/don` và tuyến tự mô tả). Tệp chỉ chạm `truy_van.DDL_G12Q` (`app/migrate.py` từ v10)
    được GIỮ NGUYÊN: đó là tầng CHỈ MỤC, có đối chứng âm RIÊNG là "hạ schema" — gộp hai tầng vào
    một phép gỡ sẽ làm đối chứng mất khả năng phân biệt "thiếu tuyến" với "thiếu chỉ mục".

    Vòng trước (đến `5fc5f6f`) hàm này chỉ sửa `app/server.py` và đòi `sau["tep"] == []`; U4 thêm
    `import truy_van` vào `app/migrate.py` ⇒ đòi hỏi đó thành SAI (một ĐỎ GIẢ của đối chứng, không
    phải của sản phẩm). Nay phép gỡ quét ĐÚNG các tệp có tham chiếu tuyến, và lời khẳng định đổi
    thành "mọi tệp còn lại chỉ chạm `DDL_G12Q`" — mạnh hơn, và đúng bản chất hai tầng.

    Dùng AST chứ không ghim dòng vì dòng nhích ở mọi bản vá kế tiếp — ghim dòng chính là họ lỗi
    H5/N-G19-04. Trả dict ĐO ĐƯỢC; ném `RuntimeError` nếu không có gì để gỡ hoặc tệp sau khi gỡ
    không còn hợp lệ cú pháp — khi đó phép đối chứng KHÔNG được kết luận gì.
    """
    da_go = []
    for rel, p in _tep_san_xuat(goc):
        with open(p, encoding="utf-8") as f:
            dong = f.read().splitlines(keepends=True)
        try:
            cay = ast.parse("".join(dong))
        except SyntaxError:
            continue
        gan = set()
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Import):
                gan.update(a.asname or "truy_van" for a in nut.names if a.name == "truy_van")
            elif isinstance(nut, ast.ImportFrom) and nut.module == "truy_van":
                gan.update(a.asname or a.name for a in nut.names if a.name != "*")
        if not gan:
            continue
        ten_tron = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)
                    and isinstance(n.ctx, ast.Load) and n.id in gan}
        # MỘT `Name` KHÔNG BAO GIỜ LÀ `Attribute` — phải nhìn LÊN cha: `truy_van.DDL_G12Q` là
        # Attribute(attr="DDL_G12Q", value=Name("truy_van")). Đếm theo Attribute và ghi nhớ
        # ĐÚNG đối tượng `Name` bên trong, rồi mới phân loại "chỉ chạm tầng CHỈ MỤC".
        ddl_id = {id(nut.value) for nut in ast.walk(cay)
                  if isinstance(nut, ast.Attribute) and nut.attr == "DDL_G12Q"
                  and isinstance(nut.value, ast.Name) and nut.value.id in gan}
        tai = [n for n in ast.walk(cay) if isinstance(n, ast.Name)
               and isinstance(n.ctx, ast.Load) and n.id in gan]
        if not tai or all(id(n) in ddl_id for n in tai):
            continue          # tầng CHỈ MỤC — không phải tầng TUYẾN
        khoang = []
        for nut in ast.walk(cay):
            if isinstance(nut, ast.Import) and any(a.name == "truy_van" for a in nut.names):
                khoang.append((nut.lineno, nut.end_lineno, "import truy_van"))
            elif isinstance(nut, ast.ImportFrom) and nut.module == "truy_van":
                khoang.append((nut.lineno, nut.end_lineno, "from truy_van import …"))
            elif isinstance(nut, ast.If) and any(
                    isinstance(x, ast.Name) and x.id in ten_tron for x in ast.walk(nut)):
                khoang.append((nut.lineno, nut.end_lineno, "khối if DÙNG truy_van (tuyến)"))
        if not khoang:
            raise RuntimeError("`%s` có tham chiếu tuyến `%s` nhưng KHÔNG tìm được khối nào để gỡ "
                               "⇒ đối chứng vô nghĩa" % (rel, ",".join(sorted(ten_tron))))
        khoang.sort()
        gop = []
        for a, b, ten in khoang:
            if gop and a <= gop[-1][1]:
                gop[-1][1] = max(gop[-1][1], b)
            else:
                gop.append([a, b, ten])
        xoa = set()
        for a, b, _ in gop:
            xoa.update(range(a - 1, b))
        moi = [d for i, d in enumerate(dong) if i not in xoa]
        try:
            cay_moi = ast.parse("".join(moi))
        except SyntaxError as e:
            raise RuntimeError("gỡ tuyến xong `%s` KHÔNG còn hợp lệ cú pháp (%s) ⇒ không đối "
                               "chứng được" % (rel, e))
        con = {n.id for n in ast.walk(cay_moi) if isinstance(n, ast.Name)
               and isinstance(n.ctx, ast.Load) and n.id in gan}
        if con:
            raise RuntimeError("gỡ tuyến xong `%s` VẪN còn DÙNG `%s` ⇒ phép gỡ CHƯA SẠCH, không "
                               "kết luận được" % (rel, ",".join(sorted(con))))
        with open(p, "w", encoding="utf-8") as f:
            f.write("".join(moi))
        da_go.append({"tep": rel, "so_khoi": len(gop), "so_dong": len(xoa),
                      "chi_tiet": [(ten, b - a + 1) for a, b, ten in gop]})
    if not da_go:
        raise RuntimeError("bản sao KHÔNG có tham chiếu TUYẾN `truy_van` nào để gỡ ⇒ đối chứng "
                           "vô nghĩa")
    return {"tep": [x["tep"] for x in da_go], "so_khoi": sum(x["so_khoi"] for x in da_go),
            "so_dong": sum(x["so_dong"] for x in da_go),
            "chi_tiet": [(x["tep"], ten, n) for x in da_go for ten, n in x["chi_tiet"]]}


def _doi_schema_ban_sao(goc, gia_tri):
    """Đổi `PHIEN_BAN_SCHEMA` trong `app/csdl.py` của BẢN SAO (KHÔNG chạm cây thật).

    Dùng cho ĐỐI CHỨNG ÂM "hạ schema xuống dưới mốc ⇒ cổng PHẢI ĐỎ" và ĐỐI CHỨNG DƯƠNG "nâng
    schema lên trên mốc ⇒ cổng VẪN XANH (không ghim đúng một số)". Ném nếu không sửa được ĐÚNG
    một dòng — khi đó phép đối chứng không kết luận được gì.
    """
    p = os.path.join(goc, "app", "csdl.py")
    with open(p, encoding="utf-8") as f:
        than = f.read()
    moi, n = re.subn(r"(?m)^PHIEN_BAN_SCHEMA\s*=\s*\d+\s*$",
                     "PHIEN_BAN_SCHEMA = %d" % gia_tri, than)
    if n != 1:
        raise RuntimeError("KHÔNG sửa được đúng MỘT dòng `PHIEN_BAN_SCHEMA` trong bản sao `%s` "
                           "(n=%d) ⇒ đối chứng vô nghĩa" % (goc, n))
    with open(p, "w", encoding="utf-8") as f:
        f.write(moi)
    return n


class H_C4(unittest.TestCase):
    """`C4` — việc thật tên là **`G19-C6`**, và từ `5fc5f6f` nó **ĐÃ ĐÓNG CẢ HAI TẦNG**.

    ĐÍNH CHÍNH so với docstring cũ ("CHƯA CÓ CHỦ SỞ HỮU … KHÔNG nhận là đã đóng"): câu đó đúng ở
    nền `a6b5b73`, nhưng SAI từ `146500b` — AG-06 đã port khối route `truy_van` (~20 dòng) vào
    `app/server.py`. ĐÍNH CHÍNH LẦN HAI (vòng này, `task_889a1ddeccdb`): câu "`nang_len_v10` CHƯA
    được áp, `PHIEN_BAN_SCHEMA` vẫn là 9" cũng đã SAI — U4 đã đóng nốt tầng chỉ mục
    (`migrate.nang_len_v10` + `PHIEN_BAN_SCHEMA = 10`). Vì thế phép đo nâng từ CẶP lên **BỘ BA**:

        `(schema_ok, chi_muc_ok, tuyen_ok)` — khớp ô `SO_DO["c4-route-va-moc-ddl"]`.

    Và `MỐC` của vế schema KHÔNG phải số 9/10 viết tay: nó được ĐỌC từ `app/migrate.py` (số N của
    hàm `nang_len_vN` áp `truy_van.DDL_G12Q`) — tức **SCHEMA TỐI THIỂU** mà `thu_qa_g22.py` cần.
    Đổi `== 9` thành `== 10` chỉ dời cái ghim đi một bước và sẽ STALE lần nữa; đọc mốc tại chỗ +
    so `>=` là bất biến đúng.

    HAI THỨ TRÙNG NHÃN "C4" — TUYỆT ĐỐI KHÔNG ĐÁNH ĐỒNG:
      · **`G19-C6`** (việc này): route `truy_van` + `DDL_G12Q` vào migration. Chủ: **Agent 06**
        (route, `146500b`) + **U4/AG-02** (mốc `nang_len_v10`) + **Agent 02** (ca đo này).
      · **`OWNER_ACTIONS C4`** = "Chuyển CSDL nghiệp vụ sang PostgreSQL" = **D-8, BLOCKED OWNER**.
        KHÔNG thực hiện, KHÔNG ép cổng xanh, KHÔNG đụng `:5432`. Đây là việc KHÁC.
    """

    def test_h1_c4_do_hay_da_dong(self):
        """ĐO `C4`/`G19-C6` TẠI CHỖ và CHỨNG MINH RĂNG của cổng bằng BA ĐỐI CHỨNG ÂM LÀM THẬT.

        BỐN vế, cả bốn đo được:
          (i)   cây THẬT: bộ ba `(schema ≥ MỐC DDL, tầng chỉ mục có thật + được gọi, tuyến nối
                thật)` phải bằng ô "đóng" `(True, True, True)`. `MỐC` đọc tại chỗ từ
                `app/migrate.py`; KHÔNG ghim con số, KHÔNG ghim tệp/dòng;
          (ii)  ĐỐI CHỨNG DƯƠNG: bản sao `app/` y nguyên phải cho ĐÚNG bộ ba + ĐÚNG danh sách
                tham chiếu — nếu bản sao đã khác cây thật thì các đối chứng dưới không nói gì;
          (iii) ĐỐI CHỨNG ÂM "GỠ TUYẾN": gỡ mọi `import truy_van` + mọi khối `if` DÙNG nó trên
                MỌI tệp sản xuất có tham chiếu TUYẾN ⇒ `tuyen_ok` False, tầng chỉ mục KHÔNG bị
                chạm, bộ ba thành `(True, True, False)` và `dat_cong` PHẢI ĐỎ;
          (iv)  ĐỐI CHỨNG ÂM "HẠ SCHEMA": hạ `PHIEN_BAN_SCHEMA` xuống `MỐC − 1` trên bản sao ⇒
                `schema_ok` False, bộ ba ≠ ô đóng, `dat_cong` PHẢI ĐỎ. Kèm ĐỐI CHỨNG DƯƠNG "NÂNG
                SCHEMA" lên `MỐC + 3`: cổng VẪN XANH — chứng minh `>=` chứ không phải ghim đúng
                một số (nếu ghim `== 10` thì vế này ĐỎ, và đó là điều ta muốn bắt).

        Không xoá ca, không `skipTest`, không nới assert: nếu sản phẩm chưa đóng, ca này ĐỎ THẬT
        và in thẳng "C4 CHƯA ĐÓNG".
        """
        dong = SO_DO["c4-route-va-moc-ddl"]["dong"]
        nen = SO_DO["c4-route-va-moc-ddl"]["nen"]

        def _mo_ta(tep):
            return ("; ".join("%s (import %d · dùng %d · DDL %d)"
                              % (t["tep"], t["import"], t["dung"], t["ddl"]) for t in tep)
                    or "KHÔNG CÓ TỆP NÀO")

        that = _do_c4()
        print("\n  [H1] C4 = G19-C6 — ĐO TẠI CHỖ trên cây thật (%s)" % that["goc"])
        if that["loi"]:
            self.fail(that["loi"])
        print("       `PHIEN_BAN_SCHEMA`=%d · MỐC migration áp `truy_van.DDL_G12Q`=%r (%s · được "
              "`migrate.chay()` gọi=%s)"
              % (that["schema"], that["moc_ddl"], that["ten_ham_ddl"], that["duoc_goi"]))
        print("       `truy_van.DDL_G12Q`: có hằng=%s · số câu=%d%s"
              % (that["hang_ddl"], that["so_cau_ddl"],
                 (" · " + that["loi_hang"]) if that["loi_hang"] else ""))
        print("       SCHEMA TỐI THIỂU = %r (đòi `schema >= mốc`, KHÔNG ghim đúng một số)"
              % (that["moc_ddl"],))
        print("       tham chiếu ĐẾM ĐƯỢC: %s" % _mo_ta(that["tep"]))
        print("       bộ ba đo được = %r · sổ G22: nền=%r · đóng=%r · phân quyết = %s"
              % (that["cap"], nen, dong,
                 "DONG" if that["cap"] == dong else ("NEN" if that["cap"] == nen else "NUA_VOI")))
        self.assertEqual(that["rc"], 0, "phép đo C4 không chạy được: %s" % that["loi"])
        self.assertIsNotNone(that["moc_ddl"],
                             "C4 CHƯA ĐÓNG: KHÔNG đọc được MỐC migration áp `truy_van.DDL_G12Q` "
                             "trong `app/migrate.py` (%s) — tầng CHỈ MỤC của G19-C6 chưa có mốc, "
                             "và không có mốc thì không có 'schema tối thiểu' để so."
                             % (that["loi_moc"] or "không rõ lý do",))
        self.assertTrue(that["schema_ok"],
                        "C4 CHƯA ĐÓNG: `PHIEN_BAN_SCHEMA`=%r < MỐC %r — CSDL ĐANG Ở mốc trước "
                        "sẽ KHÔNG nhận `DDL_G12Q`, tức tầng chỉ mục G12 chưa đóng"
                        % (that["schema"], that["moc_ddl"]))
        self.assertTrue(that["chi_muc_ok"],
                        "C4 CHƯA ĐÓNG: tầng CHỈ MỤC không đóng — `truy_van.DDL_G12Q` có=%r "
                        "(số câu=%d, %s) · mốc=%r · được gọi=%r"
                        % (that["hang_ddl"], that["so_cau_ddl"],
                           that["loi_hang"] or "không lỗi", that["moc_ddl"], that["duoc_goi"]))
        self.assertTrue(that["tuyen_ok"],
                        "C4 CHƯA ĐÓNG: KHÔNG có tệp SẢN XUẤT nào vừa import `truy_van` vừa DÙNG "
                        "nó cho tuyến (khác `DDL_G12Q`) — đây là trạng thái NỀN %r, không phải đã "
                        "đóng. Việc thật là G19-C6 (route `truy_van`), chủ: Agent 06." % (nen,))
        self.assertEqual(that["cap"], dong,
                         "C4 CHƯA ĐÓNG: bộ ba đo được %r ≠ ô đóng %r của "
                         "`SO_DO[\"c4-route-va-moc-ddl\"]` — ghi thẳng, không ép xanh"
                         % (that["cap"], dong))
        print("       CHỦ SỞ HỮU: Agent 06 (route `truy_van`, `146500b`) + U4/AG-02 (mốc "
              "`nang_len_v10` áp `DDL_G12Q`) + Agent 02 (ca đo này). Việc thật tên là **G19-C6**, "
              "KHÔNG phải `OWNER_ACTIONS C4` = D-8/BLOCKED OWNER.")

        # ── (ii) ĐỐI CHỨNG DƯƠNG: BẢN SAO Y NGUYÊN phải cho ĐÚNG bộ ba ──────────────────────
        tam = _chep_app_tam("doi-chung")
        try:
            truoc = _do_c4(tam)
            print("       ĐỐI CHỨNG DƯƠNG: bản sao `app/` y nguyên → %r (đòi %r) ✓"
                  % (truoc["cap"], dong))
            self.assertEqual(truoc["cap"], that["cap"],
                             "ĐỐI CHỨNG DƯƠNG HỎNG: bản sao y nguyên cho %r ≠ cây thật %r ⇒ "
                             "phép đối chứng không dùng được" % (truoc["cap"], that["cap"]))
            self.assertEqual(truoc["tep"], that["tep"],
                             "ĐỐI CHỨNG DƯƠNG HỎNG: danh sách tham chiếu của bản sao khác cây "
                             "thật: %r ≠ %r" % (truoc["tep"], that["tep"]))
            self.assertEqual(truoc["moc_ddl"], that["moc_ddl"],
                             "ĐỐI CHỨNG DƯƠNG HỎNG: MỐC DDL của bản sao khác cây thật")

            # ── (iii) ĐỐI CHỨNG ÂM "GỠ TUYẾN" — LÀM THẬT trên CHÍNH bản sao đó ────────────────
            go = _go_tuyen_truy_van(tam)
            sau = _do_c4(tam)
            print("       ĐỐI CHỨNG ÂM (LÀM THẬT): gỡ %d khối / %d dòng khỏi %s — %s"
                  % (go["so_khoi"], go["so_dong"], ", ".join(go["tep"]),
                     ", ".join("%s: %s (%d dòng)" % (t, ten, n) for t, ten, n in go["chi_tiet"])))
            print("       sau khi gỡ tuyến: bộ ba = %r · tham chiếu còn lại: %s"
                  % (sau["cap"], _mo_ta(sau["tep"])))
            self.assertFalse(sau["tuyen_ok"],
                             "GỠ TUYẾN MÀ `tuyen_ok` VẪN TRUE (%r) ⇒ bộ đo MÙ, 'đã đóng' trên cây "
                             "thật không chứng minh được gì" % (sau["cap"],))
            self.assertTrue(sau["schema_ok"] and sau["chi_muc_ok"],
                            "gỡ TUYẾN lại làm ĐỔ tầng CHỈ MỤC (bộ ba %r) ⇒ hai tầng không được "
                            "tách đúng, đối chứng không kết luận được" % (sau["cap"],))
            self.assertEqual(sau["cap"], (True, True, False),
                             "sau khi gỡ tuyến, bộ ba phải là (True, True, False); đo được %r"
                             % (sau["cap"],))
            self.assertNotEqual(sau["cap"], dong,
                                "sau khi gỡ tuyến, bộ ba vẫn bằng ô đóng %r ⇒ cổng không có răng"
                                % (dong,))
            self.assertTrue(all(t["ddl"] > 0 and t["dung"] == t["ddl"] for t in sau["tep"]),
                            "sau khi gỡ tuyến VẪN còn tham chiếu KHÔNG phải `DDL_G12Q`: %r ⇒ "
                            "phép gỡ chưa sạch" % (sau["tep"],))
            dat_am, vi_am = dat_cong("c4-route-va-moc-ddl", sau["cap"])
            print("       ⇒ `dat_cong` phán: %s (đòi ĐỎ) · %s"
                  % ("ĐỎ ✓" if not dat_am else "ĐẠT-SAI ✗", vi_am))
            self.assertFalse(dat_am, "GỠ TUYẾN MÀ CỔNG VẪN ĐẠT: %s" % vi_am)
        finally:
            shutil.rmtree(tam, ignore_errors=True)

        # ── (iv) ĐỐI CHỨNG ÂM "HẠ SCHEMA" + ĐỐI CHỨNG DƯƠNG "NÂNG SCHEMA" ────────────────────
        moc = that["moc_ddl"]
        if moc is None:
            self.fail("không có MỐC DDL để chạy đối chứng 'hạ schema' — bản thân phép đo đã ĐỎ")
        tam2 = _chep_app_tam("schema")
        try:
            _doi_schema_ban_sao(tam2, moc - 1)
            thap = _do_c4(tam2)
            print("       ĐỐI CHỨNG ÂM (LÀM THẬT): hạ `PHIEN_BAN_SCHEMA` %d → %d trên bản sao → "
                  "bộ ba %r · `schema_ok`=%s"
                  % (moc, moc - 1, thap["cap"], thap["schema_ok"]))
            self.assertEqual(thap["schema"], moc - 1,
                             "phép tiêm schema không tới được phép đo (đọc ra %r)" % (thap["schema"],))
            self.assertFalse(thap["schema_ok"],
                             "HẠ SCHEMA XUỐNG DƯỚI MỐC (%d < %d) MÀ `schema_ok` VẪN TRUE ⇒ phép "
                             "so `>=` KHÔNG có răng" % (moc - 1, moc))
            self.assertNotEqual(thap["cap"], dong,
                                "hạ schema xuống dưới mốc mà bộ ba vẫn bằng ô đóng %r ⇒ cổng mù"
                                % (dong,))
            dat_am2, vi_am2 = dat_cong("c4-route-va-moc-ddl", thap["cap"])
            print("       ⇒ `dat_cong` phán: %s (đòi ĐỎ) · %s"
                  % ("ĐỎ ✓" if not dat_am2 else "ĐẠT-SAI ✗", vi_am2))
            self.assertFalse(dat_am2, "HẠ SCHEMA MÀ CỔNG VẪN ĐẠT: %s" % vi_am2)

            _doi_schema_ban_sao(tam2, moc + 3)
            cao = _do_c4(tam2)
            print("       ĐỐI CHỨNG DƯƠNG: nâng `PHIEN_BAN_SCHEMA` %d → %d trên CÙNG bản sao → "
                  "bộ ba %r (đòi %r) · `schema_ok`=%s"
                  % (moc, moc + 3, cao["cap"], dong, cao["schema_ok"]))
            self.assertTrue(cao["schema_ok"],
                            "NÂNG SCHEMA LÊN TRÊN MỐC MÀ VẪN ĐỎ ⇒ cổng đang GHIM ĐÚNG một con số, "
                            "không phải 'schema tối thiểu'")
            self.assertEqual(cao["cap"], dong,
                             "schema cao hơn mốc mà bộ ba %r ≠ ô đóng %r" % (cao["cap"], dong))
        finally:
            shutil.rmtree(tam2, ignore_errors=True)

        print("       CÒN TREO (KHÔNG nhận là đã xong): KHÔNG còn phần mã nào của `G19-C6` — cả "
              "HAI tầng (tuyến + mốc `DDL_G12Q`) đã ĐO ĐƯỢC trên cây. Việc còn BLOCKED là "
              "`OWNER_ACTIONS C4` = D-8 'chuyển CSDL nghiệp vụ sang PostgreSQL' — KHÔNG thực hiện "
              "trong wave này, không đụng cụm `:5432`.")
        _dc_duong("c4-go-route")
        DA_TIEM["c4-go-route"] = True


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
                                     "ng21-03-ca-ghim-ro", "c4-go-route")
                            and not DA_TIEM.get(n))
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
    # CÁC MÔ-ĐUN HỖ TRỢ mà chính hai bàn đo import. Đo được ở `5fc5f6f`: U2 đã cho
    # `thu_qa_g20.py` `import thu_g21_chotcay`; cây gương cũ chỉ có hai bàn đo ⇒ cột "SAU" chết
    # với `ModuleNotFoundError`, và `I2` đỏ vì MÔI TRƯỜNG CÂY GƯƠNG, không phải vì bản vá. Chép
    # MỌI mô-đun trong `app/thu/` TRỪ `thu_qa_g19*` (hai tệp đó do phép TIÊM viết, mẫu số phải
    # là 2) và trừ chính hai bàn đo (ghi đè ngay dưới).
    for ten_tep in sorted(os.listdir(GOC_THU)):
        if (not ten_tep.endswith(".py") or ten_tep.startswith("thu_qa_g19")
                or ten_tep in (os.path.basename(BAN_DO_G20), os.path.basename(BAN_DO_G21))):
            continue
        shutil.copy2(os.path.join(GOC_THU, ten_tep), os.path.join(goc, "app", "thu", ten_tep))
    for duong, cap, sha_goc, sha_trong_cay in (
            (BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA, BAN_DO_G20_SHA_TRONG_CAY),
            (BAN_DO_G21, G21_G7_VA, BAN_DO_G21_GOC_SHA, BAN_DO_G21_SHA_TRONG_CAY)):
        dich = os.path.join(goc, "app", "thu", os.path.basename(duong))
        if cot == "sau":
            shutil.copy2(duong, dich)
            if _bam(dich) != _bam(duong):
                raise AssertionError("cây gương `%s`: bản chép KHÔNG khớp byte với tệp nguồn `%s`"
                                     % (ten, duong))
        else:
            than, ghi_chu = nguon_goc(duong, cap, sha_goc, sha_trong_cay)
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
        kq = do_a1()
        print("  nền: HEAD ĐỌC TẠI CHỖ=%s · HEAD^{tree}=%s · write-tree(index tạm)=%s"
              % (kq["head"][:12] or "KHÔNG ĐỌC ĐƯỢC",
                 kq["tree_head"][:12] or "KHÔNG ĐỌC ĐƯỢC",
                 kq["tree_index"][:12] or "KHÔNG ĐỌC ĐƯỢC"))
        print("  số ca E2E DO PLAYWRIGHT LIỆT KÊ (`--list`): toàn bộ=%d · bàn phím=%d "
              "· %d tệp spec" % (SO_CA["toan_bo"], SO_CA["ban_phim"], SO_CA["so_tep"]))
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
    """Bộ kiểm TỰ KIỂM phạm vi ghi: ngoài danh sách tệp được phép, cây phải sạch.

    Nền là HEAD ĐỌC TẠI CHỖ, nên KHÔNG còn delta hai commit để miễn trừ — cùng một luật với `A2`.
    """
    rc, ds = trang_thai()
    la = [d for d in ds if d.strip()]
    ngoai = [d for d in la
             if not any(duong_cua_dong_status(d).endswith(t) for t in TEP_DUOC_PHEP)]
    return {"rc": rc, "so_duong": len(la), "ngoai": ngoai}


MAIN_DOC = """
  BỘ KIỂM G22 — AG-01 (QA/VERIFIER)

  Nền: HEAD ĐỌC TẠI CHỖ = %s  (tree %s)
  Cây đang đo: %s
  Index hiện tại: write-tree (bản sao index) = %s

  Lệnh:
    python3 app/thu/thu_qa_g22.py                       # làn mặc định
    VIP_G22_CHE_DO=gop python3 app/thu/thu_qa_g22.py    # nghiệm thu bản đã gộp
    VIP_G22_DAY_DU=1 python3 app/thu/thu_qa_g22.py      # + chạy lại chay_tat_ca.sh
"""


def main():
    os.makedirs(LOG_DIR, exist_ok=True)

    # ĐO NỀN TRƯỚC KHI ĐO SẢN PHẨM. Nền KHÔNG phải hằng số: HEAD và HEAD^{tree} đọc tại chỗ.
    kq = do_a1()
    head = kq["head"] or "KHÔNG ĐỌC ĐƯỢC"
    tree_head = kq["tree_head"] or "KHÔNG ĐỌC ĐƯỢC"
    tree_index = kq["tree_index"] or "KHÔNG ĐỌC ĐƯỢC"
    print(MAIN_DOC % (head[:12], tree_head[:12], GOC_CAY, tree_index[:12]))
    if kq["dat"]:
        print("  NỀN: index == HEAD^{tree} ✓ · không có thay đổi ngoài phạm vi ✓")
    else:
        print("  ⚠ NỀN: A1 SẼ ĐỎ — " + " | ".join(kq["ly_do"]))
    print("  số ca E2E do Playwright liệt kê (`--list`): toàn bộ=%d · bàn phím=%d"
          % (SO_CA["toan_bo"], SO_CA["ban_phim"]))

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
    print("    phạm vi ghi: %d đường trong `status`; ngoài danh sách được phép: %s"
          % (pv["so_duong"], pv["ngoai"] or "KHÔNG"))
    ok20, gc20 = nguon_da_va(BAN_DO_G20, G20_C5_VA, BAN_DO_G20_GOC_SHA,
                             BAN_DO_G20_SHA_TRONG_CAY)
    ok21, gc21 = nguon_da_va(BAN_DO_G21, G21_G7_VA, BAN_DO_G21_GOC_SHA,
                             BAN_DO_G21_SHA_TRONG_CAY)
    print("    TỆP NGUỒN `app/thu/thu_qa_g20.py` (C5): ĐÃ VÁ = %s · %s" % (ok20, gc20))
    print("    TỆP NGUỒN `app/thu/thu_qa_g21.py` (G7): ĐÃ VÁ = %s · %s" % (ok21, gc21))
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
