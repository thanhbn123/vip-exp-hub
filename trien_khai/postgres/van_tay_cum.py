#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VÂN TAY CỤM PostgreSQL — chụp TRƯỚC/SAU và đối chiếu, để chứng minh lượt đo KHÔNG đụng cụm khác.

====== VÌ SAO CẦN TỆP NÀY ======
Yêu cầu G17/AG-05: *"mọi báo cáo phải ghi rõ: đã dùng cụm riêng, cổng nào, và vân tay cụm
:5432 TRƯỚC = SAU (PID postmaster, danh sách CSDL)."*

Một câu "tôi không đụng cụm :5432" là một lời khai. Tệp này biến nó thành một PHÉP ĐO:
chụp vân tay cụm đó, chạy việc cần chạy, chụp lại, rồi đối chiếu TỪNG TRƯỜNG. Lệch một
trường là lượt đo ĐỤNG vào cụm của dự án khác — và nó phải kêu to, không được lặng.

====== CHỈ ĐỌC — TUYỆT ĐỐI CHỈ ĐỌC ======
Mọi câu lệnh ở đây là `SELECT`/`SHOW`. Không `CREATE`, không `DROP`, không `ALTER`, không
`pg_ctl`. Cụm `:5432` trên máy này đang giữ CSDL của **dự án khác** (`vip_customs`,
`vip_customs_g16`, `vip_customs_test`) — xem `docs/G12_POSTGRES.md` mục 0.

====== VÂN TAY GỒM NHỮNG GÌ ======
| Trường | Lấy bằng | Bắt được cái gì |
|---|---|---|
| `pid` | dòng 1 của `<data_directory>/postmaster.pid` | cụm bị KHỞI ĐỘNG LẠI (đổi tiến trình) |
| `data_directory` | `SHOW data_directory` | trỏ nhầm sang cụm khác |
| `postmaster_bat_dau` | `pg_postmaster_start_time()` | cụm bị restart (kể cả cùng PID) |
| `phien_ban_may_chu` | `SHOW server_version` | nâng/hạ phiên bản |
| `danh_sach_csdl` | `SELECT datname FROM pg_database` | **CSDL bị THÊM hoặc MẤT** — dấu hiệu nặng nhất |
| `so_csdl` | đếm danh sách trên | chặn ca "hai danh sách rỗng bằng nhau" |
| `nghe_tcp` | `lsof -iTCP:<cổng>` | cổng bị mở thêm/đóng |

`so_csdl` có mặt là để tự chặn ca xanh giả: nếu cụm không truy cập được thì cả hai lượt chụp
đều ra `truy_cap_duoc=false` và "TRƯỚC = SAU" chẳng nói lên điều gì. `--so` TỪ CHỐI phán
"bằng nhau" khi một trong hai lượt chụp không đọc được cụm.

CHẠY
----
    python3 trien_khai/postgres/van_tay_cum.py --chup                 # in JSON vân tay :5432
    python3 trien_khai/postgres/van_tay_cum.py --chup --cong 55432
    python3 trien_khai/postgres/van_tay_cum.py --so a.json b.json     # 0 = giống, 1 = lệch
    python3 trien_khai/postgres/van_tay_cum.py --vong -- <lệnh> …     # chụp–chạy–chụp, tự đối chiếu

`--vong` là dạng dùng chính: nó bọc quanh một lượt chạy thật và trả về mã thoát của lệnh đó,
TRỪ KHI vân tay lệch — lúc đó nó trả 2 và in rõ trường nào lệch.
"""
import argparse
import json
import os
import re
import subprocess
import sys

CONG_MAC_DINH = "5432"
# Đọc-only. `pg_database` là bảng hệ thống; `SHOW`/`current_setting` là cấu hình.
SQL_VAN_TAY = (
    "SELECT 'data_directory='||current_setting('data_directory');"
    "SELECT 'postmaster_bat_dau='||pg_postmaster_start_time()::text;"
    "SELECT 'phien_ban_may_chu='||current_setting('server_version');"
    "SELECT 'datname='||datname FROM pg_database ORDER BY datname;"
)
CAC_TRUONG = ("truy_cap_duoc", "pid", "data_directory", "postmaster_bat_dau",
              "phien_ban_may_chu", "danh_sach_csdl", "so_csdl", "nghe_tcp", "ghi_chu")


def _chay(co, dau_vao=None, thoi_gian=25):
    """Chạy một lệnh, KHÔNG để nó treo vô hạn: cụm chết thì phải trả lời, không phải đợi."""
    try:
        p = subprocess.run(co, input=dau_vao, capture_output=True, text=True,
                           timeout=thoi_gian, env=dict(os.environ, PGCONNECT_TIMEOUT="3"))
        return p.returncode, p.stdout, p.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        return 127, "", "%s: %s" % (type(e).__name__, e)


def doc_pid_postmaster(data_directory):
    """PID postmaster từ `postmaster.pid`. Đây là nguồn CHÍNH vì nó không cần `ps`/`lsof`
    (môi trường soát có thể chặn hai lệnh đó) và nó chỉ đọc một tệp.<br>
    Không đọc được thì trả None — KHÔNG đoán, KHÔNG bịa số."""
    if not data_directory:
        return None
    duong = os.path.join(data_directory, "postmaster.pid")
    try:
        with open(duong, encoding="utf-8", errors="replace") as f:
            d = f.readline().strip()
        return d or None
    except OSError:
        return None


def nghe_tcp(cong):
    """Danh sách PID đang LISTEN trên cổng. Rỗng nghĩa là KHÔNG mở TCP (đúng với cụm thử
    `listen_addresses=''`). `lsof` thiếu thì trả `None` — khác hẳn `[]`."""
    try:
        p = subprocess.run(["lsof", "-nP", "-iTCP:%s" % cong, "-sTCP:LISTEN"],
                           capture_output=True, text=True, timeout=20)
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    if p.returncode not in (0, 1):
        return None
    return sorted({d.split()[1] for d in p.stdout.splitlines()[1:] if len(d.split()) > 1})


def chup(cong=CONG_MAC_DINH, nguoi=None, may_chu="localhost"):
    """Chụp vân tay cụm ở `cổng`. CHỈ ĐỌC. Không bao giờ ném ra ngoài."""
    cong = str(cong)
    vt = {"cong": cong, "may_chu": may_chu, "truy_cap_duoc": False, "pid": None,
          "data_directory": None, "postmaster_bat_dau": None, "phien_ban_may_chu": None,
          "danh_sach_csdl": [], "so_csdl": 0, "nghe_tcp": nghe_tcp(cong), "ghi_chu": ""}
    co = ["psql", "-h", may_chu, "-p", cong, "-d", "postgres", "-qtAX", "-c", SQL_VAN_TAY]
    if nguoi:
        co[1:1] = ["-U", nguoi]
    rc, out, err = _chay(co)
    if rc:
        vt["ghi_chu"] = ("psql không đọc được cụm: %s" % (err or out).strip()[:200])
        return vt
    for d in out.splitlines():
        d = d.strip()
        if d.startswith("data_directory="):
            vt["data_directory"] = d.split("=", 1)[1]
        elif d.startswith("postmaster_bat_dau="):
            vt["postmaster_bat_dau"] = d.split("=", 1)[1]
        elif d.startswith("phien_ban_may_chu="):
            vt["phien_ban_may_chu"] = d.split("=", 1)[1]
        elif d.startswith("datname="):
            vt["danh_sach_csdl"].append(d.split("=", 1)[1])
    vt["danh_sach_csdl"] = sorted(vt["danh_sach_csdl"])
    vt["so_csdl"] = len(vt["danh_sach_csdl"])
    vt["pid"] = doc_pid_postmaster(vt["data_directory"])
    vt["truy_cap_duoc"] = True
    return vt


def so_sanh(truoc, sau):
    """Trả (giống_nhau, danh_sách_lệch). TỪ CHỐI phán 'giống' khi một bên không đọc được cụm."""
    lech = []
    if not (truoc.get("truy_cap_duoc") and sau.get("truy_cap_duoc")):
        return False, [("truy_cap_duoc", "một trong hai lượt chụp KHÔNG đọc được cụm — "
                                         "'giống nhau' ở đây là câu vô nghĩa",
                        truoc.get("truy_cap_duoc"), sau.get("truy_cap_duoc"))]
    if truoc.get("so_csdl", 0) == 0:
        return False, [("so_csdl", "lượt chụp TRƯỚC thấy 0 CSDL — cụm rỗng thì so cũng vô nghĩa",
                        0, sau.get("so_csdl"))]
    for t in CAC_TRUONG:
        if t in ("truy_cap_duoc", "ghi_chu"):
            continue
        a, b = truoc.get(t), sau.get(t)
        if a != b:
            lech.append((t, "khác", a, b))
    return (not lech), lech


def in_van_tay(vt, tieu_de=""):
    if tieu_de:
        print("── %s" % tieu_de)
    print("   cổng            : %s" % vt.get("cong"))
    print("   truy cập được   : %s" % vt.get("truy_cap_duoc"))
    print("   PID postmaster  : %s" % vt.get("pid"))
    print("   data_directory  : %s" % vt.get("data_directory"))
    print("   postmaster bắt đầu: %s" % vt.get("postmaster_bat_dau"))
    print("   phiên bản máy chủ: %s" % vt.get("phien_ban_may_chu"))
    print("   số CSDL         : %s" % vt.get("so_csdl"))
    print("   danh sách CSDL  : %s" % " ".join(vt.get("danh_sach_csdl") or []))
    print("   PID nghe TCP    : %s" % (vt.get("nghe_tcp") if vt.get("nghe_tcp") is not None
                                       else "(không chạy được lsof)"))
    if vt.get("ghi_chu"):
        print("   ghi chú         : %s" % vt["ghi_chu"])


def main():
    ap = argparse.ArgumentParser(description="Vân tay cụm PostgreSQL (CHỈ ĐỌC).")
    ap.add_argument("--chup", action="store_true", help="in JSON vân tay rồi thoát")
    ap.add_argument("--cong", default=CONG_MAC_DINH)
    ap.add_argument("--nguoi", default=None)
    ap.add_argument("--may-chu", default="localhost")
    ap.add_argument("--so", nargs=2, metavar=("TRUOC.json", "SAU.json"),
                    help="đối chiếu hai vân tay đã lưu")
    ap.add_argument("--vong", action="store_true",
                    help="chụp–chạy lệnh sau `--`–chụp lại, rồi tự đối chiếu")
    ap.add_argument("lenh", nargs=argparse.REMAINDER)
    a = ap.parse_args()

    if a.so:
        with open(a.so[0], encoding="utf-8") as f:
            t = json.load(f)
        with open(a.so[1], encoding="utf-8") as f:
            s = json.load(f)
        giong, lech = so_sanh(t, s)
        in_van_tay(t, "TRƯỚC (%s)" % a.so[0])
        in_van_tay(s, "SAU (%s)" % a.so[1])
        if giong:
            print("\nVÂN TAY :5432 — TRƯỚC = SAU. Lượt đo KHÔNG đụng cụm hệ thống.")
            return 0
        print("\nVÂN TAY LỆCH — lượt đo ĐÃ ĐỤNG cụm hệ thống:")
        for ten, mo, x, y in lech:
            print("   · %-18s %s: %r → %r" % (ten, mo, x, y))
        return 1

    if a.vong:
        lenh = a.lenh[1:] if a.lenh and a.lenh[0] == "--" else a.lenh
        if not lenh:
            print("--vong cần một lệnh sau `--`", file=sys.stderr)
            return 2
        t = chup(a.cong, a.nguoi, a.may_chu)
        in_van_tay(t, "VÂN TAY TRƯỚC")
        print("\n── chạy: %s" % " ".join(lenh))
        rc = subprocess.call(lenh)
        print("── lệnh trả mã thoát %d" % rc)
        s = chup(a.cong, a.nguoi, a.may_chu)
        in_van_tay(s, "VÂN TAY SAU")
        giong, lech = so_sanh(t, s)
        if not giong:
            print("\nVÂN TAY LỆCH — ĐỤNG CỤM HỆ THỐNG:")
            for ten, mo, x, y in lech:
                print("   · %-18s %s: %r → %r" % (ten, mo, x, y))
            return 2
        print("\nVÂN TAY :%s — TRƯỚC = SAU. Lượt đo KHÔNG đụng cụm hệ thống." % a.cong)
        return rc

    vt = chup(a.cong, a.nguoi, a.may_chu)
    if a.chup:
        print(json.dumps(vt, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if vt["truy_cap_duoc"] else 3
    in_van_tay(vt)
    return 0 if vt["truy_cap_duoc"] else 3


if __name__ == "__main__":
    sys.exit(main())
