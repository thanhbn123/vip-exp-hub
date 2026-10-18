#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BỘ ĐO NGHIỆM THU G22 — CHẠY BỘ KIỂM TRÊN **BẢN SAO SẠCH** VÀ ĐỐI CHIẾU VỚI WORKTREE.

VAI: AG-05 (CLEAN ACCEPTANCE). Đây là DỤNG CỤ ĐO, KHÔNG phải một lời tuyên bố ĐẠT.

VÌ SAO PHẢI CÓ BẢN SAO SẠCH
--------------------------
Worktree của agent bị sandbox chặn ghi `.git` (`index.lock`: Operation not permitted), nên
`git write-tree` trả 128 và ba cổng "cây sạch" của bộ kiểm không thể phán quyết trong worktree.
Cách chạy ĐÚNG (đã ghi ở `docs/QA_G22.md` §1.2) là dựng một kho BÌNH THƯỜNG bằng
`git clone --shared` rồi `checkout --detach <commit>`, và chạy bộ kiểm trong đó. Script này làm
đúng việc ấy, không ghi một byte nào vào `.git` của worktree chính.

Script KHÔNG sửa bộ kiểm, KHÔNG sửa mã sản phẩm, KHÔNG đọc/ghi CSDL thật, KHÔNG gọi mạng ra
ngoài (bộ kiểm tự dùng 127.0.0.1: cổng do OS cấp), KHÔNG push/deploy.

CÁCH DÙNG (đầy đủ ở `docs/G22_ACCEPTANCE_HARNESS.md`):

    python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py \
        --commit a76ec51 --mode clone

    python3 trien_khai/g22-acceptance/nghiem_thu_ban_sao.py \
        --commit a76ec51 --dest /tmp/veh_g22_nt/ban_sao --mode clone

Tham số bắt buộc theo đề bài: `--commit` (commit đo), `--dest` (thư mục đích của bản sao),
`--mode` (`clone` = `git clone --shared` + `checkout --detach`; `archive` = `git archive` +
giải nén, KHÔNG có `.git`). `--dest` có mặc định an toàn ngoài cây (`/tmp/...`).

MÃ THOÁT CỦA CHÍNH SCRIPT (không phải của bộ kiểm):
    0 = đo xong, HAI BÊN KHỚP NHAU và ĐỦ ĐIỀU KIỆN so sánh.
    1 = đo xong, nhưng HAI BÊN LỆCH hoặc KHÔNG ĐỦ ĐIỀU KIỆN so sánh (xem mục "ĐIỀU KIỆN").
    2 = BỘ ĐO KHÔNG CHẠY ĐƯỢC (dựng bản sao hỏng, bộ kiểm không in `Ran N`, hết giờ...).
Mã thoát 0 KHÔNG BAO GIỜ là "sản phẩm ĐẠT": nó chỉ nói "phép so sánh không thấy lệch".
Bộ kiểm G22 có thể ĐỎ (mã thoát 1) mà hai bên vẫn khớp nhau — khi đó script vẫn trả 0 nếu mọi
chỉ tiêu và mọi ca khớp. Phán quyết sản phẩm nằm ở log của bộ kiểm, không ở mã thoát của script.
"""

import argparse
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import uuid

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. HẰNG SỐ ĐƯỜNG DẪN
# ══════════════════════════════════════════════════════════════════════════════════════════════

GOC_REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
BO_KIEM = "app/thu/thu_qa_g22.py"           # đường dẫn tương đối trong cây
THU_MUC_KQ = os.path.join(GOC_REPO, "trien_khai", "g22-acceptance", "ket_qua")
GOC_TMP_MAC_DINH = "/tmp/veh_g22_nghiem_thu"

# Tệp tối thiểu để chứng minh "hai bên dùng CÙNG một bộ kiểm". Không phải toàn bộ 379 tệp: chỉ
# những tệp mà bộ kiểm G22 trực tiếp chạy/đọc và những tệp quyết định kết quả của nó.
TEP_BO_KIEM = (
    "app/thu/thu_qa_g22.py",
    "app/thu/thu_qa_g20.py",
    "app/thu/thu_qa_g21.py",
    "thu_giao_dien/chay.sh",
    "app/migrate.py",
    "app/cau_hinh.py",
)

# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. TIỆN ÍCH CHUNG
# ══════════════════════════════════════════════════════════════════════════════════════════════


def luc_utc(ts=None):
    ts = time.time() if ts is None else ts
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bam_tep(p):
    """sha256 của một tệp; trả `None` nếu không đọc được (không che lỗi)."""
    try:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for khuc in iter(lambda: f.read(1024 * 1024), b""):
                h.update(khuc)
        return h.hexdigest()
    except OSError:
        return None


def bam_chuoi(s):
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


def moi_truong_git_sach(env=None):
    """Trả `(env, ghi_chu)`. Gỡ gia đình `GIT_CONFIG_*` DỊ DẠNG (thiếu KEY_*) — `N-G18-00`.

    Làm y hệt bộ kiểm G22 (`_git_env()`), không rộng hơn: chỉ gỡ khi `COUNT > 0` mà thiếu khoá.
    Biến này làm MỌI lệnh git thoát 128 trên máy này; nó là lỗi môi trường, không phải sản phẩm.
    """
    e = dict(os.environ if env is None else env)
    ghi_chu = ""
    n = e.get("GIT_CONFIG_COUNT")
    if n and str(n).isdigit() and int(n) > 0:
        thieu = [i for i in range(int(n)) if not e.get("GIT_CONFIG_KEY_%d" % i)]
        if thieu:
            for k in [k for k in e if k.startswith("GIT_CONFIG_")]:
                e.pop(k, None)
            ghi_chu = ("ĐÃ GỠ GIT_CONFIG_* dị dạng (COUNT=%s thiếu KEY_%s) — N-G18-00"
                       % (n, ",".join(map(str, thieu))))
    return e, ghi_chu


def chay(cmd, cwd, env=None, timeout=900, stdin_rong=True):
    """Chạy lệnh THẬT. Trả dict có `rc` đọc NGAY sau lệnh (không qua ống).

    `subprocess.run` là một lời gọi; mã thoát lấy từ `CompletedProcess.returncode` chứ không
    parse chữ trong output. Hết giờ ⇒ `rc = None`, `het_gio = True` (KHÔNG giả làm rc=0).
    """
    t0 = time.monotonic()
    luc = time.time()
    try:
        p = subprocess.run(
            cmd, cwd=cwd, env=env,
            stdin=subprocess.DEVNULL if stdin_rong else None,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", timeout=timeout,
        )
        rc, out, het_gio = p.returncode, (p.stdout or ""), False
    except subprocess.TimeoutExpired as ex:
        rc, out, het_gio = None, (ex.stdout or ""), True
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
    except OSError as ex:
        rc, out, het_gio = None, "OSError khi chạy lệnh: %r" % (ex,), False
    giay = time.monotonic() - t0
    return {"rc": rc, "out": out, "giay": round(giay, 3), "het_gio": het_gio,
            "truoc_epoch": luc, "bat_dau_utc": luc_utc(luc)}


def git(cay, *tham_so, **kw):
    """Chạy git với môi trường ĐÃ CHUẨN HOÁ. Trả `(rc, output)`."""
    e, _ = moi_truong_git_sach()
    r = chay(["git"] + list(tham_so), cwd=cay, env=e,
             timeout=kw.pop("timeout", 180))
    return r["rc"], r["out"]


def van_tay_git_dir(kho):
    """Chụp mtime/size/sha256 của `.git/index` + `.git/HEAD` — CHỈ ĐỌC.

    Dùng để chứng minh bộ đo KHÔNG ghi vào `.git` của worktree chính: cùng một phép chụp chạy
    trước và sau lượt; khác nhau ⇒ có ghi. (Sandbox chặn ghi `.git`; ta cũng không thử ghi.)
    """
    rc_gd, out_gd = git(kho, "rev-parse", "--absolute-git-dir")
    git_dir = out_gd.strip() if rc_gd == 0 else os.path.join(kho, ".git")
    ra = {"git_dir": git_dir, "rc": rc_gd}
    for ten, p in ((".git (tệp/ thư mục)", os.path.join(kho, ".git")),
                   ("git-dir/index", os.path.join(git_dir, "index")),
                   ("git-dir/HEAD", os.path.join(git_dir, "HEAD"))):
        if os.path.exists(p):
            st = os.stat(p)
            ra[ten] = {"mtime_ns": st.st_mtime_ns, "bytes": st.st_size,
                       "sha256": bam_tep(p) if os.path.isfile(p) else None}
    return ra


def json_ghi(p, du_lieu):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=2, sort_keys=False)


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. DỰNG BẢN SAO SẠCH — HAI CHẾ ĐỘ, KHÔNG GHI `.git` CỦA WORKTREE CHÍNH
# ══════════════════════════════════════════════════════════════════════════════════════════════


def giai_commit(kho, commit):
    """→ (sha_commit, sha_tree, ghi_chu). Dùng `^{commit}`/`^{tree}` để không nhận nhãn mơ hồ."""
    rc, out = git(kho, "rev-parse", "--verify", "%s^{commit}" % commit)
    if rc != 0:
        raise SystemExit("KHÔNG phân giải được commit %r trong %s (rc=%d):\n%s"
                         % (commit, kho, rc, out))
    sha = out.strip().splitlines()[-1]
    rc2, out2 = git(kho, "rev-parse", "--verify", "%s^{tree}" % sha)
    if rc2 != 0:
        raise SystemExit("KHÔNG đọc được tree của %s (rc=%d):\n%s" % (sha, rc2, out2))
    return sha, out2.strip().splitlines()[-1], ""


def tao_ban_sao(kho, sha, dest, mode):
    """Dựng bản sao SẠCH từ `sha`. KHÔNG ghi vào `.git` của `kho`; mọi thao tác ghi nằm ở `dest`.

    `clone`  : `git clone --shared --no-checkout` + `git checkout --detach <sha>`
               (đúng đường đã dùng ở `docs/QA_G22.md` §1.2; `.git` của bản sao là kho BÌNH THƯỜNG
                nên `git write-tree`/`git status` chạy được — điều worktree chính KHÔNG làm được).
    `archive`: `git -C kho archive --format=tar -o <tar> <sha>` rồi giải nén. KHÔNG có `.git`;
               dùng khi chỉ cần NỘI DUNG, không đo được cổng git.
    """
    if os.path.exists(dest):
        raise SystemExit("TỪ CHỐI: thư mục đích đã tồn tại, không ghi đè/xoá: %s" % dest)
    os.makedirs(os.path.dirname(os.path.abspath(dest)), exist_ok=True)
    thong_tin = {"mode": mode, "dest": os.path.abspath(dest), "cac_buoc": []}

    if mode == "clone":
        r = chay(["git", "clone", "--shared", "--no-checkout", "--quiet", kho, dest],
                 cwd=os.path.dirname(os.path.abspath(dest)),
                 env=moi_truong_git_sach()[0], timeout=1800)
        thong_tin["cac_buoc"].append({"lenh": ["git", "clone", "--shared", "--no-checkout",
                                               "--quiet", kho, dest],
                                      "rc": r["rc"], "giay": r["giay"],
                                      "dau_ra": r["out"][-2000:]})
        if r["rc"] != 0:
            raise SystemExit("DỰNG BẢN SAO HỎNG: git clone rc=%r\n%s" % (r["rc"], r["out"][-2000:]))
        r2 = chay(["git", "-C", dest, "checkout", "--detach", "--quiet", sha],
                  cwd=dest, env=moi_truong_git_sach()[0], timeout=600)
        thong_tin["cac_buoc"].append({"lenh": ["git", "-C", dest, "checkout", "--detach",
                                               "--quiet", sha],
                                      "rc": r2["rc"], "giay": r2["giay"],
                                      "dau_ra": r2["out"][-2000:]})
        if r2["rc"] != 0:
            raise SystemExit("DỰNG BẢN SAO HỎNG: checkout rc=%r\n%s"
                             % (r2["rc"], r2["out"][-2000:]))
    elif mode == "archive":
        tar = os.path.abspath(dest).rstrip(os.sep) + ".tar"
        os.makedirs(dest, exist_ok=True)
        r = chay(["git", "-C", kho, "archive", "--format=tar", "-o", tar, sha],
                 cwd=kho, env=moi_truong_git_sach()[0], timeout=1800)
        thong_tin["cac_buoc"].append({"lenh": ["git", "-C", kho, "archive", "--format=tar",
                                               "-o", tar, sha],
                                      "rc": r["rc"], "giay": r["giay"],
                                      "dau_ra": r["out"][-2000:]})
        if r["rc"] != 0:
            raise SystemExit("DỰNG BẢN SAO HỎNG: git archive rc=%r\n%s"
                             % (r["rc"], r["out"][-2000:]))
        try:
            with tarfile.open(tar, "r:") as tf:
                tf.extractall(dest)
            thong_tin["tar_bytes"] = os.path.getsize(tar)
        finally:
            try:
                os.unlink(tar)
            except OSError:
                pass
    else:
        raise SystemExit("mode không hợp lệ: %r (chỉ nhận clone|archive)" % mode)
    return thong_tin


def dem_tep_cay(cay):
    """Đếm tệp THẬT trên đĩa (kể cả symlink), bỏ `.git` và `node_modules`."""
    n = 0
    for _goc, thu_muc, tep in os.walk(cay):
        thu_muc[:] = [d for d in thu_muc if d not in (".git", "node_modules")]
        n += len(tep)
    return n


def kiem_ban_sao(kho, sha, tree_goc, dest, mode):
    """ĐO bản sao vừa dựng: HEAD/tree/status, số tệp, và (clone) so với tree nguồn."""
    ra = {"mode": mode, "dest": os.path.abspath(dest), "git_kha_dung": False}
    if mode == "clone":
        rc_h, out_h = git(dest, "rev-parse", "HEAD")
        rc_t, out_t = git(dest, "write-tree")
        rc_s, out_s = git(dest, "status", "--porcelain", "-uall")
        rc_l, out_l = git(dest, "ls-files")
        ra.update({
            "git_kha_dung": rc_h == 0,
            "head_rc": rc_h, "head": out_h.strip() if rc_h == 0 else out_h.strip(),
            "write_tree_rc": rc_t, "tree": out_t.strip() if rc_t == 0 else out_t.strip(),
            "status_rc": rc_s, "status": [d for d in out_s.splitlines() if d.strip()],
            "so_tep_git": len([x for x in out_l.splitlines() if x.strip()]) if rc_l == 0 else None,
        })
        ra["head_dung"] = (ra["head"] == sha)
        ra["tree_dung"] = (rc_t == 0 and ra["tree"] == tree_goc)
        ra["status_sach"] = (rc_s == 0 and ra["status"] == [])
        # `.git` của bản sao là kho bình thường — đây là điều worktree chính KHÔNG có.
        ra["co_dot_git"] = os.path.isdir(os.path.join(dest, ".git"))
    else:
        # Ở chế độ archive KHÔNG có `.git` trong bản sao. Không gọi `git -C dest`: nếu dest nằm
        # trong một repo khác, git sẽ leo lên thư mục cha và trả lời về kho đó — một phép đo SAI.
        ra.update({
            "git_kha_dung": False,
            "co_dot_git": os.path.exists(os.path.join(dest, ".git")),
            "so_tep_dia": dem_tep_cay(dest),
            "la_kho_git": None,
        })
    return ra


def dem_tep_git(kho, sha):
    rc, out = git(kho, "ls-tree", "-r", "--name-only", sha)
    if rc != 0:
        return None, out
    ds = [x for x in out.splitlines() if x.strip()]
    return len(ds), ""


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. CHẠY BỘ KIỂM Ở MỘT BÊN — LỆNH THẬT, MÃ THOÁT THẬT, LOG MỚI
# ══════════════════════════════════════════════════════════════════════════════════════════════


def bam_bo_kiem(cay):
    """sha256 của những tệp quyết định kết quả — dùng để chứng minh KHÔNG SỬA BỘ KIỂM."""
    return {t: bam_tep(os.path.join(cay, t)) for t in TEP_BO_KIEM}


def bam_cay(cay):
    """Băm NỘI DUNG mọi tệp theo dõi (working tree), để phát hiện cây bị đổi giữa lượt đo.

    `git ls-files -s` chỉ đọc INDEX; nó KHÔNG thấy tệp bị sửa trên đĩa mà chưa `git add`.
    Vì vậy ở đây băm thẳng nội dung tệp — đó mới là thứ bộ kiểm có thể làm hỏng.
    """
    rc, out = git(cay, "ls-files", "-z")
    if rc != 0:
        return {"doc_duoc": False, "rc": rc, "loi": out.strip()[:500], "bam": None,
                "so_tep": None, "thieu": []}
    ten = [t for t in out.split("\0") if t]
    h = hashlib.sha256()
    thieu = []
    for t in sorted(ten):
        p = os.path.join(cay, t)
        b = bam_tep(p) if os.path.isfile(p) else None
        if b is None:
            thieu.append(t)
        h.update(t.encode("utf-8", "surrogateescape"))
        h.update(b"\0")
        h.update((b or "THIEU").encode())
        h.update(b"\0")
    return {"doc_duoc": True, "rc": 0, "bam": h.hexdigest(), "so_tep": len(ten),
            "thieu": thieu}


def so_sanh_bam_cay(truoc, sau):
    """→ danh sách tên tệp đổi nội dung/mất (chỉ khi cả hai đều đọc được)."""
    if not (truoc.get("doc_duoc") and sau.get("doc_duoc")):
        return None
    if truoc.get("bam") == sau.get("bam"):
        return []
    # Không có danh sách tên trong bam_cay (chỉ có digest tổng); ghi lại digest để đối chiếu.
    return ["<digest đổi: %s → %s>" % (str(truoc.get("bam"))[:16], str(sau.get("bam"))[:16])]


def _tach_status(path):
    rc, out = git(path, "status", "--porcelain", "-uall")
    return rc, [d for d in out.splitlines() if d.strip()]


def chay_mot_ben(nhan, cay, run_dir, che_do, timeout, doi_so_them):
    """Chạy `app/thu/thu_qa_g22.py` THẬT ở `cay`. Trả toàn bộ số đo + bằng chứng không cache."""
    log_dir = os.path.join(run_dir, "log_" + nhan)
    # TMPDIR PHẢI NGẮN: vài bộ thử tạo socket/đường dẫn trong TMPDIR; giới hạn AF_UNIX trên macOS
    # là ~104 ký tự. Thư mục lượt nằm trong repo nên đường dẫn dài — không dùng nó làm TMPDIR.
    tmp_dir = "/tmp/veh-g22-nt-%s-%s" % (os.path.basename(run_dir)[:32], nhan)
    for d in (log_dir, tmp_dir):
        if os.path.exists(d):
            raise SystemExit("TỪ CHỐI: thư mục log/tmp đã tồn tại (không dùng lại kết quả cũ): %s" % d)
        os.makedirs(d, exist_ok=True)

    # Môi trường con: SẠCH các biến điều khiển của bộ kiểm, KHÔNG bật `VIP_G22_DAY_DU`
    # (nó chạy lại `chay_tat_ca.sh` 11 phút và đọc một log có sẵn — không phải phép đo này).
    e, ghi_chu_git = moi_truong_git_sach()
    for k in [k for k in e if k.startswith("VIP_G22_")]:
        e.pop(k, None)
    e.update({
        "PYTHONDONTWRITEBYTECODE": "1",   # không sinh/đọc .pyc — bằng chứng không cache
        "PYTHONUNBUFFERED": "1",
        "VIP_G22_CHE_DO": che_do,
        "VIP_G22_LOG": log_dir,           # bộ kiểm ghi log e2e vào đây, thư mục MỚI
        "TMPDIR": tmp_dir,                # nền tạm MỚI cho mọi thư mục con
    })
    e.pop("VIP_G22_DAY_DU", None)
    e.pop("VIP_G22_CHAY_MOI", None)

    lenh = [sys.executable or "python3", BO_KIEM] + list(doi_so_them)
    lenh_hien_thi = ("VIP_G22_CHE_DO=%s VIP_G22_LOG=%s TMPDIR=%s %s %s"
                     % (che_do, log_dir, tmp_dir,
                        os.path.basename(sys.executable or "python3"),
                        " ".join([BO_KIEM] + list(doi_so_them))))

    truoc_bam = bam_cay(cay)
    truoc_bo_kiem = bam_bo_kiem(cay)
    truoc_status = _tach_status(cay)
    truoc_pycache = _liet_ke_pycache(cay)
    log_dir_truoc = sorted(os.listdir(log_dir))
    tmp_dir_truoc = sorted(os.listdir(tmp_dir))

    r = chay(lenh, cwd=cay, env=e, timeout=timeout)
    t_ket_thuc = time.time()

    log_path = os.path.join(run_dir, "chay_%s.log" % nhan)
    ghi_log(log_path, nhan, lenh, lenh_hien_thi, cay, che_do, e, r, t_ket_thuc)

    sau_bam = bam_cay(cay)
    sau_bo_kiem = bam_bo_kiem(cay)
    sau_status = _tach_status(cay)
    sau_pycache = _liet_ke_pycache(cay)

    cho_phep, nhan_cho_phep = doc_ca_chinh(cay)
    pt = phan_tich(r["out"], cho_phep=cho_phep, nhan_cho_phep=nhan_cho_phep,
                   ma_thoat_thuc=r["rc"])
    # Bằng chứng KHÔNG CACHE: mọi tệp trong LOG_DIR/TMPDIR phải được tạo SAU khi lượt chạy bắt
    # đầu; trước khi chạy hai thư mục phải RỖNG; không có `.pyc` mới.
    moc = r["truoc_epoch"] - 2.0
    tep_log = _liet_ke_tep(log_dir, moc)
    tep_tmp = _liet_ke_tep(tmp_dir, moc)
    pycache_moi = [p for p in sau_pycache if p not in set(truoc_pycache)]
    st_log = os.stat(log_path)
    # KHÔNG đòi MỌI tệp trong TMPDIR có mtime mới: vài bộ thử CHÉP tệp nguồn vào nền tạm bằng
    # `shutil.copy2`, nên mtime ĐƯỢC GIỮ NGUYÊN (đo được: 718 tệp, mtime cũ hơn lượt chạy).
    # Bằng chứng không-cache nằm ở chỗ khác: thư mục TMPDIR MỚI + RỖNG trước lượt, và mọi tệp
    # LOG (do bộ kiểm sinh ra) đều có mtime ≥ bắt đầu. Ghi cả hai để người đọc tự kiểm.
    tmp_giu_mtime_cu = [x for x in tep_tmp if x["mtime_epoch"] < moc]
    khong_cache = {
        "log_dir_la_moi": (log_dir_truoc == []),
        "tmp_dir_la_moi": (tmp_dir_truoc == []),
        "log_dir_truoc": log_dir_truoc,
        "tmp_dir_truoc": tmp_dir_truoc,
        "so_tep_log": len(tep_log),
        "so_tep_tmp": len(tep_tmp),
        "tep_log_tao_sau_khi_bat_dau": tep_log,
        # TMPDIR chỉ lưu MẪU; danh sách đầy đủ 700+ tệp làm JSON phình mà không thêm bằng chứng.
        "tep_tmp_mau": tep_tmp[:10],
        "so_tep_tmp_giu_mtime_cu": len(tmp_giu_mtime_cu),
        "tat_ca_log_moi": all(x["mtime_epoch"] >= moc for x in tep_log),
        "pycache_moi": pycache_moi,
        "PYTHONDONTWRITEBYTECODE": "1",
        "VIP_G22_DAY_DU": "KHÔNG bật (không đọc lại log `chay_tat_ca.sh`)",
        "log_bo_kiem": {"duong_dan": log_path, "bytes": st_log.st_size,
                        "mtime_utc": luc_utc(st_log.st_mtime), "sha256": bam_tep(log_path)},
        "ghi_chu_git": ghi_chu_git,
    }
    khong_cache["dat"] = bool(khong_cache["log_dir_la_moi"] and khong_cache["tmp_dir_la_moi"]
                              and khong_cache["tat_ca_log_moi"]
                              and not pycache_moi)

    return {
        "nhan": nhan,
        "cay": os.path.abspath(cay),
        "lenh": lenh,
        "lenh_hien_thi": lenh_hien_thi,
        "cwd": os.path.abspath(cay),
        "che_do": che_do,
        "doi_so_them": list(doi_so_them),
        "bat_dau_utc": r["bat_dau_utc"],
        "ket_thuc_utc": luc_utc(t_ket_thuc),
        "giay": r["giay"],
        "exit": r["rc"],
        "het_gio": r["het_gio"],
        "log": khong_cache["log_bo_kiem"],
        "phan_tich": pt,
        "ca": pt["ca"],
        "dong_do": pt["dong_do"],
        "canh_bao": pt["canh_bao"],
        "van_tay_truoc": truoc_bam,
        "van_tay_sau": sau_bam,
        "tep_doi_giua_luot": so_sanh_bam_cay(truoc_bam, sau_bam),
        "bo_kiem_sha_truoc": truoc_bo_kiem,
        "bo_kiem_sha_sau": sau_bo_kiem,
        "bo_kiem_bi_doi": [t for t in TEP_BO_KIEM
                           if truoc_bo_kiem.get(t) != sau_bo_kiem.get(t)],
        "status_truoc": truoc_status[1],
        "status_sau": sau_status[1],
        "status_rc": sau_status[0],
        "khong_cache": khong_cache,
    }


def _liet_ke_pycache(cay):
    ds = []
    for goc, thu_muc, tep in os.walk(cay):
        if ".git" in goc or "node_modules" in goc:
            continue
        if os.path.basename(goc) == "__pycache__":
            ds.extend(os.path.join(goc, t) for t in tep)
    return sorted(ds)


def _liet_ke_tep(goc, moc_epoch):
    ds = []
    for g, thu_muc, tep in os.walk(goc):
        for t in tep:
            p = os.path.join(g, t)
            try:
                st = os.stat(p)
            except OSError:
                continue
            ds.append({"duong_dan": p, "bytes": st.st_size,
                       "mtime_epoch": st.st_mtime, "mtime_utc": luc_utc(st.st_mtime),
                       "sha256": bam_tep(p)})
    return sorted(ds, key=lambda x: x["duong_dan"])


def ghi_log(path, nhan, lenh, lenh_hien_thi, cay, che_do, env, r, t_ket_thuc):
    with open(path, "w", encoding="utf-8") as f:
        f.write("# %s\n" % ("=" * 100))
        f.write("# BỘ ĐO NGHIỆM THU G22 (AG-05) — BÊN: %s\n" % nhan)
        f.write("# %s\n" % ("=" * 100))
        f.write("# LỆNH THẬT (argv): %r\n" % (lenh,))
        f.write("# HIỂN THỊ       : %s\n" % lenh_hien_thi)
        f.write("# CWD            : %s\n" % os.path.abspath(cay))
        f.write("# CHẾ ĐỘ         : %s\n" % che_do)
        f.write("# BẮT ĐẦU        : %s\n" % r["bat_dau_utc"])
        f.write("# GIT_CONFIG     : %s\n" % (moi_truong_git_sach()[1] or "nguyên bản (không gỡ)"))
        f.write("# BIẾN ĐÃ ĐẶT    : VIP_G22_CHE_DO=%s · VIP_G22_LOG=%s · TMPDIR=%s · "
                "PYTHONDONTWRITEBYTECODE=1\n"
                % (env["VIP_G22_CHE_DO"], env["VIP_G22_LOG"], env["TMPDIR"]))
        f.write("# GHI CHÚ        : KHÔNG bật VIP_G22_DAY_DU · KHÔNG dùng lại log/kết quả cũ\n")
        f.write("# %s\n\n" % ("-" * 100))
        f.write(r["out"])
        if not r["out"].endswith("\n"):
            f.write("\n")
        f.write("\n# %s\n" % ("-" * 100))
        f.write("# KẾT THÚC       : %s\n" % luc_utc(t_ket_thuc))
        f.write("# MÃ THOÁT (đọc NGAY sau lệnh, không qua ống): %r\n" % (r["rc"],))
        f.write("# HẾT GIỜ        : %s\n" % r["het_gio"])
        f.write("# THỜI GIAN      : %.3fs\n" % r["giay"])
        f.write("# %s\n" % ("=" * 100))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. PHÂN TÍCH OUTPUT CỦA BỘ KIỂM — `Ran N`, PASS/FAIL/ERROR/SKIP, TỪNG CA, TỪNG DÒNG ĐO
# ══════════════════════════════════════════════════════════════════════════════════════════════

TEN_CA = re.compile(r"^(test_[A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\)$")
# Ca có output trước khi kết thúc: unittest in tên ca rồi ` ... ` trên CÙNG dòng, trạng thái
# (`ok`/`FAIL`) in thành một dòng RIÊNG sau output. Thiếu mẫu này thì bộ đọc bỏ mất ca.
TEN_CA_MO = re.compile(r"^(test_[A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\) \.\.\.\s*$")
TEN_CA_CUNG = re.compile(
    r"^(test_[A-Za-z0-9_]+) \(([A-Za-z0-9_.]+)\) \.\.\. (ok|FAIL|ERROR|skipped(?:[ ].*)?)$")
TRANG_THAI = re.compile(r"[ ]\.\.\. (ok|FAIL|ERROR|skipped(?:[ ].*)?)$")
RAN = re.compile(r"^Ran (\d+) tests? in ([\d.]+)s$")
TONG_KET = re.compile(r"^(OK|FAILED)(?: \(([^)]*)\))?$")
DONG_DO = re.compile(r"^\s{0,12}\[([A-Z][A-Z0-9_]*\d*)\]\s*(.*)$")
# Dòng tự tổng kết của CHÍNH bộ kiểm (in ở cuối, sau bảng vân tay): đối chứng độc lập với
# `Ran` của unittest và với mã thoát ta đọc được.
CA_CUOI = re.compile(r"^    ca: (\d+) · hỏng/loi: (\d+) · bỏ qua: (\d+) · MÃ THOÁT = (\d+)$")


def doc_ca_chinh(cay):
    """Đọc CHÍNH tệp bộ kiểm để biết nó có những lớp/ca nào và in những nhãn đo nào.

    Output của bộ kiểm CÓ LẪN output của các bộ thử con (E2 chạy `thu_qa_g19.py`, D1 chạy
    `thu_qa_g20.py`, Z5 chạy lại chính bộ kiểm...). Không có bộ lọc này thì bộ đọc sẽ nhặt
    `Ran 29` của bộ CON làm số ca của bộ CHÍNH — đúng lỗi đã xảy ra ở lượt chạy đầu.
    """
    try:
        src = open(os.path.join(cay, BO_KIEM), encoding="utf-8").read()
    except OSError:
        return None, None
    cho_phep, lop = set(), None
    for d in src.splitlines():
        m = re.match(r"^class (\w+)\(unittest\.TestCase\):", d)
        if m:
            lop = m.group(1)
            continue
        m = re.match(r"^    def (test_\w+)\(", d)
        if m and lop:
            cho_phep.add("%s.%s" % (lop, m.group(1)))
    nhan = set(re.findall(r"\[([A-Z][A-Z0-9_]*\d*)\]", src))
    return cho_phep, nhan


def phan_tich(van_ban, cho_phep=None, nhan_cho_phep=None, ma_thoat_thuc=None):
    """Đọc output `unittest -v` + các dòng đo của bộ kiểm. KHÔNG suy diễn chỗ không có số.

    `cho_phep` / `nhan_cho_phep`: lọc output của bộ CON (xem `doc_ca_chinh`). Tổng kết dùng
    dòng `Ran N tests` CUỐI CÙNG trong log — đó là dòng của bộ CHÍNH; các dòng trước là của
    bộ con (hoặc nằm trong thông điệp lỗi).
    """
    dong = van_ban.splitlines()
    vi_tri_ran = None
    for k, d in enumerate(dong):
        if RAN.match(d.strip()):
            vi_tri_ran = k
    ran, giay = None, None
    if vi_tri_ran is not None:
        m = RAN.match(dong[vi_tri_ran].strip())
        ran, giay = int(m.group(1)), float(m.group(2))
    khoi = dong[:vi_tri_ran] if vi_tri_ran is not None else dong

    ca = {}
    i = 0
    while i < len(khoi):
        m = TEN_CA_CUNG.match(khoi[i])
        if m:
            khoa = _khoa_ca(m.group(2), m.group(1))
            if (cho_phep is None or khoa in cho_phep) and khoa not in ca:
                ca[khoa] = _chuan_trang_thai(m.group(3))
            i += 1
            continue
        m = TEN_CA.match(khoi[i]) or TEN_CA_MO.match(khoi[i])
        if m:
            j, trang_thai = i + 1, None
            while j < len(khoi) and j < i + 80:
                # unittest in trạng thái ở CUỐI dòng (`... ok`) hoặc thành MỘT dòng riêng (`ok`)
                # khi ca có output trước khi kết thúc. Cả hai dạng đều phải đọc được.
                s = khoi[j].rstrip()
                mm = re.search(r" \.\.\. (ok|FAIL|ERROR|skipped(?:[ ].*)?)$", s)
                if mm:
                    trang_thai = mm.group(1)
                    break
                if s.strip() in ("ok", "FAIL", "ERROR"):
                    trang_thai = s.strip()
                    break
                if s.strip().startswith("skipped "):
                    trang_thai = s.strip()
                    break
                if (TEN_CA.match(khoi[j]) or TEN_CA_MO.match(khoi[j])
                        or TEN_CA_CUNG.match(khoi[j])):
                    break
                j += 1
            if trang_thai:
                khoa = _khoa_ca(m.group(2), m.group(1))
                if (cho_phep is None or khoa in cho_phep) and khoa not in ca:
                    ca[khoa] = _chuan_trang_thai(trang_thai)
                i = j + 1
                continue
        i += 1

    tong_ket, thong_ke = None, {}
    for k in range(max(0, (vi_tri_ran or 0) - 1), min(len(dong), (vi_tri_ran or 0) + 8)):
        m = TONG_KET.match(dong[k].strip())
        if m:
            tong_ket = dong[k].strip()
            if m.group(2):
                for phan in m.group(2).split(","):
                    if "=" in phan:
                        ten, so = phan.split("=", 1)
                        if so.strip().isdigit():
                            thong_ke[ten.strip()] = int(so.strip())
            break

    # Dòng tự tổng kết của chính bộ kiểm — đọc để ĐỐI CHIẾU, không thay thế số của unittest.
    ca_cuoi = None
    for d in dong:
        m = CA_CUOI.match(d)
        if m:
            ca_cuoi = {"ca": int(m.group(1)), "hong_loi": int(m.group(2)),
                       "bo_qua": int(m.group(3)), "ma_thoat_tu_bao": int(m.group(4))}

    dem = {"PASS": 0, "FAIL": 0, "ERROR": 0, "SKIP": 0}
    for tt in ca.values():
        dem[tt] += 1
    so_fail = thong_ke.get("failures", dem["FAIL"])
    so_error = thong_ke.get("errors", dem["ERROR"])
    so_skip = thong_ke.get("skipped", dem["SKIP"])
    pass_tinh = (ran - so_fail - so_error - so_skip) if ran is not None else None

    dong_do = {}
    for d in khoi:
        m = DONG_DO.match(d)
        if m and (nhan_cho_phep is None or m.group(1) in nhan_cho_phep):
            dong_do.setdefault(m.group(1), []).append(d.strip())

    canh_bao = []
    if ran is None:
        canh_bao.append("KHÔNG thấy dòng `Ran N tests` — không đọc được số ca.")
    if tong_ket is None:
        canh_bao.append("KHÔNG thấy dòng tổng kết `OK`/`FAILED`.")
    if ran is not None and dem["PASS"] + dem["FAIL"] + dem["ERROR"] + dem["SKIP"] != ran:
        canh_bao.append("SỐ CA theo dòng `Ran`=%d ≠ số ca đọc được từ output=%d "
                        "(PASS=%d FAIL=%d ERROR=%d SKIP=%d)."
                        % (ran, sum(dem.values()), dem["PASS"], dem["FAIL"],
                           dem["ERROR"], dem["SKIP"]))
    for ten, so in (("FAIL", so_fail), ("ERROR", so_error), ("SKIP", so_skip)):
        if dem[ten] != so:
            canh_bao.append("Số %s theo tổng kết=%d ≠ đếm từng ca=%d." % (ten, so, dem[ten]))
    if ca_cuoi is None:
        canh_bao.append("KHÔNG thấy dòng tự tổng kết `ca: N · hỏng/loi: … · MÃ THOÁT = …` "
                        "của bộ kiểm.")
    else:
        if ran is not None and ca_cuoi["ca"] != ran:
            canh_bao.append("Bộ kiểm tự báo %d ca ≠ `Ran`=%d." % (ca_cuoi["ca"], ran))
        if ca_cuoi["hong_loi"] != so_fail + so_error:
            canh_bao.append("Bộ kiểm tự báo hỏng/lỗi=%d ≠ failures+errors=%d."
                            % (ca_cuoi["hong_loi"], so_fail + so_error))
        if ca_cuoi["bo_qua"] != so_skip:
            canh_bao.append("Bộ kiểm tự báo bỏ qua=%d ≠ skipped=%d."
                            % (ca_cuoi["bo_qua"], so_skip))
        if ma_thoat_thuc is not None and ca_cuoi["ma_thoat_tu_bao"] != ma_thoat_thuc:
            canh_bao.append("Bộ kiểm tự báo MÃ THOÁT=%r ≠ mã thoát ta đọc được=%r."
                            % (ca_cuoi["ma_thoat_tu_bao"], ma_thoat_thuc))
    return {
        "ran": ran, "giay": giay, "tong_ket": tong_ket, "thong_ke": thong_ke,
        "pass": pass_tinh, "fail": so_fail, "error": so_error, "skip": so_skip,
        "dem_theo_ca": dem, "ca": ca, "dong_do": dong_do, "canh_bao": canh_bao,
        "tu_tong_ket": ca_cuoi,
    }


def _khoa_ca(lop, ten):
    lop = lop.split(".")[-1]
    return "%s.%s" % (lop, ten)


def _chuan_trang_thai(s):
    s = s.strip()
    if s.startswith("ok"):
        return "PASS"
    if s.startswith("FAIL"):
        return "FAIL"
    if s.startswith("ERROR"):
        return "ERROR"
    if s.startswith("skipped"):
        return "SKIP"
    return "KHAC(%s)" % s


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. SO SÁNH HAI BÊN — CHỈ IN CÁI ĐO ĐƯỢC, KHÔNG TÔ MÀU
# ══════════════════════════════════════════════════════════════════════════════════════════════


def chuan_hoa_dong(d, cay, log_dir, run_dir):
    """Bỏ khác biệt KHÔNG mang nghĩa sản phẩm: đường dẫn, cổng, PID, giây, mốc thời gian."""
    # VÁ (AG-00): `abspath` KHÔNG giải symlink. Trên macOS `/var` -> `/private/var`, nên với bản sao
    # trong TMP thì chuỗi trong log có tiền tố `/private` mà `abspath(cay)` không có ⇒ thay thế trượt
    # ⇒ sinh ra một dòng "lệch" CHỈ VÌ ĐƯỜNG DẪN, và bộ đo trả 1 dù hai bên khớp hoàn toàn.
    # Dùng `realpath` để giải symlink. Đo được: trước vá `[H1] ... (/private<CAY>)`, sau vá `(<CAY>)`.
    for p, th in ((os.path.realpath(run_dir), "<LƯỢT>"), (os.path.realpath(cay), "<CAY>"),
                  (log_dir, "<LOG>")):
        if p:
            d = d.replace(p, th)
    d = re.sub(r"/private/var/folders/[^\s'\"()]+", "<TMP>", d)
    d = re.sub(r"/var/folders/[^\s'\"()]+", "<TMP>", d)
    d = re.sub(r"/tmp/veh[-_A-Za-z0-9./]*", "<TMP>", d)
    d = re.sub(r"127\.0\.0\.1:\d+", "127.0.0.1:<CỔNG>", d)
    d = re.sub(r"\b\d+\.\d+s\b", "<GIÂY>s", d)
    d = re.sub(r"\bpid[= ]\d+", "pid=<PID>", d)
    d = re.sub(r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:[+\-]\d{2}:\d{2})?\b", "<LÚC>", d)
    d = re.sub(r"\s+", " ", d).strip()
    return d


def so_sanh(ben_a, ben_b, cay_a, cay_b, run_dir):
    """So sánh hai bên. Trả dict `khac` + danh sách ca lệch + danh sách dòng đo lệch."""
    khac = {}
    for khoa, ten in (("ran", "SỐ CA (`Ran`)"), ("pass", "PASS"), ("fail", "FAIL"),
                      ("error", "ERROR"), ("skip", "SKIP"), ("tu_tong_ket", "BỘ KIỂM TỰ BÁO")):
        a, b = ben_a["phan_tich"].get(khoa), ben_b["phan_tich"].get(khoa)
        khac[khoa] = {"ten": ten, "worktree": a, "ban_sao": b, "khop": a == b}
    # `exit` nằm ở cấp ngoài của mỗi bên (mã thoát THẬT của tiến trình), không nằm trong
    # `phan_tich` — lấy đúng chỗ, nếu không phép so sánh "mã thoát" sẽ so None với None.
    khac["exit"] = {"ten": "MÃ THOÁT BỘ KIỂM", "worktree": ben_a["exit"],
                    "ban_sao": ben_b["exit"], "khop": ben_a["exit"] == ben_b["exit"]}

    ca_a, ca_b = ben_a["ca"], ben_b["ca"]
    chi_a = sorted(set(ca_a) - set(ca_b))
    chi_b = sorted(set(ca_b) - set(ca_a))
    lech = [{"ca": k, "worktree": ca_a.get(k, "KHÔNG CÓ"), "ban_sao": ca_b.get(k, "KHÔNG CÓ")}
            for k in sorted(set(ca_a) | set(ca_b)) if ca_a.get(k) != ca_b.get(k)]

    dong_a, dong_b = ben_a["dong_do"], ben_b["dong_do"]
    nhan = sorted(set(dong_a) | set(dong_b))
    lech_dong = []
    for n in nhan:
        a = [chuan_hoa_dong(x, cay_a, ben_a["khong_cache"]["log_bo_kiem"]["duong_dan"], run_dir)
             for x in dong_a.get(n, [])]
        b = [chuan_hoa_dong(x, cay_b, ben_b["khong_cache"]["log_bo_kiem"]["duong_dan"], run_dir)
             for x in dong_b.get(n, [])]
        if a != b:
            lech_dong.append({"nhan": n, "worktree": a or ["(không có)"],
                              "ban_sao": b or ["(không có)"]})

    return {
        "khac": khac,
        "ca_chi_co_worktree": chi_a,
        "ca_chi_co_ban_sao": chi_b,
        "ca_lech": lech,
        "dong_do_lech": lech_dong,
        "tat_ca_khop": (all(x["khop"] for x in khac.values())
                        and not lech and not chi_a and not chi_b and not lech_dong),
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. IN BẢNG + GHI BẰNG CHỨNG
# ══════════════════════════════════════════════════════════════════════════════════════════════


class Ghi:
    def __init__(self):
        self.dong = []

    def __call__(self, s=""):
        print(s)
        self.dong.append(s)


def xep_bang(ghi, tieu_de, cot, dong):
    ghi(tieu_de)
    ghi("| " + " | ".join(cot) + " |")
    ghi("|" + "|".join(["---"] * len(cot)) + "|")
    for d in dong:
        ghi("| " + " | ".join(str(x) for x in d) + " |")
    ghi("")


def xep_bang_so(ghi, ben_a, ben_b, ten_a, ten_b):
    pa, pb = ben_a["phan_tich"], ben_b["phan_tich"]

    def tt(x):
        return "%s" % (x,)
    xep_bang(
        ghi,
        "## 1. BẢNG SỐ SÁNH (số đo THẬT, mỗi bên một lượt chạy mới)",
        ["chỉ tiêu", ten_a, ten_b, "khớp"],
        [
            ["lệnh", ben_a["lenh_hien_thi"], ben_b["lenh_hien_thi"], "CÓ" if ben_a["lenh"] == ben_b["lenh"] else "KHÔNG"],
            ["cwd", ben_a["cwd"], ben_b["cwd"], "KHÁC (đúng thiết kế)"],
            ["mã thoát bộ kiểm", tt(ben_a["exit"]), tt(ben_b["exit"]), "CÓ" if ben_a["exit"] == ben_b["exit"] else "KHÔNG"],
            ["thời gian", "%.1fs" % ben_a["giay"], "%.1fs" % ben_b["giay"], "—"],
            ["`Ran N`", tt(pa["ran"]), tt(pb["ran"]), "CÓ" if pa["ran"] == pb["ran"] else "KHÔNG"],
            ["PASS", tt(pa["pass"]), tt(pb["pass"]), "CÓ" if pa["pass"] == pb["pass"] else "KHÔNG"],
            ["FAIL", tt(pa["fail"]), tt(pb["fail"]), "CÓ" if pa["fail"] == pb["fail"] else "KHÔNG"],
            ["ERROR", tt(pa["error"]), tt(pb["error"]), "CÓ" if pa["error"] == pb["error"] else "KHÔNG"],
            ["SKIP", tt(pa["skip"]), tt(pb["skip"]), "CÓ" if pa["skip"] == pb["skip"] else "KHÔNG"],
            ["dòng tổng kết", pa["tong_ket"] or "KHÔNG THẤY", pb["tong_ket"] or "KHÔNG THẤY", "—"],
            ["bộ kiểm TỰ BÁO (ca/hỏng-lỗi/bỏ qua/mã thoát)",
             pa.get("tu_tong_ket") or "KHÔNG THẤY", pb.get("tu_tong_ket") or "KHÔNG THẤY",
             "CÓ" if pa.get("tu_tong_ket") == pb.get("tu_tong_ket") else "KHÔNG"],
            ["log", ben_a["log"]["duong_dan"], ben_b["log"]["duong_dan"], "—"],
            ["sha256 log", (ben_a["log"]["sha256"] or "")[:16], (ben_b["log"]["sha256"] or "")[:16], "—"],
        ])


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 7. MAIN
# ══════════════════════════════════════════════════════════════════════════════════════════════


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Đo nghiệm thu G22 trên BẢN SAO SẠCH và đối chiếu với worktree.")
    ap.add_argument("--commit", default="HEAD",
                    help="commit/nhãn cần đo (mặc định HEAD; luôn in SHA THẬT đã phân giải)")
    ap.add_argument("--dest", default=None,
                    help="thư mục đích của bản sao sạch (mặc định /tmp/veh_g22_nghiem_thu/<lượt>/ban_sao)")
    ap.add_argument("--mode", choices=("clone", "archive"), default="clone",
                    help="clone = git clone --shared + checkout --detach (ĐO ĐƯỢC cổng git); "
                         "archive = git archive, KHÔNG có .git (chỉ đo nội dung)")
    ap.add_argument("--kho", default=GOC_REPO, help="kho nguồn (mặc định: repo chứa script)")
    ap.add_argument("--che-do", choices=("nen", "gop"), default="gop",
                    help="VIP_G22_CHE_DO truyền cho bộ kiểm (mặc định gop = nghiệm thu)")
    ap.add_argument("--node-modules", default=None,
                    help="node_modules cấp cho bản sao (mặc định: node_modules của worktree nguồn; "
                         "cả hai bên dùng CÙNG một cây phụ thuộc)")
    ap.add_argument("--khong-lien-ket-node-modules", action="store_true",
                    help="không symlink node_modules vào bản sao (e2e sẽ không chạy được — có ghi)")
    ap.add_argument("--chi-mot-ben", action="store_true",
                    help="CHẨN ĐOÁN: chỉ chạy bên bản sao, không chạy worktree/không so sánh")
    ap.add_argument("--doi-so-them", nargs=argparse.REMAINDER, default=[],
                    help="CHẨN ĐOÁN: đối số thêm cho bộ kiểm (vd: A_Nen). Không dùng cho nghiệm thu.")
    ap.add_argument("--timeout-giay", type=int, default=2700,
                    help="hết giờ cho MỖI bên (mặc định 2700s)")
    ap.add_argument("--nhan", default="", help="nhãn ngắn cho lượt đo (ghi vào tên thư mục)")
    ap.add_argument("--json", default=None, help="đường dẫn JSON kết quả (mặc định trong thư mục lượt)")
    a = ap.parse_args(argv)

    luc_bat_dau = time.time()
    run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    if a.nhan:
        run_id += "-" + re.sub(r"[^A-Za-z0-9_.-]+", "_", a.nhan)[:40]
    run_dir = os.path.join(THU_MUC_KQ, run_id)
    os.makedirs(run_dir, exist_ok=False)   # KHÔNG dùng lại thư mục lượt cũ

    dest = a.dest or os.path.join(GOC_TMP_MAC_DINH, run_id, "ban_sao")
    dest = os.path.abspath(dest)
    if os.path.exists(dest):
        raise SystemExit("TỪ CHỐI: --dest đã tồn tại, không ghi đè: %s" % dest)

    ghi = Ghi()
    ket_qua = {
        "bo_do": "nghiem_thu_ban_sao.py (AG-05 G22)",
        "phien_ban": "1.0",
        "run_id": run_id,
        "luc_bat_dau_utc": luc_utc(luc_bat_dau),
        "may": {"platform": platform.platform(), "python": sys.version.split()[0],
                "python_executable": sys.executable, "hostname": socket.gethostname(),
                "cwd": os.getcwd()},
        "tham_so": {"commit": a.commit, "dest": dest, "mode": a.mode, "kho": os.path.abspath(a.kho),
                    "che_do": a.che_do, "node_modules": a.node_modules,
                    "khong_lien_ket_node_modules": a.khong_lien_ket_node_modules,
                    "chi_mot_ben": a.chi_mot_ben, "doi_so_them": a.doi_so_them,
                    "timeout_giay": a.timeout_giay},
    }

    ghi("#" * 104)
    ghi("# BỘ ĐO NGHIỆM THU G22 — BẢN SAO SẠCH (AG-05) · lượt %s" % run_id)
    ghi("# MỤC ĐÍCH: đo bộ kiểm G22 trên một bản sao sạch TỪ COMMIT, rồi so với worktree.")
    ghi("# ĐÂY LÀ DỤNG CỤ ĐO. Mã thoát 0 KHÔNG có nghĩa là sản phẩm ĐẠT.")
    ghi("#" * 104)
    ghi("")

    # ── 0. Môi trường + trạng thái nguồn TRƯỚC khi dựng bản sao ────────────────────────────────
    env_ok, ghi_chu_git = moi_truong_git_sach()
    rc_h, out_h = git(GOC_REPO, "rev-parse", "HEAD")
    rc_s, out_s = git(GOC_REPO, "status", "--porcelain", "-uall")
    status_nguon = [d for d in out_s.splitlines() if d.strip()] if rc_s == 0 else []
    van_tay_dot_git = van_tay_git_dir(GOC_REPO)
    sha_yeu_cau, tree_goc, _ = giai_commit(a.kho, a.commit)
    so_tep_nguon, loi_tep = dem_tep_git(a.kho, sha_yeu_cau)
    ket_qua["nguon"] = {
        "kho": os.path.abspath(a.kho), "head": out_h.strip() if rc_h == 0 else "LỖI(rc=%d)" % rc_h,
        "status_truoc": status_nguon,
        "commit_yeu_cau": a.commit, "commit_thuc": sha_yeu_cau, "tree_commit": tree_goc,
        "so_tep_theo_git": so_tep_nguon, "loi_dem_tep": loi_tep,
        "van_tay_dot_git_truoc": van_tay_dot_git,
        "ghi_chu_git": ghi_chu_git,
    }
    ghi("## 0. NGUỒN VÀ MÔI TRƯỜNG")
    ghi("")
    ghi("```")
    ghi("kho nguồn            : %s" % a.kho)
    ghi("HEAD worktree        : %s" % (out_h.strip() if rc_h == 0 else "KHÔNG ĐỌC ĐƯỢC rc=%d" % rc_h))
    ghi("commit yêu cầu      : %s" % a.commit)
    ghi("commit THẬT (SHA)    : %s" % sha_yeu_cau)
    ghi("tree của commit      : %s" % tree_goc)
    ghi("số tệp theo git      : %s" % so_tep_nguon)
    ghi("status worktree      : %s" % (("%d đường" % len(status_nguon)) if status_nguon else "SẠCH"))
    for d in status_nguon[:20]:
        ghi("                       %s" % d)
    ghi("môi trường git       : %s" % (ghi_chu_git or "nguyên bản (không phải gỡ biến)"))
    ghi("python               : %s (%s)" % (sys.version.split()[0], sys.executable))
    ghi("máy                  : %s" % platform.platform())
    ghi("```")
    ghi("")

    # ── 1. Dựng bản sao sạch ────────────────────────────────────────────────────────────────────
    ghi("## 1. DỰNG BẢN SAO SẠCH (mode=%s)" % a.mode)
    ghi("")
    tt_tao = tao_ban_sao(os.path.abspath(a.kho), sha_yeu_cau, dest, a.mode)
    tt_kiem = kiem_ban_sao(os.path.abspath(a.kho), sha_yeu_cau, tree_goc, dest, a.mode)
    ket_qua["ban_sao"] = {"tao": tt_tao, "kiem": tt_kiem}

    # node_modules: cả hai bên phải dùng CÙNG một cây phụ thuộc, nếu không phép so sánh e2e
    # sẽ so hai môi trường khác nhau và gọi đó là "lệch sản phẩm".
    nm_nguon = a.node_modules or os.path.join(GOC_REPO, "node_modules")
    nm_nguon = os.path.abspath(nm_nguon)
    nm_ban_sao = os.path.join(dest, "node_modules")
    lien_ket_nm = False
    if not a.khong_lien_ket_node_modules and os.path.isdir(nm_nguon) and not os.path.exists(nm_ban_sao):
        os.symlink(nm_nguon, nm_ban_sao)
        lien_ket_nm = True
    co_browser_nguon = os.path.exists(
        os.path.join(nm_nguon, "playwright-core", ".local-browsers"))
    ket_qua["cap_phat"] = {
        "node_modules_nguon": nm_nguon,
        "node_modules_ban_sao": nm_ban_sao,
        "lien_ket": lien_ket_nm,
        "co_local_browsers": co_browser_nguon,
        "co_playwright_test": os.path.isdir(os.path.join(nm_nguon, "@playwright", "test")),
    }

    ghi("```")
    for b in tt_tao["cac_buoc"]:
        ghi("$ %s" % " ".join(b["lenh"]))
        ghi("  mã thoát = %r · %.2fs" % (b["rc"], b["giay"]))
    ghi("bản sao              : %s" % dest)
    ghi("HEAD bản sao         : %s" % tt_kiem.get("head", "—"))
    ghi("write-tree bản sao   : %s" % tt_kiem.get("tree", "—"))
    ghi("tree commit nguồn    : %s" % tree_goc)
    ghi("HEAD == commit?      : %s" % tt_kiem.get("head_dung", "— (mode archive không có git)"))
    ghi("tree == tree nguồn?  : %s" % tt_kiem.get("tree_dung", "— (mode archive không có git)"))
    ghi("status bản sao       : %s" % ("RỖNG (sạch)" if tt_kiem.get("status_sach")
                                       else (tt_kiem.get("status") or "—")))
    ghi("node_modules         : %s → %s (lien_ket=%s)"
        % (nm_ban_sao, nm_nguon, lien_ket_nm))
    ghi("có .local-browsers   : %s (nếu KHÔNG: e2e Chromium không đo được, xem tài liệu)"
        % co_browser_nguon)
    ghi("```")
    ghi("")
    if tt_kiem.get("mode") == "clone" and not (tt_kiem.get("head_dung") and tt_kiem.get("tree_dung")
                                               and tt_kiem.get("status_sach")):
        ghi("⛔ BẢN SAO KHÔNG SẠCH/ KHÔNG ĐÚNG COMMIT — DỪNG, không đo tiếp.")
        ket_qua["ket_luan"] = {"ma_thoat": 2, "ly_do": "bản sao không sạch hoặc sai commit/tree"}
        json_ghi(os.path.join(run_dir, "KET_QUA.json"), ket_qua)
        return 2

    # ── 2. Chạy bộ kiểm ở hai bên ──────────────────────────────────────────────────────────────
    ben_worktree = None
    if not a.chi_mot_ben:
        ghi("## 2A. CHẠY BỘ KIỂM TRONG WORKTREE (đối chứng — KHÔNG phải bản sạch)")
        ghi("")
        ben_worktree = chay_mot_ben("worktree", GOC_REPO, run_dir, a.che_do,
                                    a.timeout_giay, a.doi_so_them)
        ghi("```")
        ghi("lệnh                : %s" % ben_worktree["lenh_hien_thi"])
        ghi("mã thoát THẬT       : %r" % ben_worktree["exit"])
        ghi("Ran                 : %r" % ben_worktree["phan_tich"]["ran"])
        ghi("PASS/FAIL/ERROR/SKIP: %r / %r / %r / %r"
            % (ben_worktree["phan_tich"]["pass"], ben_worktree["phan_tich"]["fail"],
               ben_worktree["phan_tich"]["error"], ben_worktree["phan_tich"]["skip"]))
        ghi("log                 : %s" % ben_worktree["log"]["duong_dan"])
        ghi("không cache         : %s" % ("ĐẠT" if ben_worktree["khong_cache"]["dat"] else "KHÔNG"))
        ghi("```")
        ghi("")

    ghi("## 2B. CHẠY BỘ KIỂM TRONG BẢN SAO SẠCH")
    ghi("")
    ben_ban_sao = chay_mot_ben("ban_sao", dest, run_dir, a.che_do,
                               a.timeout_giay, a.doi_so_them)
    ghi("```")
    ghi("lệnh                : %s" % ben_ban_sao["lenh_hien_thi"])
    ghi("mã thoát THẬT       : %r" % ben_ban_sao["exit"])
    ghi("Ran                 : %r" % ben_ban_sao["phan_tich"]["ran"])
    ghi("PASS/FAIL/ERROR/SKIP: %r / %r / %r / %r"
        % (ben_ban_sao["phan_tich"]["pass"], ben_ban_sao["phan_tich"]["fail"],
           ben_ban_sao["phan_tich"]["error"], ben_ban_sao["phan_tich"]["skip"]))
    ghi("log                 : %s" % ben_ban_sao["log"]["duong_dan"])
    ghi("không cache         : %s" % ("ĐẠT" if ben_ban_sao["khong_cache"]["dat"] else "KHÔNG"))
    ghi("```")
    ghi("")

    ket_qua["worktree"] = ben_worktree
    ket_qua["ban_sao_do"] = ben_ban_sao

    # Vân tay `.git` nguồn SAU lượt — phải chụp TRƯỚC khi in mục "ĐIỀU KIỆN SO SÁNH", nếu không
    # cờ còn None lúc in và tài liệu sẽ buộc tội chính bộ đo (đã xảy ra ở lượt `full-04`).
    vt_git_sau = van_tay_git_dir(GOC_REPO)
    ket_qua["nguon"]["van_tay_dot_git_sau"] = vt_git_sau
    ket_qua["nguon"]["dot_git_khong_doi"] = (vt_git_sau == van_tay_dot_git)

    # ── 3. Bằng chứng không cache ──────────────────────────────────────────────────────────────
    ghi("## 3. CÁCH XÁC NHẬN **KHÔNG DÙNG KẾT QUẢ CACHE** (đo, không khai)")
    ghi("")
    ghi("```")
    for nhan, ben in (("worktree", ben_worktree), ("bản sao", ben_ban_sao)):
        if ben is None:
            continue
        kc = ben["khong_cache"]
        ghi("[%s]" % nhan)
        ghi("  thư mục VIP_G22_LOG trước lượt : %s đường (BẮT BUỘC rỗng)"
            % len(kc["log_dir_truoc"]))
        ghi("  thư mục TMPDIR trước lượt      : %s đường (BẮT BUỘC rỗng)"
            % len(kc["tmp_dir_truoc"]))
        ghi("  tệp LOG sinh trong lượt         : %d · tệp TMPDIR: %d"
            % (kc["so_tep_log"], kc["so_tep_tmp"]))
        ghi("  MỌI tệp LOG mới (mtime ≥ bắt đầu): %s" % kc["tat_ca_log_moi"])
        ghi("  tệp TMP giữ mtime cũ (copy2)    : %d (KHÔNG phải cache — xem tài liệu §6)"
            % kc["so_tep_tmp_giu_mtime_cu"])
        ghi("  .pyc mới sinh                  : %s" % (kc["pycache_moi"] or "KHÔNG"))
        ghi("  PYTHONDONTWRITEBYTECODE         : %s" % kc["PYTHONDONTWRITEBYTECODE"])
        ghi("  VIP_G22_DAY_DU                  : %s" % kc["VIP_G22_DAY_DU"])
        ghi("  sha256 log của lượt             : %s" % (kc["log_bo_kiem"]["sha256"] or "—"))
        ghi("")
    ghi("```")
    ghi("")
    ghi("Mỗi lượt dùng một thư mục `log_<bên>` và `tmp_<bên>` MỚI (tên lượt có UUID); script TỪ CHỐI")
    ghi("chạy nếu các thư mục đó đã tồn tại. Không có tệp kết quả nào được chép vào. `unittest`")
    ghi("không có cache kết quả; `PYTHONDONTWRITEBYTECODE=1` chặn `.pyc`; `VIP_G22_DAY_DU` không bật")
    ghi("nên không đọc lại log `chay_tat_ca.sh` của lượt trước. Bộ kiểm vẫn có thể ghi log e2e của")
    ghi("chính nó vào `VIP_G22_LOG` — các tệp đó nằm trong danh sách ở trên, có mtime/sha256.")
    ghi("")

    # ── 4. So sánh ─────────────────────────────────────────────────────────────────────────────
    if a.chi_mot_ben:
        ghi("## 4. CHẾ ĐỘ CHẨN ĐOÁN `--chi-mot-ben` — KHÔNG SO SÁNH, KHÔNG PHẢI NGHIỆM THU")
        ghi("")
        ma_thoat = 0 if ben_ban_sao["phan_tich"]["ran"] is not None else 2
    else:
        # HAI DANH SÁCH KHÁC NHAU, không gộp:
        #  · `ly_do`         = vì sao KHÔNG SO SÁNH ĐƯỢC (worktree bẩn, khác bộ kiểm, khác deps).
        #  · `gioi_han_do`   = phép đo KHÔNG PHỦ tới đâu (thiếu Chromium, write-tree bị chặn).
        # Gộp hai thứ là cách một bộ đo tự lừa mình: "không đo được" không phải "không lệch".
        ly_do, gioi_han_do = [], []
        if ben_worktree["status_truoc"] or ben_worktree["status_sau"]:
            ly_do.append("worktree KHÔNG sạch: %d đường trong `status` (bản sao: %d)"
                         % (len(ben_worktree["status_truoc"]), len(ben_ban_sao["status_truoc"])))
        if ben_worktree["bo_kiem_sha_truoc"] != ben_ban_sao["bo_kiem_sha_truoc"]:
            ly_do.append("HAI BÊN KHÔNG CÙNG BỘ KIỂM (sha256 khác nhau ở %s)"
                         % [t for t in TEP_BO_KIEM
                            if ben_worktree["bo_kiem_sha_truoc"].get(t)
                            != ben_ban_sao["bo_kiem_sha_truoc"].get(t)])
        if not co_browser_nguon:
            gioi_han_do.append("node_modules dùng chung THIẾU `playwright-core/.local-browsers` ⇒ "
                               "e2e Chromium không đo được ở CẢ HAI bên. Hai bên cùng thiếu nên "
                               "chỗ này KHÔNG phân biệt được sản phẩm với môi trường.")
        # `git write-tree` ở worktree bị sandbox chặn; ghi lại thành giới hạn ĐO ĐƯỢC.
        rc_wt, out_wt = git(GOC_REPO, "write-tree")
        if rc_wt != 0:
            gioi_han_do.append("worktree: `git write-tree` rc=%d (sandbox chặn `.git/index.lock`) "
                               "⇒ cổng `A1` ở worktree KHÔNG đọc được cây chỉ mục; bản sao thì "
                               "đọc được. Mọi kết luận về `A1` phải lấy từ bản sao." % rc_wt)
        cung_dieu_kien = not ly_do

        ss = so_sanh(ben_worktree, ben_ban_sao, GOC_REPO, dest, run_dir)
        ket_qua["so_sanh"] = dict(ss, cung_dieu_kien=cung_dieu_kien, ly_do=ly_do,
                                  gioi_han_do=gioi_han_do,
                                  write_tree_worktree={"rc": rc_wt, "out": out_wt.strip()[:300]})

        xep_bang_so(ghi, ben_worktree, ben_ban_sao, "worktree", "bản sao sạch")
        ghi("## 2. LỆCH THEO TỪNG CA (nếu có)")
        ghi("")
        if ss["ca_lech"] or ss["ca_chi_co_worktree"] or ss["ca_chi_co_ban_sao"]:
            xep_bang(ghi, "", ["ca", "worktree", "bản sao"],
                     [[x["ca"], x["worktree"], x["ban_sao"]] for x in ss["ca_lech"]])
            if ss["ca_chi_co_worktree"]:
                ghi("CHỈ có ở worktree: %s" % ss["ca_chi_co_worktree"])
            if ss["ca_chi_co_ban_sao"]:
                ghi("CHỈ có ở bản sao: %s" % ss["ca_chi_co_ban_sao"])
        else:
            ghi("KHÔNG lệch ca nào (cùng tập ca, cùng trạng thái từng ca).")
        ghi("")

        ghi("## 3. LỆCH DÒNG ĐO (đã bỏ khác biệt đường dẫn/cổng/PID/giây/mốc thời gian)")
        ghi("")
        if ss["dong_do_lech"]:
            for x in ss["dong_do_lech"]:
                ghi("### [%s]" % x["nhan"])
                ghi("- worktree: %s" % " ⏎ ".join(x["worktree"])[:1200])
                ghi("- bản sao : %s" % " ⏎ ".join(x["ban_sao"])[:1200])
                ghi("")
        else:
            ghi("KHÔNG lệch dòng đo nào.")
            ghi("")

        ghi("## 4. ĐIỀU KIỆN SO SÁNH")
        ghi("")
        ghi("```")
        ghi("cùng commit           : worktree=%s · bản sao=%s · yêu cầu=%s"
            % (ket_qua["nguon"]["head"], tt_kiem.get("head"), sha_yeu_cau))
        ghi("worktree sạch         : %s" % ("CÓ" if not ben_worktree["status_truoc"] else "KHÔNG"))
        ghi("bản sao sạch          : %s" % ("CÓ" if tt_kiem.get("status_sach") else "KHÔNG"))
        ghi("cùng bộ kiểm (sha256) : %s"
            % ("CÓ" if ben_worktree["bo_kiem_sha_truoc"] == ben_ban_sao["bo_kiem_sha_truoc"] else "KHÔNG"))
        ghi("cùng node_modules     : %s" % ("CÓ" if lien_ket_nm or a.khong_lien_ket_node_modules else "KHÔNG"))
        ghi("có .local-browsers    : %s" % co_browser_nguon)
        ghi("write-tree worktree   : rc=%d" % rc_wt)
        ghi("bộ kiểm bị đổi giữa lượt: worktree=%s · bản sao=%s"
            % (ben_worktree["bo_kiem_bi_doi"] or "KHÔNG", ben_ban_sao["bo_kiem_bi_doi"] or "KHÔNG"))
        ghi("nguồn `.git` bị ghi    : %s"
            % ("KHÔNG (vân tay trước == sau)" if ket_qua["nguon"].get("dot_git_khong_doi")
               else "CÓ — VI PHẠM"))
        ghi("cây bị đổi giữa lượt  : worktree=%s · bản sao=%s"
            % (ben_worktree["tep_doi_giua_luot"] if ben_worktree["tep_doi_giua_luot"] is not None else "KHÔNG ĐỌC ĐƯỢC",
               ben_ban_sao["tep_doi_giua_luot"] if ben_ban_sao["tep_doi_giua_luot"] is not None else "KHÔNG ĐỌC ĐƯỢC"))
        ghi("ĐỦ ĐIỀU KIỆN SO SÁNH   : %s" % ("CÓ" if cung_dieu_kien else "KHÔNG"))
        for x in ly_do:
            ghi("  · KHÔNG SO SÁNH ĐƯỢC: %s" % x)
        ghi("GIỚI HẠN PHÉP ĐO       : %s" % ("KHÔNG" if not gioi_han_do else "%d mục" % len(gioi_han_do)))
        for x in gioi_han_do:
            ghi("  · GIỚI HẠN: %s" % x)
        ghi("```")
        ghi("")
        if not cung_dieu_kien:
            ghi("⚠ HAI BÊN KHÔNG CÙNG ĐIỀU KIỆN ĐO: bảng trên là ĐỐI CHIẾU THÔ, KHÔNG phải nghiệm thu.")
            ghi("  Muốn nghiệm thu: COMMIT các tệp của làn này trước, rồi chạy lại để worktree sạch.")
            ghi("")
        if gioi_han_do:
            ghi("⚠ CÓ GIỚI HẠN PHÉP ĐO (xem mục 4). Những chỗ đó KHÔNG được cộng vào cột 'khớp'.")
            ghi("")
        if ss["tat_ca_khop"] and cung_dieu_kien:
            ghi("⇒ KHÔNG thấy lệch ở mọi chỉ tiêu đo được, VÀ hai bên cùng điều kiện.")
            ghi("  (Đây vẫn KHÔNG phải 'sản phẩm ĐẠT' — bộ kiểm có thể ĐỎ; xem log.)")
            ma_thoat = 0
        else:
            ghi("⇒ CÓ LỆCH hoặc KHÔNG ĐỦ ĐIỀU KIỆN. Xem mục 2/3/4 ở trên, không suy diễn thêm.")
            ma_thoat = 1
        ghi("")
        ghi("## 5. CẢNH BÁO TỪ BỘ ĐO (nếu có)")
        ghi("")
        canh_bao = []
        for nhan, ben in (("worktree", ben_worktree), ("bản sao", ben_ban_sao)):
            for x in ben["canh_bao"]:
                canh_bao.append("%s: %s" % (nhan, x))
            for x in ben["khong_cache"]["pycache_moi"]:
                canh_bao.append("%s: .pyc mới sinh trong lượt: %s" % (nhan, x))
            if ben["bo_kiem_bi_doi"]:
                canh_bao.append("%s: BỘ KIỂM BỊ ĐỔI trong lượt: %s"
                                % (nhan, ben["bo_kiem_bi_doi"]))
            if ben["tep_doi_giua_luot"]:
                canh_bao.append("%s: CÂY BỊ ĐỔI trong lượt: %s"
                                % (nhan, ben["tep_doi_giua_luot"]))
            if not ben["khong_cache"]["dat"]:
                canh_bao.append("%s: KHÔNG chứng minh được không-cache" % nhan)
        if canh_bao:
            for x in canh_bao:
                ghi("- %s" % x)
        else:
            ghi("KHÔNG có cảnh báo.")
        ghi("")
        ket_qua["canh_bao_tong"] = canh_bao

        if (ben_worktree["phan_tich"]["ran"] is None or ben_ban_sao["phan_tich"]["ran"] is None
                or ben_worktree["het_gio"] or ben_ban_sao["het_gio"]):
            ma_thoat = 2
            ghi("")
            ghi("⛔ BỘ ĐO KHÔNG CHẠY ĐƯỢC: một bên không in `Ran N` hoặc hết giờ ⇒ không có số để so.")
            ghi("   Đây là LỖI CỦA BỘ ĐO/MÔI TRƯỜNG, không phải phán quyết về sản phẩm.")
            ghi("")

    # ── 5. Kết luận ────────────────────────────────────────────────────────────────────────────
    y_nghia = {
        0: "đo xong; hai bên khớp nhau và đủ điều kiện so sánh (KHÔNG phải 'sản phẩm ĐẠT')",
        1: "đo xong; có lệch hoặc không đủ điều kiện so sánh",
        2: "bộ đo không chạy được / không đọc được số ca",
    }[ma_thoat]
    ghi("## 6. KẾT LUẬN CỦA BỘ ĐO")
    ghi("")
    ghi("```")
    ghi("MÃ THOÁT CỦA BỘ ĐO NGHIỆM THU = %d  (%s)" % (ma_thoat, y_nghia))
    ghi("Mã thoát của BỘ KIỂM G22 (worktree) = %r" % (ben_worktree["exit"] if ben_worktree else "KHÔNG CHẠY"))
    ghi("Mã thoát của BỘ KIỂM G22 (bản sao) = %r" % ben_ban_sao["exit"])
    ghi("Lưu ý: hai mã thoát trên là của bộ kiểm; chúng KHÔNG bị bộ đo này sửa hay che.")
    ghi("```")
    ghi("")
    ghi("Thư mục bằng chứng: %s" % run_dir)
    ghi("Bản sao sạch      : %s" % dest)

    ket_qua["luc_ket_thuc_utc"] = luc_utc(time.time())
    ket_qua["giay_tong"] = round(time.time() - luc_bat_dau, 3)
    ket_qua["ket_luan"] = {"ma_thoat": ma_thoat, "y_nghia": y_nghia}

    # Ghi bằng chứng: KET_QUA.json + BANG_SO_SANH.txt
    json_path = a.json or os.path.join(run_dir, "KET_QUA.json")
    if os.path.dirname(os.path.abspath(json_path)):
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    json_ghi(json_path, ket_qua)
    with open(os.path.join(run_dir, "BANG_SO_SANH.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(ghi.dong) + "\n")
    print("\nĐã ghi: %s" % json_path)
    print("Đã ghi: %s" % os.path.join(run_dir, "BANG_SO_SANH.txt"))
    return ma_thoat


if __name__ == "__main__":
    sys.exit(main())
