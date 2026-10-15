// TẦNG 3 — PHÂN BIỆT QUYỀN TRÊN GIAO DIỆN (phép đo D-7 ở tầng mắt thấy).
//
// D-7 (15/10/2026) thêm ba quyền tài chính rời nhau: `tenant.taichinh.xem` / `.ghi` / `.duyet`.
// Nhân viên và người chỉ xem có `xem`, KHÔNG có `ghi`, KHÔNG có `duyet`.
//
// CHỐT THEO Ý ĐỊNH, không chốt theo trạng thái hiện tại: ca dưới đây không đòi "màn tài
// chính phải có" cũng không đòi "phải chưa có". Nó đòi hai thứ luôn đúng ở cả hai thì:
//   (1) quyền mà trình duyệt NHÌN THẤY phải khớp ma trận D-7;
//   (2) màn nào xuất hiện trên menu nhờ một quyền thì vai trò không có quyền đó KHÔNG
//       được thấy màn ấy, và vai trò chỉ có `xem` không được thấy nút ghi/duyệt trong đó.
// Khi AG-xx cắm màn tài chính vào menu, các ca này tự bắt đầu đo nó — không cần sửa file.
"use strict";
const { test, expect } = require("@playwright/test");
const U = require("./tien_ich");

test.describe.configure({ mode: "serial" });

/** Quyền mà CHÍNH TRÌNH DUYỆT đang giữ — đọc từ biến trạng thái của SPA, không gọi lại API.
 *  Cố ý: thứ cần đo là cái giao diện dùng để ẩn/hiện nút, không phải cái máy chủ trả. */
async function quyenTrenGiaoDien(page) {
  return page.evaluate(() => {
    // `TOI` là biến module-scope của admin.js, không ra window. Lấy qua chính API mà SPA đã gọi.
    return fetch("/api/v2/auth/toi").then((r) => r.json()).then((j) => j.quyen || []);
  });
}

const MA_TRAN_D7 = {
  "shopa-owner":  { xem: true,  ghi: true,  duyet: true },
  "shopa-staff":  { xem: true,  ghi: false, duyet: false },
  "shopa-viewer": { xem: true,  ghi: false, duyet: false },
};

for (const [ten, mong] of Object.entries(MA_TRAN_D7)) {
  test(`D-7 — quyền tài chính mà giao diện của ${ten} nhìn thấy`, async ({ page }) => {
    await U.dangNhap(page, ten);
    const q = await quyenTrenGiaoDien(page);
    expect(q.includes("tenant.taichinh.xem"), `${ten}: taichinh.xem`).toBe(mong.xem);
    expect(q.includes("tenant.taichinh.ghi"), `${ten}: taichinh.ghi`).toBe(mong.ghi);
    expect(q.includes("tenant.taichinh.duyet"), `${ten}: taichinh.duyet`).toBe(mong.duyet);
  });
}

test("D-7 — màn tài chính: ai xem được thì vào được, ai chỉ xem thì không có nút ghi/duyệt", async ({ page }) => {
  // Tìm màn tài chính trên MENU THẬT. Không có thì ca này ghi rõ là CHƯA ĐO ĐƯỢC và bỏ qua —
  // nói "đạt" cho một thứ chưa tồn tại là đúng dạng §12.1.
  await U.dangNhap(page, "shopa-staff");
  const menu = await U.docMenu(page);
  const tc = menu.filter((m) => /tai-chinh|taichinh|cod|doi-soat|cong-no|chenh-lech|dieu-chinh/.test(m.ma));
  test.skip(tc.length === 0,
    "CHƯA ĐO ĐƯỢC: không màn tài chính nào có trên menu — xem phát hiện P-1 trong docs/G12_PLAYWRIGHT.md");

  const loi = U.thuLoi(page);
  const co_nut_ghi = [];
  for (const m of tc) {
    await U.moMan(page, m.ma);
    const n = await page.locator('#man button, #man a.nut').evaluateAll((ns) =>
      ns.map((x) => x.textContent.trim())
        .filter((t) => /ghi|lưu|duyệt|nạp|điều chỉnh|xử lý|thanh toán|từ chối/i.test(t)));
    if (n.length) co_nut_ghi.push(`${m.ma}: ${n.join(", ")}`);
  }
  expect(co_nut_ghi, "nhân viên chỉ có taichinh.xem NHƯNG thấy nút ghi/duyệt").toEqual([]);
  expect(loi, "lỗi console ở màn tài chính").toEqual([]);
});

test("người chỉ xem: menu hẹp hơn chủ doanh nghiệp, và không có nút tạo đơn", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const menu_owner = (await U.docMenu(page)).map((m) => m.ma);
  await U.dangNhap(page, "shopa-viewer");
  const menu_viewer = (await U.docMenu(page)).map((m) => m.ma);

  expect(menu_viewer.length, "người chỉ xem thấy menu rộng bằng hoặc hơn chủ doanh nghiệp")
    .toBeLessThan(menu_owner.length);
  const thua = menu_viewer.filter((m) => !menu_owner.includes(m));
  expect(thua, "người chỉ xem thấy màn mà chủ doanh nghiệp không thấy").toEqual([]);

  await U.moMan(page, "don");
  expect(await page.locator("#d-them").count(),
         "người chỉ xem vẫn thấy nút ➕ Tạo đơn").toBe(0);
});

test("nhân viên: tạo được đơn nhưng không duyệt được (nút duyệt không hiện)", async ({ page }) => {
  await U.dangNhap(page, "shopa-staff");
  await U.moMan(page, "don");
  expect(await page.locator("#d-them").count(), "nhân viên không thấy nút tạo đơn").toBe(1);
  await page.locator("[data-xem]").first().click();
  await expect(page.locator("#ct-tab")).toBeVisible();
  expect(await page.locator("#ct-duyet").count(), "nhân viên thấy nút duyệt đơn").toBe(0);
  expect(await page.locator("#ct-tu-choi").count(), "nhân viên thấy nút từ chối đơn").toBe(0);
});
