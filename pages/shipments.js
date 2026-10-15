/* pages/shipments.js — mã của trang `pages/shipments.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("shipments", "Vận đơn");

/* CSP `script-src 'self'` chặn CẢ thuộc tính `onclick="…"` (không chỉ thẻ <script> nội tuyến),
   nên nút "Đóng" ở chân hộp thoại là nút CHẾT ở bản cũ. Một bộ nghe UỶ NHIỆM thay cho nó:
   một chỗ, nghe mọi nút mang `data-dong-hop` — kể cả nút vừa được chèn vào sau. */
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-dong-hop]")) VIP.dongModal();
});
let DS = [], trang = 1; const MOI_TRANG = 10;
async function khoiDong() {
  try { DS = await VIP.taiMock("shipments.json"); }
  catch (e) {
    document.getElementById("bang").innerHTML = `<tr><td colspan="10"><div class="hop-loi">Không tải được dữ liệu: ${VIP.thoat(e.message)}. Hãy chạy qua local server (xem README).</div></td></tr>`;
    return;
  }
  [...new Map(DS.map(s => [s.hang, s.ten_hang]))].forEach(([id, ten]) =>
    document.getElementById("loc-hang").insertAdjacentHTML("beforeend", `<option value="${id}">${ten}</option>`));
  [...new Map(DS.map(s => [s.trang_thai, s.trang_thai_ten]))].forEach(([id, ten]) =>
    document.getElementById("loc-tt").insertAdjacentHTML("beforeend", `<option value="${id}">${ten}</option>`));
  const q = new URLSearchParams(location.search).get("q");
  if (q) document.getElementById("tim").value = q;
  document.getElementById("tim").addEventListener("input", () => { trang = 1; ve(); });
  ["loc-hang", "loc-tt"].forEach(id => document.getElementById(id).addEventListener("change", () => { trang = 1; ve(); }));
  ve();
}
function ve() {
  const q = document.getElementById("tim").value.trim().toLowerCase();
  const h = document.getElementById("loc-hang").value;
  const t = document.getElementById("loc-tt").value;
  const ds = DS.filter(s =>
    (!h || s.hang === h) && (!t || s.trang_thai === t) &&
    (!q || [s.ma_don, s.ma_van_don, s.nguoi_nhan, s.sdt_nhan].some(x => x.toLowerCase().includes(q))));
  const tong = Math.max(1, Math.ceil(ds.length / MOI_TRANG));
  trang = Math.min(trang, tong);
  const hien = ds.slice((trang - 1) * MOI_TRANG, trang * MOI_TRANG);
  document.getElementById("dem").textContent = `${ds.length} đơn`;
  document.getElementById("bang").innerHTML = hien.map(s => `
    <tr><td><b>${s.ma_don}</b></td><td>${s.ma_van_don}</td><td>${s.ten_hang}</td>
    <td>${VIP.thoat(s.nguoi_nhan)}<br><span style="color:var(--chu-mo);font-size:12px">${s.sdt_nhan}</span></td>
    <td style="max-width:200px">${VIP.thoat(s.dia_chi)}</td>
    <td class="so-tien">${VIP.tien(s.cod)}</td><td class="so-tien">${VIP.tien(s.cuoc_phi)}</td>
    <td>${VIP.huyHieuTT(s)}</td><td style="white-space:nowrap">${s.ngay_tao}</td>
    <td><button class="nut nut-nho" data-xem="${s.ma_don}">Chi tiết</button></td></tr>`).join("")
    || `<tr><td colspan="10"><div class="trang-thai-rong"><div class="to">🔍</div>Không tìm thấy vận đơn khớp bộ lọc</div></td></tr>`;
  const pt = document.getElementById("pt");
  const nutSo = [];
  for (let i = 1; i <= tong; i++) if (i === 1 || i === tong || Math.abs(i - trang) <= 2) nutSo.push(i);
  const daDanh = [...new Set(nutSo)];
  pt.innerHTML = `<span class="thong-tin">Hiển thị ${hien.length ? (trang - 1) * MOI_TRANG + 1 : 0}–${(trang - 1) * MOI_TRANG + hien.length} / ${ds.length}</span>
    <button id="truoc" ${trang === 1 ? "disabled" : ""} aria-label="Trang trước">←</button>
    ${daDanh.map((n, i) => (i && n - daDanh[i - 1] > 1 ? "<span>…</span>" : "") +
      `<button data-tr="${n}" class="${n === trang ? "hien-tai" : ""}">${n}</button>`).join("")}
    <button id="sau" ${trang === tong ? "disabled" : ""} aria-label="Trang sau">→</button>`;
  pt.querySelector("#truoc").addEventListener("click", () => { trang--; ve(); });
  pt.querySelector("#sau").addEventListener("click", () => { trang++; ve(); });
  pt.querySelectorAll("[data-tr]").forEach(b => b.addEventListener("click", () => { trang = +b.dataset.tr; ve(); }));
  document.querySelectorAll("[data-xem]").forEach(b => b.addEventListener("click", () => chiTiet(b.dataset.xem)));
}
function chiTiet(ma) {
  const s = DS.find(x => x.ma_don === ma);
  VIP.moModal(`Vận đơn ${s.ma_van_don} <span class="tag-demo">DEMO</span>`, `
    <table class="bang"><tbody>
      <tr><td style="width:160px;color:var(--chu-mo)">Mã đơn nội bộ</td><td><b>${s.ma_don}</b></td></tr>
      <tr><td style="color:var(--chu-mo)">Hãng vận chuyển</td><td>${s.ten_hang}</td></tr>
      <tr><td style="color:var(--chu-mo)">Người nhận</td><td>${VIP.thoat(s.nguoi_nhan)} — ${s.sdt_nhan}</td></tr>
      <tr><td style="color:var(--chu-mo)">Địa chỉ</td><td>${VIP.thoat(s.dia_chi)}</td></tr>
      <tr><td style="color:var(--chu-mo)">Hàng hóa</td><td>${VIP.thoat(s.san_pham)} (${s.khoi_luong_gram} g)</td></tr>
      <tr><td style="color:var(--chu-mo)">COD / Cước</td><td>${VIP.tien(s.cod)} / ${VIP.tien(s.cuoc_phi)}</td></tr>
      <tr><td style="color:var(--chu-mo)">Trạng thái</td><td>${VIP.huyHieuTT(s)}</td></tr>
      <tr><td style="color:var(--chu-mo)">Tạo / cập nhật</td><td>${s.ngay_tao} / ${s.ngay_cap_nhat}</td></tr>
    </tbody></table>
    <p style="font-size:12px;color:var(--chu-mo)">Dữ liệu hư cấu phục vụ demo G00 — không phải vận đơn thật.</p>`,
    `<button class="nut" data-dong-hop="1">Đóng</button>`);
}
khoiDong();
