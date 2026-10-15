# NGHIỆM THU TẦNG 3 — kiểm giao diện bằng Playwright

Chỉ thị G12 mục 1, 3, 19. Nghiệm thu bởi **AG-00**, ngày **15/10/2026**.
Tài liệu kỹ thuật của bộ thử: **[G12_PLAYWRIGHT.md](G12_PLAYWRIGHT.md)** (355 dòng, AG-02).

## 1. Quyền — đã được cấp

Quyết định **D-1**, anh Thành, 14/10/2026: *"Đồng ý Playwright, cài riêng trong dự án"*.

Hợp đồng `SHARED_CONTRACTS.md` §25 mục `V-13906-01` đã sửa từ **CHƯA CẤP** sang **ĐÃ CẤP**.
Dòng đó lạc hậu từ lượt gộp AG-02 cho tới 15/10 — một lời nói sai về chính hệ thống, và nó
không báo lỗi gì cả.

## 2. AG-00 CHẠY LẠI THẬT, không tin báo cáo

| Phép đo | Kết quả |
|---|---|
| lượt chạy từ nhánh `main` sau khi gộp | **26 đạt · 1 bỏ qua · 0 hỏng** |
| mã thoát `thu_giao_dien/chay.sh` | **0** |
| thời gian | **33,6 giây** |
| khớp số AG-02 báo | **có** |

Chạy được từ `main` bằng cách **nối** `node_modules` từ worktree của AG-02 (498MB, 869 tệp —
không tải lại) cộng `PLAYWRIGHT_BROWSERS_PATH=0`, biến mà `chay.sh` đã đặt sẵn.

**Em KHÔNG tin tệp `INSTALLATION_COMPLETE`** — thử `chromium.launch()` thật trước. Lượt đầu
**HỎNG** vì chạy không có biến môi trường nên nó đi tìm ở cache hệ thống. Cache hệ thống
(`~/Library/Caches/ms-playwright/`) có chromium **1148** và **1243** **của dự án khác**;
AG-02 cài bản **1194** vào `node_modules/playwright-core/.local-browsers/`.
**Không dùng cache hệ thống, không chạm vào nó.**

## 3. Chặn 498MB không lọt vào Git

Đo **trước** khi mừng: `node_modules` **chưa** lọt vào git (0 trong lịch sử, 0 theo dõi), và
commit `cccd275` của AG-02 sạch (160 tệp, 0 `node_modules`). Nhưng `.gitignore` **chưa chặn**,
nên một lượt `git add -A` là đưa 498MB vào lịch sử — mà lịch sử Git thì không xoá sạch được.

Đã thêm **cả hai** dạng: `node_modules/` **và** `node_modules` (không gạch chéo). Mẫu có gạch
chéo khớp **thư mục** chứ không khớp **symlink**, và lượt chạy lại từ `main` dùng symlink.

**Cố ý KHÔNG chặn `package-lock.json`** — đó là chỗ duy nhất ghi `@playwright/test` khoá ở
bản nào (**1.56.1**). Thiếu nó thì hai máy cài hai bản khác nhau, và lúc đó một bộ thử xanh ở
máy này đỏ ở máy kia mà không ai giải thích được. Đã kiểm `git check-ignore -v`: không bị chặn.

## 4. Gộp — kiểm quyền sở hữu trước

| Phép đo trên nhánh AG-02 `cccd275` | Kết quả |
|---|---|
| gốc chung (`git merge-base`) | `9af8115` — đúng nhánh nền |
| tệp cũ bị sửa | **0** |
| vi phạm bảng quyền sở hữu | **0** |
| số tệp | 160, trong đó 0 `node_modules` |

Gộp xong kiểm lại sự hiện diện: 7 tệp `thu_giao_dien/` · `package.json` (12 dòng) ·
`package-lock.json` (78) · `playwright.config.js` (42) · `docs/G12_PLAYWRIGHT.md` (355).
Phép kiểm này **cần thiết** vì trong lúc thử `.gitignore` em đã chạy `rm -rf thu_giao_dien`
(lúc đó thư mục chưa có trong `main` nên vô hại, nhưng phải đo lại mới biết).

## 5. PHẠM VI ĐÃ ĐO — và cái gì NẰM NGOÀI

**Đã đo:** Chromium (bản 1194) · ba khổ màn hình **375 / 768 / 1280** · DOM và CSS tính toán
trong trình duyệt thật · điều hướng bằng bàn phím · 27 ca.

**NẰM NGOÀI, đừng suy ra:**

- **Safari, Firefox, Edge.** Chỉ Chromium.
- **Cảm ứng thật.** Playwright gửi chuột, không gửi ngón tay.
- **Trình đọc màn hình thật** (VoiceOver, NVDA). Ca kiểm bàn phím đo được `tabindex`/`role`,
  nhưng một trang qua được phép đo đó vẫn có thể không dùng nổi bằng trình đọc.
- **In thật.** Không đo bản in.
- **Thiết bị thật.** Khổ màn hình là mô phỏng.
- **Máy chủ dưới tải.** Bộ thử chạy tuần tự, không có người dùng thứ hai.
- **Dữ liệu thật.** Chạy trên CSDL dựng riêng.

## 6. Bộ thử tự phơi ra BA lỗi CỦA CHÍNH NÓ — ghi lại vì cả ba là hỏng im lặng

AG-02 ghi ra, không che:

1. `moMan()` đọc nội dung của màn **TRƯỚC ĐÓ** — lệch đúng một bậc menu. Nếu không lộ ra thì
   **mọi** phép đo tràn ngang của lượt đó cũng sai một bậc mà không ai thấy.
2. Ca *"từ chối đơn"* **tự bỏ qua chính nó** vì `count()` không cho.
3. Phép đo màu lòng `/khác/i` **trùng** `khach_huy`.

Đây là lý do §12.1 tồn tại: thứ dùng để kiểm chứng phải được kiểm **trước khi** tin nó.
Một bộ thử giao diện xanh mà đo lệch một bậc còn tệ hơn không có bộ thử.

## 7. Phát hiện của AG-02 về giao diện — CHƯA SỬA, cần quyết

AG-02 **không sửa** vì `admin/**` không thuộc quyền sở hữu của nó (hợp đồng §22).

### P-1 — **16/17 màn khai ở đợt 3 KHÔNG TỒN TẠI trong giao diện.** Mức: **cao**

Không phải "chưa được nhìn bằng mắt" mà là **không có gì để nhìn**.

Phép đo: `grep` tìm `innerHTML`/`document.` trên năm tệp
`admin/{finance,billing,carrier_health,ai,health}.js` ra **0 ở cả năm** — chúng là logic
thuần, **0 dòng chạm DOM**. Và `grep` tìm `VIPFINANCE`/`VIPBILLING`/… trong `admin.js` ra
**0** — không hàm dựng màn nào tham chiếu tới chúng.

Nghĩa là **năm module của đợt 3 là mã chưa ai gọi**. Tầng 1 kiểm chúng như hàm thuần nên
chúng xanh, nhưng **không người dùng nào với tới được**.

Số thật là **17**, không phải 12 như báo cáo trước của AG-00 — em đếm thiếu.

### P-2 — **Giao diện quản trị KHÔNG dùng được bằng bàn phím.** Mức: **cao**

Đo bằng Chromium thật: cả **10** mục menu và liên kết Đăng xuất là `<a>` **không**
`href`/`tabindex`/`role`; **15 lượt Tab không rời `body`** lần nào.

AG-02 **cố ý chưa thêm ca canh điều này** — thêm vào là bộ thử đỏ ngay mà nó không có quyền
sửa `admin/**`. Đề nghị: thêm ca canh **cùng lượt** với bản vá, không trước.

### P-3 (vừa) · P-4 (thấp)

- `admin/finance.js` dòng 19–20 ghi *"bảy màn G07 CHƯA có đường API nào"* trong khi
  `API_DANG_DUNG_TC` có 17 dòng route đã cắm — chú thích còn lại từ trước lượt cắm route.
- `API_DANG_DUNG_TC` có **2 dòng trùng**, nên "17 route" đếm từ bảng đó **cao hơn thực tế 2**
  — thật ra **15** đường rời nhau.

## 8. Cách chạy lại

```
sh thu_giao_dien/chay.sh
```

Cần `node_modules/@playwright` có mặt. Chưa có thì `npm ci`.
Bộ chạy hồi quy `app/thu/chay_tat_ca.sh` **không** chạy tầng 3 (cần Chromium + máy chủ sống,
~34 giây) nhưng nay **dò sự tồn tại thật** của `node_modules/@playwright` và in đúng trạng
thái — trước 15/10 nó vẫn in *"repo cấm thư viện ngoài nên không có Playwright"*, lạc hậu từ
lượt gộp AG-02.
