/* BEST Express — bàn nghiệm thu Owner. Không gọi thẳng hãng; mọi thứ qua backend.
   Không đưa token/secret vào DOM, console, localStorage hay thông báo lỗi. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s);
  let dsTaiKhoan = [];

  async function goi(duong, method, duLieu) {
    const res = await fetch(duong, {
      method: method || "GET",
      credentials: "same-origin",
      headers: { "X-Requested-With": "VIPHub", "Content-Type": "application/json" },
      body: duLieu == null ? undefined : JSON.stringify(duLieu),
    });
    let kq = {};
    try { kq = await res.json(); } catch (e) { /* không JSON */ }
    if (res.status === 401) {
      const e = new Error("phiên đăng nhập đã hết hạn — mở /admin/ để đăng nhập");
      e.ma = 401;
      throw e;
    }
    return { ma: res.status, ok: res.ok, kq };
  }

  function dat(id, chu, loai) {
    const o = $(id);
    if (!o) return;
    o.className = "ketqua" + (loai ? " " + loai : "");
    o.textContent = chu;
  }

  function loi(id, e) {
    dat(id, (e && e.message) ? e.message : String(e), "loi");
  }

  function renderTaiKhoan(ds) {
    dsTaiKhoan = Array.isArray(ds) ? ds.filter((x) => x.hang === "best") : [];
    const o = $("ds-tai-khoan");
    if (!o) return;
    if (!dsTaiKhoan.length) {
      o.className = "ketqua canhbao";
      o.textContent = "Chưa có tài khoản BEST. Tạo một tài khoản ở form bên dưới (mock trước, sandbox sau khi có phê duyệt).";
    } else {
      o.className = "ketqua";
      o.textContent = dsTaiKhoan.map((t) =>
        `#${t.id} · ${t.ten} · ${t.moi_truong} · ${t.kich_hoat ? "đang bật" : "đã khóa"}`
      ).join("\n");
    }
    for (const id of ["kn-tk", "wh-tk", "cuoc-tk", "don-tk", "tc-tk"]) {
      const s = $(id);
      if (!s) continue;
      s.textContent = "";
      for (const t of dsTaiKhoan) {
        const op = document.createElement("option");
        op.value = String(t.id);
        op.textContent = `#${t.id} ${t.moi_truong} — ${t.ten}`;
        s.appendChild(op);
      }
      if (!s.options.length) {
        const op = document.createElement("option");
        op.value = "";
        op.textContent = "(chưa có tài khoản BEST)";
        s.appendChild(op);
      }
    }
  }

  async function taiTaiKhoan() {
    const r = await goi("/api/v2/tai-khoan-hang");
    if (!r.ok) throw new Error((r.kq && r.kq.loi) || `HTTP ${r.ma}`);
    renderTaiKhoan((r.kq && r.kq.tai_khoan) || []);
  }

  async function taiTrangThai() {
    dat("trang-thai", "Đang tải trạng thái + TLS…");
    const r = await goi("/api/v2/best/trang-thai?tls=1");
    if (!r.ok) throw new Error((r.kq && r.kq.loi) || `HTTP ${r.ma}`);
    const kq = r.kq || {};
    const hd = kq.hop_dong || {};
    const dong = [];
    dong.push(`Phê duyệt Owner: ${kq.co_phe_duyet_owner ? "CÓ" : "CHƯA"} · mã: ${kq.co_ma_phe_duyet ? "CÓ" : "CHƯA"}`);
    dong.push(`Số mã trạng thái: ${hd.so_ma || "?"} · ServiceId: ${hd.service_id || "?"} · token: ${hd.token_ttl_days || "?"} ngày`);
    dong.push(`Query ≤ ${hd.gioi_han ? hd.gioi_han.query : "?"} · Print ≤ ${hd.gioi_han ? hd.gioi_han.print : "?"}`);
    dong.push(`Nguồn: ${hd.nguon || "?"}`);
    if (kq.tls) {
      for (const [host, t] of Object.entries(kq.tls)) {
        dong.push(`TLS ${host}: ${t.ok ? `${t.tls} · ${t.cn} · hết hạn ${t.not_after}` : `LỖI — ${t.loi}`}`);
      }
    }
    dong.push("Ghi chú: production chỉ cho đăng nhập/đọc; tạo đơn production bị khóa.");
    dat("trang-thai", dong.join("\n"), kq.co_phe_duyet_owner ? "ok" : "canhbao");
  }

  async function luuTaiKhoan(ev) {
    ev.preventDefault();
    const mt = $("tk-mt").value;
    const user = $("tk-user").value.trim();
    const pass = $("tk-pass").value;
    const xacNhan = $("tk-xac-nhan").checked;
    if (!user || !pass) return loi("tk-ghi-chu", new Error("cần username + password"));
    if (mt !== "mock") {
      if (location.protocol !== "https:") {
        return loi("tk-ghi-chu", new Error("credential thật chỉ nhận qua HTTPS. Chạy server với VIP_HUB_TLS_CERT/KEY hoặc sau reverse proxy TLS."));
      }
      if (!xacNhan) return loi("tk-ghi-chu", new Error("cần tick xác nhận phê duyệt của Owner"));
      if (mt === "production") {
        return loi("tk-ghi-chu", new Error("production chỉ cho phép sau nghiệm thu riêng; dùng sandbox trước."));
      }
    }
    const than = {
      hang: "best",
      ten: $("tk-ten").value.trim() || "BEST Express",
      moi_truong: mt,
      credentials: { username: user, password: pass },
    };
    $("tk-pass").value = "";
    dat("tk-ghi-chu", "Đang lưu (credential được mã hoá ở backend)…");
    try {
      const r = await goi("/api/v2/tai-khoan-hang", "POST", than);
      if (!r.ok) throw new Error((r.kq && r.kq.loi) || `HTTP ${r.ma}`);
      dat("tk-ghi-chu", `Đã lưu tài khoản #${r.kq.id} · môi trường ${mt} · webhook: ${r.kq.webhook_url || ""}`, "ok");
      await taiTaiKhoan();
      await taiTrangThai();
    } catch (e) { loi("tk-ghi-chu", e); }
  }

  async function kiemKetNoi() {
    const id = $("kn-tk").value;
    const xacNhan = $("kn-xac-nhan").value === "1";
    if (!id) return loi("kq-ket-noi", new Error("chưa chọn tài khoản BEST"));
    dat("kq-ket-noi", "Đang gọi backend kiểm tra đăng nhập…");
    try {
      const r = await goi("/api/v2/best/kiem-ket-noi", "POST",
        { tai_khoan_id: Number(id), xac_nhan_that: xacNhan });
      const kq = r.kq || {};
      const dong = [
        `Kết quả: ${kq.ok ? "ĐĂNG NHẬP THÀNH CÔNG" : "THẤT BẠI/BỊ CHẶN"}`,
        `Môi trường: ${kq.moi_truong || "?"} · endpoint: ${kq.meta ? kq.meta.endpoint : "?"} · HTTP: ${kq.meta ? kq.meta.http_status : "?"}`,
      ];
      if (kq.tls) dong.push(`TLS ${kq.tls.host}: ${kq.tls.ok ? kq.tls.tls + " · " + kq.tls.cn : "LỖI " + kq.tls.loi}`);
      if (kq.loi) dong.push(`Lý do: ${kq.loi}`);
      dong.push("Không có token nào được trả về giao diện.");
      dat("kq-ket-noi", dong.join("\n"), kq.ok ? "ok" : (r.ma === 403 ? "canhbao" : "loi"));
    } catch (e) { loi("kq-ket-noi", e); }
  }

  async function luuWebhook() {
    const id = $("wh-tk").value;
    const token = $("wh-token").value;
    if (!id || !token) return loi("kq-webhook", new Error("chọn tài khoản + nhập Bearer"));
    $("wh-token").value = "";
    dat("kq-webhook", "Đang lưu Bearer (mã hoá)…");
    try {
      const r = await goi("/api/v2/best/webhook-bearer", "POST",
        { tai_khoan_id: Number(id), bearer: token });
      if (!r.ok) throw new Error((r.kq && r.kq.loi) || `HTTP ${r.ma}`);
      dat("kq-webhook", `Đã lưu Bearer. URL webhook: ${r.kq.webhook_url || ""}`, "ok");
    } catch (e) { loi("kq-webhook", e); }
  }

  function donTuForm(prefix) {
    const v = (x) => $(prefix + x) ? $(prefix + x).value.trim() : "";
    return {
      ma_don: v("ma") || `UAT-${Date.now()}`,
      hang_hoa: v("hang") || "Hàng kiểm thử UAT",
      nguoi_gui_ten: v("sname") || "Nguyễn Gửi",
      nguoi_gui_sdt: v("sdt") || "0901000001",
      nguoi_gui_tinh: v("sc") || "Hồ Chí Minh",
      nguoi_gui_quan: v("sd") || "",
      nguoi_gui_xa: v("sw") || "Phường 12",
      nguoi_gui_dia_chi: v("sa") || "12 Đường ABCD",
      nguoi_nhan_ten: v("dname") || "Trần Nhận",
      nguoi_nhan_sdt: v("ddt") || "0902000002",
      nguoi_nhan_tinh: v("dc") || "Hồ Chí Minh",
      nguoi_nhan_quan: v("dd") || "",
      nguoi_nhan_xa: v("dw") || "Phường 10",
      nguoi_nhan_dia_chi: v("da") || "34 Đường XYZ",
      khoi_luong_gram: Number(v("can") || 500),
      chieu_dai_mm: Number(v("dai") || 0),
      chieu_rong_mm: Number(v("rong") || 0),
      chieu_cao_mm: Number(v("cao") || 0),
      cod: Number(v("cod") || 0),
      gia_tri_khai: Number(v("gia") || 0),
      journey_type: Number($("don-journey") ? $("don-journey").value : 1),
      pickup_type: Number($("don-pickup") ? $("don-pickup").value : 2),
    };
  }

  async function baoGia(ev) {
    ev.preventDefault();
    const id = $("cuoc-tk").value;
    if (!id) return loi("kq-cuoc", new Error("chưa chọn tài khoản"));
    const don = {
      nguoi_gui_tinh: $("cuoc-sc").value.trim(), nguoi_gui_quan: $("cuoc-sd").value.trim(),
      nguoi_gui_xa: $("cuoc-sw").value.trim(),
      nguoi_nhan_tinh: $("cuoc-dc").value.trim(), nguoi_nhan_quan: $("cuoc-dd").value.trim(),
      nguoi_nhan_xa: $("cuoc-dw").value.trim(),
      khoi_luong_gram: Number($("cuoc-can").value || 1),
      chieu_dai_mm: Number($("cuoc-dai").value || 0),
      chieu_rong_mm: Number($("cuoc-rong").value || 0),
      chieu_cao_mm: Number($("cuoc-cao").value || 0),
      cod: Number($("cuoc-cod").value || 0),
      gia_tri_khai: Number($("cuoc-gia").value || 0),
    };
    dat("kq-cuoc", "Đang báo cước…");
    try {
      const r = await goi("/api/v2/best/bao-gia", "POST",
        { tai_khoan_id: Number(id), don, xac_nhan_that: true });
      const kq = r.kq || {};
      if (!r.ok || !kq.ok) {
        const ly = (kq && kq.loi) || (r.kq && r.kq.loi) || `HTTP ${r.ma}`;
        dat("kq-cuoc", `KHÔNG BÁO ĐƯỢC CƯỚC: ${ly}`, "canhbao");
        return;
      }
      const d = kq.data || {};
      const dong = [
        `Tổng phí: ${d.TotalFee != null ? d.TotalFee : "?"} VND`,
        `Phí vận chuyển: ${d.FreightFee != null ? d.FreightFee : "?"} · COD fee: ${d.CODFee != null ? d.CODFee : "?"}`,
        `Bảo hiểm: ${d.InsuranceFee != null ? d.InsuranceFee : "?"} · VAT: ${d.FreightFeeVAT != null ? d.FreightFeeVAT : "?"}`,
        `Tổng có VAT: ${d.TotalFeeVAT != null ? d.TotalFeeVAT : "?"} · sau discount: ${d.TotalFeeVATWithDiscount != null ? d.TotalFeeVATWithDiscount : "?"}`,
        `Service: ${d.ServiceType || "?"} · COD: ${d.COD != null ? d.COD : "?"} · khai giá: ${d.ProductPrice != null ? d.ProductPrice : "?"}`,
      ];
      dat("kq-cuoc", dong.join("\n"), "ok");
    } catch (e) { loi("kq-cuoc", e); }
  }

  async function taoDon(ev) {
    ev.preventDefault();
    const id = $("don-tk").value;
    if (!id) return loi("kq-don", new Error("chưa chọn tài khoản"));
    const xacNhan = $("don-xac-nhan").value.trim();
    dat("kq-don", "Đang gửi tạo đơn sandbox…");
    try {
      const r = await goi("/api/v2/best/tao-don", "POST", {
        tai_khoan_id: Number(id), don: donTuForm("don-"), xac_nhan_that: true,
        xac_nhan: xacNhan,
      });
      const kq = r.kq || {};
      if (!r.ok || !kq.ok) {
        dat("kq-don", `KHÔNG TẠO ĐƯỢC: ${kq.loi || kq.blocked ? (kq.loi || "bị chặn") : "HTTP " + r.ma}`, "canhbao");
        return;
      }
      dat("kq-don", `ĐÃ TẠO ĐƠN SANDBOX\nMã vận đơn: ${kq.ma_van_don || "?"}\nRoute: ${kq.route_code || "?"}\nHTTP: ${kq.http_status || "?"}`, "ok");
    } catch (e) { loi("kq-don", e); }
  }

  function codes() {
    return ($("tc-codes").value || "").split(",").map((x) => x.trim()).filter(Boolean);
  }

  async function traCuu() {
    const id = $("tc-tk").value;
    const ds = codes();
    if (!id || !ds.length) return loi("kq-tra-cuu", new Error("chọn tài khoản + nhập mã"));
    dat("kq-tra-cuu", "Đang tra cứu…");
    try {
      const r = await goi("/api/v2/best/tra-cuu", "POST",
        { tai_khoan_id: Number(id), codes: ds, xac_nhan_that: true });
      const kq = r.kq || {};
      if (!r.ok || !kq.ok) return dat("kq-tra-cuu", `KHÔNG TRA CỨU ĐƯỢC: ${kq.loi || "HTTP " + r.ma}`, "canhbao");
      const rows = (kq.data || []).map((x) =>
        `• ${x.code_best || "?"} · status=${x.status || "?"} · ${x.trang_thai_chung || "chưa map"} · ${x.status_content || ""}`
      );
      dat("kq-tra-cuu", rows.length ? rows.join("\n") : "Không có kết quả.", "ok");
    } catch (e) { loi("kq-tra-cuu", e); }
  }

  async function inVanDon() {
    const id = $("tc-tk").value;
    const ds = codes();
    if (!id || !ds.length) return loi("kq-tra-cuu", new Error("chọn tài khoản + nhập mã"));
    dat("kq-tra-cuu", "Đang lấy URL PDF…");
    try {
      const r = await goi("/api/v2/best/in", "POST",
        { tai_khoan_id: Number(id), codes: ds, xac_nhan_that: true });
      const kq = r.kq || {};
      if (!r.ok || !kq.ok) return dat("kq-tra-cuu", `KHÔNG IN ĐƯỢC: ${kq.loi || "HTTP " + r.ma}`, "canhbao");
      const url = String(kq.url || "");
      const canhBao = /^http:\/\//i.test(url) ? "\nCẢNH BÁO: URL PDF là HTTP — không tải bằng trình duyệt; cần backend tải qua HTTPS/allowlist." : "";
      dat("kq-tra-cuu", `URL PDF: ${url}${canhBao}`, "ok");
    } catch (e) { loi("kq-tra-cuu", e); }
  }

  async function taiLichSu() {
    dat("kq-lich-su", "Đang tải…");
    try {
      const r = await goi("/api/v2/best/lich-su");
      if (!r.ok) throw new Error((r.kq && r.kq.loi) || `HTTP ${r.ma}`);
      const kq = r.kq || {};
      const sk = kq.su_kien || [], au = kq.audit || [];
      const dong = [`Sự kiện gần nhất: ${sk.length} · audit BEST: ${au.length}`];
      for (const s of sk.slice(0, 10)) dong.push(`• event #${s.id} · ${s.trang_thai} · ${s.nhan_luc}${s.loi_cuoi ? " · lỗi: " + s.loi_cuoi : ""}`);
      for (const a of au.slice(0, 10)) dong.push(`• audit #${a.id} · ${a.hanh_dong} · ${a.ket_qua}`);
      dat("kq-lich-su", dong.join("\n"));
    } catch (e) { loi("kq-lich-su", e); }
  }

  async function khoiTao() {
    $("form-tk").addEventListener("submit", luuTaiKhoan);
    $("form-cuoc").addEventListener("submit", baoGia);
    $("form-don").addEventListener("submit", taoDon);
    $("btn-trang-thai").addEventListener("click", () => taiTrangThai().catch((e) => dat("trang-thai", e.message, "loi")));
    $("btn-kiem-ket-noi").addEventListener("click", kiemKetNoi);
    $("btn-luu-webhook").addEventListener("click", luuWebhook);
    $("btn-tra-cuu").addEventListener("click", traCuu);
    $("btn-in").addEventListener("click", inVanDon);
    $("btn-lich-su").addEventListener("click", taiLichSu);
    try {
      await taiTaiKhoan();
      await taiTrangThai();
      $("auth").className = "the ok";
      $("auth").textContent = "Đã đăng nhập. Các nút bên dưới gọi backend nội bộ; không có token/secret nào hiển thị.";
    } catch (e) {
      $("auth").className = "the canhbao";
      $("auth").textContent = "Chưa đăng nhập hoặc thiếu quyền: " + e.message + " — mở /admin/ để đăng nhập.";
    }
  }

  document.addEventListener("DOMContentLoaded", khoiTao);
})();
