// Cấu hình Playwright — tầng 3 kiểm giao diện. Xem docs/G12_PLAYWRIGHT.md.
//
// CHẠY TUẦN TỰ, cố ý: bộ thử tạo đơn THẬT trên một nền dùng chung cho cả lượt chạy. Chạy
// song song thì hai ca cùng đếm bảng đơn và đạp số của nhau — và một bộ thử báo hỏng giả
// là kiểu sai tệ nhất với một cổng chặn hồi quy.
//
// KHÔNG `webServer`: máy chủ do `thu_giao_dien/chay.sh` dựng trên nền CÔ LẬP và tắt theo
// đúng PID. Để Playwright tự khởi động máy chủ là giao việc tắt tiến trình cho một thứ
// không biết luật §16.7 của dự án.
const { defineConfig, devices } = require("@playwright/test");

const GOC = process.env.VIP_GD_GOC;
if (!GOC) {
  throw new Error(
    "Thiếu VIP_GD_GOC. Bộ thử này KHÔNG tự dựng máy chủ — chạy qua `sh thu_giao_dien/chay.sh`.\n" +
    "Dựng nền bằng tay rồi chạy thẳng `npx playwright test` sẽ bắn vào CSDL đang dùng.");
}

module.exports = defineConfig({
  testDir: "./thu_giao_dien",
  testMatch: /.*\.spec\.js$/,
  fullyParallel: false,
  workers: 1,
  forbidOnly: true,
  retries: 0,              // không thử lại: một ca chập chờn phải LỘ RA, không được giấu
  timeout: 30_000,         // mỗi ca
  expect: { timeout: 5_000 },
  reporter: [["list"], ["html", { outputFolder: "thu_giao_dien/_bao-cao", open: "never" }]],
  outputDir: "thu_giao_dien/_ket-qua",
  use: {
    baseURL: GOC,
    headless: true,
    screenshot: "only-on-failure",   // ảnh để NGƯỜI xem, không bao giờ là điều kiện đạt
    video: "off",
    trace: "retain-on-failure",
    actionTimeout: 7_000,
    navigationTimeout: 15_000,
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 900 } } },
  ],
});
