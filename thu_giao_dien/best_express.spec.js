// TẦNG 3 — BEST EXPRESS (AGENT B4): 12 màn, 5 trạng thái, credential an toàn, không gọi hãng.
//
// PHẠM VI — đọc trước khi tin bất kỳ con số nào:
//   - Chromium ĐÃ GHIM: `node_modules/playwright-core/.local-browsers/chromium_headless_shell-1194/
//     chrome-mac/headless_shell` · 141.0.7390.37 · sha256 a9752d88…fa3040. Ca 00 đo lại cả hai.
//   - Chạy LOCAL trên nền cô lập của `thu_giao_dien/chay.sh` (SQLite tmp, cổng ngẫu nhiên,
//     bind 127.0.0.1). KHÔNG gọi API hãng BEST ở bất kỳ môi trường nào; KHÔNG tạo đơn thật.
//   - Các đường BEST CHƯA CÓ trong máy chủ nội bộ (kiểm tra kết nối, credential BEST) được
//     MOCK bằng `page.route`. Vì vậy các ca ấy là **MOCK PASS**, KHÔNG phải REAL PASS với hãng.
//     Các đường đã có (đơn, hành trình, webhook, audit, hãng) được đo bằng API THẬT trên nền
//     cô lập — chỗ nào dùng mock đều ghi rõ trong tên ca / thông điệp.
//   - MỌI CA CÓ ĐỐI CHỨNG ÂM: mỗi khẳng định "đúng" đi kèm một khẳng định "sai phải bị bắt"
//     (ví dụ: payload credential-only khai da_ket_noi KHÔNG được hiện ĐÃ KẾT NỐI; canary bí
//     mật PHẢI có trong request nhưng KHÔNG được có trong DOM).
"use strict";
const { test, expect } = require("@playwright/test");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const crypto = require("node:crypto");
const U = require("./tien_ich");

const GOC = join(__dirname, "..");
const CHUOI_GHIM = "a9752d8852a3972a07e4cddf63fa37019606336de0201631147519c732fa3040";
const DUONG_GHIM = join(GOC, "node_modules", "playwright-core", ".local-browsers",
  "chromium_headless_shell-1194", "chrome-mac", "headless_shell");

const MAN_BEST = [
  ["best-danh-sach-hang", "BEST · Danh sách hãng"],
  ["best-cau-hinh-tai-khoan", "BEST · Cấu hình tài khoản"],
  ["best-kiem-tra-ket-noi", "BEST · Kiểm tra kết nối"],
  ["best-tao-don", "BEST · Tạo đơn"],
  ["best-van-don", "BEST · Danh sách vận đơn"],
  ["best-chi-tiet-don", "BEST · Chi tiết đơn"],
  ["best-lich-su-van-chuyen", "BEST · Lịch sử vận chuyển"],
  ["best-tra-cuu-hanh-trinh", "BEST · Tra cứu hành trình"],
  ["best-tinh-cuoc", "BEST · Tính cước"],
  ["best-in-van-don", "BEST · In vận đơn"],
  ["best-theo-doi-webhook", "BEST · Theo dõi webhook"],
  ["best-nhat-ky-loi", "BEST · Nhật ký lỗi đồng bộ"],
];

const PROVIDER_BEST = {
  ma: "best", ten: "BEST Express",
  capabilities: {
    createOrder: true, cancelOrder: true, getOrder: false, trackOrder: true,
    getShippingFee: true, getShippingLabel: true, webhook: true,
  },
  live_mo: false,
};

const json = (than, ma) => ({
  status: ma || 200,
  contentType: "application/json; charset=utf-8",
  body: JSON.stringify(than),
});

/** Tài khoản BEST có credential nhưng CHƯA có bằng chứng đăng nhập API. */
function tkChoXacMinh(them) {
  return Object.assign({
    id: 77, hang: "best", ten: "BEST mock của Shop Demo A", moi_truong: "mock",
    credentials_doi_luc: "2026-10-19 10:00:00+0700", webhook_ma: "WH-BEST-THU",
    kich_hoat: 1, tao_luc: "2026-10-19 09:00:00+0700",
  }, them || {});
}

const gon = (s) => String(s == null ? "" : s).replace(/\s+/g, " ").trim();

/** Đặt nền hãng/tài khoản bằng route MOCK (BEST chưa có adapter ở backend). */
async function datNenBest(page, tuyChon) {
  const o = tuyChon || {};
  await page.unroute("**/api/v2/hang").catch(() => {});
  await page.unroute("**/api/v2/tai-khoan-hang").catch(() => {});
  await page.route("**/api/v2/hang", (r) => r.fulfill(json({ hang: o.hang || [PROVIDER_BEST] })));
  await page.route("**/api/v2/tai-khoan-hang", (r) => {
    if (r.request().method() === "GET") {
      return r.fulfill(json({ tai_khoan: o.tai_khoan || [] }));
    }
    return r.fulfill(json({ loi: "ca thử này không dùng POST tạo tài khoản" }, 400));
  });
}

async function moBest(page, ma) {
  return U.moMan(page, ma);
}

/** Đọc trạng thái đang hiện trên màn (data-best-state + nhãn). */
async function docTrangThai(page) {
  const n = page.locator("[data-best-state]").first();
  await expect(n).toBeVisible();
  return {
    ma: await n.getAttribute("data-best-state"),
    chu: gon(await n.textContent()),
  };
}

// ============================================================================================
// 00 — BINARY ĐÃ GHIM: đo hash + phiên bản trình duyệt thật
// ============================================================================================
test("00 — Chromium đúng binary đã ghim (sha256 + version)", async ({ browser }) => {
  const bam = crypto.createHash("sha256").update(readFileSync(DUONG_GHIM)).digest("hex");
  expect(bam, `sha256 của ${DUONG_GHIM} khác chuỗi ghim`).toBe(CHUOI_GHIM);
  expect(browser.version(), "phiên bản Chromium khác bản đã ghim").toBe("141.0.7390.37");

  // ĐỐI CHỨNG ÂM: hash của một tệp KHÁC trong cùng gói phải khác — nếu không, phép đo
  // "hash khớp" có thể chỉ là một hằng số dán vào chứ không phải băm thật của binary.
  const bamKhac = crypto.createHash("sha256")
    .update(readFileSync(join(DUONG_GHIM, "..", "icudtl.dat"))).digest("hex");
  expect(bamKhac, "hai tệp khác nhau lại cùng hash — phép đo hash vô nghĩa").not.toBe(bam);
});

// ============================================================================================
// 01 — 12 MÀN CÓ TRÊN MENU THẬT VÀ MỞ ĐƯỢC
// ============================================================================================
test("01 — 12 màn BEST có trên MENU THẬT; mở đủ 12, tiêu đề khớp", async ({ page }) => {
  const loi = U.thuLoi(page);
  await U.dangNhap(page, "shopa-owner");
  const menu = await U.docMenu(page);
  const best = menu.filter((m) => m.ma.startsWith("best-"));

  expect(best.length, `menu có ${best.length} mục best-*, cần đúng 12`).toBe(12);
  const idMenu = new Set(best.map((m) => m.ma));
  for (const [ma] of MAN_BEST) expect(idMenu.has(ma), `thiếu mục menu ${ma}`).toBe(true);

  // ĐỐI CHỨNG ÂM: một mã màn KHÔNG tồn tại không được có trên menu — nếu có, phép đếm 12
  // phía trên có thể đang đếm một màn rác thay vì màn thật.
  expect(idMenu.has("best-khong-ton-tai")).toBe(false);

  // Yêu cầu 4: BEST phải nằm trong DANH SÁCH HÃNG, cạnh J&T và Viettel Post. Đo bằng chữ
  // trên bảng thật (nguồn: `GET /api/v2/hang`), không tin rằng bảng có tên màn.
  await moBest(page, "best-danh-sach-hang");
  const bangHang = gon(await page.locator("#best-bang-hang").innerText());
  expect(bangHang, "bảng hãng thiếu BEST Express").toContain("BEST Express");
  expect(bangHang, "bảng hãng thiếu J&T Express (API thật)").toContain("J&T Express");
  expect(bangHang, "bảng hãng thiếu Viettel Post (API thật)").toContain("Viettel Post");
  expect(bangHang, "BEST đã có provider nhưng bảng không nói rõ").toContain("đã có provider");
  expect(bangHang, "BEST chưa cấu hình mà không ghi CHƯA CẤU HÌNH").toContain("CHƯA CẤU HÌNH");
  // ĐỐI CHỨNG ÂM: một tên hãng KHÔNG có trong API không được xuất hiện — nếu có, bảng có thể
  // đang vẽ từ dữ liệu cứng thay vì đọc API.
  expect(bangHang).not.toContain("HANG-KHONG-CO-9Q7Z");

  for (const [ma, tieuDe] of MAN_BEST) {
    const t = await moBest(page, ma);
    expect(t, `màn ${ma} mở ra tiêu đề khác`).toBe(tieuDe);
    const noiDung = await page.locator("#man").innerText();
    expect(noiDung.length, `màn ${ma} dựng nội dung rỗng`).toBeGreaterThan(80);
  }
  expect(loi, "lỗi console khi mở 12 màn BEST").toEqual([]);
});

// ============================================================================================
// 02 — NĂM TRẠNG THÁI, VÀ LUẬT CHỐNG "NÓI DỐI LÀ ĐÃ KẾT NỐI"
// ============================================================================================
test("02 — 5 trạng thái đúng; credential-only KHÔNG được hiện ĐÃ KẾT NỐI", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  // Mở một màn BEST lần đầu để nạp `admin/best.js` (module được nạp theo yêu cầu).
  await moBest(page, "best-danh-sach-hang");
  await page.evaluate(() => window.VIPBEST && window.VIPBEST.xoaCache());

  const ca = [
    {
      ten: "CHUA_CAU_HINH", tai_khoan: [], mong: "chua_cau_hinh",
      am: "không có tài khoản mà lại hiện trạng thái khác",
    },
    {
      ten: "CHO_XAC_MINH", tai_khoan: [tkChoXacMinh()], mong: "cho_xac_minh",
      am: "chỉ lưu credential mà lại hiện ĐÃ KẾT NỐI",
    },
    {
      ten: "DA_KET_NOI", tai_khoan: [tkChoXacMinh({
        kiem_ket_noi: { ok: true, luc: "2026-10-19 10:05:00+0700", tre_ms: 42, ma_http: 200 },
      })], mong: "da_ket_noi",
      am: "có bằng chứng ok=true mà lại không hiện ĐÃ KẾT NỐI",
    },
    {
      ten: "MAT_KET_NOI", tai_khoan: [tkChoXacMinh({
        da_tung_ket_noi: true,
        kiem_ket_noi: { ok: false, luc: "2026-10-19 10:06:00+0700", ma_http: 503, loi: "hãng không phản hồi" },
      })], mong: "mat_ket_noi",
      am: "từng kết nối rồi thất bại mà lại hiện CHỜ XÁC MINH",
    },
    {
      ten: "CAN_XU_LY", tai_khoan: [tkChoXacMinh({
        kiem_ket_noi: { ok: false, luc: "2026-10-19 10:06:00+0700", ma_http: 401, loi: "sai credential" },
      })], mong: "can_xu_ly",
      am: "lỗi xác thực lần đầu mà lại hiện MẤT KẾT NỐI/ĐÃ KẾT NỐI",
    },
  ];

  const daThay = new Set();
  for (const c of ca) {
    await datNenBest(page, { tai_khoan: c.tai_khoan });
    await page.evaluate(() => window.VIPBEST && window.VIPBEST.xoaCache());
    await moBest(page, "best-danh-sach-hang");
    const st = await docTrangThai(page);
    console.log(`[đo] ${c.ten}: ${st.ma} — ${st.chu}`);
    expect(st.ma, `${c.ten}: ${c.am}`).toBe(c.mong);
    expect(st.chu.length, `${c.ten}: nhãn trạng thái rỗng`).toBeGreaterThan(3);
    daThay.add(st.ma);
  }
  expect(daThay.size, "năm trạng thái không phân biệt được bằng mã — bảng trạng thái vô nghĩa").toBe(5);

  // ĐỐI CHỨNG ÂM QUAN TRỌNG NHẤT: backend KHAI "da_ket_noi" nhưng KHÔNG kèm bằng chứng
  // đăng nhập API. Giao diện phải giữ CHỜ XÁC MINH và hiện cảnh báo — không được tin lời khai.
  await datNenBest(page, {
    tai_khoan: [tkChoXacMinh({ trang_thai_ket_noi: "da_ket_noi" })],
  });
  await page.evaluate(() => window.VIPBEST && window.VIPBEST.xoaCache());
  await moBest(page, "best-danh-sach-hang");
  const khaiSuong = await docTrangThai(page);
  expect(khaiSuong.ma, "backend khai da_ket_noi mà không có bằng chứng — giao diện đã TIN LỜI KHAI")
    .toBe("cho_xac_minh");
  expect(khaiSuong.ma, "ĐÃ KẾT NỐI chỉ được phép khi có ok=true + thời điểm").not.toBe("da_ket_noi");
  await expect(page.locator("#best-canh-bao-tt")).toContainText("thiếu bằng chứng");
});

// ============================================================================================
// 03 — CẤU HÌNH CREDENTIAL AN TOÀN (MOCK POST) — chặn HTTP, không lộ secret
// ============================================================================================
test("03 — bàn nghiệm thu: ô credential là password/rỗng; không lộ secret ra DOM", async ({ page }) => {
  const CANARY = "BEST-CANARY-SECRET-9Q7Z-DO-NOT-LEAK";
  const CANARY_EMS = "BEST-EMS-SECRET-4X8K-DO-NOT-LEAK";
  let soLanPost = 0;
  let thanPost = "";

  await page.route("**/api/v2/tai-khoan-hang", (r) => {
    if (r.request().method() === "GET") return r.fulfill(json({ tai_khoan: [] }));
    soLanPost += 1;
    thanPost = r.request().postData() || "";
    return r.fulfill(json({ id: 91, webhook_ma: "WH-MOI", webhook_url: "/api/v2/webhook/nhan/WH-MOI",
                            webhook_url_cong_khai: false }, 201));
  });
  await page.route("**/api/v2/best/trang-thai", (r) => r.fulfill(json({
    hop_dong: { so_ma: 23, service_id: 12491, token_ttl_days: 30,
                gioi_han: { query: 10, print: 50 }, nguon: "DOCX", endpoints: {} },
    co_phe_duyet_owner: true, co_ma_phe_duyet: true,
    tai_khoan: [], tls: null, public_base_url: "",
  })));

  await U.dangNhap(page, "shopa-owner");
  await page.goto("/pages/best-uat.html");
  await expect(page.locator("#auth")).toContainText("Đã đăng nhập");

  for (const id of ["tk-pass", "tk-ems"]) {
    const o = page.locator("#" + id);
    await expect(o).toHaveAttribute("type", "password");
    expect(await o.inputValue(), `${id} có value dựng sẵn`).toBe("");
  }

  await page.locator("#tk-ten").fill("BEST kiểm thử");
  await page.locator("#tk-user").fill("uat-user");
  await page.locator("#tk-pass").fill(CANARY);
  await page.locator("#tk-ems").fill(CANARY_EMS);
  await page.locator("#form-tk").evaluate((f) => f.requestSubmit());
  await expect.poll(() => soLanPost, { timeout: 5000 }).toBe(1);
  expect(thanPost, "request không mang credential").toContain(CANARY);
  expect(thanPost, "request không mang ems-key").toContain(CANARY_EMS);

  const html = await page.locator("body").innerHTML();
  const chu = await page.locator("body").innerText();
  for (const biMat of [CANARY, CANARY_EMS]) {
    expect(html, `secret lọt vào innerHTML: ${biMat}`).not.toContain(biMat);
    expect(chu, `secret lọt vào chữ trên màn: ${biMat}`).not.toContain(biMat);
  }
  expect(await page.locator("#tk-pass").inputValue(), "secret còn trong ô sau khi gửi").toBe("");
  expect(await page.locator("#tk-ems").inputValue(), "ems-key còn trong ô sau khi gửi").toBe("");
  expect(chu).toContain("BEST");
});

// ============================================================================================
// 04 — KIỂM TRA KẾT NỐI: thất bại KHÔNG xanh; 404 KHÔNG tự nâng trạng thái
// ============================================================================================
test("04 — bàn nghiệm thu: 401 → THẤT BẠI; ok=true → ĐĂNG NHẬP THÀNH CÔNG", async ({ page }) => {
  let lan = 0;
  const tk = {
    id: 88, hang: "best", ten: "BEST sandbox", moi_truong: "sandbox", kich_hoat: 1,
    co_credentials: true, credentials_doi_luc: "2026-10-19 10:00:00+0700",
    webhook_ma: "WH-88", webhook_url: "/api/v2/webhook/nhan/WH-88",
    webhook_bearer: { co_bearer: true, doc_duoc: true },
  };
  await page.route("**/api/v2/tai-khoan-hang", (r) => r.fulfill(json({ tai_khoan: [tk] })));
  await page.route("**/api/v2/best/trang-thai", (r) => r.fulfill(json({
    hop_dong: { so_ma: 23, service_id: 12491, token_ttl_days: 30,
                gioi_han: { query: 10, print: 50 }, nguon: "DOCX", endpoints: {},
                bang_ma: {} },
    co_phe_duyet_owner: true, co_ma_phe_duyet: true,
    tai_khoan: [tk], tls: null, public_base_url: "",
  })));
  await page.route("**/api/v2/best/kiem-ket-noi", (r) => {
    lan += 1;
    if (lan === 1) {
      return r.fulfill(json({ ok: false, co_token: false, blocked: false,
                              moi_truong: "sandbox", endpoint: "/User/Login",
                              meta: { endpoint: "/User/Login", http_status: 401 },
                              loi: "[401] Invalid username or password" }, 401));
    }
    return r.fulfill(json({ ok: true, co_token: true, blocked: false,
                            moi_truong: "sandbox", endpoint: "/User/Login",
                            meta: { endpoint: "/User/Login", http_status: 200 },
                            tls: { ok: true, tls: "TLSv1.2", cn: "*.800best.com" }, loi: "" }));
  });

  await U.dangNhap(page, "shopa-owner");
  await page.goto("/pages/best-uat.html");
  await expect(page.locator("#kn-tk option")).toHaveCount(1);
  await page.locator("#phe-duyet-that").check();
  await page.locator("#kn-xac-nhan").selectOption("1");
  await page.locator("#btn-kiem-ket-noi").click();
  await expect(page.locator("#kq-ket-noi")).toContainText("THẤT BẠI");
  await expect(page.locator("#kq-ket-noi")).toContainText("Invalid username");

  await page.locator("#btn-kiem-ket-noi").click();
  await expect(page.locator("#kq-ket-noi")).toContainText("ĐĂNG NHẬP THÀNH CÔNG");
  await expect(page.locator("#kq-ket-noi")).toContainText("TLSv1.2");
  expect(lan, "không chạm đủ hai lượt gọi mock").toBe(2);
});

// ============================================================================================
// 05 — TÍNH CƯỚC: có phép tính khối lượng, KHÔNG bịa giá cước
// ============================================================================================
test("05 — tính cước: khối lượng quy đổi đúng; KHÔNG có số tiền BEST bịa", async ({ page }) => {
  const yeuCau = [];
  page.on("request", (r) => yeuCau.push(r.url()));
  await U.dangNhap(page, "shopa-owner");
  await moBest(page, "best-tinh-cuoc");

  await page.locator("#best-tinh-khoi-luong").click();
  const kq = gon(await page.locator("#best-kq-khoi-luong").innerText());
  console.log("[đo] khối lượng:", kq);
  expect(kq, "30×20×10 cm phải quy đổi thành 1000 g").toContain("1000 g");
  expect(kq, "800 g thực < 1000 g quy đổi ⇒ tính cước 1000 g").toContain("Khối lượng tính cước: 1000 g");

  // ĐỐI CHỨNG ÂM: khu vực báo giá KHÔNG được có số tiền. Nếu có "… ₫" thì giao diện đang bịa
  // giá cước khi chưa có biểu cước/đường API đã xác nhận.
  const gia = gon(await page.locator("#best-gia-best").innerText());
  expect(gia).toContain("bàn nghiệm thu");
  expect(/\d[\d.,]*\s*₫/.test(gia), `khu báo giá có số tiền bịa: ${gia}`).toBe(false);

  // ĐỐI CHỨNG ÂM phụ: không có request nào tới đường "tinh-cuoc" đoán trước.
  expect(yeuCau.some((u) => /tinh-cuoc/i.test(u)), "giao diện gọi endpoint tính cước CHƯA XÁC NHẬN").toBe(false);

  // ĐỐI CHỨNG DƯƠNG: hàm thuần từ chối đầu vào vô lý thay vì trả 0.
  const voLy = await page.evaluate(() => window.VIPBEST.tinhKhoiLuongQuyDoi(0, 20, 10, 500));
  expect(voLy).toBe(null);
});

// ============================================================================================
// 05b — TẠO ĐƠN: kiểm dữ liệu THẬT, nhưng KHÔNG tạo đơn / KHÔNG gửi hãng
// ============================================================================================
test("05b — tạo đơn: kiểm dữ liệu thật (hợp lệ/không hợp lệ), không POST tạo đơn", async ({ page }) => {
  const posts = [];
  page.on("request", (r) => {
    if (r.method() === "POST") {
      try { posts.push(new URL(r.url()).pathname); } catch { posts.push(r.url()); }
    }
  });

  await U.dangNhap(page, "shopa-owner");
  await moBest(page, "best-tao-don");

  const dien = async (giaTri) => {
    for (const [id, v] of Object.entries(giaTri)) await page.locator("#" + id).fill(String(v));
  };
  await dien({
    "best-dn-nguoi-gui-ten": "Shop Demo A", "best-dn-nguoi-gui-sdt": "0901111111",
    "best-dn-nguoi-gui-dia-chi": "1 Đường Thử, Hà Nội",
    "best-dn-nguoi-nhan-ten": "Khách BEST", "best-dn-nguoi-nhan-sdt": "0902223333",
    "best-dn-nguoi-nhan-dia-chi": "2 Phố Thử, TP.HCM",
    "best-dn-hang-hoa": "Kiện thử BEST", "best-dn-khoi-luong": "500",
  });

  // ĐỐI CHỨNG DƯƠNG: dữ liệu hợp lệ ⇒ backend nói HỢP LỆ (đường kiểm THẬT).
  await page.locator("#best-kiem-don").click();
  await expect(page.locator("#best-kq-kiem")).toContainText("DỮ LIỆU HỢP LỆ");

  // ĐỐI CHỨNG ÂM: xoá một trường bắt buộc ⇒ CHƯA HỢP LỆ, và lỗi phải nêu đúng trường.
  await page.locator("#best-dn-nguoi-nhan-ten").fill("");
  await page.locator("#best-kiem-don").click();
  await expect(page.locator("#best-kq-kiem")).toContainText("DỮ LIỆU CHƯA HỢP LỆ");
  await expect(page.locator("#best-kq-kiem")).toContainText("nguoi_nhan_ten");

  // ĐỐI CHỨNG ÂM QUAN TRỌNG: KHÔNG có request tạo đơn/gửi hãng nào. Màn này chỉ kiểm.
  expect(posts.filter((p) => p === "/api/v2/don" || /\/don\/\d+\/(gui|duyet)$/.test(p)),
    `đã gọi đường ghi đơn: ${posts.join(" · ")}`).toEqual([]);
  expect(posts, "không thấy POST /api/v2/don/kiem ⇒ phép kiểm không thật sự chạy")
    .toContain("/api/v2/don/kiem");

  // Nút gửi BEST phải KHOÁ và nói rõ CHỜ BACKEND — không được tạo đơn thật.
  expect(await page.locator("#best-gui-don").isDisabled(), "nút gửi BEST không bị khoá").toBe(true);
  await expect(page.locator("#best-ly-do-gui")).toContainText("ĐÃ KẾT NỐI");
});


test("06 — vận đơn: BEST rỗng nói rõ lý do; chọn Tất cả đọc đơn thật; chi tiết + hành trình khớp API", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const don = await page.evaluate(async () => {
    const r = await fetch("/api/v2/don?gioi_han=5", { headers: { "X-Requested-With": "VIPHub" } });
    return (await r.json()).don || [];
  });
  expect(don.length, "nền cô lập không có đơn nào ⇒ ca này không đo được gì").toBeGreaterThan(0);
  const d0 = don[0];

  await moBest(page, "best-van-don");
  // ĐỐI CHỨNG ÂM: mặc định lọc BEST ⇒ không có dòng DỮ LIỆU nào, nhưng PHẢI có câu giải thích
  // (không phải màn hỏng). Bảng rỗng vẫn có đúng MỘT dòng chứa `.trang-thai-rong`.
  await expect(page.locator("#best-bang-don .trang-thai-rong")).toBeVisible();
  const rong = gon(await page.locator("#best-bang-don .trang-thai-rong").innerText());
  expect(rong.length, "ô rỗng không nói lý do — người dùng không phân biệt được chưa có đơn với màn hỏng")
    .toBeGreaterThan(20);
  expect(rong).toMatch(/BEST|CHỜ BACKEND/i);

  // ĐỐI CHỨNG DƯƠNG: chọn "Tất cả đơn" ⇒ đọc được dữ liệu thật.
  await page.selectOption("#best-loc-hang", "tat_ca");
  await expect.poll(async () => {
    const chu = await page.locator("#best-bang-don").innerText();
    return chu.includes(d0.ma_don);
  }, { timeout: 10000 }).toBe(true);
  const soDong = await page.locator("#best-bang-don tbody tr").count();
  expect(soDong, "chọn Tất cả vẫn không có dòng dữ liệu nào").toBeGreaterThan(0);

  // Bấm "Chi tiết" trên dòng đầu ⇒ màn chi tiết phải chứa đúng mã đơn mà API vừa trả.
  await page.locator("#best-bang-don tbody tr").first().locator("[data-best-don]").click();
  await expect(page.locator("#tieu-de")).toHaveText("BEST · Chi tiết đơn");
  await expect(page.locator("#man")).toContainText(d0.ma_don);

  // ĐỐI CHỨNG ÂM: ID không tồn tại phải báo lỗi, không được dựng một đơn rỗng trông như thật.
  await page.locator("#best-don-id").fill("999999");
  await page.locator("#best-mo-don").click();
  await expect(page.locator(".hop-loi")).toContainText("không có đơn này");

  // Quay lại chi tiết đơn thật rồi mở hành trình.
  await page.locator("#best-don-id").fill(String(d0.id));
  await page.locator("#best-mo-don").click();
  await expect(page.locator("#man")).toContainText(d0.ma_don);
  await page.locator('[data-best-di="best-lich-su-van-chuyen"]').click();
  await expect(page.locator("#tieu-de")).toHaveText("BEST · Lịch sử vận chuyển");
  const ht = await page.evaluate(async (id) => {
    const r = await fetch(`/api/v2/don/${id}/hanh-trinh`, { headers: { "X-Requested-With": "VIPHub" } });
    return r.json();
  }, d0.id);
  await expect(page.locator("#best-hanh-trinh, #man .trang-thai-rong").first()).toBeVisible();
  const chuHt = gon(await page.locator("#man").innerText());
  expect(chuHt, "màn hành trình không chứa mã đơn API trả").toContain(d0.ma_don);
  expect(chuHt, "số mốc trên màn không khớp API").toContain(String(ht.so_moc));
});

// ============================================================================================
// 07 — TRA CỨU HÀNH TRÌNH: dương có kết quả, âm không bịa dòng
// ============================================================================================
test("07 — tra cứu: mã đơn thật ra kết quả; mã rác ra rỗng có lý do", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const d0 = await page.evaluate(async () => {
    const r = await fetch("/api/v2/don?gioi_han=1", { headers: { "X-Requested-With": "VIPHub" } });
    return ((await r.json()).don || [])[0];
  });
  expect(d0 && d0.ma_don, "không đọc được đơn mẫu").toBeTruthy();

  await moBest(page, "best-tra-cuu-hanh-trinh");
  await page.locator("#best-ma-tra-cuu").fill(d0.ma_don);
  await page.locator("#best-nut-tra-cuu").click();
  await expect(page.locator("#best-bang-tra-cuu")).toBeVisible();
  await expect(page.locator("#best-bang-tra-cuu")).toContainText(d0.ma_don);

  // ĐỐI CHỨNG ÂM: từ khoá không tồn tại ⇒ bảng không có dòng dữ liệu, có câu giải thích.
  await page.locator("#best-ma-tra-cuu").fill("KHONG-CO-MA-NAY-9Q7Z");
  await page.locator("#best-nut-tra-cuu").click();
  await expect(page.locator("#best-bang-tra-cuu .trang-thai-rong")).toBeVisible();
  const rong = gon(await page.locator("#best-bang-tra-cuu .trang-thai-rong").innerText());
  expect(rong.length).toBeGreaterThan(20);
  expect(rong).toMatch(/Không tìm thấy/);
});

// ============================================================================================
// 08 — IN VẬN ĐƠN: nhãn giả bị khoá, nhãn thật mới mở (MOCK metadata)
// ============================================================================================
test("08 — in vận đơn: nhan_that=false ⇒ watermark + nút khoá; nhan_that=true ⇒ mở", async ({ page }) => {
  let nhanThat = false;
  await page.route(/\/api\/v2\/don\/\d+\/nhan$/, (r) => {
    return r.fulfill(json(nhanThat ? {
      don_id: 1, ma_don: "T1-000001", ma_van_don: "BEST-VD-001", hang: "best",
      ten_hang: "BEST Express", moi_truong: "sandbox", la_mock: false, ho_tro_nhan: true,
      nhan_that: true, dinh_dang: "pdf", do_lon_byte: 1234, canh_bao: [],
    } : {
      don_id: 1, ma_don: "T1-000001", ma_van_don: "BEST-VD-001", hang: "best",
      ten_hang: "BEST Express", moi_truong: "mock", la_mock: true, ho_tro_nhan: true,
      nhan_that: false, dinh_dang: null, do_lon_byte: null,
      canh_bao: ["nhãn này là MOCK — không in được, không phải nhãn hãng"],
    }));
  });

  await U.dangNhap(page, "shopa-owner");
  await moBest(page, "best-in-van-don");
  await page.locator("#best-don-id").fill("1");
  await page.locator("#best-mo-don").click();
  await expect(page.locator("#best-khoi-nhan")).toBeVisible();

  // ĐỐI CHỨNG ÂM: nhãn mock ⇒ watermark rõ ràng + nút in KHOÁ.
  await expect(page.locator(".best-watermark")).toContainText("KHÔNG PHẢI NHÃN HÃNG");
  expect(await page.locator("#best-in-nhan").isDisabled(), "in nhãn mock mà nút vẫn mở").toBe(true);

  // ĐỐI CHỨNG DƯƠNG: backend khai nhãn thật ⇒ nút mở, watermark biến mất.
  nhanThat = true;
  await page.locator("#best-mo-don").click();
  await expect(page.locator("#best-in-nhan")).toBeEnabled();
  await expect(page.locator(".best-watermark")).toHaveCount(0);
});

// ============================================================================================
// 09 — THEO DÕI WEBHOOK: chỉ sự kiện BEST, không lẫn J&T (MOCK payload)
// ============================================================================================
test("09 — webhook: lọc đúng BEST; sự kiện J&T KHÔNG được hiện", async ({ page }) => {
  const suKien = [
    { id: 1, event_id: "BEST-EV-001", nhan_luc: "2026-10-19 10:00:00", trang_thai: "DA_XU_LY",
      so_lan_thu: 1, loi_cuoi: null, hang: "best", ten_tk: "BEST mock", can_soat: 0 },
    { id: 2, event_id: "BEST-EV-002", nhan_luc: "2026-10-19 10:01:00", trang_thai: "LOI",
      so_lan_thu: 3, loi_cuoi: "không ánh xạ được trạng thái", hang: "best", ten_tk: "BEST mock", can_soat: 1 },
    { id: 3, event_id: "JT-EV-KHONG-DUOC-HIEN", nhan_luc: "2026-10-19 10:02:00", trang_thai: "DA_XU_LY",
      so_lan_thu: 1, loi_cuoi: null, hang: "jt", ten_tk: "J&T mock", can_soat: 0 },
  ];
  await page.route("**/api/v2/webhook/su-kien*", (r) => r.fulfill(json({ su_kien: suKien, co_cot_soat: true })));

  await U.dangNhap(page, "shopa-owner");
  await moBest(page, "best-theo-doi-webhook");
  await expect(page.locator("#best-bang-webhook")).toBeVisible();
  const soDong = await page.locator("#best-bang-webhook tbody tr").count();
  expect(soDong, "phải có đúng 2 sự kiện BEST (trong tổng 3)").toBe(2);
  await expect(page.locator("#best-bang-webhook")).toContainText("BEST-EV-001");
  await expect(page.locator("#best-bang-webhook")).toContainText("BEST-EV-002");

  // ĐỐI CHỨNG ÂM: sự kiện J&T không được lọt vào bảng BEST; nếu lọt thì phép đếm 2 vô nghĩa.
  await expect(page.locator("#best-bang-webhook")).not.toContainText("JT-EV-KHONG-DUOC-HIEN");
  expect(soDong, "bảng đang hiện cả sự kiện không phải BEST").not.toBe(suKien.length);
});

// ============================================================================================
// 10 — NHẬT KÝ LỖI ĐỒNG BỘ: lọc audit liên quan, không lẫn đăng nhập (MOCK payload)
// ============================================================================================
test("10 — nhật ký: chỉ mục audit liên quan hãng/webhook; dang_nhap KHÔNG hiện", async ({ page }) => {
  const audit = [
    { id: 1, luc: "2026-10-19 10:00:00", hanh_dong: "tai_khoan_hang_rotate", doi_tuong: "carrier_account:77", chi_tiet: "đổi credential BEST" },
    { id: 2, luc: "2026-10-19 10:01:00", hanh_dong: "dang_nhap", doi_tuong: "user:1", chi_tiet: "đăng nhập thành công" },
    { id: 3, luc: "2026-10-19 10:02:00", hanh_dong: "webhook_replay", doi_tuong: "wh_su_kien:2", chi_tiet: "phát lại sự kiện BEST" },
  ];
  await page.route("**/api/v2/audit*", (r) => r.fulfill(json({ audit })));

  await U.dangNhap(page, "shopa-owner");
  await moBest(page, "best-nhat-ky-loi");
  await expect(page.locator("#best-bang-audit")).toBeVisible();
  const soDong = await page.locator("#best-bang-audit tbody tr").count();
  expect(soDong, "phải có 2/3 mục audit liên quan").toBe(2);
  await expect(page.locator("#best-bang-audit")).toContainText("tai_khoan_hang_rotate");
  await expect(page.locator("#best-bang-audit")).toContainText("webhook_replay");

  // ĐỐI CHỨNG ÂM: mục đăng nhập không liên quan KHÔNG được hiện.
  await expect(page.locator("#best-bang-audit")).not.toContainText("dang_nhap");
  expect(soDong).not.toBe(audit.length);
});

// ============================================================================================
// 11 — KHÔNG RÒ RỈ CREDENTIAL QUA BẤT KỲ MÀN NÀO + KHÔNG RA KHỎI LOOPBACK
// ============================================================================================
test("11 — không secret nào lên DOM; mọi request đều ở 127.0.0.1", async ({ page }) => {
  const CANARY_DB = "CANARY-DB-CIPHER-NEVER-RENDER";
  const CANARY_WH = "CANARY-WH-SECRET-NEVER-RENDER";
  const CANARY_DUOI = "9Q7Z";
  const yeuCau = [];
  page.on("request", (r) => yeuCau.push(r.url()));

  await datNenBest(page, {
    tai_khoan: [tkChoXacMinh({
      credentials_ma_hoa: CANARY_DB,
      webhook_secret_ma_hoa: CANARY_WH,
      credentials_duoi: CANARY_DUOI,
      secret: CANARY_WH,
      token: CANARY_DB,
    })],
  });

  await U.dangNhap(page, "shopa-owner");
  for (const ma of ["best-danh-sach-hang", "best-cau-hinh-tai-khoan", "best-kiem-tra-ket-noi",
                    "best-theo-doi-webhook", "best-nhat-ky-loi"]) {
    await moBest(page, ma);
    const html = await page.locator("#man").innerHTML();
    const chu = await page.locator("#man").innerText();
    for (const biMat of [CANARY_DB, CANARY_WH]) {
      expect(html, `${ma}: secret lọt vào innerHTML`).not.toContain(biMat);
      expect(chu, `${ma}: secret lọt vào chữ`).not.toContain(biMat);
    }
    // `credentials_duoi` (4 ký tự cuối) cũng KHÔNG được hiện — yêu cầu của làn B4.
    expect(chu, `${ma}: 4 ký tự cuối của credential bị hiện`).not.toContain(CANARY_DUOI);
  }

  // ĐỐI CHỨNG DƯƠNG: bộ dò vẫn thấy chữ bình thường, nên "không thấy secret" không phải vì trang rỗng.
  await moBest(page, "best-danh-sach-hang");
  await expect(page.locator("#man")).toContainText("BEST Express");
  expect(yeuCau.length, "không có request nào ⇒ phép đo loopback vô nghĩa").toBeGreaterThan(10);

  // ĐỐI CHỨNG ÂM: không request nào ra khỏi 127.0.0.1. Đây là bằng chứng KHÔNG gọi hãng.
  const ngoai = yeuCau.filter((u) => {
    try { return new URL(u).hostname !== "127.0.0.1"; } catch { return true; }
  });
  expect(ngoai, `có request ra ngoài loopback: ${ngoai.join(" · ")}`).toEqual([]);

  // Không màn nào được dựng một form mật khẩu có value.
  const coValue = await page.$$eval('input[type="password"]', (ns) => ns.filter((n) => n.value).length);
  expect(coValue, "có ô password mang value trên màn").toBe(0);
});

// ============================================================================================
// 12 — TRANG RIÊNG pages/best.html: 12 tab, không script nội tuyến (CSP)
// ============================================================================================
test("12 — pages/best.html: 12 tab, mở được, không script nội tuyến", async ({ page }) => {
  const loi = U.thuLoi(page);
  await page.goto("/pages/best.html", { waitUntil: "networkidle" });
  await expect(page.locator("#best-tieu-de")).toHaveText("BEST · Danh sách hãng");
  expect(await page.locator("[data-best-tab]").count(), "trang riêng không đủ 12 tab").toBe(12);
  // ĐỐI CHỨNG ÂM: CSP `script-src 'self'` cấm script nội tuyến — có một cái là trang sẽ chết.
  expect(await page.locator("script:not([src])").count(), "có script nội tuyến trái CSP").toBe(0);
  expect(await page.locator('[data-best-tab="best-khong-ton-tai"]').count()).toBe(0);

  // ĐỐI CHỨNG DƯƠNG: bấm tab thật đổi màn.
  await page.locator('[data-man="best-cau-hinh-tai-khoan"]').click();
  await expect(page.locator("#best-tieu-de")).toHaveText("BEST · Cấu hình tài khoản");
  expect(loi, "lỗi console ở trang riêng").toEqual([]);
});

// ============================================================================================
// 13 — BỐ CỤC 375px: 12 màn không tràn ngang (đo scrollWidth − clientWidth)
// ============================================================================================
test("13 — 12 màn BEST không tràn ngang ở 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await U.dangNhap(page, "shopa-owner");
  const tran = [];
  for (const [ma] of MAN_BEST) {
    await moBest(page, ma);
    const kq = await U.doTranNgang(page);
    if (kq.tai_lieu > 0 || (kq.phan_tu || []).length) tran.push(U.moTaTran(`375px · ${ma}`, kq));
  }
  expect(tran, "TRÀN NGANG ở 375px").toEqual([]);

  // ĐỐI CHỨNG DƯƠNG: phép đo vẫn bắt được tràn khi ta CỐ Ý tạo ra nó — nếu không, "0 tràn"
  // có thể chỉ là phép đo hỏng.
  await page.locator("#man").evaluate((n) => {
    const x = document.createElement("div");
    x.id = "best-thu-tran";
    x.style.width = "900px";
    x.textContent = "thử tràn";
    n.appendChild(x);
  });
  const coTran = await U.doTranNgang(page);
  expect(coTran.tai_lieu > 0 || (coTran.phan_tu || []).length, "phép đo không phát hiện tràn do chính ca thử tạo")
    .toBeTruthy();
});

/* --------------------------------------------------------------------------------------------
   NỀN CHUNG CHO HAI CA BÀN NGHIỆM THU (14, 15)
   --------------------------------------------------------------------------------------------
   Bàn UAT đọc hai đường THẬT của backend (`/api/v2/tai-khoan-hang`, `/api/v2/best/trang-thai`).
   Ở đây mock đúng hai đường ấy để đo BỐ CỐC/CSP và hành vi URL, không phụ thuộc dữ liệu seed —
   nhưng KHÔNG mock đường thao tác nào khác. Payload cố ý chứa tên và URL rất dài để phép đo
   tràn ngang có việc thật mà làm. */
const UAT_TK = {
  id: 77, hang: "best", ten: "BEST sandbox — tên rất dài để đo sức chứa bố cục nghiệm thu",
  moi_truong: "sandbox", kich_hoat: 1, co_credentials: true,
  credentials_doi_luc: "2026-10-19 10:00:00+0700",
  webhook_ma: "WH-BEST-UAT-77",
  webhook_url: "https://best-uat.viporder.vn/api/v2/webhook/nhan/WH-BEST-UAT-77",
  webhook_url_cong_khai: true, webhook_bearer: { co_bearer: true, doc_duoc: true },
};

const UAT_TRANG_THAI = {
  hop_dong: { so_ma: 23, service_id: 12491, token_ttl_days: 30,
              gioi_han: { query: 10, print: 50 }, nguon: "DOCX", endpoints: {}, bang_ma: {} },
  co_phe_duyet_owner: false, co_ma_phe_duyet: false,
  tai_khoan: [UAT_TK], tls: null, public_base_url: "",
};

async function datNenUat(page) {
  await page.unroute("**/api/v2/tai-khoan-hang").catch(() => {});
  await page.unroute("**/api/v2/best/trang-thai*").catch(() => {});
  await page.route("**/api/v2/tai-khoan-hang", (r) => {
    if (r.request().method() === "GET") return r.fulfill(json({ tai_khoan: [UAT_TK] }));
    return r.fulfill(json({ id: 91, webhook_ma: "WH-MOI",
                            webhook_url: "/api/v2/webhook/nhan/WH-MOI",
                            webhook_url_cong_khai: false }, 201));
  });
  await page.route("**/api/v2/best/trang-thai*", (r) => r.fulfill(json(UAT_TRANG_THAI)));
}

// ============================================================================================
// 14 — BÀN NGHIỆM THU: 375 / 768 / 1280 không tràn ngang; CSP không script nội tuyến
// ============================================================================================
test("14 — bàn nghiệm thu: 375/768/1280 không tràn ngang; không mã nội tuyến", async ({ page }) => {
  const loi = U.thuLoi(page);
  await datNenUat(page);
  await U.dangNhap(page, "shopa-owner");

  for (const beRong of [375, 768, 1280]) {
    await page.setViewportSize({ width: beRong, height: 900 });
    await page.goto("/pages/best-uat.html", { waitUntil: "networkidle" });
    await expect(page.locator("#auth"), `mất phiên ở ${beRong}px`).toContainText("Đã đăng nhập");
    // ĐỐI CHỨNG DƯƠNG: nội dung DÀI đã thật sự lên màn, nên phép đo tràn có việc để làm.
    await expect(page.locator("#ds-tai-khoan")).toContainText("BEST sandbox");

    const kq = await U.doTranNgang(page);
    expect(kq.tai_lieu, `tài liệu tràn ngang ở ${beRong}px`).toBe(0);
    expect(kq.phan_tu, `phần tử tràn ở ${beRong}px: ${JSON.stringify(kq.phan_tu)}`).toEqual([]);

    // CSP của máy chủ là `script-src 'self'`: một script/thuộc tính nội tuyến là khối chết.
    expect(await page.locator("script:not([src])").count(),
      `có script nội tuyến ở ${beRong}px`).toBe(0);
    expect(await page.locator(
      "[onclick],[onchange],[oninput],[onsubmit],[onload],[onerror],[onkeydown]").count(),
      `có thuộc tính sự kiện nội tuyến ở ${beRong}px`).toBe(0);
  }
  expect(loi, "lỗi console ở bàn nghiệm thu").toEqual([]);
});

// ============================================================================================
// 15 — URL PDF LÀ HTTP: CHỈ CẢNH BÁO, KHÔNG TỰ MỞ (và không rời loopback)
// ============================================================================================
test("15 — bàn nghiệm thu: URL PDF http chỉ hiện cảnh báo, KHÔNG tự mở trang", async ({ page }) => {
  await datNenUat(page);
  const POPUP = [];
  const RA_NGOAI = [];
  page.on("popup", (p) => POPUP.push(p.url()));
  page.on("request", (r) => {
    try {
      const u = new URL(r.url());
      if (!/^https?:$/.test(u.protocol)) return;
      if (u.hostname !== "127.0.0.1") RA_NGOAI.push(u.href);
    } catch { /* about:blank, blob:… */ }
  });
  await page.route("**/api/v2/best/in", (r) => r.fulfill(json({
    ok: true, url: "http://sea-edi-hxtest.800best.com/Print/Waybill?code=UAT123",
    ma: "UAT123",
  })));
  await page.route("**/api/v2/best/in-pdf", (r) => r.fulfill(json({
    ok: false, blocked: true, loi: "hãng từ chối in PDF trong lượt nghiệm thu này",
  }, 403)));

  await U.dangNhap(page, "shopa-owner");
  await page.goto("/pages/best-uat.html", { waitUntil: "networkidle" });
  await expect(page.locator("#auth")).toContainText("Đã đăng nhập");
  await page.locator("#phe-duyet-that").check();
  await page.locator("#tc-codes").fill("UAT123");
  const soTrangTruoc = page.context().pages().length;

  await page.locator("#btn-in").click();
  await expect(page.locator("#kq-tra-cuu")).toContainText("CẢNH BÁO");
  await expect(page.locator("#kq-tra-cuu")).toContainText("http://sea-edi-hxtest.800best.com");

  // ĐỐI CHỨNG ÂM: không popup, không tab mới, không request ra ngoài loopback.
  expect(POPUP, "đã tự mở URL HTTP của hãng").toEqual([]);
  expect(page.context().pages().length, "đã mở tab mới khi chỉ được hiện URL")
    .toBe(soTrangTruoc);
  expect(await page.locator('a[href^="http://"]').count(),
    "DOM có liên kết http:// để người dùng bấm nhầm").toBe(0);
  expect(RA_NGOAI, `có request ra ngoài 127.0.0.1: ${RA_NGOAI.join(" · ")}`).toEqual([]);

  // Nút tải PDF đi qua BACKEND, và lỗi backend hiện bằng tiếng Việt — không mở URL http.
  await page.locator("#btn-tai-pdf").click();
  await expect(page.locator("#kq-tra-cuu")).toContainText("hãng từ chối in PDF");
  expect(POPUP).toEqual([]);
});

// ============================================================================================
// 16 — MỌI NÚT CỦA BÀN NGHIỆM THU GỌI ĐÚNG API THẬT; LỖI HIỆN TIẾNG VIỆT; KHÔNG LỘ SECRET
// ============================================================================================
// Ca này không gọi hãng: route chặn MỌI đường `/api/v2/best/**` và trả lỗi có kiểm soát, rồi
// đòi đúng một lời gọi cho mỗi nút. Mục đích là bắt NÚT CHẾT / NÚT GỌI SAI ĐƯỜNG — thứ mà
// "trang mở được" không phát hiện được. Ca KHÔNG chứng minh hãng chấp nhận dữ liệu.
test("16 — bàn nghiệm thu: mọi nút gọi đúng API, lỗi tiếng Việt, không lộ secret", async ({ page }) => {
  const daGoi = [];
  const raNgoai = [];
  page.on("request", (r) => {
    try {
      const u = new URL(r.url());
      if (/^https?:$/.test(u.protocol) && u.hostname !== "127.0.0.1") raNgoai.push(u.href);
    } catch { /* blob:, about:blank */ }
  });

  const ghi = (r) => {
    const u = new URL(r.request().url());
    daGoi.push({ duong: u.pathname, truy_van: u.search, method: r.request().method() });
  };

  await page.route("**/api/v2/tai-khoan-hang", (r) => {
    ghi(r);
    if (r.request().method() === "GET") return r.fulfill(json({ tai_khoan: [UAT_TK] }));
    return r.fulfill(json({ id: 91, webhook_ma: "WH-MOI",
                            webhook_url: "/api/v2/webhook/nhan/WH-MOI",
                            webhook_url_cong_khai: false }, 201));
  });
  await page.route("**/api/v2/best/**", (r) => {
    ghi(r);
    const d = new URL(r.request().url()).pathname;
    if (d === "/api/v2/best/trang-thai") return r.fulfill(json(UAT_TRANG_THAI));
    if (d === "/api/v2/best/kiem-ket-noi") {
      return r.fulfill(json({
        ok: false, co_token: false, blocked: false, moi_truong: "sandbox",
        endpoint: "/User/Login", meta: { endpoint: "/User/Login", http_status: 401 },
        loi: "hãng từ chối: sai tài khoản hoặc mật khẩu",
      }, 401));
    }
    if (d === "/api/v2/best/webhook-bearer") {
      return r.fulfill(json({ ok: true, da_luu: true, webhook_url: "/api/v2/webhook/nhan/WH-77" }));
    }
    if (d === "/api/v2/best/in") {
      return r.fulfill(json({ ok: true, url: "http://sea-edi-hxtest.800best.com/Print/UAT123" }));
    }
    if (d === "/api/v2/best/in-pdf") {
      return r.fulfill(json({ ok: false, blocked: true,
                              loi: "hãng từ chối in PDF trong lượt nghiệm thu này" }, 403));
    }
    if (d === "/api/v2/best/lich-su") {
      return r.fulfill(json({ su_kien: [], audit: [] }));
    }
    return r.fulfill(json({ ok: false, blocked: true, loi: "hãng từ chối yêu cầu" }, 403));
  });

  await U.dangNhap(page, "shopa-owner");
  await page.goto("/pages/best-uat.html", { waitUntil: "networkidle" });
  await expect(page.locator("#auth")).toContainText("Đã đăng nhập");
  await page.locator("#phe-duyet-that").check();

  // 1. Lưu tài khoản (POST thật) — secret phải rời khỏi ô ngay và không vào DOM.
  const CANARY_PASS = "BEST-CANARY-PASS-9Q7Z";
  const CANARY_WH = "BEST-CANARY-WEBHOOK-4X8K";
  await page.locator("#tk-ten").fill("BEST UAT ca 16");
  await page.locator("#tk-user").fill("uat-user");
  await page.locator("#tk-pass").fill(CANARY_PASS);
  await page.locator("#btn-luu-tk").click();
  await expect(page.locator("#tk-kq")).toContainText("Đã lưu tài khoản #91");
  expect(await page.locator("#tk-pass").inputValue(), "mật khẩu còn trong ô").toBe("");

  // 2. Tải lại trạng thái + TLS.
  await page.locator("#btn-trang-thai").click();
  await expect.poll(() => daGoi.filter((x) => x.duong === "/api/v2/best/trang-thai"
    && x.truy_van === "?tls=1").length).toBe(1);

  // 3. Kiểm tra kết nối thật (mock 401 của hãng) — KHÔNG được báo thành công.
  await page.locator("#kn-tk").selectOption("77");
  await page.locator("#kn-xac-nhan").selectOption("1");
  await page.locator("#btn-kiem-ket-noi").click();
  await expect(page.locator("#kq-ket-noi")).toContainText("THẤT BẠI/BỊ CHẶN");
  await expect(page.locator("#kq-ket-noi")).toContainText("sai tài khoản hoặc mật khẩu");

  // 4. Lưu Bearer webhook — token rời ô ngay, không hiện lại.
  await page.locator("#wh-tk").selectOption("77");
  await page.locator("#wh-token").fill(CANARY_WH);
  await page.locator("#btn-luu-webhook").click();
  await expect(page.locator("#kq-webhook")).toContainText("Đã lưu Bearer");
  expect(await page.locator("#wh-token").inputValue(), "Bearer còn trong ô").toBe("");

  // 5. Báo cước.
  await page.locator("#cuoc-tk").selectOption("77");
  await page.locator("#btn-bao-gia").click();
  await expect(page.locator("#kq-cuoc")).toContainText("KHÔNG BÁO ĐƯỢC CƯỚC");

  // 6. Tạo đơn sandbox.
  await page.locator("#don-tk").selectOption("77");
  await page.locator("#don-xac-nhan").fill("TOI_DONG_Y_GOI_BEST_TEST");
  await page.locator("#btn-tao-don").click();
  await expect(page.locator("#kq-don")).toContainText("KHÔNG TẠO ĐƯỢC");

  // 7. Tra cứu / lấy URL PDF / tải PDF qua backend.
  await page.locator("#tc-tk").selectOption("77");
  await page.locator("#tc-codes").fill("UAT123");
  await page.locator("#btn-tra-cuu").click();
  await expect(page.locator("#kq-tra-cuu")).toContainText("KHÔNG TRA CỨU ĐƯỢC");

  await page.locator("#btn-in").click();
  await expect(page.locator("#kq-tra-cuu")).toContainText("URL PDF: http://sea-edi-hxtest.800best.com");
  await page.locator("#btn-tai-pdf").click();
  await expect(page.locator("#kq-tra-cuu")).toContainText("hãng từ chối in PDF");

  // 8. Order/Update, UpdateAddress, Cancel.
  await page.locator("#ud-tk").selectOption("77");
  await page.locator("#ud-ma").fill("UAT123");
  await page.locator("#ud-xac-nhan").fill("TOI_DONG_Y_GOI_BEST_TEST");
  await page.locator("#btn-cap-nhat").click();
  await expect(page.locator("#kq-cap-nhat")).toContainText("KHÔNG CẬP NHẬT");

  await page.locator("#btn-sua-dia-chi").click();
  await expect(page.locator("#kq-cap-nhat")).toContainText("KHÔNG SỬA ĐƯỢC");

  await page.locator("#btn-huy").click();
  await expect(page.locator("#kq-cap-nhat")).toContainText("KHÔNG HỦY ĐƯỢC");

  // 9. Lịch sử / nhật ký.
  await page.locator("#btn-lich-su").click();
  await expect(page.locator("#kq-lich-su")).toContainText("Sự kiện gần nhất: 0");

  // MỌI nút phải để lại ĐÚNG một lời gọi tới đường của nó (không nút chết, không gọi sai).
  const duong = new Set(daGoi.map((x) => x.duong));
  for (const p of ["/api/v2/tai-khoan-hang", "/api/v2/best/trang-thai",
    "/api/v2/best/kiem-ket-noi", "/api/v2/best/webhook-bearer", "/api/v2/best/bao-gia",
    "/api/v2/best/tao-don", "/api/v2/best/tra-cuu", "/api/v2/best/in",
    "/api/v2/best/in-pdf", "/api/v2/best/cap-nhat", "/api/v2/best/sua-dia-chi",
    "/api/v2/best/huy", "/api/v2/best/lich-su"]) {
    expect(duong.has(p), `không có lời gọi nào tới ${p} ⇒ nút chết hoặc gọi sai đường`)
      .toBe(true);
  }
  const post = daGoi.filter((x) => x.method === "POST").map((x) => x.duong);
  for (const p of ["/api/v2/tai-khoan-hang", "/api/v2/best/kiem-ket-noi",
    "/api/v2/best/webhook-bearer", "/api/v2/best/bao-gia", "/api/v2/best/tao-don",
    "/api/v2/best/tra-cuu", "/api/v2/best/in", "/api/v2/best/in-pdf",
    "/api/v2/best/cap-nhat", "/api/v2/best/sua-dia-chi", "/api/v2/best/huy"]) {
    expect(post, `thiếu POST ${p}`).toContain(p);
  }

  // ĐỐI CHỨNG ÂM: secret không lọt DOM; không lỗi tiếng Anh của trình duyệt; không ra ngoài.
  const chu = await page.locator("body").innerText();
  for (const biMat of [CANARY_PASS, CANARY_WH]) {
    expect(chu, `secret lọt vào chữ trên màn: ${biMat}`).not.toContain(biMat);
  }
  expect(chu).not.toContain("Failed to fetch");
  expect(chu).not.toContain("undefined");
  expect(raNgoai, `có request ra ngoài loopback: ${raNgoai.join(" · ")}`).toEqual([]);
});

// ============================================================================================
// 17 — BÁO CƯỚC: PAYLOAD ĐỦ Source.Address/Dest.Address; THIẾU ĐỊA CHỈ THÌ CHẶN TẠI UI
// ============================================================================================
// Lỗi AG-08 đo được: UI mục 5 không gửi địa chỉ đường, backend `best_hop_dong._dia_chi` từ chối
// "thiếu Source.Address" và máy chủ trả 502. Ca này KHÔNG gọi hãng: chặn `/api/v2/best/bao-gia`
// và mô phỏng ĐÚNG luật address bắt buộc của backend để thấy payload nào thật sự rời trình duyệt.
test("17 — báo cước: payload đủ Source.Address/Dest.Address; thiếu địa chỉ thì chặn tại UI", async ({ page }) => {
  const daGui = [];
  await datNenUat(page);
  await page.route("**/api/v2/best/bao-gia", (r) => {
    let than = {};
    try { than = JSON.parse(r.request().postData() || "{}"); } catch { /* body lạ */ }
    daGui.push(than);
    const don = than.don || {};
    // Mô phỏng `_dia_chi`: address bat_buoc=True cho CẢ EstimateFee (dù EstimateFee không dùng
    // address trong payload, hàm vẫn từ chối đơn thiếu). Đây chính là nguồn lỗi 502 của AG-08.
    const thieu = [];
    if (!String(don.nguoi_gui_dia_chi || "").trim()) thieu.push("Source.Address");
    if (!String(don.nguoi_nhan_dia_chi || "").trim()) thieu.push("Dest.Address");
    if (thieu.length) {
      return r.fulfill(json({ ok: false, blocked: false, loi: `thiếu ${thieu.join(", ")}` }, 502));
    }
    return r.fulfill(json({
      ok: true,
      data: { TotalFee: 22000, FreightFee: 20000, CODFee: 0, InsuranceFee: 0,
              FreightFeeVAT: 2000, TotalFeeVAT: 22000, TotalFeeVATWithDiscount: 22000,
              ServiceType: "ECO", Cod: 0, ProductPrice: 0 },
      meta: { endpoint: "/EstimateFee", http_status: 200 },
    }));
  });

  await U.dangNhap(page, "shopa-owner");
  await page.goto("/pages/best-uat.html", { waitUntil: "networkidle" });
  await expect(page.locator("#auth")).toContainText("Đã đăng nhập");
  await page.locator("#phe-duyet-that").check();
  await page.locator("#cuoc-tk").selectOption("77");

  // ĐỐI CHỨNG DƯƠNG: hai ô địa chỉ đường có NHÃN RÕ và có giá trị mặc định dùng được ngay.
  await expect(page.locator('label[for="cuoc-sa"]')).toContainText("Địa chỉ đường gửi");
  await expect(page.locator('label[for="cuoc-da"]')).toContainText("Địa chỉ đường nhận");
  for (const id of ["cuoc-sa", "cuoc-da"]) {
    expect(await page.locator("#" + id).inputValue(), `${id} không có giá trị mặc định`)
      .not.toBe("");
  }

  await page.locator("#cuoc-sa").fill("12 Đường ABCD");
  await page.locator("#cuoc-da").fill("34 Đường XYZ");
  await page.locator("#btn-bao-gia").click();
  await expect.poll(() => daGui.length, { timeout: 5000 }).toBe(1);

  const don = daGui[0].don || {};
  expect(don.nguoi_gui_dia_chi, "payload thiếu nguoi_gui_dia_chi ⇒ backend 502 Source.Address")
    .toBe("12 Đường ABCD");
  expect(don.nguoi_nhan_dia_chi, "payload thiếu nguoi_nhan_dia_chi ⇒ backend 502 Dest.Address")
    .toBe("34 Đường XYZ");
  // Chờ UI XỬ LÝ XONG phản hồi (không chỉ chờ request rời đi) rồi mới đọc chữ.
  await expect(page.locator("#kq-cuoc")).toContainText("Tổng phí");
  const kqCuoc = gon(await page.locator("#kq-cuoc").innerText());
  expect(kqCuoc, `UI còn hiện lỗi thiếu địa chỉ: ${kqCuoc}`).not.toContain("Source.Address");

  // ĐỐI CHỨNG ÂM: xoá địa chỉ GỬI ⇒ UI chặn TRƯỚC khi gọi; không payload thiếu địa chỉ nào
  // rời trình duyệt (đúng lỗi 502 mà AG-08 đã đo).
  await page.locator("#cuoc-sa").fill("");
  await page.locator("#btn-bao-gia").click();
  await expect(page.locator("#kq-cuoc")).toContainText("địa chỉ");
  expect(daGui.length, "vẫn gửi báo cước khi thiếu địa chỉ gửi — backend sẽ 502").toBe(1);

  // ĐỐI CHỨNG ÂM phụ: địa chỉ NHẬN trống cũng bị chặn — không chỉ kiểm một ô.
  await page.locator("#cuoc-sa").fill("12 Đường ABCD");
  await page.locator("#cuoc-da").fill("");
  await page.locator("#btn-bao-gia").click();
  await expect(page.locator("#kq-cuoc")).toContainText("địa chỉ");
  expect(daGui.length, "vẫn gửi báo cước khi thiếu địa chỉ nhận").toBe(1);
});
