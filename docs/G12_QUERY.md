# G12 — LỌC VÀ PHÂN TRANG Ở MÁY CHỦ

Tác tử: **AG-01 BACKEND QUERY ENGINEER** · Nhánh `agent/g12-query` · Nền `714fd76`
Ngày: 15/10/2026 · Worktree `~/code/veh4-g12-query`

File sở hữu: `app/truy_van.py` · `app/thu/thu_truy_van.py` · `docs/G12_QUERY.md`
**Không** chạm `app/server.py`, `app/don_hang.py`, `app/csdl.py`, `app/migrate.py`, `admin/*`.

---

## 1. Vấn đề đã đo, không phải giả thiết

`GET /api/v2/don` (`app/server.py` dòng 824–834) nhận đúng ba tham số: `q` · `trang_thai` ·
`gioi_han`. Nó dùng `LIMIT ?` cứng, **không `OFFSET`**, **không trả `tong`**.

`admin/logic.js` mục `API_CHO_BACKEND` (mục "Tìm đơn nâng cao ở máy chủ", `mot_phan: true`)
khai thẳng ra điều đó: *"Máy chủ hiện chỉ nhận q · trang_thai · gioi_han. Các điều kiện còn
lại đang lọc TẠI GIAO DIỆN trên tập đã tải."*

Hệ quả thật: người dùng tải 100 dòng đầu, lọc trong 100 dòng đó, và **tin rằng mình đã lọc
cả kho**. Không có thông báo lỗi, không có gì bất thường trên màn hình — chỉ là ít kết quả
hơn sự thật. Giao diện có ghi cảnh báo, nhưng đó là **vá bằng lời**; §12.2 nói lời dặn không
chặn được máy. G12 vá bằng **cấu trúc**: đưa phép lọc về chỗ nó có đủ dữ liệu để đúng.

**Phát hiện khi khảo sát:** AG-02 đã làm sẵn `don_hang.tim_don` (`POST /api/v2/don/tim`) phủ
phần lớn việc này. Nên G12 **không viết lại từ đầu**. `app/truy_van.py` là bản tổng quát hoá,
thêm bốn thứ `tim_don` chưa có:

| Thiếu ở `tim_don` | `truy_van.py` làm gì |
|---|---|
| Không lọc được theo `hang` (mã hãng) | `hang` KHÔNG phải cột của `don_hang` — đi qua câu con `carrier_accounts` có kẹp tenant |
| Tham số lạ bị **bỏ qua im lặng** | Trả **400** kèm danh sách tên hợp lệ |
| `COUNT(*)` không có trần | Đếm trong câu con `LIMIT TRAN+1`, tự khai khi chạm trần |
| `cap_nhat_*` sắp xếp không có khoá phá hoà | Mọi biểu thức sắp xếp kết thúc bằng cột duy nhất |
| Chỉ dùng được cho `don_hang` | Khai `BangTruyVan` là dùng được cho bảng khác (có ca thử trên `ai_job`) |

---

## 2. Hình dạng

`BangTruyVan` = bộ quy chuẩn truy vấn của một bảng: tên bảng · cột tenant · danh sách
`TruongLoc` · danh sách trắng sắp xếp. `chay(spec, tenant_id, loc)` dựng SQL và chạy.

```python
import truy_van
kq = truy_van.tim_don(tenant_id, {"hang": "vtp", "cod_tu": 100000,
                                  "tu_ngay": "2026-10-01", "trang": 2, "gioi_han": 50})
```

Trả về:

| Trường | Nghĩa |
|---|---|
| `dong` | bản ghi của **trang này** |
| `tong` | tổng dòng **khớp điều kiện** (không phải số dòng trang này) |
| `tong_chinh_xac` | `False` = đã chạm `TRAN_DEM`, `tong` khi đó **bằng đúng** trần |
| `tong_it_nhat` | khi chạm trần: số tối thiểu biết chắc, để giao diện hiện `10 000+` |
| `gioi_han` · `lech` · `trang` | giá trị **THẬT đã dùng** sau khi kẹp — bên gọi đối chiếu được |
| `con_nua` | còn trang sau hay không |
| `sap_xep` | khoá sắp xếp đã dùng |
| `loc_bo_qua` | điều kiện đã **bỏ** vì CSDL chưa có cột (tên đúng, cột chưa migrate) |

### Điều kiện phủ (lấy từ `admin/logic.js`, không tự nghĩ)

`tu_ngay` · `den_ngay` · `trang_thai` · `trang_thai_giao` · `hang` · `carrier_account_id` ·
`khach_hang_id` · `ma_don` · `ma_van_don` · `external_reference` · `cod_tu` · `cod_den` ·
`can_doi_soat` · `q` — cộng bốn tham số điều khiển `sap_xep` · `gioi_han` · `lech`/`trang` ·
`dem_chinh_xac`.

`trang_thai` và `trang_thai_giao` nhận cả **danh sách** → `IN (…)`.

---

## 3. Sáu quyết định, kèm lý do

### 3.1 Điều kiện lạ → **400**, không bỏ qua im lặng

Chọn 400. Lý do: bỏ qua im lặng nghĩa là người gõ `trang_thai_gia0` nhận về danh sách
**KHÔNG LỌC** và tin đó là kết quả đã lọc. Không có gì báo — chỉ là nhiều dòng hơn mong đợi,
và người ta sẽ cho rằng dữ liệu đúng là như thế. **Đó đúng là cái hỏng mà cả G12 sinh ra để
diệt**, nên không được tái tạo nó ở chính tầng đi vá nó.

Cân hai bên: 400 làm hỏng **ngay** một lượt gọi sai, người gọi sửa trong một phút. Bỏ qua im
lặng làm sai **lâu dài** mọi lượt gọi sau đó mà không ai biết.

Thông báo lỗi liệt kê đủ tên hợp lệ, nên lỗi tự nó là tài liệu.

`loc_bo_qua` là chuyện **khác**: tên tham số đúng nhưng CSDL chưa có cột (chưa migrate). Bên
gọi không sai nên không phạt bên gọi — nhưng vẫn **nói ra**, không im.

### 3.2 Trần đếm `tong` = 10 000, có cửa thoát

`COUNT(*)` không trần là **một lượt quét toàn bảng cho mỗi lần bấm lọc**. Bảng triệu dòng thì
mỗi lần gõ vào ô tìm kiếm là một lượt quét triệu dòng, và nó không báo chậm — nó chỉ chậm.

Cách làm: `SELECT COUNT(*) FROM (SELECT 1 FROM … WHERE … LIMIT 10001)`. SQLite dừng đọc ngay
khi đủ 10 001 dòng khớp. Quá trần thì trả `tong = 10000`, `tong_chinh_xac = False`,
`tong_it_nhat = 10000`.

Dấu `+1` là ranh giới: thiếu nó thì tập **đúng** 10 000 dòng bị báo nhầm là "10 000+".
Ca `test_c08` canh đúng chỗ này.

Vì sao trần chứ không đếm xấp xỉ bằng thống kê bảng: **xấp xỉ sai một cách im lặng**, còn
trần nói thẳng ra là nó không biết (§12.1 luật 3).

Cửa thoát: `dem_chinh_xac=1` thì đếm đủ. Cố ý bắt phải xin — người xin biết mình đang xin gì.

### 3.3 Ngày: **cả hai đầu BAO GỒM**, so trên cột trần

`tao_luc` lưu `"YYYY-MM-DD HH:MM:SS+0700"` (giờ VN).

```
tu_ngay  = 2026-10-15  →  tao_luc >= "2026-10-15"
den_ngay = 2026-10-15  →  tao_luc <  "2026-10-16"
```

Đầu cuối dùng `<` **ngày kế tiếp**, không `<=` cùng ngày: `<= "2026-10-15"` sẽ loại **sạch**
mọi đơn trong ngày 15 (vì `"2026-10-15 08:00" > "2026-10-15"`) — lọc ra rỗng mà không báo gì.
`tu_ngay == den_ngay` = đúng một ngày. Ca `test_a04b` cắm đơn lúc 23:59:59 để canh đúng chỗ này.

Bản đầu viết `substr(tao_luc,1,10) >= ?`. **Đổi vì đo được**, không vì sở thích — xem §5.

Ngày không có thật (`2026-02-30`) bị chặn, không chỉ sai định dạng.

### 3.4 Tiền là `INTEGER` đồng (SHARED_CONTRACTS §16)

`cod_tu`/`cod_den` **từ chối** float, chuỗi có phần thập phân, và `bool`. Không cắt cụt:
`int(float("20000.7"))` ra 20000 — mất 7 hào mà không báo gì.

### 3.5 Kẹp phân trang **cả hai đầu**, kể cả `lech`

`gioi_han` kẹp `[1, 500]`. `lech` kẹp `[0, 200 000]`.

Trần `lech` là chỗ ít người nghĩ tới: `OFFSET 50000000` buộc SQLite **đọc và bỏ** đúng ngần ấy
dòng trước khi trả dòng đầu tiên — một lượt gọi duy nhất làm kiệt máy, mà không trông như một
lượt tấn công.

Kẹp chứ không báo lỗi (bấm "trang sau" quá đà là chuyện thường), nhưng giá trị **thật đã dùng**
luôn nằm trong kết quả nên bên gọi biết mình bị kẹp — không im lặng.

`trang` đếm từ 1. Gửi **cả** `trang` và `lech` → 400: hai cách đánh số cùng lúc là hai kết quả
khác nhau, đoán hộ là đoán sai một nửa số lần.

### 3.6 `can_doi_soat`: `0` **không phải** rỗng

`1` = chỉ đơn cần đối soát · `0` = chỉ đơn **không** cần · chuỗi rỗng/`None` = không lọc.
Coi `0` là rỗng thì người bấm "không cần đối soát" nhận về **cả hai loại**.

---

## 4. An toàn

- **Tham số hoá hoàn toàn.** Thứ duy nhất ghép vào câu SQL là **tên cột** và **chiều sắp xếp**,
  và cả hai chỉ đến từ danh sách trắng khai sẵn trong mã nguồn — không bao giờ từ dữ liệu gửi lên.
  Đây là **ngoại lệ chính đáng** của §12.2: quên một cột trong danh sách trắng = một kiểu sắp
  xếp bị chặn, thấy ngay; quên một tên trong danh sách đen = SQL injection, **không báo gì**.
- **Danh sách trắng tự nó cũng bị soát** (§12.1: thứ dùng để kiểm chứng phải được kiểm trước
  khi tin). `TruongLoc` và `BangTruyVan` chạy phép kiểm hình dạng tên cột **ngay lúc khai**,
  nên một dòng gõ nhầm hỏng ở lượt nạp module, tức là hỏng ở bộ thử — không hỏng ở máy khách.
- **`tenant_id` LUÔN là mệnh đề đầu tiên.** Không nhánh nào bỏ qua được: nó nằm ở dòng khởi
  tạo danh sách điều kiện. Bảng không khai `cot_tenant` bị **từ chối lúc khai**, không đợi
  lúc chạy. `tenant_id=None` → lỗi 500.
- **Câu con `hang` mang tenant của chính nó.** Thiếu dòng đó thì `hang=vtp` khớp tài khoản của
  tenant **khác** — rò rỉ đường vòng, và vì nó chỉ đổi tập id đem đi lọc nên nhìn kết quả
  không thấy gì bất thường. Ca `test_a09` canh.
- **`thu_qa2_soat::r40` vẫn đạt, nhưng nó KHÔNG phủ file này — đừng lấy nó làm bằng chứng.**
  r40 là soát **tĩnh**: nó tìm **tên bảng viết thành chữ** trong chuỗi SQL. Mọi câu của
  `truy_van.py` dựng tên bảng động (`FROM {spec.bang}`), nên r40 **không nhìn thấy** câu nào
  của file này. Chính ca thử r40 đã ghi sẵn giới hạn đó: *"chỉ thấy SQL viết thành chuỗi
  trong mã, không thấy SQL ghép động ở thời gian chạy."*
  Nói "r40 đạt nên tenant an toàn" ở đây là đúng dạng §12.1 luật 3 — kết luận vượt phạm vi
  công cụ. Bằng chứng tenant của file này là **`test_b01`** (soát mệnh đề đầu của mọi tổ hợp
  điều kiện), **`test_b03`** (lọc rộng nhất, đủ 8 kiểu sắp xếp) và **`test_a09`** (câu con
  `hang`) — cộng với đột biến 1 và 2 ở §6 chứng minh ba ca đó thật sự bắt được.
  Điều r40 nói được: **G12 không làm hỏng** phép soát sẵn có.

---

## 5. Chỉ mục — hằng `DDL_G12Q`

Khai trong `app/truy_van.py`. **AG-00 là người cắm vào migration v9** (SHARED_CONTRACTS §22).
Chỉ `CREATE INDEX IF NOT EXISTS` — không `DROP`, không `ALTER`. Ca `test_e01` canh điều đó
bằng cách soát chính chuỗi DDL.

Chín chỉ mục, **mọi chỉ mục trên `don_hang` đều mở đầu bằng `tenant_id`** (ca `test_e03`
canh) vì mọi câu của lớp này đều bắt đầu bằng `tenant_id=?`:

```sql
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_tao      ON don_hang(tenant_id, tao_luc);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_id_desc  ON don_hang(tenant_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_ttgiao   ON don_hang(tenant_id, trang_thai_giao, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_cod      ON don_hang(tenant_id, cod, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_tk_hang  ON don_hang(tenant_id, carrier_account_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_doisoat  ON don_hang(tenant_id, can_doi_soat_ket_qua, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_khach    ON don_hang(tenant_id, khach_hang_id, id DESC);
CREATE INDEX IF NOT EXISTS ix_g12q_don_tenant_madon    ON don_hang(tenant_id, ma_don);
CREATE INDEX IF NOT EXISTS ix_g12q_tkhang_tenant_hang  ON carrier_accounts(tenant_id, hang);
```

**CỐ Ý không có chỉ mục cho `q`.** `LIKE '%…%'` mở đầu bằng `%` thì **không chỉ mục B-tree nào
dùng được** — thêm vào chỉ tốn đĩa và tốn thời gian ghi. Muốn tìm chữ nhanh thì phải là FTS5,
đó là việc khác và chưa được cấp quyền. Ghi ra để không ai tưởng là bỏ sót.

### 5.1 Số đo thật — 20 000 đơn

Lệnh: `python3 app/thu/thu_truy_van.py --hieu-nang`
CSDL tạm 5,9 MB, schema thật v8, 20 000 đơn (75 % tenant A / 25 % tenant B), `ANALYZE` chạy
trước mỗi lượt đo. Mỗi con số là **trung bình 20 lượt** trên **một** máy: MacBook Pro M5,
15/10/2026. Không đo trên Mac mini, không đo trên VPS.

| Câu | Trước | Sau | Kế hoạch SAU |
|---|---:|---:|---|
| Lọc khoảng ngày 5 tháng, trang 1 | 3,605 ms | **0,573 ms** | `ix_g12q_don_tenant_tao` |
| Lọc **một ngày** (dải hẹp) | 1,751 ms | **0,178 ms** | `ix_g12q_don_tenant_tao` |
| Lọc một ngày, **dạng cũ `substr()`** | 2,033 ms | 0,928 ms | `ix_g12q_don_tenant_id_desc` |
| Lọc ngày + trạng thái giao | 2,567 ms | **1,909 ms** | `ix_g12q_don_tenant_tao` |
| Khoảng COD, sắp xếp theo COD | 1,774 ms | **0,147 ms** | `ix_g12q_don_tenant_cod` |
| Lọc theo hãng (câu con) | 4,097 ms | **0,088 ms** | `ix_g12q_tkhang_tenant_hang` (phủ) |
| Cần đối soát | 2,018 ms | **0,086 ms** | `ix_g12q_don_tenant_doisoat` |
| Đếm có trần | 1,177 ms | **0,149 ms** | `ix_g12q_don_tenant_cod` (phủ) |
| Phân trang sâu `OFFSET 10000` | 18,669 ms | **0,217 ms** | `ix_g12q_don_tenant_id_desc` |

Trước khi có `DDL_G12Q`, **mọi** câu đều rơi vào `ix_don_extref` cộng `USE TEMP B-TREE FOR
ORDER BY` — tức là SQLite lấy toàn bộ đơn của tenant rồi sắp xếp trong bộ nhớ tạm. Đó chính
là chỗ chi phí tăng tuyến tính theo số đơn của tenant.

**Phạm vi của bảng này (§12.1 luật 3):** số đo trên SQLite trong CSDL tạm, 20 000 đơn, một
máy, một ngày, không có tải đồng thời, không qua tầng HTTP. Nó **không** nói gì về hành vi ở
200 000 đơn, trên VPS, hay khi có nhiều phiên ghi cùng lúc.

### 5.2 Một chỗ CHẬM ĐI — ghi ra, không giấu

Dòng thứ nhất và thứ ba của bảng trên nói hai điều ngược nhau, và điều đó là thật:

- **Dải hẹp (một ngày): dạng mới nhanh hơn 5,2 lần** (0,178 ms so với 0,928 ms).
- **Dải rộng (5 trên 10 tháng): dạng mới CHẬM HƠN** — 0,573 ms, trong khi dạng cũ `substr()`
  chỉ 0,091 ms.

Vì sao: dải rộng thì điều kiện ngày gần như không lọc được gì, nên đường nhanh nhất là đi
thẳng `ix_g12q_don_tenant_id_desc` (đã đúng thứ tự `ORDER BY id DESC`, lấy 50 dòng rồi dừng,
không cần sắp xếp tạm). Dạng `substr()` **buộc** SQLite phải chọn đường đó vì nó không dùng
được chỉ mục ngày. Dạng mới cho SQLite **quyền chọn**, và với thống kê hiện có nó chọn
`ix_g12q_don_tenant_tao` — đúng cho dải hẹp, không tối ưu cho dải rộng.

Vẫn giữ dạng mới. Lý do: cho bộ lập kế hoạch có quyền chọn thì chọn sai còn sửa được (bằng
`ANALYZE`, bằng thống kê tốt hơn, bằng gợi ý chỉ mục); bịt mất quyền chọn thì **không bao giờ**
sửa được, và nó sai đúng ở ca người dùng hay làm nhất — lọc một ngày, một tuần. Chênh lệch ở
ca xấu là 0,48 ms trên 20 000 đơn; chênh lệch ở ca tốt là 0,75 ms **và** nó tăng theo số đơn
chứ không đứng yên.

**Việc còn mở:** đo lại tỷ lệ này ở 200 000 đơn để biết điểm hoà vốn nằm ở đâu.

---

## 6. Nghiệm thu

### Bộ thử của G12

```
$ python3 app/thu/thu_truy_van.py
Ran 40 tests in 0.097s
OK
```

**40 ca, đạt hết.** Phạm vi: gọi thẳng `app/truy_van.py` trên CSDL tạm dựng bằng chính
`app/migrate.py` (schema thật v8, `don_hang` 40 cột). **Nằm ngoài phạm vi:** tầng HTTP (chưa
có route — xem §7), giao diện, hành vi khi nhiều phiên ghi cùng lúc, PostgreSQL.

Chia lớp: A điều kiện (17 ca) · B cách ly tenant (4) · C phân trang và đếm (9) · D an toàn (5)
· E DDL và dùng lại (5).

### Thứ dùng để kiểm chứng đã được kiểm trước khi tin (§12.1)

Một ca ĐẠT mà gỡ mã đi nó **vẫn** ĐẠT là ca vô dụng. Nên đã chạy lượt **gỡ bản vá**: sửa hỏng
từng chỗ trong `truy_van.py`, chạy lại bộ thử, xem ca nào bắt được.

**15/15 đột biến bị bắt**, mỗi cái bởi đúng ca định canh nó:

| # | Gỡ gì | Ca bắt được |
|---|---|---|
| 1 | Bỏ `tenant_id` khỏi `WHERE` | `test_b01`, `test_d02`, `test_d05` |
| 2 | Bỏ `tenant_id` khỏi câu con `hang` | `test_a09`, `test_a08`, `test_d02` |
| 3 | Bỏ danh sách trắng sắp xếp | `test_d01` |
| 4 | Tham số lạ bỏ qua im lặng | `test_d03`, `test_e05` |
| 5 | Bỏ khoá phá hoà khi sắp xếp COD | `test_c02b` |
| 6 | Bỏ trần `gioi_han` | `test_c05` |
| 7 | Bỏ trần `lech` | `test_c05` |
| 8 | Tiền thập phân bị cắt cụt thay vì chặn | `test_a07` |
| 9 | Đếm thiếu dấu `+1` ở ranh giới trần | `test_c08` |
| 10 | `loc_bo_qua` im lặng | `test_d05` |
| 11 | Ngày không kiểm định dạng | `test_a05` |
| 12 | `BangTruyVan` nhận `cot_tenant` rỗng | `test_b02` |
| 13 | `tenant_id=None` vẫn chạy | `test_b04` |
| 14 | Tên cột trong khai báo không soát | `test_d04` |
| 15 | Gửi cả `trang` và `lech` không báo | `test_c04` |

**Lượt gỡ bản vá đầu tiên LỌT 2/15** — và đó là phần đáng giá nhất của nghiệm thu này:

- **Đột biến 5 lọt.** Ca động `test_c02` cắm 8 đơn cùng COD rồi lật từng trang; gỡ khoá phá
  hoà ra thì SQLite **tình cờ** vẫn trả theo thứ tự rowid và ca vẫn ĐẠT. Phép đo tình cờ đúng
  không phải phép đo. Vá bằng ca soát **cấu trúc** `test_c02b`: mọi biểu thức sắp xếp phải kết
  thúc bằng cột **duy nhất**.
  Ca mới đó lập tức bắt một lỗi **có thật trong chính mã của G12**: `cap_nhat_moi` và
  `cap_nhat_cu` chỉ có `cap_nhat_luc DESC`, **không có khoá phá hoà** — mà một lượt cập nhật
  hàng loạt đóng dấu cùng một giây là chuyện rất thường, nên phân trang theo "cập nhật mới
  nhất" sẽ lặp dòng và sót dòng. Đã sửa.
- **Đột biến 12 lọt.** `test_b02` chỉ kiểm "có ném `ValueError`", mà phép kiểm hình dạng tên
  cột ở ngay dưới **cũng** ném `ValueError` — ca ĐẠT vì lý do khác với lý do nó định canh. Đã
  siết: kiểm cả **thông điệp** (`"THIẾU cot_tenant"`).

Script gỡ bản vá nằm ở scratchpad của phiên (không phải tài sản vault). Chạy lại được bằng
cách chép 15 cặp thay-chuỗi ở bảng trên.

### Không làm hỏng bộ thử của người khác

```
$ python3 app/thu/thu_qa2_soat.py 2>&1 | tail -3     # soát tĩnh, có ca r40 canh tenant_id
$ python3 app/thu/thu_don_hang.py 2>&1 | tail -3     # bộ thử G04 của AG-02
```
Kết quả ghi ở §8 báo cáo bàn giao.

---

## 7. Hai thứ CẦN AG-00 CẮM (mô tả, không sửa)

### 7.1 Bảng route

| Đường | Method | Quyền | Tham số vào | Ra | Mã lỗi |
|---|---|---|---|---|---|
| `/api/v2/don` | GET | `tenant.don.xem` | query string: `tu_ngay` `den_ngay` `trang_thai` `trang_thai_giao` `hang` `carrier_account_id` `khach_hang_id` `ma_don` `ma_van_don` `external_reference` `cod_tu` `cod_den` `can_doi_soat` `q` `sap_xep` `gioi_han` `lech`\|`trang` `dem_chinh_xac` | `{dong, tong, tong_chinh_xac, tong_it_nhat, gioi_han, lech, trang, con_nua, sap_xep, loc_bo_qua}` | 400 điều kiện lạ / sai kiểu · 401 chưa đăng nhập · 403 thiếu quyền |
| `/api/v2/don/loc-mo-ta` | GET | `tenant.don.xem` | — | `truy_van.mo_ta_bo_loc()` | 401 · 403 |

Đường thứ hai để giao diện dựng form lọc mà không chép tay danh sách trường — chép tay là hai
bản sẽ lệch nhau (§14.6 "một nguồn duy nhất").

**Lưu ý tương thích:** `GET /api/v2/don` hiện trả `{"don": [...]}`. Lớp mới trả `{"dong": ...}`.
Đề xuất **trả cả hai khoá** trong một đợt chuyển tiếp (`"don"` là bí danh của `"dong"`), rồi
gỡ `"don"` sau khi `admin/*` đã chuyển — đổi thẳng là làm trắng màn Đơn hàng ngay lượt đẩy.

Bản vá đề xuất cho `app/server.py` (thay nhánh dòng 824–834):

```python
if duong == "/api/v2/don" and method == "GET":
    self._can(nc, "tenant.don.xem")
    try:
        kq = truy_van.tim_don(tenant_id, dict(ts), co_cot=don_hang.co_cot)
    except truy_van.LoiTruyVan as e:
        return self._tra(e.ma, {"loi": str(e)})
    kq["don"] = kq["dong"]       # bí danh tạm cho giao diện cũ — gỡ sau khi admin/* chuyển
    return self._tra(200, kq)
```

`ts` là dict tham số query đã tách sẵn. **Không** ép kiểu trước khi đưa vào: lớp truy vấn tự
ép và tự từ chối, ép hai nơi là hai nơi có thể lệch nhau (§12.2 "lọc một chỗ, không lọc hai chỗ").

### 7.2 Bản vá đề xuất cho `don_hang.tim_don`

Hai module hiện làm việc chồng nhau. Đề xuất: **giữ `tim_don` làm cửa nghiệp vụ, rỗng ruột nó
đi và cho gọi xuống `truy_van`** — vì `tim_don` có một việc lớp truy vấn **không nên** làm, là
lọc `trang_thai_mo_rong` (giá trị suy ra ở tầng Python, không phải cột).

```python
# app/don_hang.py — thay thân hàm tim_don
def tim_don(tenant_id, loc=None):
    import truy_van
    loc = dict(loc or {})
    mo_rong = loc.pop("trang_thai_mo_rong", None)       # tách ra TRƯỚC, nếu không truy_van trả 400
    kq = truy_van.chay(truy_van.BANG_DON, tenant_id, loc, co_cot=co_cot)
    ra = kq["dong"]
    for x in ra:
        x["trang_thai_mo_rong"] = trang_thai_mo_rong(x)
    if mo_rong:
        can = MO_RONG_DONG_NGHIA.get(mo_rong, mo_rong)
        ra = [x for x in ra if x["trang_thai_mo_rong"] == can]
    return {**kq, "don": ra,
            "ghi_chu_tong": "`tong` đếm theo điều kiện SQL, CHƯA trừ phần lọc"
                            " trang_thai_mo_rong làm sau ở tầng Python" if mo_rong else ""}
```

Bốn điều phải kiểm khi cắm (đã lường, chưa đo vì không được ghi vào `don_hang.py`):

1. `don_hang.GIOI_HAN_TOI_DA` = 500 và `truy_van.GIOI_HAN_TOI_DA` = 500 — khớp. Nhưng mặc định
   khác nhau: `tim_don` mặc định **100**, `truy_van` mặc định **50**. `thu_don_hang.py` có ca
   dựa vào mặc định 100 hay không thì phải đo; an toàn nhất là `tim_don` truyền
   `gioi_han=loc.get("gioi_han") or 100` để giữ nguyên hành vi cũ.
2. `tim_don` hiện **bỏ qua im lặng** tham số lạ; `truy_van` trả 400. Ca `thu_don_hang::a04`
   gửi `external_reference` khi CSDL chưa migrate và mong `loc_bo_qua` — đường đó vẫn chạy
   (`co_cot` được truyền vào). Nhưng mọi nơi khác đang gửi tên lạ sẽ **bắt đầu hỏng**, và đó
   là điều mong muốn — chỉ cần biết trước.
3. `tim_don` trả `{"don": …}`; lớp mới trả `{"dong": …}`. Bản vá trên trả **cả hai**.
4. `tim_don` dùng `substr(tao_luc,1,10) <= den_ngay`; `truy_van` dùng `tao_luc < ngày+1`. **Hai
   cái cho cùng kết quả**, nhưng chỉ cái sau dùng được chỉ mục. Không có ca thử nào đổi nghĩa.

Nếu AG-00 **không** muốn gộp hai module, cũng chấp nhận được: `truy_van` đứng riêng cho route
`GET /api/v2/don` và cho các bảng sau (COD, đối soát, AI job), `tim_don` giữ cửa
`POST /api/v2/don/tim`. Cái giá là **hai danh sách trắng sắp xếp** phải giữ cho khớp tay —
và §14.6 đã nói hai bản nội dung là hai bản sẽ lệch nhau. Khuyến nghị: **gộp**.

---

## 8. Giới hạn còn lại — ghi ra để không ai tưởng là đã xong

1. **Chưa có route.** Lớp truy vấn chạy được và có bộ thử, nhưng **chưa ai gọi nó qua HTTP**.
   Giao diện vẫn đang lọc tại chỗ cho tới khi AG-00 cắm §7.1. Việc G12 làm là **dọn sẵn chỗ**,
   chưa phải là đã vá xong cho người dùng.
2. **`DDL_G12Q` chưa nằm trong migration.** Chỉ mục chỉ tồn tại trong CSDL tạm của bộ thử. Trên
   CSDL thật, các câu này vẫn chạy theo cột phải quét (xem số "trước" ở §5.1).
3. **`q` (tìm chữ) không có chỉ mục và sẽ không có** cho tới khi có FTS5. Với bảng lớn, `q` là
   điều kiện chậm nhất trong bộ lọc. Cố ý, lý do ở §5.
4. **Dải ngày rộng chậm hơn bản cũ** 0,48 ms trên 20 000 đơn — §5.2, đã cân và chấp nhận, kèm
   việc còn mở là đo lại ở 200 000 đơn.
5. **Chỉ đo trên SQLite.** Cú pháp `SELECT COUNT(*) FROM (… LIMIT ?)` và so chuỗi trên cột
   thời gian chạy đúng trên PostgreSQL về mặt ngữ nghĩa, nhưng **chưa đo**.
6. **Không có `GROUP BY`, không tổng hợp, không `JOIN` tuỳ ý.** Chỉ có `trong_bang_khac` dựng
   `IN (SELECT …)` theo khai báo sẵn. Màn thống kê phải tự lo.
7. **Chưa đo hành vi khi có phiên khác đang ghi.** Mọi phép đo chạy trên CSDL tĩnh.
8. **Chín chỉ mục là chín lần ghi thêm mỗi lượt `INSERT`.** Chưa đo chi phí ghi. Với luồng nhập
   file hàng nghìn đơn một lượt, đây là thứ nên đo trước khi cắm v9 — **việc còn mở**.
9. **`tong_chinh_xac=False` chưa có chỗ hiển thị.** Giao diện phải biết hiện `10 000+` thay vì
   `10 000`; chưa nói với ai vì `admin/*` không thuộc làn này.
