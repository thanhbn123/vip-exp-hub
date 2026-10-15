# BÁO CÁO TÍCH HỢP — WAVE 3 (G07 → G11)

Tài liệu này nói về **việc AG-00 làm**, không lặp lại nội dung 5 báo cáo agent. Số nghiệm thu
và bảng blocker nằm ở `docs/G07_G11_FINAL_REPORT.md`.

## 1. Vì sao gộp được 0 xung đột

Bảng quyền sở hữu file đóng băng ở WAVE 0 (`docs/SHARED_CONTRACTS.md` mục 22) chia **40 file
mới** cho 5 agent và giữ lại 8 file dùng chung cho AG-00. Kết quả đo được: **5/5 nhánh có 0
file cũ bị sửa, 0 vi phạm quyền sở hữu**.

Điều này không phải may. Hai đợt trước đã dạy: đợt 1 có một lượt AG-00 ghi file vào worktree
agent đang chạy (agent phát hiện và báo), đợt 2 có hai agent cùng cần sửa `server.py`. Cách
chặn là **cấm agent ghi vào `csdl.py` · `migrate.py` · `server.py`**, và thay vào đó:

- Cần schema mới → khai **hằng `DDL_G0x`** trong module của chính mình.
- Cần route mới → khai **bảng route** trong tài liệu của mình.
- Thấy lỗi ở file chỉ-đọc → **bản vá đề xuất** trong báo cáo, không sửa.

AG-03 đề xuất 9 bản vá, AG-05 đề xuất 4, AG-02 đề xuất 3, AG-04 đề xuất 3. AG-00 nhận 10, cố ý
từ chối 1 (bộ mã J&T thứ hai), còn lại chuyển thành việc mở.

## 2. Migration v8 — và vì sao KHÔNG chép DDL

v8 **nạp hằng từ module của agent** rồi `executescript` đúng chuỗi đó:

```python
import ai_job, goi_dich_vu, harness_hang, quan_sat, tai_chinh
for ten, ddl in (("G07", tai_chinh.DDL_G07), ("G08", goi_dich_vu.DDL_G08), ...):
    kn.executescript(ddl)
```

Chép DDL sang `migrate.py` là tạo **bản thứ hai**, và hai bản nội dung là hai bản sẽ lệch nhau
— lúc đó bộ thử của agent chạy một chuỗi còn CSDL thật mang một chuỗi khác, và **không ai thấy
cho tới khi có cột thiếu**.

Mỗi lượt nạp đo `sqlite_master` trước/sau để biết đã thêm đúng những gì, in ra trong dòng
`[migrate] Bước đã làm`.

**Nạp muộn, trong hàm** (không ở đầu file): năm module này không cần có mặt lúc `migrate` được
import, và một module hỏng không được làm chết cả đường migration.

### Quên cache schema sau khi nâng — bước dễ bỏ nhất

`billing._co_bang_phien_ban`, `webhook.xoa_cache_cot`, `don_hang.quen_cache_schema`,
`tai_chinh.quen_cache_bang`, `goi_dich_vu.nap_lai_bang` đều nhớ "bảng có hay chưa". Thiếu bước
quên cache thì một tiến trình đang chạy **vẫn nhớ "bảng chưa có"** và tiếp tục đi đường lùi —
hỏng im lặng, vì đường lùi vẫn trả kết quả hợp lệ, chỉ là kết quả của schema cũ. `chay()` nay
gọi cả 5.

## 3. 44 route — ba quyết định cố ý

| Quyết định | Vì sao |
|---|---|
| `POST /billing/du-thao` **CHƯA CẮM** | Đó là lệnh GHI tạo bản nháp **có số tiền**, mà quyền duy nhất đang có là `tenant.billing.xem` — một quyền **XEM**. Dùng nó cho lệnh ghi là **nới quyền im lặng**: ai xem được hoá đơn thì lập được hoá đơn. Cần `tenant.billing.lap_du_thao` (V-13909) |
| `POST /platform/g09/harness` **ép cứng `MOCK`** | Không nhận `che_do` từ thân. Mở cửa HTTP chạy được SANDBOX/LIVE là đưa **bốn ổ khoá chặn LIVE** ra ngoài tầm kiểm soát, và một lượt LIVE sai là **một đơn vận chuyển thật** |
| `/suc-khoe` + `/san-sang` đặt **TRƯỚC** middleware tenant | Hai đường này **vô danh**. Đặt sau middleware là health luôn trả 401 — dịch vụ sống mà bộ cân tải tưởng nó chết rồi khởi động lại vòng vo |

`/san-sang` trả **503** khi chưa sẵn sàng (bộ cân tải đọc **mã HTTP**, không đọc JSON) và chỉ
trả **chi tiết** cho người đã xác thực — thông điệp lỗi có đường dẫn và tên file.

Đường có đoạn chữ đặt **trước** nhánh có `(\d+)`.

## 4. Ba lỗi AG-00 tự tạo ra trong lượt tích hợp

Ghi ra vì chúng là bài học, không phải để tự phê:

1. **Mã hoá JSON hai lần.** Gọi `tai_chinh.json_an_toan()` trong route — nhưng hàm đó **tự
   tuần tự hoá** (trả `str`), rồi `_tra` tuần tự hoá lần nữa. Khách nhận một **chuỗi chứa
   JSON** thay vì đối tượng. Vá bằng **đổi cấu trúc**: bộ mã hoá duy nhất `_json` tự xử
   `sqlite3.Row`, rồi gỡ sạch 16 lượt gọi. Trước đó mỗi route phải tự `dict(x)` quanh từng
   truy vấn — route nào quên là ra `"<sqlite3.Row object at 0x...>"` trong phản hồi, **hỏng im
   lặng** vì nó vẫn là JSON hợp lệ và vẫn HTTP 200.
2. **`LoiGoi` không được ánh xạ** → route đổi gói trả 500. AG-02 đã nêu trong bàn giao, AG-00
   cắm thiếu. Và lượt kiểm đầu của AG-00 bảo `LoiGoi` không có `.ma` — vì hỏi trên **lớp** chứ
   không trên **thực thể**. Nó **có** `.ma`.
3. **Định danh `_ma_hoa_lạ` có dấu** — không đúng nếp mã nguồn. Đã đổi thành `_ma_hoa_la`.

## 5. Quan hệ xuyên gate — AG-00 xử thế nào

| Quan hệ | Xử |
|---|---|
| G07 → G04 | `doi_soat.py` **không chạm và không gọi** `don_hang.doi_soat_don`/`doi_soat_tay` — đối soát **kết quả gửi đơn** và đối soát **tiền** là hai việc riêng, hai bảng riêng, hai bộ trạng thái riêng |
| G07 → G06 | COD đổi trạng thái theo sự kiện giao vận, nhưng `giao_thanh_cong` **không** tự làm COD thành đã thanh toán (§18) — có ca thử dựng đơn giao thành công thật rồi đòi COD vẫn `COD_EXPECTED` |
| G08 → G01 | `goi_cua_tenant` JOIN qua `dang_ky` + `goi_phien_ban`, lùi về `goi_dich_vu` khi chưa migrate |
| G08 → G05 | Hạn mức file/dòng import **đã có** ở `gioi_han.py` PHẦN B — AG-02 nối vào cái có sẵn qua cột `nguon_dem`, không làm bộ đếm thứ hai |
| G09 → G03 | Harness **chỉ đọc** adapter; ổ khoá thứ tư là `CHO_PHEP_LIVE` trong `adapter.py`, **ngoài tầm** file harness |
| G10 → G05/G04 | AI nhận dữ liệu từ import engine, trả **đề xuất** cho đơn nháp; **không đường nào** từ kết quả AI dẫn tới `createOrder` (có ca thử) |
| G10 → G08 | Lượt AI đếm qua `billing.kiem_va_tang_ai` (nay nguyên tử) + `billing.hoan_ai` mới |
| G11 → tất cả | Lớp quan sát **chạy được khi bảng chưa có** — `ghi_su_kien()` trả `False`, chỉ ghi log. Lớp quan sát không được tự thành nguyên nhân sự cố nó định quan sát |

## 6. Việc mở sinh ra từ lượt tích hợp

| Mã | Việc |
|---|---|
| V-13908 | Quyền tài chính riêng `tenant.taichinh.xem/ghi/duyet` — hiện ai duyệt đơn thì duyệt được cả đối soát tiền |
| V-13909 | Quyền `tenant.billing.lap_du_thao` để mở `POST /billing/du-thao` |
| V-13904 | `_doc_json` chưa đóng lớp "số ở chỗ chờ chuỗi" (từ đợt 2) |
| V-13905 | Mã lý do từ chối không truy vấn được như dữ liệu có cấu trúc (từ đợt 2) |
