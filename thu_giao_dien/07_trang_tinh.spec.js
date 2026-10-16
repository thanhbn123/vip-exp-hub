// TẦNG 3 — MƯỜI TRANG DEMO TĨNH `pages/*.html` (G19 · AG-06): mã của trang có CHẠY không.
//
// VÌ SAO CÓ TỆP NÀY: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có
// `'unsafe-inline'`. Mọi `<script>` NỘI TUYẾN (và mọi thuộc tính `onclick="…"`) bị trình duyệt
// TỪ CHỐI CHẠY. Chín trang `pages/*.html` dựng khung và bảng bằng script nội tuyến, nên chúng
// hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có dòng nào, nút không ai nghe.
// Lỗ hổng này đã được AG-06 ghi ở G17 (`docs/G17_FRONTEND_E2E.md` §"chín trang kia là việc của
// AG-00") và chỉ còn `pages/carriers.html` là được sửa. G19 chuyển nốt chín trang còn lại sang
// tệp `.js` riêng (AG-00 mở rộng phạm vi cho AG-06) — tệp này canh việc đó.
//
// ĐO BẰNG GÌ: đếm `<script>` không `src` TRONG DOM sau khi trang chạy, đếm thuộc tính sự kiện
// nội tuyến, và ĐẾM DÒNG DỮ LIỆU do chính mã trang vẽ ra (không phải dòng có sẵn trong HTML).
// "Không lỗi console" KHÔNG được dùng làm điều kiện đạt: bản cũ không lỗi console nào.
"use strict";
const { test, expect } = require("@playwright/test");
const U = require("./tien_ich");

test.describe.configure({ mode: "serial" });

/* Mỗi trang phải chứng minh mã của nó ĐÃ CHẠY bằng một thứ CHỈ mã ấy tạo ra được.
   Ghi rõ nguồn của từng phép đếm — nếu bộ chọn trỏ vào thứ có sẵn trong HTML thì ca này
   không đo gì cả:
     · `#bang-nhap` và `#vung-buoc` là <tbody>/<div> RỖNG trong HTML ⇒ số dòng > 0 là do mã vẽ.
     · `#bang-cuoc` của trang `pricing` có SẴN một dòng "nhập cân nặng" trong HTML ⇒ nó KHÔNG
       được dùng làm bằng chứng ở đây; trang ấy đo bằng THAO TÁC THẬT ở ca 04.
     · `.khung` là khung do `VIP.dungKhung()` của chính trang dựng (app.js chỉ ĐỊNH NGHĨA hàm,
       không tự gọi) ⇒ có `.khung` nghĩa là mã trang đã chạy. */
const TRANG = [
  { ten: "dashboard",    do: ["#khay-kpi .the", "#bang-moi-nhat tr"], nguon: "mock/shipments.json" },
  { ten: "shipments",    do: ["#bang tr"],                            nguon: "mock/shipments.json" },
  { ten: "create-order", do: ["#bang-nhap tr"],                       nguon: "localStorage — dòng trạng thái rỗng do mã vẽ" },
  { ten: "ai-import",    do: ["#vung-buoc .the"],                     nguon: "khối bước 1 do mã dựng vào #vung-buoc rỗng" },
  { ten: "webhooks",     do: ["#bang-sk tr", "#kpi-wh .the"],         nguon: "mock + gateway" },
  { ten: "carriers",     do: ["#c-credential [data-truong]"],         nguon: "ba route thật của hệ (đã đăng nhập)" },
  { ten: "pricing",      do: [],                                      nguon: "bảng cước CHỈ hiện sau khi bấm — đo ở ca 04, không tính ở đây" },
  { ten: "cod",          do: ["#bang-cod tr", "#kpi-cod .the"],       nguon: "mock" },
  { ten: "reports",      do: ["#bang-tong tr"],                       nguon: "mock" },
  { ten: "settings",     do: ["#bang-nd tr"],                         nguon: "mảng ND trong chính trang" },
];

/** Số `<script>` KHÔNG có `src` + số thuộc tính sự kiện nội tuyến — hai thứ CSP chặn. */
async function doMaNoiTuyen(page) {
  return page.evaluate(() => ({
    script: document.querySelectorAll("script:not([src])").length,
    su_kien: document.querySelectorAll(
      "[onclick],[onchange],[oninput],[onsubmit],[onload],[onerror],[onkeydown]").length,
  }));
}

// ============================================================================================
// 1. KHÔNG TRANG NÀO CÒN MÃ NỘI TUYẾN
// ============================================================================================
test("01 — không trang nào còn `<script>` nội tuyến hay thuộc tính sự kiện nội tuyến", async ({ page }) => {
  const con = [];
  for (const t of TRANG) {
    await page.goto(`/pages/${t.ten}.html`, { waitUntil: "domcontentloaded" });
    const d = await doMaNoiTuyen(page);
    if (d.script || d.su_kien) con.push(`${t.ten}: ${d.script} script nội tuyến · ${d.su_kien} thuộc tính sự kiện`);
  }
  expect(con, "còn mã nội tuyến ⇒ CSP sẽ chặn và trang lại rỗng").toEqual([]);
});

// ============================================================================================
// 2. KHUNG DỰNG ĐƯỢC + DỮ LIỆU THẬT SỰ CÓ DÒNG
// ============================================================================================
test("02 — mỗi trang dựng được khung và có DỮ LIỆU do chính mã trang vẽ", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");            // `carriers` cần phiên để đọc route thật
  const hong = [];
  for (const t of TRANG) {
    await page.goto(`/pages/${t.ten}.html`, { waitUntil: "domcontentloaded" });
    const khung = await page.locator(".khung").count();
    const dem = [];
    for (const s of t.do) dem.push(`${s}=${await page.locator(s).count()}`);
    console.log(`[đo] ${t.ten}: .khung=${khung} ${dem.join(" ")} (nguồn: ${t.nguon})`);
    if (!khung) { hong.push(`${t.ten}: KHÔNG có .khung ⇒ mã trang không chạy`); continue; }
    for (const s of t.do) {
      const n = await page.locator(s).count();
      if (!n) hong.push(`${t.ten}: "${s}" rỗng ⇒ mã trang chạy mà không ra dữ liệu`);
    }
  }
  expect(hong, "trang hiện ra nhưng RỖNG — người dùng tưởng không có dữ liệu").toEqual([]);
});

// ============================================================================================
// 3. HỘP THOẠI: MỞ RỒI ĐÓNG ĐƯỢC (nút "Đóng" ở chân hộp thoại từng là `onclick` nội tuyến)
// ============================================================================================
test("03 — hộp thoại chi tiết mở được và nút Đóng BẤM ĐƯỢC", async ({ page }) => {
  for (const ten of ["shipments", "webhooks"]) {
    await page.goto(`/pages/${ten}.html`, { waitUntil: "domcontentloaded" });
    const nut_xem = page.locator("[data-xem]").first();
    await nut_xem.waitFor({ state: "visible", timeout: 10_000 });
    await nut_xem.click();
    await expect(page.locator("#modal-hien-tai"), `${ten}: bấm "Chi tiết" không mở hộp thoại`)
      .toBeVisible();
    await page.locator("#modal-hien-tai [data-dong-hop]").click();
    await expect(page.locator("#modal-hien-tai"), `${ten}: nút Đóng không đóng được hộp thoại`)
      .toHaveCount(0);
  }
});

// ============================================================================================
// 4. BA TRANG KHÔNG CÓ DỮ LIỆU SẴN: THAO TÁC THẬT PHẢI RA KẾT QUẢ THẬT
// ============================================================================================
test("04 — trang chỉ có kết quả SAU THAO TÁC: form báo lỗi, bảng cước hiện, bước import chạy", async ({ page }) => {
  // (a) create-order: gửi form TRỐNG ⇒ lỗi hiện TẠI CHỖ do chính mã trang kiểm.
  await page.goto("/pages/create-order.html", { waitUntil: "domcontentloaded" });
  const goi = [];
  page.on("request", (r) => { if (r.method() === "POST") goi.push(r.url()); });
  await page.locator('#form-don button[type="submit"]').click();
  await expect(page.locator("#form-don .co-loi").first(),
    "gửi form trống mà không trường nào bị đánh dấu lỗi ⇒ mã kiểm dữ liệu không chạy").toBeVisible();
  expect(goi, "form trống mà vẫn gửi dữ liệu đi").toEqual([]);

  // (b) pricing: bấm "Tính cước" ⇒ bảng đầy kết quả, dòng hướng dẫn có sẵn trong HTML phải BIẾN MẤT.
  await page.goto("/pages/pricing.html", { waitUntil: "domcontentloaded" });
  const chu_truoc = await page.locator("#bang-cuoc").textContent();
  await page.locator("#nut-tinh").click();
  await expect(page.locator("#bang-cuoc tr").nth(2),
    "bấm Tính cước mà bảng không có kết quả").toBeVisible();
  const chu_sau = await page.locator("#bang-cuoc").textContent();
  expect(chu_sau, "bảng cước không đổi sau khi bấm ⇒ mã trang không chạy").not.toBe(chu_truoc);
  expect(chu_sau, "vẫn còn dòng hướng dẫn có sẵn trong HTML ⇒ bảng không được vẽ lại")
    .not.toContain("Nhập cân nặng và bấm");

  // (c) ai-import: bấm "Dùng tệp CSV mẫu" ⇒ chuyển sang BƯỚC 2 do chính mã trang dựng.
  await page.goto("/pages/ai-import.html", { waitUntil: "domcontentloaded" });
  await page.locator("#dung-mau").click();
  await expect(page.locator("#b2-toi"),
    "dùng tệp mẫu mà không chuyển được sang bước 2 ⇒ mã trang không chạy").toBeVisible();
});

// ============================================================================================
// 5. TỰ KIỂM: CSP CÓ CHẶN THẬT KHÔNG, VÀ PHÉP ĐẾM CÓ THẤY KHÔNG
// ============================================================================================
// Nếu CSP KHÔNG chặn mã nội tuyến thì chín trang kia chưa bao giờ hỏng, và cả tệp này là
// công dựng chuyện. Ca này chèn một `<script>` nội tuyến vào trang đang chạy rồi đo HAI điều:
//   (a) nó KHÔNG chạy (CSP chặn thật), (b) phép đếm của ca 01 VẪN thấy nó.
test("05 — TỰ KIỂM: `<script>` nội tuyến bị CSP chặn THẬT, và phép đếm thấy nó", async ({ page }) => {
  await page.goto("/pages/settings.html", { waitUntil: "domcontentloaded" });
  const truoc = (await doMaNoiTuyen(page)).script;
  expect(truoc, "trang đã sạch mã nội tuyến từ trước ⇒ phép đo này mới có nghĩa").toBe(0);

  const sau = await page.evaluate(() => {
    const s = document.createElement("script");
    s.textContent = "window.__MA_NOI_TUYEN_DA_CHAY = true;";
    document.body.appendChild(s);
    return document.querySelectorAll("script:not([src])").length;
  });
  await page.waitForTimeout(300);            // đủ thời gian cho một script chạy, nếu nó được chạy
  expect(await page.evaluate(() => window.__MA_NOI_TUYEN_DA_CHAY),
    "mã nội tuyến CHẠY ĐƯỢC ⇒ CSP không chặn, và lỗ hổng 9 trang là chuyện khác").toBeUndefined();
  expect(sau, "phép đếm không thấy `<script>` nội tuyến vừa chèn ⇒ ca 01 không đo được gì")
    .toBe(truoc + 1);
});

// ============================================================================================
// 6. TỰ KIỂM: CHẶN TỆP `.js` CỦA TRANG ⇒ PHÉP ĐO CỦA CA 02 PHẢI ĐỎ
// ============================================================================================
// Dựng lại ĐÚNG trạng thái trước bản vá (mã trang không chạy) bằng cách trả 404 cho tệp `.js`
// của trang, rồi chạy lại phép đo của ca 02. Xanh ở đây nghĩa là ca 02 đang đo nhầm thứ khác.
test("06 — TỰ KIỂM: chặn `pages/settings.js` ⇒ khung và bảng RỖNG đúng như bản cũ", async ({ page }) => {
  await page.route("**/pages/settings.js", (r) => r.fulfill({ status: 404, body: "không có" }));
  await page.goto("/pages/settings.html", { waitUntil: "domcontentloaded" });
  const khung = await page.locator(".khung").count();
  const dong = await page.locator("#bang-nd tr").count();
  console.log(`[đo] chặn settings.js: .khung=${khung} #bang-nd tr=${dong}`);
  expect(khung, "chặn mã trang mà khung VẪN dựng ⇒ ca 02 không đo mã của trang").toBe(0);
  expect(dong, "chặn mã trang mà bảng VẪN có dòng ⇒ ca 02 đang đo dữ liệu có sẵn trong HTML").toBe(0);
});
