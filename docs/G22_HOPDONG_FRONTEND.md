# G22/AG-06 — HỢP ĐỒNG ĐÓNG BĂNG: GIAO DIỆN ↔ LỚP TRUY VẤN Ở MÁY CHỦ

**Làn:** AG-06 (G22, dispatch `ctx_7027ca94dcf4` · task `task_beedf9e94159`).
**Vùng được ghi của lượt này:** `thu_frontend/thu_logic.mjs` · `docs/G22_HOPDONG_FRONTEND.md` ·
`thu_giao_dien/*` (chỉ khi cần cho E2E). **KHÔNG** sửa `admin/*` — lượt này không cần, và
`admin/logic.js` / `admin/admin.js` vẫn đúng sha256 của lượt trước (`d502c35541023a0c67f0` /
`4fe38b49422e2ede0651`), tức phép đo không đi kèm một sửa đổi sản phẩm nào.

**Việc của lượt này:** (1) viết lại **chín ca 18–26** của tầng 1 theo **hợp đồng đã chốt**, không
phải để xanh; (2) **đối chứng âm bắt buộc** — dựng lại hành vi CŨ và chứng minh phép đo **BẮT ĐƯỢC**;
(3) **ghim mặt TENANT riêng** bằng mã trạng thái cụ thể; (4) chạy lại và ghi **từng bộ**.

**Nguồn sự thật (duy nhất):** `app/truy_van.py` (`BANG_DON`, `chay()`, `dung_dieu_kien()`,
`mo_ta_bo_loc()`, `_kiem_ten_la()`) + route trong `app/server.py`, và **§1 của
`docs/G22_TRUYVAN.md`** (hợp đồng đóng băng của AG-02). Tài liệu này **không** định nghĩa lại hợp
đồng — nó ghi lại **cách giao diện dùng hợp đồng đó**, các con số **đo được**, và **những chỗ lệch**.

> ⚠ **Nền đo của lượt này vẫn là CÂY GỘP, không phải cây làn.** Cây `g21-ag06-e2e` **chưa** chứa
> bản vá AG-02 (`app/csdl.py` ở đó vẫn `PHIEN_BAN_SCHEMA = 9`, `app/cau_hinh.py` chưa có
> `KHO_SQLITE`) — bản vá còn **chưa commit** trong cây `g21-ag02-backup`. Cách dựng lại cây gộp,
> byte-identical và có ghim sha256: **§4.1**. Đây vẫn là **khoảng trống acceptance tích hợp**, ghi
> ở §5.1, không giấu.

---

## 1. HỢP ĐỒNG MÁY CHỦ (chép lại để đọc một chỗ, KHÔNG phải bản thứ hai của mã)

### 1.1 `GET /api/v2/don` — tham số LỌC được nhận

| Tham số | Nghĩa | Ghi chú đo được |
|---|---|---|
| `q` | tìm mờ `LIKE %…%` trên **5 cột**: `ma_don` · `ma_van_don` · `nguoi_nhan_ten` · `nguoi_nhan_sdt` · `hang_hoa` | giao diện cũ chỉ tìm 4 cột **tại trang**; chuyển lên máy chủ là **mở rộng** phạm vi tìm (đo ở `test_37`) |
| `trang_thai` | trạng thái nghiệp vụ; nhận **danh sách** | |
| `trang_thai_giao` | trạng thái giao vận (trục riêng); nhận **danh sách** | |
| `hang` | mã hãng (`vtp`, `jt`…) | đi qua `carrier_accounts` **CỦA CHÍNH TENANT** — câu con có `tenant_id` |
| `carrier_account_id` | id tài khoản hãng | giao diện cũ gọi tên riêng `tai_khoan_id`; nay gửi **đúng tên máy chủ** |
| `cod_tu` / `cod_den` | khoảng COD (đồng, số nguyên) | **hai đầu BAO GỒM**; số thập phân bị **từ chối** (không cắt cụt) |
| `tu_ngay` / `den_ngay` | `YYYY-MM-DD` theo `tao_luc` (giờ VN) | **cả hai đầu BAO GỒM CẢ NGÀY**; đầu cuối dùng `< ngày kế tiếp`, không `<=` cùng ngày |
| `can_doi_soat` | `1` = cần đối soát · `0` = không cần · `''` = không lọc | cột thật là `can_doi_soat_ket_qua` |
| `khach_hang_id` · `ma_don` · `ma_van_don` · `external_reference` | lọc đúng giá trị | giao diện **chưa** dùng 4 trường này (vẫn nằm trong hợp đồng) |

### 1.2 Tham số ĐIỀU KHIỂN

| Tham số | Giá trị | Ghi chú |
|---|---|---|
| `sap_xep` | `moi_nhat` (mặc định) · `cu_nhat` · `cap_nhat_moi` · `cap_nhat_cu` · `cod_cao` · `cod_thap` · `nang_nhat` · `ma_don` | danh sách trắng; khoá lạ ⇒ **400** |
| `gioi_han` | mặc định **50**, trần **500** | vượt trần bị **KẸP** (không 400) và giá trị THẬT được trả ra ở `gioi_han` |
| `trang` | đếm từ **1** | **không gửi cùng `lech`** — hai cách đánh số cùng lúc ⇒ 400 |
| `lech` | OFFSET, trần 200 000 | |
| `dem_chinh_xac` | `1` = đếm chính xác (bỏ trần đếm) | |

### 1.3 Ba luật cứng của lớp truy vấn (giao diện phải sống chung)

1. **Tên lạ ⇒ 400**, KHÔNG bỏ qua im lặng. Thông điệp nêu tên nhận được. Giao diện hiện **nguyên
   văn** câu từ chối (`hop-loi` trong bảng) — nuốt nó là biến "máy chủ nói không nhận" thành "bảng trống".
2. **`tenant_id` LUÔN có trong `WHERE`** — không có đường bỏ qua. Và **`tenant_id` gửi từ client
   cũng là 400**: tenant lấy từ PHIÊN (`nc.tenant_id`), không bao giờ từ query. Giao diện vì thế
   **không** có ô nào tên `tenant_id` (ghim ở tầng 1 ca 25 và đo bằng HTTP ở tầng 3 ca 09).
3. **Cột chưa migrate ⇒ BỎ điều kiện nhưng NÓI RA** ở `loc_bo_qua`; giao diện chuyển tiếp lên
   dòng phạm vi (`<b class="canh">máy chủ BỎ điều kiện…</b>`).

### 1.4 Phản hồi

`dong` (trang hiện tại) · `tong` (số dòng KHỚP điều kiện, không phải số dòng trang) ·
`tong_chinh_xac` (`false` ⇒ đã chạm trần đếm, `tong` là **tối thiểu**) · `tong_it_nhat` ·
`gioi_han` / `lech` / `trang` (**giá trị thật sau khi kẹp**) · `con_nua` · `sap_xep` ·
`loc_bo_qua` · **`don`** — khoá **tương thích** mà AG-02 còn giữ trong lượt chuyển tiếp.

### 1.5 `GET /api/v2/don/loc-mo-ta` — máy chủ TỰ MÔ TẢ bộ lọc

Trả `bang` · `truong[]` (`ten`, `kieu`, `la_tien`, `mo_ta`) · `sap_xep_duoc` · `sap_xep_mac_dinh` ·
`gioi_han_mac_dinh` · `gioi_han_toi_da` · `lech_toi_da` · `tran_dem` · `dieu_kien_la` · `ngay_bao_gom`.
Giao diện **không gọi route này lúc chạy** (không buộc màn Đơn hàng phụ thuộc thêm một route);
**tầng 2 gọi nó** để đối chiếu hai danh sách (`test_40`) — lệch là ĐỎ, không nằm im trong chú thích.

---

## 2. PHÍA GIAO DIỆN (`admin/logic.js` + `admin/admin.js`)

| Ô trên màn Đơn hàng | Khoá gửi đi | Máy chủ |
|---|---|---|
| Ô tìm (`#d-tim`) | `q` | `tim_chu` 5 cột |
| Mọi trạng thái (`#d-tt`) | `trang_thai` | `bang` |
| Trạng thái giao vận (`#l-giao`) | `trang_thai_giao` | `bang` |
| Hãng vận chuyển (`#l-hang`) | `hang` | `trong_bang_khac` (câu con theo tenant) |
| Tài khoản hãng (`#l-tk`) | **`carrier_account_id`** | `bang` |
| COD từ/đến (`#l-cod-tu`, `#l-cod-den`) | `cod_tu` / `cod_den` | `tu` / `den` |
| Tạo từ/đến ngày (`#l-tu-ngay`, `#l-den-ngay`) | `tu_ngay` / `den_ngay` | `ngay_tu` / `ngay_den` |
| Chỉ đơn cần đối soát (`#l-doi-soat`) | `can_doi_soat` = `"1"` (bỏ trống khi không bật) | `co_khong` |
| Sắp xếp (`#l-sap-xep`, **mới**) | `sap_xep` | danh sách trắng §1.2 |
| Số đơn mỗi trang (`#l-gioi-han`) | `gioi_han` | kẹp ở 500 |
| Trang trước/sau (`#d-truoc`/`#d-sau`) | `trang` | OFFSET |
| **Mã vận đơn (`#l-vd`)** | **`co_van_don`** | **KHÔNG có ở máy chủ** — xem §2.2 |

### 2.1 Một chỗ khai, ba túi

`L.chiaDieuKien(dk)` chia điều kiện thành **ba** túi thay vì hai:

* `may_chu` — gửi lên máy chủ (tên **chép đúng** tên máy chủ nhận): **13 tên** — `q` · `trang_thai` ·
  `trang_thai_giao` · `hang` · `carrier_account_id` · `cod_tu` · `cod_den` · `tu_ngay` · `den_ngay` ·
  `can_doi_soat` · `gioi_han` · `trang` · `sap_xep`;
* `giao_dien` — lọc tại trang: **đúng một** phần tử, `co_van_don`;
* `la` — tên KHÔNG thuộc hai danh sách trên. Túi này **được nói ra** ở dòng phạm vi
  (`giao diện khai điều kiện lạ, KHÔNG gửi lên máy chủ: …`), không bị nuốt im lặng. `tenant_id`
  rơi vào đây — và đó là điều đúng: gửi nó lên là 400.

### 2.2 Vì sao `co_van_don` ở lại trang — và nói rõ ra

`#l-vd` hỏi "đã có / chưa có mã vận đơn". Máy chủ chỉ có `ma_van_don` (**khớp ĐÚNG một mã**),
không có phép lọc "có/không". Nên nó là **điều kiện DUY NHẤT** lọc trên trang vừa tải, và:

* nằm trong `L.THAM_SO_LOC_TAI_GIAO_DIEN` (một phần tử);
* dòng phạm vi ghi **tách** con số của nó (`x/y` đơn) khỏi con số của máy chủ (`tong`);
* `test_40` chốt `THAM_SO_LOC_TAI_GIAO_DIEN ∩ (danh sách máy chủ nhận) = ∅` — lọc hai chỗ là ĐỎ.

### 2.3 Không lọc hai chỗ — `locDon` NÉM

`L.locDon(ds, dk, tk_theo_id)` nay **chỉ** nhận điều kiện tại trang. Nhận được điều kiện của máy
chủ (`q`, `hang`, `cod_tu`, `tu_ngay`, `can_doi_soat`, `carrier_account_id`…) thì nó **ném lỗi**
kèm tên điều kiện, chứ không lặng lẽ lọc chồng lên kết quả máy chủ đã lọc. Đã đo ở tầng 1
(ca 21 — vòng qua **cả 13 tên**) và tầng 3 (dòng phạm vi). Màn Đơn hàng bắt lỗi này và hiện ra.

### 2.4 Dòng "phạm vi" dựng từ CHÍNH phản hồi máy chủ

`L.phamViLoc(kq, dk_giao_dien, so_dong_trang)` trả **dữ liệu** (không HTML) và `admin.js` in ra:
số điều kiện lọc ở máy chủ + tên · `tong` (`+` khi chạm trần đếm, kèm chữ "TỐI THIỂU") · `trang` ·
số đơn mỗi trang · phần lọc thêm tại trang (`x/y`) · `con_nua` · `sap_xep` · `loc_bo_qua` · túi `la`.
Thiếu `tong` (máy chủ cũ) ⇒ hiện **"chưa đo được tổng"**, KHÔNG suy ra 0. `gioi_han` hiện ra là
**giá trị máy chủ đã dùng** (đã kẹp), không phải con số giao diện xin.

### 2.5 Phân trang và thứ tự trả về

Trang là **trạng thái của màn** (`trang_dang_xem`), đổi bộ lọc ⇒ về trang 1; nút trước/sau giữ trang.
`ve()` gắn **số thứ tự lượt vẽ** (`lan_ve`) và **bỏ kết quả của lượt cũ** khi một lượt mới hơn đã
chạy xong — nếu không, một phản hồi về muộn sẽ vẽ số của bộ lọc CŨ lên màn đang hiện bộ lọc MỚI.

### 2.6 `API_CHO_BACKEND` — gỡ nhãn "một phần" của `/api/v2/don`

Mục `{ duong: "/api/v2/don", mot_phan: true, ghi_chu: "Máy chủ hiện chỉ nhận q · trang_thai ·
gioi_han" }` đã bị **gỡ khỏi `API_CHO_BACKEND`** (nó là một câu nói dối sau G22). Đường **không**
bị bỏ rơi: `["GET", "/api/v2/don"]` vẫn nằm trong `API_DANG_DUNG`, nên ca `test_08` của tầng 2
vẫn bắn thật nó mỗi lượt, và `test_09` (nhãn chờ-backend không được nói dối) không còn phải bỏ qua nó.
Nút **Xuất CSV** nay ghi rõ trong `title` và trong khung lọc: xuất 2000 đơn mới nhất và
**KHÔNG áp bộ lọc đang chọn** (đường xuất chưa nhận tham số lọc) — phạm vi của nút khác phạm vi của bảng.

---

## 3. BỐN MẶT PHẢI KHỚP — phép đo ở đâu

| Mặt | Câu hỏi | Phép đo | Ca |
|---|---|---|---|
| **1. Ngữ nghĩa lọc** | mỗi trường lọc có lọc ĐÚNG NGHĨA giao diện hứa? | hai đầu khoảng **bao gồm** (COD, ngày) · `q` tìm cả `hang_hoa` · `hang` qua tài khoản hãng · `trang_thai(_giao)` · `can_doi_soat` hai chiều · `sap_xep` đúng chiều · khoá lạ ⇒ 400 | `thu_frontend/thu_http.py::test_37` |
| **2. Phân trang** | trang có lặp/mất dòng không, `tong` có ổn định? | 5 đơn ÷ 2 = 3 trang (2/2/1) · giao hai trang = ∅ · hợp ba trang = đủ 5 · `tong` = 5 ở cả ba trang · `con_nua` đúng · `trang`+`lech` ⇒ 400 · `gioi_han=99999` → kẹp 500 và **trả ra** 500 | `test_38` |
| **3. Tenant** | bộ lọc nâng cao có rò dữ liệu tenant khác? | **tầng 2:** B tạo tài khoản hãng **cùng mã `vtp`** + đơn `cod=987654321`; A lọc 4 kiểu ⇒ 0 dòng, `tong`=0; **đối chứng đường**: chính bộ lọc ấy trên B ⇒ đúng 1 đơn; `hang=vtp` của A không chứa đơn của B. **tầng 3 (mã trạng thái GHIM):** A đọc dữ liệu của A ⇒ **200** · B đọc bản ghi của A ⇒ **404** · `tenant_id` trong query ⇒ **400** · A đọc lại ⇒ **200** | `test_39` + **`thu_giao_dien/01_luong_chinh.spec.js` ca 09** |
| **4. Phạm vi giao diện** | dòng "phạm vi" có nói thật, và hai danh sách có khớp? | `/api/v2/don/loc-mo-ta` **bắn thật từng** tham số giao diện khai (200) · khoá sắp xếp ⊆ danh sách trắng · `loc_tai_trang ∩ máy chủ = ∅` · mọi khoá `docDieuKien()` được khai ở một trong hai danh sách · màn không còn câu "Giao diện lọc thêm" · nhãn `mot_phan` đã gỡ | `test_40` + tầng 3 ca 03 (DOM thật: dòng `#d-pham-vi`) |

---

## 4. BẰNG CHỨNG CỦA LƯỢT CHẠY NÀY

### 4.1 Cây đo: gộp bằng lệnh, byte-identical, có ghim sha256

```sh
LANE=<g21-ag06-e2e>; AG02=<g21-ag02-backup>; CAY=/tmp/g22-ag06-merge
rm -rf "$CAY"; mkdir -p "$CAY"
git archive integration/g22 | tar -x -C "$CAY"          # nền tích hợp (có cau_hinh.KHO_SQLITE)
cp "$AG02/app/"{server,csdl,migrate}.py "$CAY/app/"      # bản vá AG-02 (chưa commit ở làn AG-02)
cp "$LANE/admin/"{logic.js,admin.js} "$CAY/admin/"       # việc AG-06 (giống hệt ở hai cây)
cp -R "$LANE/thu_giao_dien" "$CAY/thu_giao_dien"         # gồm chay.sh + 10 tệp .spec.js
cp "$LANE/thu_frontend/"{thu_logic.mjs,thu_http.py} "$CAY/thu_frontend/"
cp "$LANE/app/thu/thu_g22_e2e.py" "$CAY/app/thu/"          # (đo ở bộ khác — chép cho đủ trạng thái)
cp "$LANE/docs/G22_HOPDONG_FRONTEND.md" "$CAY/docs/"       # tài liệu này
ln -s "$LANE/node_modules" "$CAY/node_modules"
```

| Tệp | sha256 (20 ký tự đầu) |
|---|---|
| `thu_frontend/thu_logic.mjs` (**viết lại lượt này**) | `eb11f51af320a4a607b9` |
| `thu_giao_dien/01_luong_chinh.spec.js` (**thêm mặt tenant, ca 09**) | `748437c18b25580c2e4b` |
| `admin/logic.js` (AG-06, **không đổi lượt này**) | `d502c35541023a0c67f0` |
| `admin/admin.js` (AG-06, **không đổi lượt này**) | `4fe38b49422e2ede0651` |
| `thu_frontend/thu_http.py` (AG-06) | `178f80ff4260a284fe6e` |
| `thu_giao_dien/chay.sh` (AG-06) | `8affec95d1a8fb1824cf` |
| `app/thu/thu_g22_e2e.py` (AG-06) | `cabaeeb4959662cfe5cb` |
| `app/server.py` (AG-02, bản đang đo) | `776f13a79616ac23d314` |
| `app/csdl.py` (AG-02, `PHIEN_BAN_SCHEMA = 10`) | `156b53749ad3417833ec` |
| `app/migrate.py` (AG-02, có `nang_len_v10`) | `4a1926eee84abb436ed8` |
| Chromium đã ghim | `node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/chrome-mac/headless_shell` · `a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040` · `Chromium 141.0.7390.37` |

### 4.2 Bốn bộ — mã thoát và số ca TỪNG BỘ

| Bộ | Lệnh | Kết quả ĐO | Mã thoát |
|---|---|---|---|
| **Tầng 1** | `node --test thu_frontend/thu_logic.mjs` | `tests 56` · **pass 56 · fail 0 · skipped 0 · cancelled 0** | **0** |
| **Tầng 2** | `python3 thu_frontend/thu_http.py` | `Ran 40 tests` · `OK` — **đạt 40 · hỏng 0 · lỗi 0 · bỏ qua 0** | **0** |
| **Tầng 3** | `sh thu_giao_dien/chay.sh` (65 ca) | `65 passed (1.9m)` — tổng số ca của bộ là **65**, và lượt chạy **không in dòng `failed` / `skipped` / `did not run` nào** (cả ba đều 0; đây là điều ĐO ĐƯỢC từ đầu ra của reporter, không phải số tự điền) | **0** |
| Tầng 3 (dòng phạm vi + dọn máy chủ) | — | in `PHẠM VI` ở ĐẦU và in LẠI khi kết thúc · `mã thoát THẬT 0` · máy chủ tắt theo ĐÚNG PID | — |

`VIP_KHO_DANG_CHAY=sqlite` trong `chay.sh` **chỉ** khai kho của **nền TẠM** do chính script dựng
(`$NEN` là `mktemp -d`) — cần cho chốt 4b của `app/migrate.py`. Nó **không phải** cấu hình sản phẩm
và không nới chốt nào.

### 4.3 Tầng 1 — chín ca 18–26: TRƯỚC / SAU

TRƯỚC (bộ thử CŨ + `admin/` mới): `tests 56 · pass 47 · **fail 9** · mã thoát 1` — đúng chín ca
18–26. SAU (bộ thử viết lại): `tests 56 · pass 56 · fail 0 · mã thoát 0`.

| Ca | Ghim HÀNH VI CŨ (bản trước) | Bất biến ĐÚNG (bản này) |
|---|---|---|
| **18** | "chỉ `q`/`trang_thai`/`gioi_han` đi lên máy chủ, phần còn lại lọc tại giao diện" | **13** tham số đi lên máy chủ, tên **chép đúng** tên máy chủ nhận; chỉ `co_van_don` ở lại trang; túi `la` rỗng |
| **19** | bỏ điều kiện rỗng/false; `cod_tu='0'` là điều kiện **tại trang** | bỏ rỗng/false cho **cả ba túi**, NHƯNG `"0"` là điều kiện THẬT (`cod_tu='0'`, `can_doi_soat='0'` = chỉ đơn KHÔNG cần đối soát); tên lạ vào túi `la` và **không** lọt vào túi gửi máy chủ |
| **20** | `locDon` tự tìm chữ `q` (mã đơn + mã vận đơn + tên + SĐT) **tại trang** | `locDon` **chỉ** còn `co_van_don`, lọc đúng **cả hai chiều**; không điều kiện ⇒ trả nguyên danh sách; danh sách null ⇒ 0 dòng |
| **21** | `locDon` tự lọc `trang_thai_giao` **tại trang** | `locDon` **NÉM** với **mọi** tên trong `THAM_SO_MAY_CHU` (vòng qua cả 13), câu lỗi **nêu tên** điều kiện; trộn điều kiện máy chủ + tại trang cũng ném |
| **22** | `locDon` tự lọc `hang` qua bảng tài khoản hãng **tại trang** | `phamViLoc` dựng dòng phạm vi từ **chính phản hồi máy chủ**: `tong` · `trang` · `con_nua` · `sap_xep` · `loc_bo_qua` · `loc_tai_trang`; `gioi_han` là giá trị **ĐÃ KẸP** (500, không phải 99999) |
| **23** | khoảng ngày lọc tại trang theo 10 ký tự đầu của `tao_luc` | thiếu `tong`/`trang`/`gioi_han` ⇒ **null = CHƯA ĐO ĐƯỢC**, KHÔNG suy ra 0; thiếu `con_nua` ⇒ không hứa còn trang sau |
| **24** | khoảng ngày lọc tại trang (bao gồm hai đầu) | chạm **trần đếm** ⇒ `tong_chinh_xac=false`, `tong` là **TỐI THIỂU**; `loc_bo_qua` của máy chủ **chuyển tiếp** lên màn |
| **25** | `can_doi_soat` + `co_van_don` lọc tại trang; giao diện gọi tên riêng `tai_khoan_id` | hai danh sách **RỜI NHAU**; `carrier_account_id` (không `tai_khoan_id`); `co_van_don` không có trên máy chủ; **`tenant_id` và `lech` KHÔNG BAO GIỜ được gửi** (400) — `tenant_id` phải rơi vào túi `la` |
| **26** | nhiều điều kiện tại trang là AND; không điều kiện ⇒ trả nguyên danh sách | `SAP_XEP_DON` = **đúng 8 khoá** danh sách trắng §1.2, không trùng, mỗi khoá có nhãn riêng, có khoá **mặc định** `moi_nhat` |

Ba ca **20 · 22 · 24** trước kia đo **ba mặt khác nhau** (tìm chữ, hãng, ngày) bằng ba phép lọc
tại trang; nay chúng đo ba mặt **của hợp đồng mới** — lọc tại trang duy nhất, dòng phạm vi, trần đếm.
Không ca nào bị bỏ trống: số ca giữ nguyên **56**, số thứ tự giữ nguyên **18–26**.

### 4.4 ĐỐI CHỨNG ÂM — phép đo BẮT ĐƯỢC, không chỉ khẳng định

Ba cây, cùng **một** bộ thử (bộ thử MỚI ở cả ba), chỉ khác `admin/logic.js`:

| | Cây | `tests` | `pass` | `fail` | Ca ĐỎ | Mã thoát |
|---|---|---|---|---|---|---|
| **ĐCÂ-1** | `admin/` = bản **TRƯỚC G22** (`git show HEAD:admin/logic.js`, sha `60f0a329efdf77e934bd`) — tức **cả** "máy chủ cũ" **lẫn** giao diện cũ | 56 | 48 | **8** | **18 · 19 · 21 · 22 · 23 · 24 · 25 · 26** | **1** |
| **ĐCÂ-2** | chỉ **đảo `THAM_SO_MAY_CHU`** về danh sách CŨ `["q","trang_thai","gioi_han"]` (sha `9009e58d30d85f7a4ec3`) — đúng phép đối chứng của Phụ lục A lượt trước | 56 | 53 | **3** | **18 · 19 · 25** | **1** |
| (chuẩn) | `admin/` hiện tại | 56 | **56** | 0 | — | **0** |

Thông điệp đỏ đo được (trích nguyên văn):

* ĐCÂ-2 ca 18: `actual: [ 'gioi_han', 'q', 'trang_thai' ]` / `expected: [ 'can_doi_soat',
  'carrier_account_id', 'cod_den', 'cod_tu', 'den_ngay', 'gioi_han', 'hang', 'q', 'sap_xep',
  'trang', 'trang_thai', 'trang_thai_giao', 'tu_ngay' ]`;
* ĐCÂ-2 ca 19: `cod_tu='0' là điều kiện THẬT, không phải rỗng` — `actual: {}` / `expected: { cod_tu: '0' }`;
* ĐCÂ-2 ca 25: `máy chủ nhận carrier_account_id; giao diện không được gửi tên riêng tai_khoan_id` — `actual: false`;
* ĐCÂ-1 ca 21: `Missing expected exception: lọc lại \`q\` tại trang là LỌC HAI CHỖ — phải ném`;
* ĐCÂ-1 ca 22–24: `TypeError: L.phamViLoc is not a function` (hàm ấy **chưa tồn tại** trước lượt này);
* ĐCÂ-1 ca 26: `TypeError: Cannot read properties of undefined (reading 'map')` (`SAP_XEP_DON` chưa có).

**Một chỗ KHÔNG flip, ghi ra chứ không giấu:** ca **20** vẫn XANH ở ĐCÂ-1, vì `co_van_don` là
điều kiện **duy nhất** mà bản cũ cũng đã lọc tại trang — nó là ca **liên tục**, không phải ca đổi
hợp đồng. Nói "9/9 ca đỏ khi quay lại hành vi cũ" sẽ là **sai**; con số đo được là **8/9**.

### 4.4b Đối chứng âm ở mức HTTP — "máy chủ trả về hành vi CŨ", đo bằng HTTP thật

Bốn phép đối chứng nữa, lần này ở tầng có HTTP (nơi mặt tenant và các mã trạng thái sống):

| | Cây / phép đặt lại | Lệnh | Kết quả ĐO | Mã thoát |
|---|---|---|---|---|
| **ĐCÂ-3** | `app/server.py` = bản **TRƯỚC AG-02** (`integration/g22:app/server.py`, sha `23515e6d1dcb1cedd0e7`, `import truy_van` = **0**) | `python3 thu_frontend/thu_http.py --doi-chung-am <server.py cũ>` | `Ran 40` · **5 ĐỎ**: `test_10` · `test_37` · `test_38` · **`test_39` (tenant)** · `test_40` · `test_10` đỏ **đúng lý do** (*"máy chủ BỎ QUA điều kiện"*) | bộ thử trên cây cũ **1** · **đối chứng ĐẠT 0** |
| **ĐCÂ-4** | cùng cây cũ ấy, tầng 3 | `sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js` | `2 passed · 1 failed` (ca 03) — 8 ca sau **không chạy** vì tệp chạy `serial` | **1** |
| **ĐCÂ-5** | cùng cây cũ ấy, chỉ ca tenant | `sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js -g "09"` | ĐỎ: `phản hồi 200 thiếu \`dong\` — hình dạng phản hồi đã lệch hợp đồng §1.4` | **1** |
| **ĐCÂ-6** | cây **hợp đồng** + **đúng một dòng** `ts.pop("tenant_id", None)` trước `truy_van.tim_don` (máy chủ BỎ QUA IM LẶNG lựa chọn tenant của client) | `sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js -g "09"` | ĐỎ **đúng chỗ ghim**: `tự chọn tenant bằng \`tenant_id\` trong query: hợp đồng ghim 400, đo được 200` | **1** |

ĐCÂ-6 là phép đo quan trọng nhất của §4.5: nó chứng minh **con số 400 được GHIM**, chứ không phải
một câu "200 hoặc 400" — nếu ghim một khoảng thì lượt này đã XANH và không ai biết máy chủ đang
cho client tự chọn tenant.

### 4.5 MẶT TENANT — ghim mã trạng thái cụ thể (không dùng "200 hoặc 400")

Supervisor đã bác bỏ đề xuất `assertIn(st, (200, 400))`: một câu chấp nhận **cả hai** thì không đo
được gì. Ba mã dưới đây là **ghim**, và cả ba đều **đo được**:

| Phép đo | Ghim | Đo được ở | Kết quả |
|---|---|---|---|
| Tenant **A** đọc danh sách đơn **của A** (đối chứng DƯƠNG) | **200** | tầng 3 ca 09 | `A=1 (9 đơn)` · `tong > 0` |
| Tenant **B** đọc **một bản ghi của A** (đối chứng ÂM cross-tenant) | **404** | tầng 3 ca 09 (và `test_32` tầng 2) | `B=2 (0 đơn)` · `B đọc bản ghi của A → 404` |
| Ai đó **tự chọn tenant** bằng `tenant_id` trong query | **400** | tầng 3 ca 09 | `tenant_id trong query → 400`, thân có `loi` **nêu tên** `tenant_id` |
| Quay lại **A** đọc **chính bản ghi ấy** | **200** | tầng 3 ca 09 | `A đọc lại → 200`, đúng `id` đã hỏi |
| **B** lọc 4 kiểu bằng dữ liệu của A · đối chứng đường trên **B** | **200 · 0 dòng / 200 · 1 dòng** | tầng 2 `test_39` | `4 bộ lọc của A → 0 dòng · đối chứng trên B → đúng 1 đơn (id 24) · hang=vtp của A không chứa đơn của B` |

Ca 09 tầng 3 nay đo **đúng cái tên nó hứa**: bản trước chỉ so **chân trang đổi chữ** (một nhãn
đổi mà dữ liệu không đổi vẫn qua sạch); bản này gọi API bằng **chính phiên của trang**
(`page.request`, dùng chung cookie), đi qua đúng con đường giao diện đi, và chờ ngữ cảnh đổi bằng
`/api/v2/auth/toi` **của máy chủ** chứ không bằng `sleep`. Số ca tầng 3 **không đổi: 65**.

**Ba mã ấy là GHIM, và đã chứng minh là BẮT ĐƯỢC** — không phải lời khẳng định: ĐCÂ-3 (§4.4b) cho
`test_39` (tenant) **ĐỎ LẠI** khi máy chủ về hành vi cũ; ĐCÂ-5 cho ca 09 **ĐỎ** trên máy chủ cũ;
ĐCÂ-6 cho ca 09 **ĐỎ ĐÚNG CHỖ GHIM 400** khi máy chủ chỉ BỎ QUA IM LẶNG `tenant_id`.

---

## 5. NHỮNG CHỖ LỆCH — GHI RÕ, KHÔNG GIẤU

### 5.1 Nền đo: bản vá AG-02 vẫn CHƯA commit ⇒ chưa có acceptance tích hợp

| | |
|---|---|
| Cây làn AG-06 | `g21-ag06-e2e @ f9f6632` — `app/csdl.py` `PHIEN_BAN_SCHEMA = 9`, `app/cau_hinh.py` **chưa có** `KHO_SQLITE` |
| Bản vá AG-02 | **chưa commit**, nằm trong cây làm việc `g21-ag02-backup` (`app/server.py`, `app/csdl.py`, `app/migrate.py`) |
| `integration/g22` | cũng **chưa** có bản vá AG-02 (nhưng **đã có** `cau_hinh.KHO_SQLITE`) |

⇒ Mọi con số ở §4 chạy trên **cây gộp** dựng bằng lệnh ở §4.1. Cây ấy **không** phải cây làn, nên
đây **vẫn chưa** là acceptance tích hợp: nó là **cùng một trạng thái sau khi gộp**, với ba tệp
AG-02 byte-identical (sha256 ở §4.1). Ai gộp xong ba tệp ấy vào cây làn thì chạy lại **đúng ba
lệnh** ở §4.2 là ra lại các con số này.

### 5.2 Tầng 1 không có HTTP ⇒ mã trạng thái không thể ghim ở đó

`thu_logic.mjs` là **logic thuần** (không DOM, không fetch). Vì thế mặt **tenant** và các mã
**400/404** được ghim ở **tầng 2** (`test_37`…`test_40`) và **tầng 3** (ca 09) — nơi có HTTP thật.
Điều tầng 1 ghim được cho mặt tenant là **phía giao diện**: `tenant_id` **không** nằm trong
`THAM_SO_MAY_CHU` và phải rơi vào túi `la` (ca 25). Nói rằng tầng 1 "ghim tenant" là nói quá.

### 5.3 Hai bộ thử NGOÀI vùng được ghi của lượt này vẫn đang ghim hành vi cũ

`docs/G22_TRUYVAN.md` §5 dòng #2 và #3 (chủ: chủ bộ thử) đề xuất `assertIn(st, (200, 400))` cho
`thu_qa_soat.py::test_q09f…` và `thu_g01_g02.py::test_010…` khi gửi `?tenant_id=<B>`. Theo hợp
đồng §1.4, mã **đúng** là **400** (tham số lạ) — không phải một khoảng. Hai tệp ấy **không** nằm
trong vùng được ghi của làn này, nên **tôi không sửa**; đề nghị sửa theo cùng luật đã áp ở §4.5
(**ghim 400**, và nếu muốn đo thêm thì đo rằng **không** dòng nào của tenant khác xuất hiện).

### 5.4 Chốt 4b của `app/migrate.py` chặn `chay.sh` trên nền tích hợp

`app/migrate.py` (làn sao lưu) đòi tiến trình gọi `migrate` phải **KHAI kho đang chạy**; thiếu
khai ⇒ **TỪ CHỐI**. Đã vá **trong vùng được ghi**: `thu_giao_dien/chay.sh` và
`app/thu/thu_g22_e2e.py` khai `VIP_KHO_DANG_CHAY=sqlite` — nền của cả hai là SQLite trong thư mục
**TẠM** do chính chúng dựng, nên khai `sqlite` là khai **ĐÚNG**, không phải mặc định cho tiện.
**Runner khác gọi `migrate` mà không khai kho thì cũng sẽ bị TỪ CHỐI như vậy** — cần rà tiếp
ngoài làn này.

### 5.5 Khoá `don` (tương thích) nay có thể gỡ — việc của AG-02

`app/server.py` trả **cả** `dong` và `don` với chú thích *"gỡ `don` sau khi `admin/*` chuyển hẳn
sang `.dong`"*. `admin/admin.js` nay đọc `kq.dong || kq.don`, tức là **đã chuyển hẳn**. Gỡ khoá
`don` là việc trong `app/server.py` (làn AG-02) — giao diện chạy đúng ở cả hai trạng thái, và
`test_10` cố ý **không** ghim sự có mặt của khoá ấy (chỉ `test_40` ghim các trường phân trang).

### 5.6 Ca 18–26 KHÔNG ghim `khach_hang_id` · `ma_don` · `ma_van_don` · `external_reference`

Bốn trường ấy nằm trong hợp đồng máy chủ nhưng giao diện **chưa dùng**, nên `THAM_SO_MAY_CHU`
không có chúng và ca 18 **không** đòi chúng. Đây là **phạm vi giao diện**, không phải thiếu sót
của hợp đồng: giao diện nào cắm thêm ô lọc cho bốn trường ấy thì phải khai vào `THAM_SO_MAY_CHU`
và ca 18 sẽ đỏ cho tới khi khai — đúng chiều tiến bộ.

---

## PHỤ LỤC A — LỆNH CHẠY LẠI TOÀN BỘ BẰNG CHỨNG CỦA LƯỢT NÀY

```sh
# (0) dựng cây gộp — §4.1
# (1) tầng 1
node --test thu_frontend/thu_logic.mjs                       # 56 · pass 56 · fail 0 · rc 0

# (2) đối chứng âm tầng 1 — hai cây, cùng bộ thử MỚI
DC=/tmp/ag06-dc; rm -rf "$DC"; mkdir -p "$DC/dc1/admin" "$DC/dc2/admin" \
    "$DC/dc1/thu_frontend" "$DC/dc2/thu_frontend"
git show HEAD:admin/logic.js > "$DC/dc1/admin/logic.js"      # hành vi CŨ (cả máy chủ lẫn giao diện)
git show HEAD:admin/admin.js > "$DC/dc1/admin/admin.js"
cp admin/admin.js "$DC/dc2/admin/admin.js"                    # ĐCÂ-2: chỉ đảo THAM_SO_MAY_CHU
python3 - "$DC/dc2/admin/logic.js" <<'PY'
import sys
p = sys.argv[1]
ma = open("admin/logic.js", encoding="utf-8").read()
cu = '''  const THAM_SO_MAY_CHU = [
    "q", "trang_thai", "trang_thai_giao", "hang", "carrier_account_id",
    "cod_tu", "cod_den", "tu_ngay", "den_ngay", "can_doi_soat",
    "gioi_han", "trang", "sap_xep",
  ];'''
assert cu in ma, "khoi THAM_SO_MAY_CHU doi hinh dang — doc lai §2.1"
open(p, "w", encoding="utf-8").write(
    ma.replace(cu, '  const THAM_SO_MAY_CHU = ["q", "trang_thai", "gioi_han"];'))
PY
cp thu_frontend/thu_logic.mjs "$DC/dc1/thu_frontend/"; cp thu_frontend/thu_logic.mjs "$DC/dc2/thu_frontend/"
node --test "$DC/dc1/thu_frontend/thu_logic.mjs"             # 8 ĐỎ (18·19·21·22·23·24·25·26) · rc 1
node --test "$DC/dc2/thu_frontend/thu_logic.mjs"             # 3 ĐỎ (18·19·25) · rc 1

# (3) tầng 2 và tầng 3 — trên cây gộp
python3 thu_frontend/thu_http.py                             # Ran 40 · OK · rc 0
sh thu_giao_dien/chay.sh                                     # 65 passed · rc 0

# (4) đối chứng âm ở mức HTTP — "máy chủ trả về hành vi CŨ" (§4.4b)
git show integration/g22:app/server.py > /tmp/ag06-dc/server_cu.py   # sha 23515e6d1dcb1ced…
python3 thu_frontend/thu_http.py --doi-chung-am /tmp/ag06-dc/server_cu.py   # 5 ĐỎ · đối chứng ĐẠT · rc 0
tar -C /tmp/g22-ag06-merge -cf - . | tar -C /tmp/ag06-dc-cay-cu -xf -        # cây cũ (ĐCÂ-4/5)
cp /tmp/ag06-dc/server_cu.py /tmp/ag06-dc-cay-cu/app/server.py
cd /tmp/ag06-dc-cay-cu
sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js                 # 2 passed · 1 failed · rc 1
sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js -g "09"         # ca 09 ĐỎ (thiếu `dong`) · rc 1

# (5) đối chứng âm SÚT ĐÚNG CHỖ GHIM 400 (§4.4b, ĐCÂ-6)
tar -C /tmp/g22-ag06-merge -cf - . | tar -C /tmp/ag06-dc-cay-tenant -xf -
# chèn ĐÚNG MỘT dòng ngay trước lời gọi truy_van.tim_don trong app/server.py:
#     ts.pop("tenant_id", None)
cd /tmp/ag06-dc-cay-tenant
sh thu_giao_dien/chay.sh 01_luong_chinh.spec.js -g "09"         # ĐỎ: "ghim 400, đo được 200" · rc 1
```

Chín ca 18–26 nằm ở `thu_frontend/thu_logic.mjs`, khối
`/* --- Chín ca dưới đây (18–26) VIẾT LẠI theo hợp đồng đã chốt (G22) … */`. Mỗi ca có **hai dòng
đầu**: `CŨ:` (nó từng ghim gì) và `MỚI:` (bất biến đúng là gì) — để lượt sau không phải đoán ý.
