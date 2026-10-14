/* Giao diện quản trị VIP Express Hub SaaS v2 (local) — SPA nhỏ, gọi API /api/v2/*.
   Quyền được kiểm ở BACKEND; frontend chỉ ẩn/hiện menu theo TOI.quyen cho gọn.
   Không giữ secret nào, không gọi API hãng trực tiếp. */
(function () {
"use strict";
const goc = document.getElementById("goc");
let TOI = null;

async function api(duong, method, du_lieu, headers) {
  const res = await fetch(duong, {
    method: method || "GET",
    headers: Object.assign({ "X-Requested-With": "VIPHub", "Content-Type": "application/json" }, headers || {}),
    body: du_lieu != null ? JSON.stringify(du_lieu) : undefined,
  });
  let kq = {};
  try { kq = await res.json(); } catch {}
  if (!res.ok) throw new Error(kq.loi || ("HTTP " + res.status));
  return kq;
}
const T = VIP.thoat, tien = VIP.tien;
const bao = (m, loai) => VIP.toast(m, loai);
const duoc = (p) => (TOI.quyen || []).includes(p);

/* ===== Đăng nhập ===== */
function manDangNhap(thong_bao) {
  goc.innerHTML = `
  <div class="man-dang-nhap"><div class="hop-dang-nhap">
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:18px">
      <span style="width:34px;height:34px;border-radius:8px;background:var(--do-vip);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800">V</span>
      <b style="font-size:16px">VIP Express Hub — Quản trị</b>
    </div>
    <p style="font-size:12px;color:var(--chu-mo);margin-top:0">Bản SaaS local — dữ liệu demo, hãng vận chuyển ở chế độ MOCK.</p>
    ${thong_bao ? `<div class="hop-loi" style="margin-bottom:12px">${T(thong_bao)}</div>` : ""}
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
    } catch (e) { manDangNhap(e.message); }
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
        } catch (e) { bao(e.message, "loi"); }
      });
    }
  });
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
    await api("/api/v2/auth/dang-xuat", "POST", {}); TOI = null; manDangNhap();
  });
  document.getElementById("nut-menu").addEventListener("click", () =>
    document.getElementById("sidebar").classList.toggle("mo"));
  goc.querySelectorAll("[data-man]").forEach(a => a.addEventListener("click", () => moMan(a.dataset.man)));
  const sel = document.getElementById("chon-tenant");
  if (sel) sel.addEventListener("change", async () => {
    try {
      await api("/api/v2/auth/doi-tenant", "POST", { tenant_id: +sel.value });
      bao("Đã chuyển doanh nghiệp."); khoiDong();   // nạp lại toàn bộ: không mang dữ liệu tenant cũ
    } catch (e) { bao(e.message, "loi"); khoiDong(); }
  });
  moMan(menu[0][0]);
}

function datMan(tieu_de, html) {
  document.getElementById("tieu-de").textContent = tieu_de;
  document.getElementById("man").innerHTML = html;
}

async function moMan(id) {
  goc.querySelectorAll("[data-man]").forEach(a => a.classList.toggle("hien-tai", a.dataset.man === id));
  document.getElementById("sidebar").classList.remove("mo");
  try { await CAC_MAN[id](); }
  catch (e) { datMan("Lỗi", `<div class="hop-loi">${T(e.message)}</div>`); }
}

/* ===== Màn hình ===== */
const CAC_MAN = {
  async "tong-quan"() {
    const don = await api("/api/v2/don?gioi_han=500");
    let b = null;
    if (duoc("tenant.billing.xem")) b = await api("/api/v2/billing");
    const dem = t => don.don.filter(d => d.trang_thai === t).length;
    datMan("Tổng quan", `
      <div class="luoi luoi-kpi">
        <div class="the kpi"><div class="nhan">Đơn trong hệ</div><div class="so">${don.don.length}</div></div>
        <div class="the kpi"><div class="nhan">Đã gửi hãng</div><div class="so" style="color:var(--xanh-la)">${dem("da_gui")}</div></div>
        <div class="the kpi"><div class="nhan">Nháp/chờ duyệt</div><div class="so">${dem("nhap") + dem("da_duyet")}</div></div>
        ${b ? `<div class="the kpi"><div class="nhan">Usage tháng ${b.usage.thang}</div>
          <div class="so">${b.usage.so_don}/${b.goi.han_muc_don_thang}</div><div class="phu">gói ${T(b.goi.ten)}</div></div>`
            : `<div class="the kpi"><div class="nhan">Vai trò</div><div class="so" style="font-size:16px">${T(TOI.vai_tro)}</div></div>`}
      </div>
      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Đơn mới nhất</h2></div>
      <div class="cuon-ngang"><table class="bang"><thead><tr><th>Mã</th><th>Người nhận</th><th>Trạng thái</th><th>Giao vận</th><th class="so-tien">COD</th></tr></thead>
      <tbody>${don.don.slice(0, 8).map(d => `<tr><td><b>${T(d.ma_don)}</b></td><td>${T(d.nguoi_nhan_ten)}</td>
        <td>${nhanTT(d.trang_thai)}</td><td>${d.trang_thai_giao ? T(d.trang_thai_giao) : "—"}</td>
        <td class="so-tien">${tien(d.cod)}</td></tr>`).join("") || '<tr><td colspan="5">Chưa có đơn</td></tr>'}</tbody></table></div></div>`);
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
        } catch (e) { bao(e.message, "loi"); }
      });
    });
  },

  async import() {
    const kq = await api("/api/v2/import");
    datMan("Import file", `
      <div class="the"><div class="the-than">
        <p style="margin-top:0">Hỗ trợ <b>CSV</b>, <b>XLSX</b>, <b>PDF có lớp văn bản</b> (PDF scan chưa hỗ trợ — sẽ báo lỗi rõ).
        Upload chỉ tạo <b>batch xem trước</b>; đơn chỉ được tạo sau khi bạn duyệt.</p>
        <input type="file" id="i-tep" accept=".csv,.xlsx,.pdf">
        <button class="nut nut-chinh" id="i-len">⬆ Upload</button>
      </div></div>
      <div class="the" style="margin-top:16px"><div class="the-dau"><h2>Các batch</h2></div>
      <div class="cuon-ngang"><table class="bang"><thead><tr><th>#</th><th>File</th><th>Trạng thái</th><th>Lúc</th><th></th></tr></thead>
      <tbody>${kq.batch.map(b => `<tr><td>${b.id}</td><td>${T(b.ten_file)}</td><td>${T(b.trang_thai)}</td>
        <td>${T(b.tao_luc)}</td><td><button class="nut nut-nho" data-batch="${b.id}">Mở</button></td></tr>`).join("")
        || '<tr><td colspan="5"><div class="trang-thai-rong"><div class="to">📥</div>Chưa có batch</div></td></tr>'}</tbody></table></div></div>
      <div id="i-chi-tiet" style="margin-top:16px"></div>`);
    document.getElementById("i-len").addEventListener("click", async () => {
      const f = document.getElementById("i-tep").files[0];
      if (!f) { bao("Chọn file trước.", "canh-bao"); return; }
      const b64 = btoa(String.fromCharCode(...new Uint8Array(await f.arrayBuffer())));
      try {
        const kq2 = await api("/api/v2/import", "POST", { ten_file: f.name, noi_dung_base64: b64 });
        bao("Đã tạo batch #" + kq2.batch_id); moMan("import");
      } catch (e) { bao(e.message, "loi"); }
    });
    document.querySelectorAll("[data-batch]").forEach(n => n.addEventListener("click", () => moBatch(+n.dataset.batch)));
  },

  async hang() {
    const [hs, tk] = await Promise.all([api("/api/v2/hang"), api("/api/v2/tai-khoan-hang")]);
    const ql = duoc("tenant.hang.quan_ly");
    datMan("Hãng vận chuyển", `
      <div class="luoi luoi-3">${hs.hang.map(h => `
        <div class="the the-hang"><div><span class="ten-hang">${T(h.ten)}</span>
          <span class="huy-hieu ${h.live_mo ? "hh-xanh" : "hh-vang"}">${h.live_mo ? "LIVE mở" : "MOCK — LIVE khóa chờ duyệt"}</span></div>
        <div style="font-size:12px;color:var(--chu-mo)">Hỗ trợ: ${Object.entries(h.capabilities).filter(([, v]) => v).map(([k]) => k).join(", ") || "—"}</div>
        ${ql ? `<button class="nut nut-nho" data-them-tk="${h.ma}">＋ Thêm tài khoản (mock)</button>` : ""}</div>`).join("")}
      </div>
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
      } catch (e) { bao(e.message, "loi"); }
    }));
    document.querySelectorAll("[data-tk]").forEach(n => n.addEventListener("click", async () => {
      await api(`/api/v2/tai-khoan-hang/${n.dataset.tk}/${n.dataset.v}`, "POST", {}); moMan("hang");
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
        } catch (e) { bao(e.message, "loi"); }
      });
    }));
    document.querySelectorAll("[data-revoke]").forEach(n => n.addEventListener("click", async () => {
      if (!confirm("Thu hồi credentials và tắt tài khoản hãng này?")) return;
      await api(`/api/v2/tai-khoan-hang/${n.dataset.revoke}/revoke`, "POST", {});
      bao("Đã thu hồi."); moMan("hang");
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
      catch (e) { bao(e.message, "loi"); }
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
            bao("Xong."); moMan("thanh-vien"); } catch (e) { bao(e.message, "loi"); }
    }));
    document.querySelectorAll("[data-xoa]").forEach(n => n.addEventListener("click", async () => {
      if (!confirm("Xóa thành viên khỏi doanh nghiệp này?")) return;
      try { await api(`/api/v2/memberships/${n.dataset.xoa}`, "DELETE"); bao("Đã xóa."); moMan("thanh-vien"); }
      catch (e) { bao(e.message, "loi"); }
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
        catch (e) { bao(e.message, "loi"); }
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
        } catch (e) { bao(e.message, "loi"); }
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
      } catch (e) { bao(e.message, "loi"); }
    });
    document.getElementById("c-thu-hoi").addEventListener("click", async () => {
      await api("/api/v2/auth/thu-hoi-phien", "POST", {}); bao("Đã thu hồi các phiên khác.");
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
      await api(`/api/v2/platform/tenants/${n.dataset.t}/${n.dataset.v}`, "POST", {}); moMan("tenants");
    }));
    document.querySelectorAll("[data-goi]").forEach(n => n.addEventListener("change", async () => {
      if (!n.value) return;
      try { await api(`/api/v2/platform/tenants/${n.dataset.goi}/goi`, "POST", { goi_id: n.value });
            bao("Đã đổi gói."); moMan("tenants"); } catch (e) { bao(e.message, "loi"); }
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
        } catch (e) { bao(e.message, "loi"); }
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
    } catch (e) { bao(e.message, "loi"); }
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
    catch (e) { bao(e.message, "loi"); }
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
  const lop = { VALID: "hh-xanh", INVALID: "hh-do", SUCCESS: "hh-xanh", FAILED: "hh-do", SUBMITTED: "hh-vang", READY: "hh-xanh-duong" };
  document.getElementById("i-chi-tiet").innerHTML = `
    <div class="the"><div class="the-dau"><h2>Batch #${id} — ${T(kq.batch.ten_file)}</h2>
      <div class="phai">${duoc("tenant.import.duyet") ? `<button class="nut nut-chinh nut-nho" id="b-duyet">✔ Duyệt dòng VALID → tạo đơn nháp</button>` : ""}</div></div>
    <div class="cuon-ngang"><table class="bang">
    <thead><tr><th>#</th><th>Người nhận</th><th>SĐT</th><th>Địa chỉ</th><th>Hàng</th><th class="so-tien">KL</th>
    <th class="so-tien">COD</th><th>Trạng thái</th><th>Lỗi</th><th></th></tr></thead>
    <tbody>${kq.dong.map(x => `<tr class="${x.trang_thai === "INVALID" ? "dong-loi" : x.trang_thai === "VALID" ? "dong-hop-le" : ""}">
      <td>${x.stt}</td><td>${T(x.du_lieu.nguoi_nhan_ten)}</td><td>${T(x.du_lieu.nguoi_nhan_sdt)}</td>
      <td style="max-width:180px">${T(x.du_lieu.nguoi_nhan_dia_chi)}</td><td>${T(x.du_lieu.hang_hoa)}</td>
      <td class="so-tien">${T(x.du_lieu.khoi_luong_gram)}</td><td class="so-tien">${T(x.du_lieu.cod || "0")}</td>
      <td><span class="huy-hieu ${lop[x.trang_thai] || "hh-xam"}">${x.trang_thai}</span></td>
      <td style="font-size:11.5px;color:var(--do-dam)">${T(x.loi || "")}</td>
      <td>${["SUBMITTED", "SUCCESS"].includes(x.trang_thai) ? "" : `<button class="nut nut-nho" data-sua-dong="${x.id}">Sửa</button>`}</td></tr>`).join("")}</tbody></table></div></div>`;
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
      catch (e) { bao(e.message, "loi"); }
    });
  }));
  const bd = document.getElementById("b-duyet");
  if (bd) bd.addEventListener("click", () => {
    const m = VIP.moModal("Duyệt batch — thông tin người gửi", `
      <p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Chỉ dòng VALID được tạo đơn <b>nháp</b>; gửi hãng là bước riêng ở màn Đơn hàng.</p>
      <div class="form-nhom"><label>Tên người gửi</label><input id="ng-ten"></div>
      <div class="form-nhom"><label>SĐT</label><input id="ng-sdt"></div>
      <div class="form-nhom"><label>Địa chỉ lấy hàng</label><input id="ng-dc"></div>`,
      `<button class="nut" onclick="VIP.dongModal()">Hủy</button><button class="nut nut-chinh" id="bd-ok">Duyệt</button>`);
    m.querySelector("#bd-ok").addEventListener("click", async () => {
      try {
        const kq2 = await api(`/api/v2/import/${id}/duyet`, "POST", {
          dong_ids: kq.dong.filter(x => ["VALID", "READY", "FAILED"].includes(x.trang_thai)).map(x => x.id),
          nguoi_gui: { ten: m.querySelector("#ng-ten").value, sdt: m.querySelector("#ng-sdt").value,
                       dia_chi: m.querySelector("#ng-dc").value } });
        VIP.dongModal(); bao(`Tạo đơn: ${kq2.SUCCESS} thành công, ${kq2.FAILED} lỗi, ${kq2.bo_qua} bỏ qua.`); moBatch(id);
      } catch (e) { bao(e.message, "loi"); }
    });
  });
}

/* ===== khởi động ===== */
async function khoiDong() {
  try { TOI = await api("/api/v2/auth/toi"); dungKhung(); }
  catch { manDangNhap(); }
}
khoiDong();
})();
