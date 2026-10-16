// TẦNG 3 — DÙNG ĐƯỢC BẰNG BÀN PHÍM (V-13911). Trình duyệt THẬT, bàn phím THẬT.
//
// VÌ SAO CÓ TỆP NÀY: `BAN_GIAO.md` §6.1 ghi `V-13911` — "giao diện quản trị không dùng được
// bằng bàn phím: 10 mục menu + Đăng xuất là `<a>` không `href`/`tabindex`/`role`; 15 lượt Tab
// không rời `body`" — và §10 gọi đây là CHỖ YẾU NHẤT CỦA HỆ. Không có ca nào canh nó, nên nó
// chỉ tồn tại trong tài liệu. Bản vá ở `admin/ban_phim.js` (mô-đun riêng, xem đầu tệp ấy).
//
// ĐO BẰNG GÌ: `document.activeElement` SAU MỖI LẦN BẤM TAB THẬT, cộng `outline` đọc từ
// `getComputedStyle` của chính phần tử đang giữ tiêu điểm. KHÔNG đọc chữ trên màn rồi tin,
// KHÔNG chụp ảnh, KHÔNG kiểm "thuộc tính có mặt" — có `tabindex` mà Tab không tới thì vẫn là hỏng.
//
// PHẠM VI: Chromium (Playwright trong `node_modules/`), nền cô lập của `thu_giao_dien/chay.sh`,
// bind 127.0.0.1. Không gọi hãng ở bất kỳ môi trường nào.
"use strict";
const { test, expect } = require("@playwright/test");
const U = require("./tien_ich");

test.describe.configure({ mode: "serial" });

/** Mô tả một phần tử ĐANG giữ tiêu điểm — chạy TRONG TRANG (chuỗi, không phải hàm Node:
 *  hàm Node không thấy `document`). Dùng chung cho mọi ca để các vết Tab so được với nhau. */
const MO_TA = `(() => {
  const el = document.activeElement;
  if (!el) return "null";
  if (el === document.body) return "body";
  if (el === document.documentElement) return "html";
  const lop = (typeof el.className === "string" && el.className.trim())
    ? "." + el.className.trim().split(/\\s+/).join(".") : "";
  return el.tagName.toLowerCase() + (el.id ? "#" + el.id : "")
    + (el.dataset && el.dataset.man ? "[data-man=" + el.dataset.man + "]" : "") + lop;
})()`;

/** Bấm Tab `n` lượt, ghi lại AI giữ tiêu điểm sau từng lượt. */
async function vetTab(page, n) {
  const vet = [];
  for (let i = 0; i < n; i++) {
    await page.keyboard.press("Tab");
    vet.push(await page.evaluate(MO_TA));
  }
  return vet;
}

/** Bỏ phần LỚP khỏi mô tả để so danh tính: `a[data-man=don].hien-tai` và `a[data-man=don]` là
 *  CÙNG một phần tử (`hien-tai` chỉ là màn đang xem). Lớp vẫn được in ra ở `console.log`. */
const dinhDanh = (x) => x.split(".")[0];

/** Dấu hiệu tiêu điểm của phần tử ĐANG giữ tiêu điểm, đọc từ `getComputedStyle`.
 *  Trả về số đo, không trả "trông ổn": bề dày, kiểu, màu. */
async function doTieuDiem(page) {
  return page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return { ai: "body", rong: 0, kieu: "none", mau: "" };
    const s = getComputedStyle(el);
    return {
      ai: el.tagName.toLowerCase() + (el.id ? "#" + el.id : "")
        + (el.dataset && el.dataset.man ? "[data-man=" + el.dataset.man + "]" : ""),
      rong: parseFloat(s.outlineWidth) || 0,
      kieu: s.outlineStyle,
      mau: s.outlineColor,
    };
  });
}

/** Gỡ mô-đun bàn phím bằng cách trả về một tệp RỖNG — dựng lại ĐÚNG trạng thái trước bản vá
 *  (`V-13911`), không phải mô phỏng bằng cách tự xoá thuộc tính. Dùng cho ca TỰ KIỂM. */
async function goModuleBanPhim(page) {
  await page.route("**/admin/ban_phim.js", (r) =>
    r.fulfill({ status: 200, contentType: "application/javascript; charset=utf-8",
                body: "/* TỰ KIỂM: gỡ bỏ phần xử lý bàn phím — đúng trạng thái trước bản vá. */" }));
}

// ============================================================================================
// 1. TAB ĐI HẾT ĐƯỢC MENU — và ĐÚNG THỨ TỰ ĐANG NHÌN THẤY
// ============================================================================================
test("01 — Tab đi hết menu quản trị theo ĐÚNG thứ tự trên màn, rồi tới Đăng xuất", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const menu = (await U.docMenu(page)).map((m) => m.ma);
  expect(menu.length, "menu rỗng ⇒ ca này không đo được gì").toBeGreaterThan(3);

  const vet = await vetTab(page, menu.length + 5);
  console.log("[đo] vết Tab:\n  " + vet.map((x, i) => `${i + 1}. ${x}`).join("\n  "));
  const ten = vet.map(dinhDanh);

  // Không giả định lượt Tab ĐẦU TIÊN rơi vào đâu (trình duyệt có thể đưa tiêu điểm về đầu
  // tài liệu): tìm mục menu ĐẦU TIÊN trong vết rồi đòi phần tiếp theo khớp từng mục một.
  const dau = ten.indexOf(`a[data-man=${menu[0]}]`);
  expect(dau, `sau ${vet.length} lượt Tab vẫn không chạm được mục menu đầu tiên (${menu[0]}) — `
    + `menu KHÔNG vào được thứ tự Tab (V-13911)`).toBeGreaterThanOrEqual(0);
  expect(ten.slice(dau, dau + menu.length), "thứ tự Tab không khớp thứ tự menu đang hiện")
    .toEqual(menu.map((m) => `a[data-man=${m}]`));

  // Ngay SAU mục cuối là lối ra (Đăng xuất) — cũng là `<a>` không `href` ở bản cũ.
  expect(ten[dau + menu.length], "sau mục menu cuối, lượt Tab kế tiếp không tới Đăng xuất")
    .toBe("a#nut-thoat");

  // "Không bị kẹt trong body": số đích KHÁC NHAU phải bằng menu + lối ra. Bản cũ cho 1 đích
  // duy nhất (`body`) suốt 15 lượt.
  expect(new Set(ten).size, "số đích khác nhau quá ít ⇒ tiêu điểm kẹt một chỗ")
    .toBeGreaterThanOrEqual(menu.length + 1);
});

// ============================================================================================
// 2. ĐỔI MÀN ĐƯỢC BẰNG BÀN PHÍM — Tab tới rồi Enter, màn phải ĐỔI THẬT
// ============================================================================================
test("02 — Tab tới mục menu rồi Enter: màn ĐỔI THẬT (không chỉ có thuộc tính)", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const tieu_de_truoc = (await page.locator("#tieu-de").textContent()).trim();
  const noi_dung_truoc = await page.locator("#man").innerHTML();

  // Đi bằng BÀN PHÍM tới mục "Đơn hàng": Tab từ đầu tài liệu cho tới khi tiêu điểm đúng mục ấy.
  await page.evaluate(() => document.activeElement && document.activeElement.blur());
  let toi = false;
  for (let i = 0; i < 25 && !toi; i++) {
    await page.keyboard.press("Tab");
    toi = await page.evaluate(() =>
      document.activeElement && document.activeElement.dataset
      && document.activeElement.dataset.man === "don");
  }
  expect(toi, "25 lượt Tab mà tiêu điểm không tới được mục 'Đơn hàng' ⇒ không đổi màn được").toBe(true);

  await page.keyboard.press("Enter");
  await expect(page.locator("#tieu-de"), "Enter trên mục menu không đổi màn").toHaveText("Đơn hàng");
  expect(await page.locator("#man").innerHTML(), "tiêu đề đổi mà nội dung màn không đổi")
    .not.toBe(noi_dung_truoc);
  expect(tieu_de_truoc).not.toBe("Đơn hàng");   // ca phải bắt đầu từ màn KHÁC, nếu không thì vô nghĩa

  // Trạng thái "đang xem" phải nói được cho trình đọc màn hình, không chỉ bằng màu.
  await expect(page.locator('.menu-quan-tri a[data-man="don"]')).toHaveAttribute("aria-current", "page");
  expect(await page.evaluate(() => location.hash), "địa chỉ không ghi màn đang xem").toBe("#don");
});

// ============================================================================================
// 3. DẤU HIỆU TIÊU ĐIỂM NHÌN THẤY ĐƯỢC — đo bằng `getComputedStyle`, không bằng cảm nhận
// ============================================================================================
test("03 — mỗi điểm dừng Tab đều có dấu hiệu tiêu điểm nhìn thấy được", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");                     // màn có nhiều điều khiển để đi qua
  const so_diem = 14;
  const do_duoc = [];
  for (let i = 0; i < so_diem; i++) {
    await page.keyboard.press("Tab");
    do_duoc.push(await doTieuDiem(page));
  }
  console.log("[đo] tiêu điểm:\n  " + do_duoc.map((x) => `${x.ai}: outline ${x.rong}px ${x.kieu} ${x.mau}`).join("\n  "));

  const khong_thay = do_duoc.filter((x) => x.ai === "body" || x.rong < 1 || x.kieu === "none");
  expect(khong_thay, `điểm dừng Tab KHÔNG có dấu hiệu tiêu điểm: ${JSON.stringify(khong_thay)}`).toEqual([]);
});

// ============================================================================================
// 4. MÀN CÓ ĐIỀU KHIỂN: TAB PHẢI VÀO ĐƯỢC `#man` (bản cũ đi được phần này — giữ để không lùi)
// ============================================================================================
test("04 — Tab vào được các điều khiển TRONG màn, không chỉ quanh menu", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");
  const trong_man = await page.locator("#man a[href], #man button, #man input, #man select, #man textarea").count();
  expect(trong_man, "màn Đơn hàng không có điều khiển nào ⇒ ca này không đo được gì").toBeGreaterThan(3);

  const vet = await vetTab(page, 30);
  const ten = vet.map(dinhDanh);
  const vao_man = ten.filter((x) => /^input|^select|^textarea|^button/.test(x)).length;
  console.log(`[đo] 30 lượt Tab: ${vao_man} điểm dừng là điều khiển trong màn · `
    + `${ten.filter((x) => x === "body").length} lượt ở body · ${new Set(ten).size} đích khác nhau`);
  expect(vao_man, `30 lượt Tab chỉ vào được ${vao_man} điều khiển trong màn`).toBeGreaterThan(10);
  // Đích khác nhau ĐẾM THẤP HƠN thực tế một cách có lý: các nút cùng lớp trong một bảng có
  // cùng mô tả (`button.nut.nut-nho`) nên gộp lại. Ngưỡng dưới vì thế chỉ để bắt "kẹt một chỗ".
  expect(new Set(ten).size, "số đích khác nhau quá ít ⇒ tiêu điểm kẹt một chỗ").toBeGreaterThanOrEqual(15);
  expect(ten.filter((x) => x === "body").length, "Tab quay về body quá nhiều lượt ⇒ có chỗ chặn tiêu điểm")
    .toBeLessThanOrEqual(3);
});

// ============================================================================================
// 5. ĐĂNG XUẤT BẰNG BÀN PHÍM
// ============================================================================================
test("05 — Đăng xuất bấm được bằng bàn phím: Tab tới, Enter, về màn đăng nhập", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await page.locator("#nut-thoat").focus();
  expect(await page.evaluate(() => document.activeElement.id),
         "`#nut-thoat` không nhận được tiêu điểm").toBe("nut-thoat");
  await page.keyboard.press("Enter");
  await expect(page.locator("#dn-ten"), "Enter trên Đăng xuất không đưa về màn đăng nhập")
    .toBeVisible();
});

// ============================================================================================
// 6. TỰ KIỂM BỘ ĐO — gỡ phần xử lý bàn phím thì CÙNG phép đo PHẢI ĐỎ
// ============================================================================================
// Một ca thử chỉ đáng tin nếu chứng minh được nó ĐỎ khi mã nguồn hỏng (§12.1). Ca này trả về
// một `ban_phim.js` RỖNG — đúng trạng thái trước bản vá — rồi chạy lại chính các phép đo của
// ca 01 và ca 02. Nếu chúng vẫn xanh thì ca 01/ca 02 không đo bản vá, chúng chỉ đang đo may mắn.
test("06 — TỰ KIỂM: gỡ `ban_phim.js` ⇒ menu KHÔNG vào được thứ tự Tab và Enter không đổi màn", async ({ page }) => {
  await goModuleBanPhim(page);
  await U.dangNhap(page, "shopa-owner");

  const truoc = await page.evaluate(() => ({
    co_module: !!window.VIPBANPHIM,
    menu_co_href: document.querySelectorAll(".menu-quan-tri a[href]").length,
    tong_menu: document.querySelectorAll(".menu-quan-tri a").length,
    nut_thoat_href: document.querySelector("#nut-thoat").getAttribute("href"),
  }));
  console.log("[đo] sau khi gỡ module: " + JSON.stringify(truoc));
  expect(truoc.co_module, "tệp rỗng mà `VIPBANPHIM` vẫn có ⇒ cách gỡ không có tác dụng").toBe(false);
  expect(truoc.menu_co_href, "menu vẫn có href sau khi gỡ module ⇒ phép gỡ không chạm đúng chỗ").toBe(0);
  expect(truoc.nut_thoat_href).toBe(null);

  // (a) phép đo của ca 01 phải ĐỎ: 15 lượt Tab không tới được mục menu nào.
  const vet = await vetTab(page, 15);
  const toi_menu = vet.filter((x) => x.indexOf("[data-man=") >= 0);
  console.log("[đo] 15 lượt Tab sau khi gỡ module: " + JSON.stringify(vet));
  expect(toi_menu, "gỡ module mà Tab VẪN tới được menu ⇒ ca 01 không đo bản vá").toEqual([]);

  // (b) phép đo của ca 02 phải ĐỎ: đặt tiêu điểm vào mục menu rồi Enter — `focus()` không
  //     nhận được (thẻ `<a>` không `href` không vào được thứ tự Tab), nên màn KHÔNG đổi.
  const tieu_de_truoc = (await page.locator("#tieu-de").textContent()).trim();
  await page.locator('.menu-quan-tri a[data-man="don"]').focus();
  expect(await page.evaluate(() => document.activeElement.dataset.man),
         "gỡ module mà thẻ <a> không href VẪN nhận được tiêu điểm").not.toBe("don");
  await page.keyboard.press("Enter");
  const doi = await page.waitForFunction(
    (t) => document.querySelector("#tieu-de").textContent.trim() !== t,
    tieu_de_truoc, { timeout: 2000 }).then(() => true).catch(() => false);
  expect(doi, "gỡ module mà Enter VẪN đổi màn ⇒ ca 02 không đo bản vá").toBe(false);
});

// ============================================================================================
// 7. BỐ CỤC HẸP: KHÔNG TAB VÀO CHỖ KHÔNG NHÌN THẤY
// ============================================================================================
// Ở ≤768px thanh bên là `position:fixed; left:-260px` — NGOÀI khung nhìn nhưng VẪN trong DOM,
// nên nếu cứ để `href` thì 12 điểm dừng Tab đầu nằm ở `x=-252`: tiêu điểm có mà không thấy gì.
// (Đo được: bản vá đầu tiên của AG-06 mắc đúng lỗi này.) Ca này canh cả hai chiều.
test("07 — bố cục hẹp: thanh bên ĐÓNG thì không Tab vào chỗ khuất; MỞ ra thì Tab vào được", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await U.dangNhap(page, "shopa-owner");
  const do_diem_dung = () => page.evaluate(() => {
    const el = document.activeElement;
    if (!el || el === document.body) return { ai: "body", x: 0, y: 0, trong: true };
    const r = el.getBoundingClientRect();
    const nhan = el.tagName.toLowerCase() + (el.id ? "#" + el.id : "")
      + (el.dataset && el.dataset.man ? "[data-man=" + el.dataset.man + "]" : "");
    return { ai: nhan, x: Math.round(r.x), y: Math.round(r.y),
             trong: r.x >= 0 && r.y >= 0 && r.right <= innerWidth + 1 && r.bottom <= innerHeight + 1 };
  });

  // (a) thanh bên ĐANG ĐÓNG: mọi điểm dừng phải nằm TRONG khung nhìn.
  expect(await page.evaluate(() => document.getElementById("sidebar").classList.contains("mo")),
         "thanh bên đang mở sẵn ⇒ phép đo (a) không có nghĩa").toBe(false);
  const vet = [];
  for (let i = 0; i < 14; i++) { await page.keyboard.press("Tab"); vet.push(await do_diem_dung()); }
  console.log("[đo] 375px, thanh bên đóng:\n  "
    + vet.map((x, i) => `${i + 1}. ${x.ai} x=${x.x} trong=${x.trong}`).join("\n  "));
  const khuat = vet.filter((x) => !x.trong);
  expect(khuat, `Tab dừng ở chỗ NGOÀI khung nhìn: ${JSON.stringify(khuat)}`).toEqual([]);

  // (b) mở ☰ BẰNG BÀN PHÍM ⇒ các mục menu trở lại thứ tự Tab và nằm trong khung nhìn.
  await page.locator("#nut-menu").focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("#sidebar")).toHaveClass(/mo/);
  // Thanh bên trượt vào bằng `transition: left .2s`. Đo NGAY sau cú bấm thì vẫn còn `x=-244`
  // (khung hình giữa đường) — nên chờ ĐÚNG trạng thái cuối (`left: 0px`), không chờ đồng hồ.
  await expect(page.locator("#sidebar")).toHaveCSS("left", "0px", { timeout: 5_000 });
  // Chờ ĐÚNG điều kiện, không chờ đồng hồ: mục menu phải được TRẢ LẠI thứ tự Tab.
  await expect(page.locator('#sidebar a[data-man="don"]'),
    "mở thanh bên mà mục menu vẫn bị khoá khỏi thứ tự Tab")
    .not.toHaveAttribute("tabindex", "-1", { timeout: 5_000 });
  // Đi NGƯỢC từ nút ☰ vào trong thanh bên — đúng đường một người dùng bàn phím đi sau khi mở
  // menu (thanh bên nằm TRƯỚC nội dung trong DOM, nên Tab xuôi từ ☰ sẽ đi tiếp vào nội dung;
  // `blur()` không đặt lại điểm xuất phát của trình duyệt, đo được: Tab xuôi vẫn đi từ ☰).
  await page.keyboard.press("Shift+Tab");
  const vao = [await do_diem_dung()];
  for (let i = 0; i < 3; i++) { await page.keyboard.press("Shift+Tab"); vao.push(await do_diem_dung()); }
  console.log("[đo] 375px, sau khi mở ☰, đi ngược vào thanh bên:\n  "
    + vao.map((x, i) => `${i + 1}. ${x.ai} x=${x.x} trong=${x.trong}`).join("\n  "));
  expect(vao.filter((x) => /nut-thoat|\[data-man=/.test(x.ai)).length,
    "mở thanh bên rồi mà đi ngược vẫn không vào được mục menu").toBeGreaterThanOrEqual(3);
  expect(vao.filter((x) => !x.trong), "mục menu vẫn nằm ngoài khung nhìn sau khi mở thanh bên")
    .toEqual([]);
});
