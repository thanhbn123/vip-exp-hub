# G19 — PHỦ 31 ROUTE CÒN THIẾU BẰNG PHÉP ĐO CÁCH LY TENANT

**Làn:** AG-04 · **WAVE G19** · **Nền:** `integration/g18` @ `6e61fc1e1f1f9a6d64931464e4f40ed887192ab5`
**Bộ ca:** `app/thu/thu_g19_route.py` (49 ca) · **Dụng cụ:** `trien_khai/g19/` · **Bộ chạy:** `sh trien_khai/g19/chay_g19.sh`

---

## 0. KẾT LUẬN TRƯỚC, CHỨNG CỨ SAU

| Câu hỏi | Trả lời đo được |
|---|---|
| Khoảng trống G18 còn lại bao nhiêu? | **31 mục** — nhưng chỉ **30 là route thật**; mục thứ 31 (`/api/v2/platform/`) là **hằng số tiền tố của cổng chặn**, không phải route (§3.1) |
| Lượt này đo được bao nhiêu? | **30/30 route thật** của khoảng trống + **1/1 mục artefact** được chứng minh không phải route = **31/31 mục** |
| Còn mục nào **CHƯA ĐO**? | **0** |
| Số route **rò rỉ** dữ liệu chéo tenant? | **0** |
| **Con số cuối** | **103/103 route THẬT** đã có bằng chứng cách ly tenant = **73** (bộ AG-01, từ G18) **+ 30** (bộ này, G19). AG-06 đếm **104 mục** = 103 route thật + 1 artefact |
| Bộ trích thứ ba có răng không? | Có — **4 đột biến** trên bản sao (§2), và bộ đo cách ly cũng có **1 đột biến tự kiểm** làm nó ĐỎ được (B5, §2) |

Năm tệp mới (cộng báo cáo này), **không sửa một tệp nào đã có**:

| Tệp | SHA-256 | Vai |
|---|---|---|
| `app/thu/thu_g19_route.py` | `a73fc6c1f73966ccb768d3990d33766df871e66297a38611d1b4f25e9929fd8a` | Bộ ca 49 test |
| `trien_khai/g19/bot_route_thi_hanh.py` | `1ffd1d0e37d4bd4c33412e4059bd76ea34850c8ac1b72ba447b95795afd4ae63` | Bộ trích thứ ba + 4 hàm đột biến |
| `trien_khai/g19/may_chu_do.py` | `7413d9f904b395b1f1f9cf144afc367e295b86e2bb503c9c9402f8eb46c58a57` | Máy chủ đo (bind `127.0.0.1` cổng 0) |
| `trien_khai/g19/chay_g19.sh` | `0861d6880c29b224338ab5f9c2ff67ee2244a234cd615a1637c727b8fbf6b0ce` | Bộ chạy |
| `trien_khai/g19/README.md` | `edb5c5865cfb20aeaac6140560623713643a99b8fc96938d084e4f8b7dfeac38` | Mô tả dụng cụ |
| `docs/G19_ROUTE_COVERAGE.md` | *(chính tệp này)* | Báo cáo |

---

## 1. BỘ TRÍCH ROUTE **THỨ BA** — NGUYÊN LÝ KHÁC HAI BỘ ĐÃ CÓ

### 1.1 Vì sao phải khác nguyên lý

Hai bộ đang có cùng dùng **một** giả định: *"route là thứ đọc được từ mã nguồn"*.

| Bộ | Ở đâu | Nguyên lý |
|---|---|---|
| **AG-06** | `app/thu/thu_g17_baomat.py::_cua_tu_nguon` | `ast.parse()` rồi đi theo **cây cú pháp**, có trạng thái `dang_cho` để nối `re.fullmatch(...)` với khối `if` bên dưới → **CÚ PHÁP** |
| **AG-01** | `app/thu/thu_qa_g18.py::duong_ghi_tinh/duong_ghi_dong/duong_platform` | `re` trên **từng dòng văn bản nguồn** → **VĂN BẢN** |
| **AG-04 (lượt này)** | `trien_khai/g19/bot_route_thi_hanh.py` | Không gian ứng viên moi từ **hằng số đã BIÊN DỊCH** (`co_consts`), rồi quyết định bằng **PHẢN HỒI THẬT** của máy chủ đang chạy → **THI HÀNH** |

```
BỘ THỨ BA = (ứng viên từ HẰNG SỐ ĐÃ BIÊN DỊCH)  ∩  (PHÂN LOẠI BẰNG THI HÀNH)
```

Điểm khác biệt **có thể đo được**, không phải khẩu hiệu: tầng tĩnh đọc bảng hằng số nên một
chuỗi trong **chú thích** không vào nổi không gian ứng viên; còn một hằng số chuỗi **thật** thì
vào, và bị **tầng thi hành** loại ra. Hai tầng, hai kiểu răng, cả hai đều bị đột biến đo (§2).

### 1.2 Phép phân loại bám vào CÂU CHỮ, không bám vào mã HTTP

Router trả `{"loi": "không có đường này"}` tại **đúng 2** nhánh rơi (`_api_platform`, `_api_tenant`).

* `404` + **đúng câu đó** ⇒ **KHÔNG có route**
* mọi mã khác (200/201/202/400/401/403/404-khác-câu/409/413/500…) ⇒ **CÓ route**
* `429` ⇒ **KHÔNG KẾT LUẬN**, đo lại

Vì sao không so mỗi mã HTTP: route `/api/v2/don/(\d+)` **CÓ** nhưng vẫn trả `404 {"loi": "không có
đơn này"}` khi id không tồn tại. Hai câu đó khác nhau, và bộ đếm phải phân biệt được. Ca **A3**
tự kiểm rằng `server.py` vẫn còn **đúng 2** nhánh rơi với đúng câu chữ đó — ai sửa câu chữ thì
ca này **ĐỎ**, không im lặng đếm sai.

### 1.3 Kết quả

```
$ python3 trien_khai/g19/bot_route_thi_hanh.py --ra /tmp/g19_liet_ke.json ; echo "EXIT=$?"
EXIT=0
[G19] hằng số /api/v2 đã biên dịch : 83
[G19] không gian ứng viên (tĩnh)   : 105 đường
[G19] CÓ ROUTE  (đo bằng thi hành)  : 103 đường
[G19] lượt đo                      : 420 lượt (105 đường × 4 phương thức)
[G19] lượt bị loại (404 nhánh rơi)  : 276 lượt
[G19] đường bị loại ở MỌI 4 phương thức (⇒ KHÔNG phải route): 2
       KHÔNG PHẢI ROUTE: /api/v2/platform/
       KHÔNG PHẢI ROUTE: /api/v2/webhook/nhan/
[G19] không kết luận (429)          : 0 lượt
[G19] cặp (đường, phương thức)      : 144
```

**83** hằng số đã biên dịch → **105** đường ứng viên (cố ý chứa rác: tiền tố, URL dựng cho khách)
→ tầng thi hành loại **276/420** lượt và giữ **103** đường thật. Ứng viên tĩnh là **SIÊU TẬP**
của tập cuối — đó là điều kiện để phép "dọn rác bằng thi hành" có nghĩa (ca **A2** khẳng định
`route < ứng_viên`, tức tầng thi hành **thật sự** làm việc).

Đối chiếu **A5**: **0 route lạ** — cả 103 route bộ ba đo được đều nằm trong tập của AG-06.

---

## 2. ĐỘT BIẾN — CHỨNG MINH BỘ TRÍCH **CÓ RĂNG**

Mọi đột biến chạy trên **BẢN SAO** của `app/` trong thư mục tạm (`bot_route_thi_hanh.ban_sao_app`).
`git status` sau lượt chạy chỉ thấy các tệp **mới** của làn này (§6.3) — tệp thật không bị đụng.

| Ca | Đột biến | Kỳ vọng | Kết quả đo được |
|---|---|---|---|
| **B1** | Tiêm route giả `GET /api/v2/g19-tiem-route` (tiêm **trước** nhánh rơi cuối, chỗ code TỚI ĐƯỢC) | bộ trích **PHẢI thấy**; lượt HTTP của nó phải **200 đúng thân đã tiêm** | `103 → 104` route; `GET → 200 {"g19_tiem": true}`, **khớp thân kỳ vọng** ✓ |
| **B2** | Tiêm `# /api/v2/g19-bia-chu-thich` (chú thích) | **KHÔNG** vào không gian ứng viên | `có trong ứng viên? False` ✓ — chứng minh tầng tĩnh **không `grep` văn bản** |
| **B3** | Tiêm `_bia_g19 = "/api/v2/g19-bia-chuoi"` (hằng số **THẬT**) | tầng tĩnh **NHẬN**, tầng thi hành **LOẠI** | `có trong ứng viên? True` → `có trong route? False`, cả 4 phương thức **404 nhánh rơi** ✓ — chứng minh **tầng thi hành có răng** |
| **B4** | **Xoá** `GET /api/v2/suc-khoe` khỏi bản sao | phải **MẤT ĐÚNG** route đó | `103 → 102`, mất đúng `['/api/v2/suc-khoe']` ✓ — chứng minh **không ghim cứng danh sách** |
| **B5** | **TỰ KIỂM BỘ ĐO CÁCH LY**: bỏ `WHERE tenant_id=?` khỏi truy vấn `/api/v2/audit` | phép đo cách ly **PHẢI ĐỎ** | `rò_ri=True`, ca **ĐỎ** ✓ |

> **B5 là ca quan trọng nhất của cả tệp.** Không có nó thì 32 ca xanh ở §3 vô nghĩa: một bộ đo
> không thể đỏ là bộ đo không đo.

**B1 đã bắt được một lỗi thật của chính bộ đo** ở lần chạy đầu: chỗ tiêm ban đầu nằm **sau**
`return` cuối của `_api_tenant`, tức là code không tới được, và bộ trích báo "không thấy route
giả" vì một lý do **sai**. Đã sửa neo tiêm về **trước nhánh rơi cuối**; ghi lại đây vì đó là
bằng chứng đột biến đang đo đúng thứ nó nói đo.

---

## 3. ĐO CÁCH LY TENANT CHO 31 MỤC CÒN THIẾU

### 3.1 Mục thứ 31 không phải route — đo, không lập luận

AG-06 đếm **104** route. Bộ thứ ba đo được **103**. Chênh lệch **đúng 1 mục**: `/api/v2/platform/`.

Đó là hằng số **tiền tố** của cổng chặn `if duong.startswith("/api/v2/platform/")` (`server.py:566`),
không phải một route. Bằng chứng **thi hành** (ca **A7**): phiên **CÓ quyền nền tảng** gọi đúng
đường đó → `404 {"loi": "không có đường này"}`, tức **rơi vào nhánh rơi**. Nếu nó trả bất cứ thứ
gì khác, ca A7 sẽ **ĐỎ** và kết luận này phải rút lại.

Hệ quả cho con số: **104 mục của AG-06 = 103 route thật + 1 artefact tiền tố.**
Khoảng trống G18 **31 mục = 30 route thật + 1 artefact**.

### 3.2 Nguyên tắc đo: mỗi phủ định phải có ĐỐI CHỨNG ĐƯỜNG

Mọi hàng của A nhúng dấu `canary_a`, của B nhúng `canary_b`. Ba vế, thiếu vế nào cũng làm phép
đo mất nghĩa:

1. **ĐỐI CHỨNG DƯƠNG** — chính route đó với **chủ sở hữu hợp lệ** trả **200** kèm dấu **CỦA
   CHÍNH MÌNH**. Không đạt ⇒ ghi thẳng **CHƯA ĐO**, không tính là đạt (yêu cầu 3 của đề bài).
2. **ĐỐI CHỨNG ĐƯỜNG** — lượt của B phải mang dấu **CỦA B**. Thiếu vế này thì "B không thấy dữ
   liệu A" có thể chỉ vì **B chẳng nhận được gì**.
3. **PHỦ ĐỊNH** — thân phản hồi của B **KHÔNG** được chứa `canary_a`.

Hai kiểu đường được đo **khác nhau**, và nói rõ ra:

* **`tenant`** — đường theo phiên: A thấy dấu A, B thấy dấu B.
* **`toan_cuc`** — danh mục toàn cục / dữ liệu tiến trình: hai tenant phải nhận **GIỐNG NHAU**
  và **không lượt nào** được chứa dấu tenant.

Ca **C1** còn tự kiểm **tính không-rỗng**: một ca có danh sách khẳng định **rỗng** thì `all([])`
là `True`, tức "đạt" mà không khẳng định gì. Ca này biến chuyện đó thành **ĐỎ**
(`khẳng định rỗng 0`).

### 3.3 Bảng kết quả — 32 ca / 31 mục

| # | mục | phương thức | kiểu | A (chủ sở hữu) | B (tenant khác) | rò rỉ | kết luận |
|---|---|---|---|---|---|---|---|
| 1 | `/api/v2/ai/su-kien` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 2 | `/api/v2/ai/thong-ke` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 3 | `/api/v2/audit` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 4 | `/api/v2/auth/dang-nhap` | POST | đăng nhập | 200 ✓ | 401 ✓ | không | ĐẠT |
| 5 | `/api/v2/auth/dat-lai-mat-khau` | POST | đặt lại MK | 200 ✓ | 200 ✓ | không | ĐẠT |
| 6 | `/api/v2/auth/quen-mat-khau` | POST | quên MK | 200 ✓ | 200 ✓ | không | ĐẠT |
| 7 | `/api/v2/auth/toi` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 8 | `/api/v2/billing` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 9 | `/api/v2/billing/du-thao` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 10 | `/api/v2/dang-ky` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 11 | `/api/v2/doi-soat/dot` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 12 | `/api/v2/don/can-doi-soat` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 13 | `/api/v2/don/xuat-csv` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 14 | `/api/v2/g09/can-soat` | GET | toàn cục | 200 ✓ | 200 ✓ | không | ĐẠT |
| 15 | `/api/v2/g09/suc-khoe-hang` | GET | toàn cục | 200 ✓ | 200 ✓ | không | ĐẠT |
| 16 | `/api/v2/goi` | GET | toàn cục | 200 ✓ | 200 ✓ | không | ĐẠT |
| 17 | `/api/v2/hang` | GET | toàn cục | 200 ✓ | 200 ✓ | không | ĐẠT |
| 18 | `/api/v2/san-sang` | GET | toàn cục | 200 ✓ | 200 ✓ | không | ĐẠT |
| 19 | `/api/v2/suc-khoe` | GET | toàn cục | 200 ✓ | 200 ✓ | không | ĐẠT |
| 20 | `/api/v2/tai-chinh/cod` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 21 | `/api/v2/tai-chinh/cong-no` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 22 | `/api/v2/tai-chinh/kiem-nhat-ky` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 23 | `/api/v2/tai-chinh/tong-so` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 24 | `/api/v2/usage` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 25 | `/api/v2/usage/bao-cao` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 26 | `/api/v2/usage/doi-soat` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 27 | `/api/v2/usage/su-kien` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 28 | `/api/v2/usage/tinh-phi` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| 29 | `/api/v2/webhook/nhan/{mã A}` | POST | tenant | **202** ✓ | 401 ✓ | không | ĐẠT |
| 30 | `/api/v2/webhook/nhan/{mã A}` (gửi lại) | POST | tenant | **200** ✓ | 401 ✓ | không | ĐẠT |
| 31 | `/api/v2/webhook/nhan/{mã B}` | POST | tenant | **202** ✓ | 401 ✓ | không | ĐẠT |
| 32 | `/api/v2/webhook/su-kien` | GET | tenant | 200 ✓ | 200 ✓ | không | ĐẠT |
| — | `/api/v2/platform/` (không phải route) | GET | — | 404 nhánh rơi ✓ | 404 nhánh rơi ✓ | — | ĐẠT (ca A7) |

**ĐẠT 32/32 · CHƯA ĐO 0 · RÒ RỈ 0 · khẳng định rỗng 0.**

### 3.4 Vì sao mỗi dòng ở trên không phải "xanh vì rỗng"

Vài mục có **thân phản hồi không chứa trường chuỗi nào**, nên không thể tìm dấu bằng chuỗi.
Chúng được đo bằng **số phân biệt được**, và điều đó được ghi thẳng trong ca:

| Mục | Không có chuỗi ⇒ đo bằng gì | A | B |
|---|---|---|---|
| `/api/v2/tai-chinh/kiem-nhat-ky` | `so_dong` (số dòng sổ, khác nhau theo fixture) | `"so_dong": 1` | `"so_dong": 2` |
| `/api/v2/usage/doi-soat` | `so_su_kien` của loại `api_thang` | `"so_su_kien": 2` | `"so_su_kien": 5` |
| `/api/v2/usage`, `/api/v2/usage/tinh-phi`, `/api/v2/dang-ky` | `tenant_id` là số định danh tenant | `"tenant_id": <A>` | `"tenant_id": <B>` |
| `/api/v2/billing` | `usage_thang.so_don` | `"so_don": 7` | `"so_don": 23` |

Ba mục dùng chung khuôn `tenant` nhưng **đo bằng đường khác** vì cửa không có dữ liệu tenant
trong thân phản hồi (đúng như khảo sát handler):

* `/api/v2/auth/dang-nhap` — A đúng mật khẩu ⇒ **200 + `Set-Cookie: phien=`**; A **sai** mật khẩu
  ⇒ **401 và KHÔNG có cookie**; và B đăng nhập được thì phiên đó phải dẫn tới **đúng tenant B**
  (đo bằng `/api/v2/auth/toi` với chính token vừa nhận).
* `/api/v2/auth/quen-mat-khau` — thân phản hồi cho tên **CÓ THẬT** phải **TRÙNG** thân cho tên
  **KHÔNG có** (không dò được tài khoản), và **không** được lộ dấu của A.
* `/api/v2/auth/dat-lai-mat-khau` — token hợp lệ của A ⇒ 200; token **của B** ⇒ 200 cho tài khoản
  B nhưng **băm mật khẩu của A KHÔNG đổi**; token **bịa** ⇒ 400.

Với cửa webhook, hợp đồng **không** phải 200 cho lượt đầu: lượt đầu của một `event_id` mới là
**202**, lượt **gửi lại cùng `event_id`** là **200** (`da_nhan_truoc_do`). Vì yêu cầu của đề bài
là *"chính route đó với chủ sở hữu hợp lệ phải trả 200"*, lượt này đo **CẢ HAI** (ca 29 và ca 30)
chứ không miễn trừ mã 202. Chiều phủ định cũng đo **cả hai hướng**: ký bằng bí mật của tenant
khác trên mã webhook của A ⇒ **401** (ca 29/30), và ngược lại (ca 31).

Ca 32 khép vòng: sự kiện `EVT-<dấu A>` do ca 29 đẩy vào **phải HIỆN** trong `/api/v2/webhook/su-kien`
của A và **VẮNG** ở lượt của B — tức phép ghi của webhook rơi **đúng** tenant.

### 3.5 Mọi thao tác chỉ chạm loopback

| Ca | Con số đo được |
|---|---|
| **A4** (bộ trích) | **420** lượt `socket.connect()` · **0** lượt ra ngoài loopback |
| **C0** (phép đo cách ly) | **67** lượt `socket.connect()` · **0** lượt ra ngoài loopback |

Số lượt connect thay đổi chút giữa các lượt chạy (ba cửa đăng nhập/đặt lại mật khẩu tự gọi
thêm 2-4 lượt mỗi ca); bất biến được **khẳng định** là **0 lượt ra ngoài loopback**, không phải
con số 67. Máy chủ đo **luôn** bind `127.0.0.1` **cổng 0** (hệ điều hành cấp). Đây là bằng chứng cho BAN 1
(*"không gọi hãng kể cả sandbox"*) — **đo**, không phải lời hứa.

---

## 4. GIỚI HẠN ĐÃ ĐO — NÓI THẲNG

### 4.1 Cấp (đường, phương thức): hai bên lệch 8 cặp, và **cả hai đều có phần sai**

| Bên | Số cặp | Chi tiết | Ai đúng |
|---|---|---|---|
| Bộ ba (G19) | **144** | — | — |
| AG-06 (mở rộng mục "không có nhánh `method`" ra 4 phương thức) | **150** | — | — |
| Bộ ba **thừa** | **1** | `DELETE /api/v2/platform/tenants/{id}` | **AG-06 đúng.** `_can` chạy **TRƯỚC** khi kiểm phương thức nên trả **403**, và 403 bị bộ ba tính là "có route" |
| AG-06 **thừa** | **7** | 4 cặp thuộc `/api/v2/platform/` (không phải route) + 3 cặp `GET/PUT/DELETE` của `/api/v2/webhook/nhan/{ma}` | **Bộ ba đúng.** Cửa webhook chỉ nhận **POST**; ba lượt kia trả **404 nhánh rơi** |

**Hệ quả phương pháp:** mọi **khẳng định độ phủ** trong báo cáo này ở cấp **ĐƯỜNG**, không ở cấp
phương thức. Bộ phân loại theo phản hồi **không phân biệt được** *"có handler cho phương thức
này"* với *"khớp mẫu nhưng không có handler, hoặc bị `_can` chặn trước"*. Ca **A8** ghim con số
này lại để lượt sau không phải đoán.

### 4.2 Giả định của không gian ứng viên (được KHAI, không được chứng minh)

Không gian ứng viên đầy đủ **nếu** mọi route được so bằng một hằng số **có mặt trong mã đã biên
dịch**. Route dựng bằng f-string rồi so (`if duong == f"/api/v2/x/{y}"`) sẽ bị **bỏ sót**.

Đã kiểm `app/server.py`: f-string chứa `/api/v2` **duy nhất một chỗ** (dòng 849) và nó để **DỰNG
URL** trả cho khách, không phải để so. Nhưng đây là **giả định được khai báo**, không phải điều
lượt này chứng minh. Đột biến B1 (tiêm route bằng hằng số) không kiểm được nhánh giả định này.

### 4.3 Phạm vi bằng chứng cách ly ở con số **103/103**

Con số **103/103** = **73 route có bằng chứng V5 từ bộ của AG-01** (đo ở G18, **không chạy lại**
trong lượt này) **+ 30 route đo trong lượt này**. Nói cách khác: 30 route của lượt này là bằng
chứng **mới, độc lập**; 73 route kia là bằng chứng **kế thừa**, lượt này **không** đo lại.

Và 30 route của lượt này phần lớn là đường **ĐỌC theo phiên**; tính chất được đo là *"tenant B
nhận dữ liệu CỦA B, không nhận dữ liệu của A"*, chứ không phải một phép thử xâm nhập theo id.
Các đường **có tham số** (`/api/v2/don/{id}`, `/api/v2/khach-hang/{id}`…) **không** nằm trong
khoảng trống 31 mục — chúng đã thuộc 73 route của AG-01.

---

## 5. NHỮNG GÌ **NẰM NGOÀI PHẠM VI** LƯỢT NÀY

Nói rõ để con số không bị đọc quá mức:

1. **Nghiệm thu G16-A / G17 / G18 không được làm lại.** 1460 ca/38 bộ (G17), 1631 ca/44 bộ (G18),
   7/7 lời khai khớp — giữ nguyên như đã đạt, lượt này **không** chạy lại và **không** đụng vào.
2. **Mã trạng thái `110` (D-4) KHÔNG được phán quyết.** `/api/v2/g09/can-soat` chỉ được khẳng
   định là *dữ liệu có mặt, giống nhau ở hai tenant, và ca không vỡ* — nghĩa của mã 110 vẫn là
   câu hỏi mở của G09. Không có mã trạng thái nào chưa được hãng xác minh bị đoán ở đây.
3. **Không có phép đo lớp HTTP nào ra khỏi loopback**, kể cả sandbox: `V-G09-01` + `V-13906-05`
   chưa cấp. Adapter vẫn MOCK; `CHO_PHEP_LIVE` không bị mở.
4. **Không** push · không deploy · không tunnel · không mở cổng · không credentials thật · không
   `.env`. Nghiệp vụ vẫn **SQLite**; cụm PostgreSQL `:5432` (đang giữ `vip_customs*`) **không**
   được dùng tới.
5. **Chốt D-9 (city/area chặn cứng ngoài mock) không bị đụng tới** — không route nào trong 30
   mục đi qua đường ánh xạ city/area.
6. **Không thêm tính năng nào.** Lượt này chỉ **đo** và **ghi tài liệu**; `app/` không bị sửa
   một dòng nào (§6.3).
7. **Không kiểm** được: route dựng động bằng f-string (§4.2); hành vi dưới tải đồng thời; và mọi
   thứ thuộc tầng giao diện.

---

## 6. BẰNG CHỨNG — LỆNH THẬT, EXIT CODE THẬT, SHA THẬT

### 6.1 Bộ trích route thứ ba

```sh
$ python3 trien_khai/g19/bot_route_thi_hanh.py --ra /tmp/g19_liet_ke.json
```
**exit = 0** · 83 hằng số · 105 ứng viên · **103 route** · 420 lượt đo · 276 lượt bị loại ·
**0 lượt không kết luận** · **144 cặp** (đầu ra đầy đủ ở §1.3)

### 6.2 Bộ ca 49 test

```sh
$ python3 app/thu/thu_g19_route.py > /tmp/g19_thu.log 2>&1 ; echo "EXIT=$?"
EXIT=0
$ grep -E "^Ran |^OK$|^FAILED" /tmp/g19_thu.log
Ran 49 tests in 11.645s
OK
$ grep -c "\.\.\. ok$" /tmp/g19_thu.log
49
```
*(thời gian chạy thay đổi giữa các lượt, khoảng 9-17 giây; số ca thì cố định.)*

**49 ca · 0 hỏng · 0 bỏ qua (skip)** — `unittest` chỉ in `skipped=` khi có ca bị bỏ qua; đầu ra
`OK` không kèm `skipped` nghĩa là **0 skip**.

```sh
$ sh trien_khai/g19/chay_g19.sh ; echo "EXIT_RUNNER=$?"
EXIT_LIET_KE=0
EXIT_THU=0
EXIT_RUNNER=0
```

### 6.3 Cây làm việc sạch — không tệp cũ nào bị sửa

```sh
$ git rev-parse HEAD
6e61fc1e1f1f9a6d64931464e4f40ed887192ab5

$ git status --porcelain
?? app/thu/thu_g19_route.py
?? docs/G19_ROUTE_COVERAGE.md
?? trien_khai/g19/

$ git diff --name-only | wc -l
       0
```

**0 tệp đã theo dõi bị sửa.** Ba đường dẫn trên đều là tệp **mới** của lượt này, đúng danh sách
được cấp phép: `app/thu/thu_g19_route.py`, `trien_khai/g19/`, `docs/G19_ROUTE_COVERAGE.md`.

### 6.4 SHA-256 của các tệp mới

```
a73fc6c1f73966ccb768d3990d33766df871e66297a38611d1b4f25e9929fd8a  app/thu/thu_g19_route.py
1ffd1d0e37d4bd4c33412e4059bd76ea34850c8ac1b72ba447b95795afd4ae63  trien_khai/g19/bot_route_thi_hanh.py
7413d9f904b395b1f1f9cf144afc367e295b86e2bb503c9c9402f8eb46c58a57  trien_khai/g19/may_chu_do.py
0861d6880c29b224338ab5f9c2ff67ee2244a234cd615a1637c727b8fbf6b0ce  trien_khai/g19/chay_g19.sh
edb5c5865cfb20aeaac6140560623713643a99b8fc96938d084e4f8b7dfeac38  trien_khai/g19/README.md
```

---

## 7. DANH SÁCH 31 MỤC VÀ TRẠNG THÁI CUỐI

| # | mục | trạng thái |
|---|---|---|
| 1 | `/api/v2/ai/su-kien` | **ĐÃ ĐO** — §3.3 dòng 1 |
| 2 | `/api/v2/ai/thong-ke` | **ĐÃ ĐO** — dòng 2 |
| 3 | `/api/v2/audit` | **ĐÃ ĐO** — dòng 3 (kèm đột biến tự kiểm B5) |
| 4 | `/api/v2/auth/dang-nhap` | **ĐÃ ĐO** — dòng 4 |
| 5 | `/api/v2/auth/dat-lai-mat-khau` | **ĐÃ ĐO** — dòng 5 |
| 6 | `/api/v2/auth/quen-mat-khau` | **ĐÃ ĐO** — dòng 6 |
| 7 | `/api/v2/auth/toi` | **ĐÃ ĐO** — dòng 7 |
| 8 | `/api/v2/billing` | **ĐÃ ĐO** — dòng 8 |
| 9 | `/api/v2/billing/du-thao` | **ĐÃ ĐO** — dòng 9 |
| 10 | `/api/v2/dang-ky` | **ĐÃ ĐO** — dòng 10 |
| 11 | `/api/v2/doi-soat/dot` | **ĐÃ ĐO** — dòng 11 |
| 12 | `/api/v2/don/can-doi-soat` | **ĐÃ ĐO** — dòng 12 |
| 13 | `/api/v2/don/xuat-csv` | **ĐÃ ĐO** — dòng 13 (thân là **CSV**, không phải JSON) |
| 14 | `/api/v2/g09/can-soat` | **ĐÃ ĐO** — dòng 14 · mã 110 **có mặt**, nghĩa của nó **KHÔNG** bị phán quyết |
| 15 | `/api/v2/g09/suc-khoe-hang` | **ĐÃ ĐO** — dòng 15 |
| 16 | `/api/v2/goi` | **ĐÃ ĐO** — dòng 16 |
| 17 | `/api/v2/hang` | **ĐÃ ĐO** — dòng 17 |
| 18 | `/api/v2/platform/` | **KHÔNG PHẢI ROUTE** — ca A7, bằng chứng thi hành (§3.1) |
| 19 | `/api/v2/san-sang` | **ĐÃ ĐO** — dòng 18 |
| 20 | `/api/v2/suc-khoe` | **ĐÃ ĐO** — dòng 19 (vô danh) |
| 21 | `/api/v2/tai-chinh/cod` | **ĐÃ ĐO** — dòng 20 |
| 22 | `/api/v2/tai-chinh/cong-no` | **ĐÃ ĐO** — dòng 21 |
| 23 | `/api/v2/tai-chinh/kiem-nhat-ky` | **ĐÃ ĐO** — dòng 22 (đo bằng `so_dong`) |
| 24 | `/api/v2/tai-chinh/tong-so` | **ĐÃ ĐO** — dòng 23 |
| 25 | `/api/v2/usage` | **ĐÃ ĐO** — dòng 24 |
| 26 | `/api/v2/usage/bao-cao` | **ĐÃ ĐO** — dòng 25 |
| 27 | `/api/v2/usage/doi-soat` | **ĐÃ ĐO** — dòng 26 (đo bằng `so_su_kien`) |
| 28 | `/api/v2/usage/su-kien` | **ĐÃ ĐO** — dòng 27 |
| 29 | `/api/v2/usage/tinh-phi` | **ĐÃ ĐO** — dòng 28 |
| 30 | `/api/v2/webhook/nhan/{ma}` | **ĐÃ ĐO** — dòng 29 (202) + 30 (200) + 31 (chiều ngược) + 32 (khép vòng) |
| 31 | `/api/v2/webhook/su-kien` | **ĐÃ ĐO** — dòng 32 |

**Còn thiếu: 0 mục.** Không có mục nào bị bỏ qua vì thiếu dữ liệu hay thiếu quyền — mọi mục đều
dựng được fixture và có đối chứng dương **200** thật (hoặc **202 + 200** với cửa webhook, đo cả hai).

---

## 8. PHÁT HIỆN MANG VỀ CHO CÁC LƯỢT SAU

1. **Con số `104` của AG-06 gồm 1 artefact.** `/api/v2/platform/` là **hằng số tiền tố** của cổng
   chặn, bị bộ AST đếm thành route. Số route thật là **103**. Đề nghị AG-00 ghi lại mốc
   **`103 route thật`** thay cho `104`, kèm cách đo (ca A7).
2. **`docs/OWNER_ACTIONS.md` từng ghi "V5 phủ 41 cửa"** — `docs/QA_G18_INTEGRATED.md` §5.4 đã chỉ
   ra đó là **artefact**; lượt này xác nhận lại bằng đường đo thứ ba: mốc đúng là **73/104 mục**,
   và sau lượt này là **103/103 route thật**.
3. **Cấp phương thức chưa có dụng cụ nào đo đúng.** Bộ ba thừa 1 cặp, AG-06 thừa 7 cặp, và cả hai
   đều vì những lý do **khác nhau, đã đo được** (§4.1). Ai cần độ phủ theo phương thức thì phải
   dựng dụng cụ thứ tư (gợi ý: đếm nhánh `method ==` **bằng thi hành**, ví dụ chèn bộ đếm vào
   bản sao rồi lái bằng yêu cầu thật), **không** suy ra từ bộ ba hay AG-06.
4. **Cửa `/api/v2/webhook/nhan/{ma}` chỉ nhận POST** nhưng AG-06 khai là nhận mọi phương thức.
   Nếu có tài liệu nào dựa vào "mọi phương thức" của cửa này thì tài liệu đó **sai**; bằng chứng:
   3 lượt `GET/PUT/DELETE` trả **404 nhánh rơi** (ca A8).
5. **`/api/v2/hang`, `/api/v2/audit`, `/api/v2/billing` không kiểm phương thức** (không có
   `method ==` trong nhánh) — chúng phục vụ **mọi** phương thức. Đây là **quan sát**, không phải
   khuyến nghị sửa: lượt này **không** thêm tính năng và **không** sửa `app/`.
