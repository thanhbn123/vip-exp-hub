/* pages/settings.js — mã của trang `pages/settings.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("settings", "Cấu hình hệ thống");
const ND = [
  { ten: "Quản trị demo", email: "quantri@vi-du-demo.test", vaiTro: "Quản trị", bat: true },
  { ten: "Vận hành demo 1", email: "vanhanh1@vi-du-demo.test", vaiTro: "Vận hành", bat: true },
  { ten: "Kế toán demo", email: "ketoan@vi-du-demo.test", vaiTro: "Kế toán (chỉ xem COD)", bat: true },
  { ten: "CTV demo", email: "ctv@vi-du-demo.test", vaiTro: "Chỉ xem", bat: false },
];
document.querySelectorAll(".tab-nut").forEach(n => n.addEventListener("click", () => {
  document.querySelectorAll(".tab-nut").forEach(x => { x.classList.remove("hien-tai"); x.setAttribute("aria-selected", "false"); });
  n.classList.add("hien-tai"); n.setAttribute("aria-selected", "true");
  document.querySelectorAll(".noi-dung-tab").forEach(t => t.hidden = true);
  document.getElementById("tab-" + n.dataset.tab).hidden = false;
}));
function veND() {
  document.getElementById("bang-nd").innerHTML = ND.map((u, i) => `
    <tr><td><b>${VIP.thoat(u.ten)}</b></td><td>${VIP.thoat(u.email)}</td><td>${VIP.thoat(u.vaiTro)}</td>
    <td>${u.bat ? '<span class="huy-hieu hh-xanh">Hoạt động</span>' : '<span class="huy-hieu hh-xam">Tạm khóa</span>'}</td>
    <td><button class="nut nut-nho" data-doi="${i}">${u.bat ? "Khóa demo" : "Mở demo"}</button></td></tr>`).join("");
  document.querySelectorAll("[data-doi]").forEach(b => b.addEventListener("click", () => {
    ND[+b.dataset.doi].bat = !ND[+b.dataset.doi].bat;
    veND(); VIP.toast("DEMO: đã đổi trạng thái người dùng (chỉ trong phiên này).");
  }));
}
document.getElementById("them-nd").addEventListener("click", () => {
  ND.push({ ten: `Người dùng demo ${ND.length + 1}`, email: `demo${ND.length + 1}@vi-du-demo.test`, vaiTro: "Chỉ xem", bat: true });
  veND(); VIP.toast("DEMO: đã thêm người dùng hư cấu.");
});
["luu-chung", "luu-tb"].forEach(id => document.getElementById(id).addEventListener("click", () =>
  VIP.toast("DEMO: đã mô phỏng lưu cấu hình. Chưa có backend ở G00.")));
veND();
