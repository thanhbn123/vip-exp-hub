# G21 — AG-03: CHE BÍ MẬT (CREDENTIAL REDACTION) TRÊN MỌI ĐƯỜNG

**Vai:** AG-03 · **Nhiệm vụ:** `task_5df428fc0149` · **Dispatch:** `ctx_b31c78a1a2bd`
**Nền đo:** `integration/g20 @ a3400a8` (worktree `g21-ag03-bimat`). `main = de740dc` (KHÔNG chứa
G13–G21) — không dùng.
**Vùng được ghi:** `app/thu/thu_g21_bimat.py` (mới) · `docs/G21_BIMAT.md` (mới) · `app/http_jt.py`
(chỉ phần che bí mật) · và **hai chỗ AG-00 mở rộng giữa lượt** (xem §3.0): `app/server.py`,
`app/loi_hang.py`. `app/thu/thu_bao_mat.py` nằm trong vùng nhưng **không cần sửa** (§6 mục 9).

---

## 0. MỘT CÂU PHẢI NÓI TRƯỚC MỌI CON SỐ

Che bí mật của G16 **không hỏng ở chỗ nó được viết** — nó hỏng ở **năm đường chưa ai đo**, thuộc
hai loại: **hai đường cho HAI ĐÁP ÁN KHÁC NHAU** (JSON lồng trong header yêu cầu · JSON lồng trong
header phản hồi) và **ba đường RA KHỎI TIẾN TRÌNH** (`msg` của hãng → **thân HTTP 502** mà người
dùng nhìn thấy · QUERY và ĐƯỜNG DẪN → **tệp log trên đĩa**).

Lượt này đo lại **toàn bộ** đường che bằng một bộ kiểm mới (33 ca, **0 bỏ qua**), tìm ra **năm đường
rò thật**, **vá cả năm**, và chứng minh từng ca kiểm **ĐỎ ĐƯỢC** bằng cách tiêm lại đúng hành vi
trước bản vá (nhóm `G` cho ba đường ra-khỏi-tiến-trình, nhóm `F` cho hai đường trong tiến trình).

| Bằng chứng | Lệnh thật | Kết quả thật |
|---|---|---|
| Bộ kiểm mới | `python3 app/thu/thu_g21_bimat.py` | **`Ran 33 tests · OK · EXIT=0` · 0 bỏ qua** |
| Ca ĐỎ ĐƯỢC (D3) | `G1` — tiến trình con tiêm `loi_hang._mo_ta_msg_hang` bản cũ | `D1` **ĐỎ** · `D2` **ĐỎ**; không tiêm ⇒ **XANH** |
| Ca ĐỎ ĐƯỢC (D4/D5) | `G2` — dựng lại máy chủ với `log_message` bản cũ | bộ dò **THẤY RÒ** ở `E2` và `E3` |
| Hồi quy các bộ liên quan | 5 bộ · 190 ca | **EXIT=0** cả năm (§1.2) |
| Hồi quy chung | `sh app/thu/chay_tat_ca.sh` | **1903 ca · 52 bộ** · frontend 56+36 · E2E **41/41** · **EXIT=1** · 5 bộ đỏ: 4 do cây chưa commit / nợ cũ, 1 do bản vá `http_jt` (§7.2) |

---

## 1. LUẬT BẰNG CHỨNG VÀ CÁCH CHẠY

### 1.1 Bộ kiểm mới — chạy thế nào, đọc số ở đâu

```sh
python3 app/thu/thu_g21_bimat.py
# → Ran 33 tests in 14.2s · OK · EXIT=0 · skipped=0
```

`sha256 app/thu/thu_g21_bimat.py = bf8311ee960c314bf2f3d9e814e03c45cc5c07bc33bbf3ca3a4d73832a4301e3`

Tệp này được `app/thu/chay_tat_ca.sh` **tự nhận** (bộ chạy quét `app/thu/thu_*.py`), nên từ lượt này
nó là một phần của hồi quy chung ⇒ nó **phải xanh**. Vì vậy **không có ô "NEEDS_REVIEW" nào**: ba
đường rò đo được đã được vá ngay trong lượt này, và mọi khẳng định đều CỨNG.

Bộ kiểm in ra, ở cuối mỗi lượt chạy: **sổ đối chứng dương** (`DOI_CHUNG`), **bảng "đường nào che cái
gì"** (`BANG`, 35 dòng) và tổng số phép đo đã ghi bảng.

### 1.2 Hồi quy các bộ bị ảnh hưởng bởi bản vá

| Bộ | Lệnh | Kết quả |
|---|---|---|
| `thu_http_jt.py` (lớp HTTP) | `python3 app/thu/thu_http_jt.py` | **57 ca · OK · EXIT=0** |
| `thu_g18_bi_mat.py` (bí mật G18) | `python3 app/thu/thu_g18_bi_mat.py` | **15 ca · OK · EXIT=0** |
| `thu_nhat_ky_yeu_cau.py` (log yêu cầu G15) | `python3 app/thu/thu_nhat_ky_yeu_cau.py` | **8 ca · OK · EXIT=0** |
| `thu_g03.py` (`loi_hang`) | `python3 app/thu/thu_g03.py` | **53 ca · OK · EXIT=0** |
| `thu_bao_mat.py` (khoá/bí mật) | `python3 app/thu/thu_bao_mat.py` | **57 ca · OK · EXIT=0** *(xem ghi chú)* |

> **GHI CHÚ `thu_bao_mat.py` — một HỎNG GIẢ của môi trường, không phải của bản vá.** Chạy trong
> shell kế thừa `GIT_CONFIG_COUNT=2` mà **thiếu** `GIT_CONFIG_KEY_*` thì `git check-ignore` thoát
> **128** và ca `f3` đỏ (`git KHÔNG chặn app/du-lieu/khoa-noi-bo.key`). Đó đúng **N-G18-00/C3** đã
> ghi ở `docs/QA_G20.md` §1.1. Cùng lệnh, đã gỡ gia đình biến:
> `env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 python3 app/thu/thu_bao_mat.py`
> → **57 ca · OK · EXIT=0**. `chay_tat_ca.sh` tự gỡ gia đình biến này nên nó không thấy hỏng giả ấy.

---

## 2. BẢNG "ĐƯỜNG NÀO CHE CÁI GÌ"

In ra bằng máy ở cuối mỗi lượt chạy (`Z_TongKet.test_z2`). Cột **Dạng** là dạng bí mật đã thử.

| # | Đường | Vị trí | Dạng đã thử | Kết quả |
|---|---|---|---|---|
| A1 | Yêu cầu | header `privateKey` | dài (23) · ngắn (3) | che |
| A2 | Yêu cầu | thân form `password` | dài · ngắn | che |
| A2 | Yêu cầu | JSON lồng trong `bizContent` | ngắn · **sâu hai tầng** | che |
| A3 | Yêu cầu | query `token` | dài · ngắn · **JSON lồng** | che |
| A4 | Yêu cầu | **header KHÔNG tên credential, giá trị là JSON lồng** | ngắn (3) | **che — LỖ HỔNG ĐÃ VÁ (D1)** |
| A5 | Phản hồi | **header trả lời chứa JSON lồng** | ngắn · dài | **che — LỖ HỔNG ĐÃ VÁ (D2)** |
| A6 | Phản hồi | header lượt **2xx** (`TraLoiHTTP`) | dài · ngắn | che |
| A7 | Yêu cầu | bí mật **RỖNG** | rỗng | không vào tập che (không che bừa) |
| A8 | Yêu cầu | bí mật **trùng tên trường khác** | 12 | che |
| A9 | Yêu cầu | query bị **mã hoá URL một lớp / hai lớp** | `a b&c=d` | che cả hai |
| A10 | Yêu cầu | **đường dẫn** chứa bí mật dài | dài (23) | che từng đoạn |
| A10b | Yêu cầu | **đường dẫn** chỉ chứa bí mật NGẮN | ngắn (3) | **CHƯA ĐO ĐƯỢC — biên giới đã biết (§5.1)** |
| B1 | **Nhất quán** | 5 đường, cùng một bí mật ngắn, cùng tên credential | ngắn (3) | **1 kết quả duy nhất** (`chi tiet: [DA-CHE]`) |
| B2 | Ngưỡng độ dài | tên KHÔNG credential | ngắn | ngưỡng còn tác dụng (không che `VH12`) |
| B3 | Ngưỡng độ dài | tên KHÔNG credential | ngắn (3) | **CHƯA CHE ĐƯỢC — đánh đổi có ý thức (§5.2)** |
| C1 | **Đối chứng đường** | `don-42` + tên endpoint | ngắn (6) | **nguyên vẹn**, bí mật dài vẫn bị che |
| C2 | **Đối chứng đường** | thân **2xx** (hợp đồng §36) | — | **nguyên vẹn từng byte** |
| C3 | Yêu cầu | bí mật ở **vị trí TÊN** | dài (24) | chặn trước khi gửi; TÊN hợp lệ vẫn in |
| D1 | **Thông báo lỗi adapter** | `KetQuaHang.loi` · `.tho` · chuỗi thân 502 | ngắn · dài | **che — LỖ HỔNG ĐÃ VÁ (D3)** |
| D2 | **Thân HTTP 502** (socket thật) | thân phản hồi trên dây | ngắn · dài | **che — cùng lỗ hổng D3** |
| E1 | **Tệp trên đĩa** | thân request → log + CSDL tạm | dài | sạch |
| E2 | **Tệp trên đĩa** | query URL → log + CSDL tạm | dài | **sạch — LỖ HỔNG ĐÃ VÁ (D4)** |
| E3 | **Tệp trên đĩa** | đường dẫn URL → log + CSDL tạm | dài (39) | **sạch — LỖ HỔNG ĐÃ VÁ (D5)** |
| F4 | Chốt chặn mạng | `socket.connect` | host ngoài | **BỊ CHẶN**, và `Z3` = **0** lượt ra ngoài |
| G2 | **Chứng minh ca ĐỎ được** | tệp trên đĩa, bản CHƯA VÁ | dài · dài | **BỘ DÒ THẤY RÒ** (cả E2 và E3) |

---

## 3. NĂM ĐƯỜNG RÒ THẬT — ĐO ĐƯỢC, ĐÃ VÁ, CÓ CA KIỂM

| Mã | Đường rò | Tệp được vá | Ca kiểm | Ca chứng minh ĐỎ ĐƯỢC |
|---|---|---|---|---|
| **D1** | JSON lồng trong **giá trị header YÊU CẦU** (và trong **query**) không vào tập che | `app/http_jt.py` | `A4` · `A3` | `F2` (`_gia_tri_trong_json`) |
| **D2** | JSON lồng / cặp `tên=giá_trị` trong **header PHẢN HỒI** không được nhận diện | `app/http_jt.py` | `A5` · `A6` | `F2` (`_gia_tri_bi_mat_trong_json` + `_vb`) |
| **D3** | `msg` của hãng chép nguyên vào `thong_diep` → `kq.loi/tho` → **thân HTTP 502** | `app/loi_hang.py` | `D1` · `D2` | `G1` (tiêm lại `_mo_ta_msg_hang` cũ) |
| **D4** | QUERY của URL ghi nguyên xuống **tệp log** (dòng access log thô) | `app/server.py` | `E2` | `G2` (dựng lại `log_message` cũ) |
| **D5** | bí mật trong ĐƯỜNG DẪN xuống **tệp log** (access log + trường `duong` của JSONL) | `app/server.py` | `E3` | `G2` |

### 3.0 Vì sao có `server.py` và `loi_hang.py` trong vùng ghi

Ba lỗ hổng dưới đây nằm **ngoài** vùng ghi ban đầu của AG-03. AG-03 đã đo, rồi hỏi AG-00 bằng
`orca orchestration ask` (một câu, ba lựa chọn kèm bằng chứng). **AG-00 chọn (b): mở rộng vùng ghi
đúng hai tệp** (`app/server.py`, `app/loi_hang.py`), kèm yêu cầu (c): **ca kiểm phải ĐỎ ĐƯỢC**,
chứng minh bằng cách tiêm lại lỗi — nhóm `G` là phần chứng minh đó.

### 3.1 D1 — JSON lồng trong **header** cho hai đáp án khác nhau (vá trong `app/http_jt.py`)

**Bất biến ĐÚNG:** *mọi giá trị ta gửi đi, ở BẤT KỲ vị trí nào, đều phải được soi JSON lồng bên
trong.* Bản G16 chỉ soi JSON lồng cho **thân form** (`_gia_tri_trong_json`), không soi cho **giá
trị header**.

ĐO ĐƯỢC trước bản vá (stub `127.0.0.1`, hãng echo lại **đúng giá trị bên trong**):

```
header  X-Du-Lieu: {"password": "aB3"}      → RÒ 'aB3' qua str(e), repr(e), e.args, than_da_che, traceback
thân form bizContent={"password":"aB3"}     → sạch
```

Tức **cùng một bí mật, hai đường, hai đáp án** — đúng khuôn lỗi mà G16-05 tưởng đã đóng. Cùng lỗ
hổng ấy có ở **query** (`?d={"password":"aB3"}`) vì query cũng chưa từng được soi JSON lồng.

**Vá:** `_gia_tri_ta_gui` soi JSON lồng cho **giá trị header**; `_gia_tri_tu_url` soi cho **giá trị
query**. Ca kiểm: `A4`, `A3` (dòng "query JSON lồng").

### 3.2 D2 — bí mật **của hãng** trong JSON lồng của một header phản hồi (vá trong `app/http_jt.py`)

**Bất biến ĐÚNG:** *giá trị của một header phản hồi là DỮ LIỆU NGOÀI, và phải được soi đúng hai
dạng mà thân phản hồi đã được soi từ G18 (JSON lồng · cặp `tên=giá_trị`).* Bản G18 soi header phản
hồi **chỉ theo TÊN**, nên một header KHÁC TÊN mang JSON có khoá credential đi thẳng vào
`headers_da_che` và thông điệp ngoại lệ.

ĐO ĐƯỢC trước bản vá:

```
http_jt._gia_tri_bi_mat_tu_phan_hoi(b"{}", [("X-Debug", '{"privateKey": "hk3"}')])  → tập che RỖNG
http_jt._gia_tri_bi_mat_tu_phan_hoi(b"loi: privateKey=hk3", [])                     → {'hk3'}   (thân: CÓ)
```

**Vá:** `_gia_tri_bi_mat_tu_phan_hoi` soi thêm **giá trị** của mọi header phản hồi bằng đúng hai bộ
dò đang dùng cho thân (`_gia_tri_bi_mat_trong_json`, `_gia_tri_bi_mat_trong_vb`). Ca kiểm: `A5`,
`A6` (lượt 2xx, nơi `TraLoiHTTP` hay bị đem đi log).

### 3.3 D3 — `msg` của hãng đi thẳng vào **thân HTTP 502** (vá trong `app/loi_hang.py`)

**Đường đi:** thân lượt **HTTP 200** là bằng chứng NGUYÊN VĂN (hợp đồng §36 — cố ý, vì mã vận đơn
nằm trong đó) → adapter đọc `msg` từ chính thân ấy → `loi_hang.tu_ma_hang` chép nguyên
`| msg hãng: <msg>` vào `thong_diep` → `KetQuaHang.loi/tho` → `don_hang.gui_don` ném
`LoiNghiepVu(f"hãng từ chối: {kq.loi}", 502)` → `server._chay_that` trả `{"loi": str(e)}`.
**Bí mật đi ra ngoài đúng đường người dùng nhìn thấy.**

ĐO ĐƯỢC trước bản vá (stub trả `{"code":"145005005","msg":"khoa cua ban: <bí mật>"}` ở lượt 200):

```
kq.loi   → 'HANG_TU_CHOI · … · 获取运单号失败 … | msg hãng: khoa cua ban: BI-MAT-DAI-9f3ac21b7d4e · KHÔNG thử lại'
kq.tho   → { "loi_chuan": { … "thong_diep": "… | msg hãng: khoa cua ban: BI-MAT-DAI-9f3ac21b7d4e" } }
```

**Vá:** `loi_hang._mo_ta_msg_hang(msg)` — `thong_diep` **không chép văn bản của hãng**, chỉ nêu
**độ dài** của nó. Phần hành động được vẫn nguyên: **mô tả tiếng Việt của mã lỗi** + **mã gốc của
hãng** (`ma_goc_hang`), nên người trực tra bảng mã của hãng bằng mã. **Không dùng vân tay băm thay
thế**: băm một bí mật NGẮN là chuyện giải ngược được bằng vét cạn — vẫn là một đường rò, chỉ khó
thấy hơn. Ca kiểm: `D1` (`kq.loi` / `kq.tho` / chuỗi thân 502) và `D2` (**thân 502 đo trên socket
thật**, qua `server._chay_that`).

### 3.4 D4 + D5 — bí mật trong QUERY và trong ĐƯỜNG DẪN rơi xuống **tệp log trên đĩa** (vá trong `app/server.py`)

**Đây là chỗ dễ rò nhất mà G16–G20 chưa đo**, và `docs/QA_G20.md` §5 đã khai thẳng là "chưa đo".
Bản cũ của `log_message` ghi `fmt % args` kèm chú thích:

> "Log KHÔNG BAO GIỜ chứa body/secret — chỉ dòng request chuẩn."

**Chú thích đó SAI.** `fmt % args` chính là dòng yêu cầu ĐẦY ĐỦ. ĐO ĐƯỢC (máy chủ THẬT + đọc lại
tệp log trên đĩa):

```
[hub] "GET /api/don?token=token-GIA-QUERY-8a3f21d0 HTTP/1.1" 401 -          ← QUERY lọt
[hub] "GET /api/DUONG-DAN-CHUA-BI-MAT-c41f9a2b7e/x HTTP/1.1" 401 -          ← ĐƯỜNG DẪN lọt
{"loai":"yeu_cau", … "duong": "/api/DUONG-DAN-CHUA-BI-MAT-c41f9a2b7e/x" …}  ← trường `duong` lọt
```

Điều trớ trêu: **chính `server.py` đã khai** query "có thể mang token" và **đã cắt query** khỏi
dòng JSONL (`_chay`) — nhưng đường access log thô thì không, và cả hai cùng ghi xuống **một tệp**.

**Vá (hai chỗ, MỘT luật):**
* `BoXuLy.log_message` — cắt `?…` thành `?<da-cat-query>`, rồi che các đoạn đường dẫn nguy hiểm;
* trường `duong` của dòng JSONL — đi qua cùng bộ che.

Bộ che dùng **đúng một nguồn** với lớp HTTP: `http_jt.doan_duong_dan_da_che` (hàm công khai mới,
cùng luật với `_duong_dan_da_che` đã có từ G18). Hai bản cài cho một luật là hai bản sẽ trôi khỏi
nhau. Ca kiểm: `E2`, `E3` — kèm **đối chứng đường**: dòng log VẪN ở đó (`/api/v2/don`,
`/api/[DA-CHE]/x`), tức không phải bị bỏ hẳn.

### 3.5 CHỨNG MINH CA KIỂM **ĐỎ ĐƯỢC** (yêu cầu (c) của AG-00)

| Ca | Cách tiêm lại lỗi cũ | Kết quả |
|---|---|---|
| `G1` | tiến trình con: `loi_hang._mo_ta_msg_hang = lambda msg: ' | msg hãng: %s' % msg` | `D1` **ĐỎ** · `D2` **ĐỎ** |
| `G1` (đối chứng dương) | không tiêm | `D1` **XANH** |
| `G2` | dựng lại máy chủ với `log_message` CŨ + `_doan_duong_dan_trong_log = lambda d: d` | bộ dò **THẤY RÒ** ở `E2` và `E3` |

---

## 4. ĐỐI CHỨNG ĐƯỜNG VÀ TỰ KIỂM BỘ ĐO

* **Sổ `DOI_CHUNG`** in ra ở `Z_TongKet.test_z2` (nhóm → số lượt). `test_z1` **tự phán HỎNG** nếu
  một nhóm có ca phủ định mà không có lượt đối chứng dương nào, hoặc nếu có lượt ghi vào khoá RỖNG
  (một lớp quên khai `NHOM` — lỗi có thật đã xảy ra ở lượt chạy đầu của tệp này).
* **Đối chứng đường** (`C1`, `C2`, `A7`, `E2`, `E3`, `D1`, `D2`): `don-42` và tên endpoint
  `addOrder` đi qua **nguyên vẹn**; thân **2xx** nguyên vẹn **từng byte** (hợp đồng §36 — che nó là
  phá dữ liệu nghiệp vụ); bí mật **RỖNG** không vào tập che (nếu vào, `che_bi_mat` chèn nhãn vào
  giữa mọi ký tự và phá sạch thông điệp chẩn đoán).
* **Tự kiểm bộ đo** (`F`): tiến trình con đột biến `che_bi_mat` thành hàm đồng nhất ⇒ các ca rò rỉ
  **ĐỎ**; gỡ đúng bản vá G21 (`_gia_tri_trong_json` / `_gia_tri_bi_mat_trong_json` +
  `_gia_tri_bi_mat_trong_vb`) ⇒ ca `A4`/`A5` **ĐỎ**; **không** đột biến ⇒ **XANH**.
* **Chốt chặn mạng** (`F4`, `Z3`): mọi lượt nối ra ngoài loopback **BỊ CHẶN** và **đếm được**;
  `Z3` khẳng định **0** lượt ra ngoài. Mọi phép đo lớp HTTP chỉ chạm stub `127.0.0.1` cổng OS cấp.
* **`Z5`** — bộ kiểm **không được đụng CSDL THẬT của dự án** (`app/du-lieu/hub.db`). Ca này ra đời
  vì lỗi đó **đã xảy ra thật** trong chính tệp này (§4.2).

### 4.1 Một HỎNG GIẢ đã bắt được ngay trong bộ kiểm này (ghi lại để người sau không lặp)

Lượt chạy đầu, ca `A3` **XANH** trong khi bí mật `aB3` KHÔNG hề bị che. Nguyên nhân: stub đọc thân
yêu cầu **lần thứ hai** (sau khi `_BoXuLy` đã đọc), nên lượt đọc thứ hai **chặn tới hết hạn**; ngoại
lệ trở thành **HẾT GIỜ** — mà ngoại lệ hết giờ **không mang thân phản hồi nào**, nên mọi phép dò rò
rỉ đều "sạch" một cách vô nghĩa. Bản vá: stub đọc từ **bản ghi `yeu_cau`**, và mọi ca ÂM nay đi qua
`khang_dinh_401` — **khẳng định lượt gọi THẬT SỰ hỏng vì hãng TỪ CHỐI (HTTP 401)**, không phải vì
treo. Một ca âm không khẳng định được loại ngoại lệ là một ca có thể xanh vì lý do sai.

### 4.2 Một VI PHẠM đã tự bắt được: bộ kiểm ghi vào CSDL THẬT của dự án

`cau_hinh.THU_MUC_DU_LIEU` được tính **MỘT LẦN** lúc `cau_hinh` được nạp (theo `adapter_jt`), nên
đặt `VIP_HUB_DATA` **sau** khi import là quá muộn: `csdl.mo()` mở `app/du-lieu/hub.db` — CSDL THẬT.
ĐO ĐƯỢC: sau vài lượt chạy, `app/du-lieu/` mọc thêm `hub.db` + `-wal` + `-shm` (hai cây worktree
khác chỉ có `khoa-noi-bo.key`). Đã xoá phần rác ấy (không có gì được theo dõi bởi git trong đó),
**vá gốc** (đặt biến ở CẤP MÔ-ĐUN, trước mọi import của `app/`), và **ghim bằng ca `Z5`**. Bài học
chung: một bộ thử có thể vi phạm đúng thứ nó đang canh — nên chính bộ thử cũng phải có ca canh.

---

## 5. CHƯA ĐO — LỖ HỔNG PHẠM VI, **KHÔNG PHẢI ĐẠT**

### 5.1 Biên giới: bí mật NGẮN chỉ xuất hiện trong ĐƯỜNG DẪN (`A10b`)

Một đoạn đường dẫn 1–7 ký tự (`/api/aB3/…`) mà bí mật ấy **không** xuất hiện ở bất kỳ vị trí nào
khác thì **không có gì để nhận diện**: đoạn đường dẫn không có TÊN, và độ dài dưới ngưỡng nên
không phân biệt được với một endpoint thật (`order`, `api`, `v1`). Che mọi đoạn ngắn là che luôn
tên endpoint — thứ duy nhất cho biết lượt gọi đi tới đâu. Khuôn này đã được G18 đo và ghi
(`thu_g18_bi_mat.k2d`); lượt này **ghim lại biên giới** thay vì giả vờ nó không tồn tại.
**CÙNG bí mật ấy**, nếu so BẰNG NHAU với một giá trị ta đã gửi ở trường credential (kể cả khi nó
nằm trong đường dẫn), **vẫn bị che** — biên giới hẹp đúng chỗ đã khai, và **không** mở rộng sang
bí mật dài (`A10` xanh).

### 5.2 Biên giới: bí mật NGẮN dưới một TÊN không thuộc danh sách credential (`B3`)

`?tk=aB3`, `X-Ma-Don: aB3` — giá trị 1–7 ký tự dưới một tên KHÔNG phải credential **không** được
tự động che. Đây là **đánh đổi có ý thức từ G16/G17**, được `thu_http_jt.test_j2` và `test_j5` ghim
đúng ngưỡng; nới nó là che cả `trang=2`, `ma=1`, `id=7` và làm thông điệp chẩn đoán mất hết thông
tin. Bất biến ĐÚNG vẫn được khẳng định: nếu CÙNG bí mật ấy xuất hiện ở **một** vị trí có tên
credential thì nó bị che ở **mọi** chỗ trong thân phản hồi (che theo GIÁ TRỊ, đã gom một lần).

### 5.3 Những mục khác chưa đo trong lượt này

| # | Mục | Vì sao chưa đo | Ai/cái gì đóng được |
|---|---|---|---|
| 1 | **Gọi API hãng thật, kể cả sandbox** | `V-G09-01`/`V-13906-05` CHƯA CẤP ⇒ **BỊ CẤM**. Mọi phép đo HTTP chỉ chạm `127.0.0.1` cổng OS cấp | anh Thành cấp quyền |
| 2 | **Trace/báo cáo Playwright** (`thu_giao_dien/_bao-cao/**`, `_ket-qua/**`) | Tầng 3 chỉ ghi `trace.zip` khi ca HỎNG, và phải chạy Chromium thật; lượt này không dựng được một ca tầng 3 hỏng CÓ CHỦ Ý trong phạm vi làn AG-03. **Chuỗi CANARY của `05_ket_noi_jt.spec.js` đi qua route rotate thật** ⇒ đây là chỗ PHẢI đo ở làn tầng 3 | AG-06/AG-01 (làn tầng 3) |
| 3 | **Thư mục tĩnh phục vụ tệp lạ / `autoindex`** | Ngoài phạm vi che bí mật (đã có `J_StaticKhongPhucVuBiMat` trong `thu_bao_mat.py`) | giữ nguyên |
| 4 | **Nén/ký/mã hoá payload trước khi ra dây** | Hệ này không nén thân ở tầng HTTP; nếu tương lai thêm, tập biến thể (`_bien_the`) phải mở rộng | làn thêm tính năng |
| 5 | **`msg` của VTP (adapter thứ hai)** | Bản vá nằm ở `loi_hang.tu_ma_hang` — dùng chung cho MỌI hãng — nhưng lượt này chỉ dựng stub J&T để đo | lượt sau, cùng bộ kiểm |
| 6 | **Bốn ca PIN CẤU TRÚC trong `thu_g20_dahang.py`** | Chúng ghim **số dòng / số hàm / hash blob** của `http_jt.py`, nên MỌI bản vá thật vào tệp đó đều làm chúng ĐỎ. AG-03 đã hỏi AG-00 (xem §7) — **chưa có quyết định tại thời điểm ghi tài liệu này** | AG-00 / chủ tệp `thu_g20_dahang.py` |
| 7 | **Hai cổng "cây sạch"** (`thu_qa_g17.py`, `thu_qa_g18.py`) | Đỏ khi cây có tệp chưa commit / tệp của làn khác — đúng **N-G19-03/C1** mà `docs/QA_G20.md` §2.1 mô tả; làn sửa là `g21-ag05-chotcay` | AG-05 (chốt cây) |

---

## 6. TUÂN THỦ TUYỆT ĐỐI — TỰ KIỂM BẰNG MÁY

| # | Điều bị cấm | Cách tự kiểm | Kết quả |
|---|---|---|---|
| 1 | Gọi API hãng kể cả sandbox | `ChanMang` chặn + đếm MỌI lượt nối ra ngoài loopback (`F4`, `Z3` = **0**) | ✓ |
| 2 | Push / deploy / tunnel / mở cổng | Không lệnh `git push`/`ssh`/tunnel nào. Máy chủ của bộ kiểm bind `127.0.0.1` **cổng OS cấp** (`("127.0.0.1", 0)`) | ✓ |
| 3 | Mở `CHO_PHEP_LIVE`; credentials thật; `.env` | Không đọc `.env`; adapter chạy ở `mock`; **mọi** bí mật trong tệp này là chuỗi GIẢ tự đặt | ✓ |
| 4 | Đoán mã trạng thái hãng (D-4) | Không chạm bảng ánh xạ trạng thái; mã chưa xác minh vẫn `NEEDS_REVIEW` | ✓ |
| 5 | Giữ chốt `D-9` (`city`/`area` chặn cứng ngoài mock) | Không chạm ánh xạ `area`; adapter vẫn chặn ở cửa D-9 | ✓ |
| 6 | Chuyển CSDL sang PostgreSQL (D-8); cụm `:5432` | Không một dòng nào chạm PostgreSQL; CSDL của bộ kiểm là **thư mục tạm** (ca `Z5` canh cả CSDL thật của dự án) | ✓ |
| 7 | Dùng mô hình khác; tự bấm duyệt sandbox | Không một lời gọi mô hình nào; không thao tác duyệt nào | ✓ |
| 8 | Xoá hàng loạt; sửa ngoài phạm vi | `git status` chỉ có 3 tệp sửa + 2 tệp mới, đúng vùng được cấp | ✓ |
| 9 | **`app/thu/thu_bao_mat.py` (vùng được ghi)** | **KHÔNG cần sửa**: không ca nào trong đó ghim hành vi che bí mật của lớp HTTP (nó đo khoá/SecretProvider). Kiểm bằng cách chạy lại: **57 ca · OK · EXIT=0** | ✓ |

---

## 7. GHIM SHA, SỐ ĐO LƯỢT CHẠY CUỐI, VÀ VIỆC CÒN MỞ

### 7.1 SHA các tệp (đo sau khi mọi sửa đổi kết thúc)

| Tệp | sha256 |
|---|---|
| `app/thu/thu_g21_bimat.py` | `bf8311ee960c314bf2f3d9e814e03c45cc5c07bc33bbf3ca3a4d73832a4301e3` |
| `app/http_jt.py` | `0e9ec24d493e3f805ac2af6dc5eba78f9c74b5ec4057807c5d6a5bfa7fda7500` |
| `app/loi_hang.py` | `2e1c74fde5dbbe7fcef98e58018081acb509418d060d54bd01003cb9048c608d` |
| `app/server.py` | `23515e6d1dcb1cedd0e79baf543f40bdfe1b24575783e79fefeec7933f9c517f` |

> Một tệp **không tự ghi được SHA của chính nó** (`BAN_GIAO.md` §7.3 — dòng SHA sẽ đổi chính tệp
> đang chứa nó). Nên bảng trên ghim bốn tệp **khác**; số đo lượt chạy cuối và SHA của tài liệu này
> nằm trong **báo cáo `worker_done`** gửi AG-00.

### 7.2 Hồi quy chung — lượt chạy trên bộ kiểm ĐÃ ĐÓNG BĂNG (SHA ở §7.1)

```sh
sh app/thu/chay_tat_ca.sh
# → python: 1903 ca · 52 bộ chạy thật · +1 bộ BỎ QUA (thu_qa_g19.py)
#   frontend: 56 + 36 ca · E2E: 41/41 phép đo đạt
#   bộ hỏng: thu_g20_baomat.py · thu_g20_dahang.py · thu_postgres.py · thu_qa_g17.py · thu_qa_g18.py
#   === EXIT CODE THAT = 1
```

| Bộ đỏ | Ca đỏ | Nguyên nhân ĐO ĐƯỢC | Có phải do làn AG-03? |
|---|---|---|---|
| `thu_g20_baomat.py` | 6 ca "cây sạch" + đột biến | Cây **CHƯA COMMIT** (sandbox chặn ghi `.git` — §7.4). Chính các ca này khẳng định cây phải sạch | **Không** — sẽ xanh sau khi commit |
| `thu_qa_g17.py` · `thu_qa_g18.py` | `test_a1_cay_sach*`, `a1d`; riêng g18 thêm `b1_tang_3` | Cùng lý do cây chưa commit; `b1_tang_3` là nợ C2 của G20 (bàn phím trong màn) | **Không** — N-G19-03/C1 + V-13911 |
| `thu_g20_dahang.py` | 4 ca pin cấu trúc | Ghim **hash blob / số hàm / số dòng** của `http_jt.py` ⇒ ĐỎ với mọi bản vá thật vào tệp đó (§5.3 mục 6) | **Có** — chờ AG-00 quyết (§7.3) |
| `thu_postgres.py` | `test_h2_doi_chung_am_bo_khoa_thi_dung_nhau` (1 ca) | **Chập chờn của lượt chạy**: chạy riêng ⇒ **55 ca · OK · EXIT=0**; chạy NGAY SAU bộ kiểm G21 ⇒ **55 ca · OK · EXIT=0**. Lượt đỏ duy nhất ghi lại được | **Không** — làn PostgreSQL, bộ kiểm G21 không chạm `:5432` |

`thu_g21_bimat.py` trong chính lượt chung ấy: **✓ 33 ca**.

### 7.3 Chặn ghi `.git` — đã báo AG-00, KHÔNG tự vượt

Mọi lệnh ghi `.git` từ worktree này đều bị sandbox chặn:
`fatal: Unable to create '…/worktrees/g21-ag03-bimat/index.lock: Operation not permitted'`
(`[sandbox: file access denied under workspace-write mode]`). Theo đề bài, AG-03 **không tự vượt**
(không tự bấm duyệt sandbox) mà đã gửi `escalation` cho AG-00 kèm **đúng lệnh commit** và 5 tệp
cần commit. Hệ quả ĐO ĐƯỢC: hai cổng "cây sạch" (`thu_qa_g17.py`, `thu_qa_g18.py`) và nhóm
`B_ChotCaySach` của `thu_g20_baomat.py` đỏ **vì cây chưa commit**, không vì nội dung (§7.2).

### 7.4 Việc còn mở — cần AG-00 quyết

1. **Bốn ca pin cấu trúc trong `app/thu/thu_g20_dahang.py`** (`b6` ghim hash blob `http_jt.py`,
   `a2` ghim đếm hàm, `a6`/`a7` ghim **số dòng**) — chúng ĐỎ với **mọi** bản vá thật vào
   `http_jt.py`, tức chúng pin HÀNH VI CŨ chứ không pin bất biến. AG-03 đã hỏi AG-00 và **chờ
   quyết định** (sửa bởi AG-00/AG-06, hay mở rộng vùng ghi).
2. **Hai cổng "cây sạch"** (`thu_qa_g17.py`, `thu_qa_g18.py`) — thuộc làn `g21-ag05-chotcay`;
   chúng chỉ xanh sau khi cây được commit VÀ làn đó gộp bản vá miễn trừ theo quy tắc.
3. **Commit 5 tệp** (§7.3) — việc của AG-00.
