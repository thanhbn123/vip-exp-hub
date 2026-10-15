#!/usr/bin/env python3
# Cổng KIỂM CẤU HÌNH TRIỂN KHAI (G11). AG-05 DEVOPS sở hữu file này.
# Dùng: python3 trien_khai/kiem_cau_hinh.py [--env <duong-dan-.env>]
# Mã thoát: 0 = đạt · 1 = có lỗi phải sửa · 2 = chỉ có cảnh báo nhưng đã chọn --nghiem
#
# PHẠM VI (§12.1 luật 5 — câu "0 lỗi" phải nêu công cụ, phạm vi, và cái NGOÀI phạm vi):
#   ĐO: sự tồn tại và nội dung TĨNH của Dockerfile · docker-compose.yml · .env.example ·
#       .dockerignore · .gitignore; cờ nguy hiểm trong `.env` nếu được chỉ tới; việc mã nguồn
#       có bind ra ngoài 127.0.0.1 hay không; việc `.env.example` có giá trị trông như bí mật.
#   NGOÀI PHẠM VI: image có build được không (cần Docker), container có chạy được không,
#       cấu hình HTTPS/proxy/DNS, bí mật THẬT trên máy chủ, và mọi thứ chỉ hiện lúc chạy.
import argparse
import os
import re
import sys

GOC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOI, CANH = [], []


def loi(ma, thong_diep):
    LOI.append((ma, thong_diep))


def canh(ma, thong_diep):
    CANH.append((ma, thong_diep))


def doc(*phan):
    d = os.path.join(GOC, *phan)
    if not os.path.exists(d):
        return None
    with open(d, encoding="utf-8", errors="replace") as f:
        return f.read()


# ---------------------------------------------------------------- 1. file phải có
def c1_file_bat_buoc():
    for ten in ("Dockerfile", "docker-compose.yml", ".env.example", ".dockerignore"):
        if doc(ten) is None:
            loi("C1", f"thiếu {ten}")


# ---------------------------------------------------------------- 2. .env.example sạch
MAU_BI_MAT_THAT = re.compile(r"[A-Za-z0-9+/=_-]{28,}")


def c2_env_example_sach():
    nd = doc(".env.example")
    if nd is None:
        return
    for i, dong in enumerate(nd.split("\n"), 1):
        d = dong.strip()
        if not d or d.startswith("#") or "=" not in d:
            continue
        ten, _, gt = d.partition("=")
        gt = gt.strip()
        if not gt or gt.startswith("THAY-"):
            continue
        if MAU_BI_MAT_THAT.search(gt):
            loi("C2", f".env.example dòng {i}: {ten} có giá trị dài như bí mật thật")
    # Cờ nguy hiểm phải là 0 ngay trong file MẪU — người ta copy nguyên file rồi điền.
    m = re.search(r"(?m)^VIP_HUB_RESET_TOKEN=(.*)$", nd)
    if not m:
        canh("C2", ".env.example không khai VIP_HUB_RESET_TOKEN — người triển khai sẽ không biết nó tồn tại")
    elif m.group(1).strip() != "0":
        loi("C2", f"VIP_HUB_RESET_TOKEN trong .env.example phải là 0, đang là {m.group(1).strip()!r}")


# ---------------------------------------------------------------- 3. .env thật (nếu được chỉ tới)
def c3_env_that(duong):
    if not duong:
        return
    if not os.path.exists(duong):
        loi("C3", f"không thấy {duong}")
        return
    # KHÔNG in giá trị nào ra, kể cả một phần. Chỉ nói TÊN biến và kết luận.
    with open(duong, encoding="utf-8", errors="replace") as f:
        nd = f.read()
    bien = {}
    for dong in nd.split("\n"):
        d = dong.strip()
        if d and not d.startswith("#") and "=" in d:
            k, _, v = d.partition("=")
            bien[k.strip()] = v.strip()
    if bien.get("VIP_HUB_RESET_TOKEN", "0") == "1":
        loi("C3", "VIP_HUB_RESET_TOKEN=1 trong .env — LỖ HỔNG CHIẾM TÀI KHOẢN, phải là 0")
    if bien.get("VIP_HUB_BACKUP_PASSPHRASE"):
        loi("C3", "VIP_HUB_BACKUP_PASSPHRASE có giá trị trong .env của dịch vụ web. "
                  "Tiến trình web KHÔNG cần nó, và `docker inspect` đọc được. Bỏ ra.")
    if bien.get("VIP_HUB_PROXY_TIN_CAY"):
        canh("C3", "VIP_HUB_PROXY_TIN_CAY có giá trị — chỉ đúng khi ĐÃ có proxy thật đứng trước. "
                   "Tin sai là mở đường cho người gọi tự khai địa chỉ và lách sạch rate limit.")
    if not bien.get("VIP_HUB_DATA"):
        canh("C3", "VIP_HUB_DATA không khai — sẽ về mặc định app/du-lieu trong image (chỉ-đọc)")


def _dong_lenh(nd):
    """Bỏ dòng trống và dòng ghi chú. Dockerfile chỉ coi `#` ở ĐẦU dòng là ghi chú."""
    return [d for d in nd.split("\n") if d.strip() and not d.lstrip().startswith("#")]


# ---------------------------------------------------------------- 4. Dockerfile
def c4_dockerfile():
    nd = doc("Dockerfile")
    if nd is None:
        return
    lenh_tho = "\n".join(_dong_lenh(nd))
    if re.search(r"(?im)^\s*COPY\s+\.env\b", lenh_tho):
        loi("C4", "Dockerfile COPY .env — bí mật nằm vĩnh viễn trong layer, `docker history` đọc được")
    if re.search(r"(?im)^\s*COPY\s+\.\s+\.?\s*$", lenh_tho):
        loi("C4", "Dockerfile dùng `COPY . .` — kéo cả repo vào image; liệt kê từng đường")
    if not re.search(r"(?im)^\s*USER\s+(?!root\b)\S+", lenh_tho):
        loi("C4", "Dockerfile không có `USER` khác root")
    for dong in _dong_lenh(nd):
        if re.match(r"(?i)^\s*(ENV|ARG)\s", dong) and MAU_BI_MAT_THAT.search(dong):
            loi("C4", f"ENV/ARG mang giá trị dài như bí mật: {dong.strip()[:60]}")
    if (re.search(r"(?im)^FROM\s+\S+:latest", lenh_tho)
            or re.search(r"(?im)^FROM\s+[^:\s]+\s*$", lenh_tho)):
        loi("C4", "FROM dùng thẻ trôi (`latest` hoặc không thẻ) — image hôm nay và mai khác nhau "
                  "mà không có gì báo")
    # Chỉ đọc DÒNG LỆNH HEALTHCHECK, bỏ mọi dòng ghi chú. Bản đầu của hàm này cắt tại chữ
    # "HEALTHCHECK" xuất hiện trong một dòng `#`, nên nó báo LỖI cho một Dockerfile ĐÚNG — công
    # cụ tự giới hạn phạm vi rồi kết luận ngoài phạm vi ấy, đúng §12.1 luật 3. Đã sửa 15/10/2026.
    lenh = _dong_lenh(nd)
    hc = [d for d in lenh if re.match(r"(?i)^\s*HEALTHCHECK\b", d)]
    if not hc:
        loi("C4", "Dockerfile không có dòng lệnh HEALTHCHECK (dòng ghi chú không tính)")
    else:
        # Lệnh HEALTHCHECK có thể nối dòng bằng `\\` — lấy từ dòng đó tới hết khối nối dòng.
        i = lenh.index(hc[0])
        khoi = []
        while i < len(lenh):
            khoi.append(lenh[i])
            if not lenh[i].rstrip().endswith("\\"):
                break
            i += 1
        sau = "\n".join(khoi)
        if "san-sang" in sau:
            loi("C4", "HEALTHCHECK gọi READINESS. Nó điều khiển việc KHỞI ĐỘNG LẠI, nên một CSDL "
                      "chưa nâng schema sẽ làm container restart vòng quanh và xoá luôn log khởi động.")
        if "suc-khoe" not in sau:
            canh("C4", "HEALTHCHECK không gọi /api/v2/suc-khoe — kiểm lại nó đo cái gì")


# ---------------------------------------------------------------- 5. compose
def c5_compose():
    nd = doc("docker-compose.yml")
    if nd is None:
        return
    if re.search(r"(?m)^\s*-\s*[\"']?0\.0\.0\.0:", nd):
        loi("C5", "compose bind 0.0.0.0 — hệ chưa có HTTPS và chưa đo sau proxy thật")
    if re.search(r"(?m)^\s*-\s*[\"']?\d+:\d+", nd):
        canh("C5", "có `ports` không ghi địa chỉ — Docker mặc định là 0.0.0.0, tức là mở ra mạng")
    if re.search(r"(?i)(passphrase|password|secret|api[_-]?key)\s*:\s*[\"']?\S{8,}", nd):
        loi("C5", "compose ghi bí mật trực tiếp")
    if "privileged: true" in nd:
        loi("C5", "compose dùng privileged: true")
    if "env_file" not in nd:
        canh("C5", "compose không dùng env_file — bí mật dễ bị gõ thẳng vào `environment`")
    if "max-size" not in nd:
        canh("C5", "compose không giới hạn log — một ngày đầy đĩa, và đầy đĩa là hỏng im lặng: "
                   "dịch vụ vẫn chạy, log biến mất")


# ---------------------------------------------------------------- 6. .dockerignore
def c6_dockerignore():
    nd = doc(".dockerignore")
    if nd is None:
        return
    for mau in (".env", "*.key", "*.db", "du-lieu", "*.vipkb", ".git/"):
        if mau not in nd:
            loi("C6", f".dockerignore thiếu `{mau}` — nó sẽ vào build context")


# ---------------------------------------------------------------- 7. .gitignore
def c7_gitignore():
    nd = doc(".gitignore")
    if nd is None:
        loi("C7", "không có .gitignore")
        return
    # AG-00 giữ `.gitignore` — AG-05 KHÔNG sửa, chỉ BÁO. Bản vá đề xuất P-3.
    for mau in (".env",):
        if not re.search(r"(?m)^\s*\.env\s*$", nd):
            loi("C7", "`.gitignore` KHÔNG chặn `.env` — một lượt `git add .` là rò cấu hình "
                      "triển khai. AG-00 giữ file này; xem bản vá đề xuất P-3.")
    if not re.search(r"(?m)^\s*\*\.key\s*$", nd):
        canh("C7", "`.gitignore` không chặn `*.key`. Lớp mạnh hơn đã có: `secret_provider` ghi "
                   "khóa vào `$VIP_HUB_DATA/khoa/` mà `app/du-lieu/` đã bị chặn. Nhưng đặt "
                   "VIP_HUB_DATA vào chỗ khác trong repo thì khóa sẽ vào Git.")
    # `*.vipkb` CỐ Ý không có trong .gitignore — xem rủi ro R-i của dự án: mã hiện TỪ CHỐI ghi
    # gói khóa vào mọi chỗ trong repo mà gitignore không chặn, đó là lớp MẠNH HƠN. Thêm vào
    # gitignore sẽ LÀM YẾU đi và làm ca `h6` của AG-01 hỏng. Không báo gì ở đây là CÓ CHỦ Ý.


# ---------------------------------------------------------------- 8. mã nguồn: bind
def c8_bind_ma_nguon():
    nd = doc("app", "server.py")
    if nd is None:
        return
    if re.search(r'ThreadingHTTPServer\(\(\s*"0\.0\.0\.0"', nd):
        loi("C8", "server.py bind 0.0.0.0 — chưa có HTTPS, chưa đo sau proxy thật")
    elif re.search(r'ThreadingHTTPServer\(\(\s*"127\.0\.0\.1"', nd):
        canh("C8", "server.py GHIM CỨNG bind 127.0.0.1. Trong container nghĩa là KHÔNG AI GỌI "
                   "ĐƯỢC TỪ NGOÀI, kể cả Docker port mapping. Cần bản vá P-1 (AG-00 giữ server.py).")
    # Header bảo mật
    for h in ("X-Content-Type-Options", "Content-Security-Policy", "Referrer-Policy",
              "X-Frame-Options"):
        if h not in nd:
            canh("C8", f"server.py không gửi header `{h}` — bản vá đề xuất P-2")
    if "Secure" not in nd and "SameSite" in nd:
        canh("C8", "cookie phiên có HttpOnly+SameSite nhưng KHÔNG có `Secure`. Đúng cho local "
                   "HTTP; sai ngày có HTTPS. Bản vá P-2.")


def main():
    ap = argparse.ArgumentParser(description="Kiểm cấu hình triển khai VIP Express Hub")
    ap.add_argument("--env", help="đường dẫn .env thật để kiểm (KHÔNG in giá trị nào ra)")
    ap.add_argument("--nghiem", action="store_true", help="coi cảnh báo là lỗi")
    t = ap.parse_args()

    c1_file_bat_buoc()
    c2_env_example_sach()
    c3_env_that(t.env)
    c4_dockerfile()
    c5_compose()
    c6_dockerignore()
    c7_gitignore()
    c8_bind_ma_nguon()

    for ma, td in LOI:
        print(f"  LOI  [{ma}] {td}")
    for ma, td in CANH:
        print(f"  CANH [{ma}] {td}")
    print(f"  --> {len(LOI)} loi, {len(CANH)} canh bao.")
    print("  PHAM VI: do noi dung TINH cua Dockerfile/compose/.env.example/.dockerignore/"
          ".gitignore + bind & header trong server.py.")
    print("  NGOAI PHAM VI: image co build duoc khong, container co chay duoc khong, HTTPS/proxy/"
          "DNS, bi mat THAT tren may chu, va moi thu chi hien luc chay.")
    if LOI:
        return 1
    if CANH and t.nghiem:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
