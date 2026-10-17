#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AG-03 (G22) — A1 GIT SANDBOX: đo CÂY (write-tree) khi sandbox CHẶN ghi `.git`.

VẤN ĐỀ ĐO ĐƯỢC (không phải suy đoán)
────────────────────────────────────
Trong worktree này, `.git` là một TỆP con trỏ tới gitdir nằm NGOÀI thư mục được sandbox cho
ghi:

    gitdir: /Users/viporder/Projects/vip-express-hub/.git/worktrees/g22-a3-gitsandbox

`git write-tree` cần tạo `<gitdir>/index.lock` (và có thể ghi object mới vào `<gitdir>/objects`).
Sandbox chỉ cho ghi dưới workspace và vùng tạm của hệ điều hành, nên lệnh trả:

    fatal: Unable to create '…/worktrees/g22-a3-gitsandbox/index.lock': Operation not permitted
    rc = 128

Đây là lỗi MÔI TRƯỜNG ĐO, không phải lỗi sản phẩm: cùng lệnh trên chạy trong một bản sao nằm ở
`/tmp` trả `rc = 0` và đúng cây của `HEAD`.

CÁCH GIẢI (được CHỨNG MINH trong tệp này, không phải đề xuất suông)
──────────────────────────────────────────────────────────────────
A. ĐO TẠI CHỖ, KHÔNG GHI `.git` THẬT (dùng cho ca `test_a1_*` của bộ kiểm chính thức):
   - sao `index` của worktree chính ra một thư mục tạm;
   - `GIT_INDEX_FILE`      = bản sao index đó;
   - `GIT_OBJECT_DIRECTORY` = một ODB TẠM;
   - `GIT_ALTERNATE_OBJECT_DIRECTORIES` = ODB THẬT (CHỈ ĐỌC, để phân giải blob cũ);
   - chạy `git write-tree`. Mọi thứ cần GHI đều rơi vào thư mục tạm; cây trả về là cây của
     ĐÚNG index đang có trong worktree chính (tương đương tuyệt đối với `write-tree` trần).
B. MÔI TRƯỜNG CÔ LẬP (dùng khi chạy TOÀN BỘ bộ kiểm):
   - `git clone --shared --no-checkout <worktree> <tmp>/cp`
   - `git -C <tmp>/cp checkout --detach <NEN_SHA>`
   - mọi lệnh git trong `<tmp>/cp` ghi được `.git`, nên `write-tree` trả `rc = 0`.

ĐỐI CHỨNG DƯƠNG (bắt buộc — phép đo phải chứng minh nó NHÌN THẤY thay đổi):
   - Ca `test_03` TIÊM một mục mới vào BẢN SAO index (blob mới nằm trong ODB tạm) rồi đo lại:
     cây ĐỔI. Index thật của worktree chính KHÔNG đổi (sha256 trước == sau), không có
     `index.lock` sót lại.

PHẠM VI: chỉ ĐỌC worktree chính. Không `sudo`, không `chmod`, không xoá lock, không sửa index,
không ghi `.git`, không push/deploy/DB. Mọi thứ ghi được đều nằm trong `tempfile.mkdtemp()`.

LỆNH CHẠY:
    python3 app/thu/thu_g22_a1.py                 # 5 ca đo môi trường (kỳ vọng: OK)
    python3 app/thu/thu_g22_a1.py --kiem-ghim     # + ca đối chiếu GHIM của bộ kiểm chính thức
    python3 app/thu/thu_g22_a1.py --json          # in thêm một dòng __JSON__=… để máy đọc
    python3 app/thu/thu_g22_a1.py --giu-tmp       # giữ thư mục tạm để thanh tra
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

GOC_CAY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TEP_KIEM_CHINH_THUC = os.path.join(GOC_CAY, "app", "thu", "thu_qa_g22.py")
GIU_TMP = "--giu-tmp" in sys.argv
KIEM_GHIM = "--kiem-ghim" in sys.argv


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 0. CHẠY LỆNH THẬT — mã thoát đọc NGAY sau lệnh, stdout/stderr TÁCH RIÊNG
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _git_env():
    """Môi trường git đã chuẩn hoá.

    `GIT_CONFIG_COUNT=2` mà THIẾU `GIT_CONFIG_KEY_*` làm MỌI lệnh git thoát 128
    (`N-G18-00`, `docs/OWNER_ACTIONS.md` §F). Đây là lỗi môi trường THỨ HAI, độc lập với
    sandbox: nó nổ TRƯỚC khi git kịp mở `.git`. Gỡ để ĐO ĐƯỢC, không phải để "cho xanh".
    """
    e = dict(os.environ)
    n = e.get("GIT_CONFIG_COUNT")
    if n and n.isdigit() and int(n) > 0:
        thieu = [i for i in range(int(n)) if not e.get("GIT_CONFIG_KEY_%d" % i)]
        if thieu:
            for k in [k for k in e if k.startswith("GIT_CONFIG_")]:
                e.pop(k, None)
    return e


def chay(lenh, env_them=None, cwd=None, giay=180):
    """→ `(rc, stdout, stderr)`. `rc` đọc NGAY sau tiến trình, không qua ống."""
    e = _git_env()
    if env_them:
        e.update(env_them)
    p = subprocess.run(lenh, cwd=cwd or GOC_CAY, env=e, capture_output=True, text=True,
                       timeout=giay)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def git(*tham_so, **kw):
    return chay(["git"] + list(tham_so), **kw)


def git_out(*tham_so, **kw):
    """stdout đã strip khi rc == 0; ngược lại chuỗi rỗng."""
    rc, out, _ = git(*tham_so, **kw)
    return out.strip() if rc == 0 else ""


def _tuyet_doi(p, goc=None):
    if not p:
        return ""
    return os.path.normpath(p if os.path.isabs(p) else os.path.join(goc or GOC_CAY, p))


def sha256_tep(duong):
    try:
        with open(duong, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def co_index_lock(git_dir):
    return os.path.exists(os.path.join(git_dir, "index.lock"))


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 1. KHẢO SÁT MÔI TRƯỜNG — đường dẫn thật, không đoán
# ══════════════════════════════════════════════════════════════════════════════════════════════

def khao_sat():
    """→ dict mô tả môi trường đo. Mọi trường đều ĐỌC từ git, không viết cứng."""
    git_dir = _tuyet_doi(git_out("rev-parse", "--git-dir"))
    git_common = _tuyet_doi(git_out("rev-parse", "--git-common-dir"))
    top = _tuyet_doi(git_out("rev-parse", "--show-toplevel"))
    head = git_out("rev-parse", "HEAD")
    tree_head = git_out("rev-parse", "HEAD^{tree}")
    index = os.path.join(git_dir, "index") if git_dir else ""
    return {
        "goc_cay": GOC_CAY,
        "git_dir": git_dir,
        "git_common": git_common,
        "top": top,
        "head": head,
        "tree_head": tree_head,
        "index": index,
        "index_sha256": sha256_tep(index),
        "index_ton_tai": bool(index and os.path.exists(index)),
        "index_lock": co_index_lock(git_dir) if git_dir else None,
        "so_tep": len([d for d in git_out("ls-files").splitlines() if d.strip()]),
        "phien_ban_git": git_out("--version"),
    }


def write_tree_truc_tiep():
    """`git write-tree` TRẦN — lệnh bị sandbox chặn. → `(rc, tree, stderr)`."""
    rc, out, err = git("write-tree")
    return rc, out.strip(), err.strip()


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 2. ĐO AN TOÀN — index tạm + ODB tạm + alternates CHỈ ĐỌC
# ══════════════════════════════════════════════════════════════════════════════════════════════

def _moi_truong_index_tam(tmp):
    """Dựng môi trường ghi tạm. → `(env, index_tam, objects_tam, git_dir, git_common)`."""
    git_dir = _tuyet_doi(git_out("rev-parse", "--git-dir"))
    git_common = _tuyet_doi(git_out("rev-parse", "--git-common-dir"))
    objects_tam = os.path.join(tmp, "objects")
    os.makedirs(objects_tam, exist_ok=True)
    index_tam = os.path.join(tmp, "index")
    shutil.copy2(os.path.join(git_dir, "index"), index_tam)
    env = {
        "GIT_INDEX_FILE": index_tam,
        "GIT_OBJECT_DIRECTORY": objects_tam,
        # CHỈ ĐỌC object cũ từ kho thật; mọi object MỚI ghi vào objects_tam.
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": os.path.join(git_common, "objects"),
    }
    return env, index_tam, objects_tam, git_dir, git_common


def write_tree_an_toan(giu_tmp=None):
    """Tương đương `git write-tree` trên ĐÚNG index của worktree chính, KHÔNG ghi `.git` thật.

    → dict: rc, tree, stderr, index_sha256_truoc/sau, index_lock_truoc/sau, tmp.
    """
    giu = GIU_TMP if giu_tmp is None else giu_tmp
    kq = {"rc": None, "tree": "", "stderr": "", "stdout": "", "tmp": "",
          "index_sha256_truoc": "", "index_sha256_sau": "",
          "index_lock_truoc": None, "index_lock_sau": None,
          "git_dir": "", "git_common": ""}
    tmp = tempfile.mkdtemp(prefix="g22-a1-index-")
    kq["tmp"] = tmp
    try:
        env, index_tam, _, git_dir, git_common = _moi_truong_index_tam(tmp)
        kq["git_dir"], kq["git_common"] = git_dir, git_common
        kq["index_sha256_truoc"] = sha256_tep(os.path.join(git_dir, "index"))
        kq["index_lock_truoc"] = co_index_lock(git_dir)
        rc, out, err = chay(["git", "write-tree"], env_them=env)
        kq.update(rc=rc, tree=out.strip(), stdout=out.strip(), stderr=err.strip())
        kq["index_sha256_sau"] = sha256_tep(os.path.join(git_dir, "index"))
        kq["index_lock_sau"] = co_index_lock(git_dir)
        kq["index_tam"] = index_tam
        return kq
    finally:
        if not giu:
            kq.pop("index_tam", None)
            shutil.rmtree(tmp, ignore_errors=True)
            kq["tmp"] = ""


def tiem_index_ban_sao():
    """ĐỐI CHỨNG DƯƠNG: thêm MỘT mục vào BẢN SAO index rồi đo lại — cây phải ĐỔI.

    Không chạm index thật: blob mới ghi vào ODB tạm, mục mới ghi vào bản sao index trong TMP.
    → dict: rc, tree_goc, tree_sau, blob, index_sha256_truoc/sau, index_lock_truoc/sau, tmp.
    """
    kq = {"rc": None, "tree_goc": "", "tree_sau": "", "blob": "",
          "stderr": "", "tmp": "",
          "index_sha256_truoc": "", "index_sha256_sau": "",
          "index_lock_truoc": None, "index_lock_sau": None}
    tmp = tempfile.mkdtemp(prefix="g22-a1-tiem-")
    kq["tmp"] = tmp
    try:
        env, index_tam, objects_tam, git_dir, _ = _moi_truong_index_tam(tmp)
        kq["index_sha256_truoc"] = sha256_tep(os.path.join(git_dir, "index"))
        kq["index_lock_truoc"] = co_index_lock(git_dir)
        rc0, out0, err0 = chay(["git", "write-tree"], env_them=env)
        kq["tree_goc"] = out0.strip()
        if rc0 != 0:
            kq.update(rc=rc0, stderr=("write-tree gốc: " + err0.strip()).strip())
            return kq

        tep = os.path.join(tmp, "noi_dung_doi_chung.txt")
        with open(tep, "w", encoding="utf-8") as f:
            f.write("AG-03 G22 · đối chứng dương cho A1 · nội dung cố ý khác nền\n")
        rc_h, out_h, err_h = chay(["git", "hash-object", "-w", tep],
                                  env_them={"GIT_OBJECT_DIRECTORY": objects_tam})
        blob = out_h.strip()
        if rc_h != 0 or not re.fullmatch(r"[0-9a-f]{40}", blob):
            kq.update(rc=rc_h or 1, stderr=("hash-object: " + err_h.strip()).strip())
            return kq
        kq["blob"] = blob

        rc_u, _, err_u = chay(
            ["git", "update-index", "--add", "--cacheinfo",
             "100644,%s,docs/G22_A1_DOI_CHUNG.txt" % blob],
            env_them=env)
        if rc_u != 0:
            kq.update(rc=rc_u, stderr=("update-index: " + err_u.strip()).strip())
            return kq

        rc1, out1, err1 = chay(["git", "write-tree"], env_them=env)
        kq.update(rc=rc1, tree_sau=out1.strip(), stderr=err1.strip())
        kq["index_sha256_sau"] = sha256_tep(os.path.join(git_dir, "index"))
        kq["index_lock_sau"] = co_index_lock(git_dir)
        return kq
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        kq["tmp"] = ""


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 3. MÔI TRƯỜNG CÔ LẬP — bản sao THẬT trong TMP, `git init` của bộ khác không chạm tới
# ══════════════════════════════════════════════════════════════════════════════════════════════

def tao_ban_sao(nen_sha=""):
    """`clone --shared --no-checkout` + `checkout --detach` trong TMP rồi đo `write-tree`.

    → dict: rc_clone, rc_checkout, rc_write_tree, tree, head, tree_nen, tmp.
    """
    kq = {"rc_clone": None, "rc_checkout": None, "rc_write_tree": None,
          "tree": "", "head": "", "tree_nen": "", "tmp": "",
          "stderr": ""}
    head = git_out("rev-parse", "HEAD")
    nen = nen_sha or head
    kq["tree_nen"] = git_out("rev-parse", nen + "^{tree}") if nen else ""
    tmp = tempfile.mkdtemp(prefix="g22-a1-clone-")
    kq["tmp"] = tmp
    cp = os.path.join(tmp, "cp")
    try:
        rc1, _, err1 = chay(["git", "clone", "--shared", "--no-checkout", GOC_CAY, cp])
        kq["rc_clone"] = rc1
        if rc1 != 0:
            kq["stderr"] = err1.strip()
            return kq
        rc2, _, err2 = chay(["git", "checkout", "--detach", nen], cwd=cp)
        kq["rc_checkout"] = rc2
        if rc2 != 0:
            kq["stderr"] = err2.strip()
            return kq
        rc3, out3, err3 = chay(["git", "write-tree"], cwd=cp)
        kq.update(rc_write_tree=rc3, tree=out3.strip(), stderr=err3.strip())
        kq["head"] = git_out("rev-parse", "HEAD", cwd=cp)
        return kq
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        kq["tmp"] = ""


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 4. GHIM CỦA BỘ KIỂM CHÍNH THỨC — đọc, KHÔNG sửa
# ══════════════════════════════════════════════════════════════════════════════════════════════

def doc_ghim_thu_qa():
    """Đọc `NEN_SHA`/`TREE_NEN` từ `app/thu/thu_qa_g22.py` (CHỈ ĐỌC)."""
    if not os.path.exists(TEP_KIEM_CHINH_THUC):
        return {}
    with open(TEP_KIEM_CHINH_THUC, encoding="utf-8") as f:
        s = f.read()
    m1 = re.search(r'^NEN_SHA\s*=\s*"([0-9a-f]{40})"', s, re.M)
    m2 = re.search(r'^TREE_NEN\s*=\s*"([0-9a-f]{40})"', s, re.M)
    return {"tep": TEP_KIEM_CHINH_THUC,
            "nen_sha": m1.group(1) if m1 else "",
            "tree_nen": m2.group(1) if m2 else "",
            "sha256_tep": sha256_tep(TEP_KIEM_CHINH_THUC)}


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 5. CÁC CA
# ══════════════════════════════════════════════════════════════════════════════════════════════

class A_MoiTruong(unittest.TestCase):
    """ĐO MÔI TRƯỜNG TRƯỚC KHI ĐO SẢN PHẨM."""

    @classmethod
    def setUpClass(cls):
        cls.ks = khao_sat()

    def test_00_khao_sat_moi_truong(self):
        ks = self.ks
        print("\n  [A1-00] git=%s" % ks["phien_ban_git"])
        print("          worktree=%s" % ks["goc_cay"])
        print("          gitdir  =%s" % ks["git_dir"])
        print("          common  =%s" % ks["git_common"])
        print("          HEAD=%s · tree(HEAD)=%s · %d tệp theo dõi"
              % (ks["head"], ks["tree_head"], ks["so_tep"]))
        print("          index  =%s" % ks["index"])
        print("          sha256(index) TRƯỚC=%s · index.lock=%s"
              % (ks["index_sha256"], ks["index_lock"]))
        self.assertTrue(ks["top"], "không đọc được --show-toplevel")
        self.assertEqual(ks["top"], GOC_CAY, "worktree không phải gốc tệp này")
        self.assertRegex(ks["head"], r"^[0-9a-f]{40}$")
        self.assertRegex(ks["tree_head"], r"^[0-9a-f]{40}$")
        self.assertTrue(ks["index_ton_tai"], "không thấy index của worktree")
        self.assertFalse(ks["index_lock"], "ĐÃ CÓ index.lock TRƯỚC khi đo — dừng, không xoá")

    def test_01_lenh_tran_va_ly_do_bi_chan(self):
        """Ghi lại ĐÚNG lệnh bị chặn: rc, stderr, và chứng minh nó KHÔNG để lại dấu vết."""
        truoc = khao_sat()
        rc, tree, err = write_tree_truc_tiep()
        sau = khao_sat()
        print("\n  [A1-01] $ git write-tree")
        print("          rc=%d" % rc)
        if err:
            print("          stderr: %s" % err)
        if rc == 0:
            print("          → môi trường NÀY GHI ĐƯỢC .git: đo trực tiếp được (tree=%s)" % tree)
            self.assertEqual(tree, truoc["tree_head"])
        else:
            print("          → BỊ CHẶN ở `<gitdir>/index.lock` (môi trường đo, không phải sản phẩm)")
            self.assertEqual(rc, 128, "mã thoát lạ: %d" % rc)
            self.assertIn("index.lock", err, "thông báo không nhắc index.lock: %r" % err)
            self.assertIn("Operation not permitted", err,
                          "thông báo không phải EPERM: %r" % err)
        self.assertEqual(sau["index_sha256"], truoc["index_sha256"],
                         "index THẬT bị đổi bởi phép đo — vi phạm phạm vi")
        self.assertFalse(sau["index_lock"], "phép đo để lại index.lock — không được xoá, phải báo")

    def test_02_do_an_toan_tra_dung_cay(self):
        """Phương án A: index tạm + ODB tạm + alternates CHỈ ĐỌC ⇒ tương đương write-tree."""
        ks = self.ks
        kq = write_tree_an_toan()
        print("\n  [A1-02] $ GIT_INDEX_FILE=<tmp>/index GIT_OBJECT_DIRECTORY=<tmp>/objects \\")
        print("             GIT_ALTERNATE_OBJECT_DIRECTORIES=<common>/objects git write-tree")
        print("          rc=%d · tree=%s" % (kq["rc"], kq["tree"]))
        print("          tree(HEAD)=%s · khớp=%s" % (ks["tree_head"], kq["tree"] == ks["tree_head"]))
        print("          sha256(index) TRƯỚC=%s SAU=%s (KHÔNG ĐỔI=%s)"
              % (kq["index_sha256_truoc"], kq["index_sha256_sau"],
                 kq["index_sha256_truoc"] == kq["index_sha256_sau"]))
        self.assertEqual(kq["rc"], 0, "write-tree an toàn hỏng: %s" % kq["stderr"])
        self.assertRegex(kq["tree"], r"^[0-9a-f]{40}$")
        self.assertEqual(kq["tree"], ks["tree_head"],
                         "cây đo được ≠ cây HEAD — index đang khác HEAD (có thay đổi đã stage?)")
        self.assertEqual(kq["index_sha256_sau"], kq["index_sha256_truoc"],
                         "index THẬT bị đổi")
        self.assertFalse(kq["index_lock_sau"], "để lại index.lock")

    def test_03_doi_chung_duong_bat_duoc_thay_doi(self):
        """ĐỔI MỘT MỤC trong BẢN SAO index ⇒ cây ĐỔI. Chứng minh phép đo KHÔNG mù."""
        kq = tiem_index_ban_sao()
        print("\n  [A1-03] tiêm 1 mục vào BẢN SAO index:")
        print("          blob mới=%s" % (kq["blob"] or "(không tạo được)"))
        print("          tree TRƯỚC=%s" % kq["tree_goc"])
        print("          tree SAU  =%s" % kq["tree_sau"])
        print("          ĐỔI=%s · sha256(index thật) TRƯỚC=%s SAU=%s"
              % (kq["tree_goc"] != kq["tree_sau"], kq["index_sha256_truoc"],
                 kq["index_sha256_sau"]))
        self.assertEqual(kq["rc"], 0, "write-tree sau khi tiêm hỏng: %s" % kq["stderr"])
        self.assertRegex(kq["tree_sau"], r"^[0-9a-f]{40}$")
        self.assertNotEqual(kq["tree_sau"], kq["tree_goc"],
                            "tiêm thay đổi mà cây KHÔNG đổi ⇒ phép đo MÙ, không dùng được")
        self.assertEqual(kq["index_sha256_sau"], kq["index_sha256_truoc"],
                         "index THẬT bị đổi bởi phép tiêm")
        self.assertFalse(kq["index_lock_sau"], "để lại index.lock")

    def test_04_moi_truong_co_lap_clone(self):
        """Phương án B: clone `--shared` + `checkout --detach` trong TMP ⇒ write-tree chạy."""
        kq = tao_ban_sao()
        print("\n  [A1-04] $ git clone --shared --no-checkout <worktree> <tmp>/cp")
        print("          $ git -C <tmp>/cp checkout --detach %s" % self.ks["head"])
        print("          rc clone=%s · rc checkout=%s · rc write-tree=%s"
              % (kq["rc_clone"], kq["rc_checkout"], kq["rc_write_tree"]))
        print("          HEAD(clone)=%s · write-tree=%s" % (kq["head"], kq["tree"]))
        print("          tree(nền)=%s · khớp=%s"
              % (kq["tree_nen"], kq["tree"] == kq["tree_nen"]))
        self.assertEqual(kq["rc_clone"], 0, "clone hỏng: %s" % kq["stderr"])
        self.assertEqual(kq["rc_checkout"], 0, "checkout hỏng: %s" % kq["stderr"])
        self.assertEqual(kq["rc_write_tree"], 0, "write-tree trong bản sao hỏng: %s" % kq["stderr"])
        self.assertEqual(kq["head"], self.ks["head"])
        self.assertEqual(kq["tree"], kq["tree_nen"])


class B_Ghim(unittest.TestCase):
    """ĐỐI CHIẾU GHIM của bộ kiểm chính thức — CHỈ chạy khi có `--kiem-ghim`."""

    def test_05_ghim_bo_kiem_chinh_thuc(self):
        ghim = doc_ghim_thu_qa()
        ks = khao_sat()
        print("\n  [A1-05] tệp kiểm chính thức: %s" % ghim.get("tep", "(không có)"))
        print("          GHIM NEN_SHA =%s" % ghim.get("nen_sha", ""))
        print("          GHIM TREE_NEN=%s" % ghim.get("tree_nen", ""))
        print("          ĐO  HEAD     =%s" % ks["head"])
        print("          ĐO  tree(HEAD)=%s" % ks["tree_head"])
        print("          KHỚP NEN_SHA=%s · KHỚP TREE_NEN=%s"
              % (ghim.get("nen_sha") == ks["head"], ghim.get("tree_nen") == ks["tree_head"]))
        self.assertTrue(ghim, "không đọc được hằng số ghim")
        self.assertEqual(ghim["nen_sha"], ks["head"],
                         "GHIM NEN_SHA ≠ HEAD của cây đang đo")
        self.assertEqual(ghim["tree_nen"], ks["tree_head"],
                         "GHIM TREE_NEN ≠ cây của HEAD đang đo")


# ══════════════════════════════════════════════════════════════════════════════════════════════
# 6. MAIN — chạy ca, in bảng tổng, xuất JSON
# ══════════════════════════════════════════════════════════════════════════════════════════════

def main():
    mac_dinh = ["A_MoiTruong"] + (["B_Ghim"] if KIEM_GHIM else [])
    ds_loc = [a for a in sys.argv[1:] if not a.startswith("-")]

    print("=" * 92)
    print("  AG-03 (G22) · A1 GIT SANDBOX · đo CÂY trong worktree bị sandbox chặn ghi .git")
    print("  Worktree: %s" % GOC_CAY)
    print("  Cách chạy: python3 app/thu/thu_g22_a1.py [--kiem-ghim] [--json] [--giu-tmp]")
    print("=" * 92)

    prog = unittest.main(module=sys.modules["__main__"],
                         argv=[sys.argv[0]] + (ds_loc or mac_dinh),
                         verbosity=2, exit=False)
    ok = bool(prog.result.wasSuccessful())

    ks = khao_sat()
    rc_truc, tree_truc, err_truc = write_tree_truc_tiep()
    kq = write_tree_an_toan(giu_tmp=False)
    ghim = doc_ghim_thu_qa()
    print("\n" + "=" * 92)
    print("  BẢNG TỔNG — số đo THẬT của lượt này")
    print("    HEAD=%s · tree(HEAD)=%s · %d tệp" % (ks["head"], ks["tree_head"], ks["so_tep"]))
    print("    gitdir=%s" % ks["git_dir"])
    print("    write-tree TRẦN          : rc=%d · tree=%s · %s"
          % (rc_truc, tree_truc or "—",
             "index.lock · Operation not permitted" if rc_truc != 0 else "chạy được"))
    print("    write-tree AN TOÀN       : rc=%d · tree=%s" % (kq["rc"], kq["tree"]))
    print("    index THẬT sha256 TRƯỚC  : %s" % ks["index_sha256"])
    print("    index THẬT sha256 SAU    : %s" % sha256_tep(ks["index"]))
    print("    index.lock sau lượt      : %s" % co_index_lock(ks["git_dir"]))
    print("    GHIM bộ kiểm chính thức  : NEN_SHA=%s · TREE_NEN=%s"
          % (ghim.get("nen_sha", "?"), ghim.get("tree_nen", "?")))
    khop = (ghim.get("tree_nen") == kq["tree"])
    print("    GHIM == cây đo được      : %s%s"
          % (khop, "" if khop else "   ⚠ GHIM LỆCH — cần AG-02/AG-00 cập nhật, KHÔNG tự sửa"))
    r = prog.result
    print("    ca: %d · hỏng/lỗi: %d · bỏ qua: %d · MÃ THOÁT = %d"
          % (r.testsRun, len(r.failures) + len(r.errors), len(r.skipped), 0 if ok else 1))
    print("=" * 92)

    if "--json" in sys.argv:
        print("__JSON__=" + json.dumps({
            "goc_cay": GOC_CAY,
            "head": ks["head"],
            "tree_head": ks["tree_head"],
            "git_dir": ks["git_dir"],
            "git_common": ks["git_common"],
            "index_sha256_truoc": ks["index_sha256"],
            "index_sha256_sau": sha256_tep(ks["index"]),
            "index_lock_sau": co_index_lock(ks["git_dir"]),
            "write_tree_an_toan": {"rc": kq["rc"], "tree": kq["tree"]},
            "ghim": ghim,
            "ghim_khop": khop,
            "so_ca": r.testsRun,
            "so_hong": len(r.failures) + len(r.errors),
            "so_bo_qua": len(r.skipped),
            "ma_thoat": 0 if ok else 1,
        }, ensure_ascii=False))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
