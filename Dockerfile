# VIP Express Hub — image container cho STAGING (G11). AG-05 DEVOPS sở hữu file này.
#
# ====== BA ĐIỀU PHẢI BIẾT TRƯỚC KHI ĐỌC TIẾP ======
# 1. Image ĐÃ ĐƯỢC BUILD và self-test cô lập trên VPS 160.22.170.20 ngày 2026-10-19 (lượt
#    AG-06): health/ready 200, restart healthy. Máy MacBook dựng mã vẫn KHÔNG có Docker, nên
#    mọi lượt build phải chạy trên VPS hoặc máy có Docker; đừng đọc dòng này như "đã build trên
#    máy dựng". Bằng chứng nằm trong docs/VPS_DEPLOYMENT_SURVEY.md.
# 2. KHÔNG có bí mật nào trong image. Không `COPY .env`, không `ENV` mang khóa. Bí mật vào lúc
#    CHẠY qua biến môi trường hoặc file mount, không vào lúc BUILD — layer image là vĩnh viễn và
#    đọc được bằng `docker history`, nên một khóa lỡ nhúng vào là một khóa đã rò.
# 3. Dự án là stdlib Python + `cryptography`. Không thêm thư viện nào khác (ràng buộc kiến trúc).

# python:3.11-slim-bookworm, GHIM CẢ DIGEST (đo trên VPS 2026-10-19). Thẻ trôi làm image hôm
# nay và image mai khác nhau mà không có gì báo; digest thì không trôi. Khi cần nâng:
#   docker image inspect -f '{{json .RepoDigests}}' python:3.11-slim-bookworm
# rồi thay cả tag + digest dưới đây và build lại. ARG để bộ dựng có thể ghim digest riêng mà
# không sửa thân Dockerfile, nhưng mặc định PHẢI là digest đã đo.
ARG PYTHON_IMAGE=python:3.11-slim-bookworm@sha256:0a310eeecf4e1f5a0743f9a6520c90c88d089c903ca5fd283f501e3a805f5f89
FROM ${PYTHON_IMAGE}

# UID/GID của user trong image. PHẢI khớp `user:` của compose và chủ sở hữu bind mount
# /home/deploy/vip-express-hub/data (đo trên VPS: 1000:1000). Trước AG-06 image tạo user hệ
# thống UID 999 trong khi compose chạy 1000: hai bên lệch nhau, và một `docker run` không có
# compose (hoặc volume ẩn danh) sẽ ghi /du-lieu bằng UID 999 trong khi bind mount thật thuộc
# 1000. Đây là lỗi quyền thật, không phải chuyện thẩm mỹ.
ARG HUB_UID=1000
ARG HUB_GID=1000

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

# Chép mã. ====== VÌ SAO COPY TỪNG TỆP, KHÔNG `COPY trien_khai/` ======
# Root `.dockerignore` có `.env` và `.env.*`, nhưng Docker khớp mẫu với ĐƯỜNG DẪN ĐẦY ĐỦ: mẫu
# `.env` chỉ khớp `.env` ở GỐC context, KHÔNG khớp `trien_khai/vps/.env` (đã đo lượt AG-06:
# bản build `COPY trien_khai/` mang đúng `/app/trien_khai/vps/.env` vào image). Đó là rò bí mật
# thật khi file .env của VPS có giá trị thật, và `docker history`/`docker save` vẫn thấy nó kể
# cả khi có lớp `rm` phía sau. Vì vậy image chỉ COPY những tệp runtime THẬT SỰ cần:
#   · entrypoint `khoi_dong.sh`;
#   · script chạy trong container: bootstrap admin.
# Các script backup/restore/Caddy/kiểm tra chạy trên HOST, không vào image. `.dockerignore` vẫn
# là lớp phụ; lớp chặn thật là danh sách COPY này và phép `test` bên dưới.
COPY app/ /app/app/
COPY admin/ /app/admin/
COPY pages/ /app/pages/
COPY assets/ /app/assets/
COPY mock/ /app/mock/
COPY index.html /app/index.html
COPY trien_khai/khoi_dong.sh /app/trien_khai/khoi_dong.sh
COPY trien_khai/vps/bootstrap_admin.py /app/trien_khai/vps/bootstrap_admin.py

# Người dùng KHÔNG PHẢI root. Thư mục dữ liệu là chỗ DUY NHẤT ghi được; mã là chỉ-đọc.
# Quyền 700 cho thư mục dữ liệu vì nó chứa khóa mã hóa (`du-lieu/khoa/*.key`, mode 0600).
# Tạo user THƯỜNG với UID/GID tường minh (không `-r`): compose chạy đúng UID này, nên image
# chạy độc lập (không compose, volume ẩn danh) cũng ghi được /du-lieu.
# Chốt build: entrypoint phải còn bit thực thi sau `a-w`; thiếu là container chết ngay và
# không ai thấy vì sao. Đây là phép đo lúc build, không phải lời hứa trong comment.
RUN groupadd --gid "$HUB_GID" hub \
 && useradd --uid "$HUB_UID" --gid hub --home-dir /du-lieu --no-create-home \
            --shell /usr/sbin/nologin hub \
 && mkdir -p /du-lieu \
 && chown -R hub:hub /du-lieu \
 && chmod 700 /du-lieu \
 && chmod 755 /app/trien_khai/*.sh \
 && chmod -R a+rX /app \
 && chmod -R a-w /app \
 && test -x /app/trien_khai/khoi_dong.sh \
 && test -z "$(find /app -type f \( -name '.env' -o -name '.env.*' \) -print -quit)"

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
