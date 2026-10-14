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
  moMan(quay_lai || menu[0][0]);
}

function datMan(tieu_de, html) {
  document.getElementById("tieu-de").textContent = tieu_de;
  document.getElementById("man").innerHTML = html;
}

async function moMan(id) {
  MAN_HIEN_TAI = id;
  goc.querySelectorAll("[data-man]").forEach(a => a.classList.toggle("hien-tai", a.dataset.man === id));
  document.getElementById("sidebar").classList.remove("mo");
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
              <td style="font-size:12px">${Object.entries(o.giao).map(([k, v]) => `${T(k)}: <b>${v}</b>`).join("<br>") || "—"}</td></tr>`).join("")
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
        <td>${nhanTT(d.trang_thai)}</td><td>${d.trang_thai_giao ? T(d.trang_thai_giao) : "—"}</td>
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

  async don() {
    const tk = duoc("tenant.hang.xem") ? await api("/api/v2/tai-khoan-hang") : { tai_khoan: [] };
    datMan("Đơn hàng", `
      <div class="hang-cong-cu">
        <input id="d-tim" class="o-nho" type="search" placeholder="Tìm mã/người nhận/SĐT…" style="min-width:220px">
        <select id="d-tt" class="nut" style="padding:7px 10px"><option value="">Mọi trạng thái</option>
          ${["nhap", "da_duyet", "dang_gui", "da_gui", "huy"].map(t => `<option>${t}</option>`).join("")}</select>
        <div class="day"><a class="nut" href="/api/v2/don/xuat-csv">⬇ Xuất CSV</a>
          ${duoc("tenant.don.ghi") ? `<button class="nut nut-chinh" id="d-them">➕ Tạo đơn</button>` : ""}</div>
      </div>
      <div class="the"><div class="cuon-ngang"><table class="bang">
        <thead><tr><th>Mã</th><th>Người nhận</th><th>Hàng hóa</th><th class="so-tien">COD</th>
        <th>Trạng thái</th><th>Giao vận</th><th>Mã vận đơn</th><th></th></tr></thead>
        <tbody id="d-bang"></tbody></table></div></div>`);
    const ve = async () => {
      const q = document.getElementById("d-tim").value.trim();
      const tt = document.getElementById("d-tt").value;
      const kq = await api(`/api/v2/don?q=${encodeURIComponent(q)}&trang_thai=${tt}`);
      document.getElementById("d-bang").innerHTML = kq.don.map(d => `
        <tr><td><b>${T(d.ma_don)}</b>${d.can_doi_soat_ket_qua ? ' <span class="huy-hieu hh-vang">cần kiểm lại</span>' : ""}</td>
        <td>${T(d.nguoi_nhan_ten)}<br><span style="color:var(--chu-mo);font-size:12px">${T(d.nguoi_nhan_sdt)}</span></td>
        <td>${T(d.hang_hoa)}</td><td class="so-tien">${tien(d.cod)}</td>
        <td>${nhanTT(d.trang_thai)}</td><td>${d.trang_thai_giao ? T(d.trang_thai_giao) : "—"}</td>
        <td>${T(d.ma_van_don || "—")}</td>
        <td><button class="nut nut-nho" data-xem="${d.id}">Chi tiết</button></td></tr>`).join("")
        || '<tr><td colspan="8"><div class="trang-thai-rong"><div class="to">📦</div>Chưa có đơn</div></td></tr>';
      document.querySelectorAll("[data-xem]").forEach(n =>
        n.addEventListener("click", () => chiTietDon(+n.dataset.xem, tk.tai_khoan, ve)));
    };
    document.getElementById("d-tim").addEventListener("input", ve);
    document.getElementById("d-tt").addEventListener("change", ve);
    const nutThem = document.getElementById("d-them");
    if (nutThem) nutThem.addEventListener("click", () => formDon(null, ve));
    ve();
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
        <td>…${T(t2.credentials_duoi || "—")} <span style="color:var(--chu-mo);font-size:11px">(mã hóa, không xem lại được${t2.credentials_doi_luc ? "; đổi " + T(t2.credentials_doi_luc) : ""})</span></td>
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

  async webhook() {
    const kq = await api("/api/v2/webhook/su-kien");
    const lop = { xong: "hh-xanh", dlq: "hh-do", cho_thu_lai: "hh-vang", moi: "hh-xam", khong_khop: "hh-vang" };
    datMan("Webhook", `
      <div class="the"><div class="the-dau"><h2>Sự kiện webhook của doanh nghiệp</h2>
        <div class="phai"><button class="nut nut-nho" id="w-moi">↻ Làm mới</button></div></div>
      <div class="cuon-ngang"><table class="bang">
      <thead><tr><th>#</th><th>Event ID</th><th>Hãng</th><th>Nhận lúc</th><th>Trạng thái</th><th>Lần thử</th><th>Lỗi</th><th></th></tr></thead>
      <tbody>${kq.su_kien.map(s => `<tr><td>${s.id}</td><td>${T(s.event_id)}</td><td>${T(s.hang)}</td>
        <td style="white-space:nowrap">${T(s.nhan_luc)}</td>
        <td><span class="huy-hieu ${lop[s.trang_thai] || "hh-xam"}">${T(s.trang_thai)}</span></td>
        <td style="text-align:center">${s.so_lan_thu}</td><td style="font-size:11.5px;max-width:220px">${T(s.loi_cuoi || "")}</td>
        <td>${duoc("tenant.webhook.replay") && ["dlq", "khong_khop"].includes(s.trang_thai) ? `<button class="nut nut-nho" data-replay="${s.id}">Replay</button>` : ""}</td></tr>`).join("")
        || '<tr><td colspan="8"><div class="trang-thai-rong"><div class="to">🔔</div>Chưa có sự kiện</div></td></tr>'}</tbody></table></div></div>`);
    document.getElementById("w-moi").addEventListener("click", () => moMan("webhook"));
    document.querySelectorAll("[data-replay]").forEach(n => n.addEventListener("click", async () => {
      try { await api(`/api/v2/webhook/su-kien/${n.dataset.replay}/replay`, "POST", {});
            bao("Đã nạp lại (có audit)."); setTimeout(() => moMan("webhook"), 500); }
      catch (e) { baoLoi(e, "replay sự kiện webhook", "tenant.webhook.replay"); }
    }));
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

/* ===== phụ trợ ===== */
function nhanTT(t) {
  const lop = { nhap: "hh-xam", da_duyet: "hh-xanh-duong", dang_gui: "hh-vang", da_gui: "hh-xanh", huy: "hh-do" };
  const ten = { nhap: "Nháp", da_duyet: "Đã duyệt", dang_gui: "Đang gửi hãng", da_gui: "Đã gửi hãng", huy: "Hủy" };
  return `<span class="huy-hieu ${lop[t] || "hh-xam"}">${ten[t] || t}</span>`;
}
/* Tên tiếng Việt cho capabilities của hãng (khóa do backend/adapter đặt).
   Khóa lạ thì hiện nguyên văn khóa — không bỏ qua, để thấy ngay khi adapter thêm khả năng mới. */
const TEN_KHA_NANG = {
  createOrder: "Tạo đơn", cancelOrder: "Hủy đơn", getOrder: "Tra đơn",
  trackOrder: "Theo dõi hành trình", getShippingFee: "Tính cước",
  getShippingLabel: "In nhãn vận đơn", webhook: "Nhận webhook",
};

/* Trạng thái batch/dòng import — đỡ được CẢ bộ cũ (`moi`) và bộ mới của AG-04
   (UPLOADED…FAILED, UNSUPPORTED, NEEDS_REVIEW). Trạng thái lạ thì hiện nguyên văn
   kèm huy hiệu xám, KHÔNG im lặng bỏ qua — để thấy ngay khi backend thêm trạng thái mới. */
const BATCH_TT = {
  moi: ["hh-xam", "Mới (bộ cũ)"],
  xong: ["hh-xanh", "Xong (bộ cũ)"],
  da_duyet_mot_phan: ["hh-vang", "Duyệt một phần (bộ cũ)"],
  UPLOADED: ["hh-xam", "Đã upload"],
  PARSING: ["hh-xanh-duong", "Đang đọc file"],
  VALIDATING: ["hh-xanh-duong", "Đang kiểm dữ liệu"],
  READY: ["hh-xanh", "Sẵn sàng duyệt"],
  APPROVED: ["hh-xanh-duong", "Đã duyệt"],
  PROCESSING: ["hh-vang", "Đang tạo đơn"],
  COMPLETED: ["hh-xanh", "Hoàn tất"],
  PARTIAL_FAILED: ["hh-vang", "Hoàn tất một phần"],
  FAILED: ["hh-do", "Thất bại"],
};
const DONG_TT = {
  VALID: ["hh-xanh", "VALID", "hợp lệ, duyệt được"],
  INVALID: ["hh-do", "INVALID", "dữ liệu sai, phải sửa"],
  READY: ["hh-xanh-duong", "READY", "đã chuẩn hóa, chờ duyệt"],
  SUBMITTED: ["hh-vang", "SUBMITTED", "đã gửi tạo đơn"],
  SUCCESS: ["hh-xanh", "SUCCESS", "đã tạo đơn nháp"],
  FAILED: ["hh-do", "FAILED", "tạo đơn lỗi, thử lại được"],
  UNSUPPORTED: ["hh-xam", "UNSUPPORTED", "backend không đọc được dòng này"],
  NEEDS_REVIEW: ["hh-vang", "NEEDS_REVIEW", "backend yêu cầu người xem lại"],
};
function nhanBatch(t) {
  const d = BATCH_TT[t];
  return d ? `<span class="huy-hieu ${d[0]}" title="${T(t)}">${d[1]}</span>`
           : `<span class="huy-hieu hh-xam" title="trạng thái giao diện chưa biết tên tiếng Việt">${T(t)}</span>`;
}
function nhanDong(t) {
  const d = DONG_TT[t];
  return d ? `<span class="huy-hieu ${d[0]}" title="${T(d[2])}">${d[1]}</span>`
           : `<span class="huy-hieu hh-xam" title="trạng thái giao diện chưa biết">${T(t)}</span>`;
}
function lopDongBang(t) {
  if (["INVALID", "FAILED", "UNSUPPORTED"].includes(t)) return "dong-loi";
  if (t === "NEEDS_REVIEW") return "dong-can-xem";
  if (["VALID", "READY", "SUCCESS"].includes(t)) return "dong-hop-le";
  return "";
}

function bangAudit(ds) {
  return `<div class="the"><div class="cuon-ngang"><table class="bang">
    <thead><tr><th>Lúc</th><th>Actor</th><th>Hành động</th><th>Resource</th><th>Kết quả</th><th>Chi tiết</th></tr></thead>
    <tbody>${ds.map(a => `<tr><td style="white-space:nowrap">${T(a.luc)}</td><td>${a.user_id ?? "—"}</td>
      <td><b>${T(a.hanh_dong)}</b></td><td>${T(a.resource_type || "")}${a.resource_id ? ":" + T(a.resource_id) : ""}</td>
      <td><span class="huy-hieu ${a.ket_qua === "thanh_cong" ? "hh-xanh" : "hh-do"}">${T(a.ket_qua || "")}</span></td>
      <td style="font-size:12px">${T(a.chi_tiet || "")}</td></tr>`).join("") || '<tr><td colspan="6">Trống</td></tr>'}</tbody></table></div></div>`;
}

function formDon(don, sauKhiLuu) {
  const f = don || {};
  const m = VIP.moModal(don ? "Sửa đơn" : "Tạo đơn mới", `
    <div class="form-hang">
      <div class="form-nhom"><label>Người gửi <span class="bat-buoc">*</span></label><input id="f-gt" value="${T(f.nguoi_gui_ten || "")}"></div>
      <div class="form-nhom"><label>SĐT gửi <span class="bat-buoc">*</span></label><input id="f-gs" value="${T(f.nguoi_gui_sdt || "")}"></div>
      <div class="form-nhom" style="grid-column:1/-1"><label>Địa chỉ gửi <span class="bat-buoc">*</span></label><input id="f-gd" value="${T(f.nguoi_gui_dia_chi || "")}"></div>
      <div class="form-nhom"><label>Người nhận <span class="bat-buoc">*</span></label><input id="f-nt" value="${T(f.nguoi_nhan_ten || "")}"></div>
      <div class="form-nhom"><label>SĐT nhận <span class="bat-buoc">*</span></label><input id="f-ns" value="${T(f.nguoi_nhan_sdt || "")}"></div>
      <div class="form-nhom" style="grid-column:1/-1"><label>Địa chỉ nhận <span class="bat-buoc">*</span></label><input id="f-nd" value="${T(f.nguoi_nhan_dia_chi || "")}"></div>
      <div class="form-nhom"><label>Hàng hóa <span class="bat-buoc">*</span></label><input id="f-hh" value="${T(f.hang_hoa || "")}"></div>
      <div class="form-nhom"><label>Cân nặng (gram) <span class="bat-buoc">*</span></label><input id="f-kl" type="number" value="${f.khoi_luong_gram || ""}"></div>
      <div class="form-nhom"><label>COD (₫)</label><input id="f-cod" type="number" value="${f.cod ?? 0}"></div>
      <div class="form-nhom"><label>Ghi chú</label><input id="f-gc" value="${T(f.ghi_chu || "")}"></div>
    </div>`,
    `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="f-luu">💾 Lưu</button>`);
  m.querySelector("#f-luu").addEventListener("click", async () => {
    const d = {
      nguoi_gui_ten: m.querySelector("#f-gt").value, nguoi_gui_sdt: m.querySelector("#f-gs").value,
      nguoi_gui_dia_chi: m.querySelector("#f-gd").value, nguoi_nhan_ten: m.querySelector("#f-nt").value,
      nguoi_nhan_sdt: m.querySelector("#f-ns").value, nguoi_nhan_dia_chi: m.querySelector("#f-nd").value,
      hang_hoa: m.querySelector("#f-hh").value, khoi_luong_gram: +m.querySelector("#f-kl").value,
      cod: +m.querySelector("#f-cod").value || 0, ghi_chu: m.querySelector("#f-gc").value,
    };
    try {
      if (don) await api(`/api/v2/don/${don.id}`, "PUT", d);
      else await api("/api/v2/don", "POST", d,
        { "Idempotency-Key": "ui-" + Date.now() + "-" + Math.random().toString(36).slice(2) });
      VIP.dongModal(); bao(don ? "Đã sửa đơn." : "Đã tạo đơn nháp."); sauKhiLuu();
    } catch (e) { baoLoi(e, don ? "sửa đơn" : "tạo đơn", "tenant.don.ghi"); }
  });
}

async function chiTietDon(id, taiKhoanHang, sauKhiDoi) {
  const kq = await api(`/api/v2/don/${id}`);
  const d = kq.don;
  const duyet = duoc("tenant.don.duyet");
  const m = VIP.moModal(`Đơn ${T(d.ma_don)}`, `
    <table class="bang"><tbody>
      <tr><td style="width:150px;color:var(--chu-mo)">Trạng thái</td><td>${nhanTT(d.trang_thai)}
        ${d.can_doi_soat_ket_qua ? ' <span class="huy-hieu hh-vang">timeout — cần kiểm lại với hãng</span>' : ""}</td></tr>
      <tr><td style="color:var(--chu-mo)">Giao vận</td><td>${T(d.trang_thai_giao || "—")}</td></tr>
      <tr><td style="color:var(--chu-mo)">Mã vận đơn</td><td>${T(d.ma_van_don || "—")}</td></tr>
      <tr><td style="color:var(--chu-mo)">Người nhận</td><td>${T(d.nguoi_nhan_ten)} — ${T(d.nguoi_nhan_sdt)}<br>${T(d.nguoi_nhan_dia_chi)}</td></tr>
      <tr><td style="color:var(--chu-mo)">Hàng / COD / Phí</td><td>${T(d.hang_hoa)} (${d.khoi_luong_gram}g) / ${tien(d.cod)} / ${d.phi_van_chuyen != null ? tien(d.phi_van_chuyen) : "—"}</td></tr>
    </tbody></table>
    <h3 style="font-size:13px">Lịch sử</h3>
    <div style="max-height:160px;overflow:auto;font-size:12px">${kq.lich_su.map(l =>
      `<div style="padding:4px 0;border-bottom:1px solid var(--vien)"><span style="color:var(--chu-mo)">${T(l.luc)} · ${T(l.nguon)}</span><br>${T(l.noi_dung)}</div>`).join("")}</div>
    ${d.trang_thai === "da_duyet" && duyet ? `
      <div class="form-nhom" style="margin-top:12px"><label>Gửi qua tài khoản hãng</label>
      <select id="ct-tk">${taiKhoanHang.filter(t2 => t2.kich_hoat).map(t2 => `<option value="${t2.id}">${T(t2.ten)} (${T(t2.moi_truong)})</option>`).join("")}</select></div>` : ""}`,
    `<button class="nut" onclick="VIP.dongModal()">Đóng</button>
     ${["nhap", "da_duyet"].includes(d.trang_thai) && duoc("tenant.don.ghi") ? `<button class="nut" id="ct-sua">Sửa</button>` : ""}
     ${d.trang_thai === "nhap" && duyet ? `<button class="nut nut-chinh" id="ct-duyet">Duyệt</button>` : ""}
     ${d.trang_thai === "da_duyet" && duyet ? `<button class="nut nut-chinh" id="ct-gui">🚚 Gửi hãng (mock)</button>` : ""}
     ${d.trang_thai !== "huy" && duyet ? `<button class="nut" id="ct-huy" style="color:var(--do-dam)">Hủy đơn</button>` : ""}`);
  const lam = async (duong, body) => {
    try { await api(duong, "POST", body || {}); VIP.dongModal(); bao("Xong."); sauKhiDoi(); }
    catch (e) { baoLoi(e, "thao tác trên đơn (duyệt / gửi hãng / hủy)", "tenant.don.duyet"); }
  };
  const g = (s) => m.querySelector(s);
  if (g("#ct-duyet")) g("#ct-duyet").addEventListener("click", () => lam(`/api/v2/don/${id}/duyet`));
  if (g("#ct-gui")) g("#ct-gui").addEventListener("click", () =>
    lam(`/api/v2/don/${id}/gui`, { carrier_account_id: +g("#ct-tk").value }));
  if (g("#ct-huy")) g("#ct-huy").addEventListener("click", () => lam(`/api/v2/don/${id}/huy`));
  if (g("#ct-sua")) g("#ct-sua").addEventListener("click", () => { VIP.dongModal(); formDon(d, sauKhiDoi); });
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
