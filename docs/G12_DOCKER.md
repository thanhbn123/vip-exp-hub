# G12 — DOCKER: **BLOCKED**, soát tĩnh được tới đâu, và lệnh cài cho anh Thành

**Tác tử:** AG-04 DATA PLATFORM ENGINEER · **Ngày đo:** 15/10/2026
**Máy đo:** MacBook (Darwin arm64) · Homebrew 7.0.9 · Python 3.9.6

---

## 0. TRẠNG THÁI: **BLOCKED** — và vì sao nói thẳng ra thay vì báo đạt

```
$ which docker podman colima
docker not found
podman not found
colima not found
```

**Không có lượt `docker build` nào. Không có lượt `docker compose up` nào.**
AG-05 đợt trước đã ghi dòng này là BLOCKED; **G12 không đổi được điều đó**, vì cài Docker là
**đổi máy của anh Thành** — việc đó phải hỏi, và chưa hỏi thì chưa làm.

> **CẤM nói "Docker build PASS".** Mọi thứ trong tài liệu này là **soát tĩnh**: đọc tệp, đối
> chiếu với mã, chạy vài phép đếm. Soát tĩnh **không thay** được một lượt build, và mục 3 nói
> rõ cái gì chỉ build mới biết. Đây đúng ca §12.1: thứ dùng để kiểm chứng (ở đây là mắt người
> đọc Dockerfile) chỉ nói được trong phạm vi nó đo.

---

## 1. ĐÃ KIỂM ĐƯỢC GÌ, BẰNG CÁCH NÀO

Mười phép đo, nêu rõ công cụ và **cái gì nằm ngoài** từng phép.

| # | Phép đo | Công cụ | Kết quả | NGOÀI phạm vi |
|---|---|---|---|---|
| **D1** | Bảy đường `COPY` có tồn tại thật | `grep ^COPY` + `test -e` từng đường | **7/7 CÓ** (`app/` `admin/` `pages/` `assets/` `mock/` `index.html` `trien_khai/`) | quyền tệp, symlink, đường bên trong image |
| **D2** | Có `COPY . .` không | `grep -cE "^COPY \. "` | **0** — đúng như AG-05 nói, lớp chặn thật là liệt kê từng đường | — |
| **D3** | Thẻ image nền có ghim | `grep ^FROM` | `python:3.11-slim-bookworm` — **không** `latest`. Nhưng **chưa ghim digest** (BLOCKED B-G11-2 của AG-05 vẫn mở) | thẻ có tồn tại trên registry không |
| **D4** | `ENV`/`ARG` có mang bí mật | `grep` tên biến trên dòng `ENV`/`ARG` | **không thấy**. 5 biến: `PYTHONUNBUFFERED` `PYTHONDONTWRITEBYTECODE` `PYTHONPATH` `VIP_HUB_DATA` `VIP_HUB_PORT` | giá trị `--build-arg` truyền lúc build |
| **D5** | Build context sau `.dockerignore` | mô phỏng bằng Python `fnmatch` | **154 tệp / 2,8 MB** → loại **84 tệp / 1,5 MB** → còn **70 tệp / 1,3 MB** | **phép mô phỏng KHÔNG cài đặt luật phủ định `!`**, xem 1.1 |
| **D6** | `trien_khai/postgres/` (thư mục MỚI của G12) có lọt vào image | `grep` `.dockerignore` | **CÓ LỌT** — xem mục 4, đây là phát hiện cần vá | — |
| **D7** | Chỉ thị Dockerfile hợp lệ | phân tích từ khoá đầu dòng lệnh, có xử lý dòng nối `\` | **17 chỉ thị · 0 chỉ thị lạ** | **cú pháp BÊN TRONG mỗi chỉ thị** — đây là giới hạn lớn, xem mục 3 |
| **D8** | `docker-compose.yml` là YAML hợp lệ | **KHÔNG ĐO ĐƯỢC** — máy không có PyYAML và repo cấm thư viện ngoài | soát chuỗi thay thế: **0 dòng chứa TAB**, 2 khoá gốc (`services` `volumes`), bind `127.0.0.1:8897:8897`, không `privileged`, có đủ `read_only` `no-new-privileges` `cap_drop` `mem_limit` `pids_limit` | **tính hợp lệ YAML thật**, hợp lệ của lược đồ compose |
| **D9** | Thư viện ngoài stdlib mà `app/` cần | AST + `importlib.util.find_spec`, đối chiếu đường dẫn với `sysconfig` stdlib | **đúng một: `cryptography`** — khớp với `pip install "cryptography==43.0.1"` của Dockerfile | `gateway/`, `app/thu/` |
| **D10** | `ENTRYPOINT` tồn tại và chạy được | `ls -l` + đọc dòng đầu | `trien_khai/khoi_dong.sh` có, `-rwxr-xr-x`, shebang `#!/bin/sh` | hành vi lúc chạy trong container |

### 1.1 Một phép đo của chính tôi đã nói sai — ghi ra

**D5 không cài đặt luật phủ định của `.dockerignore`.** Tệp có ba dòng theo thứ tự:
```
.env
.env.*
!.env.example
```
Docker xử theo thứ tự, **luật khớp SAU thắng**, nên `.env.example` **được đưa vào** build
context. Trình mô phỏng của tôi bỏ qua dấu `!` nên nó **đếm `.env.example` là bị loại**. Con
số "84 tệp bị loại" vì thế **lệch 1 tệp (3,4 KB)**, và chiều lệch là **đếm thừa**.

Đưa vào đây chứ không im, vì đó đúng là chuyện §12.1 đang nói: *công cụ mình vừa tự tay giới
hạn cũng là một công cụ cần nghi ngờ.* Phép đo đúng là lệnh ở **RUNBOOK 2.3** — `find` **bên
trong image đã build** — và lệnh đó **chưa chạy được**.

### 1.2 Một kết quả quét trông như lỗi nhưng không phải
Phép soát chuỗi D8 báo `có 0.0.0.0: True`. Đọc tệp thì chuỗi đó nằm **trong một dòng chú
thích** cảnh báo *đừng* đổi sang `0.0.0.0`. Cổng thật bind `127.0.0.1:8897:8897`.
**Không phải lỗi — là phép đo bắt nhầm.** Ghi ra để lần sau không ai "sửa" nhầm.

---

## 2. MỘT PHÁT HIỆN ĐỐI CHIẾU VỚI MÃ: `cryptography` ghim 43.0.1, máy đang chạy 50.0.1

| Chỗ | Bản `cryptography` |
|---|---|
| Dockerfile `pip install` | **43.0.1** (ghim cứng) |
| MacBook này, đo 15/10/2026 | **50.0.1** |

Ghim bản là **đúng** (Dockerfile đã nêu lý do: bản trôi làm mã hoá credentials hỏng ở lượt
deploy chứ không ở lượt build). Nhưng hệ quả phải biết: **794 ca thử hiện chạy trên 50.0.1,
không ca nào chạy trên 43.0.1.** Tức là bản sẽ chạy trong container là bản **chưa được bộ thử
nào chạm tới** — khoảng **7 bản lớn** cách nhau.

Đây là rủi ro **có thật nhưng không khẩn**: `bao_mat.py` dùng AES-256-GCM qua API ổn định.
**Cách vá đúng:** lượt build đầu tiên phải chạy **toàn bộ bộ thử BÊN TRONG container**, không
chỉ `docker build` xong rồi kết luận. Thêm vào RUNBOOK mục 2 thành phép nghiệm thu **2.4**.
*(Tệp RUNBOOK thuộc AG-05 — đây là đề xuất, AG-04 không tự sửa.)*

---

## 3. CHỈ BUILD MỚI BIẾT — nói thẳng

Những thứ dưới đây **không có cách nào soát tĩnh**. Đừng ai đọc mục 1 rồi tưởng Dockerfile đã
được nghiệm thu.

| # | Chỉ build/chạy mới biết | Vì sao soát tĩnh chịu thua | Hỏng thì thế nào |
|---|---|---|---|
| 1 | `python:3.11-slim-bookworm` có kéo được cho `linux/arm64` không | cần mạng + registry | build dừng ngay — **hỏng ồn ào**, loại nhẹ |
| 2 | `pip install "cryptography==43.0.1"` có wheel cho arm64 không | cần PyPI | không có wheel thì phải biên dịch → cần toolchain mà slim-bookworm **không có** → build hỏng |
| 3 | Mã chạy đúng trên **Python 3.11** (hiện chỉ đo trên **3.9.6**) | khác bản thông dịch | 3.11 chặt hơn ở vài chỗ cú pháp/thư viện. **Có thể hỏng im lặng** |
| 4 | `groupadd`/`useradd` có trong slim-bookworm không | phụ thuộc gói image nền | build hỏng ở lớp `RUN` |
| 5 | `chmod 755 /app/trien_khai/*.sh` có khớp tệp nào không | glob chạy trong image | glob không khớp → `chmod` lỗi → build hỏng. *(Soát tĩnh: `trien_khai/` CÓ 5 tệp `.sh` ở mức gốc, nên nhiều khả năng khớp)* |
| 6 | `chmod -R a-w /app` có làm hỏng gì lúc chạy không | cần chạy thật | ghi vào `/app` sẽ hỏng; `PYTHONDONTWRITEBYTECODE=1` đã lo `.pyc`, **chưa đo chỗ khác** |
| 7 | `HEALTHCHECK` có thật sự xanh không | cần container chạy | **Đây là loại tệ nhất.** Healthcheck sai làm container **khởi động lại vòng quanh**, và vòng lặp đó **xoá log khởi động** — xoá đúng thứ cần để chẩn đoán |
| 8 | Có bí mật lọt vào layer không | `docker history` | **RUNBOOK 2.1 là phép đo đúng.** Mục 1 chỉ kiểm *ý định*, không kiểm *kết quả* |
| 9 | Tệp nào thật sự nằm trong image | `find` trong image | **RUNBOOK 2.3.** Xem 1.1 — đây đúng chỗ phép mô phỏng của tôi đã nói sai |
| 10 | `mem_limit: 512m` · `pids_limit: 512` có đủ không | cần tải thật | AG-05 đã ghi là **ước lượng** (blocker B-G11-11). G12 **không** đo thêm được gì |
| 11 | `docker-compose.yml` có hợp lệ về lược đồ không | `docker compose config` | — |

---

## 4. PHÁT HIỆN CẦN VÁ: `trien_khai/postgres/` sẽ lọt vào image production

`Dockerfile` có `COPY trien_khai/ /app/trien_khai/`. G12 vừa thêm `trien_khai/postgres/`
(3 tệp, ~27 KB): một bộ dựng cụm PostgreSQL thử, một trình sinh DDL, một bộ đo ghi đồng thời.
**Không tệp nào có việc gì trong một image chạy thật.**

Chưa nguy hiểm — không có bí mật, không có gì chạy tự động, `ENTRYPOINT` vẫn là
`khoi_dong.sh`. Nhưng nó sai nguyên tắc: image chạy thật chỉ nên mang thứ cần để chạy. Và nó
cũng là **ca thử cho chính luật** của AG-05: `.dockerignore` là **danh sách đen**, mà danh
sách đen thì **quên một mục là lọt im lặng** — đây là mục bị quên đầu tiên, chỉ 1 ngày sau khi
rủi ro r-1 được ghi ra.

**Bản vá đề xuất** — thêm vào `.dockerignore` (tệp của AG-05/AG-00, AG-04 **không tự sửa**):

```diff
 docs/
 thu_frontend/
 app/thu/
 gateway/
+# Công cụ THỬ PostgreSQL của G12 — chỉ dùng lúc khảo sát, không có việc gì trong image chạy.
+# `COPY trien_khai/` mang cả thư mục, nên không loại ở đây là nó vào image.
+trien_khai/postgres/
```

Ca thử `thu_quan_sat.py::test_h5` chỉ đòi `.dockerignore` **có chứa** các mẫu `.env` `*.key`
`*.db` `du-lieu` `*.vipkb` — thêm một dòng **không làm hỏng ca đó** (đã đọc ca thử, dòng
542–547).

**Vá gốc hơn, nếu AG-05 muốn:** `COPY trien_khai/khoi_dong.sh /app/trien_khai/` và liệt kê
từng script cần — tức là áp đúng nguyên tắc *"liệt kê từng đường"* mà Dockerfile đã dùng cho
mức thư mục, nhưng xuống một mức nữa. Lúc đó quên một mục chỉ làm **thiếu**, không làm **thừa**.

---

## 5. LỆNH CÀI DOCKER CHO MÁY NÀY — để anh Thành chạy **nếu anh đồng ý**

> **AG-04 KHÔNG chạy những lệnh này.** Cài là đổi máy của anh. Viết sẵn cho `zsh` — đúng shell
> anh dùng (`CLAUDE.md` §12.2: `read -s -p` là cú pháp bash, đã làm hỏng một lượt chẩn đoán).

Ba đường, **khuyến nghị đường A**.

### Đường A — Colima + docker CLI (NHẸ, khuyến nghị)

```zsh
# 1. Cài (ba gói, đều là formula Homebrew — không phải ứng dụng có giao diện)
brew install colima docker docker-compose

# 2. Nối plugin compose cho docker CLI — Homebrew KHÔNG tự nối.
#    Đường dưới đây chép từ `brew info --formula docker-compose` mục Caveats, đọc ngày
#    15/10/2026, KHÔNG viết theo trí nhớ (bản nháp đầu của tài liệu này viết một lệnh
#    `ln -s` khác với caveat chính thức — đã sửa).
mkdir -p ~/.docker
python3 - <<'EOF'
import json, os, pathlib
p = pathlib.Path.home() / ".docker" / "config.json"
c = json.loads(p.read_text()) if p.exists() and p.read_text().strip() else {}
d = c.setdefault("cliPluginsExtraDirs", [])
if "/opt/homebrew/lib/docker/cli-plugins" not in d:
    d.append("/opt/homebrew/lib/docker/cli-plugins")
tmp = p.with_suffix(".json.tmp")              # ghi file tạm rồi đổi tên (CLAUDE.md §16.3)
tmp.write_text(json.dumps(c, indent=2))
os.replace(tmp, p)
print("đã thêm cliPluginsExtraDirs vào", p)
EOF

# 3. Khởi động máy ảo Linux (lượt đầu TẢI ảnh đĩa, cần mạng)
colima start --cpu 2 --memory 4 --disk 20

# 4. NGHIỆM THU — bằng một lượt CHẠY THẬT, không bằng `--version`
docker run --rm hello-world
docker compose version
```

**Bản đo được trên máy này hôm nay** (`brew info`, 15/10/2026 — **không cài gì**):

| Gói | Bản | Loại |
|---|---|---|
| `colima` | 0.10.3 | formula |
| `docker` (CLI) | 29.9.0 | formula |
| `docker-compose` | 5.6.0 | formula |

**Cái gì đổi trên máy:**
* thêm 3 formula vào `/opt/homebrew` (+ phụ thuộc: `lima`, `qemu`…);
* `colima start` tạo **một máy ảo Linux** ở `~/.colima/`, ảnh đĩa **20 GB cấp phát thưa**
  (chiếm dần theo dung lượng dùng thật, không chiếm 20 GB ngay);
* tạo `~/.docker/`;
* **không** cài system extension, **không** đòi quyền quản trị, **không** tự chạy lúc khởi
  động máy (phải `colima start` mỗi lần).

**Gỡ sạch:**
```zsh
colima delete            # xoá máy ảo + ảnh đĩa
brew uninstall colima docker docker-compose
rm -rf ~/.colima ~/.docker
```

### Đường B — Docker Desktop (NẶNG, chỉ chọn nếu anh muốn giao diện)

```zsh
brew install --cask docker-desktop
open -a "Docker Desktop"        # lượt đầu phải bấm đồng ý trong cửa sổ
docker run --rm hello-world
```
Bản đo được hôm nay: **4.94.0,241994**.
**Cái gì đổi:** cài một ứng dụng vào `/Applications`, **cài privileged helper** (đòi mật khẩu
quản trị), **tự chạy lúc đăng nhập** theo mặc định, chiếm nhiều RAM nền hơn A.
**Giấy phép:** Docker Desktop **thu phí với doanh nghiệp lớn**. Dùng cá nhân/doanh nghiệp nhỏ
thì miễn phí — nhưng đây là ràng buộc pháp lý, **không phải việc AG-04 kết luận thay anh**.
Đường A không có ràng buộc này (Apache-2.0 / MIT).

### Đường C — Podman (không cần daemon)
```zsh
brew install podman podman-compose
podman machine init --cpus 2 --memory 4096 --disk-size 20
podman machine start
podman run --rm hello-world
```
Bản đo được: **6.1.3**. `docker-compose.yml` của dự án **phần lớn** chạy với `podman-compose`,
nhưng `podman-compose` **không phủ hết** đặc tả compose — **chưa đo** với tệp cụ thể này.

### Dung lượng tải — **CHƯA ĐO, không bịa**
`brew info` **không in dung lượng tải**, và đo thật thì phải tải — tức là phải cài. Nên:

| Đường | Dung lượng tải | Trạng thái |
|---|---|---|
| A (Colima) | — | **CHƯA ĐO** |
| B (Desktop) | — | **CHƯA ĐO** |
| C (Podman) | — | **CHƯA ĐO** |

Thứ **đo được** là xếp hạng tương đối theo kiến trúc: **A và C cùng cỡ** (một máy ảo Linux
tối giản + CLI), **B lớn hơn hẳn** (máy ảo + ứng dụng giao diện Electron + helper hệ thống).
Muốn con số thật, lệnh này in ra **trước khi** cài gì:
```zsh
brew fetch --formula colima docker docker-compose && du -sh "$(brew --cache)"
```

---

## 6. SAU KHI CÀI — chạy đúng thứ tự này, đừng bỏ bước

```zsh
cd ~/code/veh4-g12-data

# B1 — build
docker build -t vip-express-hub:0.3-saas-local .

# B2 — ba phép nghiệm thu của RUNBOOK mục 2 (ĐỘC LẬP với .dockerignore)
docker history --no-trunc vip-express-hub:0.3-saas-local \
  | grep -Ei 'passphrase|secret|api_key|\.env' && echo "CO BI MAT — DUNG LAI"
docker image inspect vip-express-hub:0.3-saas-local --format '{{.Config.User}}'   # phải là: hub
docker run --rm --entrypoint sh vip-express-hub:0.3-saas-local -c \
  'find / -xdev \( -name "*.key" -o -name "*.db" -o -name "*.vipkb" -o -name ".env" \) 2>/dev/null'
# phải KHÔNG in gì

# B3 — ĐỀ XUẤT MỚI của G12: chạy bộ thử BÊN TRONG container, vì nó dùng
#      cryptography 43.0.1 còn máy anh đang chạy 50.0.1 (mục 2)
docker run --rm --entrypoint sh vip-express-hub:0.3-saas-local -c \
  'cd /app && python3 -c "import cryptography; print(cryptography.__version__)"'

# B4 — compose hợp lệ về lược đồ?
docker compose config >/dev/null && echo "compose HOP LE"
```

**Ba điều KHÔNG làm:**
1. **Không** `docker compose down -v` — `-v` xoá volume `vip_hub_du_lieu`, tức là xoá **khóa
   mã hoá thật** (RUNBOOK mục 9).
2. **Không** đổi `127.0.0.1:8897:8897` thành `0.0.0.0` — hệ **chưa có HTTPS** (blocker B-G11-8).
3. **Không** mang compose này lên VPS — **V-G11-01 CHƯA ĐƯỢC CẤP QUYỀN** (SHARED_CONTRACTS §25).

---

## 7. RỦI RO CỐ Ý BỎ QUA

| # | Rủi ro | Vì sao chấp nhận | Vá đúng |
|---|---|---|---|
| d-1 | **Không build lượt nào** | Cài Docker là đổi máy anh ⇒ phải hỏi | Mục 5 rồi mục 6 |
| d-2 | **Trình mô phỏng `.dockerignore` không hiểu `!`** (mục 1.1) | Viết cho đúng luật Docker tốn nhiều hơn giá trị nó mang; phép đo đúng là RUNBOOK 2.3 | Dùng `find` trong image sau khi build |
| d-3 | **`.dockerignore` vẫn là danh sách đen** | Lý do của AG-05 (r-1) còn đúng. Nhưng mục 4 cho thấy nó **đã rò** sau đúng 1 ngày | Vá ngắn: thêm `trien_khai/postgres/`. Vá gốc: `COPY` liệt kê từng script |
| d-4 | **Không kiểm cú pháp bên trong từng chỉ thị** (D7) | Không có bộ phân tích Dockerfile, và repo cấm thư viện ngoài | `docker build` tự làm việc này |
| d-5 | **Không kiểm được YAML của compose** (D8) | Không có PyYAML | `docker compose config` |
| d-6 | **Chưa ghim digest image nền** (D3) | Blocker **B-G11-2** của AG-05, cần `docker manifest inspect` | Ghim digest ở lượt build đầu |
| d-7 | **Mã chưa chạy trên Python 3.11 lượt nào** | Máy có 3.9.6; cài 3.11 cũng là đổi máy anh | B3 ở mục 6 — chạy bộ thử trong container |
| d-8 | **`cryptography` 43.0.1 chưa được bộ thử nào chạm** (mục 2) | Ghim bản là đúng; cài 43.0.1 lên máy anh để thử là đổi máy anh | Chạy bộ thử trong container; đề xuất thành RUNBOOK 2.4 |

---

## 8. TÓM TẮT CHO ANH THÀNH

| Hạng mục | Trạng thái |
|---|---|
| Docker trên máy | **KHÔNG CÓ** (`docker`/`podman`/`colima` đều không) |
| `docker build` | **BLOCKED** — chờ anh đồng ý cài |
| `docker compose up` | **BLOCKED** — như trên |
| Soát tĩnh Dockerfile | **10 phép đo, không thấy lỗi** trong phạm vi mục 1 |
| Bí mật trong Dockerfile/compose | **không thấy** — nhưng phép đo đúng (`docker history`) **chưa chạy được** |
| Phát hiện cần vá | **1** — `trien_khai/postgres/` lọt vào image (mục 4), có bản vá sẵn |
| Phát hiện cần biết | **1** — `cryptography` ghim 43.0.1, bộ thử chỉ chạy trên 50.0.1 (mục 2) |
| Anh cần quyết | Có cài Docker không. Nếu có: **đường A (Colima)**, lệnh ở mục 5 |

---

# PHỤ LỤC G15 (15/10/2026, AG-04) — XÁC NHẬN LẠI: DOCKER VẪN **BLOCKED**

> Bổ sung, không thay thế mục nào ở trên. Báo cáo đầy đủ: [`G15_INFRA.md`](G15_INFRA.md) §4.1.
> Chạy lại: `python3 trien_khai/g15/kiem_ha_tang.py` (phần P1).

## Q.1 Đo lại trên PATH, 15/10/2026

```
docker         = KHÔNG CÓ
podman         = KHÔNG CÓ
colima         = KHÔNG CÓ
docker-compose = KHÔNG CÓ
brew           = /opt/homebrew/bin/brew   (CÓ)
```

**`Docker build` và `docker compose up` vẫn là BLOCKED.** Cài được bằng `brew`, nhưng **cài là
đổi máy của anh Thành ⇒ phải anh duyệt** (`V-13913`, `SHARED_CONTRACTS.md` §27/§29).
**Lượt G15 KHÔNG cài gì.**

> **KHÔNG có — và KHÔNG được có — dòng "Docker build PASS" nào trong bất kỳ tài liệu nào của
> G15.** `Dockerfile` (4.681 byte) · `docker-compose.yml` (3.485 byte) · `.dockerignore`
> (1.744 byte) **đã viết nhưng CHƯA CHẠY LƯỢT NÀO**. Phép đo duy nhất làm được là **soát tĩnh**
> (đã làm ở mục 1–5 ở trên), và soát tĩnh **không** chứng minh được `HEALTHCHECK`,
> `read_only: true`, `tmpfs`, hay `security_opt` chạy đúng.

## Q.2 Một điều G15 đo được mà Docker sẽ **không** sửa

`HEALTHCHECK` của `Dockerfile` gọi `/api/v2/suc-khoe` (health), cố ý **không** gọi `/san-sang`
(readiness) — lý do ở mục "HEALTHCHECK = HEALTH, KHÔNG PHẢI READINESS" trong `Dockerfile`.
Lượt G15 **đo lại và xác nhận chủ ý đó là đúng**, bằng một đối chứng âm thật:

| Phép đo (nền migrate đủ nhưng **thiếu khoá mã hoá**) | Kết quả |
|---|---|
| `GET /api/v2/suc-khoe` | **200** — nên bộ giám sát **KHÔNG** restart vòng quanh |
| `GET /api/v2/san-sang` | **503** · **chỉ** phép kiểm `khoa` hỏng, 4 phép kia vẫn chạy (không ngắn mạch) |

Nghĩa là khi Docker được cài, `HEALTHCHECK` sẽ hành xử đúng như thiết kế — nhưng **điều đó vẫn
chưa được chứng minh bằng một lượt chạy container nào**, vì **chưa có container nào chạy**.

## Q.3 Việc G15 thêm vào danh sách chờ Docker

| # | Việc | Vì sao cần Docker |
|---|---|---|
| 1 | Chạy `docker build` + `docker compose up` lượt đầu tiên | `V-13913` |
| 2 | Chứng minh `HEALTHCHECK` chuyển sang `unhealthy` khi tiến trình treo | mục Q.2 mới đo được ở mức HTTP, chưa đo ở mức container |
| 3 | Chứng minh `read_only: true` + `tmpfs /tmp` không làm hỏng đường upload | chưa chạy lượt nào |
| 4 | Chạy bộ thử trong container với `cryptography` **43.0.1** đã ghim | nợ **d-8** ở mục 7 phía trên |
| 5 | Chứng minh `X-Request-Id` và log JSON đi ra được `docker logs` | mới thêm ở G15 (P-G15-01); chưa đo trong container |
