/* VIP Express Hub — G00 — khung dùng chung cho mọi trang.
   Toàn bộ là DEMO frontend: không gọi API hãng vận chuyển nào. */
(function () {
  "use strict";

  const GOC = location.pathname.includes("/pages/") ? ".." : ".";

  const MENU = [
    { id: "dashboard", ten: "Dashboard", icon: "📊", href: "pages/dashboard.html" },
    { id: "shipments", ten: "Vận đơn", icon: "📦", href: "pages/shipments.html" },
    { id: "create-order", ten: "Tạo đơn", icon: "➕", href: "pages/create-order.html" },
    { id: "ai-import", ten: "AI Import", icon: "🤖", href: "pages/ai-import.html" },
    { id: "webhooks", ten: "Webhook Center", icon: "🔔", href: "pages/webhooks.html" },
    { id: "carriers", ten: "Nhà vận chuyển", icon: "🚚", href: "pages/carriers.html" },
    { id: "pricing", ten: "So sánh cước", icon: "💰", href: "pages/pricing.html" },
    { id: "cod", ten: "Đối soát COD", icon: "🧾", href: "pages/cod.html" },
    { id: "reports", ten: "Báo cáo", icon: "📈", href: "pages/reports.html" },
    { id: "settings", ten: "Cấu hình", icon: "⚙️", href: "pages/settings.html" },
  ];

  const TT_LOP = {
    cho_lay: "hh-xam", dang_giao: "hh-xanh-duong", giao_thanh_cong: "hh-xanh",
    giao_that_bai: "hh-do", dang_hoan: "hh-vang", da_huy: "hh-xam",
  };

  function dungKhung(trangId, tieuDe) {
    const body = document.body;
    const noiDungGoc = document.getElementById("noi-dung-trang");
    const khung = document.createElement("div");
    khung.className = "khung";
    khung.innerHTML = `
      <aside class="sidebar" id="sidebar" aria-label="Điều hướng chính">
        <div class="logo"><span class="dau" aria-hidden="true">V</span> VIP Express Hub</div>
        <nav>${MENU.map(m => `
          <a href="${GOC}/${m.href}" ${m.id === trangId ? 'class="hien-tai" aria-current="page"' : ""}>
            <span aria-hidden="true">${m.icon}</span> ${m.ten}
          </a>`).join("")}
        </nav>
        <div class="chan">G00 · HTML FIRST · bản mô phỏng<br>Dữ liệu hư cấu — không phải số liệu thật</div>
      </aside>
      <div class="noi-dung">
        <div class="bang-demo">⚠️ DEMO — CHƯA KẾT NỐI API · Mọi dữ liệu trên trang này là mô phỏng</div>
        <header class="header">
          <button class="nut-menu" id="nut-menu" aria-label="Mở menu">☰</button>
          <h1>${tieuDe}</h1>
          <div class="phai">
            <div class="tim-kiem"><input type="search" id="tim-toan-cuc" placeholder="Tìm mã vận đơn… (demo)" aria-label="Tìm kiếm toàn cục (demo)"></div>
            <button class="nut nut-nho" id="nut-thong-bao" aria-label="Thông báo (demo)">🔔</button>
            <div class="avatar" title="Người dùng demo" aria-label="Người dùng demo">VD</div>
          </div>
        </header>
        <main class="trang" id="vung-chinh"></main>
      </div>`;
    body.prepend(khung);
    if (noiDungGoc) document.getElementById("vung-chinh").appendChild(noiDungGoc);

    const khay = document.createElement("div");
    khay.id = "toast-khay"; khay.setAttribute("aria-live", "polite");
    body.appendChild(khay);

    const nutMenu = document.getElementById("nut-menu");
    const sidebar = document.getElementById("sidebar");
    nutMenu.addEventListener("click", () => sidebar.classList.toggle("mo"));
    document.addEventListener("click", (e) => {
      if (sidebar.classList.contains("mo") && !sidebar.contains(e.target) && e.target !== nutMenu) sidebar.classList.remove("mo");
    });
    document.getElementById("nut-thong-bao").addEventListener("click", () =>
      VIP.toast("DEMO — trung tâm thông báo chưa kết nối hệ thống thật.", "canh-bao"));
    const timToanCuc = document.getElementById("tim-toan-cuc");
    timToanCuc.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && timToanCuc.value.trim()) {
        location.href = `${GOC}/pages/shipments.html?q=${encodeURIComponent(timToanCuc.value.trim())}`;
      }
    });
  }

  function toast(msg, loai) {
    const khay = document.getElementById("toast-khay");
    const t = document.createElement("div");
    t.className = "toast " + (loai || "thanh-cong");
    t.textContent = msg;
    khay.appendChild(t);
    setTimeout(() => { t.style.opacity = "0"; t.style.transition = "opacity .3s"; }, 3200);
    setTimeout(() => t.remove(), 3600);
  }

  function moModal(tieuDe, thanHTML, chanHTML) {
    dongModal();
    const nen = document.createElement("div");
    nen.className = "modal-nen mo"; nen.id = "modal-hien-tai";
    nen.setAttribute("role", "dialog"); nen.setAttribute("aria-modal", "true"); nen.setAttribute("aria-label", tieuDe);
    nen.innerHTML = `
      <div class="modal">
        <div class="modal-dau"><h3>${tieuDe}</h3><button class="dong" aria-label="Đóng">×</button></div>
        <div class="modal-than">${thanHTML}</div>
        ${chanHTML ? `<div class="modal-chan">${chanHTML}</div>` : ""}
      </div>`;
    document.body.appendChild(nen);
    nen.querySelector(".dong").addEventListener("click", dongModal);
    nen.addEventListener("click", (e) => { if (e.target === nen) dongModal(); });
    document.addEventListener("keydown", thoatModal);
    nen.querySelector(".dong").focus();
    return nen;
  }
  function thoatModal(e) { if (e.key === "Escape") dongModal(); }
  function dongModal() {
    const m = document.getElementById("modal-hien-tai");
    if (m) m.remove();
    document.removeEventListener("keydown", thoatModal);
  }

  async function taiMock(ten) {
    const res = await fetch(`${GOC}/mock/${ten}`);
    if (!res.ok) throw new Error(`Không tải được mock/${ten} (HTTP ${res.status})`);
    return ten.endsWith(".json") ? res.json() : res.text();
  }

  const tien = (n) => (n === 0 ? "0 ₫" : new Intl.NumberFormat("vi-VN").format(n) + " ₫");
  const huyHieuTT = (s) =>
    `<span class="huy-hieu ${TT_LOP[s.trang_thai] || "hh-xam"}">${s.trang_thai_ten}</span>`;
  const thoat = (x) => String(x == null ? "" : x).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ---- Biểu đồ canvas tự vẽ (không CDN) ---- */
  function veBieuDoCot(canvas, nhan, bo, mauBo) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight || 260;
    canvas.width = w * dpr; canvas.height = h * dpr;
    const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr);
    const padL = 46, padB = 34, padT = 14, padR = 8;
    const vw = w - padL - padR, vh = h - padT - padB;
    const max = Math.max(1, ...bo.flatMap(b => b.so));
    const buoc = buocDep(max);
    const maxTron = Math.ceil(max / buoc) * buoc;
    ctx.font = "11px -apple-system, sans-serif";
    ctx.fillStyle = "#6B7280"; ctx.strokeStyle = "#E2E5EA";
    for (let v = 0; v <= maxTron; v += buoc) {
      const y = padT + vh - (v / maxTron) * vh;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
      ctx.textAlign = "right"; ctx.fillText(gon(v), padL - 6, y + 3);
    }
    const nhomW = vw / nhan.length;
    const cotW = Math.min(26, (nhomW * 0.7) / bo.length);
    nhan.forEach((nh, i) => {
      const x0 = padL + i * nhomW + (nhomW - cotW * bo.length) / 2;
      bo.forEach((b, j) => {
        const cao = (b.so[i] / maxTron) * vh;
        ctx.fillStyle = mauBo[j];
        ctx.beginPath();
        ctx.roundRect(x0 + j * cotW, padT + vh - cao, cotW - 2, cao, 3);
        ctx.fill();
      });
      ctx.fillStyle = "#6B7280"; ctx.textAlign = "center";
      ctx.fillText(nh, padL + i * nhomW + nhomW / 2, h - padB + 16);
    });
  }

  function veBieuDoDuong(canvas, nhan, duLieu, mau) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight || 260;
    canvas.width = w * dpr; canvas.height = h * dpr;
    const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr);
    const padL = 46, padB = 30, padT = 14, padR = 10;
    const vw = w - padL - padR, vh = h - padT - padB;
    const max = Math.max(1, ...duLieu);
    const buoc = buocDep(max);
    const maxTron = Math.ceil(max / buoc) * buoc;
    ctx.font = "11px -apple-system, sans-serif";
    ctx.strokeStyle = "#E2E5EA"; ctx.fillStyle = "#6B7280";
    for (let v = 0; v <= maxTron; v += buoc) {
      const y = padT + vh - (v / maxTron) * vh;
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke();
      ctx.textAlign = "right"; ctx.fillText(gon(v), padL - 6, y + 3);
    }
    const toaDo = duLieu.map((v, i) => [
      padL + (i / Math.max(1, duLieu.length - 1)) * vw,
      padT + vh - (v / maxTron) * vh,
    ]);
    ctx.beginPath();
    toaDo.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
    ctx.strokeStyle = mau; ctx.lineWidth = 2.2; ctx.stroke();
    ctx.lineTo(toaDo[toaDo.length - 1][0], padT + vh);
    ctx.lineTo(toaDo[0][0], padT + vh);
    ctx.closePath();
    ctx.fillStyle = mau + "22"; ctx.fill();
    ctx.fillStyle = mau;
    toaDo.forEach(([x, y]) => { ctx.beginPath(); ctx.arc(x, y, 3, 0, 7); ctx.fill(); });
    ctx.fillStyle = "#6B7280"; ctx.textAlign = "center";
    const moi = Math.ceil(nhan.length / Math.max(2, Math.floor(vw / 46)));
    nhan.forEach((nh, i) => { if (i % moi === 0) ctx.fillText(nh, toaDo[i][0], h - padB + 16); });
  }

  function veBieuDoTron(canvas, phan, mau) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth, h = canvas.clientHeight || 220;
    canvas.width = w * dpr; canvas.height = h * dpr;
    const ctx = canvas.getContext("2d"); ctx.scale(dpr, dpr);
    const tong = phan.reduce((a, b) => a + b.so, 0) || 1;
    const cx = w / 2, cy = h / 2, r = Math.min(w, h) / 2 - 12;
    let goc = -Math.PI / 2;
    phan.forEach((p, i) => {
      const quet = (p.so / tong) * Math.PI * 2;
      ctx.beginPath(); ctx.moveTo(cx, cy);
      ctx.arc(cx, cy, r, goc, goc + quet);
      ctx.closePath(); ctx.fillStyle = mau[i % mau.length]; ctx.fill();
      goc += quet;
    });
    ctx.beginPath(); ctx.arc(cx, cy, r * 0.58, 0, 7); ctx.fillStyle = "#fff"; ctx.fill();
    ctx.fillStyle = "#1F2430"; ctx.font = "700 18px -apple-system, sans-serif"; ctx.textAlign = "center";
    ctx.fillText(String(tong), cx, cy + 2);
    ctx.font = "11px -apple-system, sans-serif"; ctx.fillStyle = "#6B7280";
    ctx.fillText("tổng", cx, cy + 18);
  }

  function buocDep(max) {
    const tho = max / 4;
    const luyThua = Math.pow(10, Math.floor(Math.log10(Math.max(1, tho))));
    for (const k of [1, 2, 5, 10]) if (tho <= k * luyThua) return k * luyThua;
    return 10 * luyThua;
  }
  const gon = (n) => (n >= 1e6 ? (n / 1e6).toFixed(1).replace(".0", "") + "tr" : n >= 1e3 ? (n / 1e3).toFixed(0) + "k" : String(n));

  window.VIP = {
    dungKhung, toast, moModal, dongModal, taiMock, tien, huyHieuTT, thoat,
    veBieuDoCot, veBieuDoDuong, veBieuDoTron, gon,
    MAU: ["#CC0000", "#1D4ED8", "#15803D", "#B45309", "#7C3AED", "#0E7490"],
  };
})();
