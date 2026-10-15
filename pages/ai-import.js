/* pages/ai-import.js — mã của trang `pages/ai-import.html`, TÁCH RA KHỎI HTML.
   VÌ SAO: CSP của máy chủ (`app/server.py`) là `script-src 'self'` — KHÔNG có 'unsafe-inline'.
   Mọi `<script>` nội tuyến bị trình duyệt TỪ CHỐI CHẠY ("Refused to execute inline script…"),
   nên bản cũ của trang này hiện ra KHUNG RỖNG: `VIP.dungKhung()` không chạy, bảng không có
   dòng nào, nút không có ai nghe. Đây là cách `pages/carriers.html` đã làm từ G17 và là cách
   chín trang còn lại được sửa ở G19 (AG-06) theo quyết định của AG-00.
   NỘI DUNG DƯỚI ĐÂY LÀ BẢN CHUYỂN NGUYÊN VĂN của khối `<script>` cũ — không sửa logic. */
VIP.dungKhung("ai-import", "AI Import");
const TRUONG_CHUAN = [
  { key: "recipient_name", ten: "Tên người nhận", batBuoc: true },
  { key: "recipient_phone", ten: "SĐT người nhận", batBuoc: true },
  { key: "recipient_address", ten: "Địa chỉ người nhận", batBuoc: true },
  { key: "product_name", ten: "Tên hàng hóa", batBuoc: true },
  { key: "quantity", ten: "Số lượng", batBuoc: false },
  { key: "weight_grams", ten: "Cân nặng (gram)", batBuoc: true },
  { key: "cod_amount", ten: "Tiền COD", batBuoc: false },
  { key: "declared_value", ten: "Giá trị khai", batBuoc: false },
  { key: "note", ten: "Ghi chú", batBuoc: false },
];
const ST = { buoc: 1, tenFile: "", loaiFile: "", cotGoc: [], dongGoc: [], anhXa: {}, dong: [], moPhong: false };
const vung = document.getElementById("vung-buoc");

function toBuoc(n) {
  ST.buoc = n;
  document.querySelectorAll(".buoc").forEach(b => {
    const i = +b.dataset.buoc;
    b.classList.toggle("hien-tai", i === n);
    b.classList.toggle("xong", i < n);
  });
  ({ 1: veB1, 2: veB2, 3: veB3, 4: veB4, 5: veB5 })[n]();
  window.scrollTo(0, 0);
}

/* ===== Bước 1 — Tải file ===== */
function veB1() {
  vung.innerHTML = `
    <div class="the"><div class="the-than">
      <div class="vung-keo-tha" id="keo-tha" tabindex="0" role="button" aria-label="Kéo thả hoặc bấm để chọn tệp">
        <div style="font-size:36px">📄</div>
        <p style="margin:8px 0 2px;font-weight:700;color:var(--chu)">Kéo thả tệp vào đây hoặc bấm để chọn</p>
        <p style="margin:0">Chấp nhận: XLSX, XLS, CSV, PDF, PNG, JPG · tối đa 10 MB</p>
        <p style="margin:8px 0 0;font-size:12px">G00 đọc được <b>nội dung CSV thật</b>. Các định dạng khác chỉ chạy luồng <b>MÔ PHỎNG</b>.</p>
      </div>
      <input type="file" id="chon-tep" accept=".xlsx,.xls,.csv,.pdf,.png,.jpg,.jpeg" style="display:none" aria-label="Chọn tệp">
      <div id="loi-tep" style="margin-top:12px"></div>
      <p style="margin-top:14px;font-size:12.5px;color:var(--chu-mo)">
        Chưa có tệp? <button class="nut nut-nho" id="dung-mau">Dùng tệp CSV mẫu (mock/import-sample.csv)</button>
      </p>
    </div></div>`;
  const kt = document.getElementById("keo-tha"), inp = document.getElementById("chon-tep");
  kt.addEventListener("click", () => inp.click());
  kt.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); inp.click(); } });
  ["dragover", "dragenter"].forEach(ev => kt.addEventListener(ev, e => { e.preventDefault(); kt.classList.add("keo-qua"); }));
  ["dragleave", "drop"].forEach(ev => kt.addEventListener(ev, e => { e.preventDefault(); kt.classList.remove("keo-qua"); }));
  kt.addEventListener("drop", e => e.dataTransfer.files[0] && nhanTep(e.dataTransfer.files[0]));
  inp.addEventListener("change", () => inp.files[0] && nhanTep(inp.files[0]));
  document.getElementById("dung-mau").addEventListener("click", async () => {
    const text = await VIP.taiMock("import-sample.csv");
    ST.tenFile = "import-sample.csv"; ST.loaiFile = "csv"; ST.moPhong = false;
    docCSV(text); toBuoc(2);
  });
}
function nhanTep(f) {
  const hopLe = /\.(xlsx|xls|csv|pdf|png|jpe?g)$/i;
  const khayLoi = document.getElementById("loi-tep");
  if (!hopLe.test(f.name)) { khayLoi.innerHTML = `<div class="hop-loi">Tệp "${VIP.thoat(f.name)}" không thuộc định dạng được chấp nhận.</div>`; return; }
  if (f.size > 10 * 1024 * 1024) { khayLoi.innerHTML = `<div class="hop-loi">Tệp vượt quá 10 MB (${(f.size / 1048576).toFixed(1)} MB).</div>`; return; }
  ST.tenFile = f.name;
  if (/\.csv$/i.test(f.name)) {
    ST.loaiFile = "csv"; ST.moPhong = false;
    const r = new FileReader();
    r.onload = () => { docCSV(r.result); toBuoc(2); };
    r.readAsText(f, "utf-8");
  } else {
    ST.loaiFile = f.name.split(".").pop().toLowerCase(); ST.moPhong = true;
    khayLoi.innerHTML = "";
    VIP.taiMock("import-sample.csv").then(t => { docCSV(t); toBuoc(2); });
  }
}
function docCSV(text) {
  // Parser CSV nhỏ: hỗ trợ ô trong dấu nháy kép và dấu phẩy trong ô.
  const dong = [];
  let o = "", hang = [], trongNhay = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (trongNhay) {
      if (c === '"' && text[i + 1] === '"') { o += '"'; i++; }
      else if (c === '"') trongNhay = false;
      else o += c;
    } else if (c === '"') trongNhay = true;
    else if (c === ",") { hang.push(o); o = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      hang.push(o); o = "";
      if (hang.some(x => x.trim() !== "")) dong.push(hang);
      hang = [];
    } else o += c;
  }
  if (o !== "" || hang.length) { hang.push(o); if (hang.some(x => x.trim() !== "")) dong.push(hang); }
  ST.cotGoc = dong[0] || [];
  ST.dongGoc = dong.slice(1);
  ST.anhXa = {};
  TRUONG_CHUAN.forEach(t => {
    const i = ST.cotGoc.findIndex(c => c.trim().toLowerCase() === t.key);
    if (i >= 0) ST.anhXa[t.key] = i;
  });
}

/* ===== Bước 2 — Phân tích ===== */
function veB2() {
  const nhanMoPhong = ST.moPhong ? `
    <div class="hop-loi" style="margin-bottom:14px">
      <b>MÔ PHỎNG — CHƯA ĐỌC NỘI DUNG TỆP.</b> G00 chưa có parser cho định dạng
      <b>.${VIP.thoat(ST.loaiFile)}</b>; hệ thống KHÔNG đọc nội dung tệp bạn tải lên mà dùng bộ dữ liệu
      minh họa (mock/import-sample.csv) để trình diễn luồng. Khi có backend, bước này sẽ đọc tệp thật.
    </div>` : "";
  vung.innerHTML = `
    <div class="the"><div class="the-dau"><h2>Kết quả phân tích tệp</h2>
      <div class="phai">${ST.moPhong ? '<span class="tag-demo">MÔ PHỎNG</span>' : '<span class="huy-hieu hh-xanh">CSV — ĐÃ ĐỌC NỘI DUNG THẬT</span>'}</div></div>
    <div class="the-than">
      ${nhanMoPhong}
      <div class="luoi luoi-3">
        <div class="the kpi"><div class="nhan">Tệp</div><div class="so" style="font-size:15px;word-break:break-all">${VIP.thoat(ST.tenFile)}</div></div>
        <div class="the kpi"><div class="nhan">Số cột nhận diện</div><div class="so">${ST.cotGoc.length}</div></div>
        <div class="the kpi"><div class="nhan">Số dòng dữ liệu</div><div class="so">${ST.dongGoc.length}</div></div>
      </div>
      <h3 style="font-size:13.5px;margin:18px 0 8px">Xem trước 5 dòng đầu</h3>
      <div class="cuon-ngang"><table class="bang">
        <thead><tr>${ST.cotGoc.map(c => `<th>${VIP.thoat(c)}</th>`).join("")}</tr></thead>
        <tbody>${ST.dongGoc.slice(0, 5).map(d => `<tr>${ST.cotGoc.map((_, i) => `<td>${VIP.thoat(d[i] || "")}</td>`).join("")}</tr>`).join("")}</tbody>
      </table></div>
    </div>
    <div class="modal-chan">
      <button class="nut" id="b2-lui">← Chọn tệp khác</button>
      <button class="nut nut-chinh" id="b2-toi">Tiếp tục: Ánh xạ cột →</button>
    </div></div>`;
  document.getElementById("b2-lui").addEventListener("click", () => toBuoc(1));
  document.getElementById("b2-toi").addEventListener("click", () => toBuoc(3));
}

/* ===== Bước 3 — Ánh xạ cột ===== */
function veB3() {
  vung.innerHTML = `
    <div class="the"><div class="the-dau"><h2>Ánh xạ cột tệp → trường chuẩn</h2>
      <div class="phai"><span class="tag-demo">DEMO</span></div></div>
    <div class="the-than">
      <p style="color:var(--chu-mo);margin-top:0">Cột trùng tên đã được ánh xạ tự động. Thiết kế tương lai: lưu mẫu ánh xạ theo từng khách hàng, có phiên bản (chưa làm ở G00).</p>
      <div class="cuon-ngang"><table class="bang">
        <thead><tr><th>Trường chuẩn</th><th>Bắt buộc</th><th>Cột trong tệp</th><th>Giá trị mẫu (dòng 1)</th></tr></thead>
        <tbody>${TRUONG_CHUAN.map(t => `
          <tr><td><b>${t.ten}</b><br><span style="color:var(--chu-mo);font-size:11.5px">${t.key}</span></td>
          <td>${t.batBuoc ? '<span class="huy-hieu hh-do">bắt buộc</span>' : '<span class="huy-hieu hh-xam">tùy chọn</span>'}</td>
          <td><select data-key="${t.key}" aria-label="Ánh xạ cho ${t.ten}" style="padding:6px 8px;border:1px solid var(--vien);border-radius:7px;min-width:170px">
            <option value="">— Bỏ qua —</option>
            ${ST.cotGoc.map((c, i) => `<option value="${i}" ${ST.anhXa[t.key] === i ? "selected" : ""}>${VIP.thoat(c)}</option>`).join("")}
          </select></td>
          <td id="mau-${t.key}" style="color:var(--chu-mo)"></td></tr>`).join("")}
        </tbody></table></div>
      <div id="loi-anh-xa" style="margin-top:12px"></div>
    </div>
    <div class="modal-chan">
      <button class="nut" id="b3-lui">← Quay lại</button>
      <button class="nut nut-chinh" id="b3-toi">Tiếp tục: Kiểm tra dữ liệu →</button>
    </div></div>`;
  const capNhatMau = () => TRUONG_CHUAN.forEach(t => {
    const i = ST.anhXa[t.key];
    document.getElementById("mau-" + t.key).textContent = i != null && ST.dongGoc[0] ? (ST.dongGoc[0][i] || "(trống)") : "—";
  });
  vung.querySelectorAll("select[data-key]").forEach(sel => sel.addEventListener("change", () => {
    if (sel.value === "") delete ST.anhXa[sel.dataset.key];
    else ST.anhXa[sel.dataset.key] = +sel.value;
    capNhatMau();
  }));
  capNhatMau();
  document.getElementById("b3-lui").addEventListener("click", () => toBuoc(2));
  document.getElementById("b3-toi").addEventListener("click", () => {
    const thieu = TRUONG_CHUAN.filter(t => t.batBuoc && ST.anhXa[t.key] == null);
    if (thieu.length) {
      document.getElementById("loi-anh-xa").innerHTML =
        `<div class="hop-loi">Chưa ánh xạ trường bắt buộc: <b>${thieu.map(t => t.ten).join(", ")}</b>.</div>`;
      return;
    }
    ST.dong = ST.dongGoc.map((d, idx) => {
      const r = { _stt: idx + 1, _chon: false };
      TRUONG_CHUAN.forEach(t => { r[t.key] = ST.anhXa[t.key] != null ? String(d[ST.anhXa[t.key]] ?? "").trim() : ""; });
      r.hang_chon = "";
      return r;
    });
    toBuoc(4);
  });
}

/* ===== Bước 4 — Kiểm tra & sửa ===== */
function kiemTraDong(r) {
  const loi = [], canXem = [];
  if (!r.recipient_name) loi.push({ key: "recipient_name", msg: "Thiếu tên người nhận" });
  if (!/^0\d{9}$/.test(r.recipient_phone.replace(/[\s.]/g, ""))) loi.push({ key: "recipient_phone", msg: "SĐT phải 10 số, bắt đầu bằng 0" });
  if (!r.recipient_address) loi.push({ key: "recipient_address", msg: "Thiếu địa chỉ" });
  if (!r.product_name) loi.push({ key: "product_name", msg: "Thiếu tên hàng" });
  const kl = Number(r.weight_grams);
  if (!(kl > 0)) loi.push({ key: "weight_grams", msg: "Cân nặng phải > 0" });
  const cod = r.cod_amount === "" ? 0 : Number(r.cod_amount);
  if (Number.isNaN(cod) || cod < 0) loi.push({ key: "cod_amount", msg: "COD không được âm" });
  const gt = r.declared_value === "" ? 0 : Number(r.declared_value);
  if (Number.isNaN(gt) || gt < 0) loi.push({ key: "declared_value", msg: "Giá trị khai không được âm" });
  if (cod > 5000000) canXem.push("COD lớn (>5 triệu) — nên xem lại");
  return { loi, canXem };
}
function timTrung() {
  const thay = {};
  ST.dong.forEach(r => {
    const k = r.recipient_phone.replace(/[\s.]/g, "") + "|" + r.recipient_address.toLowerCase();
    (thay[k] = thay[k] || []).push(r._stt);
  });
  const trung = new Set();
  Object.values(thay).forEach(arr => { if (arr.length > 1 && arr[0]) arr.forEach(stt => trung.add(stt)); });
  return trung;
}
function veB4(locLoi) {
  const trung = timTrung();
  let soLoi = 0, soCanXem = 0, soHopLe = 0;
  const dsVe = [];
  ST.dong.forEach(r => {
    const kq = kiemTraDong(r);
    const nghiTrung = trung.has(r._stt) && r.recipient_phone;
    if (kq.loi.length) soLoi++;
    else if (kq.canXem.length || nghiTrung) soCanXem++;
    else soHopLe++;
    dsVe.push({ r, kq, nghiTrung });
  });
  const hien = locLoi ? dsVe.filter(x => x.kq.loi.length) : dsVe;
  vung.innerHTML = `
    <div class="hang-cong-cu">
      <span class="huy-hieu hh-xanh">✓ Hợp lệ: ${soHopLe}</span>
      <span class="huy-hieu hh-vang">⚠ Cần xem xét: ${soCanXem}</span>
      <span class="huy-hieu hh-do">✕ Lỗi: ${soLoi}</span>
      <div class="day">
        <button class="nut nut-nho" id="b4-loc">${locLoi ? "Hiện tất cả dòng" : "Chỉ hiện dòng lỗi"}</button>
      </div>
    </div>
    <div class="the"><div class="cuon-ngang"><table class="bang">
      <thead><tr><th>#</th><th>Người nhận</th><th>SĐT</th><th>Địa chỉ</th><th>Hàng hóa</th>
        <th class="so-tien">KL (g)</th><th class="so-tien">COD</th><th>Kết quả kiểm tra</th><th></th></tr></thead>
      <tbody>${hien.map(({ r, kq, nghiTrung }) => {
        const keyLoi = new Set(kq.loi.map(l => l.key));
        const lop = kq.loi.length ? "dong-loi" : (kq.canXem.length || nghiTrung) ? "dong-can-xem" : "dong-hop-le";
        return `<tr class="${lop}">
          <td>${r._stt}</td>
          <td class="${keyLoi.has("recipient_name") ? "o-loi" : ""}">${VIP.thoat(r.recipient_name) || "<i>(trống)</i>"}</td>
          <td class="${keyLoi.has("recipient_phone") ? "o-loi" : ""}">${VIP.thoat(r.recipient_phone) || "<i>(trống)</i>"}</td>
          <td class="${keyLoi.has("recipient_address") ? "o-loi" : ""}" style="max-width:220px">${VIP.thoat(r.recipient_address)}</td>
          <td class="${keyLoi.has("product_name") ? "o-loi" : ""}">${VIP.thoat(r.product_name)}</td>
          <td class="so-tien ${keyLoi.has("weight_grams") ? "o-loi" : ""}">${VIP.thoat(r.weight_grams)}</td>
          <td class="so-tien ${keyLoi.has("cod_amount") ? "o-loi" : ""}">${r.cod_amount === "" ? "0" : VIP.thoat(r.cod_amount)}</td>
          <td style="font-size:12px;max-width:200px">
            ${kq.loi.map(l => `<div style="color:var(--do-dam)">✕ ${l.msg}</div>`).join("")}
            ${kq.canXem.map(m => `<div style="color:var(--vang)">⚠ ${m}</div>`).join("")}
            ${nghiTrung ? '<div style="color:var(--vang)">⚠ Nghi trùng (SĐT + địa chỉ giống dòng khác)</div>' : ""}
            ${!kq.loi.length && !kq.canXem.length && !nghiTrung ? '<span style="color:var(--xanh-la)">✓ Đạt</span>' : ""}
          </td>
          <td><button class="nut nut-nho" data-sua="${r._stt}">Sửa</button></td></tr>`;
      }).join("") || `<tr><td colspan="9"><div class="trang-thai-rong"><div class="to">🎉</div>Không còn dòng lỗi nào</div></td></tr>`}
      </tbody></table></div>
    <div class="modal-chan">
      <button class="nut" id="b4-lui">← Quay lại ánh xạ</button>
      <button class="nut nut-chinh" id="b4-toi" ${soLoi ? "disabled title='Còn dòng lỗi — hãy sửa hoặc nhớ rằng dòng lỗi sẽ bị loại ở bước duyệt'" : ""}>Tiếp tục: Duyệt tạo đơn →</button>
      ${soLoi ? `<button class="nut" id="b4-bo-loi">Loại ${soLoi} dòng lỗi và tiếp tục →</button>` : ""}
    </div></div>`;
  document.getElementById("b4-loc").addEventListener("click", () => veB4(!locLoi));
  document.getElementById("b4-lui").addEventListener("click", () => toBuoc(3));
  document.getElementById("b4-toi").addEventListener("click", () => toBuoc(5));
  const nutBo = document.getElementById("b4-bo-loi");
  if (nutBo) nutBo.addEventListener("click", () => {
    ST.dong = ST.dong.filter(r => !kiemTraDong(r).loi.length);
    VIP.toast(`Đã loại các dòng lỗi. Còn ${ST.dong.length} dòng.`, "canh-bao");
    toBuoc(5);
  });
  vung.querySelectorAll("[data-sua]").forEach(n => n.addEventListener("click", () => moSua(+n.dataset.sua, locLoi)));
}
function moSua(stt, locLoi) {
  const r = ST.dong.find(x => x._stt === stt);
  const m = VIP.moModal(`Sửa dòng #${stt}`,
    TRUONG_CHUAN.map(t => `
      <div class="form-nhom"><label for="sua-${t.key}">${t.ten}${t.batBuoc ? ' <span class="bat-buoc">*</span>' : ""}</label>
      <input id="sua-${t.key}" value="${VIP.thoat(r[t.key])}"></div>`).join(""),
    `<button class="nut" id="sua-huy">Hủy</button><button class="nut nut-chinh" id="sua-luu">Lưu dòng</button>`);
  m.querySelector("#sua-huy").addEventListener("click", VIP.dongModal);
  m.querySelector("#sua-luu").addEventListener("click", () => {
    TRUONG_CHUAN.forEach(t => { r[t.key] = m.querySelector("#sua-" + t.key).value.trim(); });
    VIP.dongModal(); VIP.toast(`Đã cập nhật dòng #${stt} (demo, chỉ trong trình duyệt).`);
    veB4(locLoi);
  });
}

/* ===== Bước 5 — Duyệt tạo đơn (demo) ===== */
function veB5() {
  const hopLe = ST.dong.filter(r => !kiemTraDong(r).loi.length);
  vung.innerHTML = `
    <div class="hop-loi" style="background:var(--vang-nhat);border-color:#FBD38D;color:var(--vang);margin-bottom:14px">
      <b>DEMO — CHƯA KẾT NỐI API.</b> Bước duyệt này chỉ mô phỏng: không gửi yêu cầu nào tới hãng vận chuyển, không tạo đơn thật.
    </div>
    <div class="hang-cong-cu">
      <label><input type="checkbox" id="chon-het"> Chọn tất cả (${hopLe.length} dòng hợp lệ)</label>
      <div class="day">
        <label for="hang-chung" style="font-weight:600">Gán hãng cho dòng đã chọn:</label>
        <select id="hang-chung" class="nut" style="padding:7px 10px">
          <option value="">— Chọn hãng —</option>
          <option>Viettel Post</option><option>GHN</option><option>GHTK</option><option>J&amp;T Express</option><option>BEST Express</option>
        </select>
        <button class="nut nut-nho" id="gan-hang">Gán</button>
      </div>
    </div>
    <div class="the"><div class="cuon-ngang"><table class="bang">
      <thead><tr><th></th><th>#</th><th>Người nhận</th><th>SĐT</th><th class="so-tien">COD</th><th>Hãng vận chuyển</th></tr></thead>
      <tbody>${hopLe.map(r => `
        <tr><td><input type="checkbox" data-chon="${r._stt}" ${r._chon ? "checked" : ""} aria-label="Chọn dòng ${r._stt}"></td>
        <td>${r._stt}</td><td>${VIP.thoat(r.recipient_name)}</td><td>${VIP.thoat(r.recipient_phone)}</td>
        <td class="so-tien">${VIP.tien(Number(r.cod_amount) || 0)}</td>
        <td><select data-hang="${r._stt}" aria-label="Hãng cho dòng ${r._stt}" style="padding:5px 8px;border:1px solid var(--vien);border-radius:7px">
          <option value="">— Chọn hãng —</option>
          ${["Viettel Post", "GHN", "GHTK", "J&T Express", "BEST Express"].map(h => `<option ${r.hang_chon === h ? "selected" : ""}>${h}</option>`).join("")}
        </select></td></tr>`).join("")}
      </tbody></table></div>
    <div class="modal-chan">
      <button class="nut" id="b5-lui">← Quay lại kiểm tra</button>
      <button class="nut nut-chinh" id="b5-duyet">Duyệt tạo đơn (DEMO)</button>
    </div></div>`;
  document.getElementById("chon-het").addEventListener("change", e => {
    hopLe.forEach(r => r._chon = e.target.checked);
    vung.querySelectorAll("[data-chon]").forEach(c => c.checked = e.target.checked);
  });
  vung.querySelectorAll("[data-chon]").forEach(c => c.addEventListener("change", () => {
    ST.dong.find(r => r._stt === +c.dataset.chon)._chon = c.checked;
  }));
  vung.querySelectorAll("[data-hang]").forEach(s => s.addEventListener("change", () => {
    ST.dong.find(r => r._stt === +s.dataset.hang).hang_chon = s.value;
  }));
  document.getElementById("gan-hang").addEventListener("click", () => {
    const h = document.getElementById("hang-chung").value;
    if (!h) { VIP.toast("Hãy chọn hãng trước.", "canh-bao"); return; }
    let dem = 0;
    hopLe.forEach(r => { if (r._chon) { r.hang_chon = h; dem++; } });
    if (!dem) { VIP.toast("Chưa chọn dòng nào.", "canh-bao"); return; }
    VIP.toast(`Đã gán ${h} cho ${dem} dòng (demo).`); veB5();
  });
  document.getElementById("b5-lui").addEventListener("click", () => toBuoc(4));
  document.getElementById("b5-duyet").addEventListener("click", () => {
    const daChon = hopLe.filter(r => r._chon);
    if (!daChon.length) { VIP.toast("Chưa chọn dòng nào để duyệt.", "canh-bao"); return; }
    const thieuHang = daChon.filter(r => !r.hang_chon);
    if (thieuHang.length) { VIP.toast(`${thieuHang.length} dòng chưa chọn hãng.`, "loi"); return; }
    const m = VIP.moModal("Xác nhận duyệt (DEMO)",
      `<p>Sẽ mô phỏng tạo <b>${daChon.length}</b> đơn. <b>Không</b> API nào được gọi, <b>không</b> đơn thật nào được tạo.</p>
       <ul style="font-size:13px">${daChon.slice(0, 8).map(r => `<li>#${r._stt} — ${VIP.thoat(r.recipient_name)} → ${VIP.thoat(r.hang_chon)}</li>`).join("")}${daChon.length > 8 ? `<li>… và ${daChon.length - 8} dòng nữa</li>` : ""}</ul>`,
      `<button class="nut" id="xn-huy">Hủy</button><button class="nut nut-chinh" id="xn-ok">Xác nhận duyệt demo</button>`);
    m.querySelector("#xn-huy").addEventListener("click", VIP.dongModal);
    m.querySelector("#xn-ok").addEventListener("click", () => {
      VIP.dongModal();
      const dau = ["recipient_name", "recipient_phone", "recipient_address", "product_name", "quantity", "weight_grams", "cod_amount", "carrier_demo", "demo_order_id"];
      const csv = [dau.join(",")].concat(daChon.map((r, i) =>
        dau.slice(0, 7).map(k => `"${String(r[k] ?? "").replace(/"/g, '""')}"`).join(",") +
        `,"${r.hang_chon}","DEMO-${String(i + 1).padStart(4, "0")}"`)).join("\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
      a.download = "ket-qua-duyet-demo.csv"; a.click();
      VIP.toast(`DEMO: đã mô phỏng duyệt ${daChon.length} đơn và xuất CSV kết quả.`);
    });
  });
}
toBuoc(1);
