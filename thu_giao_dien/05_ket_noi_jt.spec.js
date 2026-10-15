// TẦNG 3 — MÀN "KẾT NỐI J&T" (G17 · AG-06): đường vào thật, số liệu từ API thật, và
// KHÔNG lộ giá trị credential.
//
// VÌ SAO CÓ TỆP NÀY: màn này trả lời bốn câu mà trước đây không chỗ nào trên giao diện trả
// lời được (đang ở môi trường nào · cổng đã mở chưa · bốn trường credentials có chưa · thao
// tác nào chưa làm được và vì sao). Bốn câu ấy chỉ có giá trị nếu chúng KHỚP dữ liệu thật,
// nên các ca dưới đây không đọc chữ trên màn rồi tin: chúng ĐỌC LẠI API trong chính trang,
// đọc lại MÃ NGUỒN trên đĩa, rồi so với chữ đang hiện.
//
// PHẠM VI: Chromium (Playwright trong `node_modules/`), chạy LOCAL trên nền cô lập của
// `thu_giao_dien/chay.sh`, bind 127.0.0.1. Không gọi hãng ở bất kỳ môi trường nào — có ca
// canh đúng điều đó. Không credentials thật: giá trị dùng ở ca rò rỉ là chuỗi CANARY tự đặt.
"use strict";
const { test, expect } = require("@playwright/test");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const U = require("./tien_ich");

const GOC = join(__dirname, "..");
test.describe.configure({ mode: "serial" });

const MAN = "ket-noi-jt";
const TIEU_DE = "Kết nối J&T";

/** Giá trị CANARY cho ca rò rỉ. KHÔNG phải credential thật và không giống credential thật:
 *  nó chỉ cần một chuỗi mà nếu xuất hiện trên màn thì chắc chắn là rò rỉ. 4 ký tự cuối là thứ
 *  backend lưu ở `carrier_accounts.credentials_duoi` để hiển thị — màn KHÔNG được hiện nó.
 *  Đặt canary cho MỌI tài khoản hãng (không chỉ J&T): tài khoản seed sẵn có `credentials_duoi`
 *  = "mock", mà "mock" cũng là tên môi trường, nên nếu để nguyên thì phép quét "giá trị credential
 *  có lọt ra không" sẽ báo hỏng GIẢ. Canary làm phép đo có nghĩa. */
const CANARY = [{ hang: "jt", gia_tri: "CANARY-AG06-9Q7Z", duoi: "9Q7Z" },
                { hang: "vtp", gia_tri: "CANARY-AG06-VTP-4X8K", duoi: "4X8K" }];

/** Đọc lại BA route thật TỪ TRONG TRANG (mang cookie phiên như giao diện mang). */
async function docApi(page) {
  return page.evaluate(async () => {
    const goi = async (d) => {
      const r = await fetch(d, { headers: { "X-Requested-With": "VIPHub" } });
      return { ma: r.status, ok: r.ok, du_lieu: await r.json().catch(() => null) };
    };
    return {
      g09: await goi("/api/v2/g09/suc-khoe-hang"),
      hang: await goi("/api/v2/hang"),
      tai_khoan: await goi("/api/v2/tai-khoan-hang"),
    };
  });
}

/** Chuẩn hoá khoảng trắng để so chữ đã hiện với chữ trong payload (HTML xuống dòng, gộp space). */
const gon = (s) => String(s == null ? "" : s).replace(/\s+/g, " ").trim();

/** Mọi giá trị NẰM DƯỚI một khóa nghe như bí mật, gom từ payload thật. Dùng cho ca rò rỉ:
 *  đây là danh sách "thứ không được xuất hiện trên màn", lấy từ dữ liệu chứ không chép tay. */
const KHOA_BI_MAT = /(secret|password|private|token|api_?key|duoi)/i;
function giaTriBiMat(o, ra = []) {
  if (Array.isArray(o)) { o.forEach((x) => giaTriBiMat(x, ra)); return ra; }
  if (o && typeof o === "object") {
    for (const [k, v] of Object.entries(o)) {
      if (typeof v === "string" && v && KHOA_BI_MAT.test(k)) ra.push({ khoa: k, gia_tri: v });
      giaTriBiMat(v, ra);
    }
  }
  return ra;
}

/** Đọc hằng của MÃ NGUỒN backend — nguồn chân lý cho hai thứ API không trả (mục 3 và D-9). */
function docMaNguon() {
  const ch = readFileSync(join(GOC, "app", "cau_hinh.py"), "utf8");
  const jt = readFileSync(join(GOC, "app", "adapter_jt.py"), "utf8");
  const tuple = (ten) => {
    const m = ch.match(new RegExp("^" + ten + "\\s*=\\s*\\(([^)]*)\\)", "m"));
    return m ? m[1].split(",").map((x) => x.trim().replace(/^["']|["']$/g, "")).filter(Boolean) : null;
  };
  const khoiDuongApi = jt.slice(jt.indexOf("DUONG_API = {"));
  return {
    nen_tang: tuple("JT_TRUONG_NEN_TANG"),
    buu_cuc: tuple("JT_TRUONG_BUU_CUC"),
    truong_credential: (jt.match(/^TRUONG_CREDENTIAL\s*=\s*\(([^)]*)\)/m) || [])[1]
      ?.split(",").map((x) => x.trim().replace(/^["']|["']$/g, "")).filter(Boolean) || null,
    d9_da_xac_nhan: /^ANH_XA_AREA_DA_XAC_NHAN\s*=\s*True\s*$/m.test(jt),
    d9_nguon: ((jt.match(/^NGUON_XAC_NHAN_AREA\s*=\s*"([^"]*)"/m) || [])[1] ?? null),
    d9_cap: ((jt.match(/^CAP_HANH_CHINH_CHO_AREA\s*=\s*"([^"]*)"/m) || [])[1] ?? null),
    // Khóa của bảng đường dẫn — bốn thao tác của màn phải nằm trong bảng này (còn "đã xác minh
    // hay chưa" thì API không trả, màn khai là CHỜ BACKEND, xem ca 6).
    duong_api: [...khoiDuongApi.slice(0, khoiDuongApi.indexOf("\n}")).matchAll(/"(\w+)":\s*\{/g)]
      .map((m) => m[1]),
  };
}

async function moManKetNoi(page) {
  await U.dangNhap(page, "shopa-owner");
  return U.moMan(page, MAN);
}

// ============================================================================================
// 1. ĐƯỜNG VÀO THẬT — màn phải BẤM ĐƯỢC từ menu, không chỉ tồn tại trên đĩa
// ============================================================================================
test("01 — màn Kết nối J&T có trên MENU THẬT và mở được bằng một cú bấm", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  const menu = await U.docMenu(page);
  const muc = menu.filter((m) => m.ma === MAN);
  expect(muc.length, `menu không có màn ${MAN} — màn tồn tại trên đĩa nhưng không có đường vào`)
    .toBe(1);
  expect(gon(muc[0].ten)).toContain("Kết nối J&T");

  // `U.moMan` bấm ĐÚNG thẻ <a> trên menu như người dùng bấm, rồi chờ nội dung màn đổi thật.
  const tieu_de = await U.moMan(page, MAN);
  expect(tieu_de).toBe(TIEU_DE);
  for (const id of ["#kn-tom-tat", "#kn-cong", "#kn-credential", "#kn-thao-tac", "#kn-d9", "#kn-san-sang"]) {
    await expect(page.locator(id), `thiếu khối ${id}`).toBeVisible();
  }
});

// ============================================================================================
// 2. SỐ LIỆU TRÊN MÀN = SỐ LIỆU API (không số viết tay)
// ============================================================================================
test("02 — cổng · mức sẵn sàng · khoá an toàn trên màn KHỚP payload thật", async ({ page }) => {
  await moManKetNoi(page);
  const api = await docApi(page);
  expect(api.g09.ok && api.hang.ok && api.tai_khoan.ok, "không đọc được API nền ⇒ ca này không kiểm gì").toBe(true);
  const jt = api.g09.du_lieu.hang.jt;

  // (a) ba cổng môi trường: MỞ khi danh sách "còn thiếu gì" RỖNG — đối chiếu từng môi trường.
  const doi = [["mock", null], ["sandbox", "thieu_de_sandbox"], ["production", "thieu_de_live"]];
  for (const [ma, truong] of doi) {
    const the = page.locator(`#kn-cong [data-moi-truong="${ma}"]`);
    await expect(the).toHaveCount(1);
    const chu = gon(await the.textContent());
    if (truong === null) {
      expect(chu, `${ma}: backend không có cổng cho môi trường này`).toContain("CỔNG MỞ");
      continue;
    }
    const ds = jt[truong];
    expect(Array.isArray(ds), `payload thiếu ${truong}`).toBe(true);
    expect(chu, `${ma}: ${ds.length} điều kiện thiếu ⇒ phải là CỔNG CHƯA MỞ`)
      .toContain(ds.length === 0 ? "CỔNG MỞ" : "CỔNG CHƯA MỞ");
    expect(await the.locator("li").count(), `${ma}: số lý do hiện ra ≠ số điều kiện backend trả`)
      .toBe(ds.length);
    for (const ly of ds) {
      expect(chu, `${ma}: màn không hiện nguyên văn lý do của backend`).toContain(gon(ly));
    }
  }

  // (b) khoá an toàn toàn cục: `live_mo` phải khớp, và hai trạng thái phải là hai câu KHÁC NHAU.
  const tomTat = gon(await page.locator("#kn-tom-tat").textContent());
  expect(tomTat).toContain(jt.live_mo ? "CHO_PHEP_LIVE ĐANG MỞ" : "CHO_PHEP_LIVE=False");
  const so_hang_live = api.hang.du_lieu.hang.filter((h) => h.live_mo).length;
  expect(tomTat, "số hãng mở live không khớp /api/v2/hang").toContain(`${so_hang_live}/${api.hang.du_lieu.hang.length}`);

  // (c) kết luận của lượt đo: hiện ĐÚNG giá trị backend trả, không làm tròn thành "ổn".
  for (const [ten, gt] of Object.entries(api.g09.du_lieu.ket_luan)) {
    expect(tomTat, `kết luận ${ten} không khớp payload`).toContain(`${ten} = ${gt}`);
  }

  // (d) bảng sáu mức: đủ số hạng mục, và mức từng dòng lấy từ payload.
  const hang_muc = api.g09.du_lieu.hang_muc;
  await expect(page.locator("#kn-san-sang tbody tr")).toHaveCount(hang_muc.length);
  const bang = gon(await page.locator("#kn-san-sang").textContent());
  for (const hm of hang_muc) {
    expect(bang, `bảng sẵn sàng thiếu hạng mục ${hm}`).toContain(hm);
    expect(bang, `mức của ${hm} không khớp payload`).toContain(gon(jt.san_sang[hm].muc));
  }
});

// ============================================================================================
// 3. KHÔNG LỘ GIÁ TRỊ CREDENTIAL — ca bắt buộc của AG-06
// ============================================================================================
test("03 — credential: KHÔNG giá trị, KHÔNG 4 ký tự cuối lọt ra BẤT KỲ màn nào", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");

  // Đặt canary vào credentials của MỌI tài khoản hãng qua ĐÚNG route rotate của hệ (không
  // credentials thật, không gọi hãng). Rotate là thao tác vận hành thật — nếu đường này rò
  // giá trị thì đó là rò thật, không phải rò do bộ thử tự dựng.
  const dat = await page.evaluate(async ([canary]) => {
    const h = { "X-Requested-With": "VIPHub", "Content-Type": "application/json" };
    const doc = async () => (await (await fetch("/api/v2/tai-khoan-hang", { headers: h })).json()).tai_khoan;
    const truoc = await doc();
    if (!truoc.length) return { loi: "không có tài khoản hãng nào để rotate" };
    const ra = [];
    for (const c of canary) {
      const tk = truoc.filter((x) => x.hang === c.hang)[0];
      if (!tk) { ra.push({ hang: c.hang, loi: "không có tài khoản hãng cho hãng này" }); continue; }
      const r = await fetch(`/api/v2/tai-khoan-hang/${tk.id}/rotate`, {
        method: "POST", headers: h,
        body: JSON.stringify({ credentials: { apiAccount: c.gia_tri, kiem_tra: c.gia_tri + "-2" } }),
      });
      const sau = (await doc()).filter((x) => x.id === tk.id)[0] || {};
      ra.push({ hang: c.hang, ma_rotate: r.status, duoi: sau.credentials_duoi });
    }
    return { ra };
  }, [CANARY.map((c) => ({ hang: c.hang, gia_tri: c.gia_tri }))]);

  expect(dat.loi, dat.loi).toBeUndefined();
  for (const x of dat.ra) {
    expect(x.loi, `${x.hang}: ${x.loi}`).toBeUndefined();
    expect(x.ma_rotate, `rotate credentials của ${x.hang} hỏng ⇒ ca rò rỉ không đo được gì`).toBe(200);
  }
  // 4 ký tự cuối CÓ được lưu (đó là thứ bản cũ đem đi hiển thị) ⇒ đích của phép đo là có thật.
  for (const c of CANARY) {
    const x = dat.ra.filter((y) => y.hang === c.hang)[0];
    expect(x.duoi, `${c.hang}: backend không lưu 4 ký tự cuối ⇒ ca này không đo được gì`).toBe(c.duoi);
  }

  // Backend đã che: giá trị đầy đủ KHÔNG được trả về qua API.
  const api = await docApi(page);
  const thoApi = JSON.stringify(api);
  for (const c of CANARY) {
    expect(thoApi.includes(c.gia_tri), `API trả về NGUYÊN giá trị credential của ${c.hang} — lỗi ở backend`).toBe(false);
  }
  // Danh sách "thứ không được xuất hiện": canary đầy đủ + 4 ký tự cuối + mọi giá trị nằm dưới
  // một khóa nghe như bí mật trong payload thật (danh sách lấy từ DỮ LIỆU, không chép tay).
  const cam = [];
  CANARY.forEach((c) => { cam.push({ nhan: `${c.hang}: giá trị đầy đủ`, gia_tri: c.gia_tri });
                          cam.push({ nhan: `${c.hang}: 4 ký tự cuối`, gia_tri: c.duoi }); });
  const ro = giaTriBiMat({ g09: api.g09.du_lieu, hang: api.hang.du_lieu, tai_khoan: api.tai_khoan.du_lieu })
    // Bỏ qua cột THỜI GIAN (`credentials_doi_luc`) — nó không phải giá trị credential; và bỏ
    // giá trị quá ngắn (1-3 ký tự) vì trùng chữ thường sẽ báo hỏng giả.
    .filter((x) => !/doi_luc|_luc$/.test(x.khoa) && x.gia_tri.length >= 4);
  expect(ro.length, "không gom được giá trị bí mật nào ⇒ ca này không kiểm gì").toBeGreaterThan(0);
  ro.forEach((x) => cam.push({ nhan: `${x.khoa} (từ payload)`, gia_tri: x.gia_tri }));

  // QUÉT MỌI MÀN trên menu: rò rỉ ở màn nào cũng là rò rỉ.
  const menu = (await U.docMenu(page)).map((m) => m.ma);
  expect(menu.length, "menu rỗng ⇒ ca này không quét được gì").toBeGreaterThan(3);
  const lot = [];
  for (const ma of menu) {
    await U.moMan(page, ma);
    const html = await page.evaluate(() => document.documentElement.outerHTML);
    cam.forEach((c) => { if (html.includes(c.gia_tri)) lot.push(`${ma} ← ${c.nhan}`); });
  }

  // NHƯNG TÊN bốn trường thì PHẢI hiện, kèm trạng thái có/không — nếu không thì màn không trả
  // lời được "còn thiếu gì". (Còn trong khung quản trị, chưa rời sang trang tĩnh.)
  await U.moMan(page, MAN);
  await expect(page.locator("#kn-credential [data-truong]")).toHaveCount(4);
  const chu = gon(await page.locator("#kn-credential").textContent());
  for (const ten of docMaNguon().truong_credential) {
    expect(chu, `thiếu tên trường ${ten}`).toContain(ten);
  }
  expect(chu).toMatch(/ĐÃ CẤU HÌNH|CHƯA CẤU HÌNH|CHƯA ĐO ĐƯỢC/);

  // Trang tĩnh cũng phải sạch — quét CUỐI CÙNG vì nó rời khỏi khung quản trị.
  await page.goto("/pages/carriers.html", { waitUntil: "networkidle" });
  await expect(page.locator("#c-noi-dung .dang-tai"), "trang tĩnh không đọc xong dữ liệu")
    .toHaveCount(0);
  const htmlTrang = await page.evaluate(() => document.documentElement.outerHTML);
  cam.forEach((c) => { if (htmlTrang.includes(c.gia_tri)) lot.push(`pages/carriers.html ← ${c.nhan}`); });
  expect(lot, `giá trị credential lọt ra giao diện: ${lot.join(" | ")}`).toEqual([]);
});

// ============================================================================================
// 4. TÊN TRƯỜNG + CHỐT D-9 PHẢI KHỚP MÃ NGUỒN (chống lệch giữa hai bản)
// ============================================================================================
test("04 — bốn tên trường và chốt D-9 khớp ĐÚNG hằng trong mã nguồn backend", async ({ page }) => {
  await moManKetNoi(page);
  const mn = docMaNguon();

  expect(mn.nen_tang && mn.buu_cuc, "không đọc được hằng credentials trong app/cau_hinh.py").toBeTruthy();
  expect(mn.truong_credential, "không đọc được TRUONG_CREDENTIAL trong app/adapter_jt.py").toBeTruthy();
  // Hai tệp backend phải nói CÙNG một bộ bốn tên — lệch nhau là lệch đã có từ trước, không
  // phải do màn này; ca này báo ra chứ không sửa hộ.
  expect([...mn.nen_tang, ...mn.buu_cuc].sort()).toEqual([...mn.truong_credential].sort());

  const trenMan = await page.locator("#kn-credential [data-truong]").evaluateAll((ns) =>
    ns.map((n) => n.getAttribute("data-truong")));
  expect(trenMan.slice().sort(), "tên trường trên màn ≠ hằng của backend (danh sách chép tay đã lệch)")
    .toEqual([...mn.truong_credential].sort());
  // Thứ tự và cách chia nhóm cũng phải theo backend: nhóm Console rồi nhóm bưu cục.
  expect(trenMan).toEqual([...mn.nen_tang, ...mn.buu_cuc]);

  // D-9: màn đọc hằng của mã nguồn, nên chữ trên màn phải đổi theo hằng đó.
  const d9 = gon(await page.locator("#kn-d9").textContent());
  expect(d9, "chốt D-9 trên màn không khớp ANH_XA_AREA_DA_XAC_NHAN của mã nguồn")
    .toContain(mn.d9_da_xac_nhan ? "ĐÃ GỠ" : "ĐANG CHẶN");
  expect(d9).toContain(`ANH_XA_AREA_DA_XAC_NHAN = ${mn.d9_da_xac_nhan ? "True" : "False"}`);
  expect(d9, "không hiện cấp hành chính đang ánh xạ").toContain(mn.d9_cap);
  expect(d9).toContain(mn.d9_nguon ? mn.d9_nguon : "RỖNG — chưa ai xác nhận");
  // Và phải NÓI RA rằng thứ này không đến từ API — nếu im lặng thì người đọc tin nó là số đo.
  expect(d9).toContain("KHÔNG qua API");
});

// ============================================================================================
// 5. BỐN THAO TÁC BỊ KHOÁ + LÝ DO (người vận hành phải thấy cái gì chưa làm được)
// ============================================================================================
test("05 — đủ bốn thao tác bị khoá, mỗi dòng có lý do lấy từ payload", async ({ page }) => {
  await moManKetNoi(page);
  const api = await docApi(page);
  const jt = api.g09.du_lieu.hang.jt;
  const mn = docMaNguon();

  const can = ["cancelOrder", "calculatingFees", "printOrder", "getOrder"];
  const co = await page.locator("#kn-thao-tac tbody tr").evaluateAll((ns) =>
    ns.map((n) => n.getAttribute("data-thao-tac")));
  expect(co.slice().sort(), "danh sách thao tác bị khoá không đúng bốn thao tác đã chốt")
    .toEqual(can.slice().sort());

  for (const t of can) {
    const hang = page.locator(`#kn-thao-tac tr[data-thao-tac="${t}"]`);
    const chu = gon(await hang.textContent());
    expect(chu, `${t}: không đánh dấu BỊ KHOÁ`).toContain("BỊ KHOÁ");
    // Mỗi dòng phải có ít nhất một lý do CỤ THỂ, không phải câu chung.
    expect(chu.length, `${t}: dòng lý do rỗng`).toBeGreaterThan(80);
    // Năng lực adapter trong bảng phải nằm trong DUONG_API của adapter (tên không được bịa).
    const kha_nang = await hang.getAttribute("data-kha-nang");
    expect(mn.duong_api, `${t}: ${kha_nang} không có trong app/adapter_jt.py::DUONG_API`)
      .toContain(kha_nang);
  }
  // Lý do của ba thao tác có hạng mục phải là CHÍNH câu "đo bằng gì" của backend.
  for (const [t, hm] of [["cancelOrder", "huy_don"], ["calculatingFees", "bao_gia"], ["printOrder", "nhan_van_don"]]) {
    const chu = gon(await page.locator(`#kn-thao-tac tr[data-thao-tac="${t}"]`).textContent());
    expect(chu, `${t}: lý do không phải câu backend trả cho hạng mục ${hm}`)
      .toContain(gon(jt.san_sang[hm].do_bang_gi));
    expect(chu, `${t}: không hiện mức backend đo`).toContain(gon(jt.san_sang[hm].muc));
  }
  // getOrder không có hạng mục trong báo cáo ⇒ lý do phải là năng lực adapter, không được bịa.
  const chuGet = gon(await page.locator('#kn-thao-tac tr[data-thao-tac="getOrder"]').textContent());
  expect(chuGet).toContain("capabilities.getOrder=false");
  expect(jt.capabilities.getOrder, "payload đổi capabilities.getOrder ⇒ ca này cần xem lại").toBe(false);
});

// ============================================================================================
// 6. HAI THỨ API KHÔNG TRẢ THÌ PHẢI KHAI LÀ CHƯA CÓ, KHÔNG ĐƯỢC BỊA
// ============================================================================================
test("06 — dữ kiện API không trả: khai CHỜ BACKEND và route đó phải THẬT SỰ chưa có", async ({ page }) => {
  await moManKetNoi(page);
  const duong = await page.evaluate(() =>
    (window.VIPLOGIC.API_CHO_BACKEND || []).map((x) => ({ duong: x.duong, method: x.method, ten: x.ten })));
  const muc = duong.filter((x) => x.duong === "/api/v2/g09/ket-noi-hang");
  expect(muc.length, "màn dựa vào một route CHƯA khai trong admin/logic.js ⇒ nhãn chờ không ai canh")
    .toBe(1);

  // Nhãn "CHỜ BACKEND" chỉ được nói dối nếu route đã có. Bắn thật từ trong trang.
  const ma = await page.evaluate(async (d) => {
    const r = await fetch(d, { headers: { "X-Requested-With": "VIPHub" } });
    return r.status;
  }, muc[0].duong);
  expect([404, 405], `nhãn CHỜ BACKEND nói dối: ${muc[0].duong} trả HTTP ${ma}`).toContain(ma);
});

// ============================================================================================
// 7. KHÔNG GỌI HÃNG · KHÔNG LỖI TRANG · KHÔNG TRÀN NGANG · LỐI VÀO SÂU
// ============================================================================================
test("07 — màn không gọi ra hãng, không lỗi console, không hụt tệp tĩnh", async ({ page }) => {
  const ra = [];
  page.on("request", (r) => {
    const u = r.url();
    if (!u.startsWith("http://127.0.0.1")) ra.push(u);
    else if (/jtexpress|viettelpost|demoopenapi|ylopenapi/i.test(u)) ra.push(u);
  });
  const loi = U.thuLoi(page);
  const tep = U.thuTepTinhHong(page);
  await moManKetNoi(page);
  await page.waitForLoadState("networkidle");
  expect(ra, "màn gọi ra ngoài 127.0.0.1 hoặc tới miền hãng").toEqual([]);
  expect(loi, "lỗi do chính trang sinh ở màn Kết nối J&T").toEqual([]);
  expect(tep, "tệp tĩnh của màn không tải được").toEqual([]);
});

test("08 — lối vào sâu `#ket-noi-jt` mở ĐÚNG màn, và trang pages/carriers.html bấm sang được", async ({ page }) => {
  await U.dangNhap(page, "shopa-owner");
  await page.goto("/admin/index.html#ket-noi-jt", { waitUntil: "domcontentloaded" });
  await page.locator(".menu-quan-tri a").first().waitFor({ state: "visible" });
  await expect(page.locator("#tieu-de")).toHaveText(TIEU_DE);
  await expect(page.locator("#kn-cong")).toBeVisible();

  // Trang demo `pages/carriers.html` phải đọc dữ liệu THẬT (không còn danh sách hãng mô phỏng)
  // và có lối bấm sang màn quản trị.
  await page.goto("/pages/carriers.html", { waitUntil: "networkidle" });
  await expect(page.locator("#c-credential [data-truong]")).toHaveCount(4);
  const chu = gon(await page.locator("#c-noi-dung").textContent());
  expect(chu, "trang vẫn hiện số liệu mô phỏng của bản cũ").not.toMatch(/đơn mô phỏng|Cấu hình \(giả lập\)/);
  expect(chu).toMatch(/CỔNG MỞ|CỔNG CHƯA MỞ/);

  await page.locator('#c-lien-ket a[href$="#ket-noi-jt"]').click();
  await page.locator(".menu-quan-tri a").first().waitFor({ state: "visible" });
  await expect(page.locator("#tieu-de")).toHaveText(TIEU_DE);
  await expect(page.locator("#kn-thao-tac")).toBeVisible();
});

test("09 — chưa đăng nhập: trang nói thẳng, KHÔNG hiện số suy đoán và KHÔNG hiện tên trường", async ({ page }) => {
  await page.context().clearCookies();
  await page.goto("/pages/carriers.html", { waitUntil: "networkidle" });
  const chu = gon(await page.locator("#c-noi-dung").textContent());
  expect(chu).toMatch(/Chưa đọc được trạng thái kết nối/);
  expect(await page.locator("#c-credential [data-truong]").count(),
         "chưa đăng nhập mà vẫn hiện bốn trường credentials").toBe(0);
});

test("10 — màn Kết nối J&T và trang carriers không tràn ngang ở 375px", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 760 });
  await moManKetNoi(page);
  const a = await U.doTranNgang(page);
  console.log("[đo] " + U.moTaTran("375px · màn ket-noi-jt", a));
  expect(a.tai_lieu, "màn Kết nối J&T tràn ngang ở 375px").toBe(0);
  expect(a.phan_tu).toEqual([]);

  await page.goto("/pages/carriers.html", { waitUntil: "networkidle" });
  const b = await U.doTranNgang(page);
  console.log("[đo] " + U.moTaTran("375px · pages/carriers.html", b));
  expect(b.tai_lieu, "pages/carriers.html tràn ngang ở 375px").toBe(0);
  expect(b.phan_tu).toEqual([]);
});
