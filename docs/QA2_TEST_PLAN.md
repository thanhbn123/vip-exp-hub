# QA2_TEST_PLAN — AG-05 QA / SECURITY VERIFIER, WAVE 1

> **AI-ASSISTED INDEPENDENT WORKSTREAM REVIEW.**
> Đây **KHÔNG** phải independent human review (soát độc lập bởi người). Toàn bộ kế hoạch và ca
> thử dưới đây do một tác tử AI đọc mã và tự sinh ra, chạy trong một làn công việc tách biệt với
> các tác tử đang sửa mã. Chưa có người nào ngoài hệ thống đọc lại. Xem mục 7.

**Ngày đo:** 15/10/2026 · **Worktree:** `~/code/veh2-qa-verification`, nhánh `agent/qa-verification`
**Nền chạy:** macOS Darwin 25.6.0 (MacBook Pro), `Python 3.9.6` (stdlib + `cryptography`)
**Gốc soát:** commit `4016eef8d558d13049ba56a64e219c13c7f1c3f5`
*(AG-00 WAVE 0: đông băng contract đợt 2). Nhiệm vụ ghi nền là `fd7c545`; `fd7c545..HEAD` chỉ
thêm 52 dòng vào `docs/SHARED_CONTRACTS.md`, **không** đổi dòng mã nào — nên hai mốc tương
đương về mặt mã sản phẩm, và báo cáo này ghi mốc THẬT đã chạy.*

**Cổng dùng riêng của AG-05:** `8941` (bộ thử `thu_qa2_soat.py`) · `8942` (lượt E2E).
Chọn cổng riêng vì bốn agent khác đang chạy song song — xem mục 6.

---

## 1. Vì sao có lượt soát thứ hai

`docs/QA_FINDINGS.md` của phiên trước vừa **phát hiện** 14 lỗ hổng vừa là **nơi nghiệm thu** bản
vá của chính 14 lỗ hổng đó (`app/thu/thu_qa_soat.py`: ca `LOHONG` chuyển từ FAIL sang PASS).

`CLAUDE.md` §12.1 luật 1: *thứ dùng để kiểm chứng phải độc lập với thứ được kiểm chứng, và phải
được kiểm trước khi tin.* Một bộ thử tự nghiệm thu bản vá của chính nó không thoả điều đó — nó
chỉ chứng minh "bản vá làm ca thử cũ chuyển xanh", không chứng minh "lỗ hổng đã kín".

Nên `app/thu/thu_qa2_soat.py` **viết lại từ đầu**: harness HTTP riêng, dữ liệu nền riêng, cổng
riêng, và **không `import` gì từ `thu_qa_soat.py`**. Chỗ nào hai bộ trùng kết luận thì là hai
phép đo độc lập cùng ra một kết quả; chỗ nào lệch thì phải xem tay.

---

## 2. Phạm vi — và những gì NẰM NGOÀI phạm vi

| Trong phạm vi | Ngoài phạm vi (ghi rõ để không ai tưởng đã phủ) |
|---|---|
| `app/*.py` (20 file, 4.417 dòng) | Tầng giao diện `pages/`, `admin/admin.js` — chỉ soát ở mức "có lộ bí mật trong file phục vụ công khai không" |
| `gateway/*.py` ở mức bộ thử sẵn có | Nội dung logic gateway (làn của agent khác trong WAVE 1) |
| Cửa HTTP `/api/v2/*` chạy thật | API hãng THẬT — cấm gọi; mọi lượt hãng là adapter `mock` của chính dự án |
| AES-256-GCM, xoay khóa, AAD | Phần cứng bảo vệ khóa (HSM/KMS) — `secret_provider` hiện chỉ là giao diện |
| Đồng thời ở mức **nhiều luồng trong MỘT tiến trình** | Đồng thời ở mức **nhiều tiến trình / nhiều máy** (gunicorn nhiều worker, SQLite trên ổ mạng) — xem `test_r35` |
| Bản vá của 14 phát hiện đợt trước | Bản vá mà bốn agent WAVE 1 khác **đang** viết — AG-05 không thấy worktree của họ |

**Luật của AG-05: phát hiện, KHÔNG vá.** Không dòng mã sản phẩm nào bị sửa. Đo bằng
`git diff --stat` trên 20 file `app/*.py` + `admin/` + `gateway/`: **rỗng**.

---

## 3. Quy ước tên ca thử

| Tiền tố | Nghĩa | Trạng thái mong muốn hôm nay |
|---|---|---|
| `test_rNN_KIN_…` | Chốt một bản vá **còn kín** | **PASS** |
| `test_rNN_LOHONG_…` | Chứng minh một lỗ hổng **chưa vá** | **FAIL** (vá xong phải tự PASS, **cấm sửa assert**) |
| `test_rNN_ANTOAN_…` | Mối lo đã kiểm, kết luận **không phải lỗ hổng**, kèm phạm vi | **PASS** |
| `test_rNN_PHAMVI_…` | Ghi lại phạm vi / đối chứng, **không** phán xét an toàn | **PASS** |

Hai ca `PHAMVI` tồn tại riêng để chặn hai kiểu tự lừa:

- `test_r08_PHAMVI_static_con_phuc_vu_dung_thu_muc_duoc_phep` là **đối chứng dương**. Mọi ca
  "static phải trả 404" sẽ PASS một cách vô nghĩa nếu tầng static chết hẳn. Ca này đòi
  `/admin/index.html` trả 200 trước, nên 404 ở các ca khác mới có nghĩa.
- `test_r35_PHAMVI_…CHUA_tai_hien_duoc_vuot` ghi đúng điều đo được: cấu trúc có rủi ro, phép đo
  trên máy này **không** làm nó vỡ. Nếu đổi thành `LOHONG` thì thành báo cáo sai; nếu đổi thành
  `ANTOAN` thì thành bảo đảm mình không có.

---

## 4. Bản đồ ca thử → câu hỏi nhiệm vụ

### Q01 — baseline, đo thật

| Việc | Cách đo | Bẫy đã tránh |
|---|---|---|
| Đếm số ca thật của 8 bộ thử | `python3 <file>` từng bộ, đọc dòng `Ran N tests` | Không tin con số 184 trong báo cáo cũ — đo lại rồi mới so |
| Lấy mã thoát | `rc=$?` **ngay sau** `python3`, không qua `tail`/`grep` | Đường ống làm `$?` thành mã của lệnh cuối, không phải của `python3` (đã dính lần trước) |
| Segfault ngắt quãng của gateway | chạy **24 lượt**, phân loại từng lượt | Tách `exit=139` (segfault, lỗi sản phẩm) khỏi `Address already in use` (cổng bận do agent khác — **không** phải lỗi sản phẩm) |

### Q02 — xác minh lại 14 bản vá CRITICAL/HIGH

| Nhóm | Ca thử |
|---|---|
| Token đặt lại mật khẩu | `r01` không trả token cho vô danh · `r02` không lộ tài khoản có thật · `r03` một lần + **chống replay 3 lượt** · `r04` hết hạn · `r05` thu hồi mọi phiên cũ · `r06` khóa sai mật khẩu chỉ là khóa TẠM · `r07` thông báo tài khoản bị khóa · `r29` token cũ không bị vô hiệu |
| Static | `r08` đối chứng dương · `r09` 18 đường kín (mã nguồn, `.env`, CSDL, thư mục khóa, `.git`, cấu hình gateway) · `r10` **18 biến thể path traversal** · `r11` khóa/CSDL nằm ngoài thư mục được phục vụ · `r12` quét bí mật trong 4 thư mục trắng |
| Vượt quyền ngang/dọc | `r13` chéo tenant đọc/ghi/xoá 8 cửa · `r14` dùng tài khoản hãng của tenant khác · `r15` VIEWER không ghi 7 cửa · `r16` leo thang vai trò 7 đường · `r17` tenant không vào cửa nền tảng 7 đường · `r18` 404-vs-403 · `r19` hai cửa platform không tra quyền · `r44` chéo tenant 5 cửa import |
| Thu hồi / vô hiệu | `r20` thu hồi phiên · `r21` vô hiệu tài khoản **và** vô hiệu membership · `r22` tenant bị khóa |
| AES-GCM | `r23` 4 kiểu sửa bản mã · `r24` sai khóa + sai AAD + dán key_id lạ · `r25` **đổi chỗ bản mã giữa hai tenant ngay trong CSDL** · `r26` xoay khóa không mất secret, webhook còn ký được |
| Rate limit + hạn mức import | `r27` đăng nhập · `r28` quên mật khẩu · `r33` webhook · `r30`/`r31`/`r32` hạn mức import và body |

**Về rate limiting, AG-00 đo là CHƯA CÓ.** AG-05 kiểm chứng lại bằng hai đường: (a) `grep` toàn
`app/` + `gateway/` tìm `rate.limit|throttle|per_ip|…` → **không khớp dòng nào**; (b) ba ca
`LOHONG` động ở trên bơm 60/40/40 yêu cầu và đòi thấy `429`. **Kết luận: FAIL, không ghi PASS.**

### Q03/Q04 — săn lỗ hổng mới (đọc mã, không chỉ chạy test)

| Hướng | Ca thử |
|---|---|
| Đơn hàng: vòng đời, **đồng thời**, idempotency, lỗi hãng, kết quả không rõ | `r34` **gửi đơn song song gọi hãng hai lần** · `r35` hạn mức gói · `r39` idempotency 6 luồng · `r42` vòng đời 3 cửa · `r43` timeware không bị nhận là thành công |
| Webhook: chữ ký, chống trùng/replay, DLQ, sai thứ tự, sai tenant, **mã J&T 110** | `r36` **webhook không chuẩn hoá mã hãng** · `r37` 6 phép thử chữ ký/trùng/chéo tenant · `r38` sai thứ tự · `r45` nhập nhằng 110 |
| SQL chạm bảng có `tenant_id` mà thiếu điều kiện tenant | `r40` soát tĩnh + **đối chứng động** cho dòng miễn nặng nhất |
| Endpoint quên gọi kiểm quyền | `r41` soát tĩnh `_api_tenant` + đối chứng động |
| Xử lý kiểu dữ liệu lạ | `r48` 5xx trên 5/6 cửa · `r49` thân 500 không lộ chi tiết nội bộ |
| Bí mật không lọt ra ngoài | `r47` 6 cửa API + 3 bảng + `stderr` + cột bản mã |

**Hai công cụ soát tĩnh đều tự khai giới hạn**, theo §12.1 luật 3:

- `r40` chỉ thấy **chuỗi SQL hằng** trong mã, không thấy SQL ghép ở thời gian chạy. Nó gộp các
  chuỗi liền nhau trước khi soát — bản đầu không gộp nên báo **10 báo động giả** (SQL trong mã
  này trải trên nhiều dòng). Danh sách miễn có **11 dòng, mỗi dòng kèm lý do**, và dòng miễn
  nặng nhất (`server.py` + `tenant_memberships`) được **đo động**: tenant B không sửa/xoá được
  membership của tenant A dù biết đúng id.
- `r41` đếm theo **văn bản**, nên một nhánh gọi `_can` trong hàm con sẽ bị báo thiếu. Phải xem
  tay, không tin số máy đếm.

### Q05 — end-to-end

13 bước nghiệp vụ + 1 bước chốt, chạy trên máy chủ thật, cổng `8942`, CSDL thật nằm **trong
worktree này**: `app/du-lieu/qa2-e2e/hub.db`. File Excel là `.xlsx` **thật** (zip + OOXML, kiểm
bằng chữ ký `PK` ở 2 byte đầu), không phải CSV đổi đuôi. Sau **mỗi** bước đọc lại hàng trong
CSDL — không bước nào được nghiệm thu chỉ bằng mã HTTP 200. Chi tiết: `docs/QA2_E2E_EVIDENCE.md`.

---

## 5. Cách chạy lại

```sh
cd ~/code/veh2-qa-verification

# baseline — lấy mã thoát của chính python3
for t in app/thu/*.py gateway/thu/*.py; do
  python3 "$t" >/tmp/qa2-$(basename "$t" .py).log 2>&1
  echo "$(basename "$t") exit=$?"
done

# bộ soát QA2 (cổng 8941). 9 ca LOHONG FAIL là ĐÚNG hôm nay.
python3 app/thu/thu_qa2_soat.py
```

Bộ gateway có tiền sử segfault ngắt quãng, nên đo bằng nhiều lượt chứ không một lượt:

```sh
for i in $(seq 1 24); do
  python3 gateway/thu/thu_gateway.py >/tmp/gw-$i.log 2>&1; rc=$?
  if grep -q "Address already in use" /tmp/gw-$i.log; then k=PORT_BUSY
  elif [ $rc -eq 139 ]; then k=SEGFAULT
  elif [ $rc -eq 0 ]; then k=OK; else k=OTHER_FAIL; fi
  echo "lượt $i exit=$rc $k"
done
```

---

## 6. Luật nhiều phiên song song (CLAUDE.md §16)

Bốn agent khác đang sửa mã trong worktree **riêng** của họ. Những điều AG-05 làm để không giẫm chân:

- **Chỉ ghi trong `~/code/veh2-qa-verification`.** Không chạm `~/Projects/vip-express-hub` hay
  worktree nào khác.
- **Sở hữu đúng hai thứ:** `app/thu/thu_qa2_soat.py` (mới) và `docs/QA2_*.md` (mới).
- **Cổng riêng `8941`/`8942`.** Mọi bộ thử sẵn có bind cổng cố định; chạy chồng là
  `Address already in use`, trông y như lỗi ngắt quãng. Lượt baseline đầu tiên **đã dính đúng
  chuyện đó** (xem `docs/QA2_FINDINGS.md`, R-13).
- **Không push, không deploy, không gọi API hãng thật.**
- **Không `pkill`/`killall` theo mẫu tên** (§16.7). Máy chủ thử dừng bằng `sv.shutdown()` +
  `sv.server_close()` trong chính tiến trình đã tạo nó, nên không cần săn tiến trình theo tên.

---

## 7. Công bố tính độc lập

**AI-ASSISTED INDEPENDENT WORKSTREAM REVIEW.**

- "Independent workstream" nghĩa là: làn công việc tách biệt, worktree riêng, bộ thử viết lại
  không mượn gì từ bộ thử của phiên bị soát.
- Nó **KHÔNG** nghĩa là "independent human review". **Chưa có người nào đọc lại** bản vá hay
  ca thử nào trong tài liệu này.
- Mọi câu "đã kiểm, không phải lỗ hổng" chỉ đúng **trong đúng phạm vi ca thử đã ghi**, không
  phải lời bảo đảm chung.
- Danh sách bản vá bảo mật **cần người rà trước khi lên production**: mục 5 của
  `docs/QA2_FINDINGS.md`.
