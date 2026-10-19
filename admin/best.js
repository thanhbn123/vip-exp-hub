/* admin/best.js — AGENT B4 · 12 MÀN GIAO DIỆN TÍCH HỢP BEST EXPRESS (tiếng Việt).
 *
 * PHẠM VI / RANH GIỚI — đọc trước khi tin bất kỳ chữ nào trên màn:
 *   - Giao diện LOCAL. KHÔNG gọi API hãng BEST ở bất kỳ môi trường nào. Mọi lời gọi trong
 *     tệp này đều là `/api/v2/*` CÙNG ORIGIN của máy chủ nội bộ; trình duyệt không mở kết nối
 *     ra ngoài. Bộ thử E2E canh đúng điều đó.
 *   - KHÔNG hiển thị credential/token. Không có trường bí mật nào được đưa vào HTML, kể cả
 *     4 ký tự cuối. `credentials_duoi` chỉ được đọc như một BOOLEAN "đã có credential hay
 *     chưa", không bao giờ được in ra.
 *   - LUẬT TRẠNG THÁI (quan trọng nhất): "ĐÃ KẾT NỐI" CHỈ được hiện khi có BẰNG CHỨNG của
 *     một lượt đăng nhập/kiểm tra API THÀNH CÔNG (`kiem_ket_noi.ok === true` kèm thời điểm).
 *     Chỉ lưu credential thì trạng thái là "CHỜ XÁC MINH". Backend khai "da_ket_noi" mà
 *     thiếu bằng chứng thì giao diện KHÔNG tin — hiện CHỜ XÁC MINH kèm cảnh báo.
 *   - Tài liệu API BEST (DOCX) ĐÃ đọc toàn văn 2026-10-19. Tên trường wire, envelope
 *     Result/Message, Bearer và 23 mã trạng thái đã đối chiếu. Bàn nghiệm thu thật nằm ở
 *     `pages/best-uat.html`; các màn tại đây KHÔNG gọi thẳng hãng, KHÔNG hiển thị secret.
 *   - Phần LOGIC THUẦN (trạng thái, khối lượng quy đổi, điều kiện in) không chạm DOM, để bộ
 *     thử Node/E2E kiểm được quyết định mà không cần tin chữ trên màn.
 *
 * Nạp được ở hai nơi:
 *   1. SPA quản trị: `admin/admin.js` nạp tệp này MỘT LẦN khi màn BEST đầu tiên được bấm
 *      (không thêm <script> vào admin/index.html — tệp ấy ngoài phạm vi làn B4).
 *   2. Trang riêng: `pages/best.html` nạp tệp này và tự dựng 12 tab.
 */
(function (dat) {
  "use strict";

  const MA_HANG = "best";
  const TEN_HANG = "BEST Express";
  const CO_VIP = typeof window !== "undefined" && window.VIP;
  const T = (x) => (CO_VIP && typeof VIP.thoat === "function") ? VIP.thoat(x)
    : String(x == null ? "" : x).replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  /* ========================================================================================
     1. NĂM TRẠNG THÁI — tên và màu là hợp đồng với bộ thử và với tài liệu
     ======================================================================================== */
  const TRANG_THAI = {
    chua_cau_hinh: {
      ten: "CHƯA CẤU HÌNH", lop: "hh-xam",
      mo_ta: "Chưa có tài khoản BEST hoặc chưa lưu credential nào.",
    },
    cho_xac_minh: {
      ten: "CHỜ XÁC MINH", lop: "hh-vang",
      mo_ta: "Đã lưu credential nhưng CHƯA có lượt đăng nhập API thành công nào.",
    },
    da_ket_noi: {
      ten: "ĐÃ KẾT NỐI", lop: "hh-xanh",
      mo_ta: "Có bằng chứng đăng nhập API thành công gần nhất và tài khoản đang bật.",
    },
    mat_ket_noi: {
      ten: "MẤT KẾT NỐI", lop: "hh-do",
      mo_ta: "Từng kết nối được nhưng lượt kiểm tra gần nhất thất bại hoặc tài khoản bị khoá.",
    },
    can_xu_ly: {
      ten: "CẦN XỬ LÝ", lop: "hh-do",
      mo_ta: "Kết quả kiểm tra không dùng được (sai xác thực, lỗi lạ, dữ liệu mâu thuẫn) — người vận hành phải sửa.",
    },
  };
  const THU_TU_TRANG_THAI = ["chua_cau_hinh", "cho_xac_minh", "da_ket_noi", "mat_ket_noi", "can_xu_ly"];

  /* ========================================================================================
     2. LOGIC THUẦN — không DOM, không fetch
     ======================================================================================== */

  /** Có credential hay chưa — CHỈ trả boolean. Tuyệt đối không trả giá trị/độ dài/4 ký tự cuối.
   *  `credentials_doi_luc` là dấu vết backend ghi khi lưu credential; `co_credentials` là
   *  trường hợp đồng tương lai. `credentials_duoi` chỉ được dùng làm boolean. */
  function coCredential(tk) {
    if (!tk) return false;
    if (tk.co_credentials === true) return true;
    if (tk.credentials_doi_luc) return true;
    if (tk.credentials_duoi != null && String(tk.credentials_duoi).length > 0) return true;
    return false;
  }

  /** Chuẩn hoá BẰNG CHỨNG đăng nhập API. Chỉ `ok === true` mới là bằng chứng thành công.
   *  `ok === null` (có kết quả nhưng không đọc được) KHÔNG được coi là thành công. */
  function docXacMinh(tk) {
    const x = tk && (tk.kiem_ket_noi || tk.xac_minh_ket_noi);
    if (x && typeof x === "object" && !Array.isArray(x)) {
      const ok = x.ok === true ? true : (x.ok === false ? false : null);
      return {
        biet: true, ok,
        luc: x.luc || x.thoi_diem || null,
        ma_http: (x.ma_http != null ? x.ma_http : (x.http != null ? x.http : null)),
        loi: x.loi || null,
        tre_ms: (x.tre_ms != null ? x.tre_ms : null),
        loai: x.loai || null,
      };
    }
    if (tk && (tk.ket_noi_ok === true || tk.ket_noi_ok === false)) {
      return {
        biet: true, ok: tk.ket_noi_ok,
        luc: tk.ket_noi_luc || null,
        ma_http: (tk.ket_noi_ma_http != null ? tk.ket_noi_ma_http : null),
        loi: tk.ket_noi_loi || null, tre_ms: null, loai: null,
      };
    }
    return { biet: false, ok: null, luc: null, ma_http: null, loi: null, tre_ms: null, loai: null };
  }

  function daTungKetNoi(tk) {
    if (!tk) return false;
    if (tk.da_tung_ket_noi === true || tk.ket_noi_truoc_do_ok === true) return true;
    const truoc = tk.kiem_ket_noi && tk.kiem_ket_noi.truoc_do;
    return !!(truoc && typeof truoc === "object" && truoc.ok === true);
  }

  function tt(ma, moTa, them) {
    const d = TRANG_THAI[ma];
    return Object.assign({
      ma, ten: d.ten, lop: d.lop, mo_ta: moTa || d.mo_ta,
      canh_bao: null, la: false,
      bang_chung: { co_credential: false, xac_minh: null, kich_hoat: null, khai_cua_backend: null },
    }, them || {});
  }

  /**
   * Quyết định 5 trạng thái. Đầu vào: `{ provider, tai_khoan }` (một tài khoản BEST đã chọn).
   *
   * THỨ TỰ LUẬT — cố ý, đừng đảo:
   *   (1) không có tài khoản / không có credential      → CHƯA CẤU HÌNH
   *   (2) có bằng chứng thành công + đang bật           → ĐÃ KẾT NỐI
   *   (3) có bằng chứng thành công + bị khoá            → MẤT KẾT NỐI
   *   (4) bằng chứng thất bại:
   *         - từng kết nối được                        → MẤT KẾT NỐI
   *         - chưa từng, hoặc lỗi xác thực             → CẦN XỬ LÝ
   *   (5) có credential, KHÔNG có bằng chứng            → CHỜ XÁC MINH
   *         (kể cả khi backend khai "da_ket_noi" — khai suông không phải bằng chứng)
   *   (6) trạng thái backend lạ/mâu thuẫn               → CẦN XỬ LÝ, cờ `la`
   */
  function trangThaiKetNoi(hs) {
    hs = hs || {};
    const tk = hs.tai_khoan || null;
    const provider = hs.provider || null;
    const coProvider = !!(provider && provider.ma === MA_HANG);

    if (!tk) {
      return tt("chua_cau_hinh",
        coProvider
          ? "Đã có provider BEST ở backend nhưng doanh nghiệp này CHƯA có tài khoản BEST."
          : "Backend CHƯA có provider BEST (carrier_providers) — giao diện chưa thể cấu hình.",
        { bang_chung: { co_credential: false, xac_minh: null, kich_hoat: null,
                        khai_cua_backend: null, co_provider: coProvider } });
    }

    const coCred = coCredential(tk);
    if (!coCred) {
      return tt("chua_cau_hinh",
        "Tài khoản BEST đã tồn tại nhưng CHƯA có credential nào được lưu.",
        { bang_chung: { co_credential: false, xac_minh: null,
                        kich_hoat: tk.kich_hoat !== 0, khai_cua_backend: null,
                        co_provider: coProvider } });
    }

    const xm = docXacMinh(tk);
    const active = !(tk.kich_hoat === 0 || tk.kich_hoat === false);
    const khai = String(tk.trang_thai_ket_noi || "").trim().toLowerCase();
    const bc = {
      co_credential: true, xac_minh: xm,
      kich_hoat: active, khai_cua_backend: khai || null, co_provider: coProvider,
    };

    // Trạng thái backend khai rõ ràng nhưng KHÔNG phải bằng chứng thành công.
    if (khai === "can_xu_ly" || khai === "loi" || khai === "that_bai") {
      return tt("can_xu_ly", "Backend báo trạng thái cần xử lý cho tài khoản BEST.", { bang_chung: bc });
    }
    if (khai === "mat_ket_noi") {
      return tt("mat_ket_noi", "Backend báo tài khoản BEST đã mất kết nối.", { bang_chung: bc });
    }
    if (khai === "chua_cau_hinh") {
      return tt("can_xu_ly",
        "Dữ liệu mâu thuẫn: backend khai CHƯA CẤU HÌNH nhưng tài khoản đã có credential.",
        { bang_chung: bc });
    }
    if (khai && !["cho_xac_minh", "da_ket_noi"].includes(khai)) {
      return tt("can_xu_ly", `Backend trả trạng thái LẠ "${khai}" — giao diện không đoán nghĩa.`,
        { bang_chung: bc, la: true });
    }

    // BẰNG CHỨNG THÀNH CÔNG — điều kiện duy nhất để được hiện ĐÃ KẾT NỐI.
    if (xm.ok === true && xm.luc) {
      if (active) {
        return tt("da_ket_noi",
          `Đăng nhập API thành công lúc ${xm.luc}${xm.tre_ms != null ? ` (${xm.tre_ms} ms)` : ""}.`,
          { bang_chung: bc });
      }
      return tt("mat_ket_noi",
        "Từng đăng nhập API thành công nhưng tài khoản BEST hiện đang bị khoá.",
        { bang_chung: bc });
    }
    if (xm.ok === true && !xm.luc) {
      return tt("can_xu_ly",
        "Backend báo đăng nhập thành công nhưng THIẾU thời điểm — không đủ bằng chứng để hiện ĐÃ KẾT NỐI.",
        { bang_chung: bc });
    }

    // BẰNG CHỨNG THẤT BẠI.
    if (xm.ok === false) {
      const loiXacThuc = (xm.ma_http === 401 || xm.ma_http === 403 ||
                          ["xac_thuc", "auth", "credentials"].includes(String(xm.loai || "").toLowerCase()));
      if (!active) {
        return tt("mat_ket_noi", "Tài khoản BEST đang bị khoá và lượt kiểm tra gần nhất thất bại.",
          { bang_chung: bc });
      }
      if (daTungKetNoi(tk)) {
        return tt("mat_ket_noi",
          `Từng kết nối được, nhưng lượt kiểm tra gần nhất THẤT BẠI${xm.ma_http ? ` (HTTP ${xm.ma_http})` : ""}${xm.loi ? `: ${xm.loi}` : ""}.`,
          { bang_chung: bc });
      }
      return tt("can_xu_ly",
        `Lượt kiểm tra ĐẦU TIÊN thất bại${xm.ma_http ? ` (HTTP ${xm.ma_http})` : ""}${xm.loi ? `: ${xm.loi}` : ""}.` +
        (loiXacThuc ? " Đây là lỗi xác thực — kiểm lại credential." : ""),
        { bang_chung: bc });
    }

    // Có kết quả nhưng không đọc được ok — không được coi là thành công.
    if (xm.biet && xm.ok === null) {
      return tt("can_xu_ly",
        "Backend trả kết quả kiểm tra nhưng thiếu cờ `ok` đọc được — không đủ bằng chứng để kết luận.",
        { bang_chung: bc });
    }

    if (!active) {
      return tt("can_xu_ly", "Tài khoản BEST đang bị khoá — bật lại trước khi kiểm tra kết nối.",
        { bang_chung: bc });
    }

    // Đây là nhánh CHỐNG NÓI DỐI: credential đã lưu, kể cả backend khai "da_ket_noi",
    // nhưng KHÔNG có bằng chứng đăng nhập API thành công.
    if (khai === "da_ket_noi" || tk.da_ket_noi === true) {
      return tt("cho_xac_minh",
        "Đã lưu credential nhưng CHƯA có bằng chứng đăng nhập API thành công.",
        {
          bang_chung: bc,
          canh_bao: "Backend khai ĐÃ KẾT NỐI nhưng không kèm kết quả đăng nhập API (ok + thời điểm). " +
                    "Giao diện KHÔNG hiện ĐÃ KẾT NỐI khi thiếu bằng chứng — hãy bấm Kiểm tra kết nối.",
        });
    }

    return tt("cho_xac_minh",
      "Đã lưu credential. CHƯA có lượt đăng nhập API thành công nào — bấm Kiểm tra kết nối.",
      { bang_chung: bc });
  }

  /** Khối lượng quy đổi thể tích, đơn vị gram. Công thức phổ biến 6000 cm³/kg — KHÔNG phải
   *  biểu cước của BEST và không dùng để báo giá. Trả null nếu đầu vào không hợp lệ. */
  function tinhKhoiLuongQuyDoi(daiCm, rongCm, caoCm, canNangGram) {
    const d = Number(daiCm), r = Number(rongCm), c = Number(caoCm), w = Number(canNangGram);
    if (![d, r, c, w].every((x) => Number.isFinite(x) && x >= 0)) return null;
    if (!(d > 0 && r > 0 && c > 0)) return null;
    const quyDoi = Math.round((d * r * c / 6000) * 1000);
    return {
      quy_doi_gram: quyDoi,
      can_nang_gram: Math.round(w),
      tinh_cuoc_gram: Math.max(quyDoi, Math.round(w)),
      cong_thuc: "dài × rộng × cao (cm) / 6000 × 1000 = gram",
      nguon: "công thức quy đổi thể tích phổ biến — KHÔNG phải biểu cước BEST",
    };
  }

  /** Chỉ được in khi backend nói rõ đây là nhãn THẬT và không phải môi trường mock. */
  function choPhepIn(meta) {
    return !!(meta && meta.nhan_that === true && meta.la_mock === false);
  }

  /** Bốn trạng thái của một nút gửi BEST — chỉ để hiển thị lý do, không tự gửi. */
  function lyDoChuaGuiDuoc(hs) {
    const st = trangThaiKetNoi(hs);
    if (!hs || !hs.provider) {
      return { duoc: false, ly_do: "CHỜ BACKEND — chưa có adapter/provider BEST trong hệ." };
    }
    if (st.ma !== "da_ket_noi") {
      return { duoc: false, ly_do: `Cần trạng thái ĐÃ KẾT NỐI trước (hiện tại: ${st.ten}).` };
    }
    return {
      duoc: false,
      ly_do: "CHỜ BACKEND — đường gửi đơn BEST chưa được xác nhận. Giao diện KHÔNG đoán endpoint/request schema của hãng.",
    };
  }

  function hoSo(dsHang, dsTaiKhoan) {
    const hang = Array.isArray(dsHang) ? dsHang : [];
    const tk = Array.isArray(dsTaiKhoan) ? dsTaiKhoan : [];
    const provider = hang.find((x) => x && x.ma === MA_HANG) || null;
    const dsBest = tk.filter((x) => x && x.hang === MA_HANG);
    const taiKhoan = dsBest.slice().sort((a, b) =>
      (Number(b.kich_hoat ? 1 : 0) - Number(a.kich_hoat ? 1 : 0)) ||
      (Number(b.id || 0) - Number(a.id || 0)))[0] || null;
    return { provider, tai_khoan: taiKhoan, ds_tai_khoan: dsBest };
  }

  /* ========================================================================================
     3. GỌI API NỘI BỘ — cùng origin, không bao giờ gọi hãng
     ======================================================================================== */
  class LoiApi extends Error {
    constructor(thongDiep, ma, kq) {
      super(thongDiep);
      this.ma = ma;
      this.kq = kq || {};
    }
  }

  async function goi(duong, method, duLieu, headers) {
    let res;
    try {
      res = await fetch(duong, {
        method: method || "GET",
        credentials: "same-origin",
        headers: Object.assign({
          "X-Requested-With": "VIPHub",
          "Content-Type": "application/json",
        }, headers || {}),
        body: duLieu != null ? JSON.stringify(duLieu) : undefined,
      });
    } catch (e) {
      throw new LoiApi("không gọi được máy chủ nội bộ (mất mạng hoặc máy chủ đã tắt)", 0);
    }
    let kq = {};
    try { kq = await res.json(); } catch (e) { /* 204/không JSON */ }
    if (res.status === 401) {
      throw new LoiApi(kq.loi || "phiên đăng nhập đã hết hạn — mở lại trang quản trị để đăng nhập", 401, kq);
    }
    return { ma: res.status, ok: res.ok, kq };
  }

  const cache = { luc: 0, hs: null, hang: [], tai_khoan: [], loi: [] };

  async function taiNen(lamMoi) {
    if (!lamMoi && cache.hs && Date.now() - cache.luc < 4000) return cache;
    const loi = [];
    let hang = [], taiKhoan = [];
    const [h, t] = await Promise.allSettled([
      goi("/api/v2/hang"),
      goi("/api/v2/tai-khoan-hang"),
    ]);
    if (h.status === "fulfilled" && h.value.ma === 200 && Array.isArray(h.value.kq.hang)) {
      hang = h.value.kq.hang;
    } else {
      loi.push("GET /api/v2/hang → " + (h.status === "fulfilled" ? `HTTP ${h.value.ma}` : h.reason.message));
    }
    if (t.status === "fulfilled" && t.value.ma === 200 && Array.isArray(t.value.kq.tai_khoan)) {
      taiKhoan = t.value.kq.tai_khoan;
    } else {
      loi.push("GET /api/v2/tai-khoan-hang → " + (t.status === "fulfilled" ? `HTTP ${t.value.ma}` : t.reason.message));
    }
    cache.luc = Date.now();
    cache.hang = hang;
    cache.tai_khoan = taiKhoan;
    cache.hs = hoSo(hang, taiKhoan);
    // Kết quả kiểm tra trong PHIÊN này chưa được backend lưu (route kiểm tra CHƯA CÓ).
    // Giữ nó để màn không tự mâu thuẫn: badge vừa chuyển ĐÃ KẾT NỐI mà dòng bằng chứng lại
    // ghi "chưa có lượt đăng nhập nào". Backend có kết quả riêng thì ưu tiên backend.
    if (state.xac_minh_tam && cache.hs.tai_khoan &&
        Number(cache.hs.tai_khoan.id) === Number(state.xac_minh_tam.id) &&
        !cache.hs.tai_khoan.kiem_ket_noi) {
      cache.hs.tai_khoan = Object.assign({}, cache.hs.tai_khoan, {
        kiem_ket_noi: state.xac_minh_tam.kiem_ket_noi,
        da_tung_ket_noi: state.xac_minh_tam.da_tung_ket_noi,
      });
    }
    cache.loi = loi;
    return cache;
  }

  function xoaCache() {
    cache.luc = 0;
    cache.hs = null;
    cache.hang = [];
    cache.tai_khoan = [];
    cache.loi = [];
    state.xac_minh_tam = null;
    state.don_id = null;
    state.tra_cuu = null;
    state.in_nhan = null;
    state.thong_bao = null;
    state.ket_qua_kiem = null;
  }

  /* ========================================================================================
     4. DỰNG HTML DÙNG CHUNG
     ======================================================================================== */
  function trangThaiRong(chu) {
    return `<div class="trang-thai-rong"><div class="to">📭</div>${T(chu)}</div>`;
  }

  function hopNguon(ds) {
    return `<div class="hop-nguon" style="margin-top:16px">${T("Nguồn và phạm vi số liệu:")}
      <ul>${(ds || []).map((x) => `<li>${x}</li>`).join("")}</ul></div>`;
  }

  function hopCho(duong, ghiChu) {
    return `<div class="hop-cho-backend" style="margin-top:12px">
      <b>⏳ CHỜ BACKEND — ${T(duong)}</b>
      <div>${T(ghiChu || "Đường này chưa có trong máy chủ nội bộ. Giao diện KHÔNG bịa dữ liệu thay thế.")}</div>
    </div>`;
  }

  function oKpi(nhan, so, phu, mau) {
    return `<div class="the kpi"><div class="nhan">${T(nhan)}</div>
      <div class="so"${mau ? ` style="color:${mau}"` : ""}>${so}</div>
      <div class="phu">${T(phu || "")}</div></div>`;
  }

  function bang(cot, dong, tuyChon) {
    const o = tuyChon || {};
    const dau = cot.map((c) => `<th${c.so ? ' class="so-tien"' : ""}>${T(c.ten)}</th>`).join("");
    const than = (dong && dong.length)
      ? dong.map((r) => `<tr${r.__lop ? ` class="${T(r.__lop)}"` : ""}>` +
          cot.map((c) => {
            let v, laHtml = false;
            if (typeof c.o === "function") { v = c.o(r); laHtml = true; }
            else { v = r[c.k]; laHtml = !!c.html; }
            if (v == null || v === "") v = "—";
            else if (!laHtml) v = T(v);
            return `<td${c.so ? ' class="so-tien"' : ""}>${v}</td>`;
          }).join("") + "</tr>").join("")
      : `<tr><td colspan="${cot.length}">${trangThaiRong(o.rong || "Chưa có dữ liệu để hiển thị.")}</td></tr>`;
    return `<div class="cuon-ngang"><table class="bang"${o.id ? ` id="${T(o.id)}"` : ""}>
      <thead><tr>${dau}</tr></thead><tbody>${than}</tbody></table></div>`;
  }

  function huyHieu(ttObj, id) {
    return `<span class="huy-hieu ${ttObj.lop}${ttObj.la ? " hh-la" : ""}"${id ? ` id="${T(id)}"` : ""} data-best-state="${T(ttObj.ma)}">${T(ttObj.ten)}${ttObj.la ? " ⚠" : ""}</span>`;
  }

  function khoiTrangThai(hs, tuyChon) {
    const o = tuyChon || {};
    const st = trangThaiKetNoi(hs);
    const bc = st.bang_chung || {};
    const xm = bc.xac_minh || {};
    const credChu = bc.co_credential
      ? "đã lưu credential (KHÔNG hiển thị giá trị, KHÔNG hiển thị 4 ký tự cuối)"
      : "chưa lưu credential";
    const xmChu = xm.ok === true
      ? `có — lúc ${T(xm.luc || "?")}${xm.ma_http ? ` · HTTP ${T(String(xm.ma_http))}` : ""}${xm.tre_ms != null ? ` · ${T(String(xm.tre_ms))} ms` : ""}`
      : xm.ok === false
        ? `lần gần nhất THẤT BẠI${xm.ma_http ? ` · HTTP ${T(String(xm.ma_http))}` : ""}${xm.loi ? ` · ${T(xm.loi)}` : ""}`
        : "CHƯA CÓ lượt đăng nhập API nào";
    return `<div class="the best-tt" style="margin-bottom:16px">
      <div class="the-than">
        <div class="best-tt-hang">
          <div>
            <div class="best-nhan">Trạng thái kết nối ${T(TEN_HANG)}</div>
            <div style="margin-top:7px">${huyHieu(st, "best-trang-thai")}</div>
          </div>
          <div class="best-tt-mo">${T(st.mo_ta)}</div>
          <div class="best-tt-nut">
            <button class="nut nut-nho" data-best-di="best-cau-hinh-tai-khoan">🔐 Cấu hình tài khoản</button>
            <button class="nut nut-nho" data-best-di="best-kiem-tra-ket-noi">📡 Kiểm tra kết nối</button>
            <a class="nut nut-nho" href="/pages/best-uat.html" target="_blank"
               rel="noopener">🧪 Bàn nghiệm thu thật (sandbox)</a>
          </div>
        </div>
        <div class="best-bang-chung">
          <span><b>Credential:</b> ${T(credChu)}</span>
          <span><b>Đăng nhập API thành công gần nhất:</b> ${xmChu}</span>
          <span><b>Tài khoản đang bật:</b> ${bc.kich_hoat === false ? "KHÔNG" : (bc.kich_hoat === true ? "có" : "chưa rõ")}</span>
        </div>
        <p class="ghi-chu-nguon" style="margin-top:8px">Luật cứng: <b>ĐÃ KẾT NỐI</b> chỉ hiện khi có
          bằng chứng <code>ok=true</code> kèm thời điểm từ một lượt đăng nhập/kiểm tra API.
          Lưu credential một mình KHÔNG đủ — khi ấy trạng thái là <b>CHỜ XÁC MINH</b>.</p>
      </div>
      ${st.canh_bao ? `<div class="best-canh-bao" id="best-canh-bao-tt">⚠️ ${T(st.canh_bao)}</div>` : ""}
      ${o.them || ""}
    </div>`;
  }

  /** Bảng 5 trạng thái hiển thị NGAY TRÊN MÀN — người vận hành thấy đủ luật, không phải
   *  suy ra từ một nhãn duy nhất. Dòng đang ở được đánh dấu rõ. */
  function khoiBangTrangThai(st) {
    const dieuKien = {
      chua_cau_hinh: "Không có tài khoản BEST, hoặc tài khoản chưa có credential.",
      cho_xac_minh: "Có credential nhưng CHƯA có bằng chứng đăng nhập API thành công (ok=true + thời điểm).",
      da_ket_noi: "Có bằng chứng ok=true + thời điểm và tài khoản đang bật.",
      mat_ket_noi: "Từng kết nối được rồi lượt mới thất bại, hoặc đã kết nối mà tài khoản bị khoá.",
      can_xu_ly: "Lỗi xác thực / lỗi lạ / trạng thái mâu thuẫn — người vận hành phải sửa.",
    };
    const dong = THU_TU_TRANG_THAI.map((ma) => {
      const d = TRANG_THAI[ma];
      return {
        __lop: ma === st.ma ? "dong-hop-le" : "",
        ma,
        trang_thai: huyHieu(Object.assign({}, d, { ma, la: false }), null),
        dieu_kien: dieuKien[ma],
        hien_tai: ma === st.ma ? '<span class="huy-hieu hh-xanh-duong">ĐANG Ở ĐÂY</span>' : "—",
      };
    });
    return `<div class="the" style="margin-top:16px">
      <div class="the-dau"><h2>Năm trạng thái — luật và bằng chứng</h2>
        <div class="phai"><span class="huy-hieu hh-xam">dòng nền xanh = đang ở</span></div></div>
      <div class="the-than">
        ${bang([
          { ten: "Trạng thái", html: true, k: "trang_thai" },
          { ten: "Điều kiện vào", k: "dieu_kien" },
          { ten: "Hiện tại", html: true, k: "hien_tai" },
        ], dong, { id: "best-bang-trang-thai", rong: "Không dựng được bảng trạng thái." })}
        <p class="ghi-chu-nguon" style="margin-top:10px">ĐÂY LÀ LUẬT CỨNG: <b>ĐÃ KẾT NỐI</b> chỉ hiện khi
          có một lượt đăng nhập API THÀNH CÔNG. Lưu credential một mình ⇒ <b>CHỜ XÁC MINH</b>.</p>
      </div>
    </div>`;
  }

  function khoiTaiKhoan(hs) {
    const tk = hs && hs.tai_khoan;
    if (!tk) {
      return `<div class="the" id="best-tai-khoan" style="margin-top:16px">
        <div class="the-dau"><h2>Tài khoản BEST của doanh nghiệp</h2></div>
        <div class="the-than">${trangThaiRong(
          "Chưa có tài khoản BEST nào. Đây KHÔNG phải lỗi kết nối — doanh nghiệp chưa cấu hình tài khoản cho hãng này.")}</div>
      </div>`;
    }
    const dong = [
      { k: "ID nội bộ", v: tk.id },
      { k: "Tên gợi nhớ", v: tk.ten },
      { k: "Mã hãng", v: tk.hang },
      { k: "Môi trường", v: tk.moi_truong },
      { k: "Đang bật", v: tk.kich_hoat ? "có" : "KHÔNG" },
      { k: "Credential", v: coCredential(tk) ? "đã lưu — không hiển thị giá trị" : "chưa lưu" },
      { k: "Credential đổi lúc", v: tk.credentials_doi_luc || "—" },
      { k: "Mã webhook (định danh, không phải secret)", v: tk.webhook_ma || "—" },
    ];
    return `<div class="the" id="best-tai-khoan" style="margin-top:16px">
      <div class="the-dau"><h2>Tài khoản BEST của doanh nghiệp</h2>
        <div class="phai"><span class="huy-hieu hh-xam">KHÔNG hiện credential</span></div></div>
      <div class="the-than">
        <div class="cuon-ngang"><table class="bang bang-hep"><tbody>
          ${dong.map((r) => `<tr><td style="width:240px;color:var(--chu-mo);font-weight:600">${T(r.k)}</td><td>${T(r.v)}</td></tr>`).join("")}
        </tbody></table></div>
        <p class="ghi-chu-nguon" style="margin-top:10px">Trang này KHÔNG hiển thị giá trị credential,
          độ dài, hay 4 ký tự cuối. Nếu backend trả token/secret trong payload, giao diện vẫn không in ra.</p>
      </div>
    </div>`;
  }

  function datMan(tieuDe, html) {
    const t = typeof document !== "undefined" && document.getElementById("tieu-de");
    const m = typeof document !== "undefined" && document.getElementById("man");
    if (t) t.textContent = tieuDe;
    if (m) { m.innerHTML = html; return; }
    const g = typeof document !== "undefined" && document.getElementById("best-noi-dung");
    if (g) g.innerHTML = html;
    const t2 = typeof document !== "undefined" && document.getElementById("best-tieu-de");
    if (t2) t2.textContent = tieuDe;
    if (typeof document !== "undefined") {
      document.querySelectorAll("[data-best-tab]").forEach((n) =>
        n.classList.toggle("hien-tai", n.dataset.bestTab === state.man));
    }
  }

  function moMan(id) {
    if (typeof document === "undefined") return;
    const a = document.querySelector(`.menu-quan-tri a[data-man="${id}"]`);
    if (a) { a.click(); return; }
    if (document.getElementById("best-noi-dung")) {
      state.man = id;
      if (location.hash !== "#" + id) location.hash = "#" + id;
      else veMan(id);
    }
  }

  /* ========================================================================================
     5. MÀN 1 — DANH SÁCH HÃNG (thêm BEST vào danh sách J&T · Viettel Post)
     ======================================================================================== */
  async function manDanhSachHang() {
    state.man = "best-danh-sach-hang";
    const n = await taiNen(true);
    const hs = n.hs;
    const st = trangThaiKetNoi(hs);
    const ds = n.hang.slice();
    if (!ds.some((x) => x && x.ma === MA_HANG)) {
      ds.unshift({ ma: MA_HANG, ten: TEN_HANG, capabilities: {}, live_mo: false, __thieu: true });
    }
    const demTk = (ma) => n.tai_khoan.filter((x) => x && x.hang === ma).length;
    const dong = ds.map((h) => {
      const laBest = h.ma === MA_HANG;
      const tkBest = laBest ? hs.tai_khoan : null;
      const stt = laBest ? st : null;
      const coProvider = !h.__thieu;
      return {
        ma: h.ma,
        ten: h.ten || h.ma,
        provider: coProvider
          ? '<span class="huy-hieu hh-xanh">đã có provider</span>'
          : '<span class="huy-hieu hh-vang">CHƯA CÓ PROVIDER · CHỜ BACKEND</span>',
        tai_khoan: laBest
          ? (tkBest ? `#${T(String(tkBest.id))} · ${T(tkBest.ten || "")}` : '<span class="huy-hieu hh-xam">chưa cấu hình</span>')
          : T(String(demTk(h.ma))),
        trang_thai: laBest
          ? huyHieu(st, null)
          : '<span class="huy-hieu hh-xam">không thuộc phạm vi BEST</span>',
        ho_tro: laBest
          ? (stt && stt.ma === "da_ket_noi" ? "đã xác minh đăng nhập" : "chưa xác minh đăng nhập")
          : (h.capabilities && Object.keys(h.capabilities).length
              ? Object.keys(h.capabilities).filter((k) => h.capabilities[k]).join(" · ")
              : "—"),
        ghi_chu: h.__thieu
          ? "Hàng này do GIAO DIỆN thêm vào danh sách mục tiêu; backend chưa có carrier_providers BEST."
          : (h.live_mo ? "live mở" : "live khoá"),
      };
    });
    datMan("BEST · Danh sách hãng", `
      ${khoiTrangThai(hs)}
      <div class="luoi luoi-kpi">
        ${oKpi("Provider BEST", n.hs.provider ? "CÓ" : "CHƯA CÓ", n.hs.provider ? "carrier_providers có mã best" : "CHỜ BACKEND — chưa có adapter BEST")}
        ${oKpi("Tài khoản BEST", String(n.tai_khoan.filter((x) => x && x.hang === MA_HANG).length), "tài khoản của doanh nghiệp này")}
        ${oKpi("Trạng thái", huyHieu(st, null), st.mo_ta)}
        ${oKpi("Credential", coCredential(hs.tai_khoan) ? "ĐÃ LƯU" : "CHƯA LƯU", "không hiển thị giá trị")}
      </div>
      <div class="the" style="margin-top:16px">
        <div class="the-dau"><h2>Danh sách hãng vận chuyển</h2>
          <div class="phai"><span class="tag-demo">BEST thêm bởi làn B4</span></div></div>
        <div class="the-than">
          ${bang([
            { ten: "Hãng", o: (r) => `<b>${T(r.ten)}</b><div class="ghi-chu-nguon"><code>${T(r.ma)}</code></div>` },
            { ten: "Provider backend", html: true, k: "provider" },
            { ten: "Tài khoản", html: true, k: "tai_khoan" },
            { ten: "Trạng thái BEST", html: true, k: "trang_thai" },
            { ten: "Hỗ trợ / bằng chứng", k: "ho_tro" },
            { ten: "Ghi chú", k: "ghi_chu" },
          ], dong, { id: "best-bang-hang", rong: "Không đọc được danh sách hãng từ máy chủ." })}
          <p class="ghi-chu-nguon" style="margin-top:10px">
            Danh sách này đọc <code>GET /api/v2/hang</code> và <code>GET /api/v2/tai-khoan-hang</code>.
            Hàng <b>BEST Express</b> được giao diện bổ sung vào danh sách mục tiêu khi backend chưa có
            provider — trạng thái của nó KHÔNG được suy ra từ việc "có tài khoản", mà từ bằng chứng
            đăng nhập API.
          </p>
        </div>
      </div>
      ${khoiTaiKhoan(hs)}
      ${n.loi.length ? `<div class="hop-loi" style="margin-top:12px">${n.loi.map(T).join("<br>")}</div>` : ""}
      ${hopNguon([
        "Đường đọc: <code>GET /api/v2/hang</code> · <code>GET /api/v2/tai-khoan-hang</code> (cùng origin nội bộ).",
        "Hai hãng đang có trong hệ: <b>J&amp;T Express</b> và <b>Viettel Post</b>. BEST Express được thêm vào danh sách mục tiêu của làn tích hợp này.",
        "Không gọi API hãng BEST. Không hiển thị credential — kể cả 4 ký tự cuối.",
      ])}
    `);
  }

  /* ========================================================================================
     6. MÀN 2 — CẤU HÌNH TÀI KHOẢN (nhập credential AN TOÀN)
     ======================================================================================== */
  function oNhap(id, nhan, loai, ghiChu) {
    return `<div class="form-nhom">
      <label for="${id}">${T(nhan)}</label>
      <input id="${id}" type="${loai || "text"}" autocomplete="off" spellcheck="false" maxlength="500">
      ${ghiChu ? `<div class="ghi-chu-nguon" style="margin-top:3px">${T(ghiChu)}</div>` : ""}
    </div>`;
  }

  async function manCauHinhTaiKhoan() {
    state.man = "best-cau-hinh-tai-khoan";
    const n = await taiNen(true);
    const hs = n.hs;
    datMan("BEST · Cấu hình tài khoản", `
      ${khoiTrangThai(hs)}
      <div class="the">
        <div class="the-dau"><h2>Nhập tài khoản BEST thật ở bàn nghiệm thu</h2>
          <div class="phai"><span class="huy-hieu hh-xanh">DÙNG ĐƯỢC</span></div></div>
        <div class="the-than">
          <p style="margin-top:0">Tài khoản BEST xác thực bằng <b>Username + Password</b> (không phải
            mã đối tác/secret như J&amp;T). Form nhập credential thật nằm ở bàn nghiệm thu, nơi có
            ô phê duyệt phiên, chốt HTTPS và hiển thị mã lỗi thật của hãng.</p>
          <div class="hop-nguon">
            <b>Đường dùng:</b> <code>POST /api/v2/tai-khoan-hang</code> với
            <code>{hang:"best", moi_truong:"sandbox", credentials:{username,password}}</code>.
            Backend mã hoá credential; API đọc lại KHÔNG trả secret.
          </div>
          <p><a class="nut nut-chinh" href="/pages/best-uat.html" target="_blank"
                rel="noopener">🧪 Mở bàn nghiệm thu BEST (đăng nhập thật)</a></p>
          <p class="ghi-chu-nguon">Không nhập credential thật vào trang HTTP. Bàn nghiệm thu tự chặn
            nếu trang không phải HTTPS.</p>
        </div>
      </div>
      ${khoiTaiKhoan(hs)}
    `);
  }

  /* ========================================================================================
     7. MÀN 3 — KIỂM TRA KẾT NỐI
     ======================================================================================== */
  async function manKiemTraKetNoi() {
    state.man = "best-kiem-tra-ket-noi";
    const n = await taiNen(true);
    const hs = n.hs;
    const st = trangThaiKetNoi(hs);
    datMan("BEST · Kiểm tra kết nối", `
      ${khoiTrangThai(hs)}
      <div class="the">
        <div class="the-dau"><h2>Đăng nhập thử API BEST</h2>
          <div class="phai"><span class="huy-hieu hh-xanh">DÙNG ĐƯỢC</span></div></div>
        <div class="the-than">
          <p style="margin-top:0">Đường thật: <code>POST /api/v2/best/kiem-ket-noi</code> với
            <code>{tai_khoan_id, xac_nhan_that:true}</code>. Backend gọi
            <code>POST /User/Login</code> qua HTTPS, trả <code>ok</code> + HTTP + lý do; KHÔNG trả token.</p>
          <p><a class="nut nut-chinh" href="/pages/best-uat.html" target="_blank"
                rel="noopener">🧪 Kiểm tra kết nối tại bàn nghiệm thu</a></p>
          <p class="ghi-chu-nguon">Trạng thái ĐÃ KẾT NỐI chỉ hiện khi backend trả
            <code>ok=true</code> kèm thời điểm. Lưu credential một mình là CHỜ XÁC MINH.</p>
        </div>
      </div>
      ${khoiBangTrangThai(st)}
    `);
  }

  /* ========================================================================================
     8. MÀN 4 — TẠO ĐƠN BEST (kiểm dữ liệu; KHÔNG gửi hãng)
     ======================================================================================== */
  function truongTaoDon(id, nhan, loai, batBuoc) {
    return `<div class="form-nhom">
      <label for="${id}">${T(nhan)}${batBuoc ? ' <span class="bat-buoc">*</span>' : ""}</label>
      <input id="${id}" type="${loai || "text"}" autocomplete="off" maxlength="300">
    </div>`;
  }

  async function manTaoDon() {
    state.man = "best-tao-don";
    const n = await taiNen(true);
    const hs = n.hs;
    const gui = lyDoChuaGuiDuoc(hs);
    datMan("BEST · Tạo đơn", `
      ${khoiTrangThai(hs)}
      <div class="the">
        <div class="the-dau"><h2>Biểu mẫu đơn BEST</h2>
          <div class="phai"><span class="huy-hieu hh-vang">CHỈ KIỂM DỮ LIỆU · CHƯA GỬI HÃNG</span></div></div>
        <div class="the-than">
          <div class="hop-cho-backend" style="margin-bottom:14px">
            <b>Màn này KHÔNG tạo đơn thật và KHÔNG gọi BEST.</b> Nút "Kiểm tra dữ liệu" gọi
            <code>POST /api/v2/don/kiem</code> — một phép kiểm chỉ đọc. Nút gửi BEST bị khoá với lý do
            hiển thị ngay dưới đây; giao diện không đoán endpoint/request schema của hãng.
          </div>
          <form id="best-form-don" autocomplete="off" novalidate>
            <div class="best-form-luoi">
              ${truongTaoDon("best-dn-nguoi-gui-ten", "Người gửi — tên", "text", true)}
              ${truongTaoDon("best-dn-nguoi-gui-sdt", "Người gửi — SĐT", "tel", true)}
              ${truongTaoDon("best-dn-nguoi-gui-dia-chi", "Người gửi — địa chỉ", "text", true)}
              ${truongTaoDon("best-dn-nguoi-nhan-ten", "Người nhận — tên", "text", true)}
              ${truongTaoDon("best-dn-nguoi-nhan-sdt", "Người nhận — SĐT", "tel", true)}
              ${truongTaoDon("best-dn-nguoi-nhan-dia-chi", "Người nhận — địa chỉ", "text", true)}
              ${truongTaoDon("best-dn-hang-hoa", "Hàng hoá", "text", true)}
              ${truongTaoDon("best-dn-khoi-luong", "Khối lượng (gram)", "number", true)}
              ${truongTaoDon("best-dn-cod", "Thu hộ COD (đồng)", "number", false)}
              ${truongTaoDon("best-dn-gia-tri", "Giá trị khai (đồng)", "number", false)}
            </div>
            <div class="hang-cong-cu" style="margin-top:8px">
              <button class="nut nut-chinh" type="submit" id="best-kiem-don">🔎 Kiểm tra dữ liệu</button>
              <button class="nut" type="button" id="best-gui-don" disabled
                title="${T(gui.ly_do)}">📤 Gửi BEST (bị khoá)</button>
            </div>
            <p class="ghi-chu-nguon" id="best-ly-do-gui" style="margin-top:8px">${T(gui.ly_do)}</p>
          </form>
          <div id="best-kq-kiem" style="margin-top:12px"></div>
        </div>
      </div>
      ${hopNguon([
        "Đường kiểm: <code>POST /api/v2/don/kiem</code> — đã có trong máy chủ nội bộ, chỉ đọc, không ghi đơn.",
        "Không gọi <code>POST /api/v2/don</code>/<code>/gui</code> ở màn này: gửi BEST cần adapter + đường đã xác nhận (CHỜ BACKEND).",
        "Không có đơn thật nào được tạo bởi màn này trong lượt kiểm.",
      ])}
    `);
  }

  async function kiemDon(form) {
    const o = document.getElementById("best-kq-kiem");
    const v = (id) => {
      const n = form.querySelector("#" + id);
      return n ? n.value.trim() : "";
    };
    const payload = {
      nguoi_gui_ten: v("best-dn-nguoi-gui-ten"),
      nguoi_gui_sdt: v("best-dn-nguoi-gui-sdt"),
      nguoi_gui_dia_chi: v("best-dn-nguoi-gui-dia-chi"),
      nguoi_nhan_ten: v("best-dn-nguoi-nhan-ten"),
      nguoi_nhan_sdt: v("best-dn-nguoi-nhan-sdt"),
      nguoi_nhan_dia_chi: v("best-dn-nguoi-nhan-dia-chi"),
      hang_hoa: v("best-dn-hang-hoa"),
      khoi_luong_gram: v("best-dn-khoi-luong"),
      cod: v("best-dn-cod") || 0,
      gia_tri_khai: v("best-dn-gia-tri") || 0,
    };
    if (o) o.innerHTML = '<div class="dang-tai"><span class="xoay"></span>Đang kiểm dữ liệu…</div>';
    try {
      const r = await goi("/api/v2/don/kiem", "POST", payload);
      if (!r.ok) {
        if (o) o.innerHTML = `<div class="hop-loi">Máy chủ trả HTTP ${T(String(r.ma))}: ${T((r.kq && r.kq.loi) || "")}</div>`;
        return;
      }
      const kq = r.kq || {};
      const loi = Array.isArray(kq.loi) ? kq.loi : [];
      const canhBao = Array.isArray(kq.canh_bao) ? kq.canh_bao : [];
      if (o) {
        o.innerHTML = `<div class="${kq.hop_le ? "hop-nguon" : "hop-loi"}" id="best-kq-kiem-noi-dung">
          <b>${kq.hop_le ? "DỮ LIỆU HỢP LỆ" : "DỮ LIỆU CHƯA HỢP LỆ"}</b>
          <div style="margin-top:6px">${loi.length
            ? "<b>Lỗi:</b><ul>" + loi.map((x) => `<li>${T(x)}</li>`).join("") + "</ul>"
            : "Không có lỗi chặn."}</div>
          <div>${canhBao.length
            ? "<b>Cảnh báo (không chặn):</b><ul>" + canhBao.map((x) => `<li>${T(x)}</li>`).join("") + "</ul>"
            : "Không có cảnh báo."}</div>
        </div>`;
      }
    } catch (e) {
      if (o) o.innerHTML = `<div class="hop-loi">Không kiểm được: ${T(e.message)}</div>`;
    }
  }

  /* ========================================================================================
     9. MÀN 5 — DANH SÁCH VẬN ĐƠN
     ======================================================================================== */
  const NHAN_TT = {
    nhap: "nháp", da_duyet: "đã duyệt", dang_gui: "đang gửi", da_gui: "đã gửi",
    huy: "huỷ", da_huy: "huỷ",
  };
  const NHAN_GIAO = {
    cho_lay: "chờ lấy", lay_hang: "lấy hàng", dang_giao: "đang giao",
    giao_thanh_cong: "giao thành công", giao_that_bai: "giao thất bại", hoan_hang: "hoàn hàng",
  };

  async function manVanDon() {
    state.man = "best-van-don";
    const loc = state.loc_hang || "best";
    const duong = `/api/v2/don?gioi_han=200${loc === "best" ? "&hang=best" : ""}`;
    let r;
    try { r = await goi(duong); }
    catch (e) { datMan("BEST · Danh sách vận đơn", `<div class="hop-loi">${T(e.message)}</div>`); return; }
    const ds = (r.ok && Array.isArray(r.kq.don)) ? r.kq.don : [];
    const dong = ds.map((d) => ({
      id: d.id,
      ma_don: d.ma_don,
      nguoi_nhan: `${d.nguoi_nhan_ten || "—"} · ${d.nguoi_nhan_sdt || ""}`,
      tt: T(NHAN_TT[d.trang_thai] || d.trang_thai || "—"),
      giao: d.trang_thai_giao ? T(NHAN_GIAO[d.trang_thai_giao] || d.trang_thai_giao) : "—",
      van_don: d.ma_van_don || "—",
      cod: d.cod != null ? String(d.cod) : "—",
      luc: d.tao_luc || "—",
    }));
    datMan("BEST · Danh sách vận đơn", `
      <div class="the">
        <div class="the-dau"><h2>Vận đơn ${loc === "best" ? "của BEST" : "của mọi hãng"}</h2>
          <div class="phai">
            <label class="ghi-chu-nguon" for="best-loc-hang">Lọc:</label>
            <select id="best-loc-hang" class="nut" style="padding:5px 9px">
              <option value="best"${loc === "best" ? " selected" : ""}>Chỉ đơn gán BEST</option>
              <option value="tat_ca"${loc === "tat_ca" ? " selected" : ""}>Tất cả đơn</option>
            </select>
          </div></div>
        <div class="the-than">
          ${loc === "best" ? `<div class="hop-cho-backend" style="margin-bottom:14px">
            Chưa có adapter BEST ở backend, nên dữ liệu mẫu hiện có (J&amp;T · Viettel Post) chưa
            gán được vào tài khoản BEST. Chọn <b>Tất cả đơn</b> để đo đường đọc thật trên dữ liệu
            đang có.
          </div>` : ""}
          ${bang([
            { ten: "ID", so: true, k: "id" },
            { ten: "Mã đơn", k: "ma_don" },
            { ten: "Người nhận", k: "nguoi_nhan" },
            { ten: "Nghiệp vụ", k: "tt" },
            { ten: "Giao vận", k: "giao" },
            { ten: "Mã vận đơn", k: "van_don" },
            { ten: "COD", so: true, k: "cod" },
            { ten: "Tạo lúc", k: "luc" },
            { ten: "", o: (x) => `<button class="nut nut-nho" data-best-don="${T(String(x.id))}">Chi tiết →</button>` },
          ], dong, {
            id: "best-bang-don",
            rong: loc === "best"
              ? "Chưa có đơn nào gán tài khoản BEST. Đây là CHỜ BACKEND (chưa có adapter BEST), không phải lỗi giao diện."
              : "Máy chủ không trả đơn nào cho doanh nghiệp này.",
          })}
          <p class="ghi-chu-nguon" style="margin-top:10px">Nguồn: <code>GET ${T(duong)}</code>
            · ${T(String(ds.length))} đơn · đọc từ CSDL nội bộ, KHÔNG gọi hãng.</p>
        </div>
      </div>
    `);
  }

  /* ========================================================================================
     10. MÀN 6 — CHI TIẾT ĐƠN
     ======================================================================================== */
  function khoiChonDon(idHienTai, nhanNut) {
    return `<form id="best-form-chon-don" class="hang-cong-cu" autocomplete="off" style="margin-bottom:12px">
      <label for="best-don-id" class="ghi-chu-nguon">ID đơn nội bộ:</label>
      <input id="best-don-id" type="number" min="1" step="1" style="width:150px;padding:7px 10px;border:1px solid var(--vien);border-radius:8px"
        value="${idHienTai ? T(String(idHienTai)) : ""}" placeholder="ví dụ 1">
      <button class="nut nut-nho" type="submit" id="best-mo-don">${T(nhanNut || "Mở đơn")}</button>
      <span class="ghi-chu-nguon">Không gọi hãng — chỉ đọc CSDL nội bộ.</span>
    </form>`;
  }

  async function manChiTietDon() {
    state.man = "best-chi-tiet-don";
    const id = state.don_id;
    if (!id) {
      datMan("BEST · Chi tiết đơn", `
        ${khoiChonDon(null, "Mở đơn")}
        ${trangThaiRong("Chưa chọn đơn. Nhập ID đơn ở trên, hoặc mở từ màn Danh sách vận đơn để xem chi tiết.")}
      `);
      return;
    }
    let r;
    try { r = await goi(`/api/v2/don/${encodeURIComponent(id)}`); }
    catch (e) { datMan("BEST · Chi tiết đơn", `${khoiChonDon(id)}<div class="hop-loi">${T(e.message)}</div>`); return; }
    if (r.ma === 404 || !r.ok) {
      datMan("BEST · Chi tiết đơn", `
        ${khoiChonDon(id)}
        <div class="hop-loi">Máy chủ trả HTTP ${T(String(r.ma))}: ${T((r.kq && r.kq.loi) || "không có đơn này")}</div>
      `);
      return;
    }
    const d = r.kq.don || {};
    const ls = Array.isArray(r.kq.lich_su) ? r.kq.lich_su : [];
    const dong = [
      ["Mã đơn", d.ma_don],
      ["Mã vận đơn", d.ma_van_don || "chưa có"],
      ["Trạng thái nghiệp vụ", NHAN_TT[d.trang_thai] || d.trang_thai],
      ["Trạng thái giao vận", d.trang_thai_giao ? (NHAN_GIAO[d.trang_thai_giao] || d.trang_thai_giao) : "chưa có"],
      ["Tài khoản hãng", d.carrier_account_id == null ? "chưa gán" : `#${d.carrier_account_id}`],
      ["Người gửi", `${d.nguoi_gui_ten || "—"} · ${d.nguoi_gui_sdt || ""} · ${d.nguoi_gui_dia_chi || ""}`],
      ["Người nhận", `${d.nguoi_nhan_ten || "—"} · ${d.nguoi_nhan_sdt || ""} · ${d.nguoi_nhan_dia_chi || ""}`],
      ["Hàng hoá", d.hang_hoa || "—"],
      ["Khối lượng", d.khoi_luong_gram != null ? `${d.khoi_luong_gram} g` : "—"],
      ["COD", d.cod != null ? String(d.cod) : "—"],
      ["Giá trị khai", d.gia_tri_khai != null ? String(d.gia_tri_khai) : "—"],
      ["Tạo lúc", d.tao_luc || "—"],
      ["Cập nhật lúc", d.cap_nhat_luc || "—"],
    ];
    datMan("BEST · Chi tiết đơn", `
      ${khoiChonDon(id)}
      <div class="luoi luoi-2">
        <div class="the"><div class="the-dau"><h2>Thông tin đơn #${T(String(id))}</h2></div>
          <div class="the-than"><div class="cuon-ngang"><table class="bang bang-hep"><tbody>
            ${dong.map(([k, v]) => `<tr><td style="width:190px;color:var(--chu-mo);font-weight:600">${T(k)}</td><td>${T(v == null || v === "" ? "—" : v)}</td></tr>`).join("")}
          </tbody></table></div></div></div>
        <div class="the"><div class="the-dau"><h2>Lịch sử gần nhất</h2>
          <div class="phai"><button class="nut nut-nho" data-best-di="best-lich-su-van-chuyen">Xem đầy đủ →</button></div></div>
          <div class="the-than">
            ${ls.length ? `<ul class="dong-thoi-gian">${ls.slice(-6).map((x) => `
              <li class="nguon-${T(x.nguon || "khac")}">
                <div class="luc">${T(x.luc || "")}</div>
                <div class="noi">${T(x.noi_dung || "")}</div>
                <div class="nguon">nguồn: ${T(x.nguon || "?")}</div>
              </li>`).join("")}</ul>`
              : trangThaiRong("Đơn chưa có mốc lịch sử nào trong CSDL nội bộ.")}
          </div></div>
      </div>
      <div class="hang-cong-cu" style="margin-top:14px">
        <button class="nut" data-best-di="best-in-van-don">🖨️ In vận đơn</button>
        <button class="nut" data-best-di="best-van-don">← Danh sách vận đơn</button>
      </div>
      ${hopNguon([
        `Đường đọc: <code>GET /api/v2/don/${T(String(id))}</code> — có kiểm tenant ở backend.`,
        "Không gọi hãng. Không hiển thị credential.",
      ])}
    `);
  }

  /* ========================================================================================
     11. MÀN 7 — LỊCH SỬ VẬN CHUYỂN
     ======================================================================================== */
  async function manLichSuVanChuyen() {
    state.man = "best-lich-su-van-chuyen";
    const id = state.don_id;
    if (!id) {
      datMan("BEST · Lịch sử vận chuyển", `
        ${khoiChonDon(null, "Xem hành trình")}
        ${trangThaiRong("Chưa chọn đơn. Nhập ID đơn để xem các mốc vận chuyển lấy từ CSDL nội bộ.")}
      `);
      return;
    }
    let r;
    try { r = await goi(`/api/v2/don/${encodeURIComponent(id)}/hanh-trinh`); }
    catch (e) { datMan("BEST · Lịch sử vận chuyển", `${khoiChonDon(id)}<div class="hop-loi">${T(e.message)}</div>`); return; }
    if (!r.ok) {
      datMan("BEST · Lịch sử vận chuyển", `
        ${khoiChonDon(id)}
        <div class="hop-loi">Máy chủ trả HTTP ${T(String(r.ma))}: ${T((r.kq && r.kq.loi) || "không đọc được hành trình")}</div>
      `);
      return;
    }
    const kq = r.kq || {};
    const moc = Array.isArray(kq.moc) ? kq.moc : [];
    datMan("BEST · Lịch sử vận chuyển", `
      ${khoiChonDon(id, "Xem hành trình")}
      <div class="luoi luoi-kpi">
        ${oKpi("Mã đơn", T(kq.ma_don || "—"), `ID ${T(String(id))}`)}
        ${oKpi("Mã vận đơn", T(kq.ma_van_don || "chưa có"), "từ hãng — chỉ có sau khi gửi thành công")}
        ${oKpi("Số mốc", T(String(kq.so_moc == null ? moc.length : kq.so_moc)), "đọc từ don_lich_su")}
        ${oKpi("Trạng thái giao", T(NHAN_GIAO[kq.trang_thai_giao] || kq.trang_thai_giao || "chưa có"), T(kq.hang_trang_thai_giao || ""))}
      </div>
      <div class="the" style="margin-top:16px">
        <div class="the-dau"><h2>Dòng thời gian</h2></div>
        <div class="the-than">
          ${moc.length ? `<ul class="dong-thoi-gian" id="best-hanh-trinh">${moc.map((x) => `
            <li class="nguon-${T(x.nguon || "khac")}">
              <div class="luc">${T(x.luc || "")}</div>
              <div class="noi">${T(x.noi_dung || "")}</div>
              <div class="nguon">nguồn: ${T(x.nguon || "?")}${x.trang_thai_giao ? ` · trạng thái giao: ${T(NHAN_GIAO[x.trang_thai_giao] || x.trang_thai_giao)}` : ""}</div>
            </li>`).join("")}</ul>`
            : trangThaiRong("Chưa có mốc vận chuyển nào trong CSDL nội bộ cho đơn này.")}
          <p class="ghi-chu-nguon" style="margin-top:10px">Nguồn (nguyên văn từ backend):
            <i>${T(kq.nguon_du_lieu || "")}</i>. Đây không phải dữ liệu live của BEST; chưa gọi hãng.</p>
        </div>
      </div>
      ${hopNguon([
        `Đường đọc: <code>GET /api/v2/don/${T(String(id))}/hanh-trinh</code> — KHÔNG gọi hãng.`,
        "Hành trình trộn lịch sử nghiệp vụ và sự kiện giao vận; nguồn ghi rõ ở backend.",
      ])}
    `);
  }

  /* ========================================================================================
     12. MÀN 8 — TRA CỨU HÀNH TRÌNH
     ======================================================================================== */
  async function manTraCuuHanhTrinh() {
    state.man = "best-tra-cuu-hanh-trinh";
    const tc = state.tra_cuu;
    datMan("BEST · Tra cứu hành trình", `
      <div class="the">
        <div class="the-dau"><h2>Tra cứu theo mã đơn / mã vận đơn / SĐT</h2></div>
        <div class="the-than">
          <form id="best-form-tra-cuu" class="hang-cong-cu" autocomplete="off">
            <input id="best-ma-tra-cuu" type="search" maxlength="120"
              placeholder="ví dụ T1-000001 hoặc mã vận đơn"
              style="flex:1;min-width:220px;padding:8px 12px;border:1px solid var(--vien);border-radius:8px">
            <button class="nut nut-chinh" type="submit" id="best-nut-tra-cuu">🔎 Tra cứu</button>
            <span class="ghi-chu-nguon">Tìm trong đơn của doanh nghiệp — không gọi hãng.</span>
          </form>
          ${tc ? `
            <p class="ghi-chu-nguon" style="margin-top:10px">Từ khoá: <b>${T(tc.q)}</b>
              · ${T(String(tc.tong))} kết quả · <code>GET ${T(tc.duong)}</code></p>
            ${bang([
              { ten: "ID", so: true, k: "id" },
              { ten: "Mã đơn", k: "ma_don" },
              { ten: "Mã vận đơn", k: "ma_van_don" },
              { ten: "Người nhận", k: "nguoi_nhan_ten" },
              { ten: "Nghiệp vụ", o: (x) => T(NHAN_TT[x.trang_thai] || x.trang_thai || "—") },
              { ten: "Giao vận", o: (x) => T(x.trang_thai_giao ? (NHAN_GIAO[x.trang_thai_giao] || x.trang_thai_giao) : "—") },
              { ten: "", o: (x) => `<button class="nut nut-nho" data-best-don="${T(String(x.id))}" data-best-di="best-lich-su-van-chuyen">Hành trình →</button>` },
            ], tc.rows, { id: "best-bang-tra-cuu", rong: "Không tìm thấy đơn nào khớp từ khoá. Đây là kết quả THẬT từ CSDL nội bộ, không phải lỗi mạng." })}
          ` : trangThaiRong("Nhập từ khoá rồi bấm Tra cứu. Màn này tìm trong CSDL nội bộ của doanh nghiệp, không gọi API BEST.")}
        </div>
      </div>
      ${hopNguon([
        "Đường đọc: <code>GET /api/v2/don?q=&lt;từ khoá&gt;&amp;gioi_han=20</code> — có kiểm tenant ở backend.",
        "Chỉ tìm trong đơn của doanh nghiệp đang đăng nhập; không có đường nào nhận tenant_id từ client.",
      ])}
    `);
  }

  async function traCuu(form) {
    const q = ((form.querySelector("#best-ma-tra-cuu") || {}).value || "").trim();
    if (!q) {
      state.tra_cuu = null;
      return manTraCuuHanhTrinh();
    }
    const duong = `/api/v2/don?q=${encodeURIComponent(q)}&gioi_han=20`;
    let r;
    try { r = await goi(duong); }
    catch (e) {
      state.tra_cuu = { q, rows: [], tong: 0, duong, loi: e.message };
      return manTraCuuHanhTrinh();
    }
    const rows = (r.ok && Array.isArray(r.kq.don)) ? r.kq.don : [];
    state.tra_cuu = { q, rows, tong: rows.length, duong, ma: r.ma };
    return manTraCuuHanhTrinh();
  }

  /* ========================================================================================
     13. MÀN 9 — TÍNH CƯỚC (chuẩn bị đầu vào; KHÔNG bịa biểu cước)
     ======================================================================================== */
  async function manTinhCuoc() {
    state.man = "best-tinh-cuoc";
    const n = await taiNen(false);
    const hs = n.hs;
    datMan("BEST · Tính cước", `
      ${khoiTrangThai(hs)}
      <div class="the">
        <div class="the-dau"><h2>Bước 1 — khối lượng tính cước</h2>
          <div class="phai"><span class="huy-hieu hh-xam">công thức chung, KHÔNG phải biểu cước BEST</span></div></div>
        <div class="the-than">
          <form id="best-form-cuoc" class="best-form-luoi" autocomplete="off" novalidate>
            <div class="form-nhom"><label for="best-cuoc-dai">Dài (cm)</label><input id="best-cuoc-dai" type="number" min="1" step="0.1" value="30"></div>
            <div class="form-nhom"><label for="best-cuoc-rong">Rộng (cm)</label><input id="best-cuoc-rong" type="number" min="1" step="0.1" value="20"></div>
            <div class="form-nhom"><label for="best-cuoc-cao">Cao (cm)</label><input id="best-cuoc-cao" type="number" min="1" step="0.1" value="10"></div>
            <div class="form-nhom"><label for="best-cuoc-can">Cân nặng thực (gram)</label><input id="best-cuoc-can" type="number" min="0" step="1" value="800"></div>
          </form>
          <div class="hang-cong-cu" style="margin-top:10px">
            <button class="nut nut-chinh" id="best-tinh-khoi-luong">⚖️ Tính khối lượng tính cước</button>
          </div>
          <div id="best-kq-khoi-luong" style="margin-top:12px"></div>
        </div>
      </div>
      <div class="the" style="margin-top:16px">
        <div class="the-dau"><h2>Bước 2 — báo giá cước BEST</h2>
          <div class="phai"><span class="huy-hieu hh-vang">CHƯA KIỂM CHỨNG</span></div></div>
        <div class="the-than">
          <div class="hop-nguon" id="best-gia-best">
            <b>Báo giá cước BEST thật nằm ở bàn nghiệm thu.</b>
            Đường đã có: <code>POST /api/v2/best/bao-gia</code> → backend gọi
            <code>POST /Service/EstimateFee</code> và trả <code>data.TotalFee</code> (kèm
            <code>Cod</code>/<code>COD</code>, VAT, bảo hiểm). Màn này chỉ tính khối lượng quy đổi,
            <b>không hiển thị số tiền tự bịa</b>. <a href="/pages/best-uat.html" target="_blank"
            rel="noopener">Mở bàn nghiệm thu →</a>
          </div>
          <p class="ghi-chu-nguon" style="margin-top:10px">Không có số tiền nào trên màn này là giá
            cước BEST. Khối lượng quy đổi chỉ là đầu vào; giá do hãng trả về sau khi có hợp đồng/biểu cước.</p>
        </div>
      </div>
      ${hopNguon([
        "Công thức thể tích: dài × rộng × cao (cm) / 6000 × 1000 = gram — công thức quy đổi phổ biến, KHÔNG phải biểu cước BEST.",
        "Không gọi API hãng, không gọi endpoint báo giá chưa xác nhận. Không bịa số tiền.",
      ])}
    `);
  }

  function tinhCuocTrenMan() {
    const g = (id) => Number((document.getElementById(id) || {}).value);
    const kq = tinhKhoiLuongQuyDoi(g("best-cuoc-dai"), g("best-cuoc-rong"),
                                   g("best-cuoc-cao"), g("best-cuoc-can"));
    const o = document.getElementById("best-kq-khoi-luong");
    if (!o) return;
    if (!kq) {
      o.innerHTML = '<div class="hop-loi">Kích thước phải lớn hơn 0 và cân nặng không âm.</div>';
      return;
    }
    o.innerHTML = `<div class="hop-nguon" id="best-kq-khoi-luong-noi-dung">
      <b>Khối lượng quy đổi: ${T(String(kq.quy_doi_gram))} g</b> ·
      <b>Khối lượng tính cước: ${T(String(kq.tinh_cuoc_gram))} g</b>
      <div style="margin-top:5px">Cân thực ${T(String(kq.can_nang_gram))} g so với quy đổi ${T(String(kq.quy_doi_gram))} g —
        lấy số lớn hơn. <i>${T(kq.nguon)}.</i></div>
      <div class="ghi-chu-nguon" style="margin-top:5px">Không có giá cước nào được tính ở bước này.</div>
    </div>`;
  }

  /* ========================================================================================
     14. MÀN 10 — IN VẬN ĐƠN
     ======================================================================================== */
  async function manInVanDon() {
    state.man = "best-in-van-don";
    const id = state.don_id;
    if (state.in_nhan && state.in_nhan.don_id != null && Number(state.in_nhan.don_id) !== Number(id)) {
      state.in_nhan = null;   // không bao giờ hiện siêu dữ liệu của đơn KHÁC
    }
    const meta = state.in_nhan;
    datMan("BEST · In vận đơn", `
      ${khoiChonDon(id, "Lấy siêu dữ liệu nhãn")}
      ${!id ? trangThaiRong("Chưa chọn đơn. Nhập ID đơn để đọc siêu dữ liệu nhãn từ backend nội bộ.") : ""}
      ${id && !meta ? `<div class="the"><div class="the-than"><div class="dang-tai"><span class="xoay"></span>Chưa đọc nhãn — bấm nút phía trên.</div></div></div>` : ""}
      ${meta && meta.__loi ? `<div class="hop-loi" id="best-loi-nhan">Máy chủ trả HTTP ${T(String(meta.__ma || "?"))}: ${T(meta.__loi)}</div>` : ""}
      ${meta && !meta.__loi ? khoiNhan(id, meta) : ""}
      <div class="the" style="margin-top:16px">
        <div class="the-dau"><h2>Vì sao chưa in được nhãn BEST</h2></div>
        <div class="the-than">
          <p style="margin-top:0">Đường <code>GET /api/v2/don/&lt;id&gt;/nhan</code> chỉ trả
            <b>siêu dữ liệu</b>. Mọi adapter đang khoá live, nên nhãn hãng thật chưa tồn tại.
            Giao diện chỉ cho in khi backend nói rõ <code>nhan_that=true</code> và
            <code>la_mock=false</code>; ngược lại nút in bị khoá.</p>
          ${hopCho("byte nhãn BEST", "Backend chưa trả nội dung nhãn PDF/ZPL. Không có nhãn giả nào được in ra để tránh dán nhầm.")}
        </div>
      </div>
      ${hopNguon([
        `Đường đọc: <code>GET /api/v2/don/${id ? T(String(id)) : "&lt;id&gt;"}/nhan</code> — siêu dữ liệu, không phải nhãn thật.`,
        "Không in nhãn giả; không gọi hãng; không tải tệp nhãn từ nguồn ngoài.",
      ])}
    `);
  }

  function khoiNhan(id, meta) {
    const inDuoc = choPhepIn(meta);
    return `<div class="the" id="best-khoi-nhan" style="margin-top:16px">
      <div class="the-dau"><h2>Siêu dữ liệu nhãn</h2>
        <div class="phai"><span class="huy-hieu ${inDuoc ? "hh-xanh" : "hh-do"}">${inDuoc ? "NHÃN THẬT" : "KHÔNG PHẢI NHÃN THẬT"}</span></div></div>
      <div class="the-than">
        ${inDuoc ? "" : `<div class="best-watermark">KHÔNG PHẢI NHÃN HÃNG — CHƯA CÓ NHÃN THẬT</div>`}
        <div class="cuon-ngang"><table class="bang bang-hep"><tbody>
          <tr><td style="width:220px;color:var(--chu-mo);font-weight:600">Mã đơn</td><td>${T(meta.ma_don || "—")}</td></tr>
          <tr><td style="color:var(--chu-mo);font-weight:600">Mã vận đơn</td><td>${T(meta.ma_van_don || "—")}</td></tr>
          <tr><td style="color:var(--chu-mo);font-weight:600">Hãng / môi trường</td><td>${T(meta.ten_hang || meta.hang || "—")} · ${T(meta.moi_truong || "—")}</td></tr>
          <tr><td style="color:var(--chu-mo);font-weight:600">Hỗ trợ nhãn</td><td>${meta.ho_tro_nhan ? "có" : "không"}</td></tr>
          <tr><td style="color:var(--chu-mo);font-weight:600">Nhãn thật</td><td>${meta.nhan_that === true ? "CÓ" : "KHÔNG — mock/không có nhãn"}</td></tr>
          <tr><td style="color:var(--chu-mo);font-weight:600">Định dạng / số byte</td><td>${T(meta.dinh_dang || "—")} · ${T(meta.do_lon_byte == null ? "—" : String(meta.do_lon_byte))}</td></tr>
          <tr><td style="color:var(--chu-mo);font-weight:600">Cảnh báo từ backend</td><td>${(meta.canh_bao || []).length ? (meta.canh_bao || []).map(T).join("<br>") : "—"}</td></tr>
        </tbody></table></div>
        <div class="hang-cong-cu" style="margin-top:12px">
          <button class="nut" id="best-in-nhan"${inDuoc ? "" : " disabled"}>🖨️ In nhãn</button>
          <span class="ghi-chu-nguon">${inDuoc ? "Backend khai nhãn thật — nút mở hộp thoại in của trình duyệt." : "Nút in bị khoá: backend KHÔNG khai nhãn thật. Không in phiếu giả."}</span>
        </div>
      </div>
    </div>`;
  }

  async function layNhan(id) {
    try {
      const r = await goi(`/api/v2/don/${encodeURIComponent(id)}/nhan`);
      state.in_nhan = r.ok
        ? Object.assign({ don_id: Number(id) }, r.kq || {})
        : { don_id: Number(id), __loi: (r.kq && r.kq.loi) || `HTTP ${r.ma}`, __ma: r.ma };
    } catch (e) {
      state.in_nhan = { don_id: Number(id), __loi: e.message, __ma: e.ma || 0 };
    }
    return manInVanDon();
  }

  /* ========================================================================================
     15. MÀN 11 — THEO DÕI WEBHOOK
     ======================================================================================== */
  async function manTheoDoiWebhook() {
    state.man = "best-theo-doi-webhook";
    const n = await taiNen(false);
    const hs = n.hs;
    let r;
    try { r = await goi("/api/v2/webhook/su-kien?gioi_han=200"); }
    catch (e) { datMan("BEST · Theo dõi webhook", `${khoiTrangThai(hs)}<div class="hop-loi">${T(e.message)}</div>`); return; }
    if (!r.ok) {
      datMan("BEST · Theo dõi webhook", `${khoiTrangThai(hs)}
        <div class="hop-loi">Máy chủ trả HTTP ${T(String(r.ma))}: ${T((r.kq && r.kq.loi) || "không đọc được sự kiện webhook")}</div>`);
      return;
    }
    const tatCa = Array.isArray(r.kq.su_kien) ? r.kq.su_kien : [];
    const ds = tatCa.filter((x) => x && x.hang === MA_HANG);
    const tk = hs.tai_khoan;
    datMan("BEST · Theo dõi webhook", `
      ${khoiTrangThai(hs)}
      <div class="luoi luoi-kpi">
        ${oKpi("Sự kiện BEST", T(String(ds.length)), `trong ${T(String(tatCa.length))} sự kiện của tenant`)}
        ${oKpi("Mã webhook", tk && tk.webhook_ma ? `<span class="best-ma">…/nhan/${T(tk.webhook_ma)}</span>` : "CHƯA CÓ", "định danh công khai trong URL — KHÔNG phải secret")}
        ${oKpi("Cần soát", T(String(ds.filter((x) => x.can_soat).length)), "cột can_soat của backend")}
        ${oKpi("Lỗi cuối", T(String(ds.filter((x) => x.loi_cuoi).length)), "sự kiện có loi_cuoi")}
      </div>
      <div class="the" style="margin-top:16px">
        <div class="the-dau"><h2>Sự kiện webhook của BEST</h2>
          <div class="phai"><span class="tag-demo">CHỈ ĐỌC</span></div></div>
        <div class="the-than">
          ${bang([
            { ten: "ID", so: true, k: "id" },
            { ten: "Event ID", k: "event_id" },
            { ten: "Nhận lúc", k: "nhan_luc" },
            { ten: "Trạng thái", k: "trang_thai" },
            { ten: "Số lần thử", so: true, k: "so_lan_thu" },
            { ten: "Cần soát", o: (x) => x.can_soat ? '<span class="huy-hieu hh-vang">CÓ</span>' : "—" },
            { ten: "Lỗi cuối", k: "loi_cuoi" },
            { ten: "Tài khoản", k: "ten_tk" },
          ], ds, {
            id: "best-bang-webhook",
            rong: "Chưa có sự kiện webhook nào của BEST. Đây là dữ liệu THẬT từ CSDL nội bộ — không có sự kiện giả nào được dựng.",
          })}
          <p class="ghi-chu-nguon" style="margin-top:10px">
            Nguồn: <code>GET /api/v2/webhook/su-kien</code> — lọc <code>hang=best</code> tại trang từ
            ${T(String(tatCa.length))} sự kiện. Không hiển thị payload thô/chữ ký; hai thứ ấy có thể
            chứa secret. Không có nút replay ở màn này (ghi dữ liệu là việc khác).
          </p>
        </div>
      </div>
      ${hopNguon([
        "Đường đọc: <code>GET /api/v2/webhook/su-kien</code> — có kiểm tenant ở backend.",
        "Chữ ký webhook được backend xác thực trước khi lưu; giao diện không nhận/không hiện secret chữ ký.",
        ds.length === 0 ? "Chưa có sự kiện BEST: trạng thái này KHÔNG chứng minh webhook hỏng — có thể hãng chưa gửi." : "Sự kiện BEST đang có trong CSDL nội bộ.",
      ])}
    `);
  }

  /* ========================================================================================
     16. MÀN 12 — NHẬT KÝ LỖI ĐỒNG BỘ
     ======================================================================================== */
  async function manNhatKyLoi() {
    state.man = "best-nhat-ky-loi";
    let r;
    try { r = await goi("/api/v2/audit"); }
    catch (e) { datMan("BEST · Nhật ký lỗi đồng bộ", `<div class="hop-loi">${T(e.message)}</div>`); return; }
    if (!r.ok) {
      datMan("BEST · Nhật ký lỗi đồng bộ", `<div class="hop-loi">Máy chủ trả HTTP ${T(String(r.ma))}:
        ${T((r.kq && r.kq.loi) || "không đọc được audit")}. Cần quyền <code>tenant.audit.xem</code>.</div>`);
      return;
    }
    const tatCa = Array.isArray(r.kq.audit) ? r.kq.audit : [];
    const LQ = /(tai_khoan_hang|carrier|webhook|dong_bo|\bgui\b|best|hãng)/i;
    const ds = tatCa.filter((x) => LQ.test([x.hanh_dong, x.doi_tuong, x.chi_tiet].filter(Boolean).join(" ")));
    datMan("BEST · Nhật ký lỗi đồng bộ", `
      <div class="luoi luoi-kpi">
        ${oKpi("Mục audit liên quan", T(String(ds.length)), `trong ${T(String(tatCa.length))} mục gần nhất`)}
        ${oKpi("Nguồn", "AUDIT CHUNG", "CHƯA có endpoint nhật ký đồng bộ BEST riêng")}
        ${oKpi("Lỗi đồng bộ BEST", "CHƯA ĐO ĐƯỢC", "không có trường sync/retry chuyên biệt")}
        ${oKpi("Gọi hãng", "KHÔNG", "màn này chỉ đọc CSDL nội bộ")}
      </div>
      <div class="the" style="margin-top:16px">
        <div class="the-dau"><h2>Audit liên quan hãng / webhook / gửi đơn</h2>
          <div class="phai"><span class="huy-hieu hh-vang">CHỜ BACKEND</span></div></div>
        <div class="the-than">
          <div class="hop-cho-backend" style="margin-bottom:12px">
            <b>CHƯA CÓ nhật ký lỗi đồng bộ BEST riêng.</b>
            Màn này lọc <code>GET /api/v2/audit</code> (audit chung của tenant) theo hành động liên
            quan. Không có endpoint riêng cho sync/retry BEST, nên không cột "mã lỗi đồng bộ" nào
            được bịa ra.
          </div>
          ${bang([
            { ten: "ID", so: true, k: "id" },
            { ten: "Lúc", k: "luc" },
            { ten: "Hành động", k: "hanh_dong" },
            { ten: "Đối tượng", k: "doi_tuong" },
            { ten: "Chi tiết", k: "chi_tiet" },
          ], ds, {
            id: "best-bang-audit",
            rong: "Chưa có mục audit nào liên quan hãng/webhook/gửi đơn trong 200 mục gần nhất. Đây là dữ liệu THẬT, không phải lỗi màn hình.",
          })}
          <p class="ghi-chu-nguon" style="margin-top:10px">
            Nguồn: <code>GET /api/v2/audit</code> · lọc tại trang bằng
            <code>${T(String(LQ))}</code> trên ${T(String(tatCa.length))} mục. Không hiển thị secret:
            audit backend đã che; giao diện cũng không in payload thô nào.
          </p>
        </div>
      </div>
      ${hopNguon([
        "Đường đọc: <code>GET /api/v2/audit</code> — quyền <code>tenant.audit.xem</code>.",
        "Nhật ký đồng bộ BEST: <code>GET /api/v2/best/lich-su</code> trả <code>{su_kien, audit}</code> — đúng dữ liệu backend đang có; không có endpoint riêng cho từng mã lỗi.",
      ])}
    `);
  }

  /* ========================================================================================
     17. BẢNG ĐIỀU PHỐI 12 MÀN
     ======================================================================================== */
  const MAN = {
    "best-danh-sach-hang": manDanhSachHang,
    "best-cau-hinh-tai-khoan": manCauHinhTaiKhoan,
    "best-kiem-tra-ket-noi": manKiemTraKetNoi,
    "best-tao-don": manTaoDon,
    "best-van-don": manVanDon,
    "best-chi-tiet-don": manChiTietDon,
    "best-lich-su-van-chuyen": manLichSuVanChuyen,
    "best-tra-cuu-hanh-trinh": manTraCuuHanhTrinh,
    "best-tinh-cuoc": manTinhCuoc,
    "best-in-van-don": manInVanDon,
    "best-theo-doi-webhook": manTheoDoiWebhook,
    "best-nhat-ky-loi": manNhatKyLoi,
  };
  const DANH_SACH_MAN = [
    ["best-danh-sach-hang", "🚚", "Danh sách hãng"],
    ["best-cau-hinh-tai-khoan", "🔐", "Cấu hình tài khoản BEST"],
    ["best-kiem-tra-ket-noi", "📡", "Kiểm tra kết nối"],
    ["best-tao-don", "➕", "Tạo đơn BEST"],
    ["best-van-don", "📦", "Danh sách vận đơn"],
    ["best-chi-tiet-don", "🔎", "Chi tiết đơn"],
    ["best-lich-su-van-chuyen", "🕒", "Lịch sử vận chuyển"],
    ["best-tra-cuu-hanh-trinh", "🧭", "Tra cứu hành trình"],
    ["best-tinh-cuoc", "⚖️", "Tính cước"],
    ["best-in-van-don", "🖨️", "In vận đơn"],
    ["best-theo-doi-webhook", "🔔", "Theo dõi webhook"],
    ["best-nhat-ky-loi", "📝", "Nhật ký lỗi đồng bộ"],
  ];

  const state = {
    man: "best-danh-sach-hang",
    xac_minh_tam: null,
    don_id: null,
    tra_cuu: null,
    in_nhan: null,
    loc_hang: "best",
    thong_bao: null,
    ket_qua_kiem: null,
  };

  /* ========================================================================================
     18. TRANG RIÊNG `pages/best.html` — 12 tab, cùng logic
     ======================================================================================== */
  function dungTrangDayDu(goc) {
    goc.innerHTML = `
      <div class="best-dau-trang">
        <div>
          <div class="best-nhan">AGENT B4 · LOCAL ONLY</div>
          <h1 style="margin:4px 0 4px;font-size:20px">BEST Express — 12 màn tích hợp</h1>
          <div class="ghi-chu-nguon">Không gọi API hãng BEST · không tạo đơn thật · không hiển thị credential</div>
        </div>
        <div class="best-dau-trang-nut">
          <a class="nut nut-nho" href="../admin/index.html">← Quản trị</a>
          <span class="huy-hieu hh-vang">MOCK / CHỜ BACKEND</span>
        </div>
      </div>
      <div class="best-tabs" role="tablist">
        ${DANH_SACH_MAN.map(([id, icon, ten]) =>
          `<a class="best-tab" role="tab" href="#${id}" data-best-tab="${id}" data-man="${id}"><span aria-hidden="true">${icon}</span> ${T(ten)}</a>`).join("")}
      </div>
      <h2 id="best-tieu-de" style="font-size:17px;margin:0 0 14px">BEST Express</h2>
      <div id="best-noi-dung"><div class="dang-tai"><span class="xoay"></span>Đang tải…</div></div>
    `;
    const macDinh = (location.hash || "").replace(/^#/, "");
    const id = MAN[macDinh] ? macDinh : state.man;
    veMan(id);
  }

  function veMan(id) {
    const f = MAN[id];
    if (!f) return;
    state.man = id;
    document.querySelectorAll("[data-best-tab]").forEach((n) =>
      n.classList.toggle("hien-tai", n.dataset.bestTab === id));
    Promise.resolve().then(() => f()).catch((e) => {
      datMan("Lỗi màn BEST", `<div class="hop-loi">${T(e.message)}</div>`);
    });
  }

  /* ========================================================================================
     19. GẮN SỰ KIỆN MỘT LẦN — uỷ nhiệm trên document
     ======================================================================================== */
  function ganSuKien() {
    if (typeof document === "undefined" || document.__bestDaGan) return;
    document.__bestDaGan = true;

    document.addEventListener("click", (e) => {
      const di = e.target.closest && e.target.closest("[data-best-di]");
      if (di) {
        const don = e.target.closest("[data-best-don]");
        if (don) state.don_id = Number(don.dataset.bestDon);
        e.preventDefault();
        moMan(di.dataset.bestDi);
        return;
      }
      const don = e.target.closest && e.target.closest("[data-best-don]");
      if (don) {
        state.don_id = Number(don.dataset.bestDon);
        moMan("best-chi-tiet-don");
        return;
      }
      if (e.target.closest && e.target.closest("#best-kiem-ket-noi")) {
        e.preventDefault();
        kiemKetNoiNgay();
        return;
      }
      if (e.target.closest && e.target.closest("#best-tinh-khoi-luong")) {
        e.preventDefault();
        tinhCuocTrenMan();
        return;
      }
      if (e.target.closest && e.target.closest("#best-in-nhan")) {
        e.preventDefault();
        if (choPhepIn(state.in_nhan)) window.print();
        return;
      }
    });

    document.addEventListener("submit", (e) => {
      const f = e.target;
      if (!f || !f.id) return;
      if (f.id === "best-form-tk") { e.preventDefault(); luuTaiKhoan(f); return; }
      if (f.id === "best-form-don") { e.preventDefault(); kiemDon(f); return; }
      if (f.id === "best-form-chon-don") {
        e.preventDefault();
        const id = Number((f.querySelector("#best-don-id") || {}).value);
        if (!(id > 0)) return;
        state.don_id = id;
        state.in_nhan = null;
        const man = state.man;
        if (man === "best-in-van-don") return layNhan(id);
        return veMan(man);
      }
      if (f.id === "best-form-tra-cuu") { e.preventDefault(); traCuu(f); return; }
    });

    document.addEventListener("change", (e) => {
      if (e.target && e.target.id === "best-loc-hang") {
        state.loc_hang = e.target.value === "tat_ca" ? "tat_ca" : "best";
        manVanDon();
      }
    });

    window.addEventListener("hashchange", () => {
      if (!document.getElementById("best-noi-dung")) return;
      const id = (location.hash || "").replace(/^#/, "");
      if (MAN[id] && id !== state.man) veMan(id);
    });
  }

  /* ========================================================================================
     20. CSS — chỉ lớp `best-*`, không ghi đè CSS dùng chung
     ======================================================================================== */
  const CSS = `
  .best-tt-hang{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}
  .best-nhan{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--chu-mo);font-weight:700}
  .best-tt-mo{font-size:13px;max-width:560px;color:var(--chu)}
  .best-tt-nut{margin-left:auto;display:flex;gap:8px;flex-wrap:wrap}
  .best-bang-chung{display:flex;gap:8px 18px;flex-wrap:wrap;margin-top:12px;font-size:12px;color:var(--chu-mo)}
  .best-bang-chung b{color:var(--chu)}
  .best-canh-bao{background:var(--vang-nhat);border:1px solid #F5D08A;border-radius:9px;padding:12px 16px;font-size:12.5px;color:#7A4F10;line-height:1.7}
  .best-form-luoi{display:grid;grid-template-columns:1fr 1fr;gap:0 16px}
  .best-xac-nhan{display:flex;gap:9px;align-items:flex-start;background:var(--do-nhat);border:1px solid #F5B5B5;border-radius:9px;padding:11px 13px;font-size:12.5px;line-height:1.6;margin-top:10px}
  .best-xac-nhan input{margin-top:3px;flex-shrink:0}
  .best-watermark{border:2px dashed var(--do-vip);color:var(--do-dam);background:var(--do-nhat);border-radius:8px;padding:14px;text-align:center;font-weight:800;letter-spacing:.08em;font-size:13px;margin-bottom:12px}
  .best-ma{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;word-break:break-all}
  .best-dau-trang{display:flex;gap:14px;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;margin-bottom:14px;background:var(--the);border:1px solid var(--vien);border-radius:var(--bo-goc);padding:16px 18px;box-shadow:var(--bong)}
  .best-dau-trang-nut{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  .best-tabs{display:flex;gap:5px;flex-wrap:wrap;border-bottom:1px solid var(--vien);margin-bottom:16px;padding-bottom:2px}
  .best-tab{display:inline-flex;gap:5px;align-items:center;padding:7px 11px;border-radius:8px 8px 0 0;text-decoration:none;color:var(--chu-mo);font-size:12.5px;font-weight:600;border-bottom:2.5px solid transparent}
  .best-tab:hover{background:var(--xam-nhat);color:var(--chu)}
  .best-tab.hien-tai{color:var(--do-vip);border-bottom-color:var(--do-vip);background:var(--the)}
  @media (max-width:768px){.best-form-luoi{grid-template-columns:1fr}.best-tt-nut{margin-left:0}.best-dau-trang-nut{width:100%}}
  @media print{.best-tab,.best-dau-trang,.hop-nguon,.best-xac-nhan{display:none!important}}
  `;

  function chenCss() {
    if (typeof document === "undefined" || document.getElementById("best-css")) return;
    const s = document.createElement("style");
    s.id = "best-css";
    s.textContent = CSS;
    (document.head || document.documentElement).appendChild(s);
  }

  function khoiTao() {
    chenCss();
    ganSuKien();
    const goc = document.getElementById("best-goc");
    if (goc) dungTrangDayDu(goc);
  }

  if (typeof document !== "undefined") {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", khoiTao);
    else khoiTao();
  }

  /* ========================================================================================
     21. XUẤT — bộ thử E2E và Node đọc được phần LOGIC THUẦN
     ======================================================================================== */
  const API = {
    MA_HANG, TEN_HANG, TRANG_THAI, THU_TU_TRANG_THAI,
    MAN, DANH_SACH_MAN, MAN_BEST: Object.keys(MAN),
    hoSo, coCredential, docXacMinh, daTungKetNoi, trangThaiKetNoi,
    tinhKhoiLuongQuyDoi, choPhepIn, lyDoChuaGuiDuoc,
    xoaCache,
    hienTai: () => ({
      man: state.man, don_id: state.don_id,
      loc_hang: state.loc_hang,
      co_cache: !!cache.hs,
      trang_thai: cache.hs ? trangThaiKetNoi(cache.hs) : null,
    }),
  };
  dat.VIPBEST = API;
  if (typeof module !== "undefined" && module.exports) module.exports = API;
})(typeof window !== "undefined" ? window : {});
