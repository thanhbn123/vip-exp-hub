/* pages/cod.js — mã của trang `pages/cod.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("cod", "Đối soát COD");
let DS = [];
async function khoiDong() {
  let don;
  try { don = await VIP.taiMock("shipments.json"); }
  catch (e) { document.getElementById("kpi-cod").innerHTML = `<div class="hop-loi" style="grid-column:1/-1">Không tải được dữ liệu: ${VIP.thoat(e.message)}</div>`; return; }
  // Dựng dòng COD mô phỏng từ các đơn giao thành công có COD.
  DS = don.filter(s => s.trang_thai === "giao_thanh_cong" && s.cod > 0).map((s, i) => {
    const daDoiSoat = i % 3 !== 0;
    const lech = i % 7 === 0 ? -s.cuoc_phi : 0; // vài dòng cố ý lệch để demo
    return {
      ma: s.ma_van_don, hang: s.hang, ten_hang: s.ten_hang,
      phai_thu: s.cod,
      da_nhan: daDoiSoat ? s.cod - s.cuoc_phi + lech : 0,
      phi: s.cuoc_phi, da_doi_soat: daDoiSoat, lech,
    };
  });
  [...new Map(DS.map(s => [s.hang, s.ten_hang]))].forEach(([id, ten]) =>
    document.getElementById("loc-hang").insertAdjacentHTML("beforeend", `<option value="${id}">${ten}</option>`));
  ["loc-hang", "loc-ds"].forEach(id => document.getElementById(id).addEventListener("change", ve));
  document.getElementById("nut-doi-soat").addEventListener("click", chayDoiSoat);
  ve();
}
function ve() {
  const h = document.getElementById("loc-hang").value;
  const d = document.getElementById("loc-ds").value;
  const ds = DS.filter(r => (!h || r.hang === h) && (!d || (d === "da") === r.da_doi_soat));
  const phaiThu = ds.reduce((a, r) => a + r.phai_thu, 0);
  const daNhan = ds.reduce((a, r) => a + r.da_nhan, 0);
  const phi = ds.filter(r => r.da_doi_soat).reduce((a, r) => a + r.phi, 0);
  const lech = ds.reduce((a, r) => a + r.lech, 0);
  document.getElementById("kpi-cod").innerHTML = `
    <div class="the kpi"><div class="nhan">COD phải thu (demo)</div><div class="so">${VIP.tien(phaiThu)}</div><div class="phu">${ds.length} vận đơn</div></div>
    <div class="the kpi"><div class="nhan">Đã nhận về (demo)</div><div class="so" style="color:var(--xanh-la)">${VIP.tien(daNhan)}</div></div>
    <div class="the kpi"><div class="nhan">Phí hãng đã trừ</div><div class="so">${VIP.tien(phi)}</div></div>
    <div class="the kpi"><div class="nhan">Chênh lệch cần xử lý</div><div class="so" style="color:${lech ? "var(--do-vip)" : "var(--xanh-la)"}">${VIP.tien(Math.abs(lech))}</div>
      <div class="phu">${lech ? ds.filter(r => r.lech).length + " dòng lệch (demo)" : "không lệch"}</div></div>`;
  document.getElementById("bang-cod").innerHTML = ds.map(r => `
    <tr><td><b>${r.ma}</b></td><td>${r.ten_hang}</td>
    <td class="so-tien">${VIP.tien(r.phai_thu)}</td>
    <td class="so-tien">${r.da_doi_soat ? VIP.tien(r.da_nhan) : "—"}</td>
    <td class="so-tien">${r.da_doi_soat ? VIP.tien(r.phi) : "—"}</td>
    <td class="so-tien" style="color:${r.lech ? "var(--do-dam)" : "inherit"}">${r.da_doi_soat ? VIP.tien(r.lech) : "—"}</td>
    <td>${r.da_doi_soat ? '<span class="huy-hieu hh-xanh">Đã đối soát (demo)</span>' : '<span class="huy-hieu hh-vang">Chưa đối soát</span>'}</td></tr>`).join("")
    || `<tr><td colspan="7"><div class="trang-thai-rong"><div class="to">🧾</div>Không có dòng COD khớp bộ lọc</div></td></tr>`;
}
function chayDoiSoat() {
  const chua = DS.filter(r => !r.da_doi_soat);
  if (!chua.length) { VIP.toast("Mọi dòng đều đã đối soát (demo).", "canh-bao"); return; }
  const m = VIP.moModal("Chạy đối soát (DEMO)",
    `<p>Sẽ <b>mô phỏng</b> đối soát <b>${chua.length}</b> dòng chưa đối soát. Không có dữ liệu nào gửi tới hãng hay hệ thống kế toán thật.</p>`,
    `<button class="nut" id="ds-huy">Hủy</button><button class="nut nut-chinh" id="ds-ok">Chạy demo</button>`);
  m.querySelector("#ds-huy").addEventListener("click", VIP.dongModal);
  m.querySelector("#ds-ok").addEventListener("click", () => {
    chua.forEach(r => { r.da_doi_soat = true; r.da_nhan = r.phai_thu - r.phi; });
    VIP.dongModal(); ve();
    VIP.toast(`DEMO: đã mô phỏng đối soát ${chua.length} dòng.`);
  });
}
khoiDong();
