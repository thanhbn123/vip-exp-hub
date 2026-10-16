/* pages/pricing.js — mã của trang `pages/pricing.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("pricing", "So sánh cước");
// Hệ số hoàn toàn hư cấu, chỉ để demo UI — không phải biểu cước thật của hãng nào.
const BIEU_DEMO = [
  { ten: "Viettel Post", goc: 16000, moi500g: 4500, heSo: { "noi-tinh": 0.8, "noi-mien": 1, "lien-mien": 1.35 }, gio: [24, 48] },
  { ten: "GHN", goc: 15500, moi500g: 5000, heSo: { "noi-tinh": 0.85, "noi-mien": 1, "lien-mien": 1.3 }, gio: [24, 48] },
  { ten: "GHTK", goc: 14500, moi500g: 5500, heSo: { "noi-tinh": 0.8, "noi-mien": 1, "lien-mien": 1.4 }, gio: [36, 60] },
  { ten: "J&T Express", goc: 15000, moi500g: 5200, heSo: { "noi-tinh": 0.85, "noi-mien": 1, "lien-mien": 1.32 }, gio: [36, 60] },
  { ten: "BEST Express", goc: 14000, moi500g: 5800, heSo: { "noi-tinh": 0.9, "noi-mien": 1, "lien-mien": 1.38 }, gio: [48, 72] },
];
document.getElementById("nut-tinh").addEventListener("click", () => {
  const kl = Number(document.getElementById("t-kl").value);
  const vung = document.getElementById("t-vung").value;
  if (!(kl > 0)) { VIP.toast("Cân nặng phải lớn hơn 0.", "loi"); return; }
  const kq = BIEU_DEMO.map(b => ({
    ten: b.ten,
    cuoc: Math.round((b.goc + Math.max(0, Math.ceil(kl / 500) - 1) * b.moi500g) * b.heSo[vung] / 500) * 500,
    gio: b.gio,
  })).sort((a, b) => a.cuoc - b.cuoc);
  document.getElementById("bang-cuoc").innerHTML = kq.map((r, i) => `
    <tr><td><b>${r.ten}</b>${i === 0 ? ' <span class="huy-hieu hh-xanh">rẻ nhất (minh họa)</span>' : ""}</td>
    <td class="so-tien">${VIP.tien(r.cuoc)}</td>
    <td>${r.gio[0]}–${r.gio[1]} giờ</td>
    <td style="color:var(--chu-mo);font-size:12px">Số liệu hư cấu — không phải báo giá thực</td></tr>`).join("");
  VIP.toast("DEMO: cước hiển thị là minh họa, không phải báo giá thực.", "canh-bao");
});
