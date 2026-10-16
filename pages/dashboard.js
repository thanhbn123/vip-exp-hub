/* pages/dashboard.js — mã của trang `pages/dashboard.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("dashboard", "Dashboard");
let DON = [];
async function khoiDong() {
  try { DON = await VIP.taiMock("shipments.json"); }
  catch (e) {
    document.getElementById("khay-kpi").innerHTML =
      `<div class="hop-loi" style="grid-column:1/-1">Không tải được dữ liệu mô phỏng: ${VIP.thoat(e.message)}.<br>Hãy mở trang qua local server (xem README), không mở trực tiếp file.</div>`;
    return;
  }
  const hangs = [...new Map(DON.map(s => [s.hang, s.ten_hang]))];
  const sel = document.getElementById("loc-hang-db");
  hangs.forEach(([id, ten]) => sel.insertAdjacentHTML("beforeend", `<option value="${id}">${ten}</option>`));
  ["loc-ngay", "loc-hang-db"].forEach(id => document.getElementById(id).addEventListener("change", ve));
  ve();
}
function ve() {
  const soNgay = +document.getElementById("loc-ngay").value;
  const hang = document.getElementById("loc-hang-db").value;
  const moc = new Date("2026-10-14T23:59");
  const tu = new Date(moc); tu.setDate(tu.getDate() - soNgay + 1);
  const ds = DON.filter(s => {
    const d = new Date(s.ngay_tao.replace(" ", "T"));
    return d >= tu && (!hang || s.hang === hang);
  });
  const ok = ds.filter(s => s.trang_thai === "giao_thanh_cong");
  const fail = ds.filter(s => s.trang_thai === "giao_that_bai");
  const codThu = ok.reduce((a, s) => a + s.cod, 0);
  const daGiaoXong = ok.length + fail.length;
  document.getElementById("khay-kpi").innerHTML = `
    <div class="the kpi"><div class="nhan">Tổng đơn</div><div class="so">${ds.length}</div><div class="phu">trong ${soNgay} ngày (demo)</div></div>
    <div class="the kpi"><div class="nhan">Giao thành công</div><div class="so" style="color:var(--xanh-la)">${ok.length}</div>
      <div class="phu"><span class="tang">${daGiaoXong ? Math.round(ok.length / daGiaoXong * 100) : 0}%</span> trên đơn đã có kết quả</div></div>
    <div class="the kpi"><div class="nhan">Giao thất bại</div><div class="so" style="color:var(--do-vip)">${fail.length}</div>
      <div class="phu"><span class="giam">${daGiaoXong ? Math.round(fail.length / daGiaoXong * 100) : 0}%</span> trên đơn đã có kết quả</div></div>
    <div class="the kpi"><div class="nhan">COD đã thu (demo)</div><div class="so">${VIP.tien(codThu)}</div><div class="phu">từ ${ok.filter(s=>s.cod>0).length} đơn có COD</div></div>`;

  const nhanNgay = [], soNgayArr = [];
  for (let i = soNgay - 1; i >= 0; i--) {
    const d = new Date(moc); d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    nhanNgay.push(key.slice(8, 10) + "/" + key.slice(5, 7));
    soNgayArr.push(ds.filter(s => s.ngay_tao.startsWith(key)).length);
  }
  VIP.veBieuDoDuong(document.getElementById("bd-duong"), nhanNgay, soNgayArr, "#CC0000");

  const nhomTT = {};
  ds.forEach(s => { nhomTT[s.trang_thai_ten] = (nhomTT[s.trang_thai_ten] || 0) + 1; });
  const phan = Object.entries(nhomTT).map(([ten, so]) => ({ ten, so }));
  VIP.veBieuDoTron(document.getElementById("bd-tron"), phan, VIP.MAU);
  document.getElementById("cg-tron").innerHTML = phan.map((p, i) =>
    `<span><span class="cham" style="background:${VIP.MAU[i % VIP.MAU.length]}"></span>${p.ten}: <b>${p.so}</b></span>`).join("");

  const tenHang = [...new Map(DON.map(s => [s.hang, s.ten_hang]))];
  const nhanH = tenHang.map(([, t]) => t.replace(" Express", ""));
  VIP.veBieuDoCot(document.getElementById("bd-cot"), nhanH, [
    { so: tenHang.map(([id]) => ds.filter(s => s.hang === id && s.trang_thai === "giao_thanh_cong").length) },
    { so: tenHang.map(([id]) => ds.filter(s => s.hang === id && s.trang_thai === "giao_that_bai").length) },
  ], ["#15803D", "#CC0000"]);

  document.getElementById("bang-moi-nhat").innerHTML = ds.slice(0, 7).map(s => `
    <tr><td><a href="shipments.html?q=${s.ma_van_don}">${s.ma_van_don}</a></td>
    <td>${s.ten_hang}</td><td>${VIP.huyHieuTT(s)}</td><td class="so-tien">${VIP.tien(s.cod)}</td></tr>`).join("")
    || `<tr><td colspan="4"><div class="trang-thai-rong"><div class="to">📭</div>Không có đơn trong bộ lọc này</div></td></tr>`;
}
let hgio; window.addEventListener("resize", () => { clearTimeout(hgio); hgio = setTimeout(ve, 200); });
khoiDong();
