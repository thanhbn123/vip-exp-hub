// TẦNG 3 — `pages/*.html`: BẢNG DỮ LIỆU PHẢI ĐẾN TỪ MỘT NGUỒN THẬT, VÀ TRANG NÀO KHÔNG CÓ
// NGUỒN THÌ GHI VÀO "CHƯA ĐO" — KHÔNG TÍNH LÀ ĐẠT (G20 · AG-02).
//
// QUAN HỆ VỚI `07_trang_tinh.spec.js` (G19 · AG-06) — đọc trước khi sửa tệp nào:
// Tệp 07 đã canh hai điều rất đúng: (1) không trang nào còn `<script>` nội tuyến hay thuộc
// tính sự kiện nội tuyến, kèm ca TỰ KIỂM chứng minh CSP chặn thật; (2) mỗi trang dựng được
// khung và bộ chọn dữ liệu của nó CÓ phần tử. Tệp này KHÔNG viết lại hai việc ấy.
//
// NÓ BỊT HAI KẼ HỞ CÒN LẠI, cả hai đều đo được:
//
//   KẼ 1 — "BỘ CHỌN CÓ PHẦN TỬ" KHÔNG PHẢI LÀ "CÓ DỮ LIỆU". Tệp 07 đếm `#bang-nd tr` = 4 và
//   ghi `settings` là ĐẠT. Nhưng bốn dòng ấy do một MẢNG VIẾT CỨNG trong `pages/settings.js`
//   vẽ ra — trang KHÔNG đọc ở đâu cả. Cùng cảnh: `create-order` (localStorage, rỗng lúc mới
//   mở) và `pricing` (bảng cước TÍNH từ công thức). Ba trang ấy hiện ra đúng như thiết kế,
//   nhưng gọi chúng là "có dữ liệu" là ĐỌC SAI phép đo. Ở đây chúng được ghi vào CHƯA ĐO.
//
//   KẼ 2 — DANH SÁCH TRANG CHÉP TAY. Tệp 07 liệt kê mười trang thành một mảng trong mã. Thêm
//   một tệp `pages/*.html` mới thì nó KHÔNG được canh ở cả hai điều kiện, và bộ thử vẫn XANH
//   — không một dòng nào nói rằng có trang vừa thoát khỏi vòng canh. Ở đây danh sách được
//   ĐỌC TỪ ĐĨA (`pages/*.html`), rồi đối chiếu với bảng khai: trang lạ ⇒ HỎNG.
//
// CÁCH ĐO "CÓ NGUỒN THẬT": không đọc mã trang rồi tin. Trong lượt mở trang, ghi lại MỌI phản
// hồi không phải html/css/js, rồi đòi một GIÁ TRỊ VÔ HƯỚNG lấy từ chính phản hồi ấy xuất hiện
// trên màn. Giá trị chỉ tồn tại lúc chạy nên không mã cứng trước được — thấy nó trên màn
// nghĩa là DOM dựng từ phản hồi ấy.
//
// PHẠM VI: Chromium (Playwright trong `node_modules/`), nền cô lập của `thu_giao_dien/chay.sh`,
// bind 127.0.0.1. KHÔNG gọi ra hãng.
"use strict";
const { test, expect } = require("@playwright/test");
const { readdirSync } = require("node:fs");
const { join } = require("node:path");
const U = require("./tien_ich");

const GOC = join(__dirname, "..");
const THU_MUC_TRANG = join(GOC, "pages");
test.describe.configure({ mode: "serial" });

/* BẢNG KHAI: mỗi trang `pages/*.html` phải có mặt ở đây, kèm NGUỒN DỮ LIỆU của nó.
   `nguon: "http"`  — trang đọc dữ liệu qua HTTP; ca 03 đòi chứng minh DOM gắn với phản hồi.
   `nguon: "khong"` — trang KHÔNG đọc ở đâu; ca 04 ghi nó vào CHƯA ĐO. Đây KHÔNG phải "trang
                      hỏng": cả ba đều hiện đúng thiết kế. Chỉ là chúng KHÔNG được tính là
                      bằng chứng cho câu "mỗi trang có dữ liệu thật".
   Thêm trang mới mà quên khai ⇒ ca 01 HỎNG (đó là mục đích của ca 01). */
const TRANG = {
  dashboard: { nguon: "http", doc: "mock/shipments.json" },
  shipments: { nguon: "http", doc: "mock/shipments.json" },
  cod: { nguon: "http", doc: "mock/shipments.json" },
  reports: { nguon: "http", doc: "mock/shipments.json" },
  webhooks: { nguon: "http", doc: "mock/webhook-events.json" },
  "ai-import": { nguon: "http", doc: "mock/import-sample.csv — CHỈ tải sau khi bấm \"Dùng tệp CSV mẫu\"",
                 lam: async (page) => {
                   await page.locator("#dung-mau").click();
                   await page.locator("#b2-toi").waitFor({ state: "visible", timeout: 10_000 });
                 } },
  carriers: { nguon: "http", doc: "ba route thật /api/v2/** (cần phiên đăng nhập)" },
  settings: { nguon: "khong", ly_do: "bảng nội dung do MẢNG VIẾT CỨNG trong pages/settings.js vẽ" },
  "create-order": { nguon: "khong", ly_do: "localStorage — rỗng lúc mới mở, không đọc ở đâu" },
  pricing: { nguon: "khong", ly_do: "bảng cước TÍNH từ công thức, không đọc ở đâu" },
  // Bàn nghiệm thu BEST cần phiên đăng nhập + quyền tenant.hang.*; bộ tĩnh không có phiên nên
  // API trả 401. Trang vẫn được canh ở 07 (CSP/khung); dữ liệu thật đo ở app/thu/thu_best_uat.py.
  "best-uat": { nguon: "khong", ly_do: "trang cần phiên đăng nhập; API 401 nếu chưa đăng nhập" },
};

/* ============================================================================================
   BỘ ĐO
   ============================================================================================ */

/** Mọi giá trị VÔ HƯỚNG lá trong payload, kèm đường dẫn tới nó (để in ra đọc lại được). */
function nhatVoScalar(o, duong, ra) {
  ra = ra || []; duong = duong || "";
  if (o === null || o === undefined) return ra;
  if (Array.isArray(o)) { o.forEach((x, i) => nhatVoScalar(x, `${duong}[${i}]`, ra)); return ra; }
  if (typeof o === "object") {
    Object.entries(o).forEach(([k, v]) => nhatVoScalar(v, duong ? `${duong}.${k}` : k, ra));
    return ra;
  }
  ra.push({ duong: duong, gia_tri: o });
  return ra;
}

/** Neo phải ĐỦ ĐẶC THÙ: chuỗi ≥ 4 ký tự (bỏ từ chung), hoặc số ≥ 100. Ngưỡng thấp hơn thì
 *  `0`, `1`, `Có`, `Không` khớp bừa ở mọi trang và ca thử xanh vô nghĩa. */
const TU_CHUNG = new Set(["true", "false", "null", "không", "chưa có", "không có", "đang",
                          "hoạt động", "thành công", "thất bại", "demo", "mock"]);
function duDacThu(g) {
  if (typeof g === "number") return Number.isFinite(g) && Math.abs(g) >= 100;
  if (typeof g !== "string") return false;
  const t = g.trim();
  return t.length >= 4 && !TU_CHUNG.has(t.toLowerCase()) && !/^[\s\d.,%-]*$/.test(t);
}

/** Neo lấy từ một phản hồi: JSON thì lấy giá trị lá; CSV/text thì lấy token. */
function neoTuPhanHoi(r) {
  const ra = [];
  if (r.than && typeof r.than === "object") {
    for (const v of nhatVoScalar(r.than, r.d)) if (duDacThu(v.gia_tri)) ra.push(v);
  } else if (typeof r.than === "string") {
    r.than.split(/[,\n;]+/).forEach((t, i) => {
      const s = t.trim();
      if (duDacThu(s)) ra.push({ duong: `${r.d}#token${i}`, gia_tri: s });
    });
  }
  return ra;
}

/** Mở một trang và ghi lại mọi phản hồi KHÔNG phải html/css/js — tức mọi NGUỒN DỮ LIỆU.
 *  `lam` (tuỳ chọn): thao tác phải bấm thì trang mới chịu đọc nguồn của nó. `ai-import` là
 *  trang như thế — nó KHÔNG tải `mock/import-sample.csv` lúc mở, mà chỉ tải khi người dùng
 *  bấm "Dùng tệp CSV mẫu". Đo ngay sau `goto` thì ra 0 nguồn, và kết luận "trang không đọc
 *  dữ liệu" sẽ là kết luận SAI về sản phẩm, chỉ đúng về phép đo.
 *
 *  HAI CHỐT CHỐNG ĐO SAI, cả hai đều bắt được ở lượt chạy đầy đủ đầu tiên:
 *   · `about:blank` TRƯỚC khi gắn bộ thu. Không có bước này thì phản hồi CÒN BAY của trang
 *     trước rơi vào bộ thu của trang sau: lượt chạy đầy đủ ghi `settings` "đọc 1 nguồn
 *     /api/v2/tai-khoan-hang" — đó là lời gọi của trang `carriers` mở ngay trước đó, không
 *     phải của `settings`. Chạy riêng tệp này thì không thấy, vì lúc ấy chưa có trang trước.
 *   · Bỏ qua `/api/v2/auth/**`: đó là lời gọi PHIÊN, có mặt ở mọi trang động, không phải
 *     nguồn dữ liệu. Tính nó là "nguồn" thì mọi trang đều thành "có dữ liệu". */
async function moVaThuNguon(page, ten, lam) {
  const nguon = [];
  const thu = async (r) => {
    const d = new URL(r.url()).pathname;
    if (/\.(html|css|js|png|jpg|svg|woff2?|ico)$/.test(d)) return;
    if (d.startsWith("/api/v2/auth/")) return;          // phiên, không phải dữ liệu
    let than = null;
    try { than = await r.json(); } catch {
      try { than = await r.text(); } catch { /* không đọc được thân */ }
    }
    nguon.push({ d, ma: r.status(), than });
  };
  await page.goto("about:blank");
  page.on("response", thu);
  await page.goto(`/pages/${ten}.html`, { waitUntil: "networkidle" });
  if (lam) await lam(page);
  await page.waitForTimeout(300);
  page.off("response", thu);
  return nguon;
}

// ============================================================================================
// 1. DANH SÁCH TRANG ĐỌC TỪ ĐĨA — trang lạ phải làm ca thử HỎNG
// ============================================================================================
test("01 — mọi tệp `pages/*.html` trên đĩa đều có mặt trong bảng khai của ca thử", async () => {
  const tren_dia = readdirSync(THU_MUC_TRANG).filter((f) => f.endsWith(".html"))
    .map((f) => f.replace(/\.html$/, "")).sort();
  const khai = Object.keys(TRANG).sort();
  console.log(`[đo] trên đĩa ${tren_dia.length} trang: ${tren_dia.join(", ")}`);
  console.log(`[đo] bảng khai ${khai.length} trang`);
  const la = tren_dia.filter((t) => !khai.includes(t));
  const thua = khai.filter((t) => !tren_dia.includes(t));
  expect(la, "trang MỚI có trên đĩa mà KHÔNG có trong bảng khai ⇒ nó thoát khỏi MỌI ca canh "
    + "của tệp này (và của 07) mà bộ thử vẫn xanh. Khai nó vào `TRANG` rồi đo cho thật.").toEqual([]);
  expect(thua, "bảng khai có trang KHÔNG tồn tại trên đĩa ⇒ ca thử đang canh một cái bóng")
    .toEqual([]);
  expect(tren_dia.length, "không thấy trang nào ⇒ ca này không kiểm gì").toBeGreaterThan(0);
});

// ============================================================================================
// 2. KHÔNG MÃ NỘI TUYẾN — ĐO LẠI ĐỘC LẬP ĐIỀU 07 ĐÃ KHAI (không viết lại, chỉ đối chiếu)
// ============================================================================================
test("02 — không trang nào còn `<script>` nội tuyến hay thuộc tính sự kiện nội tuyến", async ({ page }) => {
  const con = [];
  for (const ten of Object.keys(TRANG)) {
    await page.goto(`/pages/${ten}.html`, { waitUntil: "domcontentloaded" });
    const d = await page.evaluate(() => ({
      script: document.querySelectorAll("script:not([src])").length,
      su_kien: document.querySelectorAll(
        "[onclick],[onchange],[oninput],[onsubmit],[onload],[onerror],[onkeydown]").length,
    }));
    if (d.script || d.su_kien) con.push(`${ten}: ${d.script} script · ${d.su_kien} thuộc tính sự kiện`);
    const khung = await page.locator(".khung").count();
    if (!khung) con.push(`${ten}: không có .khung ⇒ mã trang không chạy`);
  }
  expect(con, "còn mã nội tuyến (CSP `script-src 'self'` sẽ chặn) hoặc trang không dựng được khung")
    .toEqual([]);
});

// ============================================================================================
// 3. TRANG KHAI CÓ NGUỒN — DOM PHẢI GẮN VỚI MỘT PHẢN HỒI THẬT
// ============================================================================================
test("03 — bảy trang khai `http`: bảng dữ liệu dựng từ phản hồi THẬT, có neo đối chiếu", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");     // `carriers` cần phiên để đọc ba route thật
  const hong = [];
  const xong = [];
  for (const [ten, t] of Object.entries(TRANG)) {
    if (t.nguon !== "http") continue;
    const nguon = await moVaThuNguon(page, ten, t.lam);
    const chu = await page.locator("body").innerText();
    const tot = nguon.filter((r) => r.ma >= 200 && r.ma < 300);
    const neo = [];
    for (const r of tot) {
      for (const v of neoTuPhanHoi(r)) {
        if (chu.includes(String(v.gia_tri))) neo.push(`${v.duong}=${JSON.stringify(v.gia_tri)}`);
      }
    }
    console.log(`[đo] ${ten.padEnd(13)} nguồn=${tot.length}/${nguon.length} phản hồi 2xx · `
      + `${neo.length} neo khớp · khai: ${t.doc}`);
    for (const g of tot.slice(0, 4)) console.log(`        ← ${g.ma} ${g.d}`);
    if (neo.length) console.log(`        neo: ${neo.slice(0, 3).join(" · ")}`);

    if (!tot.length) {
      hong.push(`${ten}: KHÔNG đọc nguồn dữ liệu nào (khai: ${t.doc}) ⇒ bảng toàn dòng viết `
        + `cứng hoặc trang không chạy`);
      continue;
    }
    if (!neo.length) {
      hong.push(`${ten}: có ${tot.length} phản hồi 2xx (${tot.map((g) => g.d).join(", ")}) mà `
        + `KHÔNG giá trị nào của chúng xuất hiện trên màn ⇒ không chứng minh được DOM dựng từ `
        + `phản hồi, hay chỉ là bảng viết cứng tình cờ khớp`);
      continue;
    }
    xong.push({ ten, neo: neo.length, nguon: tot.map((g) => g.d).join("+") });
  }
  expect(xong.length, "không trang nào chứng minh được DOM gắn với nguồn ⇒ ca này không kiểm gì")
    .toBe(Object.values(TRANG).filter((t) => t.nguon === "http").length);
  expect(hong, "trang khai có nguồn dữ liệu nhưng KHÔNG chứng minh được").toEqual([]);
});

// ============================================================================================
// 4. TRANG KHÔNG CÓ NGUỒN — GHI VÀO "CHƯA ĐO", KHÔNG TÍNH LÀ ĐẠT
// ============================================================================================
// Ca này KHÔNG hỏi ba trang kia có hỏng không — chúng hiện đúng thiết kế. Nó chốt đúng một
// điều: chúng KHÔNG được lẫn vào nhóm "có dữ liệu thật" khi ai đó trích kết quả lượt chạy.
// Nên nó in ra danh sách CHƯA ĐO, và khẳng định danh sách ấy ĐÚNG BẰNG bảng khai — để một
// trang lặng lẽ MẤT nguồn dữ liệu (ví dụ ai đó bỏ `taiMock` khỏi `cod.js`) cũng làm HỎNG.
test("04 — ba trang không có nguồn dữ liệu: ghi vào CHƯA ĐO, không tính là đạt", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const chuaDo = [];
  for (const [ten, t] of Object.entries(TRANG)) {
    if (t.nguon !== "khong") continue;
    const nguon = await moVaThuNguon(page, ten);
    const dong = await page.locator("#man, .khung").first().count();
    console.log(`[đo] ${ten.padEnd(13)} CHƯA ĐO — ${t.ly_do}`);
    console.log(`        trang dựng khung=${dong}, đọc ${nguon.length} nguồn dữ liệu `
      + `(kỳ vọng 0)`);
    if (nguon.length) {
      // Trang bỗng đọc được nguồn ⇒ bảng khai đã cũ và phải chuyển nó sang nhóm `http`
      // (kèm neo), chứ không được để nó nằm mãi trong sổ CHƯA ĐO.
      chuaDo.push(`${ten}: khai KHÔNG có nguồn mà đọc ${nguon.length} nguồn `
        + `(${nguon.map((g) => g.d).join(", ")}) — chuyển sang nhóm \`http\` và đo cho thật`);
      continue;
    }
    chuaDo.push(ten);
  }
  console.log(`[đo] CHƯA ĐO của lượt này (${chuaDo.length} trang): ${chuaDo.join(", ")}`);
  const phaiChuaDo = Object.entries(TRANG).filter(([, t]) => t.nguon === "khong")
    .map(([k]) => k).sort();
  expect(chuaDo.sort(), "danh sách CHƯA ĐO không khớp bảng khai").toEqual(phaiChuaDo);
  console.log(`[đo] ${Object.values(TRANG).filter((t) => t.nguon === "http").length} trang CÓ `
    + `DỮ LIỆU THẬT · ${phaiChuaDo.length} trang CHƯA ĐO (${phaiChuaDo.join(", ")})`);
});

// ============================================================================================
// 5. TỰ KIỂM — CHẶN NGUỒN DỮ LIỆU THÌ PHÉP ĐO NEO PHẢI MẤT NEO
// ============================================================================================
// Nếu neo vẫn "khớp" khi nguồn bị chặn thì phép đo ở ca 03 đang khớp NHẦM thứ gì đó có sẵn
// trong HTML, và cả tệp này là công dựng chuyện. Ca này dựng lại đúng trạng thái "nguồn chết"
// bằng cách trả 404 cho `mock/shipments.json`, rồi chạy LẠI phép đo của ca 03 trên `shipments`.
test("05 — TỰ KIỂM: chặn `mock/shipments.json` ⇒ phép đo NEO phải MẤT NEO", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");

  // (a) ĐỐI CHỨNG DƯƠNG: không chặn gì thì `shipments` phải CÓ neo. Không có thì ca tự kiểm
  //     này không dựng lại được trạng thái hỏng một cách có nghĩa.
  let nguon = await moVaThuNguon(page, "shipments");
  let chu = await page.locator("body").innerText();
  let neo = [];
  for (const r of nguon.filter((x) => x.ma >= 200 && x.ma < 300)) {
    for (const v of neoTuPhanHoi(r)) if (chu.includes(String(v.gia_tri))) neo.push(v.duong);
  }
  console.log(`[đo] tự kiểm (a) không chặn: ${nguon.length} nguồn, ${neo.length} neo`);
  expect(neo.length, "trang `shipments` bình thường đã không có neo ⇒ ca tự kiểm vô nghĩa")
    .toBeGreaterThan(0);

  // (b) CHẶN nguồn ⇒ neo phải BIẾN MẤT.
  await page.route("**/mock/shipments.json", (r) => r.fulfill({ status: 404, body: "không có" }));
  nguon = await moVaThuNguon(page, "shipments");
  chu = await page.locator("body").innerText();
  neo = [];
  for (const r of nguon.filter((x) => x.ma >= 200 && x.ma < 300)) {
    for (const v of neoTuPhanHoi(r)) if (chu.includes(String(v.gia_tri))) neo.push(v.duong);
  }
  const bang = await page.locator("#bang tr").count();
  console.log(`[đo] tự kiểm (b) chặn nguồn: 2xx=${nguon.filter((x) => x.ma < 300).length}, `
    + `neo=${neo.length}, #bang tr=${bang}`);
  expect(neo.length, "chặn nguồn dữ liệu mà neo VẪN khớp ⇒ neo đang khớp thứ có sẵn trong "
    + "HTML, không phải dữ liệu đọc về").toBe(0);

  // (c) VÀ trang phải NÓI RA là không tải được, chứ không im lặng hiện bảng rỗng.
  expect(chu, "chặn nguồn mà trang KHÔNG nói gì với người dùng ⇒ hỏng im lặng")
    .toMatch(/Không tải được/);
});
