// Tiện ích dùng chung cho tầng 3. Không có ca thử nào ở đây — chỉ phép đo và thao tác.
//
// LUẬT CỦA FILE NÀY:
// - Mọi phép đo trả về SỐ hoặc DANH SÁCH đo được. Không hàm nào trả "trông ổn".
// - Ảnh chụp màn hình KHÔNG bao giờ là điều kiện đạt (Playwright tự chụp khi ca hỏng, để
//   người xem). Điều kiện đạt luôn là một khẳng định trên số đo.
"use strict";

const MK = "MatKhauThu-GiaoDien-123";

// Mười màn của vai trò doanh nghiệp + bốn màn nền tảng, đọc từ chính `admin/admin.js`
// lúc chạy (xem `docMenu`) chứ KHÔNG chép lại thành bảng ở đây: hai bản nội dung là hai
// bản sẽ lệch nhau, và bản trong bộ thử là bản không ai nhớ cập nhật.

const BE_RONG = [
  { ten: "điện thoại 375", width: 375, height: 760 },
  { ten: "máy tính bảng 768", width: 768, height: 900 },
  { ten: "màn rộng 1280", width: 1280, height: 900 },
];

/** Gắn bộ thu lỗi. PHẢI gọi trước khi điều hướng. Trả về MẢNG lỗi CỦA ỨNG DỤNG.
 *
 *  PHÂN BIỆT CÓ CHỦ Ý — đây là chỗ dễ đo sai nhất:
 *  - Trình duyệt tự ghi `console.error: Failed to load resource …` cho MỌI phản hồi không
 *    phải 2xx, kể cả phản hồi mà ứng dụng CỐ Ý gây ra và xử lý đúng (401 ở `/auth/toi` khi
 *    chưa đăng nhập là đường chạy bình thường). Gom nó vào "lỗi giao diện" thì câu "0 lỗi
 *    console" vừa sai vừa vô dụng.
 *  - Nên mảng trả về chỉ chứa lỗi do CHÍNH TRANG sinh: `pageerror` (ngoại lệ chưa bắt) và
 *    `console.error` do mã của trang gọi.
 *  - Lỗi tải TỆP TĨNH thì không bỏ qua được — đo riêng bằng `thuTepTinhHong`.
 */
function thuLoi(page) {
  const loi = [];
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const t = m.text();
    if (/^Failed to load resource/.test(t)) return;   // tiếng của trình duyệt, không phải của trang
    loi.push("console.error: " + t);
  });
  page.on("pageerror", (e) => loi.push("pageerror: " + (e && e.message)));
  return loi;
}

/** Đo riêng: tệp tĩnh của giao diện có tải được hết không (js/css/html/ảnh).
 *  404 một tệp tĩnh là lỗi giao diện thật, khác hẳn 401 của một lời gọi API được xử lý. */
function thuTepTinhHong(page) {
  const hong = [];
  page.on("response", (r) => {
    const d = new URL(r.url()).pathname;
    if (d.startsWith("/api/")) return;
    if (r.status() >= 400) hong.push(`${r.status()} ${d}`);
  });
  page.on("requestfailed", (r) => {
    const d = new URL(r.url()).pathname;
    if (d.startsWith("/api/")) return;
    hong.push(`requestfailed ${d} — ${(r.failure() || {}).errorText}`);
  });
  return hong;
}

/** Đăng nhập qua ĐÚNG form của giao diện, không tiêm cookie. */
async function dangNhap(page, ten, mk = MK) {
  // Xoá cookie trước: cùng một `page` đăng nhập hai lần trong một ca thì lần thứ hai sẽ
  // vào thẳng SPA bằng phiên cũ và không có form nào để điền — ca hỏng vì HẠ TẦNG bộ thử,
  // không phải vì sản phẩm. Hỏng giả là kiểu sai tệ nhất với một cổng chặn hồi quy.
  await page.context().clearCookies();
  await page.goto("/admin/index.html", { waitUntil: "domcontentloaded" });
  await page.locator("#dn-ten").fill(ten);
  await page.locator("#dn-mk").fill(mk);
  await page.locator("#dn-nut").click();
  // Khung sau đăng nhập dựng xong khi menu có ít nhất một mục.
  await page.locator(".menu-quan-tri a").first().waitFor({ state: "visible" });
}

/** Danh sách màn đang có trên MENU THẬT (không phải bảng chép tay). */
async function docMenu(page) {
  return page.$$eval(".menu-quan-tri a", (ns) =>
    ns.map((n) => ({ ma: n.dataset.man, ten: n.textContent.trim() })));
}

/** Mở một màn và chờ NỘI DUNG màn thật sự đổi. Trả về tiêu đề đo được.
 *
 *  CHỖ NÀY TỪNG SAI VÀ SAI IM LẶNG — ghi lại để không ai rút ngắn lại:
 *  bản đầu chờ "menu có lớp `hien-tai`" và "#tieu-de khác rỗng". Cả hai điều kiện ấy đã
 *  đúng NGAY LÚC BẤM, vì `moMan()` của `admin.js` gắn lớp và đặt `MAN_HIEN_TAI` TRƯỚC khi
 *  gọi hàm dựng màn. Kết quả: mọi phép đo đọc nội dung của màn TRƯỚC ĐÓ, không báo lỗi gì,
 *  và tự nó cho ra kết quả "đạt". Lượt chạy 15/10 lộ ra vì nhãn CHỜ BACKEND của màn Đơn
 *  hàng bị ghi là của màn Khách hàng — lệch đúng một bậc trong menu.
 *  Nay chờ bằng dấu vết KHÔNG THỂ có sẵn: nội dung `#man` phải khác nội dung trước khi bấm.
 */
async function moMan(page, ma) {
  const a = page.locator(`.menu-quan-tri a[data-man="${ma}"]`);
  // Ở bề rộng điện thoại, thanh bên nằm NGOÀI khung nhìn cho tới khi bấm ☰. Đây là hành vi
  // đúng của sản phẩm, nên bộ thử phải bấm ☰ như người dùng bấm, chứ không được ép click.
  if (await page.locator("#nut-menu").isVisible()) {
    const dang_mo = await page.locator("#sidebar").evaluate((n) => n.classList.contains("mo"));
    if (!dang_mo) {
      await page.locator("#nut-menu").click();
      await page.waitForFunction(() => document.getElementById("sidebar").classList.contains("mo"));
    }
  }
  // Đặt một DẤU HIỆU không thể có sẵn vào `#man`, rồi chờ nó bị thay. So nội dung cũ/mới
  // thì KHÔNG đủ: mở lại chính màn đang xem (hoặc một màn dựng ra đúng chừng ấy chữ) cho
  // nội dung y hệt, và phép chờ sẽ treo — đo sai vì chính phép đo, không vì sản phẩm.
  const DAU = "<!--G12-CHO-MAN-" + ma + "-->";
  await page.locator("#man").evaluate((n, d) => { n.innerHTML = d; }, DAU);
  await a.click();
  await page.waitForFunction(
    ([m, dau]) => {
      const el = document.querySelector(`.menu-quan-tri a[data-man="${m}"]`);
      const o = document.getElementById("man");
      const t = document.getElementById("tieu-de");
      if (!el || !o || !t) return false;
      if (!el.classList.contains("hien-tai")) return false;
      return o.innerHTML !== dau && t.textContent.trim().length > 0;
    }, [ma, DAU], { timeout: 10000 });
  // Màn nào cũng nạp dữ liệu bằng fetch; chờ mạng lặng rồi mới đo bố cục.
  await page.waitForLoadState("networkidle");
  return (await page.locator("#tieu-de").textContent()).trim();
}

/** Đo tràn ngang. Trả { tai_lieu, phan_tu } — hai con số, không phải một lời nhận xét.
 *
 *  - `tai_lieu`: `scrollWidth - clientWidth` của <html>. > 0 là trang cuộn ngang được,
 *    tức bố cục đã tràn ra ngoài khung nhìn.
 *  - `phan_tu`: danh sách phần tử tự nó tràn, ĐÃ LOẠI TRỪ mọi thứ nằm trong `.cuon-ngang`
 *    — bảng rộng PHẢI cuộn ngang trong vùng của nó, đó là thiết kế, không phải lỗi.
 */
async function doTranNgang(page) {
  return page.evaluate(() => {
    const d = document.documentElement;
    const ra = [];
    document.querySelectorAll("body *").forEach((n) => {
      if (n.closest(".cuon-ngang")) return;              // loại trừ CÓ CHỦ Ý
      if (n.scrollWidth - n.clientWidth > 1) {
        ra.push({
          the: n.tagName.toLowerCase(),
          lop: (n.className || "").toString().slice(0, 60),
          id: n.id || "",
          lech: n.scrollWidth - n.clientWidth,
        });
      }
    });
    return { tai_lieu: d.scrollWidth - d.clientWidth, phan_tu: ra };
  });
}

/** Gói một phép đo tràn ngang thành dòng chữ có đủ phạm vi để đọc lại sau này. */
function moTaTran(nhan, kq) {
  return `${nhan}: tài liệu lệch ${kq.tai_lieu}px; ${kq.phan_tu.length} phần tử tràn ngoài .cuon-ngang` +
    (kq.phan_tu.length ? " → " + kq.phan_tu.map((x) => `${x.the}${x.id ? "#" + x.id : ""}.${x.lop}(${x.lech}px)`).join(", ") : "");
}

module.exports = { MK, BE_RONG, thuLoi, thuTepTinhHong, dangNhap, docMenu, moMan, doTranNgang, moTaTran };
