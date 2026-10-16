// TẦNG 3 — CA CANH BẢNG KHAI ĐƯỜNG CỦA `admin/billing.js` (G20 · AG-02).
//
// VÌ SAO CÓ TỆP NÀY — đọc trước khi sửa, vì đây là cả lý do tệp tồn tại:
// `admin/billing.js` khai hai bảng `API_DANG_DUNG` / `API_CHO_BACKEND`. NĂM dòng đầu của bảng
// chờ trỏ `/api/v2/billing/{goi,dang-ky,muc-dung,canh-bao,lich-su}` — ĐO RA CẢ NĂM ĐỀU 404.
// Chức năng ấy nằm ở `/api/v2/goi`, `/api/v2/dang-ky`, `/api/v2/usage…`.
//
// Bảng sai ấy sống sót qua nhiều đợt vì **KHÔNG AI CANH NÓ**: `finance.js` có hẳn một ca
// (`app/thu/thu_tai_chinh.py::test_j4`) canh bảng tương đương, còn `billing.js` thì không
// (`grep -rn "billing.js" app/thu/*.py` → 0 dòng). AG-05 (G19) đo ra nhưng CỐ Ý không sửa —
// và lý do rất đúng: *sửa một bảng không ai canh là tạo ra một chỗ hỏng im lặng MỚI*. G20
// sửa bảng VÀ thêm ca này trong cùng một lượt, đúng luật dự án.
//
// VÌ SAO NẰM Ở `thu_giao_dien/` CHỨ KHÔNG Ở `app/thu/`: bản gương của ca này là
// `test_j4` trong `app/thu/thu_tai_chinh.py`, và đó mới là nhà ĐÚNG của nó. `app/thu/**`
// KHÔNG nằm trong danh sách tệp làn này được cấp ghi, nên ca được đặt tạm ở đây — cùng thư
// mục với các ca tầng 3 khác, chạy cùng lượt, cùng mã thoát. Ghi ra để AG-00 chuyển về
// `app/thu/` nếu muốn nó chạy trong bộ Python.
//
// HAI CHIỀU, KHÔNG MỘT: một bảng khai nói dối theo hai cách, và cách thứ hai TỆ HƠN.
//   (1) Khai CHỜ BACKEND cho một đường ĐÃ CẮM  ⇒ giao diện tự nhận là chưa làm được.
//   (2) Khai ĐANG DÙNG cho một đường KHÔNG CÓ ⇒ giao diện gọi thật rồi báo lỗi lạ cho người
//       dùng. Đây là chiều tệ hơn, và là chiều dễ bị bỏ sót khi chỉ canh "đừng khai chờ nữa".
//
// VÀ PHẢI ĐỎ ĐƯỢC: ca 02 (TỰ KIỂM) đưa vào bộ đo hai bảng CỐ Ý SAI và đòi bộ đo phải bắt.
// Một ca canh không đỏ được là một ca canh đang ru ngủ người đọc — xem §12.1 luật 5.
"use strict";
const { test, expect } = require("@playwright/test");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const U = require("./tien_ich");

const GOC = join(__dirname, "..");
const BILLING = join(GOC, "admin", "billing.js");
const SERVER = join(GOC, "app", "server.py");

test.describe.configure({ mode: "serial" });

const B = require(BILLING);

/* ============================================================================================
   BỘ ĐO TĨNH — đọc `app/server.py` THẬT rồi rút ra tập đường máy chủ phục vụ.
   --------------------------------------------------------------------------------------------
   KHÔNG dùng `assertNotIn(chuỗi con)`: bản `test_j4` làm thế và nó có một lỗ đã biết —
   `POST /api/v2/platform/goi/phien-ban` CHỨA chuỗi con `/api/v2/platform/goi`, mà
   `/api/v2/platform/goi` thì CÓ thật. Đếm theo chuỗi con là kết luận "đã cắm" cho một đường
   404. Ở đây rút ra đúng ba dạng khai mà `server.py` đang dùng rồi so KHỚP TOÀN PHẦN.
   ============================================================================================ */

/** Rút tập đường `server.py` phục vụ: [{khop: RegExp, method: Set|"ANY", dong: number}]. */
function docDuongServer(nguon) {
  const ra = [];
  const dong = nguon.split("\n");
  const themMethod = (tap, s) => {
    const m1 = s.match(/method\s*==\s*"([A-Z]+)"/);
    if (m1) tap.add(m1[1]);
    const m2 = s.match(/method\s+in\s*\(([^)]*)\)/);
    if (m2) m2[1].split(",").forEach((x) => {
      const t = x.trim().replace(/["']/g, "");
      if (t) tap.add(t);
    });
  };
  dong.forEach((d, i) => {
    // Dạng 1 và 2: `if duong == "…"` (kèm hoặc không kèm điều kiện method).
    const thang = d.match(/^\s*if duong == "([^"]+)"/);
    if (thang) {
      const method = new Set();
      themMethod(method, d);
      ra.push({ khop: new RegExp("^" + thang[1].replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + "$"),
                method: method.size ? method : "ANY", dong: i + 1 });
      return;
    }
    // Dạng 3: `m = re.fullmatch(r"…", duong)` — method nằm trong khối bên dưới.
    const fm = d.match(/^\s*m = re\.fullmatch\(r"([^"]+)", duong\)/);
    if (fm) {
      const method = new Set();
      const thut = d.match(/^\s*/)[0].length;
      for (let j = i + 1; j < Math.min(i + 30, dong.length); j++) {
        const s = dong[j];
        if (s.trim() && s.match(/^\s*/)[0].length <= thut) break;   // ra khỏi khối
        themMethod(method, s);
      }
      ra.push({ khop: new RegExp("^" + fm[1] + "$"), method: method.size ? method : "ANY",
                dong: i + 1 });
    }
  });
  return ra;
}

/** Đường khai `{id}` / `<id>` → mẫu khớp. Giữ nguyên phần còn lại. */
function mauKhai(duong) {
  return new RegExp("^" + duong
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/\\\{id\\\}|<id>/g, "[^/]+") + "$");
}

/** BỘ ĐO. Trả {thua, thieu, tong} — hai danh sách ĐO ĐƯỢC, không phải một lời nhận xét.
 *   - `thua`: khai CHỜ BACKEND mà `server.py` ĐÃ phục vụ  (nhãn nói dối chiều 1)
 *   - `thieu`: khai ĐANG DÙNG mà `server.py` KHÔNG có      (nhãn nói dối chiều 2 — tệ hơn)
 */
function soiBangDuong(dsCho, dsDung, duongServer) {
  const co = (method, duong) => duongServer.some(
    (x) => x.khop.test(duong) && (x.method === "ANY" || x.method.has(method)));
  const thua = dsCho.filter((r) => co(r[0], r[1]))
    .map((r) => `${r[0]} ${r[1]} — ĐÃ cắm trong server.py mà vẫn khai CHỜ BACKEND`);
  const thieu = dsDung.filter((r) => !co(r[0], r[1]))
    .map((r) => `${r[0]} ${r[1]} — khai ĐANG DÙNG mà server.py KHÔNG có`);
  return { thua, thieu, tong: dsCho.length + dsDung.length };
}

// ============================================================================================
// 1. HAI CHIỀU, ĐỌC TỆP THẬT
// ============================================================================================
test("01 — bảng khai của billing.js KHỚP `app/server.py` ở CẢ HAI chiều", async () => {
  const server = readFileSync(SERVER, "utf8");
  const duongServer = docDuongServer(server);
  console.log(`[đo] server.py khai ${duongServer.length} đường (đọc thẳng tệp, không chép tay)`);
  expect(duongServer.length, "không rút được đường nào từ server.py ⇒ bộ đo hỏng, "
    + "và mọi kết luận 'đạt' sau đây là rỗng").toBeGreaterThan(50);

  const kq = soiBangDuong(B.API_CHO_BACKEND, B.API_DANG_DUNG, duongServer);
  console.log(`[đo] billing.js khai ${B.API_DANG_DUNG.length} đang dùng + `
    + `${B.API_CHO_BACKEND.length} chờ backend = ${kq.tong}`);
  for (const r of B.API_DANG_DUNG) console.log(`      ĐANG DÙNG  ${r[0]} ${r[1]}`);
  for (const r of B.API_CHO_BACKEND) console.log(`      CHỜ        ${r[0]} ${r[1]}`);

  // SÀN ĐẾM: hai bảng rỗng thì hai khẳng định dưới đây đúng một cách vô nghĩa. Sàn đếm TỔNG
  // hai bảng (không đếm riêng bảng chờ) để không chặn chiều tiến bộ — đúng cách `test_j4` đã
  // phải sửa một lần rồi.
  expect(kq.tong, "hai bảng chỉ còn " + kq.tong + " dòng ⇒ ca này canh gần như không gì")
    .toBeGreaterThanOrEqual(10);

  expect(kq.thua, "billing.js khai CHỜ BACKEND cho đường ĐÃ CẮM").toEqual([]);
  expect(kq.thieu, "billing.js khai ĐANG DÙNG cho đường KHÔNG có").toEqual([]);
});

// ============================================================================================
// 2. TỰ KIỂM — BỘ ĐO PHẢI ĐỎ ĐƯỢC, Ở CẢ HAI CHIỀU
// ============================================================================================
// Không có ca này thì ca 01 chỉ là một khẳng định `[] === []` mà không ai biết nó có hiệu lực
// gì. Ở đây đưa vào CHÍNH hai bảng sai của bản trước G20 và đòi bộ đo bắt được:
//   (a) `GET /api/v2/billing/du-thao` nằm trong bảng CHỜ — đo được HTTP 200 ⇒ phải vào `thua`.
//   (b) `GET /api/v2/billing/goi` (đường SAI của bản cũ) khai ĐANG DÙNG ⇒ phải vào `thieu`.
test("02 — TỰ KIỂM: đưa bảng SAI của bản trước G20 vào thì bộ đo PHẢI ĐỎ", async () => {
  const duongServer = docDuongServer(readFileSync(SERVER, "utf8"));

  // (a) chiều 1 — chờ-mà-đã-cắm. Đây là dòng AG-05 CHƯA nêu; ca 01 bắt được nó ở lượt này.
  const choSai = [["GET", "/api/v2/billing/du-thao"]];
  const a = soiBangDuong(choSai, [], duongServer);
  console.log(`[đo] tự kiểm chiều 1: thua=${a.thua.length} thieu=${a.thieu.length}`);
  expect(a.thua.length, "bộ đo KHÔNG bắt được đường đã cắm nằm trong bảng CHỜ ⇒ ca 01 vô hiệu")
    .toBe(1);

  // (b) chiều 2 — dùng-mà-không-có. Đây đúng là năm dòng sai đường của bản trước G20.
  const dungSai = [["GET", "/api/v2/billing/goi"], ["GET", "/api/v2/billing/dang-ky"],
                   ["GET", "/api/v2/billing/muc-dung"], ["GET", "/api/v2/billing/canh-bao"],
                   ["GET", "/api/v2/billing/lich-su"]];
  const b = soiBangDuong([], dungSai, duongServer);
  console.log(`[đo] tự kiểm chiều 2: thua=${b.thua.length} thieu=${b.thieu.length}`);
  expect(b.thieu.length, "bộ đo KHÔNG bắt được đường không có mà khai ĐANG DÙNG ⇒ ca 01 vô hiệu")
    .toBe(5);

  // (c) ĐỐI CHỨNG DƯƠNG: đúng năm đường THẬT thay vào chỗ năm đường sai ⇒ bộ đo phải XANH.
  //     Thiếu vế này thì một bộ đo "luôn đỏ" cũng qua được (a) và (b).
  const dungThat = [["GET", "/api/v2/goi"], ["GET", "/api/v2/dang-ky"], ["GET", "/api/v2/usage"],
                    ["GET", "/api/v2/usage/bao-cao"], ["GET", "/api/v2/usage/su-kien"]];
  const c = soiBangDuong([], dungThat, duongServer);
  expect(c.thieu, "năm đường THẬT bị bộ đo coi là không có ⇒ bộ đo hỏng, không phải bảng hỏng")
    .toEqual([]);

  // (d) MỘT LỖ ĐÃ BIẾT của bản `test_j4`: so bằng CHUỖI CON thì `/api/v2/platform/goi` (CÓ
  //     thật) làm `/api/v2/platform/goi/phien-ban` (404) bị coi là "đã cắm". Ca này đóng lỗ
  //     ấy: khớp TOÀN PHẦN, nên đường 404 vẫn nằm đúng ở bảng chờ.
  const ho = [["POST", "/api/v2/platform/goi/phien-ban"]];
  const d = soiBangDuong(ho, [], duongServer);
  console.log(`[đo] tự kiểm lỗ chuỗi con: thua=${d.thua.length} (kỳ vọng 0)`);
  expect(d.thua, "khớp theo chuỗi con: `/api/v2/platform/goi` kéo theo cả `/phien-ban` ⇒ "
    + "bộ đo báo 'đã cắm' cho một đường 404").toEqual([]);
});

// ============================================================================================
// 3. ĐO BẰNG HTTP THẬT — lời khai phải khớp MÁY CHỦ ĐANG CHẠY, không chỉ khớp tệp mã nguồn
// ============================================================================================
// Ca 01 đối chiếu với MÃ NGUỒN. Mã nguồn và máy chủ đang chạy có thể lệch (route bị chặn
// quyền, bị cổng chặn, hoặc tệp trên đĩa khác bản đang phục vụ). Nên ca này bắn THẬT.
//
// GHI RÕ RỦI RO CỐ Ý: ca này bắn đúng method khai trong bảng, kể cả POST. Trên nền cô lập của
// `chay.sh` thì vô hại (nền xoá khi xong), và các đường POST ở đây đều 404 nên không ghi gì.
// ĐỪNG chạy bộ thử này vào CSDL đang dùng — `playwright.config.js` đã từ chối chạy khi thiếu
// `VIP_GD_GOC` đúng vì thế.
async function ban(page, method, duong) {
  return page.evaluate(async ([m, d]) => {
    const h = { "X-Requested-With": "VIPHub" };
    const opt = { method: m, headers: h };
    if (m !== "GET" && m !== "HEAD") { h["Content-Type"] = "application/json"; opt.body = "{}"; }
    const r = await fetch(d, opt);
    return r.status;
  }, [method, duong]);
}

test("03 — đo THẬT: mỗi đường ĐANG DÙNG trả khác 404, mỗi đường CHỜ trả ĐÚNG 404", async ({ page }) => {
  // ĐO BẰNG ĐÚNG VAI, nếu không thì phép đo nói dối theo CẢ HAI chiều — chỗ này đã sai một
  // lượt rồi và lượt chạy đầu tiên bắt được, ghi lại để không ai rút gọn:
  //   · Đường TENANT (`/api/v2/billing/**`, `/api/v2/usage/**`, …) đo bằng `platform-owner`
  //     thì trả **403** — người nền tảng không phải thành viên doanh nghiệp nào. 403 ấy bị
  //     đọc thành "đã chạy" và làm ca ĐỎ GIẢ trên chính hai đường đang CHỜ đúng.
  //   · Đường NỀN TẢNG (`/api/v2/platform/**`) đo bằng `shopa-owner` cũng trả **403**, vì có
  //     cổng riêng ở `server.py:566` chặn TRƯỚC khi tới bảng route — 403 ấy KHÔNG nói gì về
  //     việc đường có được cắm hay không.
  const laNenTang = (d) => d.startsWith("/api/v2/platform/");
  const ket = [];

  await U.dangNhap(page, "shopa-owner");
  for (const [method, duong] of B.API_DANG_DUNG.map((r) => [r[0], r[1]])) {
    const ma = await ban(page, method, duong);
    console.log(`[đo] ĐANG DÙNG ${method} ${duong} → HTTP ${ma}`);
    ket.push({ method, duong, ma, chieu: "dung" });
  }
  for (const [method, duong] of B.API_CHO_BACKEND.map((r) => [r[0], r[1]])) {
    if (laNenTang(duong)) continue;
    const ma = await ban(page, method, duong.replace("{id}", "1"));
    console.log(`[đo] CHỜ       ${method} ${duong} → HTTP ${ma}  (đo bằng shopa-owner)`);
    ket.push({ method, duong, ma, chieu: "cho" });
  }

  await U.dangNhap(page, "platform-owner");
  for (const [method, duong] of B.API_CHO_BACKEND.map((r) => [r[0], r[1]])) {
    if (!laNenTang(duong)) continue;
    const ma = await ban(page, method, duong.replace("{id}", "1"));
    console.log(`[đo] CHỜ       ${method} ${duong} → HTTP ${ma}  (đo bằng platform-owner)`);
    ket.push({ method, duong, ma, chieu: "cho" });
  }

  const sai = [];
  for (const k of ket) {
    if (k.chieu === "dung" && k.ma === 404) {
      sai.push(`${k.method} ${k.duong} khai ĐANG DÙNG mà máy chủ trả 404 — giao diện sẽ gọi `
        + `đường chết và báo lỗi lạ cho người dùng`);
    }
    if (k.chieu === "cho" && k.ma !== 404) {
      sai.push(`${k.method} ${k.duong} khai CHỜ BACKEND mà máy chủ trả HTTP ${k.ma} — `
        + `đường ĐÃ CHẠY, nhãn đang nói dối`);
    }
  }
  const soDung = ket.filter((k) => k.chieu === "dung").length;
  const soCho = ket.filter((k) => k.chieu === "cho").length;
  console.log(`[đo] đo được ${soDung} đường ĐANG DÙNG + ${soCho} đường CHỜ = ${ket.length}`);
  // SÀN ĐẾM theo TỪNG VẾ: một vế rỗng làm vế ấy của khẳng định dưới đây đúng một cách vô nghĩa.
  expect(soDung, "không đo được đường ĐANG DÙNG nào ⇒ vế 'khác 404' không kiểm gì")
    .toBe(B.API_DANG_DUNG.length);
  expect(soCho, "không đo được đường CHỜ nào ⇒ vế 'đúng 404' không kiểm gì")
    .toBe(B.API_CHO_BACKEND.length);
  expect(sai, "bảng khai KHỚP mã nguồn nhưng KHÔNG khớp máy chủ đang chạy").toEqual([]);
});
