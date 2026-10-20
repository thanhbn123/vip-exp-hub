/* BEST Express — bàn nghiệm thu Owner. Không gọi thẳng hãng; mọi thứ qua backend.
   Không đưa token/secret vào DOM, console, localStorage hay thông báo lỗi. */
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s);
  let dsTaiKhoan = [];

  /* CHỐT THỨ HAI CHỐNG LỘ SECRET. Backend đã không trả token/credential, nhưng lý do lỗi của
     hãng có thể chứa URL kèm token hoặc một chuỗi dài trông như Bearer. Mọi chữ đi vào DOM đều
     qua `anBiMat`; giá trị thật KHÔNG bao giờ được chép vào thông báo. */
  const MAU_JWT = /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g;
  function anBiMat(chu) {
    return String(chu == null ? "" : chu)
      .replace(/(Bearer\s+)[A-Za-z0-9._~+/=-]{8,}/gi, "$1•••")
      .replace(MAU_JWT, "•••")
      .replace(/((?:token|password|mat_khau|mật\s*khẩu|secret|bearer)\s*[=:]\s*)([A-Za-z0-9._~+/=-]{20,})/gi,
               "$1•••");
  }

  /** Lỗi mạng của trình duyệt là tiếng Anh ("Failed to fetch", "Load failed") — đổi sang câu
   *  tiếng Việt để người nghiệm thu biết việc cần làm, không đoán. */
  function loiMang(m) {
    return /failed to fetch|networkerror|load failed|fetch failed|network request failed/i.test(m)
      ? "không kết nối được máy chủ nội bộ — kiểm tra máy chủ đang chạy và phiên đăng nhập"
      : m;
  }

  function xacNhanThat() {
    const o = $("phe-duyet-that");
    return !!(o && o.checked);
  }

  function canPheDuyet(id) {
    if (xacNhanThat()) return true;
    dat(id || "kq-ket-noi", "CHẶN: hãy tick ô phê duyệt phiên nghiệm thu ở mục 0 trước.", "canhbao");
    return false;
  }

  async function goi(duong, method, duLieu) {
    let res;
    try {
      res = await fetch(duong, {
        method: method || "GET",
        credentials: "same-origin",
        headers: { "X-Requested-With": "VIPHub", "Content-Type": "application/json" },
        body: duLieu == null ? undefined : JSON.stringify(duLieu),
      });
    } catch (e) {
      // Mất mạng / máy chủ tắt là ca thường gặp khi nghiệm thu local. Không để "Failed to fetch".
      const loi = new Error(loiMang((e && e.message) || String(e)));
      loi.ma = 0;
      throw loi;
    }
    let kq = {};
    try { kq = await res.json(); } catch (e) { /* không JSON */ }
    // 401 có HAI nghĩa: phiên hub hết hạn (`{loi:...}`) và BEST từ chối credential
    // (`{ok:false, meta:{http_status:401}, ...}`). Gộp hai thứ này từng làm bàn nghiệm thu
    // báo "hết phiên" ngay khi hãng trả sai mật khẩu. Phân biệt bằng cờ `ok` của phản hồi BEST.
    if (res.status === 401 && kq.ok === undefined) {
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
    o.textContent = anBiMat(chu);
  }

  function loi(id, e) {
    dat(id, loiMang((e && e.message) ? e.message : String(e)), "loi");
  }

  function renderTaiKhoan(ds) {
    dsTaiKhoan = Array.isArray(ds) ? ds.filter((x) => x.hang === "best") : [];
    const o = $("ds-tai-khoan");
    if (!o) return;
    if (!dsTaiKhoan.length) {
      o.className = "ketqua canhbao";
      o.textContent = "Chưa có tài khoản BEST. Tạo tài khoản sandbox ở form bên dưới.";
    } else {
      o.className = "ketqua";
      o.textContent = anBiMat(dsTaiKhoan.map((t) => {
        const wh = t.webhook_url || `/api/v2/webhook/nhan/${t.webhook_ma || ""}`;
        const b = t.webhook_bearer || {};
        return `#${t.id} · ${t.ten} · ${t.moi_truong} · ${t.kich_hoat ? "đang bật" : "đã khóa"}`
          + `\n   webhook: ${wh}${t.webhook_url_cong_khai ? "" : " (CHƯA khai VIP_HUB_PUBLIC_BASE_URL — BEST không gọi được)"}`
          + `\n   Bearer webhook: ${b.co_bearer === true ? "đã lưu" : "CHƯA lưu"}`
          + ` · credential: ${t.co_credentials ? "đã lưu" : "chưa lưu"}`;
      }).join("\n"));
    }
    // Các ô THAO TÁC chỉ nhận tài khoản thật (sandbox/production). Tài khoản mock
    // không thể kiểm tra/báo cước/tạo đơn với BEST; để mock trong danh sách chỉ gây
    // hiểu nhầm "mock = lỗi kết nối". Mock vẫn hiện ở bảng tài khoản phía trên.
    const dsThat = dsTaiKhoan.filter((t) => t.moi_truong !== "mock");
    for (const id of ["kn-tk", "wh-tk", "cuoc-tk", "don-tk", "tc-tk", "ud-tk"]) {
      const s = $(id);
      if (!s) continue;
      s.textContent = "";
      for (const t of dsThat) {
        const op = document.createElement("option");
        op.value = String(t.id);
        op.textContent = `#${t.id} ${t.moi_truong} — ${t.ten}`;
        s.appendChild(op);
      }
      if (!s.options.length) {
        const op = document.createElement("option");
        op.value = "";
        op.textContent = "(chưa có tài khoản sandbox/production — tạo ở mục 2)";
        s.appendChild(op);
      }
    }
  }

  async function taiTaiKhoan() {
    const r = await goi("/api/v2/tai-khoan-hang");
    if (!r.ok) throw new Error((r.kq && r.kq.loi) || `HTTP ${r.ma}`);
    renderTaiKhoan((r.kq && r.kq.tai_khoan) || []);
  }

  async function taiTrangThai(coTls) {
    // CHỈ kiểm TLS khi người dùng bấm nút: lượt mở trang không tự bắt tay ra host hãng.
    // (Test E2E và chế độ local không được phát sinh kết nối ngoài loopback.)
    dat("trang-thai", coTls ? "Đang tải trạng thái + TLS…" : "Đang tải trạng thái…");
    const r = await goi("/api/v2/best/trang-thai" + (coTls ? "?tls=1" : ""));
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
    if (Array.isArray(kq.tai_khoan)) {
      // Dùng danh sách từ /trang-thai vì nó kèm webhook_url + trạng thái Bearer (không secret).
      renderTaiKhoan(kq.tai_khoan);
      for (const t of kq.tai_khoan) {
        dong.push(`Tài khoản #${t.id} · ${t.moi_truong} · webhook ${t.webhook_url || "?"}`
          + ` · Bearer ${(t.webhook_bearer && t.webhook_bearer.co_bearer) ? "đã lưu" : "CHƯA lưu"}`);
      }
    }
    dat("trang-thai", dong.join("\n"), kq.co_phe_duyet_owner ? "ok" : "canhbao");
  }

  async function luuTaiKhoan(ev) {
    ev.preventDefault();
    const mt = $("tk-mt").value;
    const user = $("tk-user").value.trim();
    const pass = $("tk-pass").value;
    const xacNhan = $("tk-xac-nhan").checked;
    if (!user || !pass) return loi("tk-kq", new Error("cần username + password"));
    if (mt !== "mock") {
      if (location.protocol !== "https:") {
        return loi("tk-kq", new Error("credential thật chỉ nhận qua HTTPS. Chạy server với VIP_HUB_TLS_CERT/KEY hoặc sau reverse proxy TLS."));
      }
      if (!xacNhan) return loi("tk-kq", new Error("cần tick xác nhận phê duyệt của Owner"));
      if (!xacNhanThat()) return loi("tk-kq", new Error("cần tick ô phê duyệt phiên nghiệm thu ở mục 0"));
      if (mt === "production") {
        return loi("tk-kq", new Error("production chỉ cho phép sau nghiệm thu riêng; dùng sandbox trước."));
      }
    }
    const cred = { username: user, password: pass };
    const ems = ($("tk-ems") ? $("tk-ems").value : "").trim();
    if (ems) cred.ems_key = ems;
    const ghiChu = ($("tk-ghi-chu") ? $("tk-ghi-chu").value : "").trim();
    if (ghiChu) cred.ghi_chu = ghiChu;
    const than = {
      hang: "best",
      ten: $("tk-ten").value.trim() || "BEST Express",
      moi_truong: mt,
      credentials: cred,
    };
    $("tk-pass").value = "";
    if ($("tk-ems")) $("tk-ems").value = "";
    dat("tk-kq", "Đang lưu (credential được mã hoá ở backend)…");
    try {
      const r = await goi("/api/v2/tai-khoan-hang", "POST", than);
      if (!r.ok) throw new Error((r.kq && r.kq.loi) || `HTTP ${r.ma}`);
      dat("tk-kq", `Đã lưu tài khoản #${r.kq.id} · môi trường ${mt} · webhook: ${r.kq.webhook_url || ""}`, "ok");
      await taiTaiKhoan();
      await taiTrangThai(false);
    } catch (e) { loi("tk-kq", e); }
  }

  async function kiemKetNoi() {
    const id = $("kn-tk").value;
    const xacNhan = $("kn-xac-nhan").value === "1" && xacNhanThat();
    if (!id) return loi("kq-ket-noi", new Error("chưa chọn tài khoản BEST"));
    if (!canPheDuyet("kq-ket-noi")) return;
    if (!xacNhan) return loi("kq-ket-noi", new Error("chọn 'Tôi đã phê duyệt kiểm tra thật'"));
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
    if (!canPheDuyet("kq-webhook")) return;
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
    const diaChiGui = $("cuoc-sa").value.trim();
    const diaChiNhan = $("cuoc-da").value.trim();
    // `dung_estimate` / `dung_order_add` dựng Source.Address/Dest.Address và TỪ CHỐI đơn thiếu
    // địa chỉ đường (lỗi cũ: bấm Báo cước là 502 "thiếu Source.Address"). Chặn tại UI để người
    // nghiệm thu thấy câu tiếng Việt rõ ràng thay vì một 502 từ backend.
    if (!diaChiGui || !diaChiNhan) {
      return loi("kq-cuoc", new Error(
        "thiếu địa chỉ đường gửi/nhận — backend cần Source.Address/Dest.Address; nhập cả hai ô rồi báo cước lại"));
    }
    const don = {
      nguoi_gui_tinh: $("cuoc-sc").value.trim(), nguoi_gui_quan: $("cuoc-sd").value.trim(),
      nguoi_gui_xa: $("cuoc-sw").value.trim(), nguoi_gui_dia_chi: diaChiGui,
      nguoi_nhan_tinh: $("cuoc-dc").value.trim(), nguoi_nhan_quan: $("cuoc-dd").value.trim(),
      nguoi_nhan_xa: $("cuoc-dw").value.trim(), nguoi_nhan_dia_chi: diaChiNhan,
      khoi_luong_gram: Number($("cuoc-can").value || 1),
      chieu_dai_mm: Number($("cuoc-dai").value || 0),
      chieu_rong_mm: Number($("cuoc-rong").value || 0),
      chieu_cao_mm: Number($("cuoc-cao").value || 0),
      cod: Number($("cuoc-cod").value || 0),
      gia_tri_khai: Number($("cuoc-gia").value || 0),
    };
    if (!canPheDuyet("kq-cuoc")) return;
    dat("kq-cuoc", "Đang báo cước…");
    try {
      const r = await goi("/api/v2/best/bao-gia", "POST",
        { tai_khoan_id: Number(id), don, xac_nhan_that: xacNhanThat() });
      const kq = r.kq || {};
      if (!r.ok || !kq.ok) {
        const ly = (kq && kq.loi) || (r.kq && r.kq.loi) || `HTTP ${r.ma}`;
        dat("kq-cuoc", `KHÔNG BÁO ĐƯỢC CƯỚC: ${ly}`, "canhbao");
        return;
      }
      const d = kq.data || {};
      const codVal = d.COD != null ? d.COD : d.Cod;
      const dong = [
        `Tổng phí: ${d.TotalFee != null ? d.TotalFee : "?"} VND`,
        `Phí vận chuyển: ${d.FreightFee != null ? d.FreightFee : "?"} · COD fee: ${d.CODFee != null ? d.CODFee : "?"}`,
        `Bảo hiểm: ${d.InsuranceFee != null ? d.InsuranceFee : "?"} · VAT: ${d.FreightFeeVAT != null ? d.FreightFeeVAT : "?"}`,
        `Tổng có VAT: ${d.TotalFeeVAT != null ? d.TotalFeeVAT : "?"} · sau discount: ${d.TotalFeeVATWithDiscount != null ? d.TotalFeeVATWithDiscount : "?"}`,
        `Service: ${d.ServiceType || "?"} · COD: ${codVal != null ? codVal : "?"} · khai giá: ${d.ProductPrice != null ? d.ProductPrice : "?"}`,
        "Lưu ý: hãng trả `Cod` (chữ d thường) ở một số phản hồi; trang đọc cả `COD` và `Cod`.",
      ];
      dat("kq-cuoc", dong.join("\n"), "ok");
    } catch (e) { loi("kq-cuoc", e); }
  }

  async function taoDon(ev) {
    ev.preventDefault();
    const id = $("don-tk").value;
    if (!id) return loi("kq-don", new Error("chưa chọn tài khoản"));
    if (!canPheDuyet("kq-don")) return;
    const xacNhan = $("don-xac-nhan").value.trim();
    if (!xacNhan) return loi("kq-don", new Error("gõ đúng câu xác nhận ghi đơn sandbox"));
    dat("kq-don", "Đang gửi tạo đơn sandbox…");
    try {
      const r = await goi("/api/v2/best/tao-don", "POST", {
        tai_khoan_id: Number(id), don: donTuForm("don-"), xac_nhan_that: xacNhanThat(),
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
    if (!canPheDuyet("kq-tra-cuu")) return;
    dat("kq-tra-cuu", "Đang tra cứu…");
    try {
      const r = await goi("/api/v2/best/tra-cuu", "POST",
        { tai_khoan_id: Number(id), codes: ds, xac_nhan_that: xacNhanThat() });
      const kq = r.kq || {};
      if (!r.ok || !kq.ok) return dat("kq-tra-cuu", `KHÔNG TRA CỨU ĐƯỢC: ${kq.loi || "HTTP " + r.ma}`, "canhbao");
      const rows = (kq.data || []).map((x) => {
        let s = `• ${x.code_best || "?"} · status=${x.status || "?"}`
          + ` · ${x.trang_thai_chung || "chưa map"} · ${x.status_content || ""}`;
        const logs = Array.isArray(x.traceLogs) ? x.traceLogs.slice(-5) : [];
        for (const l of logs) {
          const luc = l.modified_at ? new Date(Number(l.modified_at)).toISOString() : "?";
          s += `\n   - ${String(l.status || "?")} · ${luc} · ${l.status_content || ""}`;
        }
        return s;
      });
      dat("kq-tra-cuu", rows.length ? rows.join("\n") : "Không có kết quả.", "ok");
    } catch (e) { loi("kq-tra-cuu", e); }
  }

  async function inVanDon() {
    const id = $("tc-tk").value;
    const ds = codes();
    if (!id || !ds.length) return loi("kq-tra-cuu", new Error("chọn tài khoản + nhập mã"));
    if (!canPheDuyet("kq-tra-cuu")) return;
    dat("kq-tra-cuu", "Đang lấy URL PDF…");
    try {
      const r = await goi("/api/v2/best/in", "POST",
        { tai_khoan_id: Number(id), codes: ds, xac_nhan_that: xacNhanThat() });
      const kq = r.kq || {};
      if (!r.ok || !kq.ok) return dat("kq-tra-cuu", `KHÔNG IN ĐƯỢC: ${kq.loi || "HTTP " + r.ma}`, "canhbao");
      const url = String(kq.url || "");
      const canhBao = /^http:\/\//i.test(url) ? "\nCẢNH BÁO: URL PDF là HTTP — không tải bằng trình duyệt; cần backend tải qua HTTPS/allowlist." : "";
      dat("kq-tra-cuu", `URL PDF: ${url}${canhBao}`, "ok");
    } catch (e) { loi("kq-tra-cuu", e); }
  }

  async function taiPdf() {
    const id = $("tc-tk").value;
    const ds = codes();
    if (!id || !ds.length) return loi("kq-tra-cuu", new Error("chọn tài khoản + nhập mã"));
    if (!canPheDuyet("kq-tra-cuu")) return;
    dat("kq-tra-cuu", "Đang in và tải PDF qua backend (HTTPS)…");
    try {
      const res = await fetch("/api/v2/best/in-pdf", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-Requested-With": "VIPHub", "Content-Type": "application/json" },
        body: JSON.stringify({ tai_khoan_id: Number(id), codes: ds,
                               xac_nhan_that: xacNhanThat() }),
      });
      if (!res.ok) {
        let kq = {};
        try { kq = await res.json(); } catch (e) { /* không JSON */ }
        throw new Error((kq && kq.loi) || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "BEST-waybill-" + (ds[0] || "pdf").replace(/[^A-Za-z0-9._-]/g, "_") + ".pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      dat("kq-tra-cuu", `Đã tải PDF (${blob.size} byte) qua backend. Không mở URL http trực tiếp.`, "ok");
    } catch (e) { loi("kq-tra-cuu", e); }
  }

  function duLieuCapNhat() {
    const tinh = $("ud-tinh").value.trim();
    const quan = $("ud-quan").value.trim();
    const xa = $("ud-xa").value.trim();
    const dc = $("ud-dc").value.trim();
    const ten = $("ud-ten").value.trim();
    const sdt = $("ud-sdt").value.trim();
    // Cùng một bộ địa chỉ được gửi dưới cả ba tên Source/Dest/Return. Backend chọn đúng bộ
    // theo AddressTypeId; nếu chỉ gửi nguoi_nhan_* thì sửa địa chỉ lấy hàng/trả hàng sẽ dùng
    // dữ liệu cũ của đơn thay vì dữ liệu người dùng vừa nhập.
    const diaChi = {
      tinh, quan, xa, dia_chi: dc, ten, sdt,
    };
    return {
      ma_van_don: $("ud-ma").value.trim(),
      hang_hoa: $("ud-hang").value.trim(),
      cod: Number($("ud-cod").value || 0),
      gia_tri_khai: Number($("ud-gia").value || 0),
      khoi_luong_gram: Number($("ud-can").value || 1),
      chieu_dai_mm: Number($("ud-dai").value || 0),
      chieu_rong_mm: Number($("ud-rong").value || 0),
      chieu_cao_mm: Number($("ud-cao").value || 0),
      address_type_id: Number($("ud-loai-dc").value || 2),
      nguoi_nhan_tinh: diaChi.tinh, nguoi_nhan_quan: diaChi.quan,
      nguoi_nhan_xa: diaChi.xa, nguoi_nhan_dia_chi: diaChi.dia_chi,
      nguoi_nhan_ten: diaChi.ten, nguoi_nhan_sdt: diaChi.sdt,
      nguoi_gui_tinh: diaChi.tinh, nguoi_gui_quan: diaChi.quan,
      nguoi_gui_xa: diaChi.xa, nguoi_gui_dia_chi: diaChi.dia_chi,
      nguoi_gui_ten: diaChi.ten, nguoi_gui_sdt: diaChi.sdt,
      nguoi_tra_tinh: diaChi.tinh, nguoi_tra_quan: diaChi.quan,
      nguoi_tra_xa: diaChi.xa, nguoi_tra_dia_chi: diaChi.dia_chi,
      nguoi_tra_ten: diaChi.ten, nguoi_tra_sdt: diaChi.sdt,
    };
  }

  async function capNhatDon(ev) {
    ev.preventDefault();
    const id = $("ud-tk").value;
    if (!id) return loi("kq-cap-nhat", new Error("chưa chọn tài khoản"));
    if (!canPheDuyet("kq-cap-nhat")) return;
    const xacNhan = $("ud-xac-nhan").value.trim();
    if (!xacNhan) return loi("kq-cap-nhat", new Error("gõ đúng câu xác nhận ghi"));
    dat("kq-cap-nhat", "Đang gửi Order/Update…");
    try {
      const r = await goi("/api/v2/best/cap-nhat", "POST", {
        tai_khoan_id: Number(id), don: duLieuCapNhat(),
        xac_nhan_that: xacNhanThat(), xac_nhan: xacNhan,
      });
      const kq = r.kq || {};
      dat("kq-cap-nhat", kq.ok ? "ĐÃ CẬP NHẬT ĐƠN" : `KHÔNG CẬP NHẬT: ${kq.loi || "HTTP " + r.ma}`,
          kq.ok ? "ok" : "canhbao");
    } catch (e) { loi("kq-cap-nhat", e); }
  }

  async function suaDiaChi() {
    const id = $("ud-tk").value;
    if (!id) return loi("kq-cap-nhat", new Error("chưa chọn tài khoản"));
    if (!canPheDuyet("kq-cap-nhat")) return;
    const xacNhan = $("ud-xac-nhan").value.trim();
    if (!xacNhan) return loi("kq-cap-nhat", new Error("gõ đúng câu xác nhận ghi"));
    dat("kq-cap-nhat", "Đang gửi Order/UpdateAddress…");
    try {
      const r = await goi("/api/v2/best/sua-dia-chi", "POST", {
        tai_khoan_id: Number(id), don: duLieuCapNhat(),
        address_type_id: Number($("ud-loai-dc").value || 2),
        xac_nhan_that: xacNhanThat(), xac_nhan: xacNhan,
      });
      const kq = r.kq || {};
      dat("kq-cap-nhat", kq.ok
        ? `ĐÃ SỬA ĐỊA CHỈ (AddressTypeId=${kq.address_type_id || "?"})`
        : `KHÔNG SỬA ĐƯỢC: ${kq.loi || "HTTP " + r.ma}`, kq.ok ? "ok" : "canhbao");
    } catch (e) { loi("kq-cap-nhat", e); }
  }

  async function huyDon() {
    const id = $("ud-tk").value;
    const ma = $("ud-ma").value.trim();
    if (!id || !ma) return loi("kq-cap-nhat", new Error("chọn tài khoản + nhập mã vận đơn"));
    if (!canPheDuyet("kq-cap-nhat")) return;
    const xacNhan = $("ud-xac-nhan").value.trim();
    if (!xacNhan) return loi("kq-cap-nhat", new Error("gõ đúng câu xác nhận ghi"));
    dat("kq-cap-nhat", "Đang gửi Order/Cancel…");
    try {
      const r = await goi("/api/v2/best/huy", "POST", {
        tai_khoan_id: Number(id), ma_van_don: ma,
        xac_nhan_that: xacNhanThat(), xac_nhan: xacNhan,
      });
      const kq = r.kq || {};
      dat("kq-cap-nhat", kq.ok ? "ĐÃ GỬI HỦY (chỉ trước khi lấy hàng thành công)"
        : `KHÔNG HỦY ĐƯỢC: ${kq.loi || "HTTP " + r.ma}`, kq.ok ? "ok" : "canhbao");
    } catch (e) { loi("kq-cap-nhat", e); }
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
    // Dấu hiệu ĐỒNG BỘ cho biết mã trang đã chạy (bộ thử đọc thuộc tính này thay vì tin vào
    // chữ có sẵn trong HTML). Đặt trước mọi lời gọi mạng để không phụ thuộc tốc độ máy chủ.
    document.documentElement.setAttribute("data-best-uat", "1");
    $("form-tk").addEventListener("submit", luuTaiKhoan);
    $("form-cuoc").addEventListener("submit", baoGia);
    $("form-don").addEventListener("submit", taoDon);
    $("btn-trang-thai").addEventListener("click", () => taiTrangThai(true).catch((e) => loi("trang-thai", e)));
    $("btn-kiem-ket-noi").addEventListener("click", kiemKetNoi);
    $("btn-luu-webhook").addEventListener("click", luuWebhook);
    $("btn-tra-cuu").addEventListener("click", traCuu);
    $("btn-in").addEventListener("click", inVanDon);
    $("btn-tai-pdf").addEventListener("click", taiPdf);
    $("form-cap-nhat").addEventListener("submit", capNhatDon);
    $("btn-sua-dia-chi").addEventListener("click", suaDiaChi);
    $("btn-huy").addEventListener("click", huyDon);
    $("btn-lich-su").addEventListener("click", taiLichSu);
    try {
      await taiTaiKhoan();
      await taiTrangThai(false);
      $("auth").className = "the ok";
      $("auth").textContent = "Đã đăng nhập. Các nút bên dưới gọi backend nội bộ; không có token/secret nào hiển thị.";
    } catch (e) {
      $("auth").className = "the canhbao";
      $("auth").textContent = "Chưa đăng nhập hoặc thiếu quyền: "
        + anBiMat(loiMang((e && e.message) ? e.message : String(e)))
        + " — mở /admin/ để đăng nhập.";
    }
  }

  document.addEventListener("DOMContentLoaded", khoiTao);
})();
