/* pages/webhooks.js — mã của trang `pages/webhooks.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("webhooks", "Webhook Center");

/* CSP `script-src 'self'` chặn CẢ thuộc tính `onclick="…"` (không chỉ thẻ <script> nội tuyến),
   nên nút "Đóng" ở chân hộp thoại là nút CHẾT ở bản cũ. Một bộ nghe UỶ NHIỆM thay cho nó:
   một chỗ, nghe mọi nút mang `data-dong-hop` — kể cả nút vừa được chèn vào sau. */
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-dong-hop]")) VIP.dongModal();
});
const TT_XL = {
  thanh_cong: '<span class="huy-hieu hh-xanh">Thành công</span>',
  loi: '<span class="huy-hieu hh-do">Lỗi</span>',
  dang_cho: '<span class="huy-hieu hh-vang">Đang chờ</span>',
};
let SK = [], trang = 1; const MOI_TRANG = 12;
const GW = "http://127.0.0.1:8898";
const nguonLa = () => document.getElementById("nguon").value;
const khoaAPI = () => document.getElementById("khoa-api").value.trim();

async function goiGW(duong, method) {
  const res = await fetch(GW + duong, { method: method || "GET", headers: { "X-API-Key": khoaAPI() } });
  const kq = await res.json();
  if (!res.ok) throw new Error(kq.loi || ("HTTP " + res.status));
  return kq;
}
// Ánh xạ trạng thái gateway → ba nhóm hiển thị của trang
const GW_TT = { xong: "thanh_cong", dlq: "loi", cho_thu_lai: "loi", moi: "dang_cho", dang_xu_ly: "dang_cho" };
const TEN_HANG_GW = { vtp: "Viettel Post", ghn: "GHN", ghtk: "GHTK", jt: "J&T Express", best: "BEST Express" };

async function taiGateway() {
  const kq = await goiGW("/api/su-kien?gioi_han=500");
  SK = kq.su_kien.map(s => ({
    id: "GW-" + s.id, gw_id: s.id,
    hang: s.hang, ten_hang: TEN_HANG_GW[s.hang] || s.hang,
    loai: s.trang_thai, loai_ten: s.event_id,
    ma_van_don: (s.event_id || "").replace(/-[a-z_]+$/, ""),
    trang_thai_xu_ly: GW_TT[s.trang_thai] || "dang_cho",
    so_lan_thu: s.so_lan_thu, thoi_gian: s.nhan_luc,
    loi_cuoi: s.loi_cuoi, gw_trang_thai: s.trang_thai,
  }));
}
async function khoiDong() {
  try {
    if (nguonLa() === "gateway") await taiGateway();
    else SK = await VIP.taiMock("webhook-events.json");
  } catch (e) {
    document.getElementById("bang-sk").innerHTML = `<tr><td colspan="8"><div class="hop-loi">Không tải được dữ liệu: ${VIP.thoat(e.message)}${nguonLa() === "gateway" ? "<br>Gateway G01 chưa chạy? Khởi động: <code>python3 gateway/server.py</code> rồi bắn demo: <code>python3 gateway/mo_phong_hang.py</code>" : ""}</div></td></tr>`;
    document.getElementById("kpi-wh").innerHTML = "";
    return;
  }
  const selH = document.getElementById("loc-hang");
  selH.querySelectorAll("option:not(:first-child)").forEach(o => o.remove());
  const hangs = [...new Map(SK.map(s => [s.hang, s.ten_hang]))];
  hangs.forEach(([id, ten]) => selH.insertAdjacentHTML("beforeend", `<option value="${id}">${ten}</option>`));
  veKPI(); ve();
}
document.getElementById("nguon").addEventListener("change", () => {
  document.getElementById("khoa-api").style.display = nguonLa() === "gateway" ? "" : "none";
  trang = 1; khoiDong();
});
document.getElementById("khoa-api").addEventListener("change", () => { if (nguonLa() === "gateway") khoiDong(); });
["loc-hang", "loc-tt"].forEach(id => document.getElementById(id).addEventListener("change", () => { trang = 1; ve(); }));
document.getElementById("loc-ma").addEventListener("input", () => { trang = 1; ve(); });
function veKPI() {
  const ok = SK.filter(s => s.trang_thai_xu_ly === "thanh_cong").length;
  const loi = SK.filter(s => s.trang_thai_xu_ly === "loi").length;
  const cho = SK.filter(s => s.trang_thai_xu_ly === "dang_cho").length;
  document.getElementById("kpi-wh").innerHTML = `
    <div class="the kpi"><div class="nhan">Tổng sự kiện (demo)</div><div class="so">${SK.length}</div></div>
    <div class="the kpi"><div class="nhan">Xử lý thành công</div><div class="so" style="color:var(--xanh-la)">${ok}</div></div>
    <div class="the kpi"><div class="nhan">Lỗi</div><div class="so" style="color:var(--do-vip)">${loi}</div></div>
    <div class="the kpi"><div class="nhan">Đang chờ</div><div class="so" style="color:var(--vang)">${cho}</div></div>`;
}
function locDS() {
  const h = document.getElementById("loc-hang").value;
  const t = document.getElementById("loc-tt").value;
  const m = document.getElementById("loc-ma").value.trim().toLowerCase();
  return SK.filter(s => (!h || s.hang === h) && (!t || s.trang_thai_xu_ly === t) && (!m || s.ma_van_don.toLowerCase().includes(m)));
}
function ve() {
  const ds = locDS();
  const tong = Math.max(1, Math.ceil(ds.length / MOI_TRANG));
  trang = Math.min(trang, tong);
  const hien = ds.slice((trang - 1) * MOI_TRANG, trang * MOI_TRANG);
  document.getElementById("dem-sk").textContent = `${ds.length} sự kiện`;
  document.getElementById("bang-sk").innerHTML = hien.map(s => `
    <tr><td><b>${s.id}</b></td><td style="white-space:nowrap">${s.thoi_gian}</td><td>${s.ten_hang}</td>
    <td>${s.loai_ten}</td><td>${s.ma_van_don}</td><td>${TT_XL[s.trang_thai_xu_ly]}</td>
    <td style="text-align:center">${s.so_lan_thu}</td>
    <td style="white-space:nowrap">
      <button class="nut nut-nho" data-xem="${s.id}">Chi tiết</button>
      ${s.trang_thai_xu_ly === "loi" ? `<button class="nut nut-nho" data-retry="${s.id}">Retry</button>` : ""}
      <button class="nut nut-nho" data-replay="${s.id}">Replay</button>
    </td></tr>`).join("")
    || `<tr><td colspan="8"><div class="trang-thai-rong"><div class="to">🔍</div>Không có sự kiện khớp bộ lọc</div></td></tr>`;
  const pt = document.getElementById("pt-sk");
  pt.innerHTML = `<span class="thong-tin">Trang ${trang}/${tong}</span>
    <button id="pt-truoc" ${trang === 1 ? "disabled" : ""}>←</button>
    ${Array.from({ length: tong }, (_, i) => `<button data-tr="${i + 1}" class="${i + 1 === trang ? "hien-tai" : ""}">${i + 1}</button>`).join("")}
    <button id="pt-sau" ${trang === tong ? "disabled" : ""}>→</button>`;
  pt.querySelector("#pt-truoc").addEventListener("click", () => { trang--; ve(); });
  pt.querySelector("#pt-sau").addEventListener("click", () => { trang++; ve(); });
  pt.querySelectorAll("[data-tr]").forEach(b => b.addEventListener("click", () => { trang = +b.dataset.tr; ve(); }));
  document.querySelectorAll("[data-xem]").forEach(b => b.addEventListener("click", () => xemChiTiet(b.dataset.xem)));
  document.querySelectorAll("[data-retry]").forEach(b => b.addEventListener("click", () => moPhong("Retry", b.dataset.retry)));
  document.querySelectorAll("[data-replay]").forEach(b => b.addEventListener("click", () => moPhong("Replay", b.dataset.replay)));
}
async function xemChiTiet(id) {
  const s = SK.find(x => x.id === id);
  if (s.gw_id != null) {
    try {
      const ct = await goiGW("/api/su-kien/" + s.gw_id);
      let payload = ct.payload_tho;
      try { payload = JSON.stringify(JSON.parse(ct.payload_tho), null, 2); } catch {}
      VIP.moModal(`Sự kiện GW-${ct.id} <span class="tag-demo">GATEWAY G01</span>`,
        `<p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Sự kiện thô lưu bền trong SQLite. Hãng: <b>${VIP.thoat(s.ten_hang)}</b> · nhận ${VIP.thoat(ct.nhan_luc)} · trạng thái <b>${VIP.thoat(ct.trang_thai)}</b>${ct.loi_cuoi ? " · lỗi: " + VIP.thoat(ct.loi_cuoi) : ""}</p>
         <pre class="json-xem">${VIP.thoat(payload)}</pre>`,
        `<button class="nut" data-dong-hop="1">Đóng</button>`);
    } catch (e) { VIP.toast("Gateway: " + e.message, "loi"); }
    return;
  }
  VIP.moModal(`Sự kiện ${s.id} — ${s.loai_ten} <span class="tag-demo">DEMO</span>`,
    `<p style="margin-top:0;font-size:12.5px;color:var(--chu-mo)">Payload mô phỏng, thông tin cá nhân đã được che. Hãng: <b>${s.ten_hang}</b> · ${s.thoi_gian}</p>
     <pre class="json-xem">${VIP.thoat(JSON.stringify(s.payload, null, 2))}</pre>`,
    `<button class="nut" data-dong-hop="1">Đóng</button>`);
}
function moPhong(loai, id) {
  const s = SK.find(x => x.id === id);
  if (s.gw_id != null) {
    // Nguồn gateway: replay THẬT vào gateway local — server kiểm quyền admin + ghi audit.
    goiGW(`/api/su-kien/${s.gw_id}/replay`, "POST")
      .then(() => { VIP.toast(`Gateway: đã nạp lại sự kiện GW-${s.gw_id} (có audit).`); setTimeout(khoiDong, 600); })
      .catch(e => VIP.toast("Gateway từ chối: " + e.message + (khoaAPI() !== "demo-admin-key" ? " — replay cần khóa admin (demo-admin-key)" : ""), "loi"));
    return;
  }
  const m = VIP.moModal(`${loai} sự kiện ${id} (DEMO)`,
    `<p>Thao tác <b>${loai}</b> trên nguồn mock chỉ là <b>mô phỏng</b> — không gửi lại yêu cầu nào tới hệ thống thật.</p>
     <p>Muốn xem retry/replay thật (local): đổi "Nguồn" sang <b>Gateway local G01</b>.</p>`,
    `<button class="nut" id="mp-huy">Hủy</button><button class="nut nut-chinh" id="mp-ok">Chạy ${loai} demo</button>`);
  m.querySelector("#mp-huy").addEventListener("click", VIP.dongModal);
  m.querySelector("#mp-ok").addEventListener("click", () => {
    VIP.dongModal();
    if (loai === "Retry" && s.trang_thai_xu_ly === "loi") { s.trang_thai_xu_ly = "thanh_cong"; s.so_lan_thu += 1; veKPI(); ve(); }
    VIP.toast(`DEMO: đã mô phỏng ${loai} cho ${id}.`);
  });
}
khoiDong();
