/* pages/reports.js — mã của trang `pages/reports.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("reports", "Báo cáo đa hãng");
let DON = [];
async function khoiDong() {
  try { DON = await VIP.taiMock("shipments.json"); }
  catch (e) { document.getElementById("bang-tong").innerHTML = `<tr><td colspan="5"><div class="hop-loi">Không tải được dữ liệu: ${VIP.thoat(e.message)}</div></td></tr>`; return; }
  document.getElementById("loc-ngay").addEventListener("change", ve);
  ve();
}
function ve() {
  const soNgay = +document.getElementById("loc-ngay").value;
  const moc = new Date("2026-10-14T23:59");
  const tu = new Date(moc); tu.setDate(tu.getDate() - soNgay + 1);
  const ds = DON.filter(s => new Date(s.ngay_tao.replace(" ", "T")) >= tu);
  const hangs = [...new Map(DON.map(s => [s.hang, s.ten_hang]))];
  const nhan = hangs.map(([, t]) => t.replace(" Express", ""));
  const tong = hangs.map(([id]) => ds.filter(s => s.hang === id).length);
  const ok = hangs.map(([id]) => ds.filter(s => s.hang === id && s.trang_thai === "giao_thanh_cong").length);
  const fail = hangs.map(([id]) => ds.filter(s => s.hang === id && s.trang_thai === "giao_that_bai").length);
  const cod = hangs.map(([id]) => ds.filter(s => s.hang === id && s.trang_thai === "giao_thanh_cong").reduce((a, s) => a + s.cod, 0));
  VIP.veBieuDoCot(document.getElementById("bd-hang"), nhan, [{ so: tong }, { so: ok }, { so: fail }], ["#1D4ED8", "#15803D", "#CC0000"]);
  VIP.veBieuDoCot(document.getElementById("bd-cod"), nhan, [{ so: cod }], ["#B45309"]);
  document.getElementById("bang-tong").innerHTML = hangs.map(([id, ten], i) => `
    <tr><td><b>${ten}</b></td><td class="so-tien">${tong[i]}</td><td class="so-tien">${ok[i]}</td>
    <td class="so-tien">${tong[i] ? Math.round(ok[i] / tong[i] * 100) : 0}%</td>
    <td class="so-tien">${VIP.tien(cod[i])}</td></tr>`).join("") +
    `<tr style="font-weight:700;background:var(--xam-nhat)"><td>Tổng</td><td class="so-tien">${ds.length}</td>
    <td class="so-tien">${ok.reduce((a, b) => a + b, 0)}</td><td class="so-tien">—</td>
    <td class="so-tien">${VIP.tien(cod.reduce((a, b) => a + b, 0))}</td></tr>`;
}
let hgio; window.addEventListener("resize", () => { clearTimeout(hgio); hgio = setTimeout(ve, 200); });
khoiDong();
