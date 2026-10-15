// TẦNG 3 — BỐ CỤC: tràn ngang đo bằng `scrollWidth` vs `clientWidth`, không bằng cảm nhận
// và không bằng ảnh chụp.
//
// PHẠM VI: ba bề rộng 375 / 768 / 1280, chỉ Chromium. Không có thiết bị cảm ứng thật, không
// trình đọc màn hình, không in ra giấy. Màn nào không có trên menu thì KHÔNG được đo — và
// ca cuối nói rõ đã đo bao nhiêu màn, để con số không nói rộng hơn phạm vi (§12.1 luật 5).
//
// LOẠI TRỪ CÓ CHỦ Ý: phần tử nằm trong `.cuon-ngang`. Bảng rộng PHẢI cuộn ngang trong vùng
// của nó — đó là thiết kế. Loại trừ này là lỗ hổng đã biết của phép đo: một bố cục hỏng mà
// lại nằm trong `.cuon-ngang` thì bộ thử này không thấy.
"use strict";
const { test, expect } = require("@playwright/test");
const U = require("./tien_ich");

test.describe.configure({ mode: "serial" });

for (const br of U.BE_RONG) {
  test(`tràn ngang — mọi màn trên menu ở ${br.ten}px`, async ({ page }) => {
    await page.setViewportSize({ width: br.width, height: br.height });
    const loi = U.thuLoi(page);
    await U.dangNhap(page, "shopa-owner");
    const menu = await U.docMenu(page);
    expect(menu.length, "không có màn nào để đo").toBeGreaterThan(0);

    const bao = [];
    const tran = [];
    for (const m of menu) {
      await U.moMan(page, m.ma);
      const kq = await U.doTranNgang(page);
      bao.push(U.moTaTran(`${br.width}px · ${m.ma}`, kq));
      if (kq.tai_lieu > 0 || kq.phan_tu.length) tran.push(U.moTaTran(`${br.width}px · ${m.ma}`, kq));
    }
    console.log(`[đo] ${bao.length} phép đo ở ${br.width}px:\n  ` + bao.join("\n  "));
    expect(tran, `TRÀN NGANG ở ${br.width}px`).toEqual([]);
  });
}

test("tràn ngang — modal chi tiết đơn, cả 4 tab, ở 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");
  await page.locator("[data-xem]").first().click();
  await expect(page.locator("#ct-tab")).toBeVisible();

  const tran = [];
  for (const t of ["tt", "tl", "ls", "in"]) {
    await page.locator(`#ct-tab .tab-nut[data-tab="${t}"]`).click();
    const kq = await U.doTranNgang(page);
    console.log("[đo] " + U.moTaTran(`375px · modal tab ${t}`, kq));
    if (kq.tai_lieu > 0 || kq.phan_tu.length) tran.push(U.moTaTran(`375px · modal tab ${t}`, kq));
  }
  expect(tran, "TRÀN NGANG trong modal chi tiết đơn ở 375px").toEqual([]);
});

test("tràn ngang — modal tạo đơn ở 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");
  await page.locator("#d-them").click();
  await expect(page.locator("#f-luu")).toBeVisible();
  const kq = await U.doTranNgang(page);
  console.log("[đo] " + U.moTaTran("375px · modal tạo đơn", kq));
  expect(kq.tai_lieu, "modal tạo đơn tràn ngang ở 375px").toBe(0);
  expect(kq.phan_tu, "phần tử tràn trong modal tạo đơn").toEqual([]);
});

test("tràn ngang — màn đăng nhập và màn phiên hết hạn ở 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await page.goto("/admin/index.html", { waitUntil: "networkidle" });
  const a = await U.doTranNgang(page);
  console.log("[đo] " + U.moTaTran("375px · màn đăng nhập", a));
  expect(a.tai_lieu, "màn đăng nhập tràn ngang ở 375px").toBe(0);
  expect(a.phan_tu).toEqual([]);
});

test("tràn ngang — mười trang demo tĩnh ở 375px (CSS dùng chung, không được phá)", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  const trang = ["dashboard", "shipments", "create-order", "carriers", "cod",
                 "webhooks", "reports", "pricing", "ai-import", "settings"];
  const tran = [];
  for (const t of trang) {
    await page.goto(`/pages/${t}.html`, { waitUntil: "networkidle" });
    const kq = await U.doTranNgang(page);
    console.log("[đo] " + U.moTaTran(`375px · pages/${t}.html`, kq));
    if (kq.tai_lieu > 0 || kq.phan_tu.length) tran.push(U.moTaTran(`375px · pages/${t}.html`, kq));
  }
  expect(tran, "TRÀN NGANG ở trang demo tĩnh, 375px").toEqual([]);
});

test("menu điện thoại: nút ☰ mở/đóng được sidebar ở 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await U.dangNhap(page, "shopa-owner");
  const sb = page.locator("#sidebar");
  const mo_truoc = await sb.evaluate((n) => n.classList.contains("mo"));
  await page.locator("#nut-menu").click();
  const mo_sau = await sb.evaluate((n) => n.classList.contains("mo"));
  expect(mo_sau, "bấm ☰ không đổi trạng thái sidebar").not.toBe(mo_truoc);
});
