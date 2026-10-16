// TẦNG 3 — HAI MƯƠI MÀN AG-05 (G19) PHẢI BẤM ĐƯỢC **VÀ** ĐỌC DỮ LIỆU THẬT (G20 · AG-02).
//
// VÌ SAO CÓ TỆP NÀY — khoảng trống nó bịt, đo được chứ không phải cảm nhận:
// `thu_giao_dien/04_nhan_va_man_dot3.spec.js` (G19) canh 12 màn đợt 3 bằng ba điều kiện:
// **mở được · không lỗi console · không tràn ngang**. Ba điều kiện ấy KHÔNG nói gì về việc
// màn có ĐỌC dữ liệu thật hay không — một màn dựng ra đúng cái khung rỗng, không gọi đường
// nào, vẫn qua sạch cả ba. Mười sáu màn mới của AG-05 vì thế chưa từng được khẳng định là
// "bấm được VÀ đọc dữ liệu thật" ở bất kỳ ca nào.
//
// BA ĐIỀU KIỆN Ở ĐÂY, và điều kiện thứ ba mới là điều kiện khó:
//   C1 BẤM ĐƯỢC   — có mục menu thật, một cú bấm mở ra màn, tiêu đề khớp tên khai.
//   C2 ĐỌC THẬT   — trong lượt mở màn có phản hồi `/api/v2/**` mã 2xx THẬT, và KHÔNG có 5xx.
//   C3 GẮN VÀO NHAU — DOM phải CHỨNG MINH nó dựng từ phản hồi ấy, theo ĐÚNG MỘT trong hai vế:
//        (a) CÓ DỮ LIỆU: `#man` chứa một giá trị CHỈ có thể đến từ payload (neo), hoặc số
//            dòng bảng bằng độ dài một mảng trong payload;
//        (b) CHƯA CÓ DỮ LIỆU: màn hiện ô trạng thái rỗng NÓI RÕ LÝ DO (`.trang-thai-rong`)
//            và KHÔNG bịa dòng nào — bảng không được có quá một dòng.
//
// VẾ (b) KHÔNG PHẢI KẼ HỞ, và đây là chỗ dễ hiểu sai nhất: nền cô lập của `chay.sh` KHÔNG có
// đợt đối soát, không có lô import, không có việc AI. Bắt những màn ấy phải "có dòng" là bắt
// chúng BỊA dữ liệu — đúng thứ luật 1 của AG-05 cấm. Nên vế (b) là ĐẠT THẬT, với điều kiện
// màn phải NÓI RA là chưa đo được. Màn nào im lặng (khung rỗng, không câu nào) thì HỎNG.
//
// MÀN NÀO CHƯA ĐO ĐƯỢC THÌ GHI RA, KHÔNG TÍNH LÀ ĐẠT: ca 01 in rõ từng màn rơi vào vế (a)
// hay (b), kèm neo tìm được hoặc câu trạng thái rỗng. Con số ấy đi thẳng vào báo cáo.
//
// PHẠM VI: Chromium (Playwright trong `node_modules/`), chạy LOCAL trên nền cô lập của
// `thu_giao_dien/chay.sh`, bind 127.0.0.1. KHÔNG gọi ra hãng ở bất kỳ môi trường nào.
"use strict";
const { test, expect } = require("@playwright/test");
const U = require("./tien_ich");

test.describe.configure({ mode: "serial" });

/* HAI MƯƠI MÀN AG-05 CẮM Ở G19 — đúng danh sách `docs/G19_MAN_MA.md` §3:
   7 tài chính + 6 gói & tính phí (màn `goi` đã có sẵn từ trước, được "làm cho đúng tên")
   + 6 trợ lý AI + 1 hệ thống = 20.
   KHÔNG có `quan-tri-goi`: nó nằm ở MENU NỀN TẢNG, đo bằng tài khoản khác — xem ca 04.
   KHÔNG có `ket-noi-jt`: màn ấy của AG-06 (G17) và đã có ca riêng
   (`05_ket_noi_jt.spec.js` ca 01 + 02, đo lại ở ca 05 dưới đây). */
const MAN = [
  { ma: "cod", ten: "Bảng COD", nhom: "tài chính" },
  { ma: "dot", ten: "Đợt đối soát", nhom: "tài chính" },
  { ma: "bang_ke", ten: "Bảng kê của hãng", nhom: "tài chính" },
  { ma: "chenh_lech", ten: "Chênh lệch đối soát", nhom: "tài chính" },
  { ma: "phai_thu", ten: "Công nợ phải thu", nhom: "tài chính" },
  { ma: "phai_tra", ten: "Công nợ phải trả", nhom: "tài chính" },
  { ma: "dieu_chinh", ten: "Lịch sử điều chỉnh", nhom: "tài chính" },
  { ma: "goi", ten: "Gói & usage", nhom: "gói & tính phí" },
  { ma: "dang-ky", ten: "Chi tiết đăng ký", nhom: "gói & tính phí" },
  { ma: "muc-dung", ten: "Bảng mức dùng", nhom: "gói & tính phí" },
  { ma: "canh-bao", ten: "Cảnh báo hạn mức", nhom: "gói & tính phí" },
  { ma: "lich-su", ten: "Lịch sử tính phí", nhom: "gói & tính phí" },
  { ma: "du-thao", ten: "Dự thảo hoá đơn", nhom: "gói & tính phí" },
  { ma: "ai", ten: "Trợ lý AI — lô import", nhom: "trợ lý AI" },
  { ma: "ai-goi-y", ten: "Gợi ý AI cho người duyệt", nhom: "trợ lý AI" },
  { ma: "ai-canh-bao", ten: "Cảnh báo kiểm tra", nhom: "trợ lý AI" },
  { ma: "ai-trang-thai", ten: "Trạng thái việc AI", nhom: "trợ lý AI" },
  { ma: "ai-lich-su-duyet", ten: "Lịch sử duyệt AI", nhom: "trợ lý AI" },
  { ma: "ai-thong-ke", ten: "Thống kê mức dùng AI", nhom: "trợ lý AI" },
  { ma: "health", ten: "Sức khoẻ hệ thống", nhom: "hệ thống" },
];

/* ============================================================================================
   BỘ ĐO — ba hàm thuần, không hàm nào trả "trông ổn"
   ============================================================================================ */

/** Mọi giá trị VÔ HƯỚNG lá trong payload, kèm đường dẫn tới nó (để in ra đọc lại được).
 *  Đây là nguồn neo: một chuỗi/số lấy từ phản hồi mà nếu thấy trên màn thì DOM CHẮC CHẮN
 *  dựng từ phản hồi ấy — không cách nào mã cứng trước được, vì giá trị chỉ có lúc chạy. */
function nhatVoScalar(o, duong, ra) {
  ra = ra || [];
  duong = duong || "";
  if (o === null || o === undefined) return ra;
  if (Array.isArray(o)) { o.forEach((x, i) => nhatVoScalar(x, `${duong}[${i}]`, ra)); return ra; }
  if (typeof o === "object") {
    Object.entries(o).forEach(([k, v]) => nhatVoScalar(v, duong ? `${duong}.${k}` : k, ra));
    return ra;
  }
  ra.push({ duong: duong, gia_tri: o });
  return ra;
}

/** Neo ĐỦ ĐẶC THÙ để không trùng ngẫu nhiên: chuỗi ≥ 4 ký tự (và không phải từ chung), hoặc
 *  số ≥ 100. Ngưỡng thấp hơn thì `0`, `1`, `có`, `không` khớp bừa ở mọi màn và ca thử xanh
 *  vô nghĩa — đúng kiểu hỏng im lặng mà tệp này sinh ra để chặn. */
const TU_CHUNG = new Set(["true", "false", "null", "không", "chưa có", "không có", "đang",
                          "hoạt động", "sẵn sàng", "thành công", "thất bại", "xong"]);
function duDacThu(g) {
  if (typeof g === "number") return Number.isFinite(g) && Math.abs(g) >= 100;
  if (typeof g !== "string") return false;
  const t = g.trim();
  return t.length >= 4 && !TU_CHUNG.has(t.toLowerCase()) && !/^[\s\d.,%-]*$/.test(t);
}

/** Ô trạng thái rỗng có NÓI RÕ LÝ DO không. Trả {co, chu} — `chu` để in ra đọc lại.
 *  Một câu cụt như "Không có" KHÔNG được tính: nó không nói vì sao, và người dùng không
 *  phân biệt được "chưa có dữ liệu" với "màn hỏng". */
async function docTrangThaiRong(page) {
  const ns = page.locator("#man .trang-thai-rong");
  const n = await ns.count();
  if (!n) return { co: false, chu: "" };
  const chu = (await ns.allTextContents()).join(" ").replace(/\s+/g, " ").trim();
  return { co: true, chu: chu, ro: chu.length >= 20 };
}

/** Số dòng `tbody tr` của từng bảng trong `#man`. */
async function demDongBang(page) {
  return page.locator("#man table").evaluateAll(
    (ts) => ts.map((t) => t.querySelectorAll("tbody tr").length));
}

// ============================================================================================
// 1. HAI MƯƠI MÀN: BẤM ĐƯỢC · ĐỌC THẬT · GẮN VÀO NHAU
// ============================================================================================
test("01 — 20 màn AG-05: bấm được, gọi API thật, và DOM GẮN với phản hồi ấy", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const menu = (await U.docMenu(page)).map((m) => m.ma);

  // C1 — có mặt trên MENU THẬT trước đã. Màn không có đường vào thì mọi phép đo sau vô nghĩa.
  const thieu_menu = MAN.filter((m) => !menu.includes(m.ma)).map((m) => m.ma);
  expect(thieu_menu, "màn khai là đã cắm mà KHÔNG có mục menu — không có đường vào")
    .toEqual([]);

  // Bộ thu phản hồi: gắn MỘT lần, tự làm rỗng trước mỗi màn.
  let goi = [];
  page.on("response", async (r) => {
    const d = new URL(r.url()).pathname;
    if (!d.startsWith("/api/")) return;
    let than = null;
    try { than = await r.json(); } catch { /* không phải JSON — vẫn ghi mã */ }
    goi.push({ d, ma: r.status(), than });
  });

  const hong = [];
  const ket = [];
  for (const m of MAN) {
    goi = [];
    let tieu_de;
    try {
      tieu_de = await U.moMan(page, m.ma);
    } catch (e) {
      hong.push(`${m.ma}: KHÔNG bấm mở được — ${e.message}`);
      ket.push({ ma: m.ma, ten: m.ten, nhom: m.nhom, ket: "HỎNG: không mở được" });
      continue;
    }
    await page.waitForTimeout(200);          // để phản hồi cuối kịp về bộ thu
    if (tieu_de !== m.ten) {
      hong.push(`${m.ma}: tiêu đề màn là "${tieu_de}", khai là "${m.ten}"`);
    }

    // C2 — có đọc thật không.
    const haiXX = goi.filter((g) => g.ma >= 200 && g.ma < 300);
    const namXX = goi.filter((g) => g.ma >= 500);
    const chu = await page.locator("#man").innerText();
    if (!haiXX.length) {
      hong.push(`${m.ma}: mở màn mà KHÔNG gọi đường /api/v2/** nào trả 2xx `
        + `(đã gọi: ${goi.map((g) => g.ma + " " + g.d).join(", ") || "không gọi gì"}) `
        + `⇒ màn dựng khung rỗng, không đọc dữ liệu`);
      ket.push({ ma: m.ma, ten: m.ten, nhom: m.nhom, ket: "HỎNG: không gọi API" });
      continue;
    }
    if (namXX.length) {
      hong.push(`${m.ma}: có phản hồi 5xx — ${namXX.map((g) => g.ma + " " + g.d).join(", ")}`);
    }

    // C3 — DOM gắn với phản hồi ấy. Hai vế, đúng một vế phải đứng vững.
    const neo = [];
    for (const g of haiXX) {
      for (const v of nhatVoScalar(g.than, g.d)) {
        if (duDacThu(v.gia_tri) && chu.includes(String(v.gia_tri))) {
          neo.push(`${v.duong}=${JSON.stringify(v.gia_tri)}`);
        }
      }
    }
    const dong = await demDongBang(page);
    const rong = await docTrangThaiRong(page);

    if (neo.length) {
      ket.push({ ma: m.ma, ten: m.ten, nhom: m.nhom, ket: "CÓ DỮ LIỆU",
                 neo: neo.slice(0, 3).join(" · "), dong: JSON.stringify(dong) });
      continue;
    }
    // Không tìm được neo: còn một đường nữa để vế (a) đứng vững — số dòng bảng khớp độ dài
    // một MẢNG trong payload. Đây đúng phép đo "số dòng DOM = số dòng API" của AG-05.
    const khop = [];
    for (const g of haiXX) {
      const mang = [];
      nhatVoScalar(g.than, g.d);
      for (const [k, v] of Object.entries(g.than && typeof g.than === "object" ? g.than : {})) {
        if (Array.isArray(v)) mang.push({ k: `${g.d}#${k}`, n: v.length, v });
      }
      for (const a of mang) {
        if (a.n > 0 && dong.includes(a.n)) khop.push(`${a.k}=${a.n}`);
      }
    }
    if (khop.length) {
      ket.push({ ma: m.ma, ten: m.ten, nhom: m.nhom, ket: "CÓ DỮ LIỆU (khớp số dòng)",
                 neo: khop.slice(0, 3).join(" · "), dong: JSON.stringify(dong) });
      continue;
    }
    // Vế (b) — chưa có dữ liệu, nhưng phải NÓI RA và KHÔNG được bịa dòng.
    if (rong.co && rong.ro) {
      if (dong.some((n) => n > 1)) {
        hong.push(`${m.ma}: hiện ô "chưa đo được" mà bảng vẫn có ${JSON.stringify(dong)} dòng `
          + `⇒ vừa nói chưa có số liệu vừa bày dòng`);
        ket.push({ ma: m.ma, ten: m.ten, nhom: m.nhom, ket: "HỎNG: rỗng mà có dòng" });
        continue;
      }
      ket.push({ ma: m.ma, ten: m.ten, nhom: m.nhom, ket: "CHƯA CÓ DỮ LIỆU (nói rõ lý do)",
                 neo: rong.chu.slice(0, 90), dong: JSON.stringify(dong) });
      continue;
    }
    hong.push(`${m.ma}: KHÔNG chứng minh được DOM gắn với phản hồi — không có giá trị nào `
      + `của payload xuất hiện trên màn, không khớp số dòng (bảng ${JSON.stringify(dong)}), `
      + `và cũng KHÔNG có ô trạng thái rỗng nói rõ lý do. Màn ${haiXX.length} phản hồi 2xx `
      + `mà không hiện gì đọc được từ chúng.`);
    ket.push({ ma: m.ma, ten: m.ten, nhom: m.nhom, ket: "HỎNG: không gắn được" });
  }

  console.log(`\n[đo] 20 màn AG-05 — kết quả từng màn (${MAN.length} màn):`);
  for (const k of ket) {
    console.log(`   ${k.ma.padEnd(17)} ${String(k.ket).padEnd(30)} ${k.neo ? "neo: " + k.neo : ""}`);
  }
  const coDuLieu = ket.filter((k) => /^CÓ DỮ LIỆU/.test(k.ket)).length;
  const chuaCo = ket.filter((k) => /^CHƯA CÓ DỮ LIỆU/.test(k.ket)).length;
  console.log(`[đo] tổng kết: ${coDuLieu} màn CÓ DỮ LIỆU · ${chuaCo} màn CHƯA CÓ DỮ LIỆU `
    + `(nói rõ lý do) · ${ket.length - coDuLieu - chuaCo} màn HỎNG`);
  console.log(`[đo] trong ${chuaCo} màn chưa có dữ liệu, ĐÂY là danh sách CHƯA ĐO ĐƯỢC `
    + `của lượt này: ` + ket.filter((k) => /^CHƯA CÓ/.test(k.ket)).map((k) => k.ma).join(", "));

  expect(ket.length, "không đo được màn nào ⇒ ca này không kiểm gì").toBe(MAN.length);
  expect(hong, "màn AG-05 bấm được nhưng KHÔNG chứng minh được là đọc dữ liệu thật").toEqual([]);
});

// ============================================================================================
// 2. ĐỐI CHỨNG ĐƯỜNG — SÀN ĐẾM, KHÔNG ĐỂ CA THỬ THÀNH VÔ NGHĨA
// ============================================================================================
// Ca 01 có thể "đạt" theo hai cách rất khác nhau: 20 màn đều có dữ liệu, hoặc 20 màn đều
// rỗng. Cách thứ hai vẫn là một lượt đo hợp lệ (nền cô lập vốn ít dữ liệu), nhưng người đọc
// phải NHÌN THẤY con số ấy chứ không được để nó lẫn vào chữ "đạt". Ca này chốt sàn: nếu
// KHÔNG màn nào có dữ liệu thì lời khai "đọc dữ liệu thật" của tệp này chưa được chứng minh,
// và ca thử phải HỎNG để không ai trích nó làm bằng chứng.
test("02 — ĐỐI CHỨNG: lượt đo phải có ít nhất một màn chứng minh được DỮ LIỆU THẬT", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  let goi = [];
  page.on("response", async (r) => {
    const d = new URL(r.url()).pathname;
    if (!d.startsWith("/api/")) return;
    let than = null;
    try { than = await r.json(); } catch { /* bỏ */ }
    goi.push({ d, ma: r.status(), than });
  });

  // Ba màn mà nền cô lập CHẮC CHẮN có dữ liệu, vì `chuan_bi.py`/`khoi_tao.py` seed sẵn:
  // `goi` (danh mục gói), `muc-dung` (hạn mức của gói hiện tại), `health` (phép kiểm tiến trình).
  const PHAI_CO = ["goi", "muc-dung", "health"];
  const dat = [];
  for (const ma of PHAI_CO) {
    goi = [];
    await U.moMan(page, ma);
    await page.waitForTimeout(200);
    const chu = await page.locator("#man").innerText();
    const neo = [];
    for (const g of goi.filter((x) => x.ma >= 200 && x.ma < 300)) {
      for (const v of nhatVoScalar(g.than, g.d)) {
        if (duDacThu(v.gia_tri) && chu.includes(String(v.gia_tri))) {
          neo.push(`${v.duong}=${JSON.stringify(v.gia_tri)}`);
        }
      }
    }
    console.log(`[đo] đối chứng ${ma}: ${neo.length} neo khớp payload`
      + (neo.length ? " → " + neo.slice(0, 3).join(" · ") : ""));
    if (neo.length) dat.push(ma);
  }
  expect(dat.length, `KHÔNG màn nào trong ${PHAI_CO.join("/")} chứng minh được DOM gắn với `
    + `payload ⇒ ca 01 "đạt" chỉ vì mọi màn đều rỗng, và tệp này CHƯA chứng minh được điều `
    + `nó khai. Không được trích lượt chạy này làm bằng chứng "đọc dữ liệu thật".`)
    .toBeGreaterThan(0);
});

// ============================================================================================
// 3. TỰ KIỂM — BỘ ĐO C3 PHẢI ĐỎ ĐƯỢC
// ============================================================================================
// Ca 01 khẳng định "DOM gắn với payload". Nếu bộ đo ấy không đỏ được thì nó chỉ là một câu
// khẳng định suông. Ca này dựng lại HAI trạng thái hỏng mà bộ đo PHẢI bắt, trên chính màn
// `goi` (màn có dữ liệu thật, đo được 3 gói):
//   (a) `#man` bị làm rỗng ⇒ không neo, không trạng thái rỗng ⇒ phải HỎNG.
//   (b) `#man` chỉ còn một ô trạng thái rỗng CỤT ("Không có") ⇒ phải HỎNG vì không nói lý do.
test("03 — TỰ KIỂM: xoá nội dung màn và câu rỗng cụt đều làm bộ đo C3 ĐỎ", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  let goi = [];
  page.on("response", async (r) => {
    const d = new URL(r.url()).pathname;
    if (!d.startsWith("/api/")) return;
    let than = null;
    try { than = await r.json(); } catch { /* bỏ */ }
    goi.push({ d, ma: r.status(), than });
  });

  // Đo trên màn NGUYÊN VẸN trước: phải có neo. Không có thì ca tự kiểm này vô nghĩa.
  goi = [];
  await U.moMan(page, "goi");
  await page.waitForTimeout(200);
  const chuThat = await page.locator("#man").innerText();
  const neoThat = [];
  for (const g of goi.filter((x) => x.ma >= 200 && x.ma < 300)) {
    for (const v of nhatVoScalar(g.than, g.d)) {
      if (duDacThu(v.gia_tri) && chuThat.includes(String(v.gia_tri))) neoThat.push(v.duong);
    }
  }
  console.log(`[đo] tự kiểm: màn nguyên vẹn có ${neoThat.length} neo`);
  expect(neoThat.length, "màn `goi` nguyên vẹn đã không có neo ⇒ ca tự kiểm không dựng lại "
    + "được trạng thái hỏng một cách có nghĩa").toBeGreaterThan(0);

  // (a) xoá nội dung màn.
  await page.locator("#man").evaluate((n) => { n.innerHTML = ""; });
  const chuRong = await page.locator("#man").innerText();
  const neoRong = neoThat.filter((d) => {
    const g = goi.find((x) => d.startsWith(x.d));
    const v = nhatVoScalar(g && g.than, d).find((y) => y.duong === d);
    return v && chuRong.includes(String(v.gia_tri));
  });
  const rongA = await docTrangThaiRong(page);
  console.log(`[đo] tự kiểm (a) xoá #man: neo=${neoRong.length} trạng thái rỗng=${rongA.co}`);
  expect(neoRong.length, "xoá sạch #man mà bộ đo vẫn thấy neo ⇒ bộ đo không đọc DOM thật")
    .toBe(0);
  expect(rongA.co, "xoá sạch #man mà vẫn thấy ô trạng thái rỗng ⇒ bộ đo hỏng").toBe(false);

  // (b) câu rỗng CỤT: có ô trạng thái rỗng nhưng KHÔNG nói lý do ⇒ vẫn phải HỎNG.
  await page.locator("#man").evaluate((n) => {
    n.innerHTML = '<div class="trang-thai-rong">Không có</div>';
  });
  const rongB = await docTrangThaiRong(page);
  console.log(`[đo] tự kiểm (b) câu rỗng cụt: co=${rongB.co} ro=${!!rongB.ro} "${rongB.chu}"`);
  expect(rongB.co, "ô trạng thái rỗng không được nhận ra ⇒ vế (b) của ca 01 không chạy")
    .toBe(true);
  expect(rongB.ro, "câu rỗng CỤT bị tính là 'nói rõ lý do' ⇒ vế (b) của ca 01 là kẽ hở: "
    + "màn chỉ cần in 'Không có' là qua").toBeFalsy();
});

// ============================================================================================
// 4. MÀN NỀN TẢNG `quan-tri-goi` — CÙNG BA ĐIỀU KIỆN, NHƯNG BẰNG TÀI KHOẢN NỀN TẢNG
// ============================================================================================
// Màn này nằm ở MENU NỀN TẢNG, nên `shopa-owner` không thấy nó. Đo nó bằng tài khoản tenant
// là đo nhầm vai, và kết luận "không có màn" sẽ là kết luận SAI về sản phẩm.
test("04 — màn nền tảng `quan-tri-goi` bấm được và đọc dữ liệu thật", async ({ page }) => {
  await U.dangNhap(page, "platform-owner");
  const menu = (await U.docMenu(page)).map((m) => m.ma);
  expect(menu, "tài khoản nền tảng không thấy mục `quan-tri-goi`").toContain("quan-tri-goi");

  let goi = [];
  page.on("response", async (r) => {
    const d = new URL(r.url()).pathname;
    if (!d.startsWith("/api/")) return;
    let than = null;
    try { than = await r.json(); } catch { /* bỏ */ }
    goi.push({ d, ma: r.status(), than });
  });
  const td = await U.moMan(page, "quan-tri-goi");
  await page.waitForTimeout(200);
  const chu = await page.locator("#man").innerText();
  const neo = [];
  for (const g of goi.filter((x) => x.ma >= 200 && x.ma < 300)) {
    for (const v of nhatVoScalar(g.than, g.d)) {
      if (duDacThu(v.gia_tri) && chu.includes(String(v.gia_tri))) {
        neo.push(`${v.duong}=${JSON.stringify(v.gia_tri)}`);
      }
    }
  }
  console.log(`[đo] quan-tri-goi "${td}": ${goi.length} lời gọi API, ${neo.length} neo khớp`);
  console.log(`   gọi: ${goi.map((g) => g.ma + " " + g.d).join(", ")}`);
  console.log(`   neo: ${neo.slice(0, 4).join(" · ") || "(không có)"}`);
  expect(goi.filter((g) => g.ma >= 200 && g.ma < 300).length,
    "màn nền tảng không gọi đường 2xx nào ⇒ không đọc dữ liệu").toBeGreaterThan(0);
  expect(neo.length, "không giá trị nào của payload xuất hiện trên màn ⇒ DOM không gắn với "
    + "phản hồi (hoặc màn đang rỗng vì lý do khác — đọc log [đo] ở trên)").toBeGreaterThan(0);
});

// ============================================================================================
// 5. ĐỐI CHIẾU: MÀN `ket-noi-jt` (AG-06 · G17) — ĐÃ CÓ CA RIÊNG, ĐO LẠI ĐỂ KHÔNG KHAI LẠI
// ============================================================================================
// Nhiệm vụ G20 nêu màn này trong cùng nhóm "chưa có ca E2E nào khẳng định bấm được và đọc dữ
// liệu thật". ĐO LẠI thì thấy KHÔNG ĐÚNG: `05_ket_noi_jt.spec.js` đã có ca 01 (một cú bấm từ
// menu thật) và ca 02 (từng con số trên màn đối chiếu payload thật). Ca này KHÔNG viết lại
// việc ấy — nó chỉ ĐO LẠI hai điều kiện ấy bằng chính bộ đo của tệp này, để câu "đã có ca"
// là một phép đo ở lượt này chứ không phải một câu chép từ báo cáo cũ.
test("05 — ĐỐI CHIẾU: `ket-noi-jt` (AG-06) đã đạt cả ba điều kiện, không cần ca mới", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  let goi = [];
  page.on("response", async (r) => {
    const d = new URL(r.url()).pathname;
    if (!d.startsWith("/api/")) return;
    let than = null;
    try { than = await r.json(); } catch { /* bỏ */ }
    goi.push({ d, ma: r.status(), than });
  });
  const td = await U.moMan(page, "ket-noi-jt");
  await page.waitForTimeout(200);
  const chu = await page.locator("#man").innerText();
  const neo = [];
  for (const g of goi.filter((x) => x.ma >= 200 && x.ma < 300)) {
    for (const v of nhatVoScalar(g.than, g.d)) {
      if (duDacThu(v.gia_tri) && chu.includes(String(v.gia_tri))) {
        neo.push(`${v.duong}=${JSON.stringify(v.gia_tri)}`);
      }
    }
  }
  console.log(`[đo] ket-noi-jt "${td}": ${goi.filter((g) => g.ma >= 200 && g.ma < 300).length} `
    + `phản hồi 2xx, ${neo.length} neo khớp payload`);
  console.log(`   neo: ${neo.slice(0, 4).join(" · ") || "(không có)"}`);
  expect(td, "tiêu đề màn không khớp").toBe("Kết nối J&T");
  expect(neo.length, "màn mở được nhưng không giá trị nào của payload xuất hiện ⇒ bộ đo "
    + "của tệp này không xác nhận được ca cũ; xem lại `05_ket_noi_jt.spec.js`").toBeGreaterThan(0);
});
