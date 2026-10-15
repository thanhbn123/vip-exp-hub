/* Giao diện quản trị VIP Express Hub SaaS v2 (local) — SPA nhỏ, gọi API /api/v2/*.
   Quyền được kiểm ở BACKEND; frontend chỉ ẩn/hiện menu theo TOI.quyen cho gọn.
   Không giữ secret nào, không gọi API hãng trực tiếp. */
(function () {
"use strict";
const goc = document.getElementById("goc");
let TOI = null;
let MAN_HIEN_TAI = null;        // màn đang xem — để quay lại sau khi đăng nhập lại (401)
let MAN_CHO_QUAY_LAI = null;    // màn cần mở lại ngay sau khi đăng nhập lại

/* Lỗi API mang theo mã HTTP: màn 401/403 cần biết MÃ, không chỉ biết câu chữ.
   daXuLy = true nghĩa là chỗ ném đã hiện giao diện lỗi rồi, chỗ bắt đừng toast thêm. */
class LoiApi extends Error {
  constructor(thong_diep, ma, kq) {
    super(thong_diep);
    this.ma = ma;
    this.kq = kq || {};
    this.daXuLy = false;
  }
}

async function api(duong, method, du_lieu, headers) {
  let res;
  try {
    res = await fetch(duong, {
      method: method || "GET",
      headers: Object.assign({ "X-Requested-With": "VIPHub", "Content-Type": "application/json" }, headers || {}),
      body: du_lieu != null ? JSON.stringify(du_lieu) : undefined,
    });
  } catch {
    throw new LoiApi("không gọi được máy chủ (mất mạng hoặc máy chủ đã tắt)", 0);
  }
  let kq = {};
  try { kq = await res.json(); } catch {}
  if (!res.ok) {
    const e = new LoiApi(kq.loi || ("HTTP " + res.status), res.status, kq);
    if (res.status === 401 && TOI) {   // đang ở trong hệ mà bị 401 ⇒ phiên hết hạn
      manPhienHetHan(e.message);
      e.daXuLy = true;
    }
    throw e;
  }
  return kq;
}
const T = VIP.thoat, tien = VIP.tien;
const bao = (m, loai) => VIP.toast(m, loai);

/* LOGIC THUẦN nằm ở admin/logic.js — tách ra để bộ thử Node chạy được mà không cần trình
   duyệt. File này chỉ dựng HTML và gắn sự kiện; mọi QUYẾT ĐỊNH (nhãn nào, lọc ra sao, chế độ
   dữ liệu nào) đều hỏi L. Sửa luật nhãn/lọc thì sửa ở logic.js để bộ thử bắt được. */
const L = window.VIPLOGIC;

/* Dựng huy hiệu từ kết quả của logic.js. `la=true` nghĩa là trạng thái backend mới thêm mà
   giao diện chưa biết tên — vẫn hiện NGUYÊN VĂN kèm dấu ⚠, không nuốt im lặng. */
function hh(d, them) {
  if (!d) return "—";
  return `<span class="huy-hieu ${d.lop}${d.la ? " hh-la" : ""}" title="${T(d.ma)}${d.mo_ta ? " — " + T(d.mo_ta) : ""}">${T(d.ten)}${d.la ? " ⚠" : ""}</span>${them || ""}`;
}
/* Nhãn chế độ dữ liệu: MOCK DATA / LOCAL REAL DATA / LIVE CARRIER DATA (brief F01). */
const nhanCheDo = (cd) => cd
  ? `<span class="che-do ${cd.lop}" title="${T(cd.giai_thich)}">${T(cd.nhan)}</span>` : "";

/* Nhãn + hộp CHỜ BACKEND tra từ bảng API_CHO_BACKEND trong logic.js (một chỗ khai duy nhất,
   và bộ thử HTTP bắn thật vào từng đường trong bảng đó — nhãn không nói dối được lâu). */
function nhanChoBackend(duong) {
  const d = L.API_CHO_BACKEND.find(x => x.duong === duong);
  return d ? `<span class="tag-demo" title="${T(d.method + " " + d.duong)} — ${T(d.ghi_chu)}">CHỜ BACKEND</span>`
           : `<span class="tag-demo">CHỜ BACKEND</span>`;
}
function hopChoBackend(duong, loi_them) {
  const d = L.API_CHO_BACKEND.find(x => x.duong === duong) || { duong: duong, method: "?", ghi_chu: "" };
  return `<div class="hop-cho-backend">
    <b>⏳ Chờ backend — ${T(d.ten || d.duong)}</b>
    <div>Giao diện mong đợi <code>${T(d.method)} ${T(d.duong)}</code>. ${T(d.ghi_chu)}</div>
    ${loi_them ? `<div>Máy chủ vừa trả: <b>${T(loi_them)}</b></div>` : ""}
    <div class="ghi-chu-nguon" style="margin-top:6px">Schema mong đợi ghi ở
      <code>admin/logic.js → API_CHO_BACKEND</code> và trong báo cáo gửi AG-00. Giao diện
      <b>không</b> tự chế endpoint giả: chưa có thì để trống, không tuyên bố đã chạy.</div>
  </div>`;
}

/* Báo lỗi đúng loại: 401 đã có màn riêng; 403 mở hộp "Không đủ quyền" nằm lại
   trên màn hình chứ không phải toast trôi qua; còn lại mới dùng toast. */
function baoLoi(e, hanh_dong, quyen_can) {
  if (e && e.daXuLy) return;
  if (e && e.ma === 403) { hopKhongDuQuyen(e, hanh_dong, quyen_can); return; }
  bao((e && e.message) || "lỗi không rõ", "loi");
}
const duoc = (p) => (TOI.quyen || []).includes(p);

/* Gọi API phụ cho dashboard: thiếu quyền thì trả null để màn vẫn dựng được phần còn lại.
   Quyền vẫn do BACKEND chốt — kiểm `quyen` ở đây chỉ để đỡ một lượt gọi chắc chắn 403.
   403 thật từ backend cũng trả null (không nuốt im lặng: chỗ gọi hiện dòng "không có quyền"). */
async function apiNeuDuoc(duong, quyen_can) {
  if (quyen_can && !duoc(quyen_can)) return null;
  try { return await api(duong); }
  catch (e) {
    if (e.daXuLy) throw e;                 // 401 → đã có màn phiên hết hạn
    if (e.ma === 403 || e.ma === 404) return null;
    throw e;
  }
}

/* Canvas không tự co theo cửa sổ — phải vẽ lại. Chỉ giữ MỘT hàm vẽ lại đang hiệu lực,
   nếu không mỗi lần mở màn lại cộng thêm một listener vẽ vào canvas đã bị xóa. */
let VE_LAI = null;
function datVeLai(fn) {
  if (!VE_LAI) {
    let hen = null;
    VE_LAI = { fn };
    window.addEventListener("resize", () => {
      clearTimeout(hen);
      hen = setTimeout(() => { try { VE_LAI && VE_LAI.fn(); } catch {} }, 150);
    });
  }
  VE_LAI.fn = fn;
}

/* ===== Đăng nhập ===== */
function manDangNhap(thong_bao, man_quay_lai) {
  goc.innerHTML = `
  <div class="man-dang-nhap"><div class="hop-dang-nhap">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px">
      <span style="width:34px;height:34px;border-radius:8px;background:var(--do-vip);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800">V</span>
      <b style="font-size:16px">VIP Express Hub — Quản trị</b>
    </div>
    <p style="font-size:12px;color:var(--chu-mo);margin-top:0">Bản SaaS local — dữ liệu demo, hãng vận chuyển ở chế độ MOCK.</p>
    ${thong_bao ? `<div class="hop-loi" style="margin-bottom:12px">${T(thong_bao)}</div>` : ""}
    ${man_quay_lai ? `<div class="hop-loi" style="margin-bottom:12px;background:var(--xanh-duong-nhat);border-color:#BFD4FE;color:var(--xanh-duong)">
      Đăng nhập xong sẽ mở lại màn <b>${T(man_quay_lai)}</b>.</div>` : ""}
    <div class="form-nhom"><label for="dn-ten">Tên đăng nhập</label><input id="dn-ten" autocomplete="username"></div>
    <div class="form-nhom"><label for="dn-mk">Mật khẩu</label><input id="dn-mk" type="password" autocomplete="current-password"></div>
    <button class="nut nut-chinh" id="dn-nut" style="width:100%;justify-content:center">Đăng nhập</button>
    <p style="margin-top:12px"><a id="dn-quen" style="cursor:pointer;font-size:12.5px">Quên mật khẩu?</a></p>
    <p style="font-size:11.5px;color:var(--chu-mo)">Tài khoản demo: xem <code>app/du-lieu/TAI-KHOAN-DEMO.md</code>.</p>
  </div></div>`;
  const vao = async () => {
    try {
      await api("/api/v2/auth/dang-nhap", "POST", {
        ten_dang_nhap: document.getElementById("dn-ten").value.trim(),
        mat_khau: document.getElementById("dn-mk").value,
      });
      khoiDong();
    } catch (e) { manDangNhap(e.message, man_quay_lai); }
  };
  document.getElementById("dn-nut").addEventListener("click", vao);
  goc.querySelectorAll("input").forEach(i => i.addEventListener("keydown", e => { if (e.key === "Enter") vao(); }));
  document.getElementById("dn-quen").addEventListener("click", manQuenMatKhau);
}

function manQuenMatKhau() {
  const m = VIP.moModal("Quên mật khẩu", `
    <p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Chưa cấu hình email ở bản local nên hệ thống dùng
    <b>provider giả lập</b>: token hiện ngay tại đây để bạn thử luồng. Bản thật sẽ gửi qua email.</p>
    <div class="form-nhom"><label>Tên đăng nhập</label><input id="qm-ten"></div>
    <div id="qm-kq"></div>`,
    `<button class="nut" onclick="VIP.dongModal()">Đóng</button><button class="nut nut-chinh" id="qm-gui">Lấy liên kết</button>`);
  m.querySelector("#qm-gui").addEventListener("click", async () => {
    const kq = await api("/api/v2/auth/quen-mat-khau", "POST",
      { ten_dang_nhap: m.querySelector("#qm-ten").value.trim() });
    const o = m.querySelector("#qm-kq");
    o.innerHTML = `<div class="hop-loi" style="background:var(--xanh-la-nhat);border-color:#A7F3D0;color:var(--xanh-la)">${T(kq.thong_bao)}</div>`;
    if (kq.token_gia_lap) {
      o.innerHTML += `
        <div class="form-nhom" style="margin-top:12px"><label>Mật khẩu mới (≥8 ký tự)</label>
        <input id="qm-mk" type="password"></div>
        <button class="nut nut-chinh" id="qm-dat">Đặt lại mật khẩu</button>`;
      o.querySelector("#qm-dat").addEventListener("click", async () => {
        try {
          await api("/api/v2/auth/dat-lai-mat-khau", "POST",
            { token: kq.token_gia_lap, mat_khau_moi: o.querySelector("#qm-mk").value });
          VIP.dongModal(); bao("Đã đặt lại mật khẩu — hãy đăng nhập lại.");
        } catch (e) { baoLoi(e); }
      });
    }
  });
}

/* ===== Màn phiên hết hạn (401) =====
   Trước đây 401 rơi thẳng về màn đăng nhập trống — người dùng không biết mình vừa
   bị đẩy ra vì cái gì, và mất luôn màn đang xem. Nay nói rõ và giữ chỗ để quay lại. */
function manPhienHetHan(ly_do) {
  MAN_CHO_QUAY_LAI = MAN_HIEN_TAI;
  const ten_man = MAN_HIEN_TAI ? (tenMan(MAN_HIEN_TAI) || MAN_HIEN_TAI) : null;
  TOI = null;
  goc.innerHTML = `
  <div class="man-dang-nhap"><div class="hop-dang-nhap" id="hop-het-han">
    <div style="text-align:center;font-size:40px;line-height:1">⏳</div>
    <h2 style="font-size:17px;text-align:center;margin:10px 0 6px">Phiên đăng nhập đã hết hạn</h2>
    <p style="font-size:13px;color:var(--chu-mo);text-align:center;margin-top:0">
      Máy chủ trả lời <b>HTTP 401</b>${ly_do ? ` — ${T(ly_do)}` : ""}.
      Phiên có thể đã hết hạn, bị thu hồi khi đổi mật khẩu, hoặc bạn đã đăng xuất ở thiết bị khác.</p>
    <div class="hop-loi" style="background:var(--xanh-duong-nhat);border-color:#BFD4FE;color:var(--xanh-duong);font-size:12.5px">
      Dữ liệu đang nhập trong hộp thoại <b>không được gửi đi</b> và không được giữ lại — hãy nhập lại sau khi đăng nhập.
      ${ten_man ? `<br>Đăng nhập lại xong, hệ thống mở lại màn <b>${T(ten_man)}</b>.` : ""}
    </div>
    <button class="nut nut-chinh" id="hh-vao" style="width:100%;justify-content:center;margin-top:14px">🔑 Đăng nhập lại</button>
  </div></div>`;
  const n = document.getElementById("hh-vao");
  n.addEventListener("click", () => manDangNhap(null, ten_man));
  n.focus();
}

function tenMan(id) {
  const d = MAN_TENANT.concat(MAN_PLATFORM).find(([m]) => m === id);
  return d ? d[1].replace(/^[^\p{L}]+/u, "") : null;
}

/* ===== Khối / hộp "Không đủ quyền" (403) =====
   Trước đây 403 chỉ hiện toast 3 giây rồi mất, người dùng không biết thiếu quyền gì.
   Backend vẫn là chỗ kiểm quyền — khối này chỉ GIẢI THÍCH câu trả lời 403 của backend. */
function htmlKhongDuQuyen(e, hanh_dong, quyen_can) {
  return `
    <div class="hop-khong-quyen">
      <div class="dau"><span class="bieu-tuong">🔒</span>
        <div><b>Không đủ quyền</b>
          <div class="ma">máy chủ trả <code>HTTP 403</code> — quyết định chặn nằm ở backend, không ở giao diện</div></div></div>
      <table class="bang bang-quyen"><tbody>
        ${hanh_dong ? `<tr><td>Việc bạn vừa làm</td><td><b>${T(hanh_dong)}</b></td></tr>` : ""}
        <tr><td>Vai trò hiện tại</td><td><code>${T(TOI ? TOI.vai_tro : "—")}</code>${TOI && TOI.tenant ? ` tại <b>${T(TOI.tenant.ten)}</b>` : TOI ? " (phạm vi nền tảng)" : ""}</td></tr>
        <tr><td>Quyền còn thiếu</td><td>${quyen_can
          ? `<code>${T(quyen_can)}</code> — vai trò <code>${T(TOI ? TOI.vai_tro : "—")}</code> chưa được cấp quyền này`
          : `<span style="color:var(--chu-mo)">máy chủ không nêu tên quyền; thông điệp gốc: <b>${T(e && e.message)}</b></span>`}</td></tr>
        <tr><td>Thông điệp máy chủ</td><td>${T(e && e.message)}</td></tr>
        <tr><td>Cách mở</td><td>Nhờ <b>TENANT_OWNER</b>/<b>TENANT_ADMIN</b> của doanh nghiệp cấp thêm quyền
          (màn <b>Thành viên</b>), hoặc quản trị nền tảng sửa ma trận <code>role_permissions</code> (màn <b>Vai trò &amp; quyền</b>).</td></tr>
      </tbody></table>
      <p class="ghi-chu">Quyền của bạn <b>lúc đăng nhập</b> (nguồn <code>GET /api/v2/auth/toi</code>, có thể đã cũ nếu quản trị vừa sửa vai trò —
        backend luôn tra lại ở từng lần gọi): ${(TOI && TOI.quyen || []).map(q => `<code>${T(q)}</code>`).join(" · ") || "—"}</p>
    </div>`;
}

function khoiKhongDuQuyen(e, man_id) {
  const d = MAN_TENANT.concat(MAN_PLATFORM).find(([m]) => m === man_id);
  datMan("Không đủ quyền", htmlKhongDuQuyen(e, d ? `mở màn ${tenMan(man_id)}` : null, d ? d[2] : null));
}

function hopKhongDuQuyen(e, hanh_dong, quyen_can) {
  VIP.moModal("Không đủ quyền", htmlKhongDuQuyen(e, hanh_dong, quyen_can),
    `<button class="nut nut-chinh" onclick="VIP.dongModal()">Đã hiểu</button>`);
}

/* ===== Khung sau đăng nhập ===== */
const MAN_TENANT = [
  ["tong-quan", "📊 Tổng quan", null],
  ["don", "📦 Đơn hàng", "tenant.don.xem"],
  ["khach", "👤 Khách hàng", "tenant.khach.xem"],
  ["import", "📥 Import file", "tenant.import.ghi"],
  ["hang", "🚚 Hãng vận chuyển", "tenant.hang.xem"],
  /* G17 · AG-06 — màn kết nối J&T. Cùng quyền với màn Hãng vận chuyển vì nó đọc đúng những
     route mà màn ấy đọc (`tenant.hang.xem` ở backend, không phải ẩn/hiện của giao diện). */
  ["ket-noi-jt", "🔌 Kết nối J&T", "tenant.hang.xem"],
  ["webhook", "🔔 Webhook", "tenant.webhook.xem"],
  ["thanh-vien", "👥 Thành viên", "tenant.membership.xem"],
  ["goi", "💳 Gói & usage", "tenant.billing.xem"],
  ["nhat-ky", "📝 Nhật ký", "tenant.audit.xem"],
  ["cai-dat", "⚙️ Cài đặt", null],
];
const MAN_PLATFORM = [
  ["tenants", "🏢 Tenants", "platform.tenant.xem"],
  ["vai-tro", "🔑 Vai trò & quyền", null],
  ["audit-nen-tang", "📝 Audit nền tảng", "platform.audit.xem"],
  ["cai-dat", "⚙️ Cài đặt", null],
];

function dungKhung() {
  const laPlatform = !TOI.tenant;
  const menu = (laPlatform ? MAN_PLATFORM : MAN_TENANT).filter(([, , p]) => !p || duoc(p));
  const nhieuTenant = (TOI.tenant_kha_dung || []).length > 1;
  goc.innerHTML = `
  <div class="khung">
    <aside class="sidebar" id="sidebar">
      <div class="logo"><span class="dau">V</span> VIP Express Hub</div>
      <nav class="menu-quan-tri">${menu.map(([id, ten]) => `<a data-man="${id}">${ten}</a>`).join("")}</nav>
      <div class="chan">${T(TOI.ho_ten)}<br><b>${T(TOI.vai_tro)}</b>${TOI.tenant ? "<br>" + T(TOI.tenant.ten) : "<br>Nền tảng"}<br>
        <a id="nut-thoat" style="color:#fff;cursor:pointer">Đăng xuất</a></div>
    </aside>
    <div class="noi-dung">
      <div class="bang-demo">⚠️ SaaS LOCAL — hãng vận chuyển đang ở chế độ MOCK, chưa tạo đơn thật</div>
      <header class="header">
        <button class="nut-menu" id="nut-menu">☰</button><h1 id="tieu-de"></h1>
        <div class="phai">${nhieuTenant ? `
          <label for="chon-tenant" style="font-size:12.5px;color:var(--chu-mo)">Doanh nghiệp:</label>
          <select id="chon-tenant" class="nut" style="padding:6px 10px">
            ${TOI.tenant_kha_dung.map(t => `<option value="${t.tenant_id}" ${TOI.tenant && t.tenant_id === TOI.tenant.id ? "selected" : ""}>${T(t.tenant_ten)} (${T(t.role.replace("TENANT_", ""))})</option>`).join("")}
          </select>` : ""}
        </div>
      </header>
      <main class="trang" id="man"></main>
    </div>
  </div>`;
  document.getElementById("nut-thoat").addEventListener("click", async () => {
    try { await api("/api/v2/auth/dang-xuat", "POST", {}); } catch {}
    TOI = null; MAN_HIEN_TAI = null; MAN_CHO_QUAY_LAI = null; manDangNhap();
  });
  document.getElementById("nut-menu").addEventListener("click", () =>
    document.getElementById("sidebar").classList.toggle("mo"));
  goc.querySelectorAll("[data-man]").forEach(a => a.addEventListener("click", () => moMan(a.dataset.man)));
  const sel = document.getElementById("chon-tenant");
  if (sel) sel.addEventListener("change", async () => {
    try {
      await api("/api/v2/auth/doi-tenant", "POST", { tenant_id: +sel.value });
      bao("Đã chuyển doanh nghiệp."); khoiDong();   // nạp lại toàn bộ: không mang dữ liệu tenant cũ
    } catch (e) { baoLoi(e); khoiDong(); }
  });
  // Sau 401 → đăng nhập lại: mở lại đúng màn đang xem, nếu vai trò mới vẫn vào được màn đó.
  const quay_lai = MAN_CHO_QUAY_LAI && menu.some(([m]) => m === MAN_CHO_QUAY_LAI) ? MAN_CHO_QUAY_LAI : null;
  MAN_CHO_QUAY_LAI = null;
  if (quay_lai) bao("Đã mở lại màn bạn đang xem trước khi phiên hết hạn.");
  /* ĐƯỜNG VÀO SÂU `admin/index.html#ket-noi-jt`. SPA này không có router, nên không có hash
     thì MỌI lối vào đều dừng ở màn đầu menu — và một lối vào không tới được chỗ cần tới thì
     không phải lối vào. Hash chỉ được mở khi màn đó CÓ trong menu của vai trò này; vai trò
     không có quyền thì rơi về màn đầu, không hiện màn trắng. */
  const tu_hash = String(location.hash || "").replace(/^#/, "");
  const man_hash = tu_hash && menu.some(([mm]) => mm === tu_hash) ? tu_hash : null;
  moMan(quay_lai || man_hash || menu[0][0]);
}

function datMan(tieu_de, html) {
  document.getElementById("tieu-de").textContent = tieu_de;
  document.getElementById("man").innerHTML = html;
}

/* Đổi hash NGAY TRONG TRANG (`#man-khac`) là điều hướng CÙNG TÀI LIỆU: trình duyệt không nạp
   lại trang, nên nếu chỉ đọc hash lúc dựng khung thì liên kết sâu trông như hỏng — bấm mà
   không có gì xảy ra. Nghe `hashchange` để mở đúng màn. Chỉ mở màn CÓ trên menu của vai trò
   đang đăng nhập: hash không được phép mở màn mà người dùng không có quyền thấy. */
window.addEventListener("hashchange", () => {
  const ma = String(location.hash || "").replace(/^#/, "");
  if (!ma || ma === MAN_HIEN_TAI) return;
  // So bằng `dataset`, KHÔNG ghép hash vào selector: hash là chuỗi người dùng sửa được, và
  // một dấu nháy trong đó làm `querySelector` ném lỗi ngay giữa lượt điều hướng.
  const co = Array.from(goc.querySelectorAll(".menu-quan-tri a")).some((a) => a.dataset.man === ma);
  if (co) moMan(ma);
});

async function moMan(id) {
  MAN_HIEN_TAI = id;
  goc.querySelectorAll("[data-man]").forEach(a => a.classList.toggle("hien-tai", a.dataset.man === id));
  document.getElementById("sidebar").classList.remove("mo");
  /* Ghi màn đang xem vào hash để lối vào sâu (`#ket-noi-jt`) và nút Back của trình duyệt có
     nghĩa. `replaceState` chứ không `pushState`: bấm 6 màn trong menu không nên đắp 6 bước
     vào lịch sử — người dùng bấm Back sẽ phải bấm 6 lần mới thoát khỏi trang quản trị. */
  try { history.replaceState(null, "", "#" + id); } catch { /* file:// hoặc trình duyệt chặn — không quan trọng */ }
  try { await CAC_MAN[id](); }
  catch (e) {
    if (e && e.daXuLy) return;                         // 401 đã có màn riêng
    if (e && e.ma === 403) return khoiKhongDuQuyen(e, id);
    datMan("Lỗi", `<div class="hop-loi"><b>Không mở được màn này.</b><br>${T(e.message)}
      ${e && e.ma ? ` <span class="huy-hieu hh-xam">HTTP ${e.ma}</span>` : ""}</div>`);
  }
}

/* ===== Màn hình ===== */
const CAC_MAN = {
  /* F05 — Dashboard thống kê.
     LUẬT SỐ LIỆU ở màn này: mỗi con số phải nói rõ ĐO TỪ ĐÂU và TRONG PHẠM VI NÀO.
     Không có backend thì ghi "CHỜ BACKEND" và để trống, KHÔNG bịa số minh họa. */
  async "tong-quan"() {
    const GIOI_HAN = 500;
    const don = (await api(`/api/v2/don?gioi_han=${GIOI_HAN}`)).don;
    const b   = await apiNeuDuoc("/api/v2/billing", "tenant.billing.xem");
    const tk  = await apiNeuDuoc("/api/v2/tai-khoan-hang", "tenant.hang.xem");
    const hs  = await apiNeuDuoc("/api/v2/hang", "tenant.hang.xem");
    const im  = await apiNeuDuoc("/api/v2/import", "tenant.don.xem");
    const ad  = await apiNeuDuoc("/api/v2/audit", "tenant.audit.xem");

    const dem = t => don.filter(d => d.trang_thai === t).length;
    const day_du = don.length < GIOI_HAN;        // chưa chạm trần ⇒ đây là TOÀN BỘ đơn của tenant
    const pham_vi = day_du ? `toàn bộ ${don.length} đơn của doanh nghiệp`
                           : `${don.length} đơn mới nhất (chạm trần ${GIOI_HAN} của API — không phải toàn bộ)`;

    /* --- thống kê theo hãng: ghép carrier_account_id của đơn với tài khoản hãng --- */
    const ten_hang = {};
    (hs ? hs.hang : []).forEach(h => ten_hang[h.ma] = h.ten);
    const tk_theo_id = {};
    (tk ? tk.tai_khoan : []).forEach(t2 => tk_theo_id[t2.id] = t2);
    const theo_hang = {};
    don.forEach(d => {
      if (!d.carrier_account_id) return;
      const t2 = tk_theo_id[d.carrier_account_id];
      const ma = t2 ? t2.hang : `tài khoản #${d.carrier_account_id}`;
      const o = theo_hang[ma] = theo_hang[ma] || { tong: 0, da_gui: 0, cod: 0, giao: {} };
      o.tong++; o.cod += d.cod || 0;
      if (d.trang_thai === "da_gui") o.da_gui++;
      if (d.trang_thai_giao) o.giao[d.trang_thai_giao] = (o.giao[d.trang_thai_giao] || 0) + 1;
    });
    const chua_gan_hang = don.filter(d => !d.carrier_account_id).length;
    const hang_ds = Object.entries(theo_hang).sort((a, b2) => b2[1].tong - a[1].tong);

    /* --- thống kê import: đếm batch theo trạng thái --- */
    const batch_tt = {};
    (im ? im.batch : []).forEach(x => batch_tt[x.trang_thai] = (batch_tt[x.trang_thai] || 0) + 1);

    /* --- đơn theo ngày (14 ngày gần nhất, trong phạm vi đã nêu) --- */
    const theo_ngay = {};
    don.forEach(d => { const ng = String(d.tao_luc || "").slice(0, 10); if (ng) theo_ngay[ng] = (theo_ngay[ng] || 0) + 1; });
    const ngay_ds = Object.keys(theo_ngay).sort().slice(-14);

    datMan("Tổng quan", `
      <div class="hop-nguon">
        <b>Nguồn số liệu màn này</b> — <span class="tag-demo">DỮ LIỆU LOCAL / HÃNG MOCK</span>
        <ul>
          <li>Đơn hàng, thống kê theo hãng, đơn theo ngày: <code>GET /api/v2/don?gioi_han=${GIOI_HAN}</code> + <code>GET /api/v2/tai-khoan-hang</code> — phạm vi: <b>${T(pham_vi)}</b>.</li>
          <li>Thống kê import: <code>GET /api/v2/import</code> — phạm vi: <b>100 batch gần nhất</b> (giới hạn do backend đặt). Số DÒNG trong mỗi batch chưa có trong API danh sách.</li>
          <li>Hoạt động gần đây: <code>GET /api/v2/audit</code> — ${ad ? "<b>200 mục gần nhất</b> của doanh nghiệp." : "<b>bạn không có quyền xem</b>."}</li>
          <li>Mọi đơn ở đây tạo qua <b>adapter MOCK</b>, chưa phải đơn thật của hãng vận chuyển.</li>
        </ul>
      </div>

      <div class="luoi luoi-kpi" style="margin-top:16px">
        <div class="the kpi"><div class="nhan">Đơn trong phạm vi</div><div class="so">${don.length}</div>
          <div class="phu">${day_du ? "là toàn bộ đơn" : "đã chạm trần API"}</div></div>
        <div class="the kpi"><div class="nhan">Đã gửi hãng</div><div class="so" style="color:var(--xanh-la)">${dem("da_gui")}</div>
          <div class="phu">${don.length ? Math.round(dem("da_gui") / don.length * 100) : 0}% trong phạm vi</div></div>
        <div class="the kpi"><div class="nhan">Nháp / chờ duyệt</div><div class="so">${dem("nhap") + dem("da_duyet")}</div>
          <div class="phu">${dem("nhap")} nháp · ${dem("da_duyet")} đã duyệt</div></div>
        ${b ? `<div class="the kpi"><div class="nhan">Usage tháng ${T(b.usage.thang)}</div>
          <div class="so">${b.usage.so_don}/${b.goi.han_muc_don_thang}</div><div class="phu">gói ${T(b.goi.ten)} · đo ở backend</div></div>`
            : `<div class="the kpi"><div class="nhan">Usage tháng</div><div class="so" style="font-size:15px">không có quyền</div>
          <div class="phu">cần <code>tenant.billing.xem</code></div></div>`}
      </div>

      <div class="luoi luoi-2" style="margin-top:16px">
        <div class="the"><div class="the-dau"><h2>Đơn theo hãng vận chuyển</h2>
          <div class="phai"><span class="huy-hieu hh-xam">${hang_ds.length} hãng có đơn</span></div></div>
          <div class="the-than">
            ${hang_ds.length ? `<canvas class="bieu-do" id="bd-hang" height="220"></canvas>
            <div class="chu-giai"><span><span class="cham" style="background:${VIP.MAU[0]}"></span>Số đơn — tên hãng ghi dưới trục ngang</span></div>`
              : '<div class="trang-thai-rong"><div class="to">🚚</div>Chưa đơn nào được gán tài khoản hãng</div>'}
            <div class="cuon-ngang" style="margin-top:12px"><table class="bang"><thead><tr>
              <th>Hãng</th><th class="so-tien">Đơn</th><th class="so-tien">Đã gửi</th><th class="so-tien">Tổng COD</th><th>Trạng thái giao</th></tr></thead>
            <tbody>${hang_ds.map(([ma, o]) => `<tr><td><b>${T(ten_hang[ma] || ma)}</b> <code>${T(ma)}</code></td>
              <td class="so-tien">${o.tong}</td><td class="so-tien">${o.da_gui}</td><td class="so-tien">${tien(o.cod)}</td>
              <td style="font-size:12px">${Object.entries(o.giao).map(([k, v]) => `${nhanGiao(k)} <b>${v}</b>`).join("<br>") || "—"}</td></tr>`).join("")
              || '<tr><td colspan="5">—</td></tr>'}
              ${chua_gan_hang ? `<tr><td colspan="5" style="color:var(--chu-mo)">Ngoài ra <b>${chua_gan_hang}</b> đơn chưa gán tài khoản hãng (nháp / đã duyệt / hủy).</td></tr>` : ""}
            </tbody></table></div>
            ${!tk ? '<p class="ghi-chu-nguon">Thiếu quyền <code>tenant.hang.xem</code> nên không đọc được tên hãng — bảng chỉ hiện số hiệu tài khoản.</p>' : ""}
          </div></div>

        <div class="the"><div class="the-dau"><h2>Đơn theo trạng thái</h2></div>
          <div class="the-than">
            ${don.length ? `<canvas class="bieu-do" id="bd-tt" height="220"></canvas>
            <div class="chu-giai">${["nhap", "da_duyet", "dang_gui", "da_gui", "huy"].map((t, i) =>
              `<span><span class="cham" style="background:${VIP.MAU[i % VIP.MAU.length]}"></span>${T(t)} (${dem(t)})</span>`).join("")}</div>`
              : '<div class="trang-thai-rong"><div class="to">📦</div>Chưa có đơn</div>'}
          </div></div>
      </div>

      <div class="luoi luoi-2" style="margin-top:16px">
        <div class="the"><div class="the-dau"><h2>Thống kê import file</h2></div>
          <div class="the-than">
            ${im ? `<div class="luoi luoi-kpi" style="grid-template-columns:repeat(2,1fr)">
                <div class="the kpi" style="box-shadow:none"><div class="nhan">Batch (100 gần nhất)</div><div class="so">${im.batch.length}</div></div>
                <div class="the kpi" style="box-shadow:none"><div class="nhan">Batch thất bại</div>
                  <div class="so" style="color:var(--do-vip)">${(batch_tt.FAILED || 0) + (batch_tt.PARTIAL_FAILED || 0)}</div>
                  <div class="phu">FAILED + PARTIAL_FAILED</div></div>
              </div>
              <div class="cuon-ngang" style="margin-top:12px"><table class="bang bang-hep"><thead><tr><th>Trạng thái batch</th><th class="so-tien">Số batch</th></tr></thead>
              <tbody>${Object.entries(batch_tt).sort((a, c) => c[1] - a[1]).map(([t, n]) =>
                `<tr><td>${nhanBatch(t)}</td><td class="so-tien">${n}</td></tr>`).join("")
                || '<tr><td colspan="2"><div class="trang-thai-rong">Chưa có batch nào</div></td></tr>'}</tbody></table></div>
              <p class="ghi-chu-nguon">Số <b>dòng</b> (VALID/INVALID/NEEDS_REVIEW…) không đếm được ở đây:
                <code>GET /api/v2/import</code> chỉ trả danh sách batch. Mở từng batch ở màn <b>Import file</b> để xem dòng.
                <span class="tag-demo">CHỜ BACKEND</span> cần API tổng hợp số dòng — xem báo cáo cho AG-00.</p>`
              : '<div class="trang-thai-rong">Không có quyền <code>tenant.don.xem</code></div>'}
          </div></div>

        <div class="the"><div class="the-dau"><h2>Đơn theo ngày</h2>
          <div class="phai"><span class="huy-hieu hh-xam">${ngay_ds.length} ngày có đơn</span></div></div>
          <div class="the-than">
            ${ngay_ds.length ? `<canvas class="bieu-do" id="bd-ngay" height="220"></canvas>
              <p class="ghi-chu-nguon">Đếm theo <code>tao_luc</code> của đơn, trong ${T(pham_vi)}.
                Ngày không có đơn nào thì không có cột — đây không phải chuỗi ngày liên tục.</p>`
              : '<div class="trang-thai-rong"><div class="to">📈</div>Chưa có đơn</div>'}
          </div></div>
      </div>

      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Hoạt động gần đây</h2>
        <div class="phai">${ad ? `<span class="huy-hieu hh-xam">${ad.audit.length} mục</span>` : ""}</div></div>
        ${ad ? `<div class="cuon-ngang"><table class="bang"><thead><tr>
            <th>Lúc</th><th>Hành động</th><th>Đối tượng</th><th>Kết quả</th><th>Chi tiết</th></tr></thead>
          <tbody>${ad.audit.slice(0, 12).map(a => `<tr>
            <td style="white-space:nowrap">${T(a.luc)}</td><td><b>${T(a.hanh_dong)}</b></td>
            <td>${T(a.resource_type || "")}${a.resource_id ? ":" + T(a.resource_id) : ""}</td>
            <td><span class="huy-hieu ${a.ket_qua === "thanh_cong" ? "hh-xanh" : a.ket_qua === "tu_choi" ? "hh-vang" : "hh-do"}">${T(a.ket_qua || "")}</span></td>
            <td style="font-size:12px;max-width:260px">${T(a.chi_tiet || "")}</td></tr>`).join("")
            || '<tr><td colspan="5"><div class="trang-thai-rong">Chưa có mục audit nào</div></td></tr>'}</tbody></table></div>
          <p class="ghi-chu-nguon" style="padding:0 18px 14px">12 mục mới nhất trong 200 mục mà <code>GET /api/v2/audit</code> trả về. Xem đủ ở màn <b>Nhật ký</b>.</p>`
          : `<div class="the-than"><div class="trang-thai-rong">Vai trò <code>${T(TOI.vai_tro)}</code> không có quyền
            <code>tenant.audit.xem</code> — không hiện hoạt động gần đây.</div></div>`}
      </div>

      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Chỉ số CHƯA có backend <span class="tag-demo">CHỜ BACKEND</span></h2></div>
        <div class="the-than"><p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">
          Những chỉ số dưới đây <b>không hiện số</b> vì backend chưa có đường lấy — theo luật chống bịa, thà để trống còn hơn hiện số minh họa:</p>
          <ul style="font-size:12.5px;margin:0;padding-left:20px;line-height:1.9">
            <li>Tỷ lệ giao thành công / thất bại theo hãng theo thời gian (cần lịch sử trạng thái giao, API hiện chỉ trả trạng thái mới nhất của đơn).</li>
            <li>Thời gian giao trung bình, SLA theo hãng.</li>
            <li>COD đã đối soát / chưa đối soát (chưa có module đối soát COD trong API v2).</li>
            <li>Số dòng import theo trạng thái trên toàn bộ batch (xem ghi chú ở thẻ Thống kê import).</li>
          </ul></div></div>

      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Đơn mới nhất</h2></div>
      <div class="cuon-ngang"><table class="bang"><thead><tr><th>Mã</th><th>Người nhận</th><th>Hãng</th><th>Trạng thái</th><th>Giao vận</th><th class="so-tien">COD</th></tr></thead>
      <tbody>${don.slice(0, 8).map(d => `<tr><td><b>${T(d.ma_don)}</b></td><td>${T(d.nguoi_nhan_ten)}</td>
        <td>${d.carrier_account_id ? T((tk_theo_id[d.carrier_account_id] || {}).hang || ("#" + d.carrier_account_id)) : "—"}</td>
        <td>${nhanTT(d.trang_thai)}</td><td>${nhanGiao(d.trang_thai_giao)}</td>
        <td class="so-tien">${tien(d.cod)}</td></tr>`).join("") || '<tr><td colspan="6">Chưa có đơn</td></tr>'}</tbody></table></div></div>`);

    /* vẽ biểu đồ sau khi HTML đã vào DOM; vẽ lại khi đổi cỡ cửa sổ (canvas không tự co) */
    const ve = () => {
      const c1 = document.getElementById("bd-hang");
      if (c1) VIP.veBieuDoCot(c1, hang_ds.map(([ma]) => ten_hang[ma] || ma),
        [{ ten: "Đơn", so: hang_ds.map(([, o]) => o.tong) }], [VIP.MAU[0]]);
      const c2 = document.getElementById("bd-tt");
      if (c2) VIP.veBieuDoTron(c2, ["nhap", "da_duyet", "dang_gui", "da_gui", "huy"]
        .map(t => ({ ten: t, so: dem(t) })), VIP.MAU);
      const c3 = document.getElementById("bd-ngay");
      if (c3) VIP.veBieuDoDuong(c3, ngay_ds.map(n => n.slice(5)), ngay_ds.map(n => theo_ngay[n]), VIP.MAU[1]);
    };
    ve();
    datVeLai(ve);
  },

  /* F01 — Order Management UI.
     Ba điều phải đúng ở màn này:
     1. CHẾ ĐỘ DỮ LIỆU hiện rõ từng đơn: MOCK DATA / LOCAL REAL DATA / LIVE CARRIER DATA.
        `CHO_PHEP_LIVE=False` và `live_mo=0` ⇒ không đơn nào được dán LIVE (luật ở L.cheDoDon).
     2. PHẠM VI LỌC nói thật: máy chủ chỉ nhận q · trang_thai · gioi_han (đo ở app/server.py
        15/10/2026). Điều kiện còn lại lọc TẠI GIAO DIỆN trên tập đã tải — ghi rõ, không để
        người đọc tưởng đang lọc toàn bộ CSDL.
     3. API chưa có thì hiện CHỜ BACKEND, không tự chế endpoint. */
  async don() {
    const co_hang = duoc("tenant.hang.xem");
    const tk = co_hang ? await api("/api/v2/tai-khoan-hang") : { tai_khoan: [] };
    const hs = co_hang ? await api("/api/v2/hang") : { hang: [] };
    const tk_theo_id = {}; tk.tai_khoan.forEach(x => tk_theo_id[x.id] = x);
    const hang_theo_ma = {}; hs.hang.forEach(h => hang_theo_ma[h.ma] = h);
    const che_do_he = L.cheDoHeThong(hs.hang);
    const ma_hang_co_tk = [...new Set(tk.tai_khoan.map(x => x.hang))];

    datMan("Đơn hàng", `
      <div class="hang-cong-cu">
        <input id="d-tim" class="o-nho" type="search" placeholder="Tìm mã đơn / mã vận đơn / người nhận / SĐT…" style="min-width:240px">
        <select id="d-tt" class="nut" style="padding:7px 10px"><option value="">Mọi trạng thái</option>
          ${Object.keys(L.TT_DON).map(t => `<option value="${t}">${T(L.TT_DON[t][1])}</option>`).join("")}</select>
        <button class="nut" id="d-nang-cao" aria-expanded="false">⚙ Bộ lọc nâng cao</button>
        <div class="day">
          <a class="nut" href="/api/v2/don/xuat-csv">⬇ Xuất CSV</a>
          ${duoc("tenant.don.ghi") ? `<button class="nut nut-chinh" id="d-them">➕ Tạo đơn</button>` : ""}
        </div>
      </div>

      <div class="the loc-nang-cao" id="d-bang-loc" hidden><div class="the-than">
        <div class="luoi-loc">
          <div class="form-nhom"><label for="l-giao">Trạng thái giao vận</label>
            <select id="l-giao" class="o-nho"><option value="">Mọi trạng thái giao</option>
              ${Object.keys(L.TT_GIAO).map(t => `<option value="${t}">${T(L.TT_GIAO[t][1])}</option>`).join("")}</select></div>
          <div class="form-nhom"><label for="l-hang">Hãng vận chuyển</label>
            <select id="l-hang" class="o-nho"><option value="">Mọi hãng</option>
              ${ma_hang_co_tk.map(m => `<option value="${T(m)}">${T((hang_theo_ma[m] || {}).ten || m)}</option>`).join("")}</select>
            ${co_hang ? "" : '<div class="ghi-chu-nguon">Thiếu quyền <code>tenant.hang.xem</code> nên không lọc được theo hãng.</div>'}</div>
          <div class="form-nhom"><label for="l-tk">Tài khoản hãng cụ thể</label>
            <select id="l-tk" class="o-nho"><option value="">Mọi tài khoản</option>
              ${tk.tai_khoan.map(x => `<option value="${x.id}">${T(x.hang)} · ${T(x.ten)}${x.kich_hoat ? "" : " (khóa)"}</option>`).join("")}</select></div>
          <div class="form-nhom"><label for="l-vd">Mã vận đơn</label>
            <select id="l-vd" class="o-nho"><option value="">Không xét</option>
              <option value="co">Đã có mã vận đơn</option><option value="khong">Chưa có mã vận đơn</option></select></div>
          <div class="form-nhom"><label for="l-cod-tu">COD từ (₫)</label><input id="l-cod-tu" class="o-nho" type="number" min="0" placeholder="0"></div>
          <div class="form-nhom"><label for="l-cod-den">COD đến (₫)</label><input id="l-cod-den" class="o-nho" type="number" min="0" placeholder="không giới hạn"></div>
          <div class="form-nhom"><label for="l-tu-ngay">Tạo từ ngày</label><input id="l-tu-ngay" class="o-nho" type="date"></div>
          <div class="form-nhom"><label for="l-den-ngay">Tạo đến ngày</label><input id="l-den-ngay" class="o-nho" type="date"></div>
          <div class="form-nhom"><label for="l-gioi-han">Số đơn tải từ máy chủ</label>
            <select id="l-gioi-han" class="o-nho">
              <option value="100">100 đơn mới nhất</option><option value="300">300</option><option value="500">500 (trần API)</option></select></div>
          <div class="form-nhom" style="display:flex;align-items:center;gap:8px;padding-top:18px">
            <input type="checkbox" id="l-doi-soat" style="width:auto">
            <label for="l-doi-soat" style="margin:0">Chỉ đơn <b>cần đối soát</b> với hãng</label></div>
        </div>
        <div class="hang-cong-cu" style="margin:6px 0 0"><div class="day">
          <button class="nut" id="l-xoa">↺ Xóa bộ lọc</button></div></div>
        <p class="ghi-chu-nguon" style="margin-top:10px">
          <b>Phạm vi lọc — đọc kỹ:</b> máy chủ chỉ lọc được
          <code>${L.THAM_SO_MAY_CHU.map(x => T(x)).join("</code> · <code>")}</code>.
          ${L.THAM_SO_LOC_TAI_GIAO_DIEN.length} điều kiện còn lại
          (<code>${L.THAM_SO_LOC_TAI_GIAO_DIEN.map(x => T(x)).join("</code> <code>")}</code>)
          lọc <b>tại giao diện trên tập đã tải</b>, nên đơn cũ hơn trần tải về sẽ không xuất hiện
          dù khớp điều kiện. ${nhanChoBackend("/api/v2/don")} cần tham số lọc + <code>tong</code> ở máy chủ.
        </p>
      </div></div>

      <div class="hop-nguon" style="margin-bottom:14px">
        <b>Chế độ dữ liệu màn này</b> — ${nhanCheDo(che_do_he)}
        <ul>
          <li>${nhanCheDo(L.CHE_DO.LOCAL)} đơn chưa gán tài khoản hãng — dữ liệu thật trong CSDL local, chưa gửi hãng nào.</li>
          <li>${nhanCheDo(L.CHE_DO.MOCK)} đơn đã đi qua <b>adapter MOCK</b>: mã vận đơn và phí do bản mô phỏng sinh.</li>
          <li>${nhanCheDo(L.CHE_DO.LIVE)} chỉ xuất hiện khi tài khoản hãng khác môi trường <code>mock</code>
            <b>và</b> hãng mở cờ <code>live_mo</code>. Hiện
            <b>${hs.hang.filter(h => h.live_mo).length}/${hs.hang.length}</b> hãng mở live ⇒
            không đơn nào được dán nhãn LIVE.</li>
        </ul>
      </div>

      <div class="the"><div class="the-dau"><h2>Danh sách đơn</h2>
        <div class="phai" id="d-dem"></div></div>
        <div class="cuon-ngang"><table class="bang">
        <thead><tr><th>Mã</th><th>Người nhận</th><th>Hàng hóa</th><th class="so-tien">COD</th>
        <th>Trạng thái</th><th>Giao vận</th><th>Hãng / tài khoản</th><th>Mã vận đơn</th><th>Chế độ</th><th></th></tr></thead>
        <tbody id="d-bang"></tbody></table></div></div>`);

    const g = (id) => document.getElementById(id);
    const docDieuKien = () => ({
      q: g("d-tim").value.trim(), trang_thai: g("d-tt").value,
      gioi_han: g("l-gioi-han").value,
      trang_thai_giao: g("l-giao").value, hang: g("l-hang").value,
      tai_khoan_id: g("l-tk").value, co_van_don: g("l-vd").value,
      cod_tu: g("l-cod-tu").value, cod_den: g("l-cod-den").value,
      tu_ngay: g("l-tu-ngay").value, den_ngay: g("l-den-ngay").value,
      can_doi_soat: g("l-doi-soat").checked,
    });

    const ve = async () => {
      const dk = docDieuKien();
      const chia = L.chiaDieuKien(dk);
      const ts = new URLSearchParams();
      ts.set("q", chia.may_chu.q || "");
      ts.set("trang_thai", chia.may_chu.trang_thai || "");
      ts.set("gioi_han", chia.may_chu.gioi_han || "100");
      const tai_ve = (await api("/api/v2/don?" + ts.toString())).don;
      const ds = L.locDon(tai_ve, chia.giao_dien, tk_theo_id);
      const so_dk_gd = Object.keys(chia.giao_dien).length;
      const cham_tran = tai_ve.length >= +(chia.may_chu.gioi_han || 100);

      g("d-dem").innerHTML = `<span class="huy-hieu hh-xam">${ds.length}/${tai_ve.length} đơn</span>`;
      g("d-bang").innerHTML = ds.map(d => {
        const t2 = tk_theo_id[d.carrier_account_id];
        const h = t2 ? hang_theo_ma[t2.hang] : null;
        const cd = L.cheDoDon(d, t2, h);
        return `<tr><td><b>${T(d.ma_don)}</b>${d.can_doi_soat_ket_qua
            ? ' <span class="huy-hieu hh-vang" title="hãng timeout — chưa biết kết quả, tuyệt đối không coi là thành công">cần đối soát</span>' : ""}
            <div style="color:var(--chu-mo);font-size:11.5px">${T(String(d.tao_luc || "").slice(0, 16))}</div></td>
          <td>${T(d.nguoi_nhan_ten)}<br><span style="color:var(--chu-mo);font-size:12px">${T(d.nguoi_nhan_sdt)}</span></td>
          <td>${T(d.hang_hoa)}<br><span style="color:var(--chu-mo);font-size:11.5px">${T(d.khoi_luong_gram)}g</span></td>
          <td class="so-tien">${tien(d.cod)}</td>
          <td>${nhanTT(d.trang_thai)}</td><td>${nhanGiao(d.trang_thai_giao)}</td>
          <td style="font-size:12px">${t2 ? `<b>${T(h ? h.ten : t2.hang)}</b><br><span style="color:var(--chu-mo)">${T(t2.ten)} · ${T(t2.moi_truong)}</span>`
            : d.carrier_account_id ? `tài khoản #${d.carrier_account_id} <span class="ghi-chu-nguon">(thiếu quyền đọc tên)</span>` : "—"}</td>
          <td>${T(d.ma_van_don || "—")}</td>
          <td>${nhanCheDo(cd)}</td>
          <td><button class="nut nut-nho" data-xem="${d.id}">Chi tiết</button></td></tr>`;
      }).join("") || `<tr><td colspan="10"><div class="trang-thai-rong"><div class="to">📦</div>
          ${tai_ve.length ? `Máy chủ trả <b>${tai_ve.length}</b> đơn nhưng không đơn nào khớp ${so_dk_gd} điều kiện lọc tại giao diện.`
                          : "Không có đơn nào khớp điều kiện gửi máy chủ."}</div></td></tr>`;

      g("d-pham-vi").innerHTML = `Máy chủ trả <b>${tai_ve.length}</b> đơn
        (lọc máy chủ: ${Object.keys(chia.may_chu).filter(k => chia.may_chu[k] && k !== "gioi_han").length || "không"} điều kiện).
        Giao diện lọc thêm <b>${so_dk_gd}</b> điều kiện, còn <b>${ds.length}</b> đơn.
        ${cham_tran ? `<b class="canh">⚠ Đã chạm trần ${T(chia.may_chu.gioi_han || "100")} đơn — có thể còn đơn cũ hơn khớp điều kiện mà chưa tải về.</b>` : ""}`;

      document.querySelectorAll("[data-xem]").forEach(n =>
        n.addEventListener("click", () => chiTietDon(+n.dataset.xem, tk.tai_khoan, hs.hang, ve)));
    };

    // dòng phạm vi đặt ngay dưới bảng, dựng một lần rồi cập nhật nội dung
    g("d-bang").closest(".the").insertAdjacentHTML("beforeend",
      '<p class="ghi-chu-nguon" id="d-pham-vi" style="padding:0 18px 14px"></p>');

    g("d-tim").addEventListener("input", ve);
    g("d-tt").addEventListener("change", ve);
    g("d-nang-cao").addEventListener("click", () => {
      const o = g("d-bang-loc");
      o.hidden = !o.hidden;
      g("d-nang-cao").setAttribute("aria-expanded", String(!o.hidden));
    });
    ["l-giao", "l-hang", "l-tk", "l-vd", "l-gioi-han", "l-doi-soat"].forEach(id =>
      g(id).addEventListener("change", ve));
    ["l-cod-tu", "l-cod-den", "l-tu-ngay", "l-den-ngay"].forEach(id =>
      g(id).addEventListener("change", ve));
    g("l-xoa").addEventListener("click", () => {
      ["l-giao", "l-hang", "l-tk", "l-vd", "l-cod-tu", "l-cod-den", "l-tu-ngay", "l-den-ngay"]
        .forEach(id => g(id).value = "");
      g("l-doi-soat").checked = false; g("l-gioi-han").value = "100"; ve();
    });
    const nutThem = g("d-them");
    if (nutThem) nutThem.addEventListener("click", () => formDon(null, ve));
    ve();
  },

  /* ================= G17 · AG-06 — MÀN KẾT NỐI J&T =================
     MỘT chỗ trả lời bốn câu của người vận hành: hệ đang ở môi trường nào và cổng đã mở chưa ·
     bốn trường credentials đã có chưa · thao tác nào CHƯA làm được và vì sao · chốt D-9 còn
     chặn không. Trước màn này, bốn câu đó nằm rải trong mã nguồn, tài liệu và đầu người.

     DỮ LIỆU — ba route ĐÃ CÓ, không thêm route nào, không sửa `app/server.py`:
       `GET /api/v2/g09/suc-khoe-hang` · `GET /api/v2/hang` · `GET /api/v2/tai-khoan-hang`
     Phần QUYẾT ĐỊNH (cổng mở/chưa, trường nào có/không, thao tác nào khoá) nằm ở
     `admin/carrier_health.js` mục 8 — ở đây CHỈ dựng HTML, để bộ thử Node kiểm được quyết
     định mà không cần trình duyệt.

     BA ĐIỀU CẤM Ở MÀN NÀY, ghi ra để người sửa sau không vô tình phá:
       1. KHÔNG hiện giá trị credential — không giá trị, không độ dài, không 4 ký tự cuối,
          không băm. Kể cả trong `title`, comment HTML hay chuỗi gửi lên máy chủ.
       2. KHÔNG có nút nào gọi hãng (kể cả sandbox) và không có nút mở cổng. Mở cổng là việc
          phải SỬA MÃ + có phiếu duyệt (`app/cau_hinh.py` ghi rõ lý do), không phải một cú bấm.
       3. KHÔNG bịa số. Chỗ nào API không trả thì hiện "CHƯA ĐO ĐƯỢC" kèm lý do, hoặc nhãn
          CHỜ BACKEND trỏ về `admin/logic.js → API_CHO_BACKEND` — nơi bộ thử HTTP bắn thật. */
  async "ket-noi-jt"() {
    const CH = window.VIPCARRIERHEALTH;
    if (!CH || !CH.dungManKetNoi) {
      datMan("Kết nối J&T", `<div class="hop-loi"><b>Không nạp được <code>admin/carrier_health.js</code>.</b>
        Màn này không tự dựng lại dữ liệu — thiếu module thì phải nói thẳng, không đoán.</div>`);
      return;
    }
    const [bc, hs, tk] = await Promise.all([
      api("/api/v2/g09/suc-khoe-hang"),
      api("/api/v2/hang"),
      api("/api/v2/tai-khoan-hang"),
    ]);
    const m = CH.dungManKetNoi(bc, "jt", tk.tai_khoan);
    const so_hang_live_mo = hs.hang.filter(h => h.live_mo).length;
    const nhanCo = (co, chu_co, chu_khong) => co === true
      ? `<span class="huy-hieu hh-xanh">${chu_co}</span>`
      : co === false ? `<span class="huy-hieu hh-do">${chu_khong}</span>`
      : '<span class="huy-hieu hh-vang" title="API không trả đủ căn cứ — không suy ra là có">CHƯA ĐO ĐƯỢC</span>';
    const nhanMo = (mo) => mo === true ? `<span class="huy-hieu hh-xanh">CỔNG MỞ</span>`
      : mo === false ? `<span class="huy-hieu hh-do">CỔNG CHƯA MỞ</span>`
      : '<span class="huy-hieu hh-vang">CHƯA ĐO ĐƯỢC</span>';

    datMan("Kết nối J&T", `
      <div class="hop-nguon" style="margin-bottom:14px">
        <b>Màn này đọc gì:</b> ba route đã có của hệ (${["GET /api/v2/g09/suc-khoe-hang",
          "GET /api/v2/hang", "GET /api/v2/tai-khoan-hang"].map(x => `<code>${T(x)}</code>`).join(" · ")}).
        Nó <b>chỉ đọc</b>: không gọi hãng ở bất kỳ môi trường nào, không có nút mở cổng, không sửa credentials.
        Dòng nào không đo được từ ba route ấy thì ghi rõ "chưa đo được" ngay trên dòng đó.
      </div>

      <div class="the" id="kn-tom-tat"><div class="the-dau"><h2>${T(m.ten)} — đang ở đâu</h2>
        <div class="phai">${hh({ lop: m.suc_khoe.lop, ten: m.suc_khoe.trang_thai, la: false, mo_ta: m.suc_khoe.mo_ta })}</div></div>
        <div class="the-than">
          <p style="margin-top:0">${T(m.suc_khoe.mo_ta)} · <span class="ghi-chu-nguon">phạm vi: ${T(m.suc_khoe.pham_vi)}</span></p>
          <div class="luoi luoi-3">
            <div><div class="ghi-chu-nguon">Môi trường ghi trên tài khoản hãng</div>
              ${m.moi_truong_tai_khoan.length
                ? m.moi_truong_tai_khoan.map(x => `<div><b>${T(x.moi_truong)}</b> · ${T(x.ten)}
                    ${x.kich_hoat ? '<span class="huy-hieu hh-xanh">đang bật</span>' : '<span class="huy-hieu hh-xam">đang khoá</span>'}
                    <div class="ghi-chu-nguon">credentials đổi lần cuối: ${x.credentials_doi_luc ? T(x.credentials_doi_luc) : "chưa ghi nhận"}</div></div>`).join("")
                : '<div class="trang-thai-rong">Chưa có tài khoản hãng nào cho J&T</div>'}</div>
            <div><div class="ghi-chu-nguon">Khoá an toàn toàn cục</div>
              ${m.khoa_toan_cuc.live_mo
                ? '<span class="huy-hieu hh-do">CHO_PHEP_LIVE ĐANG MỞ</span>'
                : '<span class="huy-hieu hh-xanh">CHO_PHEP_LIVE=False</span>'}
              <div class="ghi-chu-nguon">${T(m.khoa_toan_cuc.ly_do)}</div>
              <div class="ghi-chu-nguon">khoá chống trùng: ${m.khoa_toan_cuc.khoa_chong_trung ? "đang bật" : "TẮT"}</div>
              <div class="ghi-chu-nguon">Hãng mở live trong hệ: <b>${so_hang_live_mo}/${hs.hang.length}</b> (${T((hs.hang.map(h => h.ma).join(", ")) || "—")})</div></div>
            <div><div class="ghi-chu-nguon">Kết luận của lượt đo gần nhất</div>
              ${m.ket_luan.map(k => `<div>${hh({ lop: k.lop, ten: k.ten + " = " + k.gia_tri, la: false, mo_ta: "" })}</div>`).join("")}
              <div class="ghi-chu-nguon">Lượt chạy harness trong báo cáo này:
                ${m.lan_chay ? T(JSON.stringify(m.lan_chay)) : "<b>chưa có lượt nào</b>"}</div></div>
          </div>
        </div></div>

      <div class="the" id="kn-cong" style="margin-top:16px"><div class="the-dau">
        <h2>Cổng môi trường — đã MỞ hay CHƯA</h2>
        <div class="phai"><span class="huy-hieu hh-xam">nguồn: ${T("GET /api/v2/g09/suc-khoe-hang")}</span></div></div>
        <div class="luoi luoi-3">
          ${m.cong.map(c => `<div class="the the-hang" data-moi-truong="${T(c.ma)}">
            <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
              <b>${T(c.ten)}</b> ${nhanMo(c.mo)}</div>
            <div style="font-size:12.5px;color:var(--chu-mo);margin-top:6px">${T(c.ket_luan)}</div>
            ${c.ly_do.length ? `<ul style="margin:8px 0 0;padding-left:18px;font-size:12.5px">
              ${c.ly_do.map(l => `<li>${T(l)}</li>`).join("")}</ul>` : ""}
            <div class="ghi-chu-nguon" style="margin-top:auto">nguồn: <code>${T(c.nguon)}</code></div>
          </div>`).join("")}
        </div>
        <div class="the-than" style="padding-top:0">
          <div class="ghi-chu-nguon">Cổng MỞ khi danh sách "còn thiếu gì" của backend RỖNG —
            giao diện không tự đặt điều kiện, chỉ đọc. Mở cổng phải SỬA MÃ trong
            <code>app/cau_hinh.py</code> và có phiếu duyệt của Owner; màn này cố ý không có nút mở.</div>
        </div></div>

      <div class="the" id="kn-credential" style="margin-top:16px"><div class="the-dau">
        <h2>Bốn trường credentials — chỉ TÊN và trạng thái có/không</h2>
        <div class="phai">${m.credential.do_duoc
          ? '<span class="huy-hieu hh-xanh-duong">backend có trả căn cứ</span>'
          : '<span class="huy-hieu hh-vang">backend chưa trả đủ căn cứ</span>'}</div></div>
        <div class="the-than">
          <div class="hop-loi" style="background:var(--xanh-duong-nhat);border-color:#BFDBFE;color:var(--xanh-duong)">
            Màn này <b>không hiện giá trị</b>, <b>không hiện độ dài</b>, <b>không hiện 4 ký tự cuối</b>,
            <b>không hiện băm</b> của bất kỳ trường nào. Cột
            <code>carrier_accounts.credentials_duoi</code> (4 ký tự cuối) <b>cố ý không được đọc</b>:
            đó là một phần giá trị credential, không phải thông tin vận hành.
          </div>
          <div class="luoi luoi-2">
            ${m.credential.nhom.map(n => `<div>
              <div class="ghi-chu-nguon">${T(n.nhom)}</div>
              <ul style="margin:6px 0 0;padding-left:18px">
                ${n.truong.map(t => `<li data-truong="${T(t.ten)}"><code>${T(t.ten)}</code>
                  ${nhanCo(t.co, "ĐÃ CẤU HÌNH", "CHƯA CẤU HÌNH")}
                  <div class="ghi-chu-nguon">${T(t.ly_do)}</div></li>`).join("")}
              </ul></div>`).join("")}
          </div>
          <div class="ghi-chu-nguon">Căn cứ: <code>${T(m.credential.nguon)}</code></div>
          ${m.credential.do_duoc ? "" : `<div class="ghi-chu-nguon" style="margin-top:8px">
            ${m.credential.ly_do.map(l => T(l)).join(" ")}</div>
            ${hopChoBackend("/api/v2/g09/ket-noi-hang")}`}
          <div class="ghi-chu-nguon" style="margin-top:8px">Nhóm 2 lấy từ hợp đồng bưu cục:
            thiếu nhóm này thì ký đúng vẫn không tạo được đơn —
            <code>app/harness_hang.py</code> mục 3 ghi rõ.</div>
        </div></div>

      <div class="the" id="kn-thao-tac" style="margin-top:16px"><div class="the-dau">
        <h2>Thao tác ĐANG BỊ KHOÁ — ${m.so_thao_tac_khoa}/${m.thao_tac.length}</h2>
        <div class="phai"><span class="huy-hieu hh-xam">nguồn: g09/suc-khoe-hang + /api/v2/hang</span></div></div>
        <div class="cuon-ngang"><table class="bang">
          <thead><tr><th style="white-space:nowrap">Thao tác</th><th style="white-space:nowrap">Hạng mục sẵn sàng</th>
          <th style="white-space:nowrap">Mức backend đo</th>
          <th style="white-space:nowrap">Năng lực adapter</th><th style="white-space:nowrap">Trạng thái</th>
          <th style="min-width:420px">Vì sao chưa làm được</th></tr></thead>
          <tbody>${m.thao_tac.map(t => `<tr data-thao-tac="${T(t.thao_tac)}" data-kha-nang="${T(t.ten_kha_nang)}">
            <td><code>${T(t.thao_tac)}</code></td>
            <td>${T(t.ten_hang_muc)}${t.hang_muc ? ` <span class="ghi-chu-nguon">(${T(t.hang_muc)})</span>` : ""}</td>
            <td>${t.muc ? hh({ lop: t.lop, ten: t.muc, la: t.muc_la, mo_ta: "" }) : '<span class="huy-hieu hh-vang">không có hạng mục</span>'}</td>
            <td>${t.kha_nang === true ? '<span class="kha-nang co">có</span>' : t.kha_nang === false
                 ? '<span class="kha-nang khong">KHÔNG</span>' : '<span class="huy-hieu hh-vang">chưa đo được</span>'}</td>
            <td>${t.khoa ? '<span class="huy-hieu hh-do">BỊ KHOÁ</span>' : '<span class="huy-hieu hh-xanh">không khoá</span>'}</td>
            <td><ul style="margin:0;padding-left:16px;font-size:12.5px">${t.ly_do.map(l => `<li>${T(l)}</li>`).join("")}</ul>
              ${t.do_bang_gi ? `<div class="ghi-chu-nguon">đo bằng gì: ${T(t.do_bang_gi)}</div>` : ""}</td>
          </tr>`).join("")}</tbody></table></div>
        <div class="the-than" style="padding-top:0">
          <div class="ghi-chu-nguon"><b>"Bị khoá" là câu SUY RA</b> theo hướng an toàn: còn bất kỳ
            lý do nào khiến thao tác không gọi được hãng thật thì giao diện coi là khoá — và in
            ra từng lý do kèm nguồn. Giao diện không hứa thay backend.</div>
        </div></div>

      <div class="the" id="kn-d9" style="margin-top:16px"><div class="the-dau">
        <h2>Chốt D-9 — ánh xạ <code>area</code> (city/area)</h2>
        <div class="phai">${m.d9.dang_bat
          ? '<span class="huy-hieu hh-do">ĐANG CHẶN</span>'
          : '<span class="huy-hieu hh-vang">ĐÃ GỠ (theo mã nguồn)</span>'}</div></div>
        <div class="the-than">
          <p style="margin-top:0"><b>${T(m.d9.ket_luan)}</b></p>
          <p>${T(m.d9.vi_sao)}</p>
          <div class="luoi luoi-3">
            <div><div class="ghi-chu-nguon">Hằng trong mã nguồn</div>
              <code>${T(m.d9.hang_so)} = ${m.d9.dang_bat ? "False" : "True"}</code></div>
            <div><div class="ghi-chu-nguon">Nguồn xác nhận của hãng</div>
              ${m.d9.nguon_xac_nhan ? T(m.d9.nguon_xac_nhan)
                : '<span class="huy-hieu hh-do">RỖNG — chưa ai xác nhận</span>'}</div>
            <div><div class="ghi-chu-nguon">Cấp hành chính đang ánh xạ</div>
              <code>${T(m.d9.cap_hanh_chinh)}</code></div>
          </div>
          <div class="hop-loi" style="margin-top:12px">
            <b>Đọc dòng này trước khi tin phần còn lại:</b> trạng thái D-9 lấy từ
            <b>MÃ NGUỒN</b> (<code>${T(m.d9.nguon_ma)}</code>), <b>KHÔNG qua API</b> — vì không
            route nào trả nó. Ca E2E đọc lại chính tệp đó và so với chữ trên màn: mã nguồn đổi
            mà màn chưa đổi là ca HỎNG.
            ${T(m.d9.ghi_chu_api)} ${nhanChoBackend("/api/v2/g09/ket-noi-hang")}
          </div>
        </div></div>

      <div class="the" id="kn-san-sang" style="margin-top:16px"><div class="the-dau">
        <h2>Bảng sáu mức sẵn sàng của ${T(m.ten)} — ${m.san_sang.length} hạng mục</h2>
        <div class="phai">${hh(m.ngat_mach, " ngắt mạch: " + T(m.ngat_mach.ten))}</div></div>
        <div class="cuon-ngang"><table class="bang">
          <thead><tr><th>Hạng mục</th><th>Mức</th><th>Đo bằng gì</th></tr></thead>
          <tbody>${m.san_sang.map(d => `<tr><td>${T(d.ten)} <span class="ghi-chu-nguon">(${T(d.ma)})</span></td>
            <td>${hh({ lop: d.lop, ten: d.muc, la: d.muc_la, mo_ta: d.do_bang_gi })}</td>
            <td style="font-size:12.5px">${T(d.do_bang_gi)}
            ${d.thieu_do_bang_gi ? ' <span class="huy-hieu hh-vang">thiếu câu đo bằng gì</span>' : ""}</td></tr>`).join("")}
          </tbody></table></div>
        <div class="the-than" style="padding-top:0">
          <div class="ghi-chu-nguon">Ngắt mạch: ${T(m.ngat_mach.mo_ta)}${m.ngat_mach.biet ? "" : " — mặc định KHÔNG phải \"bình thường\", chỉ là chưa đo."}</div>
          ${m.can_soat.length ? `<div class="ghi-chu-nguon" style="margin-top:6px">Mã trạng thái hãng còn
            NEEDS_REVIEW/AMBIGUOUS: ${m.can_soat.map(c => `<code>${T(c.ma)}</code> (${T(c.nhan)})`).join(" · ")}
            — đơn mang mã này KHÔNG tiến trạng thái. Màn này không cho chốt nghĩa: chốt nghĩa đòi căn cứ thật từ hãng.</div>` : ""}
        </div></div>

      <div class="the" id="kn-nguon" style="margin-top:16px"><div class="the-than">
        <b>Phạm vi đã đo của màn này</b>
        <ul style="margin:6px 0 0;padding-left:18px;font-size:12.5px">
          <li>Đo được: cổng môi trường · mức sẵn sàng từng hạng mục · khoá an toàn · năng lực adapter ·
            môi trường và lần đổi credentials của tài khoản hãng · kết luận lượt đo.</li>
          <li>KHÔNG đo được (và màn nói thẳng): trạng thái TỪNG trường credentials khi backend không
            liệt kê tên trường thiếu · bảng đường dẫn đã/chưa xác minh của hãng · chốt D-9 qua API ·
            ngắt mạch (payload chưa có trường này).</li>
          <li>${T(m.khong_vi)}</li>
        </ul>
      </div></div>`);
  },

  async khach() {
    const kq = await api("/api/v2/khach-hang");
    datMan("Khách hàng", `
      ${duoc("tenant.khach.ghi") ? `<div class="hang-cong-cu"><div class="day"><button class="nut nut-chinh" id="k-them">➕ Thêm khách</button></div></div>` : ""}
      <div class="the"><div class="cuon-ngang"><table class="bang">
      <thead><tr><th>Tên</th><th>SĐT</th><th>Địa chỉ</th><th>Tạo lúc</th></tr></thead>
      <tbody>${kq.khach_hang.map(k => `<tr><td><b>${T(k.ten)}</b></td><td>${T(k.sdt || "")}</td>
        <td>${T(k.dia_chi || "")}</td><td>${T(k.tao_luc)}</td></tr>`).join("")
        || '<tr><td colspan="4"><div class="trang-thai-rong"><div class="to">👤</div>Chưa có khách</div></td></tr>'}</tbody></table></div></div>`);
    const n = document.getElementById("k-them");
    if (n) n.addEventListener("click", () => {
      const m = VIP.moModal("Thêm khách hàng", `
        <div class="form-nhom"><label>Tên <span class="bat-buoc">*</span></label><input id="k-ten"></div>
        <div class="form-nhom"><label>SĐT</label><input id="k-sdt"></div>
        <div class="form-nhom"><label>Địa chỉ</label><input id="k-dc"></div>`,
        `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="k-luu">Lưu</button>`);
      m.querySelector("#k-luu").addEventListener("click", async () => {
        try {
          await api("/api/v2/khach-hang", "POST", { ten: m.querySelector("#k-ten").value,
            sdt: m.querySelector("#k-sdt").value, dia_chi: m.querySelector("#k-dc").value });
          VIP.dongModal(); bao("Đã thêm khách."); moMan("khach");
        } catch (e) { baoLoi(e, "thêm khách hàng", "tenant.khach.ghi"); }
      });
    });
  },

  async import() {
    const kq = await api("/api/v2/import");
    datMan("Import file", `
      <div class="buoc-day" id="i-buoc">
        <div class="buoc hien-tai"><span class="so-buoc">1</span>Upload file</div>
        <div class="buoc"><span class="so-buoc">2</span>Ánh xạ cột</div>
        <div class="buoc"><span class="so-buoc">3</span>Kiểm tra &amp; sửa dòng</div>
        <div class="buoc"><span class="so-buoc">4</span>Duyệt → đơn nháp</div>
      </div>
      <div class="the"><div class="the-than">
        <p style="margin-top:0">Hỗ trợ <b>CSV</b>, <b>XLSX</b>, <b>PDF có lớp văn bản</b> (PDF scan chưa hỗ trợ — sẽ báo lỗi rõ).
        Upload chỉ tạo <b>batch xem trước</b>; đơn chỉ được tạo sau khi bạn duyệt.</p>
        <div class="hang-cong-cu" style="margin-bottom:0">
          <input type="file" id="i-tep" accept=".csv,.xlsx,.pdf">
          <button class="nut nut-chinh" id="i-len">⬆ Upload</button>
        </div>
      </div></div>
      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Các batch</h2>
        <div class="phai"><button class="nut nut-nho" id="i-moi">↻ Làm mới</button></div></div>
      <div class="cuon-ngang"><table class="bang"><thead><tr><th>#</th><th>File</th><th>Loại</th><th>Trạng thái</th><th>Lúc</th><th></th></tr></thead>
      <tbody>${kq.batch.map(b => `<tr><td>${b.id}</td><td>${T(b.ten_file)}</td>
        <td><code>${T(b.loai_file || "")}</code></td><td>${nhanBatch(b.trang_thai)}</td>
        <td style="white-space:nowrap">${T(b.tao_luc)}</td><td><button class="nut nut-nho" data-batch="${b.id}">Mở</button></td></tr>`).join("")
        || '<tr><td colspan="6"><div class="trang-thai-rong"><div class="to">📥</div>Chưa có batch</div></td></tr>'}</tbody></table></div></div>
      <div id="i-chi-tiet" style="margin-top:16px"></div>`);
    document.getElementById("i-moi").addEventListener("click", () => moMan("import"));
    document.getElementById("i-len").addEventListener("click", async () => {
      const f = document.getElementById("i-tep").files[0];
      if (!f) { bao("Chọn file trước.", "canh-bao"); return; }
      const b64 = btoa(String.fromCharCode(...new Uint8Array(await f.arrayBuffer())));
      try {
        const kq2 = await api("/api/v2/import", "POST", { ten_file: f.name, noi_dung_base64: b64 });
        bao("Đã tạo batch #" + kq2.batch_id); moMan("import");
      } catch (e) { baoLoi(e, "upload file import", "tenant.import.ghi"); }
    });
    document.querySelectorAll("[data-batch]").forEach(n => n.addEventListener("click", () => moBatch(+n.dataset.batch)));
  },

  async hang() {
    const [hs, tk] = await Promise.all([api("/api/v2/hang"), api("/api/v2/tai-khoan-hang")]);
    const ql = duoc("tenant.hang.quan_ly");
    // trạng thái kết nối suy từ tài khoản hãng THẬT của tenant (không phải ping hãng — xem ghi chú dưới thẻ)
    const tk_theo_hang = {};
    tk.tai_khoan.forEach(t2 => (tk_theo_hang[t2.hang] = tk_theo_hang[t2.hang] || []).push(t2));
    datMan("Hãng vận chuyển", `
      <div class="luoi luoi-3">${hs.hang.map(h => {
        const ds = tk_theo_hang[h.ma] || [];
        const bat = ds.filter(x => x.kich_hoat).length;
        const kn = !ds.length ? ["hh-xam", "Chưa kết nối", "doanh nghiệp chưa có tài khoản hãng này"]
                 : bat ? ["hh-xanh", `Đã kết nối (${bat}/${ds.length} đang bật)`, "có tài khoản hãng đang bật"]
                       : ["hh-do", `Tài khoản bị khóa (0/${ds.length} bật)`, "có tài khoản nhưng đều đang khóa/thu hồi"];
        return `
        <div class="the the-hang">
          <div style="display:flex;align-items:flex-start;gap:8px;flex-wrap:wrap">
            <span class="ten-hang">${T(h.ten)}</span> <code style="font-size:11.5px">${T(h.ma)}</code>
          </div>
          <div style="display:flex;gap:6px;flex-wrap:wrap">
            <span class="huy-hieu ${kn[0]}" title="${T(kn[2])}">${T(kn[1])}</span>
            <span class="huy-hieu ${h.live_mo ? "hh-xanh" : "hh-vang"}" title="cờ live_mo trong CSDL — khóa an toàn, giao diện không mở được">
              ${h.live_mo ? "LIVE mở" : "MOCK — LIVE khóa chờ duyệt"}</span>
          </div>
          <div>
            <div style="font-size:11.5px;font-weight:700;color:var(--chu-mo);text-transform:uppercase;letter-spacing:.04em;margin-bottom:6px">
              Khả năng (capabilities) — nguồn: <code>GET /api/v2/hang</code></div>
            <div class="luoi-kha-nang">${Object.entries(h.capabilities).map(([k, v]) =>
              `<span class="kha-nang ${v ? "co" : "khong"}" title="${T(k)}: ${v ? "hãng hỗ trợ" : "hãng KHÔNG hỗ trợ — giao diện sẽ không mời bạn dùng"}">
                 ${v ? "✓" : "✕"} ${T(TEN_KHA_NANG[k] || k)}</span>`).join("")
              || '<span style="font-size:12px;color:var(--chu-mo)">máy chủ không trả capabilities</span>'}</div>
          </div>
          ${ds.length ? `<div style="font-size:12px;color:var(--chu-mo)">Tài khoản: ${ds.map(x =>
            `<span class="dong-tk" style="display:inline-flex;margin:2px 2px 0 0">${T(x.ten)} · <span class="tag-demo">${T(x.moi_truong)}</span> ${x.kich_hoat ? "" : "· <b>khóa</b>"}</span>`).join("")}</div>` : ""}
          ${ql ? `<button class="nut nut-nho" data-them-tk="${h.ma}">＋ Thêm tài khoản (mock)</button>` : ""}
        </div>`; }).join("")}
      </div>
      <p class="ghi-chu-nguon" style="margin-top:12px">
        <b>Trạng thái kết nối</b> ở trên suy từ <code>GET /api/v2/tai-khoan-hang</code> (có tài khoản hãng hay không, đang bật hay khóa).
        Đây <b>không</b> phải phép thử gọi API hãng: giao diện không ping hãng, và hãng đang ở chế độ MOCK.
        Muốn biết hãng có thật sự trả lời hay không thì cần API kiểm kết nối ở backend
        <span class="tag-demo">CHỜ BACKEND</span>.
        Cờ <code>live_mo</code> là <b>khóa an toàn ở backend</b> — giao diện chỉ hiển thị, không mở được.
      </p>
      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Tài khoản hãng của doanh nghiệp</h2></div>
      <div class="cuon-ngang"><table class="bang">
      <thead><tr><th>Hãng</th><th>Tên</th><th>Môi trường</th><th>Credentials</th><th>Webhook URL</th><th></th></tr></thead>
      <tbody>${tk.tai_khoan.map(t2 => `<tr><td><b>${T(t2.hang)}</b></td><td>${T(t2.ten)}</td>
        <td><span class="tag-demo">${T(t2.moi_truong)}</span></td>
        <td>${String(t2.credentials_duoi || "").trim()
            ? '<span class="huy-hieu hh-xanh">đã có credentials</span>'
            : '<span class="huy-hieu hh-xam">chưa có credentials</span>'}
          <div style="color:var(--chu-mo);font-size:11px">đã mã hoá, không xem lại được. Màn này
          <b>không hiện giá trị</b>, <b>không hiện độ dài</b>, <b>không hiện 4 ký tự cuối</b> —
          cột <code>credentials_duoi</code> chỉ được đọc để biết CÓ hay KHÔNG${t2.credentials_doi_luc ? "; đổi lần cuối " + T(t2.credentials_doi_luc) : ""}</div></td>
        <td style="font-size:11.5px"><code>/api/v2/webhook/nhan/${T(t2.webhook_ma)}</code></td>
        <td style="white-space:nowrap">${ql ? `
          <button class="nut nut-nho" data-tk="${t2.id}" data-v="${t2.kich_hoat ? "khoa" : "mo"}">${t2.kich_hoat ? "Khóa" : "Mở"}</button>
          <button class="nut nut-nho" data-rotate="${t2.id}">Đổi khóa</button>
          <button class="nut nut-nho" data-revoke="${t2.id}">Thu hồi</button>` : ""}</td></tr>`).join("")
        || '<tr><td colspan="6">Chưa có tài khoản hãng</td></tr>'}</tbody></table></div></div>`);
    document.querySelectorAll("[data-them-tk]").forEach(n => n.addEventListener("click", async () => {
      try {
        const kq = await api("/api/v2/tai-khoan-hang", "POST",
          { hang: n.dataset.themTk, ten: n.dataset.themTk.toUpperCase() + " mock", credentials: { ghi_chu: "demo" } });
        VIP.moModal("Tài khoản hãng đã tạo", `
          <p>Webhook secret chỉ hiện <b>MỘT LẦN</b> — lưu lại để cấu hình phía gửi:</p>
          <pre class="json-xem">URL:    /api/v2/webhook/nhan/${T(kq.webhook_ma)}
Secret: ${T(kq.webhook_secret_mot_lan)}</pre>`,
          `<button class="nut nut-chinh" onclick="VIP.dongModal()">Đã lưu xong</button>`);
      } catch (e) { baoLoi(e); }
    }));
    document.querySelectorAll("[data-tk]").forEach(n => n.addEventListener("click", async () => {
      try { await api(`/api/v2/tai-khoan-hang/${n.dataset.tk}/${n.dataset.v}`, "POST", {}); moMan("hang"); }
      catch (e) { baoLoi(e, "khóa/mở tài khoản hãng", "tenant.hang.quan_ly"); }
    }));
    document.querySelectorAll("[data-rotate]").forEach(n => n.addEventListener("click", () => {
      const m = VIP.moModal("Đổi credentials (rotate)", `
        <p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Giá trị cũ bị thay hẳn và không xem lại được.
        Ở bản local chỉ dùng giá trị DEMO — không nhập khóa thật.</p>
        <div class="form-nhom"><label>Khóa mới (demo)</label><input id="rt-key" value="demo-key-moi"></div>`,
        `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="rt-ok">Đổi</button>`);
      m.querySelector("#rt-ok").addEventListener("click", async () => {
        try {
          await api(`/api/v2/tai-khoan-hang/${n.dataset.rotate}/rotate`, "POST",
            { credentials: { api_key: m.querySelector("#rt-key").value } });
          VIP.dongModal(); bao("Đã đổi credentials."); moMan("hang");
        } catch (e) { baoLoi(e, "đổi credentials hãng (rotate)", "tenant.hang.quan_ly"); }
      });
    }));
    document.querySelectorAll("[data-revoke]").forEach(n => n.addEventListener("click", async () => {
      if (!confirm("Thu hồi credentials và tắt tài khoản hãng này?")) return;
      try { await api(`/api/v2/tai-khoan-hang/${n.dataset.revoke}/revoke`, "POST", {});
            bao("Đã thu hồi."); moMan("hang"); }
      catch (e) { baoLoi(e, "thu hồi credentials hãng", "tenant.hang.quan_ly"); }
    }));
  },

  /* F03 — Webhook Monitor UI.
     Hiển thị: số lần thử lại · DLQ · chi tiết sự kiện · cập nhật tracking · TRẠNG THÁI NHẬP NHẰNG.
     Trạng thái lạ (AG-03 đang thêm NEEDS_REVIEW / AMBIGUOUS cho mã J&T 110) hiện NGUYÊN VĂN
     kèm dấu ⚠ và được gom thành một khối riêng — không nuốt im lặng, không tự đoán kết quả.
     Nút Replay vẫn để BACKEND kiểm quyền (giữ nguyên hành vi cũ). */
  async webhook() {
    const kq = await api("/api/v2/webhook/su-kien");
    const n = L.nhomWebhook(kq.su_kien);
    const oTT = (t) => `${nhanWH(t)} <b>${n.theo_trang_thai[t] || 0}</b>`;

    datMan("Webhook", `
      <div class="luoi luoi-kpi">
        <div class="the kpi"><div class="nhan">Sự kiện (200 gần nhất)</div><div class="so">${n.tong}</div>
          <div class="phu">trần 200 do <code>GET /api/v2/webhook/su-kien</code> đặt</div></div>
        <div class="the kpi"><div class="nhan">DLQ — hết lượt thử</div>
          <div class="so" style="color:var(--do-vip)">${n.dlq.length}</div>
          <div class="phu">${n.dlq.length ? "cần người xử — replay hoặc sửa gốc" : "không có"}</div></div>
        <div class="the kpi"><div class="nhan">Tổng lần thử lại</div><div class="so">${n.tong_lan_thu_lai}</div>
          <div class="phu">${n.so_su_kien_da_thu_lai} sự kiện từng thử lại${n.thu_lai_nhieu_nhat
            ? ` · nhiều nhất <b>${n.thu_lai_nhieu_nhat.so_lan_thu}</b> lần (#${n.thu_lai_nhieu_nhat.id})` : ""}</div></div>
        <div class="the kpi"><div class="nhan">Trạng thái nhập nhằng</div>
          <div class="so" style="color:var(--vang)">${n.nhap_nhang.length + n.trang_thai_la.length}</div>
          <div class="phu">${n.nhap_nhang.length} nhập nhằng · ${n.trang_thai_la.length} trạng thái lạ khác</div></div>
      </div>

      ${(n.nhap_nhang.length + n.trang_thai_la.length) ? `
      <div class="the" style="margin-top:16px;border-color:#F5D08A"><div class="the-dau" style="background:var(--vang-nhat)">
        <h2>⚠ Trạng thái nhập nhằng / giao diện chưa biết</h2></div>
        <div class="the-than">
          <p style="margin-top:0;font-size:12.5px">Những sự kiện dưới đây mang trạng thái <b>không</b> nằm trong
            hợp đồng §12 (<code>moi · dang_xu_ly · xong · cho_thu_lai · dlq · khong_khop</code>).
            Giao diện <b>hiện nguyên văn</b> và không tự quy ra thành công/thất bại —
            ánh xạ trạng thái là việc của backend (AG-03 <code>normalizeTrackingStatus</code>).</p>
          <div class="cuon-ngang"><table class="bang bang-hep"><thead><tr>
            <th>#</th><th>Event ID</th><th>Hãng</th><th>Trạng thái nguyên văn</th><th>Lần thử</th></tr></thead>
          <tbody>${n.nhap_nhang.concat(n.trang_thai_la).map(s => `<tr>
            <td>${s.id}</td><td><code>${T(s.event_id)}</code></td><td>${T(s.hang)}</td>
            <td>${nhanWH(s.trang_thai)}</td><td style="text-align:center">${s.so_lan_thu}</td></tr>`).join("")}</tbody></table></div>
        </div></div>` : ""}

      ${n.dlq.length ? `
      <div class="the" style="margin-top:16px;border-color:#F5B5B5"><div class="the-dau" style="background:var(--do-nhat)">
        <h2>☠ Dead Letter Queue — ${n.dlq.length} sự kiện</h2>
        <div class="phai"><span class="huy-hieu hh-do">hết lượt thử tự động</span></div></div>
        <div class="the-than" style="padding-bottom:0"><p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">
          Sự kiện vào DLQ là sự kiện backend đã thử hết số lần cho phép mà vẫn lỗi. Replay là
          <b>quyết định của người</b>; quyền replay do backend kiểm (<code>tenant.webhook.replay</code>).</p></div>
        <div class="cuon-ngang"><table class="bang"><thead><tr>
          <th>#</th><th>Event ID</th><th>Hãng</th><th>Nhận lúc</th><th>Lần thử</th><th>Lỗi cuối</th><th></th></tr></thead>
        <tbody>${n.dlq.map(s => `<tr><td>${s.id}</td><td><code>${T(s.event_id)}</code></td><td>${T(s.hang)}</td>
          <td style="white-space:nowrap">${T(s.nhan_luc)}</td><td style="text-align:center"><b>${s.so_lan_thu}</b></td>
          <td style="font-size:11.5px;color:var(--do-dam);max-width:260px">${T(s.loi_cuoi || "(máy chủ không trả lỗi cuối)")}</td>
          <td style="white-space:nowrap"><button class="nut nut-nho" data-chi-tiet="${s.id}">Chi tiết</button>
            ${duoc("tenant.webhook.replay") ? `<button class="nut nut-nho" data-replay="${s.id}">Replay</button>` : ""}</td></tr>`).join("")}
        </tbody></table></div></div>` : ""}

      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Toàn bộ sự kiện của doanh nghiệp</h2>
        <div class="phai">
          <select id="w-loc" class="o-nho"><option value="">Mọi trạng thái</option>
            ${Object.keys(n.theo_trang_thai).map(t => `<option value="${T(t)}">${T(t)} (${n.theo_trang_thai[t]})</option>`).join("")}</select>
          <button class="nut nut-nho" id="w-moi">↻ Làm mới</button></div></div>
      <div class="the-than" style="padding-bottom:0"><div class="chu-giai" style="margin:0">
        ${Object.keys(L.TT_WH).map(t => oTT(t)).join(" · ")}</div></div>
      <div class="cuon-ngang"><table class="bang">
      <thead><tr><th>#</th><th>Event ID</th><th>Hãng</th><th>Nhận lúc</th><th>Trạng thái</th>
        <th>Lần thử</th><th>Lỗi cuối</th><th></th></tr></thead>
      <tbody id="w-bang">${kq.su_kien.map(s => dongWebhook(s)).join("")
        || '<tr><td colspan="8"><div class="trang-thai-rong"><div class="to">🔔</div>Chưa có sự kiện</div></td></tr>'}</tbody></table></div>
      <p class="ghi-chu-nguon" style="padding:0 18px 14px">
        <b>Nguồn:</b> <code>GET /api/v2/webhook/su-kien</code> — 200 sự kiện gần nhất, tenant resolve từ
        <code>carrier_account</code> (§12: <b>không bao giờ</b> từ payload).
        <b>Chống trùng</b> do CSDL cưỡng chế bằng <code>UNIQUE(carrier_account_id, event_id)</code>.
        <b>Chưa có:</b> payload thô, headers, đơn/mã vận đơn liên quan, lịch sử từng lần thử —
        ${nhanChoBackend("/api/v2/webhook/su-kien/<id>")}
      </p></div>

      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Cập nhật tracking từ webhook</h2></div>
        <div class="the-than">${hopChoBackend("/api/v2/webhook/su-kien/<id>")}
          <p class="ghi-chu-nguon">Màn này <b>chưa nối được</b> sự kiện webhook với đơn mà nó cập nhật:
            danh sách API không trả <code>don_id</code> hay <code>ma_van_don</code>. Trong khi chờ, xem
            cột <b>Giao vận</b> và tab <b>Dòng thời gian</b> ở màn <b>Đơn hàng</b> — các mốc có
            nguồn <code>webhook:&lt;id tài khoản&gt;</code> chính là cập nhật do hãng đẩy về.</p>
        </div></div>`);

    const g = (id) => document.getElementById(id);
    g("w-moi").addEventListener("click", () => moMan("webhook"));
    g("w-loc").addEventListener("change", () => {
      const v = g("w-loc").value;
      const ds = v ? kq.su_kien.filter(s => s.trang_thai === v) : kq.su_kien;
      g("w-bang").innerHTML = ds.map(s => dongWebhook(s)).join("")
        || `<tr><td colspan="8"><div class="trang-thai-rong">Không sự kiện nào ở trạng thái <code>${T(v)}</code></div></td></tr>`;
      gocWebhook(kq.su_kien);
    });
    gocWebhook(kq.su_kien);
  },

  async "thanh-vien"() {
    const kq = await api("/api/v2/memberships");
    const ql = duoc("tenant.membership.quan_ly");
    datMan("Thành viên", `
      ${ql ? `<div class="hang-cong-cu"><div class="day"><button class="nut nut-chinh" id="tv-them">➕ Mời thành viên</button></div></div>` : ""}
      <p style="font-size:12.5px;color:var(--chu-mo)">Một người có thể thuộc nhiều doanh nghiệp. Vai trò ở đây chỉ áp dụng cho <b>${T(TOI.tenant.ten)}</b>.</p>
      <div class="the"><div class="cuon-ngang"><table class="bang">
      <thead><tr><th>Tên đăng nhập</th><th>Họ tên</th><th>Vai trò</th><th>Trạng thái</th><th></th></tr></thead>
      <tbody>${kq.memberships.map(x => `<tr><td><b>${T(x.ten_dang_nhap)}</b></td><td>${T(x.ho_ten || "")}</td>
        <td>${T(x.role)}</td>
        <td>${x.trang_thai === "hoat_dong" ? '<span class="huy-hieu hh-xanh">Hoạt động</span>' : '<span class="huy-hieu hh-do">Vô hiệu</span>'}
            ${x.tt_user === "khoa" ? ' <span class="huy-hieu hh-do">TK khóa</span>' : ""}</td>
        <td style="white-space:nowrap">${ql && x.role !== "TENANT_OWNER" && x.user_id !== TOI.id ? `
          <button class="nut nut-nho" data-mem="${x.id}" data-tt="${x.trang_thai === "hoat_dong" ? "vo_hieu" : "hoat_dong"}">${x.trang_thai === "hoat_dong" ? "Vô hiệu" : "Kích hoạt"}</button>
          <button class="nut nut-nho" data-role="${x.id}">Đổi vai trò</button>
          <button class="nut nut-nho" data-xoa="${x.id}">Xóa</button>` : ""}</td></tr>`).join("")}</tbody></table></div></div>`);
    document.querySelectorAll("[data-mem]").forEach(n => n.addEventListener("click", async () => {
      try { await api(`/api/v2/memberships/${n.dataset.mem}`, "PUT", { trang_thai: n.dataset.tt });
            bao("Xong."); moMan("thanh-vien"); } catch (e) { baoLoi(e); }
    }));
    document.querySelectorAll("[data-xoa]").forEach(n => n.addEventListener("click", async () => {
      if (!confirm("Xóa thành viên khỏi doanh nghiệp này?")) return;
      try { await api(`/api/v2/memberships/${n.dataset.xoa}`, "DELETE"); bao("Đã xóa."); moMan("thanh-vien"); }
      catch (e) { baoLoi(e); }
    }));
    document.querySelectorAll("[data-role]").forEach(n => n.addEventListener("click", () => {
      const m = VIP.moModal("Đổi vai trò", `
        <div class="form-nhom"><label>Vai trò mới</label><select id="vr-moi">
          ${(TOI.vai_tro === "TENANT_OWNER" ? ["TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"]
                                            : ["TENANT_STAFF", "TENANT_VIEWER"]).map(r => `<option>${r}</option>`).join("")}
        </select></div>`,
        `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="vr-ok">Đổi</button>`);
      m.querySelector("#vr-ok").addEventListener("click", async () => {
        try { await api(`/api/v2/memberships/${n.dataset.role}`, "PUT", { role: m.querySelector("#vr-moi").value });
              VIP.dongModal(); bao("Đã đổi vai trò."); moMan("thanh-vien"); }
        catch (e) { baoLoi(e); }
      });
    }));
    const nt = document.getElementById("tv-them");
    if (nt) nt.addEventListener("click", () => {
      const m = VIP.moModal("Mời thành viên", `
        <p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Nếu tên đăng nhập đã tồn tại, người đó được
        thêm vào doanh nghiệp này (giữ nguyên tài khoản cũ). Nếu chưa có, cần đặt mật khẩu ban đầu.</p>
        <div class="form-nhom"><label>Tên đăng nhập</label><input id="tv-dn"></div>
        <div class="form-nhom"><label>Họ tên (nếu tạo mới)</label><input id="tv-ht"></div>
        <div class="form-nhom"><label>Mật khẩu ban đầu (nếu tạo mới, ≥8)</label><input id="tv-mk" type="password"></div>
        <div class="form-nhom"><label>Vai trò</label><select id="tv-vt">
          ${(TOI.vai_tro === "TENANT_OWNER" ? ["TENANT_ADMIN", "TENANT_STAFF", "TENANT_VIEWER"]
                                            : ["TENANT_STAFF", "TENANT_VIEWER"]).map(r => `<option>${r}</option>`).join("")}
        </select></div>`,
        `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="tv-luu">Thêm</button>`);
      m.querySelector("#tv-luu").addEventListener("click", async () => {
        try {
          await api("/api/v2/memberships", "POST", {
            ten_dang_nhap: m.querySelector("#tv-dn").value.trim(), ho_ten: m.querySelector("#tv-ht").value,
            mat_khau: m.querySelector("#tv-mk").value, role: m.querySelector("#tv-vt").value });
          VIP.dongModal(); bao("Đã thêm thành viên."); moMan("thanh-vien");
        } catch (e) { baoLoi(e, "mời thành viên", "tenant.membership.quan_ly"); }
      });
    });
  },

  async goi() {
    const b = await api("/api/v2/billing");
    datMan("Gói & usage", `
      <div class="luoi luoi-kpi">
        <div class="the kpi"><div class="nhan">Gói hiện tại</div><div class="so" style="font-size:18px">${T(b.goi.ten)}</div>
          <div class="phu">${tien(b.goi.gia_thang)}/tháng (chưa thu tiền thật)</div></div>
        <div class="the kpi"><div class="nhan">Đơn tháng ${b.usage.thang}</div><div class="so">${b.usage.so_don}/${b.goi.han_muc_don_thang}</div></div>
        <div class="the kpi"><div class="nhan">Lượt AI</div><div class="so">${b.usage.so_ai}/${b.goi.han_muc_ai_thang}</div></div>
        <div class="the kpi"><div class="nhan">Hạn mức khác</div>
          <div class="phu" style="margin-top:8px">${b.goi.so_nhan_vien} thành viên · ${b.goi.so_tai_khoan_hang} kết nối hãng</div></div>
      </div>
      <p style="font-size:12.5px;color:var(--chu-mo)">Usage đo từ backend. Nâng/hạ gói do quản trị nền tảng thực hiện. Thanh toán thật chưa bật.</p>`);
  },

  async "nhat-ky"() {
    datMan("Nhật ký", bangAudit((await api("/api/v2/audit")).audit));
  },

  async "cai-dat"() {
    datMan("Cài đặt", `
      <div class="the" style="max-width:480px"><div class="the-dau"><h2>Đổi mật khẩu</h2></div><div class="the-than">
        <div class="form-nhom"><label>Mật khẩu cũ</label><input id="c-cu" type="password"></div>
        <div class="form-nhom"><label>Mật khẩu mới (≥8 ký tự)</label><input id="c-moi" type="password"></div>
        <button class="nut nut-chinh" id="c-doi">Đổi mật khẩu</button>
        <p style="font-size:12px;color:var(--chu-mo)">Đổi xong, mọi phiên đăng nhập khác bị thu hồi.</p>
      </div></div>
      <div class="the" style="max-width:480px;margin-top:16px"><div class="the-than">
        <button class="nut" id="c-thu-hoi">Thu hồi các phiên đăng nhập khác</button>
      </div></div>
      <div class="the" style="max-width:480px;margin-top:16px"><div class="the-dau"><h2>Quyền của bạn</h2></div>
      <div class="the-than"><p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Vai trò <b>${T(TOI.vai_tro)}</b> — backend kiểm từng quyền:</p>
      <div style="font-size:12px;line-height:1.9">${(TOI.quyen || []).map(q => `<code>${T(q)}</code>`).join(" · ") || "—"}</div></div></div>`);
    document.getElementById("c-doi").addEventListener("click", async () => {
      try {
        await api("/api/v2/auth/doi-mat-khau", "POST", {
          mat_khau_cu: document.getElementById("c-cu").value,
          mat_khau_moi: document.getElementById("c-moi").value });
        bao("Đã đổi mật khẩu — các phiên khác bị thu hồi.");
      } catch (e) { baoLoi(e); }
    });
    document.getElementById("c-thu-hoi").addEventListener("click", async () => {
      try { await api("/api/v2/auth/thu-hoi-phien", "POST", {}); bao("Đã thu hồi các phiên khác."); }
      catch (e) { baoLoi(e, "thu hồi phiên đăng nhập khác"); }
    });
  },

  /* ===== màn platform ===== */
  async tenants() {
    const [ts, goi] = await Promise.all([api("/api/v2/platform/tenants"), api("/api/v2/platform/goi")]);
    datMan("Tenants", `
      ${duoc("platform.tenant.tao") ? `<div class="hang-cong-cu"><div class="day"><button class="nut nut-chinh" id="t-them">➕ Tạo tenant</button></div></div>` : ""}
      <div class="the"><div class="cuon-ngang"><table class="bang">
      <thead><tr><th>#</th><th>Mã</th><th>Tên</th><th>Gói</th><th>Thành viên</th><th>Trạng thái</th><th></th></tr></thead>
      <tbody>${ts.tenants.map(t2 => `<tr><td>${t2.id}</td><td><code>${T(t2.code || "")}</code></td><td><b>${T(t2.ten)}</b></td>
        <td>${T(t2.ten_goi)}</td><td style="text-align:center">${t2.so_thanh_vien}</td>
        <td>${t2.trang_thai === "hoat_dong" ? '<span class="huy-hieu hh-xanh">Hoạt động</span>' : '<span class="huy-hieu hh-do">Khóa</span>'}</td>
        <td style="white-space:nowrap">${duoc("platform.tenant.khoa") ? `<button class="nut nut-nho" data-t="${t2.id}" data-v="${t2.trang_thai === "hoat_dong" ? "khoa" : "mo"}">${t2.trang_thai === "hoat_dong" ? "Khóa" : "Mở"}</button>` : ""}
        ${duoc("platform.goi.doi") ? `<select class="o-nho" data-goi="${t2.id}"><option value="">Đổi gói…</option>
          ${goi.goi.map(g => `<option value="${g.id}">${T(g.ten)}</option>`).join("")}</select>` : ""}</td></tr>`).join("")}</tbody></table></div></div>`);
    document.querySelectorAll("[data-t]").forEach(n => n.addEventListener("click", async () => {
      try { await api(`/api/v2/platform/tenants/${n.dataset.t}/${n.dataset.v}`, "POST", {}); moMan("tenants"); }
      catch (e) { baoLoi(e, "khóa/mở tenant", "platform.tenant.khoa"); }
    }));
    document.querySelectorAll("[data-goi]").forEach(n => n.addEventListener("change", async () => {
      if (!n.value) return;
      try { await api(`/api/v2/platform/tenants/${n.dataset.goi}/goi`, "POST", { goi_id: n.value });
            bao("Đã đổi gói."); moMan("tenants"); } catch (e) { baoLoi(e); }
    }));
    const nt = document.getElementById("t-them");
    if (nt) nt.addEventListener("click", () => {
      const m = VIP.moModal("Tạo tenant mới", `
        <div class="form-nhom"><label>Tên doanh nghiệp/shop</label><input id="t-ten"></div>
        <div class="form-nhom"><label>Mã (code, để trống sẽ tự sinh)</label><input id="t-code"></div>
        <div class="form-nhom"><label>Gói</label><select id="t-goi">${goi.goi.map(g => `<option value="${g.id}">${T(g.ten)}</option>`).join("")}</select></div>
        <div class="form-nhom"><label>Tên đăng nhập chủ tenant</label><input id="t-dn"></div>
        <div class="form-nhom"><label>Mật khẩu chủ tenant (≥8)</label><input id="t-mk" type="password"></div>`,
        `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="t-luu">Tạo</button>`);
      m.querySelector("#t-luu").addEventListener("click", async () => {
        try {
          const d = { ten: m.querySelector("#t-ten").value, goi_id: m.querySelector("#t-goi").value,
                      owner_ten_dang_nhap: m.querySelector("#t-dn").value.trim(),
                      owner_mat_khau: m.querySelector("#t-mk").value };
          const code = m.querySelector("#t-code").value.trim();
          if (code) d.code = code;
          await api("/api/v2/platform/tenants", "POST", d);
          VIP.dongModal(); bao("Đã tạo tenant."); moMan("tenants");
        } catch (e) { baoLoi(e); }
      });
    });
  },

  async "vai-tro"() {
    const kq = await api("/api/v2/platform/vai-tro");
    const theoRole = {};
    kq.role_permissions.forEach(rp => (theoRole[rp.role_ma] = theoRole[rp.role_ma] || []).push(rp.perm_ma));
    datMan("Vai trò & quyền", `
      <p style="font-size:12.5px;color:var(--chu-mo)">Ma trận này nằm trong CSDL (<code>role_permissions</code>) — backend tra bảng ở từng endpoint, không hard-code ở giao diện.</p>
      <div class="the"><div class="cuon-ngang"><table class="bang">
      <thead><tr><th>Vai trò</th><th>Phạm vi</th><th>Số quyền</th><th>Quyền</th></tr></thead>
      <tbody>${kq.roles.map(r => `<tr><td><b>${T(r.ma)}</b><br><span style="color:var(--chu-mo);font-size:12px">${T(r.ten)}</span></td>
        <td><span class="huy-hieu ${r.pham_vi === "platform" ? "hh-do" : "hh-xanh-duong"}">${T(r.pham_vi)}</span></td>
        <td style="text-align:center">${(theoRole[r.ma] || []).length}</td>
        <td style="font-size:11.5px">${(theoRole[r.ma] || []).map(p => `<code>${T(p)}</code>`).join(" ") || "—"}</td></tr>`).join("")}</tbody></table></div></div>`);
  },

  async "audit-nen-tang"() {
    datMan("Audit nền tảng", bangAudit((await api("/api/v2/platform/audit")).audit));
  },
};

/* ===== phụ trợ =====
   Bảng trạng thái và luật nhãn đã chuyển hẳn sang admin/logic.js (bộ thử Node kiểm trực
   tiếp ở đó). Ở đây chỉ còn lớp dựng HTML mỏng. */
const nhanTT    = (t) => hh(L.nhanTT(t));
const nhanBatch = (t) => hh(L.nhanBatch(t));
const nhanDong  = (t) => hh(L.nhanDong(t));
const nhanGiao  = (t) => (t ? hh(L.nhanGiao(t)) : "—");
const nhanWH    = (t) => hh(L.nhanWebhook(t));
const lopDongBang = (t) => L.lopDongBang(t);

/* Tên tiếng Việt cho capabilities của hãng (khóa do backend/adapter đặt).
   Khóa lạ thì hiện nguyên văn khóa — để thấy ngay khi adapter thêm khả năng mới. */
const TEN_KHA_NANG = {
  createOrder: "Tạo đơn", cancelOrder: "Hủy đơn", getOrder: "Tra đơn",
  trackOrder: "Theo dõi hành trình", getShippingFee: "Tính cước",
  getShippingLabel: "In nhãn vận đơn", webhook: "Nhận webhook",
};

/* ===== F03 — phụ trợ webhook ===== */
function dongWebhook(s) {
  const n = L.nhanWebhook(s.trang_thai);
  return `<tr class="${n.nhap_nhang ? "dong-can-xem" : s.trang_thai === "dlq" ? "dong-loi" : ""}">
    <td>${s.id}</td><td><code>${T(s.event_id)}</code></td><td>${T(s.hang)}${s.ten_tk
      ? `<div class="ghi-chu-nguon">${T(s.ten_tk)}</div>` : ""}</td>
    <td style="white-space:nowrap">${T(s.nhan_luc)}</td>
    <td>${hh(n)}</td>
    <td style="text-align:center">${s.so_lan_thu > 0 ? `<b title="số lần backend đã thử xử lý lại">${s.so_lan_thu}</b>` : "0"}</td>
    <td style="font-size:11.5px;max-width:220px">${T(s.loi_cuoi || "")}</td>
    <td style="white-space:nowrap"><button class="nut nut-nho" data-chi-tiet="${s.id}">Chi tiết</button>
      ${duoc("tenant.webhook.replay") && ["dlq", "khong_khop"].includes(s.trang_thai)
        ? `<button class="nut nut-nho" data-replay="${s.id}">Replay</button>` : ""}</td></tr>`;
}

function gocWebhook(ds) {
  document.querySelectorAll("[data-replay]").forEach(n => {
    if (n.dataset.goc) return; n.dataset.goc = "1";
    n.addEventListener("click", async () => {
      try {
        await api(`/api/v2/webhook/su-kien/${n.dataset.replay}/replay`, "POST", {});
        bao("Đã nạp lại (có audit). Kết quả do backend xử — xem lại trạng thái sau khi làm mới.");
        setTimeout(() => moMan("webhook"), 500);
      } catch (e) { baoLoi(e, "replay sự kiện webhook", "tenant.webhook.replay"); }
    });
  });
  document.querySelectorAll("[data-chi-tiet]").forEach(n => {
    if (n.dataset.goc) return; n.dataset.goc = "1";
    n.addEventListener("click", () =>
      chiTietSuKienWebhook((ds || []).find(x => x.id === +n.dataset.chiTiet)));
  });
}

/* Chi tiết sự kiện: API chi tiết CHƯA CÓ. Thay vì bỏ trống, hiện đủ những trường danh sách
   ĐÃ trả về, rồi nói thẳng cái gì còn thiếu và endpoint nào cần. Không bịa payload. */
function chiTietSuKienWebhook(s) {
  if (!s) { bao("Không tìm thấy sự kiện trong danh sách đã tải.", "loi"); return; }
  const n = L.nhanWebhook(s.trang_thai);
  const m = VIP.moModal(`Sự kiện webhook #${s.id}`, `
    <table class="bang"><tbody>
      <tr><td style="width:150px;color:var(--chu-mo)">Event ID</td><td><code>${T(s.event_id)}</code>
        <div class="ghi-chu-nguon">khóa chống trùng cùng với tài khoản hãng —
          <code>UNIQUE(carrier_account_id, event_id)</code> do CSDL cưỡng chế</div></td></tr>
      <tr><td style="color:var(--chu-mo)">Hãng / tài khoản</td><td><b>${T(s.hang)}</b>${s.ten_tk ? " · " + T(s.ten_tk) : ""}</td></tr>
      <tr><td style="color:var(--chu-mo)">Nhận lúc</td><td>${T(s.nhan_luc)}</td></tr>
      <tr><td style="color:var(--chu-mo)">Trạng thái</td><td>${hh(n)}
        <div class="ghi-chu-nguon">${T(n.mo_ta || "")}</div></td></tr>
      <tr><td style="color:var(--chu-mo)">Số lần thử</td><td><b>${s.so_lan_thu}</b>
        ${s.trang_thai === "dlq" ? ' — đã hết lượt thử tự động, chỉ còn replay bằng tay' : ""}</td></tr>
      <tr><td style="color:var(--chu-mo)">Lỗi cuối</td><td>${T(s.loi_cuoi || "—")}</td></tr>
    </tbody></table>
    ${n.nhap_nhang ? `<div class="hop-loi" style="margin-top:12px">
      <b>Trạng thái nhập nhằng.</b> Backend đánh dấu sự kiện này cần người xem lại
      (ví dụ mã hãng J&amp;T 110 ánh xạ được ra nhiều trạng thái chuẩn). Giao diện
      <b>không</b> tự chọn giúp — hiện nguyên văn <code>${T(s.trang_thai)}</code>.</div>` : ""}
    ${hopChoBackend("/api/v2/webhook/su-kien/<id>")}`,
    `<button class="nut nut-chinh" onclick="VIP.dongModal()">Đóng</button>`);
  return m;
}

function bangAudit(ds) {
  return `<div class="the"><div class="cuon-ngang"><table class="bang">
    <thead><tr><th>Lúc</th><th>Actor</th><th>Hành động</th><th>Resource</th><th>Kết quả</th><th>Chi tiết</th></tr></thead>
    <tbody>${ds.map(a => `<tr><td style="white-space:nowrap">${T(a.luc)}</td><td>${a.user_id ?? "—"}</td>
      <td><b>${T(a.hanh_dong)}</b></td><td>${T(a.resource_type || "")}${a.resource_id ? ":" + T(a.resource_id) : ""}</td>
      <td><span class="huy-hieu ${a.ket_qua === "thanh_cong" ? "hh-xanh" : "hh-do"}">${T(a.ket_qua || "")}</span></td>
      <td style="font-size:12px">${T(a.chi_tiet || "")}</td></tr>`).join("") || '<tr><td colspan="6">Trống</td></tr>'}</tbody></table></div></div>`;
}

/* Form tạo/sửa đơn. Kiểm dữ liệu ở L.kiemTraDon (logic thuần, bộ thử Node phủ) rồi mới gọi
   API — nhưng backend VẪN là chỗ chốt, kiểm ở đây chỉ để người dùng khỏi mất một lượt gọi. */
function formDon(don, sauKhiLuu) {
  const f = don || {};
  const o = (k, nhan, kieu, bat_buoc, rong) => `
    <div class="form-nhom${rong ? " o-rong" : ""}" data-o="${k}">
      <label for="f-${k}">${nhan}${bat_buoc ? ' <span class="bat-buoc">*</span>' : ""}</label>
      <input id="f-${k}" data-truong="${k}" ${kieu ? `type="${kieu}"` : ""} value="${T(f[k] == null ? (k === "cod" ? 0 : "") : f[k])}">
      <div class="loi-nhan"></div></div>`;
  const m = VIP.moModal(don ? "Sửa đơn " + T(f.ma_don || "") : "Tạo đơn mới", `
    <div class="hop-nguon" style="margin-bottom:12px">Đơn tạo ở đây là
      ${nhanCheDo(L.CHE_DO.LOCAL)} — lưu vào CSDL local, <b>chưa</b> gửi hãng vận chuyển.
      Gửi hãng là bước riêng ở chi tiết đơn.</div>
    <div class="form-hang">
      ${o("nguoi_gui_ten", "Người gửi", "", true)}
      ${o("nguoi_gui_sdt", "SĐT gửi", "", true)}
      ${o("nguoi_gui_dia_chi", "Địa chỉ gửi", "", true, true)}
      ${o("nguoi_nhan_ten", "Người nhận", "", true)}
      ${o("nguoi_nhan_sdt", "SĐT nhận", "", true)}
      ${o("nguoi_nhan_dia_chi", "Địa chỉ nhận", "", true, true)}
      ${o("hang_hoa", "Hàng hóa", "", true)}
      ${o("khoi_luong_gram", "Cân nặng (gram)", "number", true)}
      ${o("cod", "COD (₫)", "number", false)}
      ${o("ghi_chu", "Ghi chú", "", false)}
    </div>
    <div id="f-tong-loi"></div>`,
    `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="f-luu">💾 Lưu</button>`);
  const docForm = () => {
    const d = {};
    m.querySelectorAll("[data-truong]").forEach(i2 => d[i2.dataset.truong] = i2.value);
    return d;
  };
  const hienLoi = (loi) => {
    m.querySelectorAll("[data-o]").forEach(n => { n.classList.remove("co-loi"); n.querySelector(".loi-nhan").textContent = ""; });
    loi.forEach(e => {
      const n = m.querySelector(`[data-o="${e.truong}"]`);
      if (n) { n.classList.add("co-loi"); n.querySelector(".loi-nhan").textContent = e.thong_diep; }
    });
    m.querySelector("#f-tong-loi").innerHTML = loi.length
      ? `<div class="hop-loi">Còn <b>${loi.length}</b> chỗ phải sửa trước khi lưu.</div>` : "";
  };
  m.querySelector("#f-luu").addEventListener("click", async () => {
    const tho = docForm();
    const loi = L.kiemTraDon(tho);
    hienLoi(loi);
    if (loi.length) { bao("Dữ liệu chưa hợp lệ — xem các ô bị đánh dấu.", "loi"); return; }
    const d = Object.assign({}, tho, {
      khoi_luong_gram: +tho.khoi_luong_gram, cod: +tho.cod || 0,
    });
    try {
      if (don) await api(`/api/v2/don/${don.id}`, "PUT", d);
      else await api("/api/v2/don", "POST", d,
        { "Idempotency-Key": "ui-" + Date.now() + "-" + Math.random().toString(36).slice(2) });
      VIP.dongModal(); bao(don ? "Đã sửa đơn." : "Đã tạo đơn nháp."); sauKhiLuu();
    } catch (e) { baoLoi(e, don ? "sửa đơn" : "tạo đơn", "tenant.don.ghi"); }
  });
}

/* ===== F01 — Chi tiết đơn: thông tin · dòng thời gian · lịch sử · phiếu in · hành động =====
   Timeline dựng từ `don_lich_su` do GET /api/v2/don/<id> trả về (§11 — mọi thay đổi trạng thái
   PHẢI có một dòng ở đó), nên là dữ liệu THẬT. L.dungTimeline không bịa mốc nào: trạng thái
   giao không xuất hiện trong lịch sử thì nút cuối gắn cờ "suy ra", không có giờ. */
async function chiTietDon(id, taiKhoanHang, dsHang, sauKhiDoi) {
  const kq = await api(`/api/v2/don/${id}`);
  const d = kq.don;
  const duyet = duoc("tenant.don.duyet");
  const tk = (taiKhoanHang || []).find(x => x.id === d.carrier_account_id) || null;
  const hang_theo_ma = {}; (dsHang || []).forEach(h => hang_theo_ma[h.ma] = h);
  const hang = tk ? hang_theo_ma[tk.hang] : null;
  const cd = L.cheDoDon(d, tk, hang);
  const tl = L.dungTimeline(d, kq.lich_su);
  const chon = L.chonTaiKhoanGui(taiKhoanHang || [], dsHang || []);

  const m = VIP.moModal(`Đơn ${T(d.ma_don)}`, `
    <div class="hang-cheo">${nhanTT(d.trang_thai)} ${nhanGiao(d.trang_thai_giao)} ${nhanCheDo(cd)}
      ${d.can_doi_soat_ket_qua ? '<span class="huy-hieu hh-vang" title="hãng timeout: ba kết cục không gộp — ok / từ chối / KHÔNG BIẾT. Đây là không biết.">timeout — cần đối soát với hãng</span>' : ""}</div>

    <div class="tab-day" id="ct-tab">
      <button class="tab-nut hien-tai" data-tab="tt">Thông tin</button>
      <button class="tab-nut" data-tab="tl">Dòng thời gian (${tl.nut.length})</button>
      <button class="tab-nut" data-tab="ls">Lịch sử (${kq.lich_su.length})</button>
      <button class="tab-nut" data-tab="in">Phiếu in</button>
    </div>

    <div data-vung="tt">
      <table class="bang"><tbody>
        <tr><td style="width:150px;color:var(--chu-mo)">Mã vận đơn</td><td>${T(d.ma_van_don || "—")}
          ${d.ma_van_don ? `<span class="ghi-chu-nguon">(${T(cd.nhan)} — ${T(cd.giai_thich)})</span>` : ""}</td></tr>
        <tr><td style="color:var(--chu-mo)">Hãng / tài khoản</td><td>${tk
          ? `<b>${T(hang ? hang.ten : tk.hang)}</b> <code>${T(tk.hang)}</code><br>
             tài khoản <b>${T(tk.ten)}</b> (#${tk.id}) · môi trường <span class="tag-demo">${T(tk.moi_truong)}</span>
             ${tk.kich_hoat ? "" : ' · <b style="color:var(--do-dam)">đang khóa</b>'}`
          : d.carrier_account_id ? `tài khoản #${d.carrier_account_id} — thiếu quyền <code>tenant.hang.xem</code> để đọc tên`
                                 : "chưa gán — đơn chưa gửi hãng nào"}</td></tr>
        <tr><td style="color:var(--chu-mo)">Người gửi</td><td>${T(d.nguoi_gui_ten)} — ${T(d.nguoi_gui_sdt)}<br>${T(d.nguoi_gui_dia_chi)}</td></tr>
        <tr><td style="color:var(--chu-mo)">Người nhận</td><td>${T(d.nguoi_nhan_ten)} — ${T(d.nguoi_nhan_sdt)}<br>${T(d.nguoi_nhan_dia_chi)}</td></tr>
        <tr><td style="color:var(--chu-mo)">Hàng / COD / Phí</td><td>${T(d.hang_hoa)} (${T(d.khoi_luong_gram)}g) / ${tien(d.cod)} /
          ${d.phi_van_chuyen != null ? tien(d.phi_van_chuyen) : '<span style="color:var(--chu-mo)">chưa có — hãng chưa trả phí</span>'}</td></tr>
        <tr><td style="color:var(--chu-mo)">Ghi chú</td><td>${T(d.ghi_chu || "—")}</td></tr>
        <tr><td style="color:var(--chu-mo)">Tạo lúc</td><td>${T(d.tao_luc || "—")}</td></tr>
      </tbody></table>
      ${d.trang_thai === "da_duyet" && duyet ? `
        <h3 style="font-size:13px;margin-bottom:6px">Gửi hãng — chọn hãng và tài khoản</h3>
        ${chon.dung_duoc.length ? `
          <div class="form-nhom"><label for="ct-tk">Tài khoản hãng dùng để gửi</label>
            <select id="ct-tk">${chon.dung_duoc.map(x =>
              `<option value="${x.id}">${T(x.hang_ten)} (${T(x.hang)}) · ${T(x.ten)} · ${T(x.moi_truong)} · ${T(x.che_do.nhan)}</option>`).join("")}</select>
            <div class="ghi-chu-nguon">Danh sách chỉ gồm tài khoản <b>đang bật</b> và hãng có khả năng
              <code>createOrder</code>. Gửi đi sẽ chạy qua <b>adapter MOCK</b> — không tạo đơn thật.</div></div>`
          : `<div class="hop-loi">Không có tài khoản hãng nào dùng được để gửi
              ${chon.loai_ra.length ? `(${chon.loai_ra.length} tài khoản bị loại: ${chon.loai_ra.map(x => T(x.ten) + " — " + T(x.ly_do_loai)).join("; ")})` : ""}.</div>`}
        ${chon.loai_ra.length && chon.dung_duoc.length ? `<p class="ghi-chu-nguon">Bị loại khỏi danh sách:
          ${chon.loai_ra.map(x => `<b>${T(x.ten)}</b> — ${T(x.ly_do_loai)}`).join(" · ")}</p>` : ""}` : ""}
    </div>

    <div data-vung="tl" hidden>
      ${tl.nut.length ? `<ol class="dong-thoi-gian">${tl.nut.map(n => `
        <li class="${n.suy_ra ? "suy-ra" : "nguon-" + T(n.nguon_loai)}">
          <div class="luc">${n.luc ? T(n.luc) : '<i>không có mốc giờ</i>'}</div>
          <div class="noi">${T(n.noi_dung)}</div>
          <div class="nguon">${T(n.nguon_ten)}${n.suy_ra
            ? ' — <b>suy ra từ trường <code>trang_thai_giao</code>, KHÔNG phải một sự kiện có giờ</b>' : ""}</div>
        </li>`).join("")}</ol>`
        : '<div class="trang-thai-rong">Chưa có mốc nào trong <code>don_lich_su</code></div>'}
      <p class="ghi-chu-nguon"><b>Nguồn:</b> <code>don_lich_su</code> qua <code>GET /api/v2/don/${id}</code> —
        dữ liệu thật, không suy diễn. <b>Phạm vi:</b> ${T(tl.ghi_chu_pham_vi)}</p>
    </div>

    <div data-vung="ls" hidden>
      <div class="cuon-ngang"><table class="bang bang-hep"><thead><tr><th>Lúc</th><th>Nguồn</th><th>Nội dung</th></tr></thead>
      <tbody>${kq.lich_su.map(l => {
        const ng = L.dienGiaiNguon(l.nguon);
        return `<tr><td style="white-space:nowrap">${T(l.luc)}</td>
          <td><b>${T(ng.ten)}</b><br><code style="font-size:11px">${T(l.nguon)}</code>
            <div class="ghi-chu-nguon">${T(ng.mo_ta)}</div></td>
          <td>${T(l.noi_dung)}</td></tr>`; }).join("")
        || '<tr><td colspan="3"><div class="trang-thai-rong">Trống</div></td></tr>'}</tbody></table></div>
    </div>

    <div data-vung="in" hidden>${htmlPhieuIn(L.metaNhan(d, tk, hang), hang)}</div>`,
    `<button class="nut" onclick="VIP.dongModal()">Đóng</button>
     ${["nhap", "da_duyet"].includes(d.trang_thai) && duoc("tenant.don.ghi") ? `<button class="nut" id="ct-sua">Sửa</button>` : ""}
     ${d.trang_thai === "nhap" && duyet ? `<button class="nut nut-chinh" id="ct-duyet">✔ Duyệt</button>` : ""}
     ${["nhap", "da_duyet"].includes(d.trang_thai) && duyet ? `<button class="nut" id="ct-tu-choi" style="color:var(--do-dam)">✖ Từ chối</button>` : ""}
     ${d.trang_thai === "da_duyet" && duyet && chon.dung_duoc.length ? `<button class="nut nut-chinh" id="ct-gui">🚚 Gửi hãng (MOCK)</button>` : ""}
     ${d.trang_thai !== "huy" && duyet ? `<button class="nut" id="ct-huy" style="color:var(--do-dam)">Hủy đơn</button>` : ""}`);

  const g = (s2) => m.querySelector(s2);
  m.querySelectorAll("[data-tab]").forEach(b => b.addEventListener("click", () => {
    m.querySelectorAll("[data-tab]").forEach(x => x.classList.toggle("hien-tai", x === b));
    m.querySelectorAll("[data-vung]").forEach(v => v.hidden = v.dataset.vung !== b.dataset.tab);
  }));
  const lam = async (duong, body, ten_viec) => {
    try { await api(duong, "POST", body || {}); VIP.dongModal(); bao("Xong."); sauKhiDoi(); }
    catch (e) { baoLoi(e, ten_viec || "thao tác trên đơn", "tenant.don.duyet"); }
  };
  if (g("#ct-duyet")) g("#ct-duyet").addEventListener("click", () => lam(`/api/v2/don/${id}/duyet`, {}, "duyệt đơn"));
  if (g("#ct-gui")) g("#ct-gui").addEventListener("click", () =>
    lam(`/api/v2/don/${id}/gui`, { carrier_account_id: +g("#ct-tk").value }, "gửi đơn sang hãng"));
  if (g("#ct-huy")) g("#ct-huy").addEventListener("click", () => {
    if (!confirm(`Hủy đơn ${d.ma_don}? Hủy KHÔNG ghi lý do — muốn ghi lý do thì dùng "Từ chối".`)) return;
    lam(`/api/v2/don/${id}/huy`, {}, "hủy đơn");
  });
  if (g("#ct-sua")) g("#ct-sua").addEventListener("click", () => { VIP.dongModal(); formDon(d, sauKhiDoi); });
  if (g("#ct-tu-choi")) g("#ct-tu-choi").addEventListener("click", () => manTuChoiDon(d, sauKhiDoi));
  const inNut = g("#pi-in");
  if (inNut) inNut.addEventListener("click", () => window.print());
}

/* ===== F01 — Màn TỪ CHỐI ĐƠN (reject có lý do) =====
   API ĐÃ CÓ từ 15/10/2026 (AG-00 cắm route G04 `POST /api/v2/don/<id>/tu-choi`). Backend nhận
   cả `{ly_do}` thuần và `{ly_do_ma, ghi_chu}` của màn này, rồi tự ghép thành chuỗi lý do lưu
   vào `don_hang.ly_do_tu_choi` + `tu_choi_boi` + `tu_choi_luc`.
   LƯU Ý về trạng thái: "bị từ chối" KHÔNG phải một giá trị `trang_thai` mới — AG-02 cố ý mô
   hình hoá nó là `trang_thai='nhap'` + `ly_do_tu_choi` khác NULL, vì hợp đồng ghim `trang_thai`
   đúng 5 giá trị. Nên sau khi từ chối, đơn quay về danh sách chờ duyệt KÈM lý do, không biến
   mất. Giao diện phải đọc `ly_do_tu_choi` để hiện "đã bị từ chối", không đọc `trang_thai`.
   Nhánh 404 bên dưới GIỮ LẠI làm lưới an toàn cho nền chưa migrate (backend trả 501 khi thiếu
   cột `ly_do_tu_choi`) — không gỡ, vì gỡ là mất đường báo khi chạy trên nền cũ.
   Tuyệt đối không thay bằng /huy một cách im lặng — hủy và từ chối là hai việc khác nhau. */
const DUONG_TU_CHOI = (id) => `/api/v2/don/${id}/tu-choi`;

function manTuChoiDon(d, sauKhiDoi) {
  const m = VIP.moModal(`Từ chối đơn ${T(d.ma_don)}`, `
    <p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Từ chối là <b>quyết định có lý do</b>,
      khác với hủy đơn. Lý do phải vào được nhật ký để sau này tra được vì sao đơn không đi.</p>
    <div class="form-nhom" data-o="ly_do_ma"><label for="tc-ly-do">Lý do <span class="bat-buoc">*</span></label>
      <select id="tc-ly-do"><option value="">— chọn lý do —</option>
        ${L.LY_DO_TU_CHOI.map(([ma, ten]) => `<option value="${T(ma)}">${T(ten)}</option>`).join("")}</select>
      <div class="loi-nhan"></div></div>
    <div class="form-nhom" data-o="ghi_chu"><label for="tc-ghi-chu">Ghi chú</label>
      <input id="tc-ghi-chu" placeholder="bắt buộc nếu chọn &quot;Lý do khác&quot;">
      <div class="loi-nhan"></div></div>
    <div id="tc-kq"></div>`,
    `<button class="nut" onclick="VIP.dongModal()">Hủy</button>
     <button class="nut nut-chinh" id="tc-ok" style="background:var(--do-dam);border-color:var(--do-dam)">✖ Từ chối đơn</button>`);
  m.querySelector("#tc-ok").addEventListener("click", async () => {
    const body = { ly_do_ma: m.querySelector("#tc-ly-do").value, ghi_chu: m.querySelector("#tc-ghi-chu").value.trim() };
    const loi = L.kiemTraTuChoi(body);
    m.querySelectorAll("[data-o]").forEach(n => { n.classList.remove("co-loi"); n.querySelector(".loi-nhan").textContent = ""; });
    loi.forEach(e => {
      const n = m.querySelector(`[data-o="${e.truong}"]`);
      if (n) { n.classList.add("co-loi"); n.querySelector(".loi-nhan").textContent = e.thong_diep; }
    });
    if (loi.length) return;
    try {
      await api(DUONG_TU_CHOI(d.id), "POST", body);
      VIP.dongModal(); bao("Đã từ chối đơn."); sauKhiDoi();
    } catch (e) {
      if (e.daXuLy) return;
      if (e.ma === 404 || e.ma === 405 || e.ma === 501) {
        // 501 = backend CÓ route nhưng CSDL chưa chạy migration G04 (thiếu cột ly_do_tu_choi).
        // Backend cố ý từ chối thay vì âm thầm bỏ mất lý do — lý do là toàn bộ giá trị của
        // hành động này. Giao diện phải nói đúng điều đó, không báo "đã từ chối".
        m.querySelector("#tc-kq").innerHTML = hopChoBackend("/api/v2/don/<id>/tu-choi",
          "HTTP " + e.ma + (e.message ? " — " + e.message : ""));
        m.querySelector("#tc-ok").disabled = true;
        bao("Chưa từ chối được: backend chưa có endpoint từ chối (CHỜ BACKEND).", "canh-bao");
        return;
      }
      baoLoi(e, "từ chối đơn", "tenant.don.duyet");
    }
  });
}

/* ===== F01 — Phiếu in =====
   KHÔNG có API nhãn vận đơn của hãng. Phiếu dưới đây là PHIẾU NỘI BỘ dựng từ CSDL local và
   tự khai đúng như vậy ngay trên giấy in (`la_nhan_hang=false` là bất biến — có ca thử canh).
   Cấm in ra cái trông như nhãn hãng rồi để người dùng dán lên hàng. */
function htmlPhieuIn(meta, hang) {
  const o = meta.o;
  return `
    <div class="hop-cho-backend" style="margin-bottom:12px">
      <b>⏳ Đây KHÔNG phải nhãn vận đơn của hãng</b>
      <div>Backend chưa phơi <code>getShippingLabel</code> ra HTTP
        (mong đợi <code>GET /api/v2/don/&lt;id&gt;/nhan</code> ${nhanChoBackend("/api/v2/don/<id>/nhan")}).
        Phiếu dưới đây dựng từ <b>${T(meta.nguon)}</b> — dùng để dán nội bộ / đối chiếu kho,
        <b>không</b> dán lên hàng thay nhãn hãng.</div>
      <div>Hãng ${hang ? `<b>${T(hang.ten)}</b>` : "(chưa gán)"}
        ${meta.hang_ho_tro_in_nhan ? "<b>có</b>" : "<b>không khai</b>"} khả năng
        <code>getShippingLabel</code> trong capabilities.</div>
      ${meta.thieu.length ? `<div>Thiếu dữ liệu: ${meta.thieu.map(x => T(x)).join(" · ")}.</div>` : ""}
    </div>
    <div class="phieu-in" id="pi-giay">
      <div class="pi-dau">
        <div><b>PHIẾU NỘI BỘ — KHÔNG PHẢI NHÃN VẬN ĐƠN</b>
          <div class="pi-nho">VIP Express Hub · ${T(meta.che_do.nhan)} · in lúc ${T(new Date().toISOString().slice(0, 16).replace("T", " "))}</div></div>
        <div class="pi-ma">${T(o.ma_don)}</div>
      </div>
      <table class="bang bang-hep"><tbody>
        <tr><td>Mã vận đơn</td><td><b>${T(o.ma_van_don || "— chưa có —")}</b></td></tr>
        <tr><td>Người gửi</td><td>${o.nguoi_gui.map(x => T(x || "")).join("<br>")}</td></tr>
        <tr><td>Người nhận</td><td>${o.nguoi_nhan.map(x => T(x || "")).join("<br>")}</td></tr>
        <tr><td>Hàng hóa</td><td>${T(o.hang_hoa)} — ${T(o.khoi_luong_gram)}g</td></tr>
        <tr><td>COD</td><td><b>${tien(o.cod)}</b></td></tr>
        <tr><td>Phí vận chuyển</td><td>${o.phi_van_chuyen != null ? tien(o.phi_van_chuyen) : "— chưa có —"}</td></tr>
        <tr><td>Ghi chú</td><td>${T(o.ghi_chu || "—")}</td></tr>
        <tr><td>Tạo lúc</td><td>${T(o.tao_luc)}</td></tr>
      </tbody></table>
      <div class="pi-chan">Mọi số liệu lấy từ CSDL local. Phiếu này không có mã vạch của hãng
        và không thay thế nhãn vận đơn.</div>
    </div>
    <div class="hang-cong-cu" style="margin:12px 0 0"><div class="day">
      <button class="nut nut-chinh" id="pi-in">🖨 In phiếu nội bộ</button></div></div>`;
}

async function moBatch(id) {
  const kq = await api(`/api/v2/import/${id}`);
  const dem = {};
  kq.dong.forEach(x => dem[x.trang_thai] = (dem[x.trang_thai] || 0) + 1);
  const anh_xa = await napAnhXaCot(id);
  document.getElementById("i-chi-tiet").innerHTML = `
    <div class="the"><div class="the-dau"><h2>Batch #${id} — ${T(kq.batch.ten_file)}</h2>
      <div class="phai">${nhanBatch(kq.batch.trang_thai)}</div></div>
      <div class="the-than" style="padding-bottom:0">
        <div class="chu-giai" style="margin:0 0 12px">${Object.entries(dem).map(([t, n]) =>
          `<span>${nhanDong(t)} <b>${n}</b> dòng</span>`).join("") || "<span>Batch không có dòng nào</span>"}</div>
      </div>
    </div>
    <div id="i-anh-xa" style="margin-top:16px">${htmlAnhXaCot(id, anh_xa, kq)}</div>
    <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Dòng trong batch</h2>
      <div class="phai">${duoc("tenant.import.duyet") ? `<button class="nut nut-chinh nut-nho" id="b-duyet">✔ Duyệt dòng hợp lệ → tạo đơn nháp</button>` : ""}</div></div>
    <div class="cuon-ngang"><table class="bang">
    <thead><tr><th>#</th><th>Người nhận</th><th>SĐT</th><th>Địa chỉ</th><th>Hàng</th><th class="so-tien">KL</th>
    <th class="so-tien">COD</th><th>Trạng thái</th><th>Lỗi</th><th></th></tr></thead>
    <tbody>${kq.dong.map(x => `<tr class="${lopDongBang(x.trang_thai)}">
      <td>${x.stt}</td><td>${T(x.du_lieu.nguoi_nhan_ten)}</td><td>${T(x.du_lieu.nguoi_nhan_sdt)}</td>
      <td style="max-width:180px">${T(x.du_lieu.nguoi_nhan_dia_chi)}</td><td>${T(x.du_lieu.hang_hoa)}</td>
      <td class="so-tien">${T(x.du_lieu.khoi_luong_gram)}</td><td class="so-tien">${T(x.du_lieu.cod || "0")}</td>
      <td>${nhanDong(x.trang_thai)}</td>
      <td style="font-size:11.5px;color:var(--do-dam)">${T(x.loi || "")}</td>
      <td>${["SUBMITTED", "SUCCESS"].includes(x.trang_thai) ? "" : `<button class="nut nut-nho" data-sua-dong="${x.id}">Sửa</button>`}</td></tr>`).join("")
      || '<tr><td colspan="10"><div class="trang-thai-rong">Batch không có dòng nào</div></td></tr>'}</tbody></table></div></div>`;
  gocAnhXaCot(id, anh_xa, kq);
  document.querySelectorAll("[data-sua-dong]").forEach(n => n.addEventListener("click", () => {
    const x = kq.dong.find(y => y.id === +n.dataset.suaDong);
    const m = VIP.moModal(`Sửa dòng #${x.stt}`,
      ["nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa", "khoi_luong_gram", "cod"].map(k =>
        `<div class="form-nhom"><label>${k}</label><input data-k="${k}" value="${T(x.du_lieu[k] || "")}"></div>`).join(""),
      `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="sd-luu">Lưu</button>`);
    m.querySelector("#sd-luu").addEventListener("click", async () => {
      const d = {};
      m.querySelectorAll("[data-k]").forEach(i => d[i.dataset.k] = i.value);
      try { await api(`/api/v2/import/dong/${x.id}`, "PUT", d); VIP.dongModal(); moBatch(id); }
      catch (e) { baoLoi(e); }
    });
  }));
  const bd = document.getElementById("b-duyet");
  if (bd) bd.addEventListener("click", () => {
    const gui_mac_dinh = kq.dong.filter(x => ["VALID", "READY", "FAILED"].includes(x.trang_thai));
    const can_xem = kq.dong.filter(x => x.trang_thai === "NEEDS_REVIEW");
    const khong_ho_tro = kq.dong.filter(x => x.trang_thai === "UNSUPPORTED");
    const m = VIP.moModal("Duyệt batch — thông tin người gửi", `
      <p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Duyệt chỉ tạo đơn <b>nháp</b>; gửi hãng là bước riêng ở màn Đơn hàng.</p>
      <div class="hop-loi" style="background:var(--xanh-duong-nhat);border-color:#BFD4FE;color:var(--xanh-duong);font-size:12.5px">
        Lượt duyệt này gửi <b>${gui_mac_dinh.length}</b> dòng (VALID / READY / FAILED-thử-lại).
        ${khong_ho_tro.length ? `<br><b>${khong_ho_tro.length}</b> dòng <code>UNSUPPORTED</code> bị loại — định dạng dòng đó backend chưa đọc được.` : ""}
      </div>
      ${can_xem.length ? `<div class="form-nhom" style="display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="bd-can-xem" style="width:auto">
        <label for="bd-can-xem" style="margin:0">Gửi kèm <b>${can_xem.length}</b> dòng <code>NEEDS_REVIEW</code> (backend đánh dấu cần người xem lại)</label></div>` : ""}
      <div class="form-nhom"><label>Tên người gửi <span class="bat-buoc">*</span></label><input id="ng-ten"></div>
      <div class="form-nhom"><label>SĐT <span class="bat-buoc">*</span></label><input id="ng-sdt"></div>
      <div class="form-nhom"><label>Địa chỉ lấy hàng <span class="bat-buoc">*</span></label><input id="ng-dc"></div>`,
      `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="bd-ok">Duyệt</button>`);
    m.querySelector("#bd-ok").addEventListener("click", async () => {
      const kem = m.querySelector("#bd-can-xem");
      const ids = gui_mac_dinh.map(x => x.id).concat(kem && kem.checked ? can_xem.map(x => x.id) : []);
      try {
        const kq2 = await api(`/api/v2/import/${id}/duyet`, "POST", {
          dong_ids: ids,
          nguoi_gui: { ten: m.querySelector("#ng-ten").value, sdt: m.querySelector("#ng-sdt").value,
                       dia_chi: m.querySelector("#ng-dc").value } });
        VIP.dongModal(); bao(`Tạo đơn: ${kq2.SUCCESS} thành công, ${kq2.FAILED} lỗi, ${kq2.bo_qua} bỏ qua.`); moBatch(id);
      } catch (e) { baoLoi(e, "duyệt batch import", "tenant.import.duyet"); }
    });
  });
}

/* ===== Ánh xạ cột khi import (F04-UI) =====
   API ánh xạ cột do AG-04 làm, lúc viết màn này CHƯA CÓ (đo 14/10/2026: GET
   /api/v2/import/<id>/anh-xa-cot → 404). Nên: gọi đúng tên dự kiến, 404 thì
   hiện nhãn "CHỜ BACKEND" + phần chẩn đoán suy ra từ dữ liệu THẬT của batch.
   Không bịa endpoint, không bịa tên cột trong file. */
const DUONG_ANH_XA = (id) => `/api/v2/import/${id}/anh-xa-cot`;
// Gợi ý giao diện, KHÔNG phải nguồn chân lý: backend (app/nhap_file.py) mới là chỗ chốt.
const BAT_BUOC_GOI_Y = ["nguoi_nhan_ten", "nguoi_nhan_sdt", "nguoi_nhan_dia_chi", "hang_hoa", "khoi_luong_gram"];

async function napAnhXaCot(id) {
  try {
    return { co: true, d: await api(DUONG_ANH_XA(id)) };
  } catch (e) {
    if (e.ma === 404) return { co: false, ma: 404, loi: e.message };
    if (e.ma === 403) return { co: false, ma: 403, loi: e.message };
    if (e.daXuLy) throw e;
    return { co: false, ma: e.ma, loi: e.message };
  }
}

function htmlAnhXaCot(id, ax, kq) {
  const truong = kq.dong.length ? Object.keys(kq.dong[0].du_lieu) : BAT_BUOC_GOI_Y.slice();
  // trường nào KHÔNG dòng nào có dữ liệu ⇒ gần như chắc là cột chưa được ánh xạ từ file
  const rong = truong.filter(t => kq.dong.length && kq.dong.every(x => !String(x.du_lieu[t] ?? "").trim()));

  if (!ax.co) {
    return `
    <div class="the"><div class="the-dau"><h2>Ánh xạ cột <span class="tag-demo">CHỜ BACKEND</span></h2></div>
      <div class="the-than">
        <div class="hop-loi">
          <b>Chưa sửa được ánh xạ cột trên giao diện.</b><br>
          Giao diện đã gọi <code>GET ${T(DUONG_ANH_XA(id))}</code> và máy chủ trả
          <code>HTTP ${T(ax.ma)}</code>${ax.loi ? ` — ${T(ax.loi)}` : ""}.
          ${ax.ma === 404
            ? "Endpoint này chưa tồn tại (AG-04 đang làm phần backend import). Khi nào backend bật, bảng chỉnh ánh xạ ở đây tự hoạt động, không cần sửa giao diện."
            : "Lỗi không phải 404 — xem lại quyền hoặc máy chủ."}
        </div>
        <h3 style="font-size:13px;margin-bottom:6px">Ánh xạ hiện tại — suy ra từ dữ liệu batch, không phải từ API ánh xạ</h3>
        <p style="font-size:12px;color:var(--chu-mo);margin-top:0">Backend hiện chỉ trả <b>trường nội bộ</b> của từng dòng,
          <b>không</b> trả tên cột gốc trong file. Vì vậy phần dưới chỉ nói được: trường nội bộ nào có nhận dữ liệu, trường nào trống toàn bộ.</p>
        <div class="cuon-ngang"><table class="bang"><thead><tr>
          <th>Trường nội bộ</th><th>Bắt buộc?</th><th>Có dữ liệu?</th><th>Giá trị dòng đầu</th></tr></thead>
        <tbody>${truong.map(t => `<tr>
          <td><code>${T(t)}</code></td>
          <td>${BAT_BUOC_GOI_Y.includes(t) ? '<span class="huy-hieu hh-do">bắt buộc</span>' : '<span class="huy-hieu hh-xam">tùy chọn</span>'}</td>
          <td>${rong.includes(t)
            ? '<span class="huy-hieu hh-vang">trống ở mọi dòng — cột chưa được ánh xạ?</span>'
            : '<span class="huy-hieu hh-xanh">có</span>'}</td>
          <td style="font-size:12px;max-width:220px">${kq.dong.length ? T(kq.dong[0].du_lieu[t] || "") : "—"}</td></tr>`).join("")}</tbody></table></div>
        <p style="font-size:12px;color:var(--chu-mo)">Cột "Bắt buộc?" là <b>gợi ý giao diện</b> theo tài liệu import;
          danh sách chốt nằm ở backend. Trong khi chờ API: sửa từng dòng bằng nút <b>Sửa</b> ở bảng dưới,
          hoặc sửa tiêu đề cột trong file rồi upload lại.</p>
      </div></div>`;
  }

  // Đường có backend: cot_file + anh_xa do máy chủ trả về
  const cot_file = ax.d.cot_file || [];
  const hien = ax.d.anh_xa || {};
  const ds_truong = ax.d.truong_noi_bo || truong;
  const bat_buoc = ax.d.bat_buoc || BAT_BUOC_GOI_Y;
  const mau = ax.d.mau_dong || [];
  const da_phu = new Set(Object.values(hien));
  const thieu = bat_buoc.filter(t => !da_phu.has(t));
  return `
    <div class="the"><div class="the-dau"><h2>Ánh xạ cột</h2>
      <div class="phai">${thieu.length
        ? `<span class="huy-hieu hh-do">thiếu ${thieu.length} trường bắt buộc</span>`
        : '<span class="huy-hieu hh-xanh">đủ trường bắt buộc</span>'}</div></div>
      <div class="the-than">
        <p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Mỗi cột trong file chọn đúng một trường nội bộ.
          Chọn <b>— bỏ qua —</b> nếu cột đó không dùng. Lưu xong, backend kiểm (validate) lại toàn batch.</p>
        ${thieu.length ? `<div class="hop-loi">Chưa ánh xạ trường bắt buộc: ${thieu.map(t => `<code>${T(t)}</code>`).join(" ")}</div>` : ""}
        <div class="cuon-ngang"><table class="bang bang-anh-xa"><thead><tr>
          <th>Cột trong file</th><th>Giá trị mẫu</th><th>→ Trường nội bộ</th></tr></thead>
        <tbody>${cot_file.map((ten, i) => `<tr>
          <td><b>${T(ten)}</b> <span style="color:var(--chu-mo);font-size:11.5px">cột ${i + 1}</span></td>
          <td style="font-size:12px;color:var(--chu-mo);max-width:220px">${(mau[i] != null ? [].concat(mau[i]) : []).slice(0, 2).map(v => T(v)).join(" · ") || "—"}</td>
          <td><select class="o-nho" data-cot="${i}" style="min-width:190px">
            <option value="">— bỏ qua —</option>
            ${ds_truong.map(t => `<option value="${T(t)}" ${hien[i] === t || hien[String(i)] === t ? "selected" : ""}>${T(t)}${bat_buoc.includes(t) ? " *" : ""}</option>`).join("")}
          </select></td></tr>`).join("") || '<tr><td colspan="3">Máy chủ không trả cột nào</td></tr>'}</tbody></table></div>
        <div class="hang-cong-cu" style="margin:14px 0 0">
          <div class="day">
            <button class="nut" id="ax-dat-lai">↺ Lấy lại từ máy chủ</button>
            ${duoc("tenant.import.ghi") ? `<button class="nut nut-chinh" id="ax-luu">💾 Lưu ánh xạ &amp; kiểm lại</button>` : ""}
          </div></div>
      </div></div>`;
}

function gocAnhXaCot(id, ax, kq) {
  if (!ax.co) return;
  const dl = document.getElementById("ax-dat-lai");
  if (dl) dl.addEventListener("click", () => moBatch(id));
  const luu = document.getElementById("ax-luu");
  if (!luu) return;
  luu.addEventListener("click", async () => {
    const anh_xa = {};
    const trung = [];
    document.querySelectorAll("[data-cot]").forEach(s => {
      if (!s.value) return;
      if (Object.values(anh_xa).includes(s.value)) trung.push(s.value);
      anh_xa[s.dataset.cot] = s.value;
    });
    if (trung.length) { bao("Một trường chỉ nhận một cột. Trùng: " + trung.join(", "), "loi"); return; }
    luu.disabled = true;
    try {
      const kq2 = await api(DUONG_ANH_XA(id), "PUT", { anh_xa });
      bao("Đã lưu ánh xạ" + (kq2 && kq2.dem ? ` — kiểm lại: ${JSON.stringify(kq2.dem)}` : "") + ".");
      moBatch(id);
    } catch (e) {
      luu.disabled = false;
      if (e.ma === 404) { bao("Máy chủ chưa có endpoint lưu ánh xạ (404) — CHỜ BACKEND.", "canh-bao"); return; }
      baoLoi(e, "lưu ánh xạ cột import", "tenant.import.ghi");
    }
  });
}

/* ===== khởi động ===== */
async function khoiDong() {
  try { TOI = await api("/api/v2/auth/toi"); dungKhung(); }
  catch { manDangNhap(); }
}
khoiDong();
})();
