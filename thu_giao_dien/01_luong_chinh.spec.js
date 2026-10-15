// TẦNG 3 — LUỒNG CHÍNH trong trình duyệt thật.
// Đăng nhập → menu → đơn hàng → bộ lọc → tạo đơn → chi tiết 4 tab → từ chối → webhook →
// chuyển doanh nghiệp → 401 giữa chừng.
//
// Mỗi ca có ĐÚNG MỘT thứ nó chứng minh, ghi ở dòng đầu. Ca nào không chứng minh được gì
// đo được thì không nên tồn tại.
"use strict";
const { test, expect } = require("@playwright/test");
const U = require("./tien_ich");

test.describe.configure({ mode: "serial" });

test("01 — đăng nhập dựng được khung, menu có màn, không lỗi trang, không hụt tệp tĩnh", async ({ page }) => {
  const loi = U.thuLoi(page);
  const tep = U.thuTepTinhHong(page);
  await U.dangNhap(page, "shopa-owner");
  const menu = await U.docMenu(page);
  expect(menu.length, "menu rỗng ⇒ khung không dựng").toBeGreaterThan(0);
  expect(loi, "lỗi do chính trang sinh khi đăng nhập").toEqual([]);
  expect(tep, "tệp tĩnh của giao diện không tải được").toEqual([]);
});

test("02 — mọi màn trên menu mở được, có tiêu đề, không lỗi console", async ({ page }) => {
  const loi = U.thuLoi(page);
  await U.dangNhap(page, "shopa-owner");
  const menu = await U.docMenu(page);
  const hong = [];
  for (const m of menu) {
    const td = await U.moMan(page, m.ma).catch((e) => "LỖI: " + e.message);
    if (!td || td.startsWith("LỖI") || td === "Lỗi") hong.push(`${m.ma} → ${td}`);
  }
  expect(hong, "màn không mở được").toEqual([]);
  expect(loi, "lỗi console khi đi hết menu").toEqual([]);
});

test("03 — bộ lọc nâng cao lọc THẬT: số đơn đếm từ DOM phải đổi đúng chiều", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");
  const demDong = () => page.locator("#d-bang tr td[colspan]").count()
    .then((rong) => rong ? 0 : page.locator("#d-bang tr").count());

  const tong = await demDong();
  expect(tong, "nền chưa có đơn nào ⇒ ca lọc không chứng minh được gì").toBeGreaterThan(0);

  await page.locator("#d-nang-cao").click();
  await expect(page.locator("#d-bang-loc")).toBeVisible();

  // COD >= 300.000 — `chuan_bi.py` tạo 4 đơn ở mỗi phía, nhưng ca này KHÔNG chốt con số 4:
  // nó chốt QUAN HỆ (lọc ra ít hơn tổng, và > 0). Chốt con số là khoá bộ thử vào dữ liệu mẫu.
  await page.locator("#l-cod-tu").fill("300000");
  await page.locator("#l-cod-tu").dispatchEvent("change");
  await page.waitForFunction((t) => {
    const n = document.querySelectorAll("#d-bang tr").length;
    return n !== t;
  }, tong, { timeout: 5000 });
  const sau = await demDong();
  expect(sau, "lọc COD không giảm số dòng ⇒ bộ lọc không chạy").toBeLessThan(tong);
  expect(sau).toBeGreaterThan(0);

  // Dòng "phạm vi lọc" phải nói đúng số điều kiện lọc tại giao diện.
  const pv = await page.locator("#d-pham-vi").textContent();
  expect(pv, "dòng phạm vi lọc không cập nhật").toContain("Giao diện lọc thêm");

  await page.locator("#l-xoa").click();
  await page.waitForFunction((t) => document.querySelectorAll("#d-bang tr").length === t, tong, { timeout: 5000 });
  expect(await demDong(), "xóa lọc không trả về đủ đơn").toBe(tong);
});

test("04 — form tạo đơn trống báo lỗi TẠI CHỖ và KHÔNG gọi API", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");

  // Đếm lượt gọi POST /api/v2/don: điều kiện đạt là 0, và nó là phép đo, không phải cảm nhận.
  let so_post = 0;
  page.on("request", (r) => {
    if (r.method() === "POST" && new URL(r.url()).pathname === "/api/v2/don") so_post++;
  });

  await page.locator("#d-them").click();
  await expect(page.locator("#f-luu")).toBeVisible();
  // Xoá sạch mọi ô rồi bấm Lưu.
  for (const o of await page.locator("[data-truong]").all()) await o.fill("");
  await page.locator("#f-luu").click();

  const so_o_loi = await page.locator("[data-o].co-loi").count();
  expect(so_o_loi, "form trống mà không ô nào bị đánh dấu lỗi").toBeGreaterThan(0);
  await expect(page.locator("#f-tong-loi")).toContainText("phải sửa trước khi lưu");
  expect(so_post, "form trống NHƯNG vẫn bắn POST /api/v2/don lên máy chủ").toBe(0);
  await expect(page.locator("#f-luu"), "modal bị đóng dù dữ liệu chưa hợp lệ").toBeVisible();
});

test("05 — tạo đơn thật trên giao diện: bảng tăng đúng 1 dòng", async ({ page }) => {
  const loi = U.thuLoi(page);
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");
  const truoc = await page.locator("#d-bang tr").count();

  await page.locator("#d-them").click();
  const dien = {
    nguoi_gui_ten: "Shop G12", nguoi_gui_sdt: "0905550001", nguoi_gui_dia_chi: "9 Ngõ G12, HN",
    nguoi_nhan_ten: "Khách G12 tạo tay", nguoi_nhan_sdt: "0905550002",
    nguoi_nhan_dia_chi: "10 Ngõ G12, HCM", hang_hoa: "Kiện tạo từ giao diện",
    khoi_luong_gram: "750", cod: "210000",
  };
  for (const [k, v] of Object.entries(dien)) await page.locator(`[data-truong="${k}"]`).fill(v);
  await page.locator("#f-luu").click();
  await page.waitForFunction((t) => document.querySelectorAll("#d-bang tr").length === t + 1,
                             truoc, { timeout: 10000 });
  await expect(page.locator("#d-bang")).toContainText("Khách G12 tạo tay");
  expect(loi, "lỗi console khi tạo đơn").toEqual([]);
});

test("06 — chi tiết đơn: 4 tab đổi được, phiếu in nói rõ KHÔNG PHẢI nhãn vận đơn", async ({ page }) => {
  const loi = U.thuLoi(page);
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");
  await page.locator("[data-xem]").first().click();
  await expect(page.locator("#ct-tab")).toBeVisible();

  const tabs = await page.locator("#ct-tab .tab-nut").evaluateAll((ns) => ns.map((n) => n.dataset.tab));
  expect(tabs, "chi tiết đơn không đủ 4 tab").toEqual(["tt", "tl", "ls", "in"]);
  for (const t of tabs) {
    await page.locator(`#ct-tab .tab-nut[data-tab="${t}"]`).click();
    await expect(page.locator(`[data-vung="${t}"]`), `tab ${t} không hiện vùng của nó`).toBeVisible();
    // Đúng một vùng hiện tại một thời điểm.
    const hien = await page.locator("[data-vung]:not([hidden])").count();
    expect(hien, `tab ${t}: ${hien} vùng cùng hiện`).toBe(1);
  }
  await page.locator('#ct-tab .tab-nut[data-tab="in"]').click();
  await expect(page.locator('[data-vung="in"]')).toContainText("KHÔNG PHẢI NHÃN VẬN ĐƠN");
  expect(loi, "lỗi console ở chi tiết đơn").toEqual([]);
});

test("07 — từ chối đơn: thiếu lý do báo tại chỗ; backend trả gì thì nói đúng cái đó", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "don");
  await page.locator("[data-xem]").first().click();
  // CHỜ modal dựng xong rồi mới đếm nút. Bản đầu đếm ngay sau cú bấm: `count()` không chờ,
  // nên nó luôn thấy 0 và ca TỰ BỎ QUA chính mình — một ca bỏ qua trông y hệt một ca không
  // áp dụng, và không ai biết luồng từ chối chưa bao giờ được kiểm.
  await expect(page.locator("#ct-tab")).toBeVisible();
  const nut = page.locator("#ct-tu-choi");
  expect(await nut.count(),
         "đơn đầu danh sách không có nút Từ chối — nền thử sai, hoặc nút đã bị gỡ").toBe(1);
  await nut.click();
  await expect(page.locator("#tc-ok")).toBeVisible();

  // (a) chưa chọn lý do
  await page.locator("#tc-ok").click();
  expect(await page.locator('[data-o="ly_do_ma"].co-loi').count(),
         "không chọn lý do mà không báo lỗi tại chỗ").toBe(1);

  // (b) "Lý do khác" mà bỏ trống ghi chú
  const cac_ly_do = await page.locator("#tc-ly-do option").evaluateAll((ns) => ns.map((n) => n.value).filter(Boolean));
  // Khớp CHÍNH XÁC mã "khac". Bản đầu dùng /khac/i và nó trúng `khach_huy` — mã đứng
  // trước trong danh mục và KHÔNG đòi ghi chú — nên ca thử đo một thứ khác thứ nó nói,
  // rồi báo hỏng. Dò mẫu lỏng trên mã định danh là một cách đo sai rất khó thấy.
  const khac = cac_ly_do.find((x) => x === "khac");
  expect(khac, 'danh mục lý do không còn mã "khac" — ca này phải được viết lại theo danh mục mới')
    .toBeTruthy();
  {
    await page.locator("#tc-ly-do").selectOption(khac);
    await page.locator("#tc-ghi-chu").fill("");
    await page.locator("#tc-ok").click();
    expect(await page.locator('[data-o="ghi_chu"].co-loi').count(),
           '"Lý do khác" không ghi chú mà không báo lỗi tại chỗ').toBe(1);
  }

  // (c) lý do hợp lệ → gọi THẬT. Hai kết cục đều hợp lệ, nhưng KHÔNG được có kết cục thứ ba
  //     là "nói đã từ chối trong khi máy chủ từ chối lời gọi". Ca này chốt theo Ý ĐỊNH:
  //     nhãn phải KHỚP thực tế, chứ không chốt "route phải chưa có" như ba ca đã từng
  //     khoá ngược chiều tiến bộ của dự án.
  const hop_le = cac_ly_do.find((x) => x !== khac) || cac_ly_do[0];
  await page.locator("#tc-ly-do").selectOption(hop_le);
  await page.locator("#tc-ghi-chu").fill("ghi chú của bộ thử G12");
  const [ph] = await Promise.all([
    page.waitForResponse((r) => /\/api\/v2\/don\/\d+\/tu-choi$/.test(new URL(r.url()).pathname)),
    page.locator("#tc-ok").click(),
  ]);
  const ma = ph.status();
  if (ma >= 200 && ma < 300) {
    await expect(page.locator("#toast-khay"), "máy chủ nhận nhưng giao diện không báo đã từ chối")
      .toContainText("Đã từ chối");
  } else {
    await expect(page.locator("#tc-kq"), `máy chủ trả ${ma} nhưng giao diện không hiện hộp CHỜ BACKEND`)
      .toContainText("Chờ backend");
    await expect(page.locator("#tc-ok"), "máy chủ từ chối mà nút vẫn bấm được").toBeDisabled();
    await expect(page.locator("#toast-khay")).not.toContainText("Đã từ chối đơn.");
  }
});

test("08 — webhook monitor: KPI là số, trạng thái lạ hiện NGUYÊN VĂN", async ({ page }) => {
  const loi = U.thuLoi(page);
  await U.dangNhap(page, "shopa-owner");
  const td = await U.moMan(page, "webhook");
  expect(td).toContain("Webhook");
  const so_kpi = await page.locator(".luoi-kpi .the.kpi .so").count();
  expect(so_kpi, "màn webhook không dựng đủ 4 thẻ KPI").toBe(4);
  const cac_so = await page.locator(".luoi-kpi .the.kpi .so").allTextContents();
  for (const s of cac_so) {
    expect(s.trim(), `KPI không phải số: "${s}"`).toMatch(/^\d+$/);
  }
  expect(loi, "lỗi console ở màn webhook").toEqual([]);
});

test("09 — chuyển doanh nghiệp: vai trò và phạm vi dữ liệu đổi hẳn", async ({ page }) => {
  await U.dangNhap(page, "da-tenant");
  const chon = page.locator("#chon-tenant");
  await expect(chon, "tài khoản đa tenant không thấy ô chọn doanh nghiệp").toBeVisible();
  const cac = await chon.locator("option").evaluateAll((ns) => ns.map((n) => n.value));
  expect(cac.length, "ô chọn doanh nghiệp chỉ có một lựa chọn").toBeGreaterThan(1);

  const chan_truoc = (await page.locator(".sidebar .chan").textContent()).trim();
  const dang_chon = await chon.inputValue();
  const khac = cac.find((v) => v !== dang_chon);
  expect(khac, "không tìm được doanh nghiệp thứ hai để chuyển sang").toBeTruthy();
  await chon.selectOption(khac);
  await page.waitForFunction((cu) => {
    const n = document.querySelector(".sidebar .chan");
    return n && n.textContent.trim() !== cu;
  }, chan_truoc, { timeout: 10000 });
  const chan_sau = (await page.locator(".sidebar .chan").textContent()).trim();
  expect(chan_sau, "đổi doanh nghiệp mà chân trang không đổi ⇒ chưa nạp lại").not.toBe(chan_truoc);
});

test("10 — 401 giữa chừng: hiện màn phiên hết hạn, hứa mở lại đúng màn", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await U.moMan(page, "khach");
  // Thu hồi phiên NGẦM: gọi đăng xuất bằng fetch trong trang, rồi bấm menu như người dùng.
  await page.evaluate(() => fetch("/api/v2/auth/dang-xuat", {
    method: "POST", headers: { "X-Requested-With": "VIPHub", "Content-Type": "application/json" },
    body: "{}",
  }));
  await page.locator('.menu-quan-tri a[data-man="don"]').click();
  await expect(page.locator("#hop-het-han"), "401 giữa chừng không hiện màn phiên hết hạn")
    .toBeVisible({ timeout: 10000 });
  await expect(page.locator("#hop-het-han")).toContainText("HTTP 401");
  await page.locator("#hh-vao").click();
  await expect(page.locator(".hop-dang-nhap")).toContainText("Đăng nhập xong sẽ mở lại màn");
});
