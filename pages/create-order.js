/* pages/create-order.js — mã của trang `pages/create-order.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("create-order", "Tạo đơn vận chuyển");
const KHOA_NHAP = "vip_g00_nhap_don";
function layNhap() { try { return JSON.parse(localStorage.getItem(KHOA_NHAP) || "[]"); } catch { return []; } }
function veNhap() {
  const ds = layNhap();
  document.getElementById("bang-nhap").innerHTML = ds.map(n => `
    <tr><td style="white-space:nowrap">${n.luc}</td><td>${VIP.thoat(n.nguoi_nhan)}<br><span style="color:var(--chu-mo);font-size:12px">${VIP.thoat(n.sdt)}</span></td>
    <td>${VIP.thoat(n.hang_hoa)} (${n.kl} g)</td><td class="so-tien">${VIP.tien(n.cod)}</td><td>${VIP.thoat(n.hang)}</td></tr>`).join("")
    || `<tr><td colspan="5"><div class="trang-thai-rong"><div class="to">📝</div>Chưa có nháp nào — điền form bên trên rồi lưu thử</div></td></tr>`;
}
function kiemTruong(nhom) {
  const inp = nhom.querySelector("input, select, textarea");
  const v = inp.value.trim();
  let hopLe = true;
  if (inp.required && !v) hopLe = false;
  else if (nhom.dataset.kieu === "sdt" && !/^0\d{9}$/.test(v.replace(/[\s.]/g, ""))) hopLe = false;
  else if (nhom.dataset.kieu === "so-duong" && !(Number(v) > 0)) hopLe = false;
  else if (nhom.dataset.kieu === "so-khong-am" && (v !== "" && (Number.isNaN(Number(v)) || Number(v) < 0))) hopLe = false;
  nhom.classList.toggle("co-loi", !hopLe);
  return hopLe;
}
document.querySelectorAll("[data-truong]").forEach(nhom => {
  nhom.querySelector("input, select, textarea").addEventListener("blur", () => kiemTruong(nhom));
});
document.getElementById("form-don").addEventListener("submit", (e) => {
  e.preventDefault();
  const cacNhom = [...document.querySelectorAll("[data-truong]")];
  const hong = cacNhom.filter(n => !kiemTruong(n));
  if (hong.length) {
    hong[0].querySelector("input, select, textarea").focus();
    VIP.toast(`Còn ${hong.length} trường chưa hợp lệ.`, "loi");
    return;
  }
  const nhap = {
    luc: new Date().toLocaleString("vi-VN"),
    nguoi_nhan: document.getElementById("n-ten").value.trim(),
    sdt: document.getElementById("n-sdt").value.trim(),
    hang_hoa: document.getElementById("h-ten").value.trim(),
    kl: Number(document.getElementById("h-kl").value),
    cod: Number(document.getElementById("h-cod").value || 0),
    hang: document.getElementById("h-hang").value,
  };
  const ds = layNhap(); ds.unshift(nhap);
  try { localStorage.setItem(KHOA_NHAP, JSON.stringify(ds.slice(0, 20))); } catch {}
  veNhap();
  VIP.toast("DEMO: đã lưu nháp trong trình duyệt. Không có API nào được gọi.");
});
document.getElementById("nut-xoa-form").addEventListener("click", () => {
  document.getElementById("form-don").reset();
  document.querySelectorAll(".co-loi").forEach(n => n.classList.remove("co-loi"));
});
document.getElementById("nut-xoa-nhap").addEventListener("click", () => {
  try { localStorage.removeItem(KHOA_NHAP); } catch {}
  veNhap(); VIP.toast("Đã xóa nháp demo trong trình duyệt.", "canh-bao");
});
veNhap();
