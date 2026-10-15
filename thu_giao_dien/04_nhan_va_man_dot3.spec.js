// TẦNG 3 — NHÃN "CHỜ BACKEND" PHẢI KHỚP THỰC TẾ, và tình trạng 12 màn khai ở đợt 3.
//
// VÌ SAO CÓ FILE NÀY, viết rõ để lần sau không ai sửa nhầm chiều:
// Dự án đã ba lần viết ca thử khoá vào trạng thái hiện tại của một việc chưa xong — một ca
// đòi "route phải CHƯA có", hai ca đòi "mọi màn phải mang nhãn CHỜ BACKEND". Backend làm
// xong thì ca HỎNG, tức là ca thử đứng chắn đường tiến bộ.
//
// Nên ở đây chốt theo Ý ĐỊNH: **nhãn phải KHỚP thực tế**.
//   - Màn hiện nhãn "CHỜ BACKEND" cho một đường ⇒ đường ấy phải THẬT SỰ chưa dùng được.
//   - Đường đã dùng được ⇒ KHÔNG được còn nhãn chờ ở màn.
// Ca này đúng ở cả hai thì, và tự chuyển vế khi AG-00 cắm route.
//
// GHI RÕ RỦI RO CỐ Ý: ca "nhãn khớp thực tế" bắn ĐÚNG method khai trong nhãn, kể cả POST.
// Trên nền cô lập của `chay.sh` thì vô hại (nền xoá khi xong). Đừng chạy bộ thử này vào
// CSDL đang dùng — `playwright.config.js` đã từ chối chạy khi thiếu VIP_GD_GOC đúng vì thế.
"use strict";
const { test, expect } = require("@playwright/test");
const U = require("./tien_ich");

test.describe.configure({ mode: "serial" });

/** Bắn thật một đường từ TRONG trang (mang cookie phiên như giao diện mang). */
async function ban(page, method, duong) {
  return page.evaluate(async ([m, d]) => {
    const h = { "X-Requested-With": "VIPHub" };
    const opt = { method: m, headers: h };
    if (m !== "GET" && m !== "HEAD") { h["Content-Type"] = "application/json"; opt.body = "{}"; }
    const r = await fetch(d, opt);
    return r.status;
  }, [method, duong]);
}

/** Đường có `<id>` thì thay bằng một id có thật, nếu không thì 404 sẽ là 404 vì SAI ID
 *  chứ không phải vì thiếu route — đó là phép đo nói dối. */
async function thayId(page, duong) {
  if (!duong.includes("<id>")) return duong;
  const id = await page.evaluate(async () => {
    const r = await fetch("/api/v2/don?gioi_han=1");
    if (!r.ok) return null;
    const j = await r.json();
    return (j.don && j.don[0] && j.don[0].id) || null;
  });
  return id == null ? null : duong.replace("<id>", String(id));
}

test("nhãn CHỜ BACKEND hiện trên màn phải KHỚP thực tế của máy chủ", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const menu = await U.docMenu(page);

  // Những đường khai `mot_phan: true` trong `admin/logic.js`: đường ĐÃ CÓ nhưng chưa đủ
  // (thiếu tham số, hoặc trả siêu dữ liệu chứ chưa trả thứ cuối cùng). Nhãn chờ ở đó là
  // ĐÚNG dù máy chủ trả 2xx — nên đọc cờ ấy ra, không suy từ mã HTTP.
  const mot_phan = await page.evaluate(() =>
    (window.VIPLOGIC.API_CHO_BACKEND || []).filter((x) => x.mot_phan)
      .map((x) => x.method + " " + x.duong));

  // Gom mọi nhãn CHỜ BACKEND trên DOM thật, kèm đường ghi trong thuộc tính title.
  const nhan = new Map();
  for (const m of menu) {
    await U.moMan(page, m.ma);
    const ds = await page.locator("#man .tag-demo").evaluateAll((ns) =>
      ns.filter((n) => /CHỜ BACKEND/i.test(n.textContent))
        .map((n) => n.getAttribute("title") || ""));
    for (const t of ds) {
      const mm = t.match(/^(GET|POST|PUT|DELETE|PATCH)\s+(\/\S+)/);
      if (!mm) continue;
      const khoa = mm[1] + " " + mm[2];
      const cu = nhan.get(khoa);
      if (cu) { cu.man.push(m.ma); continue; }
      nhan.set(khoa, { man: [m.ma], method: mm[1], duong: mm[2] });
    }
  }
  console.log(`[đo] ${nhan.size} nhãn CHỜ BACKEND có đường, thu từ ${menu.length} màn`);
  expect(nhan.size, "không thu được nhãn CHỜ BACKEND nào có đường ⇒ ca này không kiểm gì — " +
                    "hoặc nhãn đã hết, hoặc nhãn mất thuộc tính title").toBeGreaterThan(0);

  const noi_doi = [];
  for (const [khoa, x] of nhan) {
    const duong = await thayId(page, x.duong);
    if (duong === null) { console.log(`[bỏ qua] ${khoa} — không có đơn nào để thay <id>`); continue; }
    const ma = await ban(page, x.method, duong);
    const mp = mot_phan.includes(khoa);
    console.log(`[đo] ${khoa} (màn ${x.man.join("+")}) → HTTP ${ma}${mp ? " [khai mot_phan]" : ""}`);
    // Đường CHƯA dùng được thì máy chủ phải nói chưa có: 404 / 405 / 501.
    // 2xx nghĩa là đường đã chạy ⇒ nhãn nói dối — TRỪ đường khai `mot_phan`, vốn đã nói
    // thẳng là "có nhưng chưa đủ". Không có ngoại lệ này thì ca thử ép gỡ nhãn của một
    // đường còn thiếu thật, tức là ép giao diện tuyên bố làm được việc nó chưa làm được.
    if (ma >= 200 && ma < 300 && !mp) {
      noi_doi.push(`${khoa} (màn ${x.man.join("+")}) trả HTTP ${ma} — đường ĐÃ CHẠY mà màn vẫn dán nhãn CHỜ BACKEND, và nó KHÔNG khai mot_phan`);
    }
  }
  expect(noi_doi, "nhãn CHỜ BACKEND nói dối").toEqual([]);
});

test("năm module đợt 3 nạp được trong trình duyệt và lộ đúng tên window", async ({ page }) => {
  const loi = U.thuLoi(page);
  const tep = U.thuTepTinhHong(page);
  await page.context().clearCookies();
  await page.goto("/admin/index.html", { waitUntil: "networkidle" });
  const co = await page.evaluate(() => ({
    VIPLOGIC: typeof window.VIPLOGIC,
    VIPFINANCE: typeof window.VIPFINANCE,
    VIPBILLING: typeof window.VIPBILLING,
    VIPCARRIERHEALTH: typeof window.VIPCARRIERHEALTH,
    VIPAI: typeof window.VIPAI,
    VIPHEALTH: typeof window.VIPHEALTH,
  }));
  for (const [k, v] of Object.entries(co)) {
    expect(v, `window.${k} không nạp được — sai thứ tự script trong admin/index.html?`).toBe("object");
  }
  expect(loi, "lỗi do chính trang sinh khi nạp trang quản trị").toEqual([]);
  expect(tep, "tệp tĩnh của trang quản trị không tải được").toEqual([]);
});

// === 12 màn khai ở đợt 3 ===================================================================
// Năm module trên KHAI màn (VIPFINANCE.MAN_HINH có 7 màn tài chính; billing/carrier_health/
// ai/health mỗi module một màn). Ca dưới đối chiếu DANH SÁCH KHAI với MENU THẬT và bắt mọi
// màn ĐÃ CÓ trên menu phải mở được, không lỗi console, không tràn ngang ở cả ba bề rộng.
//
// Nó KHÔNG đòi màn phải có — đó là chốt theo trạng thái hiện tại. Nó in ra con số "khai bao
// nhiêu / có bao nhiêu" để khoảng cách luôn nhìn thấy được, và tự bắt đầu đo khi màn được cắm.

test("12 màn khai ở đợt 3 — màn nào ĐÃ có trên menu thì phải chạy được", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const khai = await page.evaluate(() => {
    const ra = [];
    const f = window.VIPFINANCE;
    if (f && f.MAN_HINH) f.MAN_HINH.forEach((m) => ra.push({ nguon: "finance.js", ma: m.ma, ten: m.ten }));
    // `billing.js` khai màn dạng MẢNG `[ma, ten, quyen]`, `finance.js` dạng OBJECT
    // `{ma, ten}`. Phải đọc đúng từng dạng — `String(x)` trên một mảng cho ra
    // "goi,Danh sách gói,tenant.billing.xem", tức là một mã màn không tồn tại, và mọi
    // phép so với menu sau đó đều vô nghĩa mà vẫn chạy trơn.
    [["billing.js", window.VIPBILLING], ["carrier_health.js", window.VIPCARRIERHEALTH],
     ["ai.js", window.VIPAI], ["health.js", window.VIPHEALTH]].forEach(([n, mod]) => {
      if (!mod) return;
      const m = mod.MAN || mod.MAN_HINH;
      if (Array.isArray(m)) {
        m.forEach((x) => {
          if (Array.isArray(x)) ra.push({ nguon: n, ma: x[0], ten: x[1] || x[0], quyen: x[2] || null });
          else ra.push({ nguon: n, ma: x.ma, ten: x.ten || x.ma, quyen: x.quyen || null });
        });
      } else {
        // Module không khai bảng màn (carrier_health / ai / health): coi là MỘT màn, lấy
        // tên module làm mã. Ghi rõ là suy ra, không phải khai báo.
        ra.push({ nguon: n, ma: n.replace(".js", "").replace(/_/g, "-"), ten: n, suy_ra: true });
      }
    });
    return ra;
  });
  const menu = (await U.docMenu(page)).map((m) => m.ma);
  const co_tren_menu = khai.filter((k) => menu.includes(k.ma));
  const chua_cam = khai.filter((k) => !menu.includes(k.ma));

  console.log(`[đo] đợt 3 khai ${khai.length} màn; ${co_tren_menu.length} đã có trên menu; ` +
              `${chua_cam.length} CHƯA cắm vào giao diện:\n  ` +
              chua_cam.map((k) => `${k.nguon} → ${k.ma} (${k.ten})`).join("\n  "));

  expect(khai.length, "không đọc được màn nào từ năm module đợt 3 ⇒ ca này không kiểm gì")
    .toBeGreaterThan(0);

  const hong = [];
  for (const k of co_tren_menu) {
    const loi = U.thuLoi(page);
    const td = await U.moMan(page, k.ma).catch((e) => "LỖI: " + e.message);
    if (!td || String(td).startsWith("LỖI")) { hong.push(`${k.ma}: không mở được — ${td}`); continue; }
    if (loi.length) hong.push(`${k.ma}: ${loi.length} lỗi console — ${loi.join(" | ")}`);
    for (const br of U.BE_RONG) {
      await page.setViewportSize({ width: br.width, height: br.height });
      const kq = await U.doTranNgang(page);
      if (kq.tai_lieu > 0 || kq.phan_tu.length) hong.push(U.moTaTran(`${k.ma} @ ${br.width}px`, kq));
    }
    await page.setViewportSize({ width: 1280, height: 900 });
  }
  expect(hong, "màn đợt 3 đã cắm nhưng hỏng").toEqual([]);
});
