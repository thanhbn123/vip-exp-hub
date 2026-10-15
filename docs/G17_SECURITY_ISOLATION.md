# G17-AG06 — BẢO MẬT & CÁCH LY TENANT: BA CỔNG **V5 · V6 · V7 TOÀN CỤC**

> **Trạng thái: ĐỀ XUẤT.** AG-00 đề xuất lượt này; **Owner CHƯA chốt**. Mọi câu dưới đây là
> **kết quả ĐO**, không phải nghiệm thu. Ba cổng V5/V6/V7 vẫn thuộc quyền phán của AG-01/Owner.
>
> **Phạm vi ghi của làn:** chỉ hai tệp — `app/thu/thu_g17_baomat.py` (mới) và tài liệu này.
> Đoạn mã sản phẩm nào cũng **không** bị sửa. `git status` trên nhánh `g17-ag06-security`:
> đúng hai tệp mới, không tệp nào khác.

## 0. Vì sao có lượt này

`docs/QA_G13_G15.md` §L2.8 (AG-01 **tự ghi**) nói thẳng: ba cổng sau **chưa bao giờ được đo độc
lập**, và `docs/G16_ACCEPTANCE.md` §8 mục 3 xác nhận tới G16 chúng **vẫn mở**:

| Cổng | AG-01 nói gì ở §L2.8 | Cần gì để đóng |
|---|---|---|
| **V5** Cách ly tenant toàn cục | mới đo **đường webhook** | dựng 2 tenant + quét **mọi cửa** `/api/v2/*` |
| **V6** RBAC | chưa chạy lại ma trận `role × hành_động` | ma trận **động** trên `role_permissions` |
| **V7** AES-256-GCM đầy đủ | chưa tự sửa bản mã / đổi chỗ bản mã / thử sai AAD | bộ ca riêng, không mượn `thu_bao_mat.py` |

Lượt này dựng phép đo **riêng** cho cả ba, ở tầng **HTTP thật + CSDL thật**, không mượn bộ thử
của ai. Bốn hàm hợp đồng `ma_hoa_cred` / `giai_ma_cred` / `ma_hoa_wh` / `giai_ma_wh` **chỉ được
GỌI**, không viết lại (có ca `M1` khẳng định chữ ký hàm còn nguyên).

---

## 1. Lệnh chạy — kết quả THẬT

```sh
$ python3 app/thu/thu_g17_baomat.py
...
Ran 31 tests in 6.240s

OK
$ echo $?
0
```

Ba lượt liên tiếp: **6.419 s · 6.132 s · 6.169 s**; lượt chạy trên **bản chốt** (tệp đã đóng
băng): **`Ran 31 tests in 5.693s` · `OK` · exit `0`** — không có ca nào bị bỏ qua.

Môi trường đo **do chính bộ thử dựng**, in ra ở cuối mỗi lượt chạy:

```
  CSDL      : SQLite schema v8 tại /var/folders/…/vip-hub-ag06-XXXX   (thư mục TẠM riêng)
  máy chủ   : 127.0.0.1:63496 (cổng 0, hệ tự cấp) · tiến trình đơn
  cửa quét  : 113 lượt cửa × 2 (A đối chứng dương + B phủ định) = 226 lượt HTTP
  đo CHẶT   : 90 cửa (mã chính xác + dấu vết A) · đo 'qua được cửa': 23 cửa ghi có hồ sơ sâu
  RBAC      : lưới HTTP 50 cửa × 4 vai trò tenant = 200 ô · ma trận CSDL = 168 ô (từng ô)
  ảnh chụp  : hàng của B đổi trong lượt B: 51 · hàng CỦA A bị đụng: 0 · audit thiếu nhãn tenant: 1
  sổ nhóm   : E(4/4) M1(1/1) … V(113/113) V1(1/1) V2(0/113) V3(113/1) V4(1/1) V5(1/1) V6(8/1) W(5/5) X(1/1)
```

**Không một byte ra mạng**: adapter hãng ở chế độ `MOCK` (trong tiến trình); máy chủ chỉ bind
`127.0.0.1` **cổng 0** (hệ tự cấp) nên bốn làn chung một cây không tranh cổng (bài học R-13).
Không gọi API hãng, kể cả sandbox; không mở `CHO_PHEP_LIVE`; không sửa `cau_hinh.py`.

---

## 2. V5 — CÁCH LY TENANT TOÀN CỤC

### 2.1 Cách đo (và vì sao đo được)

1. **Hai tenant THẬT**: A và B, hai bộ người dùng riêng (A có owner/admin/staff/viewer + 7 tài
   khoản phụ; B có owner + 3). Không dùng chung một người dùng cho hai tenant — có chung thì
   "B đọc được dữ liệu A" là chuyện hợp pháp, không phải lỗi.
2. **Dấu vết A** (`SI = "AG06A-…"`, **ngẫu nhiên mỗi lượt chạy**) được nhét vào **mọi loại dữ
   liệu của A**: tên tenant · tên khách · tên hàng · ghi chú đơn · credentials (3 tài khoản hãng)
   · webhook secret · tên file & nội dung lô import · mã đợt thanh toán · lý do điều chỉnh · bảng
   kê đối soát · payload việc AI · chi tiết audit. Nhờ vậy "B có thấy dữ liệu A không" là một
   phép `in` chuỗi trên **bytes thô** của phản hồi — phủ cả JSON lẫn CSV, không chỉ JSON.
3. **Bảng cửa 113 cửa** phủ **mọi** route `/api/v2/*` (xem Phụ lục A). Mỗi cửa chạy **HAI** lượt:
   * **lượt A** — chủ sở hữu hợp lệ, **đối chứng DƯƠNG**;
   * **lượt B** — tenant B (hoặc người vô danh với cửa vô danh), **lượt phủ định**.
4. **Canh KHAI BÁO bằng AST** (`test_v1`): bộ thử tự trích mọi cặp `(route, method)` mà
   `server.py` **thật sự so sánh**, rồi bắt bảng cửa phải khai đủ — và **chiều ngược lại**:
   khai một route không tồn tại cũng ĐỎ. Thêm route mới mà quên khai ⇒ **bộ thử đỏ**, không im.
5. **Ảnh chụp CSDL trước/sau lượt B**: so **từng hàng** của **mọi bảng**; phân loại chủ sở hữu
   theo `tenant_id`, theo bảng cha (`don_lich_su`→`don_hang`, `import_dong`→`import_batch`,
   `wh_su_kien`→`carrier_accounts`, `don_mat_hang`→`don_hang`), theo `users`/`sessions`; bảng
   toàn cục (`roles`, `permissions`, `role_permissions`, `goi_dich_vu`, `carrier_providers`,
   `schema_version`) **không được đổi một hàng nào**; hàng **không rõ chủ** ⇒ **ĐỎ** (buộc phải
   khai cách phân loại, không được bỏ qua im lặng).

### 2.2 Kết quả đo

| Chỉ số | Số đo |
|---|---|
| Cửa đã quét | **113** (×2 lượt = **226** lượt HTTP) |
| Bộ thử có **RÒ dấu vết A** ở lượt B | **0** |
| Hàng **CỦA A** bị lượt B thêm/sửa/xoá | **0** |
| Hàng **CỦA B** đổi trong lượt B (đối chứng dương của ảnh chụp) | **51** |
| Audit ghi bằng `tenant_id=NULL` | **1** (`doi_tenant` bị từ chối của B — xem §6) |
| Mã trả cho A | 98×200 · 10×201 · 1×202 · 2×400 · 2×409 |
| Mã trả cho B | 49×200 · 9×201 · 1×400 · 13×403 · 37×404 · 4×409 |

**15 cửa mà A KHÔNG nhận 200 — đọc kèm, không giấu:**

* 11 cửa **tạo mới**: A nhận `201`/`202` (đúng thiết kế: `POST /don`, `/khach-hang`,
  `/memberships`, `/tai-khoan-hang`, `/import`, `/ai/job`, `/tai-chinh/dieu-chinh`,
  `/tai-chinh/dot-thanh-toan`, `/doi-soat/nap`, `/platform/tenants`; `replay` trả `202`).
* `POST /auth/doi-mat-khau` — A **cố ý** gõ sai mật khẩu cũ ⇒ `400`; B cũng `400` cho **chính tài
  khoản B** (đối chứng dương: cửa chạy được cho cả hai, chỉ khác tài khoản).
* 3 cửa **đo lỏng** (23 cửa thuộc nhóm này — cửa ghi cần hồ sơ nghiệp vụ sâu): A bị **trạng thái
  nghiệp vụ** từ chối, không phải bị chặn quyền/tenant —
  `POST /don/{id}/doi-soat-tay` (409: đơn chưa ở trạng thái "không rõ kết quả"),
  `POST /dang-ky/doi-goi` (409: gói đích bị chính sách gói từ chối),
  `POST /ai/job/{id}/tu-choi` (400: việc AI chưa chạy nên chưa có gì để từ chối).
  Với ba cửa này, phép đo **chỉ** khẳng định: A **qua được cửa quyền và cửa tenant**
  (mã ∉ {401,403,404,5xx}), B thì **404**; tài liệu này **không** nói "A thực hiện thành công".

**Số cửa theo họ** (đủ 113): `don` 21 · `ai` 13 · `platform` 12 · `tai-chinh` 11 · `doi-soat` 9 ·
`import` 7 · `tai-khoan-hang` 6 · `usage` 6 · `auth` 5 · `memberships` 4 · `khach-hang` 3 ·
`tenant` 2 · `webhook` 2 · `dang-ky` 2 · `billing` 2 · `g09` 2 · `suc-khoe`/`san-sang`/`hang`/
`polling`/`goi`/`audit` mỗi họ 1.

### 2.3 Vì sao "B bị chặn" ở đây KHÔNG vô nghĩa

Đây là chỗ dễ tự lừa nhất: một cửa **hỏng sẵn cho mọi người** cũng làm "B bị chặn" xanh. Bốn chốt
chống điều đó, cả bốn đều **có thật trong mã**:

1. **Đối chứng dương trên CHÍNH cửa đó**: lượt A chạy cùng đường, cùng payload. Cửa nào A không
   qua được ⇒ `test_v2` **ĐỎ** và cửa đó bị ghi là **CHƯA ĐO ĐƯỢC**, không tính là cách ly.
2. **Ảnh chụp có đối chứng dương**: `test_v4` khẳng định **> 0 hàng của B đã đổi** trong lượt B.
   Nếu lượt B chẳng ghi được gì thì câu "không hàng nào của A bị đụng" là vô nghĩa — và bộ thử
   tự báo hỏng. Số đo: **51** hàng.
3. **Ca riêng cho switch-tenant** (`test_v5`): B đòi vào tenant A ⇒ **403**, và
   `sessions.active_tenant_id` của B **không đổi** — kiểm **thẳng trong CSDL**, không tin mã HTTP.
4. **Ca `tenant_id` TỰ KHAI** (`test_v6`): bơm `tenant_id` của A vào **query** (5 cửa) và **body**
   (2 cửa + 1 cửa tạo mới). Kết quả: không rò dấu vết A; hàng B tạo ra khi tự khai `tenant_id=A`
   **vẫn thuộc B** (đếm trong CSDL: số khách hàng của A **không tăng**).

### 2.4 Cửa vô danh & webhook — đo riêng (nhóm `W`)

| Ca | Phép đo | Kết quả |
|---|---|---|
| `W1` | đăng nhập sai ⇒ 401, **không** nhận cookie; đúng ⇒ 200 + cookie | đạt |
| `W2` | quên mật khẩu: tài khoản **có thật** và **không có thật** trả **cùng mã + cùng thông báo**; cửa vô danh **không** trả token | đạt |
| `W3` | token đặt lại mật khẩu **bịa** ⇒ 400 | đạt |
| `W4` | webhook **chữ ký sai** ⇒ 401 và `wh_su_kien` **không thêm dòng nào**; ký đúng ⇒ 202 (đối chứng dương nằm ở fixture) | đạt |
| `W5` | B ký bằng secret **CỦA B** vào `webhook_ma` **CỦA A** ⇒ 401, không sự kiện nào vào tài khoản A; B ký đúng cho tài khoản B ⇒ 202 | đạt |

---

## 3. V6 — RBAC: MA TRẬN **ĐỘNG** `role × hành_động`

Bốn tầng đo, mỗi tầng bắt một kiểu hỏng khác nhau:

| Tầng | Ca | Phép đo | Kết quả |
|---|---|---|---|
| Lưới CSDL | `R1` | **6 vai trò × 28 quyền = 168 ô**, đối chiếu **từng ô** với bảng `role_permissions` | 168/168 khớp |
| Đột biến (hàm) | `R2` | **CẤP** một ô **KHÔNG có trong hằng `MA_TRAN`** (`TENANT_VIEWER × tenant.khach.ghi`) ⇒ `co_quyen` phải đổi thành True | đạt |
| Đột biến (hàm) | `R3` | **THU** một ô đang có (`TENANT_OWNER × tenant.khach.xem`) ⇒ `co_quyen` phải thành False | đạt |
| Đột biến qua HTTP | `R4` | viewer được cấp `tenant.khach.ghi` ⇒ `POST /khach-hang` **201**; gỡ ra ⇒ **403**. Chủ doanh nghiệp bị thu `tenant.khach.xem` ⇒ `GET /khach-hang` **403**; trả lại ⇒ **200** | đạt |
| Lưới HTTP | `R5` | **50 cửa đọc × 4 vai trò = 200 ô**: thiếu quyền ⇒ **đúng 403**; có quyền ⇒ **không được 403** | 200/200 khớp |
| Canh quyền chết | `R6` | mọi chuỗi quyền mà mã **hỏi tới** phải có trong bảng `permissions`; quyền seed mà **không ai hỏi** cũng là quyền chết | 29 hỏi → 28 có trong bảng · **1 ngoại lệ F-01** · 0 quyền chết |

**Vì sao `R2`/`R3` mới là phép chứng minh "theo DỮ LIỆU, không theo hằng viết cứng":** `quyen.py`
**có** hằng `MA_TRAN` (nguồn để seed). Nếu `co_quyen()` lỡ đọc hằng đó thay vì bảng, lưới `R1` vẫn
xanh (vì seed và hằng khớp nhau lúc đầu). `R2` cấp một ô **không có trong hằng** — chỉ hàm đọc
**bảng** mới trả True. `R3` thu một ô **có trong hằng** — chỉ hàm đọc **bảng** mới trả False. Đo
được: **cả hai chiều đều đi theo bảng**, và `R4` khẳng định điều đó qua **HTTP thật** ở **từng
yêu cầu** (không cache quyền vào phiên).

**Canh quyền chết trích bằng AST, không grep** — vì grep bắt nhầm **nhãn trần tần suất**
(`platform.quan_tri`, `webhook.nhan`, `ai.goi`…) và nhầm cả **quyền con** của tài chính
(`_can_quyen_tc(..., "duyet")`, không phải mã quyền trong bảng). Bộ trích chỉ nhận chuỗi dạng
`tenant.*`/`platform.*` truyền vào `_can` / `_can_quyen` / `_can_quyen_tc` / `co_quyen`, và **đi cả
vào trong biểu thức** (đã dính một lần: bỏ sót `"platform.goi.doi" if … else "platform.tenant.khoa"`
⇒ báo "quyền chết" **sai** — xem §7.4).

---

## 4. V7 — AES-256-GCM ĐẦY ĐỦ

Bảy ca, **đều có đối chứng dương** (bản gốc phải giải được trước khi khẳng định bản sửa hỏng):

| Ca | Phép đo | Kết quả |
|---|---|---|
| `M1` | 4 hàm hợp đồng **còn đúng chữ ký**; bản mã mới khớp `^v3\$<key_id>\$<nonce>\$<ct>$`; `key_id_cua()` = khóa hiện hành; secret **sinh qua HTTP** (tạo tài khoản hãng) cũng là `v3$…` và giải đúng bằng `giai_ma_cred` | đạt |
| `M2` | **sửa 1 byte** phần ciphertext ⇒ giải mã **HỎNG**; sửa 1 byte phần **nonce** cũng hỏng | đạt |
| `M3` | **ĐỔI CHỖ bản mã credentials giữa hai tenant TRONG CSDL** (cùng hãng `jt`) ⇒ `giai_ma_cred` **HỎNG**; và **đường HTTP thật** (`POST /don/{id}/gui` → `_adapter_cua_account` giải mã) **không** trả 200, đơn của A **không** đổi trạng thái | đạt |
| `M4` | **ĐỔI CHỖ `webhook_secret_ma_hoa` giữa A và B** ⇒ chữ ký **ĐÚNG** của A (đã đạt 202 trước khi tráo) bị **401**, và `wh_su_kien` không thêm dòng | đạt |
| `M5` | **sai AAD**: sai tenant · sai hãng · hãng có khoảng trắng · tenant không tồn tại ⇒ **HỎNG** (4 lượt); sai `webhook_ma` (khác/rỗng/khoảng trắng) ⇒ hỏng (3 lượt); gọi trần `giai_ma(..., aad="")` ⇒ hỏng | đạt |
| `M6` | **sai `key_id`**: key_id bịa ⇒ hỏng; đổi sang một **khóa CÓ THẬT nhưng khác** ⇒ **cũng hỏng**; key_id trong bản mã **không đổi** sau đó (không âm thầm sinh khóa mới) | đạt |
| `M7` | **AES chạy thật**: cùng plaintext hai lượt ⇒ hai bản mã **KHÁC NHAU** (nonce ngẫu nhiên) và **cả hai** giải đúng; giải bằng sai hãng ⇒ hỏng | đạt |

`M7` là **đối chứng dương nền**: không có nó thì "sửa byte là hỏng" có thể đúng một cách vô nghĩa
(vì mọi thứ đều hỏng).

---

## 5. TỰ KIỂM BỘ ĐO — làm cho nó **ĐỎ** được

| Ca | Cách làm bộ đo đỏ | Kết quả |
|---|---|---|
| `E1` | chạy một ca **CỐ Ý HỎNG** trong **tiến trình con** | bộ dò thấy: exit ≠ 0, **không** có dòng `OK` |
| `E2` | **tiêm một route GIẢ** (`/api/v2/zz-kiem-tra-dot-bien`) vào **bản sao** `server.py` | phép canh khai báo **thấy** route lạ và kêu thiếu |
| `E3` | đưa bộ dò rò rỉ một phản hồi **GIẢ CÓ chứa dấu vết A** | bộ dò kêu `RÒ`; phản hồi sạch thì im (không kêu nhầm) |
| `E4` | **sao toàn bộ `app/` sang thư mục tạm, BỎ BỘ LỌC TENANT** của `GET /api/v2/khach-hang/{id}` rồi chạy **chính tệp này** ở bản sao | bản sao **ĐỎ**, thông báo đúng `RÒ dấu vết của A`, và **chỉ đúng cửa** vừa bị phá |

`E4` là chốt mạnh nhất và **đã chạy thật**: nó sao `app/` (~1 MB) sang thư mục tạm, sửa một câu
SQL rồi chạy **lại cả bộ thử** ở bản sao (bản sao tự bỏ qua `E4` nhờ `VIP_AG06_KHONG_TU_DOT_BIEN=1`,
chống đệ quy). Đo riêng ca này: **2,94 s** (`unittest` chạy `E4` một mình, `OK`). **Bản đột biến đầu tiên của tôi SAI NGHĨA**: chỉ
xoá chuỗi ` AND tenant_id=?` nên câu SQL thừa tham số ⇒ **500 cho cả hai tenant**, tức bộ thử đỏ
vì "chưa đo được" **chứ không phải vì bắt được rò rỉ**. Đã sửa thành bản đột biến **giữ đúng số
tham số** (`WHERE id=?`, một tham số) ⇒ A 200, B **200 kèm dữ liệu A** ⇒ bộ dò kêu `RÒ`. Ghi lại
vì đây đúng là §7.1: *thứ dùng để kiểm chứng phải được kiểm trước khi tin*.

---

## 6. PHÁT HIỆN (kèm mức và bằng chứng)

### `F-01` · **LOW** · Quyền `tenant.billing.quan_ly` được mã hỏi nhưng **không tồn tại** trong bảng
`server.py` (dòng 1187) viết:
`self._can(nc, "tenant.billing.quan_ly" if quyen.co_quyen(nc.role, "tenant.billing.quan_ly") else "tenant.membership.quan_ly")`.
`tenant.billing.quan_ly` **không** có trong `quyen.QUYEN` ⇒ không có dòng nào trong `permissions`
⇒ `co_quyen` **luôn False** ⇒ **nhánh ba ngôi là nhánh CHẾT**; trên thực tế `/api/v2/dang-ky/doi-goi`
đòi `tenant.membership.quan_ly`. Không phải lỗ hổng (cửa vẫn bị chặn đúng, chỉ chặt hơn ý định),
nhưng là **guard chết**: đọc mã tưởng có một núm "quản lý gói" riêng, thật ra không có.
**Bằng chứng:** `R6` đo 29 chuỗi quyền được hỏi → 28 có trong bảng → **đúng 1** ngoại lệ là
`tenant.billing.quan_ly`; ngoại lệ này được **khai tường minh** trong bộ thử nên một quyền mới
xuất hiện ngoài danh sách sẽ làm **ĐỎ**.
*Đề xuất (không thuộc quyền tôi):* hoặc thêm `tenant.billing.quan_ly` vào `quyen.QUYEN` + ma trận,
hoặc bỏ nhánh ba ngôi và ghi thẳng `tenant.membership.quan_ly`.

### `F-02` · **INFO** · Cửa webhook **vô danh** ghi audit mang `tenant_id` của **chủ tài khoản**
Ba lượt `POST /api/v2/webhook/nhan/{wh_ma}` với **chữ ký sai** (không cần phiên, không cần biết
secret) làm `audit` của **tenant A** tăng **đúng 3 dòng** `webhook_chu_ky_tu_choi` — trong khi
`wh_su_kien` **không** tăng dòng nào (dữ liệu nghiệp vụ sạch). **Đo được:** 3 lượt ⇒ +3 dòng,
`wh_su_kien` +0. Đây là **ghi log gán nhãn tenant**, không phải ghi dữ liệu nghiệp vụ; nhưng nó
cho người ngoài một đường **bơm rác vào nhật ký của tenant** (bị chặn bởi trần
`webhook.chu_ky_sai`: 10 lượt/phút mỗi `webhook_ma`, 30/phút mỗi IP, phạt 300 giây).
**Không** sửa ở lượt này (ngoài phạm vi ghi) — nêu ra để Owner quyết.

### `F-03` · **LOW** · Ba cửa tài chính/đối soát trả **409** thay vì **404** khi id thuộc tenant khác
Đo trên chính CSDL thật: đợt thanh toán của A ⇒ B nhận **409** (`chốt`, `từ chối đợt`);
chênh lệch của A ⇒ B nhận **409** (`xử lý chênh lệch`). Cả ba câu ghi đều có
`UPDATE … WHERE id=? AND tenant_id=?` nên **B KHÔNG sửa được gì** (ảnh chụp CSDL: 0 hàng của A bị
đụng) — nhưng mã trả lời **gộp** "không phải của bạn / không tồn tại" với "đã chốt / đã xử lý rồi",
đúng cái mà `server.py` đã **cố ý tách** ở cửa `replay` (`404` cho "không có / của tenant khác",
`409` cho "vượt trần"). Ở đây **không có** oracle tồn tại (id của A và id không tồn tại đều 409),
nên đây là lỗi **tính nhất quán của mã trả lời**, không phải rò dữ liệu. `chan_B=(409,)` được khai
kèm chú thích `PHÁT HIỆN F-03` ngay trong bảng cửa.

### `F-04` · **INFO** · Hai cửa **đọc** trả `200` + **rỗng** cho id thuộc tenant khác
`GET /api/v2/don/{id}/mat-hang` và `GET /api/v2/doi-soat/dot/{id}/chenh-lech`: B nhận **200** với
danh sách **rỗng**. Đo bằng cờ `rong_B` (bộ thử khẳng định **rỗng**, không chỉ "không thấy dấu vết
A") ⇒ **không rò dữ liệu**; chỉ lệch quy ước 404 của các cửa cùng họ. Id của A và id không tồn tại
cho cùng kết quả ⇒ không có oracle.

### `F-05` · **MÔI TRƯỜNG (không phải mã dự án)** · `git` hỏng trong runtime này
Hai bộ thử **khác** (`app/thu/thu_bao_mat.py` ca `f3`, `app/thu/thu_tich_hop.py` ca `04`/`11`) đỏ
trong lượt hồi quy **không phải vì mã dự án**, mà vì tiến trình `git` trong runtime này chết:

```sh
$ git check-ignore -q app/du-lieu/khoa-noi-bo.key ; echo $?
error: missing config key GIT_CONFIG_KEY_0
fatal: unable to parse command-line config
128
$ env -u GIT_CONFIG_COUNT -u GIT_CONFIG_VALUE_0 -u GIT_CONFIG_VALUE_1 \
      git check-ignore -q app/du-lieu/khoa-noi-bo.key ; echo $?
0
```

Biến `GIT_CONFIG_COUNT=3` có mặt nhưng **thiếu** `GIT_CONFIG_KEY_*`. Gỡ ba biến đó rồi chạy lại:
`thu_bao_mat.py` → **`Ran 57 tests … OK`**; `thu_tich_hop.py` → **`Ran 12 tests … OK`**.
Bộ thử của tôi **không** gọi `git` nên **không** bị ảnh hưởng.

---

## 7. BỐN LẦN CHÍNH BỘ ĐO CỦA TÔI SAI (ghi lại, không giấu)

1. **`/api/v2/san-sang` trả 503 cho lượt B — HỎNG GIẢ do chính tôi.** Tôi gọi `webhook.dung()`
   trước khi chụp CSDL để "đóng băng" dữ liệu; mà cửa `san-sang` **kiểm "worker webhook sống"** ⇒
   tôi tự tay làm nó 503. Sửa: chờ `webhook.cho_rong(10)` rồi **giữ worker sống**. Nếu tôi kết
   luận sớm, báo cáo đã có một "phát hiện" về lỗi không tồn tại.
2. **Đột biến `E4` bản đầu sai nghĩa** — xoá chuỗi lọc tenant làm câu SQL **thừa tham số** ⇒ 500
   cho cả hai tenant. Bộ thử đỏ vì "chưa đo được", **không** phải vì bắt được rò rỉ. Đã sửa thành
   đột biến **giữ đúng số tham số** (xem §5).
3. **"Rò rỉ" trong `GET /api/v2/audit` của B — thật ra là dấu vết A do CHÍNH B gửi vào body.**
   Vài cửa ghi audit theo chi tiết yêu cầu, nên khi payload của B còn chứa `SI`, nhật ký **của B**
   có `SI` — không phải rò rỉ. Sửa: mọi body gửi bởi B đi qua `_doi_si()` (đổi hết dấu vết A thành
   dấu vết B). Bài học §7.1: *một kết luận "rò" chỉ từ một đường là SAI* — phải phân biệt "dữ liệu
   của A" với "chuỗi mà B tự gửi".
4. **Canh "quyền chết" (`R6`) kêu nhầm** vì bộ trích AST chỉ lấy **đối số trực tiếp** của `_can`,
   bỏ sót quyền nằm trong **biểu thức ba ngôi**. Đã sửa: đi cả vào trong biểu thức. Và **hai lần
   trước đó** nữa: bản đầu của tôi còn **unpack sai** `Tra` (thêm `__iter__`), và bản đầu của phép
   canh route **không quy đổi** tên tham số fixture (`{kh_a}`) về dạng của `server.py` (`{id}`).

---

## 8. HỒI QUY TOÀN DỰ ÁN (hai lượt chạy cuối, cùng bản chốt)

```sh
$ sh app/thu/chay_tat_ca.sh
  ✓ thu_g17_baomat.py          31 ca
  ✗ thu_bao_mat.py             57 ca  HỎNG (mã thoát 1)     ← F-05, môi trường git
  ✗ thu_tich_hop.py            12 ca  HỎNG (mã thoát 1)     ← F-05, môi trường git
  python:   1315 ca · 37 bộ chạy thật
  frontend: 56 + 36 ca
  E2E:      KẾT QUẢ: 41/41 phép đo đạt
```

`chay_tat_ca.sh` trả **exit 1** vì **hai bộ kia** — đã chứng minh ở `F-05` là do **môi trường
runtime** (biến `GIT_CONFIG_*` hỏng), không do mã dự án và không do lượt này: gỡ ba biến đó thì
`thu_bao_mat.py` **OK 57 ca**, `thu_tich_hop.py` **OK 12 ca**. Bộ thử của lượt này **xanh** trong
**cả hai** lượt hồi quy đầy đủ.

**Một bộ chập chờn sẵn có, ghi ra cho đủ** (`thu_nhat_ky_yeu_cau.py`): lượt hồi quy **đầu** trong
hai lượt có thêm bộ này đỏ ở ca `test_a2_moi_dong_yeu_cau_du_truong_va_co_request_id`; lượt **sau**
thì nó **xanh 8 ca**. Chạy **riêng ba lượt liên tiếp**: `Ran 8 tests … OK` cả ba (0,92 / 0,86 /
0,86 giây). Bộ này mở **máy chủ riêng trong tiến trình con** rồi **đọc tệp log của tiến trình đó**
— đúng dạng đua đọc-ghi — và nó **không** dùng chung tài nguyên nào với bộ của lượt này (thư mục dữ
liệu tạm riêng, cổng do chính nó tự chọn bằng `socket.bind(…, 0)`). Vì vậy tôi **không** kết luận
gì thêm về nó: đây là quan sát của lượt đo này, **không** phải phát hiện về mã sản phẩm, và **cũng
không** phải do lượt này gây ra. Việc của AG-01/Owner nếu muốn truy.

---

## 9. **CHƯA ĐO** — và cái gì NẰM NGOÀI phạm vi

Nói thẳng, theo §12.1 luật 3 (kết luận chỉ được nói trong đúng phạm vi đã đo):

1. **Hãng thật / sandbox** — `V-G09-01` + `V-13906-05` **CHƯA CẤP**. Không một byte ra mạng; mọi
   adapter ở `MOCK`. Ba cửa có nhánh gọi hãng (`POST /don/{id}/gui`, `POST /polling/chay`,
   `POST /tai-khoan-hang/{id}/rotate`) chỉ được đo ở nhánh **MOCK**.
2. **Nhiều tiến trình**: trần tần suất sống trong bộ nhớ **một** tiến trình; `csdl.khoa_ghi` là
   `RLock` của Python. Lượt này chạy **một** tiến trình ⇒ **không** đo được tranh chấp liên tiến
   trình (bộ riêng `app/thu/dong_thoi/chay.py`).
3. **PostgreSQL** — D-8: CSDL nghiệp vụ **vẫn SQLite**. Mọi kết luận ở đây là **SQLite schema v8**.
4. **TLS/HTTPS thật, tunnel, VPS, triển khai, container** — không đo.
5. **Giao diện trình duyệt (tầng 3 Chromium)** — không chạy ở đây (bộ riêng
   `thu_giao_dien/chay.sh`). Cách ly tenant được đo ở **API**, không ở DOM.
6. **`CAP_DUOC`** (vai trò nào cấp được vai trò nào) là **hằng trong mã**, **không** nằm trong
   `role_permissions` ⇒ **NẰM NGOÀI** ma trận động V6. Đừng đọc kết quả §3 thành "RBAC đã động
   hoàn toàn".
7. **Mô hình đe doạ**: `PLATFORM_OWNER` được coi là **bên tin cậy**. Lượt này **không** đo
   "quản trị nền tảng độc ác đọc trộm tenant" (họ đọc được là đúng thiết kế: `platform.tenant.xem`).
8. **Ba cửa đo lỏng** ở §2.2 (doi-soat-tay · doi-goi · ai tu-choi): A bị **trạng thái nghiệp vụ**
   từ chối, nên phép đo **không** khẳng định A thực hiện thành công — chỉ khẳng định A **qua được**
   cửa quyền/tenant và B thì **404**. Dựng đủ trạng thái cho ba cửa này (kịch bản mock "kết quả
   không rõ", gói đích hợp lệ, việc AI đã chạy) là việc **chưa làm**.
9. **`F-01`/`F-02`/`F-03`/`F-04` chưa sửa** — thuộc quyền quyết của Owner/AG-00; lượt này **chỉ đo**
   (làn AG-06 chỉ được ghi 2 tệp).
10. **Chưa có người đọc lại**: toàn bộ lượt này do **tác tử AI** thực hiện.

---

## 10. PHỤ LỤC A — BẢNG ĐẦY ĐỦ 113 CỬA (A = chủ sở hữu · B = tenant khác)

`mức = chặt` nghĩa là mã trả **chính xác** theo kỳ vọng **và** lượt A phải thấy dấu vết A (với
cửa đọc). `mức = lỏng` là cửa ghi cần hồ sơ nghiệp vụ sâu: chỉ khẳng định **qua được cửa**
(mã ∉ {401,403,404,5xx}). Cột ghi chú giữ nguyên văn từ bảng cửa trong mã.

| # | cửa (method + đường) | A | B | mức | ghi chú |
|---|---|---|---|---|---|
| 1 | `GET /api/v2/suc-khoe` | 200 | 200 | chặt | — |
| 2 | `GET /api/v2/san-sang` | 200 | 200 | chặt | — |
| 3 | `POST /api/v2/auth/dang-xuat` | 200 | 200 | chặt | — |
| 4 | `GET /api/v2/auth/toi` | 200 | 200 | chặt | — |
| 5 | `POST /api/v2/auth/doi-tenant` | 200 | 403 | chặt | B đòi vào tenant A ⇒ phải 403 và phiên B KHÔNG đổi tenant |
| 6 | `POST /api/v2/auth/doi-mat-khau` | 400 | 400 | chặt | A: mật khẩu cũ SAI ⇒ 400 · B: cũng 400 cho CHÍNH tài khoản B (phiên B riêng, vì cửa đăng-xuất phía trước đã th |
| 7 | `POST /api/v2/auth/thu-hoi-phien` | 200 | 200 | chặt | — |
| 8 | `GET /api/v2/platform/tenants` | 200 | 403 | chặt | — |
| 9 | `POST /api/v2/platform/tenants` | 201 | 403 | chặt | tạo luôn tenant C để đo các cửa theo id |
| 10 | `GET /api/v2/platform/tenants/3` | 200 | 403 | chặt | — |
| 11 | `PUT /api/v2/platform/tenants/3` | 200 | 403 | chặt | — |
| 12 | `POST /api/v2/platform/tenants/3/khoa` | 200 | 403 | chặt | — |
| 13 | `POST /api/v2/platform/tenants/3/mo` | 200 | 403 | chặt | — |
| 14 | `POST /api/v2/platform/tenants/3/goi` | 200 | 403 | chặt | — |
| 15 | `GET /api/v2/platform/goi` | 200 | 403 | chặt | — |
| 16 | `GET /api/v2/platform/vai-tro` | 200 | 403 | chặt | ma trận RBAC: tenant B KHÔNG được đọc (QA q03) |
| 17 | `GET /api/v2/platform/quan-sat/metric` | 200 | 403 | chặt | — |
| 18 | `POST /api/v2/platform/g09/harness` | 200 | 403 | chặt | harness ép MOCK, không ra mạng |
| 19 | `GET /api/v2/platform/audit` | 200 | 403 | chặt | — |
| 20 | `GET /api/v2/tenant` | 200 | 200 | chặt | — |
| 21 | `PUT /api/v2/tenant` | 200 | 200 | lỏng | — |
| 22 | `GET /api/v2/memberships` | 200 | 200 | chặt | — |
| 23 | `POST /api/v2/memberships` | 201 | 201 | chặt | — |
| 24 | `PUT /api/v2/memberships/6` | 200 | 404 | lỏng | — |
| 25 | `DELETE /api/v2/memberships/7` | 200 | 404 | chặt | — |
| 26 | `GET /api/v2/khach-hang` | 200 | 200 | chặt | — |
| 27 | `POST /api/v2/khach-hang` | 201 | 201 | chặt | — |
| 28 | `GET /api/v2/khach-hang/1` | 200 | 404 | chặt | — |
| 29 | `GET /api/v2/hang` | 200 | 200 | chặt | — |
| 30 | `GET /api/v2/tai-khoan-hang` | 200 | 200 | chặt | và KHÔNG được trả secret (đo riêng ở V_KhongLoBiMat) |
| 31 | `POST /api/v2/tai-khoan-hang` | 201 | 201 | chặt | — |
| 32 | `POST /api/v2/tai-khoan-hang/3/rotate` | 200 | 404 | chặt | — |
| 33 | `POST /api/v2/tai-khoan-hang/3/khoa` | 200 | 404 | chặt | — |
| 34 | `POST /api/v2/tai-khoan-hang/3/mo` | 200 | 404 | chặt | — |
| 35 | `POST /api/v2/tai-khoan-hang/3/revoke` | 200 | 404 | chặt | — |
| 36 | `POST /api/v2/don/tim` | 200 | 200 | chặt | — |
| 37 | `POST /api/v2/don/kiem` | 200 | 200 | chặt | — |
| 38 | `GET /api/v2/don/can-doi-soat` | 200 | 200 | chặt | — |
| 39 | `GET /api/v2/don` | 200 | 200 | chặt | — |
| 40 | `GET /api/v2/don/xuat-csv` | 200 | 200 | chặt | — |
| 41 | `POST /api/v2/don` | 201 | 201 | chặt | — |
| 42 | `GET /api/v2/don/1` | 200 | 404 | chặt | — |
| 43 | `PUT /api/v2/don/2` | 200 | 404 | lỏng | — |
| 44 | `DELETE /api/v2/don/10` | 200 | 404 | chặt | — |
| 45 | `GET /api/v2/don/1/hanh-trinh` | 200 | 404 | chặt | — |
| 46 | `GET /api/v2/don/11/nhan` | 200 | 404 | chặt | — |
| 47 | `GET /api/v2/don/1/day-du` | 200 | 404 | chặt | — |
| 48 | `GET /api/v2/don/1/kiem` | 200 | 404 | chặt | — |
| 49 | `GET /api/v2/don/1/mat-hang` | 200 | 200 | chặt | B nhận 200 với danh sách RỖNG (cửa không 404) — không rò dữ liệu |
| 50 | `PUT /api/v2/don/3/mat-hang` | 200 | 404 | lỏng | — |
| 51 | `POST /api/v2/don/4/tu-choi` | 200 | 404 | lỏng | — |
| 52 | `POST /api/v2/don/5/doi-soat` | 200 | 404 | lỏng | — |
| 53 | `POST /api/v2/don/6/doi-soat-tay` | 409 | 404 | lỏng | — |
| 54 | `POST /api/v2/don/7/duyet` | 200 | 404 | lỏng | — |
| 55 | `POST /api/v2/don/8/gui` | 200 | 404 | lỏng | adapter MOCK trong tiến trình, KHÔNG ra mạng |
| 56 | `POST /api/v2/don/9/huy` | 200 | 404 | lỏng | — |
| 57 | `GET /api/v2/import` | 200 | 200 | chặt | — |
| 58 | `POST /api/v2/import` | 201 | 201 | chặt | — |
| 59 | `GET /api/v2/import/1` | 200 | 404 | chặt | — |
| 60 | `PUT /api/v2/import/dong/5` | 200 | 404 | lỏng | — |
| 61 | `GET /api/v2/import/1/xuat-csv` | 200 | 404 | chặt | — |
| 62 | `POST /api/v2/import/dong/7/xac-nhan` | 200 | 404 | chặt | — |
| 63 | `POST /api/v2/import/2/duyet` | 200 | 404 | chặt | — |
| 64 | `GET /api/v2/webhook/su-kien` | 200 | 200 | chặt | — |
| 65 | `POST /api/v2/webhook/su-kien/1/replay` | 202 | 404 | chặt | — |
| 66 | `POST /api/v2/polling/chay` | 200 | 200 | lỏng | quét hãng ở chế độ MOCK |
| 67 | `GET /api/v2/goi` | 200 | 200 | chặt | — |
| 68 | `GET /api/v2/dang-ky` | 200 | 200 | chặt | — |
| 69 | `POST /api/v2/dang-ky/doi-goi` | 409 | 409 | lỏng | đổi gói tác động lên CHÍNH tenant người gọi — cách ly đo bằng ảnh chụp CSDL |
| 70 | `GET /api/v2/usage` | 200 | 200 | chặt | — |
| 71 | `GET /api/v2/usage/bao-cao` | 200 | 200 | chặt | — |
| 72 | `GET /api/v2/usage/su-kien` | 200 | 200 | chặt | — |
| 73 | `GET /api/v2/usage/doi-soat` | 200 | 200 | chặt | — |
| 74 | `GET /api/v2/usage/tinh-phi` | 200 | 200 | chặt | — |
| 75 | `GET /api/v2/billing/du-thao` | 200 | 200 | chặt | — |
| 76 | `POST /api/v2/usage/dong-ky` | 200 | 200 | lỏng | — |
| 77 | `GET /api/v2/g09/suc-khoe-hang` | 200 | 200 | chặt | — |
| 78 | `GET /api/v2/g09/can-soat` | 200 | 200 | chặt | — |
| 79 | `POST /api/v2/ai/job` | 201 | 201 | chặt | — |
| 80 | `GET /api/v2/ai/job` | 200 | 200 | chặt | — |
| 81 | `GET /api/v2/ai/su-kien` | 200 | 200 | chặt | — |
| 82 | `GET /api/v2/ai/thong-ke` | 200 | 200 | chặt | — |
| 83 | `GET /api/v2/ai/lo/1` | 200 | 404 | chặt | — |
| 84 | `GET /api/v2/ai/job/1` | 200 | 404 | chặt | — |
| 85 | `POST /api/v2/ai/job/2/chay` | 200 | 404 | lỏng | AI gateway ở chế độ MOCK nội bộ |
| 86 | `POST /api/v2/ai/job/2/duyet` | 200 | 404 | lỏng | — |
| 87 | `POST /api/v2/ai/job/3/tu-choi` | 400 | 404 | lỏng | — |
| 88 | `POST /api/v2/ai/job/2/de-xuat` | 200 | 404 | lỏng | — |
| 89 | `POST /api/v2/ai/chuan-hoa-dia-chi` | 200 | 200 | chặt | — |
| 90 | `POST /api/v2/ai/phat-hien-bat-thuong` | 200 | 200 | chặt | — |
| 91 | `POST /api/v2/ai/goi-y-hang` | 200 | 200 | chặt | — |
| 92 | `GET /api/v2/tai-chinh/cod` | 200 | 200 | chặt | — |
| 93 | `GET /api/v2/tai-chinh/tong-so` | 200 | 200 | chặt | — |
| 94 | `GET /api/v2/tai-chinh/cong-no` | 200 | 200 | chặt | — |
| 95 | `GET /api/v2/tai-chinh/dieu-chinh` | 200 | 200 | chặt | — |
| 96 | `POST /api/v2/tai-chinh/dieu-chinh` | 201 | 201 | chặt | — |
| 97 | `GET /api/v2/tai-chinh/kiem-nhat-ky` | 200 | 200 | chặt | — |
| 98 | `POST /api/v2/tai-chinh/tinh-lai-cong-no` | 200 | 200 | lỏng | việc trên TOÀN tenant người gọi |
| 99 | `POST /api/v2/tai-chinh/dot-thanh-toan` | 201 | 201 | chặt | — |
| 100 | `POST /api/v2/tai-chinh/dot-thanh-toan/2/ghi-nhan` | 200 | 404 | lỏng | — |
| 101 | `POST /api/v2/tai-chinh/dot-thanh-toan/3/chot` | 200 | 409 | lỏng | PHÁT HIỆN F-03: đợt của A ⇒ B nhận 409 (như đợt ĐÃ CHỐT), không phải 404; câu UPDATE vẫn lọc tenant_id nên KHÔ |
| 102 | `GET /api/v2/tai-chinh/cod/1` | 200 | 200 | chặt | trả cấu trúc rỗng cho đơn không thuộc mình — đo bằng dấu vết |
| 103 | `POST /api/v2/doi-soat/nap` | 201 | 201 | chặt | — |
| 104 | `GET /api/v2/doi-soat/dot` | 200 | 200 | chặt | — |
| 105 | `POST /api/v2/doi-soat/dot/5/doi-chieu` | 200 | 404 | chặt | đợt RIÊNG chưa đối chiếu (các đợt khác đã đối chiếu sẵn để đo duyet/tu-choi) |
| 106 | `POST /api/v2/doi-soat/dot/3/duyet` | 200 | 404 | lỏng | — |
| 107 | `POST /api/v2/doi-soat/dot/4/tu-choi` | 200 | 409 | lỏng | PHÁT HIỆN F-03: đợt của A ⇒ B nhận 409, không phải 404; UPDATE vẫn lọc tenant |
| 108 | `GET /api/v2/doi-soat/dot/1/bang-ke` | 200 | 404 | chặt | — |
| 109 | `GET /api/v2/doi-soat/dot/1/chenh-lech` | 200 | 200 | chặt | cửa không 404 với đợt của tenant khác — trả RỖNG (đo bằng rong_B), không rò dữ liệu |
| 110 | `GET /api/v2/doi-soat/dot/1/xuat-csv` | 200 | 200 | chặt | CSV của đợt A: B phải 404 hoặc CSV rỗng, không có dấu vết A |
| 111 | `POST /api/v2/doi-soat/chenh-lech/1/xu-ly` | 200 | 409 | chặt | PHÁT HIỆN F-03: chênh lệch của A ⇒ B nhận 409 (như đã xử), không phải 404 |
| 112 | `GET /api/v2/billing` | 200 | 200 | chặt | — |
| 113 | `GET /api/v2/audit` | 200 | 200 | chặt | — |

---

## 11. PHỤ LỤC B — chạy lại và vân tay

```sh
# bộ thử của lượt này (tự dựng CSDL tạm + máy chủ cổng 0; KHÔNG cần cài gì thêm)
python3 app/thu/thu_g17_baomat.py

# hồi quy toàn dự án
sh app/thu/chay_tat_ca.sh
```

* Nhánh: `g17-ag06-security` · `HEAD = 98baeb357214d41a9380467fde2fee2b94fd31cc`
  (nền `integration/g16` @ `98baeb3`; `main = de740dc` **không** chứa G13–G16 — đã theo đúng nền).
* `git status --short`: **đúng hai tệp mới** —
  `app/thu/thu_g17_baomat.py` · `docs/G17_SECURITY_ISOLATION.md`. Không tệp sản phẩm nào bị sửa.
* Mọi số đo trong tài liệu này lấy từ **lệnh chạy thật** ở §1/§8 và ô phạm vi in ra ở cuối mỗi
  lượt chạy bộ thử. Không có số nào được chép từ báo cáo của làn khác.
