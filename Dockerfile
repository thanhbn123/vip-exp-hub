# VIP Express Hub — image container cho STAGING (G11). AG-05 DEVOPS sở hữu file này.
#
# ====== BA ĐIỀU PHẢI BIẾT TRƯỚC KHI ĐỌC TIẾP ======
# 1. Image này CHƯA BAO GIỜ ĐƯỢC BUILD. Máy MacBook dựng nó (đo 15/10/2026) KHÔNG CÓ Docker:
#    `docker --version` → `command not found`. Mọi dòng dưới đây là viết cho đúng theo mã thật,
#    đã soát cú pháp và soát tính nhất quán với mã — nhưng **chưa có lượt build nào**.
#    Báo cáo G11 ghi dòng này là **BLOCKED**, không phải PASS (§12.1: không tự nhận ĐẠT khi
#    chưa chạy). Ai build lượt đầu thì xem `trien_khai/RUNBOOK.md` mục 2.
# 2. KHÔNG có bí mật nào trong image. Không `COPY .env`, không `ENV` mang khóa. Bí mật vào lúc
#    CHẠY qua biến môi trường hoặc file mount, không vào lúc BUILD — layer image là vĩnh viễn và
#    đọc được bằng `docker history`, nên một khóa lỡ nhúng vào là một khóa đã rò.
# 3. Dự án là stdlib Python + `cryptography`. Không thêm thư viện nào khác (ràng buộc kiến trúc).

# python:3.11-slim-bookworm. Mã dự án chạy trên Python 3.9 (máy dựng đo được 3.9.6) và không
# dùng cú pháp nào sau 3.9 — 3.11 là tương thích tiến. KHÔNG dùng thẻ `latest`: thẻ trôi làm
# image hôm nay và image mai khác nhau mà không có gì báo.
# CHƯA ĐO: digest SHA256 của thẻ này. Ghim digest là việc nên làm và chưa làm được vì không có
# Docker để `docker manifest inspect` — xem BLOCKED B-G11-2 trong báo cáo.
FROM python:3.11-slim-bookworm

# PYTHONUNBUFFERED: log phải ra NGAY. Đệm stdout làm log mất khi container bị kill — và lúc cần
# log nhất chính là lúc container bị kill.
# PYTHONDONTWRITEBYTECODE: không ghi .pyc vào thư mục mã (mã để chỉ-đọc).
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/app \
    VIP_HUB_DATA=/du-lieu \
    VIP_HUB_PORT=8897

WORKDIR /app

# Phụ thuộc cài TRƯỚC khi chép mã: lớp này chỉ dựng lại khi danh sách phụ thuộc đổi.
# `cryptography` cần bản wheel; slim-bookworm có wheel sẵn cho linux/amd64 và linux/arm64.
# Ghim phiên bản CHÍNH XÁC: `cryptography` từng đổi API giữa các bản lớn, và một bản trôi làm
# mã hóa credentials hỏng ở lượt deploy chứ không ở lượt build.
RUN pip install --no-cache-dir "cryptography==43.0.1"

# Chép mã. `.dockerignore` chặn `.env`, `*.key`, `*.db`, `du-lieu/`, `*.vipkb` — tức là build
# context KHÔNG mang theo khóa hay CSDL của máy dựng. Đó là lớp chặn thật; dòng COPY này chỉ
# đúng khi `.dockerignore` còn nguyên, nên có ca thử `thu_quan_sat.H_*.test_h5` canh nó.
COPY app/ /app/app/
COPY admin/ /app/admin/
COPY pages/ /app/pages/
COPY assets/ /app/assets/
COPY mock/ /app/mock/
COPY index.html /app/index.html
COPY trien_khai/ /app/trien_khai/

# Người dùng KHÔNG PHẢI root. Thư mục dữ liệu là chỗ DUY NHẤT ghi được; mã là chỉ-đọc.
# Quyền 700 cho thư mục dữ liệu vì nó chứa khóa mã hóa (`du-lieu/khoa/*.key`, mode 0600).
RUN groupadd -r hub && useradd -r -g hub -d /du-lieu -s /usr/sbin/nologin hub \
 && mkdir -p /du-lieu \
 && chown -R hub:hub /du-lieu \
 && chmod 700 /du-lieu \
 && chmod 755 /app/trien_khai/*.sh \
 && chmod -R a-w /app

VOLUME ["/du-lieu"]
USER hub
EXPOSE 8897

# ====== HEALTHCHECK = HEALTH, KHÔNG PHẢI READINESS ======
# Cố ý gọi `/api/v2/suc-khoe`, KHÔNG gọi `/api/v2/san-sang`.
# Vì sao: HEALTHCHECK của Docker điều khiển việc KHỞI ĐỘNG LẠI. Nếu nó đo readiness thì một CSDL
# chưa nâng schema (thứ cần NGƯỜI chạy migration) sẽ làm container khởi động lại vòng quanh mãi
# — vòng lặp đó xoá luôn log khởi động, tức là xoá đúng thứ cần để chẩn đoán. Readiness là việc
# của bộ cân tải / cổng triển khai, gọi bằng `trien_khai/kiem_san_sang.sh`.
# Phép đo này nằm ở MỘT TIẾN TRÌNH KHÁC và đi qua HTTP thật — tiến trình tự khẳng định mình
# sống là lời khai, không phải phép đo (§12.1).
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python3 -c "import os,urllib.request,sys;\
u='http://127.0.0.1:%s/api/v2/suc-khoe'%os.environ.get('VIP_HUB_PORT','8897');\
sys.exit(0 if urllib.request.urlopen(u,timeout=4).status==200 else 1)"

# `khoi_dong.sh` KHÔNG tự chạy migration (xem lý do trong chính script đó).
ENTRYPOINT ["/app/trien_khai/khoi_dong.sh"]
