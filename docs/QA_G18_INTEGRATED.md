# NGHIỆM THU TÍCH HỢP G18 — AG-01 LƯỢT 2 (ĐỘC LẬP)

> **Vai**: NGƯỜI KIỂM. Lượt này **không sửa một dòng mã sản phẩm nào**. Tệp được ghi:
> `docs/QA_G18_INTEGRATED.md` (mới) và `app/thu/thu_qa_g18_tich_hop.py` (mới).
> Mọi số trong tài liệu này do **chính tôi chạy**, không chép từ báo cáo của làn nào.
>
> **Khác gì `docs/QA_G18.md` (lượt 1)**: lượt 1 nghiệm thu **từng làn trên nhánh của nó**.
> Lượt này nghiệm thu **cây đã gộp** `integration/g18` — nơi sáu làn gặp nhau — và chỉ hỏi những
> câu mà từng làn riêng lẻ **không thể** thấy.

---

## 0. BỐI CẢNH

| | |
|---|---|
| Nhánh worktree | `g18-ag01-verify` |
| `HEAD` | `626d4221be88dfb8988d6382ff0b781328d4869c` |
| `integration/g18` | `626d4221be88dfb8988d6382ff0b781328d4869c` (**trùng** — worktree đứng đúng mốc) |
| Mốc gộp | `626d422 AG-00 gop g18-ag04-httpserver (commit tai lieu cuoi) — lay BAN CUA AG-04` |
| Số bộ thử bộ chạy chung dò được | **43** (khớp lời khai của AG-00) |

Sáu làn đã gộp: AG-01 (`thu_qa_g18` 43 ca) · AG-02 (`thu_g18_multiprocess` 26 ca) ·
AG-03 (`thu_g18_bi_mat` 15 ca) · AG-04 (`thu_g18_maysrv` 17 ca + harness riêng) ·
AG-05 (`thu_postgres` 55 ca) · AG-06 (`thu_g18_crash` 31 ca).

---

## 1. VÂN TAY CÂY · MÔI TRƯỜNG · CÁCH ĐO

**Lệnh vân tay (nguyên văn, dùng cho cả TRƯỚC và SAU):**

```sh
{ git ls-files -s; git status --porcelain=v1; } | shasum -a 256
```

| Mốc | Vân tay |
|---|---|
| **TRƯỚC** (cây sạch, chưa ghi gì) | `1cf4d24886eb6b1ebbeb5ebe446472ac7ea76567e16587c39dcaa88d21142713` |
| Sau lượt hồi quy, **trước khi** tôi thêm hai tệp | `1cf4d24886eb6b1ebbeb5ebe446472ac7ea76567e16587c39dcaa88d21142713` (**BẰNG**) |
| SAU (đã thêm hai tệp của lượt này) | xem §3.3 — chênh lệch **đúng hai tệp mới**, không tệp nào khác đổi |

### 1.1 `N-G18-00` — cái bẫy môi trường, và nó đã bẫy chính tôi ở lần đo đầu

Phiên này có `GIT_CONFIG_COUNT=2` nhưng **thiếu** `GIT_CONFIG_KEY_0/1` (chỉ có `VALUE_0/1`).
Hệ quả: **mọi lệnh git thoát 128**, kể cả `git status`. Lượt chạy "nguyên văn" vì thế cho ra
một vân tay của **chuỗi rỗng**:

```
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855   ← sha256 của 0 byte
```

**Tôi đã dính đúng bẫy này** ở khối ghi vân tay đầu tiên (đã ghi lại trong log thô). Nó không
làm hỏng lượt đo — tôi đã lấy vân tay TRƯỚC bằng một lệnh riêng đã gỡ biến, **trước khi ghi bất
kỳ tệp nào**, và con số ở §1 là con số đó. Nhưng nó là bằng chứng sống cho `N-G18-00`: một bộ đo
mà kết quả phụ thuộc việc người gọi có nhớ gỡ một biến hay không thì không đáng tin — và
`app/thu/chay_tat_ca.sh` đã tự chuẩn hoá đúng chỗ ấy (tôi xác nhận nó in dòng cảnh báo và chạy
tiếp, exit 0).

Mọi lệnh dưới đây chạy với gia đình `GIT_CONFIG_*` **đã gỡ**.

---

## 2. BẢNG ĐỐI CHIẾU — LỜI KHAI TỪNG LÀN vs SỐ TÔI TỰ ĐO

Nguyên tắc: **mã thoát đọc TRƯỚC mọi pipe**, số ca đọc từ chính dòng `Ran N` / `N ca — ĐẠT` của
bộ thử. Không dùng `| head`/`| tail` chắn giữa lệnh và `$?`.

| Làn | Bộ thử | Khai | **Tôi đo** | Exit | Bỏ qua | Khớp? |
|---|---|---|---|---|---|---|
| AG-02 | `app/thu/thu_g18_multiprocess.py` | 26 ca · exit 0 | **`26 ca — ĐẠT`** | **0** | 0 | ✅ |
| AG-03 | `app/thu/thu_g18_bi_mat.py` | 15 ca · exit 0 | **`Ran 15 tests` · `OK`** (2,606 s) | **0** | 0 | ✅ |
| AG-04 | `app/thu/thu_g18_maysrv.py` | 17 ca · exit 0 | **`Ran 17 tests` · `OK`** (5,505 s) | **0** | 0 | ✅ |
| AG-04 | `trien_khai/g18/chay_harness.sh` (harness riêng) | 18/20 đạt · 2 bỏ qua | **`18/20 ca đạt · 0 hỏng · 0 BLOCKED · 2 bỏ qua`** | **0** | 2 | ✅ |
| AG-05 | `app/thu/thu_postgres.py` | 55 ca · exit 0 | **`Ran 55 tests` · `OK`** (7,335 s) | **0** | 0 | ✅ |
| AG-06 | `app/thu/thu_g18_crash.py` | 31 ca · exit 0 | **`Ran 31 tests` · `OK`** (5,666 s) | **0** | 0 | ✅ |
| AG-01 | `app/thu/thu_qa_g18.py` | 43 ca | **`Ran 43 tests` · `OK (skipped=1)`** (93,260 s) | **0** | **1** | ✅ |
| AG-01 (lượt 2) | `app/thu/thu_qa_g18_tich_hop.py` | (tệp mới) | **`Ran 26 tests` · `OK`** (3,378 s) | **0** | 0 | — |

**Kết luận: KHÔNG LỆCH MỘT CA NÀO.** Bảy trên bảy lời khai đều đúng ở cả số ca lẫn mã thoát.
Hai dòng đáng chú ý:

* **AG-05 chạy được thật, không bỏ qua.** Bộ này tự dựng cụm PostgreSQL riêng bằng `initdb` +
  `pg_ctl`; tôi chạy với `VHPG_CONG=55432`. Cổng **5432 đang bị một `postgres` hệ thống giữ**
  (đã kiểm bằng `lsof`); bộ thử **từ chối chạy nếu cổng là 5432** (`_kiem_cong_an_toan`), và tôi
  **không đụng** cụm ấy. Cụm 55432 trống trước khi chạy.
* **`thu_qa_g18` có đúng 1 ca BỎ QUA** (`H_Postgres`: chỉ chạy khi `VIP_G18_DAY_DU=1`). Con số 43
  là số ca **đã chạy**; ca thứ 44 chỉ chạy ở làn đầy đủ. Đây là bỏ qua **có khai báo**, không im lặng.

---

## 3. HỒI QUY TRÊN CÂY SẠCH (việc 3)

### 3.1 Số liệu

| | |
|---|---|
| **SHA** | `626d4221be88dfb8988d6382ff0b781328d4869c` |
| **Lệnh** | `sh app/thu/chay_tat_ca.sh` |
| **Mã thoát** | **0** |
| **Số ca** | **1605** |
| **Số bộ** | **43 bộ chạy thật · 0 bộ BỎ QUA** |
| **Số bộ HỎNG** | **0** |
| **SKIP** | **0** (không dòng `skipped` nào; không bộ nào bị bỏ qua ở mức bộ) |
| **Frontend** | tầng 1 (node): **56 ca** · tầng 2 (HTTP + tệp tĩnh): **36 ca** |
| **E2E qua HTTP thật** | **`KẾT QUẢ: 41/41 phép đo đạt`** |
| **Vân tay TRƯỚC** | `1cf4d24886eb6b1ebbeb5ebe446472ac7ea76567e16587c39dcaa88d21142713` |
| **Vân tay SAU** | `1cf4d24886eb6b1ebbeb5ebe446472ac7ea76567e16587c39dcaa88d21142713` (**BẰNG**) |
| Phạm vi in ra | Darwin arm64 · python 3.9.6 · SQLite 3.51.0 · 2 hãng đăng ký (jt, vtp), **0 hãng mở live** |

**Khớp AG-00 từng con số**: exit 0 · 1605 ca · 43 bộ · 0 hỏng · E2E 41/41.

**Một điểm KHÔNG khớp — vân tay.** AG-00 ghi `e5df72e93bd647d1` (16 ký tự hex). Tôi **không tái
lập được** giá trị ấy bằng lệnh đã cho: trên cây sạch tôi đo được **sha256**
`1cf4d24886eb6b1ebbeb5ebe446472ac7ea76567e16587c39dcaa88d21142713`; tôi cũng thử **sha1**
(`c56a0083…`) và **md5** (`182d833b…`) trên cùng đầu vào — **không** giá trị nào là
`e5df72e93bd647d1`. Nên nhiều khả năng AG-00 dùng **công thức băm khác** (16 hex ⇒ hàm 64-bit),
chứ không phải dạng rút gọn của sha256.

Điều **kiểm được** và **vẫn đúng**: TRƯỚC = SAU theo **cùng một lệnh** — đó mới là tính chất mà
vân tay dùng để canh. Nhưng nếu muốn lượt sau đối chiếu được với AG-00 thì **phải ghi kèm công
thức**, nếu không thì hai vân tay không so được với nhau (đúng bài học `N-G18-00`: hai nhiệt kế đo
hai thứ khác nhau thì không con số nào đối chiếu được).

Tầng 3 (DOM/CSS trong Chromium) **không chạy** trong bộ này theo thiết kế — bộ chạy in rõ
`CÓ, nhưng KHÔNG chạy ở đây` và trỏ sang `sh thu_giao_dien/chay.sh`. Tôi **không** chạy nó ở lượt
này (xem §6).

### 3.2 Cảnh báo EPERM đã được kiểm đúng cách

Đề bài dặn: `EPERM` do sandbox chặn ghi `thu_giao_dien/_bao-cao/` **không phải** ca thử hỏng.
Lượt này **không gặp** `EPERM` nào: cả 43 bộ đều thoát 0, không bộ nào bị báo hỏng. Ghi lại để
người sau không phải suy đoán.

### 3.3 Vân tay SAU khi thêm hai tệp của lượt này

Hai tệp tôi được phép ghi là **tệp mới** (untracked). Vân tay SAU cùng delta được ghi ở §7.3.
Tôi đã kiểm: **không tệp nào khác** bị đổi (`git status --porcelain` chỉ có đúng hai dòng `??`).

### 3.4 Hồi quy lần 2 — SAU khi hai tệp mới ra đời: **2 bộ ĐỎ**, và đây là một PHÁT HIỆN

Tôi chạy lại cổng chung một lần nữa, lần này **có** hai tệp mới, để trả lời câu "tệp mới của tôi
có phá cổng chung không":

| | |
|---|---|
| Lệnh | `sh app/thu/chay_tat_ca.sh` |
| Mã thoát | **1** |
| Số ca | **1631** (= 1605 + **26** ca của tệp mới) |
| Số bộ | **44** bộ chạy thật |
| **Bộ HỎNG** | **`thu_qa_g17.py` · `thu_qa_g18.py`** |
| Tệp mới của tôi trong cổng chung | **`✓ thu_qa_g18_tich_hop.py 26 ca`** — **ĐẠT** |
| Vân tay TRƯỚC = SAU | `78eeaa98…` (BẰNG) |

**Nguyên nhân — đọc thẳng từ output, không suy đoán:**

```
✗ thu_qa_g17.py   53 ca  HỎNG  FAIL: test_a1_cay_sach_va_head (__main__.A_Nen)
✗ thu_qa_g18.py   43 ca  HỎNG  FAIL: test_a1_cay_sach_mien_tru_dung_hai_tep_ag01 (__main__.A_Nen)
```

Chạy riêng `thu_qa_g18.py` để lấy nguyên văn:

```
AssertionError: Lists differ: ['?? app/thu/thu_qa_g18_tich_hop.py',
                               '?? docs/QA_G18_INTEGRATED.md'] != []
  : cây có thay đổi NGOÀI hai tệp AG-01 G18
```

Cả hai bộ đỏ ở **cổng nền F0-a "cây sạch"** — cổng này liệt kê `git status --porcelain` rồi
**miễn trừ theo MẪU TÊN của chính làn mình**:

* `thu_qa_g17.py`: `MAU_TEP_CUA_AG01_G17 = ("app/thu/thu_qa_g17*.py", "docs/QA_G17*.md")`
* `thu_qa_g18.py`: miễn trừ đúng hai tệp của lượt 1

Hai tệp mới của lượt này (`thu_qa_g18_tich_hop.py`, `QA_G18_INTEGRATED.md`) **không khớp mẫu nào**,
nên bị tính là "cây bẩn". Đây là **xung đột quyền sở hữu mẫu tên giữa các làn**, và nó **chỉ hiện
ra khi gộp** — mỗi làn tự thấy mình đúng.

**Bằng chứng đây là ĐỎ TẠM THỜI, không phải lỗi sản phẩm** — và tôi đo được, không suy luận:

> Hồi quy **lần 1** (§3.1) chạy trên cây **đã commit** `626d422`, trong đó `app/thu/thu_qa_g17.py`
> và `app/thu/thu_qa_g18.py` **có mặt**, và **cả hai đều XANH**. Nghĩa là: tệp **đã theo dõi và
> không sửa** thì `git status --porcelain` **không in dòng nào** ⇒ cổng F0-a không thấy.
> Hai tệp của tôi đỏ **chỉ vì chúng chưa được commit**.

⇒ **Ngay khi AG-00 commit hai tệp này, cả hai cổng trở lại XANH** mà không phải sửa một dòng mã
nào. Không cần nới mẫu miễn trừ — nhưng nếu muốn cổng chịu được tệp mới **trước** khi commit thì
phải nới mẫu.

**Điều đáng ghi lại** (không phải lỗi, mà là bài học vận hành): một **tạo tác nghiệm thu** lại làm
**cổng nghiệm thu của làn khác** đỏ. Ai chạy cổng chung trong lúc có tệp mới chưa commit sẽ thấy
2 bộ đỏ và **dễ kết luận sai là hồi quy**. Ghi ra đây để lượt sau không mất thời gian truy lại.

**Bộ thử mới của tôi tự nó KHÔNG có cổng "cây sạch"** — nó không đỏ vì tệp của người khác.

---

## 4. ĐỐI CHIẾU CHÉO (việc 2 — phần quan trọng nhất)

> Đề bài: *"Chỉ chạy lại bộ của người khác rồi bảo 'khớp' thì đó KHÔNG phải đối chiếu độc lập."*
> Nên mỗi mục dưới đây nêu rõ **tôi đã làm gì KHÁC** hai người kia.

### 4.1 V5 — hai dụng cụ đo: **ĐỒNG Ý**, và lệch chỉ ở **PHẠM VI**

Hai bộ đo V5 (cách ly tenant toàn cục) **khác nhau về nguyên lý**:

| | AG-06 — `thu_g17_baomat.py` | AG-01 — `thu_qa_g18.py` |
|---|---|---|
| Cách dựng phạm vi | **BẢNG CỬA khai tay** + phép canh KHAI BÁO đối chiếu `server.py` (`bang_cua()` ↔ `_cua_tu_nguon()`) | **RÚT từ chính mã nguồn** bằng regex (`duong_ghi_tinh` / `duong_ghi_dong` / `duong_platform`) |
| Cách phán | quét `(cửa × phiên A/B)` qua HTTP, phân loại `doc_ds/doc_id/ghi_id/tao/toan_cuc/nen_tang/…` | bắn HTTP thật, đòi mã chính xác (401/403) |
| Điểm mạnh riêng | có **canh khai báo**: route mới mà quên khai ⇒ ĐỎ | không có bảng tay nên không bỏ sót route mới |

**Tôi đã làm gì khác**: tôi **không** so kết luận của hai bộ, mà **so hai BỘ TRÍCH với nhau** —
chạy cả hai bộ trích trong hai tiến trình riêng, chuẩn hoá hai đầu ra bằng **cùng một hàm**
(`_mo_rong(_chuan_hoa(p))`, bản sao đúng của AG-06), rồi so hai tập. Có **ca tự kiểm B0**: bộ
chuẩn hoá của tôi phải cho ra **đúng** tập mà AG-06 tự chuẩn hoá — nếu không thì mọi phép so dưới
đây so hai thứ khác nhau.

Kết quả (`[B0]`–`[B4]` trong bộ thử):

```
[B0] bộ chuẩn hoá của tôi == bộ của AG-06 (104 route)
[B1] AG-06 = 104 route · AG-01 = 73 route
[B2] 0 route lạ: cả 73 route của AG-01 đều nằm trong tập của AG-06
[B3] GIAO = 73 · CHỈ AG-06 đo = 31
[B4] 31/31 route chỉ-AG-06-đo đều thuộc /api/v2/ ⇒ route thật, không phải rác
```

**Trả lời câu hỏi "hai phép đo có đồng ý không?"**

* **ĐỒNG Ý.** Trên **73 route** mà cả hai cùng đo, hai dụng cụ **không mâu thuẫn ở một route nào**:
  cả hai bộ đều XANH trên cùng commit này, và `[B2]` chứng minh AG-01 **không đo route hoang** nào
  (mọi route nó đo đều tồn tại theo phép đếm độc lập của AG-06).
* **LỆCH — nhưng lệch PHẠM VI, không lệch KẾT LUẬN.** AG-06 phủ **104** route; AG-01 có bằng
  chứng cho **73**; **31 route chỉ AG-06 đo**. Đó **không phải** "hai bên nói khác nhau", mà là
  **một bên không đo**. Nói theo §12.1 luật 3: 31 route ấy **chưa có bằng chứng V5 từ bộ của AG-01**
  — và **cũng không được coi là hở**, vì AG-06 đã đo chúng và thấy kín.

### 4.2 PHÁT HIỆN: con số `41` đang lưu trong tài liệu là **artefact của phép so**

`docs/OWNER_ACTIONS.md` dòng 63 ghi: *"V5 của AG-01 phủ **41 cửa ⊂ 104 route** của AG-06"*.

Tôi **tái hiện được đúng 41** — nhưng chỉ khi so **SAI**: không mở các **nhóm chọn** `(a|b|c)`
trong mẫu route của AG-01.

| Cách so | AG-01 | GIAO |
|---|---|---|
| **Mở nhóm chọn** (đúng — mỗi nhánh là một route thật) | 73 | **73** |
| **KHÔNG mở nhóm chọn** (sai) | 75 | **41** ← đúng con số đang lưu |

Ví dụ cụ thể: `/api/v2/don/(\d+)/(duyet|gui|huy)` là **3 route thật**; so mà không mở nhóm thì cả
3 bị coi là 1 chuỗi không khớp gì, nên **mất 2 route** khỏi phần giao.

**Nói thẳng mức độ chắc chắn**: tôi **không** chứng minh được ai đã đo bằng cách nào. Tôi chỉ
chứng minh: (a) cách so đúng cho **73**; (b) cách so sai cho **đúng 41**; (c) cả hai cách đều cho
`⊂ 104`. Nên **con số 41 nhiều khả năng là artefact**, và nếu vậy thì nó **nói thấp hơn sự thật**
về phủ V5 của AG-01 — hướng sai *ít nguy hiểm* hơn "nói quá", nhưng vẫn là một con số không đo được
lại. **Đề nghị AG-00 ghi lại mốc `73/104` (khoảng trống 31 route)** kèm cách so, để lượt sau đo lại được.

### 4.3 Đa tiến trình — AG-02 (subprocess) vs AG-04 (HTTP thật): **ĐỒNG Ý**

| | AG-02 | AG-04 |
|---|---|---|
| Đường đo | `subprocess` gọi thẳng hàm, N = 1·2·4·8 | **hai tiến trình `app/server.py` THẬT**, bắn xen kẽ qua HTTP |
| Số khai | trần thực = khai báo **× số bản** | 1 bản **10** · 2 bản **20** ⇒ **2,0×** |

**Tôi đã làm gì khác**: dựng harness **của tôi** và đo trên **một tuyến KHÁC** —
`auth.dang_nhap` (trần `dinh_danh` 12/300 s) thay vì `webhook.chu_ky_sai` (10/60 s) mà AG-04 dùng.
Không dùng lại mã của ai. Đo trên **ba nhánh**, mỗi nhánh dùng **tiến trình máy chủ MỚI** (bộ đếm
trần nằm trong bộ nhớ tiến trình, nên dùng lại tiến trình cũ là đo nhầm):

```
[C1] trần khai báo `auth.dang_nhap` = 12 (đọc từ CHÍNH SÁCH, không viết cứng)
[C2] gọi thẳng hàm (tiến trình sạch) : 12 lượt qua rồi chặn
[C3] HTTP 1 tiến trình máy chủ THẬT  : 12 lượt qua rồi 429   ⇒ BẰNG đường hàm
[C4] HTTP 2 tiến trình (xen kẽ)      : 24 lượt qua           ⇒ TỈ LỆ 2,0×
```

⇒ **ĐỒNG Ý với cả AG-02 lẫn AG-04**, trên một tuyến khác, bằng một harness khác. Kết luận
`B-G11-10` **tái lập được độc lập lần thứ ba**.

### 4.4 "HTTP khớp tuyệt đối với gọi thẳng hàm" và "trần NHÂN theo số bản" — **cùng đúng**

Đây là câu hỏi của đề bài, và câu trả lời nằm ở chỗ **hai câu nói về hai PHẠM VI khác nhau**:

* **Trong MỘT tiến trình**: đường đi (HTTP hay gọi thẳng hàm) **không đổi con số** — `12 == 12`
  (`[C3]`). Đây là điều AG-04 §5 khẳng định, và nó **đúng**.
* **Qua NHIỀU tiến trình**: mỗi bản có **ngân sách riêng** bằng đúng khai báo, nên tổng **nhân lên**
  — `12 → 24` (`[C4]`). Đây là điều AG-02 §2 và AG-04 §6.1 khẳng định, và nó **cũng đúng**.

Không có mâu thuẫn nào: phép **BẰNG** đúng ở phạm vi một tiến trình, phép **NHÂN** đúng ở phạm vi
nhiều tiến trình, và **cả hai đo trên cùng một tuyến trong cùng một lượt chạy** (`[C5]`).
Cơ chế: `gioi_han` PHẦN A giữ bộ đếm trong **bộ nhớ tiến trình**; `ThreadingHTTPServer` chỉ chia
luồng trong **một** tiến trình, nên nó không đụng tới bộ đếm của tiến trình khác.

### 4.5 AG-02 (`http_jt` an toàn qua tiến trình) vs AG-05 (đọc-rồi-ghi mất cập nhật) — **KHÔNG mâu thuẫn**

Hai câu này nói về **hai tầng khác nhau**. Tôi chỉ ra ranh giới bằng **cấu trúc** và bằng **một
phép đo mất cập nhật tất định**:

**Cấu trúc** — cùng một phép quét AST, quét ba mô-đun:

```
[D1] app/http_jt.py  : 25 tên mức mô-đun · 2 dict hằng · 0 dấu hiệu GHI
[D2] app/gioi_han.py : 10 dấu hiệu GHI ⇒ _lan[…] · _chan_den[…] · _lan.clear() · _chan_den.pop() · global
[D3] csdl.khoa_ghi   = RLock (khoá TRONG tiến trình) · chú thích "KHÔNG phủ nhiều tiến trình" còn nguyên
```

**Hành vi** — khuôn đọc-rồi-ghi `mot()` + `ghi()`, **hai tiến trình thật**, mỗi tiến trình
đọc-rồi-ghi **một lần** (kỳ vọng ra `2`):

```
[D4] NGOÀI `giao_dich()` : giá trị cuối = 1  ⇒ MẤT 1 CẬP NHẬT, IM LẶNG (không ngoại lệ, không mã lỗi)
[D5] TRONG `giao_dich()` : giá trị cuối = 2  ⇒ KHÔNG mất
```

**Ranh giới ở đâu — trả lời thẳng:**

| Tầng | Mô-đun | Trạng thái dùng chung? | An toàn qua tiến trình? |
|---|---|---|---|
| VẬN CHUYỂN (HTTP tới hãng) | `app/http_jt.py` | **Không có** (0 dấu hiệu ghi) | **CÓ** — AG-02 đúng |
| TRẦN TẦN SUẤT PHẦN A | `app/gioi_han.py` | **Có** (`_lan`, `_chan_den` trong bộ nhớ) | **KHÔNG** — trần × N |
| LƯU TRỮ (đọc-rồi-ghi) | `app/csdl.py` | `khoa_ghi` là **RLock** ⇒ chỉ trong tiến trình | **KHÔNG** — mất cập nhật im lặng (AG-05 đúng) |

⇒ **Không mâu thuẫn.** AG-02 nói về **tầng vận chuyển**, AG-05 nói về **tầng lưu trữ**, và
AG-02 **đã tự nêu đúng ranh giới ấy** ngay trong bình luận của nó trong `http_jt.py`
("Cái KHÔNG an toàn nằm ở lớp khác: `gioi_han` PHẦN A … và `csdl.khoa_ghi` là RLock nên không phủ
tiến trình"). `app/csdl.py` cũng tự ghi: *"KHÔNG phủ nhiều tiến trình — chỗ đó phải đo riêng"*.

**Cảnh báo cách đọc** (đây là chỗ dễ sai nhất khi GỘP): ghép hai câu lại thành
*"G18 đã làm hệ an toàn qua nhiều tiến trình"* là **SAI**. Đúng phải là: *"G18 đã đo và **chỉ ra**
ba tầng, trong đó **hai tầng vẫn KHÔNG an toàn** qua nhiều tiến trình"*. AG-05 chính là phép đo
lượng hoá cho tầng thứ ba.

---

## 5. LỖ HỔNG TÍCH HỢP TÌM THẤY (việc 4)

**Tổng hợp — đọc bảng này trước:**

| # | Phát hiện | Loại | Mức | Hành động đề nghị (AG-00) |
|---|---|---|---|---|
| 5.1 | Gộp `http_jt.py` giữ **đủ** cả AG-02 và AG-03 | ✅ **ĐẠT** | — | không cần gì |
| 5.2 | Bình luận AG-02 khai `20 tên mức mô-đun`, cây gộp có **25** | ⚠️ số đo cũ trong mã sản phẩm | nhẹ | sửa một từ trong `app/http_jt.py` |
| 5.3 | `duong_platform()` gộp nhóm chọn thành `1` ⇒ **1 đường không tồn tại** | ⚠️ dụng cụ đo nói quá phạm vi | nhẹ | mở nhóm chọn như `_mo_rong` |
| 5.4 | Con số `41` trong tài liệu là **artefact**; số đúng **73/104** | 📌 con số không đo lại được | nhẹ | ghi lại mốc kèm cách so |
| 5.5 | Ba cặp kết luận trông mâu thuẫn | ❌ **KHÔNG mâu thuẫn** | — | không cần gì |
| 5.6 | Vân tay AG-00 không tái lập được; công thức vân tay **mù** với tệp mới | ⚠️ hạ tầng đo | nhẹ | ghi kèm công thức + băm tệp |
| 5.7 | Cổng "cây sạch" của mỗi làn chỉ miễn trừ tệp của chính làn đó | ⚠️ hạ tầng đo (đỏ giả) | nhẹ | commit 2 tệp, hoặc nới mẫu |

**Không tìm thấy lỗi LOGIC nào trong sản phẩm đã gộp.** Nói thẳng: không có bằng chứng nào cho
thấy việc gộp sáu làn làm hỏng hành vi. **Năm** phát hiện (5.2, 5.3, 5.4, 5.6, 5.7) đều thuộc
**dụng cụ đo / tài liệu**, không thuộc mã chạy.

### 5.0 Quét HỆ THỐNG trước: tệp nào bị **nhiều làn cùng sửa**?

Rủi ro gộp chỉ nằm ở tệp bị **≥ 2 làn** cùng sửa. Tôi liệt kê mọi tệp **không phải `docs/`** mà
từng làn đổi so với **mốc chung** `7b741c88b3b280d65f80b5e11301f17ebd767b26`
(`git merge-base` của cả sáu nhánh — cũng đúng là `VIP_G18_HEAD` mà `thu_qa_g18` ghim):

| Làn | Tệp SẢN PHẨM đã đổi | Tệp thử / harness đã đổi |
|---|---|---|
| AG-01 | *(không có)* | `app/thu/thu_qa_g18.py` |
| AG-02 | **`app/http_jt.py`** | `app/thu/stub_jt.py`, `app/thu/thu_g18_multiprocess.py` |
| AG-03 | **`app/http_jt.py`** | `app/thu/thu_g18_bi_mat.py` |
| AG-04 | *(không có)* | `app/thu/thu_g18_maysrv.py`, `trien_khai/g18/**` |
| AG-05 | *(không có)* | `app/thu/thu_postgres.py`, `trien_khai/postgres/**` |
| AG-06 | *(không có)* | `app/thu/thu_g18_crash.py`, `trien_khai/g18-crash/**` |

**Kết quả: `app/http_jt.py` là tệp SẢN PHẨM DUY NHẤT bị hai làn cùng sửa.** Bốn làn còn lại
(AG-01, AG-04, AG-05, AG-06) **không đụng một dòng mã sản phẩm nào** — chúng chỉ thêm tệp thử và
harness. Nghĩa là **toàn bộ rủi ro gộp của G18 nằm gọn ở một tệp**, và §5.1 kiểm chính tệp đó
bằng sáu đường độc lập. Đây là tin tốt, nhưng phải **đo** mới nói được — không suy ra từ việc
"các làn báo cáo xanh".

### 5.1 ✅ ĐÃ KIỂM — việc gộp `app/http_jt.py` **KHÔNG làm mất** thay đổi nào

AG-02 (+16 dòng) và AG-03 (+275 dòng) sửa **cùng một tệp, cùng một vùng bình luận**. Đây là chỗ
hỏng-im-lặng kinh điển: chọn một trong hai thì **bộ thử của làn bị bỏ vẫn XANH**, vì nó chỉ nhìn
phần của mình. Tôi kiểm bằng **sáu đường độc lập**:

| Đường kiểm | Kết quả |
|---|---|
| **Từng dòng**: mọi dòng AG-02 **thêm** (`git show a9f076b`) còn trong `HEAD` | **16/16 còn** |
| **Từng dòng**: mọi dòng AG-03 **thêm** (`git show d23d875`) còn trong `HEAD` | **275/275 còn** |
| **Ký hiệu + bình luận** (`[A1]`–`[A3]`) | 5/5 ký hiệu AG-03 · 3/3 câu chốt AG-02 · ghi chú gộp AG-00 — **còn nguyên** |
| **Định nghĩa trùng** (`[A4]`) | **0** định nghĩa bị lu mờ · `_gia_tri_can_che` đúng **1** định nghĩa |
| **Hành vi** (`[A5]`, `[A6]`) | bí mật hãng echo lại (header + JSON) **bị che** · bí mật trong **đường dẫn bị che từng đoạn**, endpoint thật **đi qua nguyên vẹn** |
| **Đột biến** (`[A7]`) | thay `mo_ta_yeu_cau` bằng bản in nguyên đường dẫn ⇒ bộ dò **ĐỎ**; khôi phục ⇒ **XANH** (bộ dò có răng) |

> Ghi chú phương pháp: phép so **từng dòng** có **dương tính giả** — 3 dòng ngắn (ví dụ
> `return _mo_rong_bien_the(ra)`) bị báo "còn" dù chúng thuộc hàm khác. Tôi đã kiểm từng ca:
> **cả 3 là dương tính giả**, không phải mã cũ quay lại. Phép so từng dòng chỉ là **sàng lọc**;
> phép phán quyết là **hành vi** (`[A5]`, `[A6]`, và hai bộ thử `thu_g18_bi_mat` 15 ca +
> `thu_g18_multiprocess` 26 ca đều XANH trên cây gộp**).

**Kết luận 5.1: việc gộp ĐẠT.** AG-00 giữ đúng cả hai khối, và tôi xác nhận bằng hành vi, không
chỉ bằng chữ trong bình luận.

**Đối chiếu chéo trên cây gộp (`[E1]`)**: AG-02 đo tính không-trạng-thái trên **nhánh của nó**,
**trước** khi 275 dòng của AG-03 vào cùng tệp — nên tính chất ấy chưa từng được đo lại. Tôi đo
lại: **4 tiến trình thật qua `http_jt`, 4 kết nối TCP riêng biệt, 4 thân trả lời khác nhau,
0 lẫn nhau**. Tính không-trạng-thái **vẫn đúng sau khi gộp**.

### 5.2 ⚠️ LỖI THẬT (nhẹ) — số đo trong `app/http_jt.py` đã **CŨ** sau khi gộp

Bình luận của AG-02 trong `app/http_jt.py` khai: *"quét AST: **20 tên mức mô-đun**, 2 trong đó là
dict HẰNG số cấu hình"*.

| Cây | Số tên mức mô-đun |
|---|---|
| Nhánh AG-02 `a9f076b` | **20** ← lời khai **đúng ở thời điểm đo** |
| Sau AG-03 `d23d875` | **25** |
| `integration/g18` / `HEAD` `626d422` | **25** |

AG-03 thêm **đúng 5 tên** (`TRUONG_CREDENTIAL_PHAN_HOI`, `DOAN_DUONG_DAN_DAI_TOI_THIEU`,
`DOAN_DUONG_DAN_KHAC_NHAU_TOI_THIEU`, `_CHUOI_DOAN_HOP_LE`, `_MAU_CAP_TEN_BI_MAT`) cùng 275 dòng.
AG-00 gộp bình luận **nguyên văn**, nên **mã sản phẩm đang mang một số đo không còn đúng với
chính tệp chứa nó**.

* **Mức độ**: nhẹ — đây là **bình luận**, không phải logic. **Kết luận chịu lực vẫn ĐÚNG**: tôi
  đo lại độc lập trên cây gộp được **0 dấu hiệu GHI** (`[A8]`, `[D1]`), và **2 dict hằng** vẫn
  đúng là 2.
* **Vì sao vẫn đáng ghi**: người sau đọc bình luận để **kiểm lại** tính không-trạng-thái sẽ đếm ra
  25, thấy lệch với lời khai 20, và **mất niềm tin vào cả khối** — hoặc tệ hơn, tưởng mình đếm sai.
  Đây đúng là loại lỗi **chỉ hiện ra khi gộp**.
* **Đề nghị** (không tự sửa — tôi là người kiểm): AG-00 sửa con số trong `app/http_jt.py` thành
  **25** (hoặc ghi rõ mốc đo "20 tên, đo trên nhánh AG-02 trước khi gộp AG-03"). Sửa **một từ**.
* Bộ thử của tôi **in ra cảnh báo** ở `[A8]` nhưng **không đỏ**: kết luận chịu lực vẫn đúng, và
  biến cổng hồi quy chung thành đỏ vì một con số trong bình luận sẽ làm người sau **bỏ qua màu đỏ**
  — đúng cái §12.2 dặn tránh. Phát hiện nằm ở đây, và ở dòng `[A8]` của bộ thử.

### 5.3 ⚠️ LỖI THẬT (nhẹ) — bộ trích `duong_platform()` của AG-01 sinh **một đường KHÔNG TỒN TẠI**

`thu_qa_g18.duong_platform()` thay **mọi** nhóm `(…)` bằng ký tự `1`:

```
/api/v2/platform/tenants/(\d+)/(khoa|mo|goi)   →   /api/v2/platform/tenants/1/1   ← KHÔNG TỒN TẠI
```

`[B5]` đo được: `duong_platform()` sinh **8** đường, trong đó **1** đường không tồn tại.
Ca `F1` của `thu_qa_g18` **vẫn XANH** — nhưng xanh vì `server.py` dòng 566 chặn theo **TIỀN TỐ**
(`duong.startswith("/api/v2/platform/")`) **TRƯỚC** khi khớp route, nên **mọi** URL
`/api/v2/platform/*` đều trả 403 với phiên không phải platform, kể cả URL bịa. Nghĩa là dòng
`/tenants/1/1` trong danh sách phủ **không đo route thật** nào.

* **Hệ quả**: phủ V5 mặt `/platform/*` của AG-01 **hụt 1 mục** so với khai báo. Route thật
  `/api/v2/platform/tenants/{id}/(khoa|mo|goi)` **không** được ca F1 chạm tới. (AG-06 **có** đo
  route này trong bảng cửa của nó.)
* **Hướng sai**: đây là **nói quá** phạm vi đã đo — hướng nguy hiểm theo §12.1 luật 3, dù mức độ nhỏ.
* **Đề nghị**: AG-00 sửa `duong_platform()` để **mở nhóm chọn** (như `_mo_rong` của AG-06) thay vì
  thay bằng `1`. Bộ thử của tôi in ra ở `[B5]`; tôi **không** tự sửa mã của làn khác.

### 5.4 📌 PHÁT HIỆN — con số `41` (xem §4.2)

Không phải lỗi mã, mà là **một con số không đo lại được** đang lưu trong `docs/OWNER_ACTIONS.md`.
Số đúng theo cách so đúng: **73/104**, khoảng trống **31 route**.

### 5.5 ❌ BA CẶP KẾT LUẬN TRÔNG MÂU THUẪN — **KHÔNG mâu thuẫn**, và tôi đã THỬ PHÁ

Đề bài yêu cầu nói rõ **đã thử phá bằng cách nào** nếu không tìm thấy lỗ hổng. Ba cặp bị nghi:

| Cặp bị nghi | Cách tôi THỬ PHÁ | Kết quả |
|---|---|---|
| AG-04 "HTTP khớp tuyệt đối với gọi thẳng hàm" ⟷ AG-02 "trần nhân theo số bản" | Đo **cả hai** trên **cùng một tuyến** (`auth.dang_nhap`), ba nhánh, tiến trình mới mỗi nhánh | **Không phá được** — `12==12` và `12→24` cùng đúng (`[C3]`–`[C5]`) |
| AG-02 "lớp HTTP an toàn qua tiến trình" ⟷ AG-05 "đọc-rồi-ghi mất cập nhật" | Quét AST ba mô-đun + đo mất cập nhật 2 tiến trình, có **đối chứng âm** (`giao_dich()`) | **Không phá được** — khác tầng; ranh giới = **dòng tiến trình** (`[D1]`–`[D6]`) |
| AG-00 gộp hai khối bình luận xung đột trong `http_jt.py` | Kiểm từng dòng + ký hiệu + **hành vi** + **đột biến** | **Không phá được** — cả hai thay đổi còn nguyên và còn tác dụng (`[A1]`–`[A7]`, `[E1]`) |

**Tôi đã THỬ PHÁ thêm ở ba chỗ nữa** (đây là phần "nếu không tìm thấy thì đã thử gì"):

1. **Đột biến có chủ đích** `mo_ta_yeu_cau` để chứng minh bộ dò rò rỉ **có răng** (`[A7]`) —
   nếu không có ca này thì một hàm bị vô hiệu hoàn toàn vẫn làm `[A6]` xanh.
2. **Nghi ngờ định nghĩa trùng** do gộp: `_gia_tri_can_che` xuất hiện **6 lần** trong tệp nên
   rất dễ có hai `def`. Quét AST toàn tệp: **0 định nghĩa trùng** (`[A4]`).
3. **Nghi ngờ 275 dòng của AG-03 phá tính không-trạng-thái của AG-02**: quét AST (**0 dấu hiệu
   GHI**) + **4 tiến trình thật** qua `http_jt` sau khi gộp (`[E1]`).

### 5.6 ⚠️ LỖI THẬT (nhẹ) — vân tay cây của AG-00 **không tái lập được**, và công thức vân tay **mù với nội dung tệp mới**

Hai chuyện, cùng một gốc: **dụng cụ đo phải đo lại được**.

1. AG-00 ghi vân tay `e5df72e93bd647d1`. Tôi **không** tái lập được bằng lệnh đã cho (sha256 ra
   `1cf4d248…`; thử thêm sha1 `c56a0083…` và md5 `182d833b…` — không khớp). Nhiều khả năng AG-00
   dùng **công thức băm khác** nhưng **không ghi kèm**. Hệ quả: hai vân tay **không so được với
   nhau** — đúng bài học `N-G18-00`. Điều **vẫn kiểm được**: TRƯỚC = SAU theo **cùng một lệnh**.
2. Công thức `{ git ls-files -s; git status --porcelain=v1; } | shasum -a 256` **không phủ nội
   dung tệp chưa theo dõi**. Đo được: sửa nội dung `app/thu/thu_qa_g18_tich_hop.py` **không** làm
   vân tay đổi (`78eeaa98…` giữ nguyên), vì `git status --porcelain` chỉ in **đường dẫn** `??`.
   ⇒ Vân tay canh được "thêm/sửa/xoá **tệp đã theo dõi**", **không** canh được nội dung tệp mới.
   Bù bằng băm nội dung (§7.5).

**Đề nghị**: ghi kèm **công thức** mỗi lần báo vân tay; và với tệp mới thì ghi thêm `shasum -a 256`
của chính tệp.

### 5.7 ⚠️ LỖI THẬT (nhẹ, thuộc HẠ TẦNG ĐO) — cổng "cây sạch" của mỗi làn **chỉ miễn trừ tệp của chính làn đó**

Đo được ở §3.4: thêm **hai tạo tác nghiệm thu** của lượt này làm **hai cổng F0-a của làn KHÁC**
(`thu_qa_g17.py`, `thu_qa_g18.py`) đỏ, với thông điệp **đúng** là "cây có thay đổi NGOÀI hai tệp
AG-01". Cơ chế: mỗi bộ miễn trừ theo **mẫu tên của chính nó** —

```python
MAU_TEP_CUA_AG01_G17 = ("app/thu/thu_qa_g17*.py", "docs/QA_G17*.md")   # thu_qa_g17.py
```

— nên tạo tác của làn khác (hoặc của **lượt sau** cùng làn) **luôn** bị tính là cây bẩn.

* **Mức độ**: nhẹ, và **tự hết khi commit** (§3.4 đã đo: trên cây đã commit, cả hai bộ đều XANH).
  Không phải lỗi sản phẩm, không phải hồi quy.
* **Vì sao vẫn đáng ghi**: nó tạo ra **đỏ giả** ở cổng chung đúng vào lúc có người đang giao tạo
  tác mới — thời điểm dễ kết luận sai nhất. Một cổng chống "cây bẩn" mà **không phân biệt được**
  "người khác sửa mã sản phẩm" với "đồng nghiệp vừa thêm một tệp thử" thì đang canh **sai thứ**.
* **Đề nghị** (không tự sửa — tôi là người kiểm): hoặc (a) commit hai tệp này (hết đỏ ngay), hoặc
  (b) đổi mẫu miễn trừ thành "mọi tệp `app/thu/thu_*.py` + `docs/QA_*.md` **mới thêm**", hoặc
  (c) — tốt nhất — cổng chỉ tố khi có tệp **ĐÃ THEO DÕI** bị **SỬA/XOÁ**, và **ghi ra** (không
  phán) khi có tệp mới chưa theo dõi. Việc (c) giữ đúng răng của cổng mà bỏ hẳn đỏ giả.

---

## 6. CHƯA ĐO — NÓI THẲNG (kể cả thứ KHÔNG THỂ kiểm trong worktree này)

| # | Chưa đo | Vì sao |
|---|---|---|
| 1 | **Tầng 3 — DOM/CSS trong Chromium thật** (`thu_giao_dien/chay.sh`) | Bộ chạy chung **cố ý** không chạy nó (cần Chromium + máy chủ sống, ~34 s, và phải chạy bằng đúng bộ chạy của nó). Lượt này tôi **không** chạy. Số cũ của AG-01 lượt 1: 26 đạt · 1 bỏ qua, **và AG-01 ghi nó "CHẬP CHỜN"** — nên **không** coi là đã đo lại. |
| 2 | **Cụm `dong_thoi/chay.py` — bộ đa tiến trình riêng của dự án** | Không nằm trong `chay_tat_ca.sh`. Tôi đo đa tiến trình bằng **harness tự viết** (`[C4]`, `[E1]`) và bằng harness của AG-04, **không** chạy cụm này. |
| 3 | **PostgreSQL cho CSDL NGHIỆP VỤ** | AG-05 chỉ thử **schema + đường ghi** trên **cụm tạm 55432**. CSDL nghiệp vụ **chưa** chuyển sang PostgreSQL. Chốt `D-8`: **không** migration DB nghiệp vụ. |
| 4 | **Hãng thật / sandbox thật** | `CHO_PHEP_MOI_TRUONG = {mock: True, sandbox: False, production: False}`. Mọi phép đo đi qua stub/loopback. **Không** gọi API hãng, kể cả sandbox. **Không** credentials thật, **không** `.env`. |
| 5 | **Mã `110` (ánh xạ `area`)** | Chưa xác minh ⇒ **NEEDS_REVIEW**; chốt `D-9` **khoá cứng** city/area ở mọi chế độ khác `mock`. Lượt này **không** đoán URL/mapping hãng. |
| 6 | **Trần 5432 / cụm PostgreSQL hệ thống** | **Cấm dùng.** Cổng 5432 đang bị một `postgres` hệ thống giữ; AG-05 từ chối chạy trên 5432 và tôi chạy trên 55432. **Không** đo gì trên cụm hệ thống. |
| 7 | **Tunnel / deploy / push** | **Không làm**, theo chốt. |
| 8 | **`VIP_G18_DAY_DU=1`** (làn đầy đủ của `thu_qa_g18`, ca `H_Postgres`) | **1 ca BỎ QUA** trong lượt này (`skipped=1`). Lượt này chạy làn **mặc định**. |
| 9 | **Nhiều máy / nhiều tiến trình qua MẠNG thật** | Mọi phép đa tiến trình đều trên **một máy, loopback**. Trần × N chỉ được đo trên loopback. |
| 10 | **Hai bộ đo V5 ở 31 route còn lại** | AG-06 **đã** đo và thấy kín; nhưng đó là **một** dụng cụ. Lượt này **không** tạo dụng cụ thứ ba cho 31 route ấy. |
| 11 | **Soát hết mọi khối đọc-rồi-ghi trong `app/`** | AG-05 §"Chưa đếm" nói thẳng: **chưa đếm** bao nhiêu chỗ dùng khuôn đọc-rồi-ghi **ngoài `giao_dich()`**. Tôi **xác nhận khuôn đó mất cập nhật thật** (`[D4]`), nhưng **không** đếm hết số chỗ. |

---

## 7. CHẠY LẠI

### 7.1 Bộ thử độc lập của lượt này (26 ca · ~3,4 s)

```sh
python3 app/thu/thu_qa_g18_tich_hop.py
# → Ran 26 tests … OK   (mã thoát 0)
```

### 7.2 Hồi quy toàn phần — hai lượt, hai mục đích

```sh
# LƯỢT 1 — CÂY SẠCH (đúng yêu cầu đề bài: "trên ĐÚNG commit này")
sh app/thu/chay_tat_ca.sh
# → python 1605 ca · 43 bộ chạy thật · 0 bộ hỏng · E2E 41/41 · EXIT=0

# LƯỢT 2 — SAU khi hai tệp mới của lượt này ra đời (kiểm tệp mới có phá cổng chung không)
sh app/thu/chay_tat_ca.sh
# → python 1631 ca · 44 bộ chạy thật · 2 bộ hỏng (thu_qa_g17.py · thu_qa_g18.py) · EXIT=1
#   tệp mới:  ✓ thu_qa_g18_tich_hop.py 26 ca
#   nguyên nhân 2 bộ đỏ: xem §3.4 — đỏ TẠM THỜI do tệp CHƯA COMMIT, hết khi commit
```

### 7.3 Vân tay cây

```sh
{ git ls-files -s; git status --porcelain=v1; } | shasum -a 256
```

| Mốc | Giá trị |
|---|---|
| TRƯỚC (cây sạch `626d422`) | `1cf4d24886eb6b1ebbeb5ebe446472ac7ea76567e16587c39dcaa88d21142713` |
| SAU hồi quy, chưa thêm tệp | `1cf4d24886eb6b1ebbeb5ebe446472ac7ea76567e16587c39dcaa88d21142713` (BẰNG) |
| SAU khi thêm hai tệp của lượt này | `78eeaa9860700f20d9a3521b22b15f5cc10f2ee1ba6a7df7f53eec957652cd5d` |

Delta của vân tay SAU **chỉ** gồm hai dòng `??`:

```
?? app/thu/thu_qa_g18_tich_hop.py
?? docs/QA_G18_INTEGRATED.md
```

**Không tệp nào khác bị đổi.** Mọi phép đo ở §2–§4 chạy **trước** khi hai tệp này ra đời, nên
chúng đo **đúng cây `626d422` sạch**.

### 7.4 Chạy riêng sáu bộ G18 (mã thoát đọc TRƯỚC pipe)

```sh
python3 app/thu/thu_g18_multiprocess.py          # EXIT=0 · 26 ca — ĐẠT
python3 app/thu/thu_g18_bi_mat.py                 # EXIT=0 · Ran 15 · OK
python3 app/thu/thu_g18_maysrv.py                 # EXIT=0 · Ran 17 · OK
VHPG_CONG=55432 python3 app/thu/thu_postgres.py   # EXIT=0 · Ran 55 · OK   (CẤM 5432)
python3 app/thu/thu_g18_crash.py                  # EXIT=0 · Ran 31 · OK
python3 app/thu/thu_qa_g18.py                     # EXIT=0 · Ran 43 · OK (skipped=1)
VIP_HUB_DATA=/tmp/nen_ag04 sh trien_khai/g18/chay_harness.sh
                                                  # EXIT=0 · 18/20 đạt · 0 hỏng · 0 BLOCKED · 2 bỏ qua
```

**Cách lấy mã thoát (nguyên văn khuôn đã dùng — mã thoát đọc TRƯỚC mọi pipe):**

```sh
python3 app/thu/thu_g18_bi_mat.py > /tmp/log 2>&1
MA=$?                       # ← ĐỌC Ở ĐÂY, trước khi grep/head/tail
grep -E "^Ran [0-9]+|^OK|^FAILED|skipped" /tmp/log
```

Không dùng `python3 … | tail` rồi đọc `$?`, vì `$?` khi đó là mã thoát của **pipe cuối**, không
phải của bộ thử.

### 7.5 Vân tay **KHÔNG** phủ nội dung tệp mới — nên ghi kèm băm nội dung

Đo được: sửa nội dung `app/thu/thu_qa_g18_tich_hop.py` **không** làm vân tay đổi một ký tự
(vẫn `78eeaa98…`), vì `git ls-files -s` chỉ liệt kê tệp **đã theo dõi**, còn `git status
--porcelain` chỉ in **đường dẫn** của tệp chưa theo dõi — **không** in nội dung.

⇒ Vân tay cây đủ để canh "có ai đó sửa/ thêm/ xoá tệp không", **không** đủ để canh nội dung của
tệp mới. Bổ sung băm nội dung cho tệp mới của lượt này:

```sh
shasum -a 256 app/thu/thu_qa_g18_tich_hop.py
# → 45062d66a0be65b6841ef7584afebdd36fd1164df0dfa27b8d7fc9ee91fbd5bf
```

(`docs/QA_G18_INTEGRATED.md` là **chính tài liệu này**, nên băm của nó không tự ghi vào chính nó
được — sửa một chữ là băm đổi. Ai cần thì băm lại tại chỗ.)

---

## 8. GIỚI HẠN CỦA CHÍNH TÀI LIỆU NÀY

1. **Toàn bộ là tác tử AI.** Không có người kiểm độc lập nào khác. Lượt này **không** thay thế
   nghiệm thu của Owner.
2. **Hai tệp được ghi là TỆP MỚI.** Tôi **không** sửa một dòng mã sản phẩm nào — đúng ràng buộc
   "NGƯỜI KIỂM, không phải người viết". Mọi phát hiện ở §5 là **đề nghị**, chưa được sửa.
3. **Cả năm phát hiện ở §5.2, §5.3, §5.4, §5.6, §5.7 đều là mức NHẸ** (ba con số, một bộ trích
   dùng cho danh sách phủ, và hai chỗ ở hạ tầng đo). **Không** tìm thấy lỗi logic trong sản phẩm
   đã gộp. Nói thẳng: **không** có bằng chứng nào cho thấy việc gộp làm hỏng hành vi.
4. **Phép so tập route ở §4.1 phụ thuộc bộ chuẩn hoá.** Tôi đã tự kiểm nó khớp bộ của AG-06
   (`[B0]`), nhưng nó vẫn là **một** cách chuẩn hoá; một cách khác có thể cho con số hơi khác.
   Điều **không** phụ thuộc cách chuẩn hoá: **104 ⊃ 73** và **khoảng trống 31 route là thật**.
5. **`[D4]`/`[D5]` đo trên SQLite**, không phải PostgreSQL (AG-05 mới là bên đo cả hai kho).
   Kết luận "mất cập nhật im lặng" ở đây **chỉ** phát biểu cho kho mặc định của lượt chạy này.
6. **Con số `1605 ca` là số ca ĐÃ CHẠY**, không phải số ca tồn tại: một ca của `thu_qa_g18` bỏ qua
   ở làn mặc định (§6 mục 8).
7. **Hai lượt hồi quy cho hai con số khác nhau** (1605/43/0 hỏng và 1631/44/2 hỏng) — **cả hai
   đều đúng**, vì chúng đo **hai cây khác nhau**: cây sạch `626d422`, và cây đó **cộng hai tệp
   chưa commit**. Không được lấy con số này thay con số kia. Yêu cầu của đề bài ("trên ĐÚNG commit
   này") ứng với **lượt 1**.
8. **Tôi KHÔNG commit, KHÔNG push, KHÔNG sửa mã sản phẩm.** Hai tệp của lượt này để ở trạng thái
   `??` (chưa theo dõi) — đó là lý do §3.4 xảy ra. Việc commit thuộc AG-00/Owner.
