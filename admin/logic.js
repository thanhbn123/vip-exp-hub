/* admin/logic.js — LOGIC THUẦN của giao diện quản trị (F04).
   Tách ra khỏi admin.js để BỘ THỬ TỰ ĐỘNG chạy được bằng Node mà không cần trình duyệt.

   Luật của file này:
   - KHÔNG chạm DOM, KHÔNG fetch, KHÔNG setTimeout. Vào là dữ liệu, ra là dữ liệu.
   - KHÔNG sinh HTML. Trả về {lop, ten, ...} để admin.js tự dựng thẻ — như vậy bộ thử
     kiểm được QUYẾT ĐỊNH (nhãn nào, lớp nào) mà không phải so chuỗi HTML.
   - KHÔNG giữ secret nào. KHÔNG tự quyết định quyền — quyền do backend chốt.
   - Trạng thái LẠ thì trả nguyên văn kèm cờ `la=true`, tuyệt đối không nuốt im lặng
     (AG-03 đang thêm NEEDS_REVIEW/AMBIGUOUS cho mã J&T 110 — hiện lên nguyên văn là ĐÚNG).

   Nạp được ở hai nơi: trình duyệt (window.VIPLOGIC) và Node (module.exports). */
(function (dat) {
  "use strict";

  /* ===== 1. Trạng thái nghiệp vụ của đơn (don_hang.trang_thai) =====
     Hợp đồng ĐÓNG BĂNG ĐỢT 2 §10: nhap · da_duyet · dang_gui · da_gui · huy. */
  const TT_DON = {
    nhap:     ["hh-xam", "Nháp"],
    da_duyet: ["hh-xanh-duong", "Đã duyệt"],
    dang_gui: ["hh-vang", "Đang gửi hãng"],
    da_gui:   ["hh-xanh", "Đã gửi hãng"],
    huy:      ["hh-do", "Hủy"],
  };

  /* ===== 2. Trạng thái GIAO VẬN (don_hang.trang_thai_giao) =====
     §10: hai trục CỐ Ý tách nhau. `rank` là thứ hạng backend dùng để chặn sự kiện
     đến muộn — giao diện chỉ hiển thị, không tự suy diễn bước kế tiếp. */
  const TT_GIAO = {
    cho_lay:          ["hh-xam", "Chờ lấy hàng", 1],
    lay_hang:         ["hh-xanh-duong", "Đã lấy hàng", 2],
    dang_giao:        ["hh-xanh-duong", "Đang giao", 3],
    giao_that_bai:    ["hh-do", "Giao thất bại", 4],
    giao_thanh_cong:  ["hh-xanh", "Giao thành công", 5],
    hoan_hang:        ["hh-vang", "Hoàn hàng", 6],
  };

  /* ===== 3. Trạng thái batch / dòng import (SHARED_CONTRACTS §6) ===== */
  const TT_BATCH = {
    moi: ["hh-xam", "Mới (bộ cũ)"],
    xong: ["hh-xanh", "Xong (bộ cũ)"],
    da_duyet_mot_phan: ["hh-vang", "Duyệt một phần (bộ cũ)"],
    UPLOADED: ["hh-xam", "Đã upload"],
    PARSING: ["hh-xanh-duong", "Đang đọc file"],
    VALIDATING: ["hh-xanh-duong", "Đang kiểm dữ liệu"],
    READY: ["hh-xanh", "Sẵn sàng duyệt"],
    APPROVED: ["hh-xanh-duong", "Đã duyệt"],
    PROCESSING: ["hh-vang", "Đang tạo đơn"],
    COMPLETED: ["hh-xanh", "Hoàn tất"],
    PARTIAL_FAILED: ["hh-vang", "Hoàn tất một phần"],
    FAILED: ["hh-do", "Thất bại"],
  };
  const TT_DONG = {
    VALID: ["hh-xanh", "VALID", "hợp lệ, duyệt được"],
    INVALID: ["hh-do", "INVALID", "dữ liệu sai, phải sửa"],
    READY: ["hh-xanh-duong", "READY", "đã chuẩn hóa, chờ duyệt"],
    SUBMITTED: ["hh-vang", "SUBMITTED", "đã gửi tạo đơn"],
    SUCCESS: ["hh-xanh", "SUCCESS", "đã tạo đơn nháp"],
    FAILED: ["hh-do", "FAILED", "tạo đơn lỗi, thử lại được"],
    UNSUPPORTED: ["hh-xam", "UNSUPPORTED", "backend không đọc được dòng này"],
    NEEDS_REVIEW: ["hh-vang", "NEEDS_REVIEW", "backend yêu cầu người xem lại"],
  };

  /* ===== 4. Trạng thái sự kiện webhook (§12) =====
     NHẬP NHẰNG: AG-03 đang thêm NEEDS_REVIEW / AMBIGUOUS cho mã J&T 110. Hai trạng thái
     này CHƯA nằm trong §12 nên vẫn tính là "lạ" — nhưng được gắn `nhap_nhang=true` để
     giao diện dựng khối cảnh báo riêng thay vì chỉ hiện huy hiệu xám. */
  const TT_WH = {
    moi:          ["hh-xam", "Mới"],
    dang_xu_ly:   ["hh-xanh-duong", "Đang xử lý"],
    xong:         ["hh-xanh", "Xong"],
    cho_thu_lai:  ["hh-vang", "Chờ thử lại"],
    dlq:          ["hh-do", "DLQ — hết lượt thử"],
    khong_khop:   ["hh-vang", "Không khớp đơn"],
  };
  const WH_NHAP_NHANG = ["NEEDS_REVIEW", "AMBIGUOUS", "needs_review", "ambiguous", "nhap_nhang"];

  function tra(bang, ma, mac_dinh_lop) {
    const d = bang[ma];
    if (d) return { ma: ma, lop: d[0], ten: d[1], mo_ta: d[2] || "", la: false };
    // Trạng thái backend thêm mới mà giao diện chưa biết: hiện NGUYÊN VĂN.
    return {
      ma: ma, lop: mac_dinh_lop || "hh-xam", ten: String(ma == null ? "—" : ma),
      mo_ta: "trạng thái giao diện chưa biết tên tiếng Việt — hiện nguyên văn từ máy chủ",
      la: ma != null && ma !== "",
    };
  }

  const nhanTT    = (t) => tra(TT_DON, t);
  const nhanBatch = (t) => tra(TT_BATCH, t);
  const nhanDong  = (t) => tra(TT_DONG, t);
  function nhanGiao(t) {
    const d = tra(TT_GIAO, t);
    d.rank = TT_GIAO[t] ? TT_GIAO[t][2] : null;
    return d;
  }
  function nhanWebhook(t) {
    const d = tra(TT_WH, t);
    d.nhap_nhang = WH_NHAP_NHANG.indexOf(String(t)) >= 0;
    if (d.nhap_nhang) {
      d.lop = "hh-vang";
      d.mo_ta = "trạng thái NHẬP NHẰNG do backend đánh dấu — cần người xem lại, " +
                "giao diện không tự đoán kết quả";
    }
    return d;
  }
  function lopDongBang(t) {
    if (["INVALID", "FAILED", "UNSUPPORTED"].indexOf(t) >= 0) return "dong-loi";
    if (t === "NEEDS_REVIEW") return "dong-can-xem";
    if (["VALID", "READY", "SUCCESS"].indexOf(t) >= 0) return "dong-hop-le";
    return "";
  }

  /* ===== 5. CHẾ ĐỘ DỮ LIỆU — MOCK / LOCAL REAL / LIVE CARRIER =====
     Brief F01 đòi phân biệt rõ ba chế độ trên giao diện. Quy tắc (đo từ app/server.py
     và SHARED_CONTRACTS §4):

       LOCAL REAL DATA — dữ liệu THẬT trong CSDL local, chưa qua hãng nào:
                         đơn chưa gán carrier_account_id (nháp/đã duyệt/hủy).
       MOCK DATA       — đã đi qua adapter MOCK: có carrier_account_id, nhưng tài khoản
                         ở môi trường mock HOẶC hãng chưa mở cờ live_mo.
       LIVE CARRIER    — CHỈ khi CẢ HAI đúng: tài khoản hãng khác môi trường "mock"
                         VÀ hãng có live_mo=true.

     `CHO_PHEP_LIVE=False` là khóa an toàn ở backend và `live_mo` hiện là 0 cho mọi hãng,
     nên hàm này KHÔNG BAO GIỜ trả LIVE với dữ liệu hiện tại. Có ca thử canh đúng điều đó:
     môi trường "production" mà live_mo=false vẫn phải ra MOCK. */
  const CHE_DO = {
    LOCAL: {
      ma: "LOCAL", nhan: "LOCAL REAL DATA", lop: "cd-local",
      giai_thich: "dữ liệu thật trong CSDL local — chưa gửi hãng vận chuyển nào",
    },
    MOCK: {
      ma: "MOCK", nhan: "MOCK DATA", lop: "cd-mock",
      giai_thich: "đã đi qua adapter MOCK — mã vận đơn và phí là do bản mô phỏng sinh, " +
                  "không phải của hãng thật",
    },
    LIVE: {
      ma: "LIVE", nhan: "LIVE CARRIER DATA", lop: "cd-live",
      giai_thich: "dữ liệu từ hãng vận chuyển thật",
    },
  };

  function cheDoDon(don, tai_khoan, hang) {
    don = don || {};
    if (!don.carrier_account_id) return CHE_DO.LOCAL;
    const tk = tai_khoan || null;
    const h = hang || null;
    const moi_truong_that = tk && tk.moi_truong && tk.moi_truong !== "mock";
    const hang_mo_live = !!(h && h.live_mo);
    if (moi_truong_that && hang_mo_live) return CHE_DO.LIVE;
    return CHE_DO.MOCK;
  }

  /* Chế độ của CẢ MÀN: LIVE nếu có bất kỳ hãng nào mở live, ngược lại MOCK. */
  function cheDoHeThong(ds_hang) {
    const co_live = (ds_hang || []).some((h) => !!h.live_mo);
    return co_live ? CHE_DO.LIVE : CHE_DO.MOCK;
  }

  /* ===== 6. Bộ lọc nâng cao cho màn Đơn hàng =====
     Máy chủ hiện CHỈ nhận q · trang_thai · gioi_han (đo ở app/server.py, 15/10/2026).
     Mọi điều kiện còn lại phải lọc tại giao diện TRÊN TẬP ĐÃ TẢI — nên giao diện phải
     nói rõ phạm vi, không được để người đọc tưởng đang lọc toàn bộ CSDL. */
  const THAM_SO_MAY_CHU = ["q", "trang_thai", "gioi_han"];
  const THAM_SO_LOC_TAI_GIAO_DIEN = [
    "trang_thai_giao", "hang", "tai_khoan_id", "cod_tu", "cod_den",
    "tu_ngay", "den_ngay", "can_doi_soat", "co_van_don",
  ];

  function chiaDieuKien(dk) {
    const may_chu = {}, giao_dien = {};
    Object.keys(dk || {}).forEach((k) => {
      const v = dk[k];
      if (v === "" || v == null || v === false) return;
      if (THAM_SO_MAY_CHU.indexOf(k) >= 0) may_chu[k] = v;
      else giao_dien[k] = v;
    });
    return { may_chu: may_chu, giao_dien: giao_dien };
  }

  function _ngay(x) { return String(x || "").slice(0, 10); }

  function locDon(ds, dk, tk_theo_id) {
    dk = dk || {};
    tk_theo_id = tk_theo_id || {};
    const q = String(dk.q || "").trim().toLowerCase();
    return (ds || []).filter((d) => {
      if (q) {
        const kho = [d.ma_don, d.ma_van_don, d.nguoi_nhan_ten, d.nguoi_nhan_sdt]
          .map((x) => String(x == null ? "" : x).toLowerCase()).join(" ");
        if (kho.indexOf(q) < 0) return false;
      }
      if (dk.trang_thai && d.trang_thai !== dk.trang_thai) return false;
      if (dk.trang_thai_giao && (d.trang_thai_giao || "") !== dk.trang_thai_giao) return false;
      if (dk.tai_khoan_id && String(d.carrier_account_id || "") !== String(dk.tai_khoan_id)) return false;
      if (dk.hang) {
        const tk = tk_theo_id[d.carrier_account_id];
        if (!tk || tk.hang !== dk.hang) return false;
      }
      if (dk.cod_tu !== undefined && dk.cod_tu !== "" && +(d.cod || 0) < +dk.cod_tu) return false;
      if (dk.cod_den !== undefined && dk.cod_den !== "" && +(d.cod || 0) > +dk.cod_den) return false;
      if (dk.tu_ngay && _ngay(d.tao_luc) < dk.tu_ngay) return false;
      if (dk.den_ngay && _ngay(d.tao_luc) > dk.den_ngay) return false;
      if (dk.can_doi_soat && !d.can_doi_soat_ket_qua) return false;
      if (dk.co_van_don === "co" && !d.ma_van_don) return false;
      if (dk.co_van_don === "khong" && d.ma_van_don) return false;
      return true;
    });
  }

  /* ===== 7. Dòng thời gian giao vận (tracking timeline) =====
     Nguồn DUY NHẤT: `don_lich_su` do `GET /api/v2/don/<id>` trả về (§11). Mỗi thay đổi
     trạng thái bắt buộc có một dòng ở đó, nên timeline là dữ liệu THẬT, không suy diễn.

     Hàm này KHÔNG bịa mốc thời gian: mốc nào không có trong lich_su thì không có nút.
     Nút cuối "trạng thái hiện tại" chỉ được thêm khi lich_su KHÔNG hề nhắc tới trạng thái
     giao hiện tại — và khi đó gắn cờ `suy_ra=true` + `luc=null` để giao diện ghi rõ là
     suy ra từ trường `trang_thai_giao`, không phải một sự kiện có giờ. */
  const NGUON_NHAN = {
    polling: ["Polling hệ thống", "hệ thống tự hỏi hãng (fallback khi hãng không đẩy webhook)"],
    he_thong: ["Hệ thống", "tiến trình nội bộ"],
  };
  function dienGiaiNguon(nguon) {
    const s = String(nguon || "");
    if (NGUON_NHAN[s]) return { ten: NGUON_NHAN[s][0], mo_ta: NGUON_NHAN[s][1], loai: s };
    if (s.indexOf("user:") === 0) {
      return { ten: "Người dùng #" + s.slice(5), mo_ta: "người trong doanh nghiệp bấm trên giao diện", loai: "user" };
    }
    if (s.indexOf("webhook:") === 0) {
      return { ten: "Webhook hãng (tài khoản #" + s.slice(8) + ")", mo_ta: "hãng đẩy sự kiện về", loai: "webhook" };
    }
    return { ten: s || "—", mo_ta: "nguồn giao diện chưa biết — hiện nguyên văn", loai: "la" };
  }

  function dungTimeline(don, lich_su) {
    don = don || {};
    const nut = (lich_su || []).slice()
      .sort((a, b) => (a.id || 0) - (b.id || 0))
      .map((l) => {
        const ng = dienGiaiNguon(l.nguon);
        return {
          luc: l.luc || null,
          nguon: l.nguon,
          nguon_ten: ng.ten,
          nguon_loai: ng.loai,
          noi_dung: l.noi_dung || "",
          suy_ra: false,
        };
      });
    const tt_giao = don.trang_thai_giao || null;
    if (tt_giao) {
      const da_co = nut.some((n) => String(n.noi_dung).indexOf(tt_giao) >= 0);
      if (!da_co) {
        nut.push({
          luc: null, nguon: "truong_trang_thai_giao", nguon_ten: "suy ra từ trường trang_thai_giao",
          nguon_loai: "suy_ra",
          noi_dung: "Trạng thái giao hiện tại: " + tt_giao,
          suy_ra: true,
        });
      }
    }
    return {
      nut: nut,
      tt_giao: tt_giao,
      nhan_giao: tt_giao ? nhanGiao(tt_giao) : null,
      can_doi_soat: !!don.can_doi_soat_ket_qua,
      /* Thiếu gì so với một timeline "đủ": mốc quét của hãng (scan events) chỉ về được
         qua webhook; đơn chưa gửi hãng thì không thể có. Nói ra để không ai tưởng
         timeline này là hành trình đầy đủ bên hãng. */
      ghi_chu_pham_vi: don.carrier_account_id
        ? "Mốc hãng chỉ có khi hãng đẩy webhook về hoặc polling chạy — không phải toàn bộ hành trình bên hãng."
        : "Đơn chưa gửi hãng nên timeline chỉ có các bước nội bộ.",
    };
  }

  /* ===== 8. Kiểm dữ liệu form tạo/sửa đơn (kiểm ở giao diện cho nhanh — backend vẫn chốt) ===== */
  const TRUONG_BAT_BUOC_DON = [
    ["nguoi_gui_ten", "Tên người gửi"],
    ["nguoi_gui_sdt", "SĐT người gửi"],
    ["nguoi_gui_dia_chi", "Địa chỉ gửi"],
    ["nguoi_nhan_ten", "Tên người nhận"],
    ["nguoi_nhan_sdt", "SĐT người nhận"],
    ["nguoi_nhan_dia_chi", "Địa chỉ nhận"],
    ["hang_hoa", "Hàng hóa"],
    ["khoi_luong_gram", "Cân nặng (gram)"],
  ];
  function kiemTraDon(d) {
    d = d || {};
    const loi = [];
    TRUONG_BAT_BUOC_DON.forEach(([k, ten]) => {
      const v = d[k];
      if (v == null || String(v).trim() === "") loi.push({ truong: k, thong_diep: ten + " không được trống" });
    });
    if (d.khoi_luong_gram != null && String(d.khoi_luong_gram).trim() !== "") {
      const kl = Number(d.khoi_luong_gram);
      if (!isFinite(kl) || kl <= 0) loi.push({ truong: "khoi_luong_gram", thong_diep: "Cân nặng phải là số gram lớn hơn 0" });
    }
    if (d.cod != null && String(d.cod).trim() !== "") {
      const c = Number(d.cod);
      if (!isFinite(c) || c < 0) loi.push({ truong: "cod", thong_diep: "COD phải là số không âm" });
    }
    ["nguoi_gui_sdt", "nguoi_nhan_sdt"].forEach((k) => {
      const v = String(d[k] == null ? "" : d[k]).trim();
      if (v && !/^[0-9+\s.()-]{8,20}$/.test(v)) {
        loi.push({ truong: k, thong_diep: "Số điện thoại chỉ gồm chữ số và dấu phân cách, 8–20 ký tự" });
      }
    });
    return loi;
  }

  /* ===== 9. Chọn tài khoản hãng khi gửi đơn =====
     Phải nói rõ hãng NÀO và tài khoản NÀO; tài khoản bị khóa thì không được mời chọn,
     và hãng không có capability `createOrder` thì phải cảnh báo trước khi bấm. */
  function chonTaiKhoanGui(tai_khoan, ds_hang) {
    const hang_theo_ma = {};
    (ds_hang || []).forEach((h) => { hang_theo_ma[h.ma] = h; });
    const dung_duoc = [], loai_ra = [];
    (tai_khoan || []).forEach((tk) => {
      const h = hang_theo_ma[tk.hang] || null;
      const cap = (h && h.capabilities) || {};
      const muc = {
        id: tk.id, ten: tk.ten, hang: tk.hang,
        hang_ten: h ? h.ten : tk.hang,
        moi_truong: tk.moi_truong,
        che_do: cheDoDon({ carrier_account_id: tk.id }, tk, h),
        tao_don_duoc: cap.createOrder !== false,
        in_nhan_duoc: !!cap.getShippingLabel,
        theo_doi_duoc: !!cap.trackOrder,
      };
      if (!tk.kich_hoat) {
        muc.ly_do_loai = "tài khoản đang bị khóa hoặc đã thu hồi credentials";
        loai_ra.push(muc);
      } else if (!muc.tao_don_duoc) {
        muc.ly_do_loai = "hãng này không hỗ trợ createOrder (theo capabilities backend trả về)";
        loai_ra.push(muc);
      } else {
        dung_duoc.push(muc);
      }
    });
    return { dung_duoc: dung_duoc, loai_ra: loai_ra };
  }

  /* ===== 10. Metadata phiếu in =====
     KHÔNG có API nhãn vận đơn của hãng (đo 15/10/2026: không có route nào khớp
     /api/v2/don/<id>/nhan). Nên phiếu in được dựng từ dữ liệu đơn trong CSDL local và
     PHẢI tự khai là phiếu nội bộ. `la_nhan_hang=false` là bất biến cho tới khi có API. */
  function metaNhan(don, tk, hang) {
    don = don || {};
    const che_do = cheDoDon(don, tk, hang);
    const thieu = [];
    if (!don.ma_van_don) thieu.push("mã vận đơn (đơn chưa gửi hãng hoặc hãng chưa trả về)");
    if (don.phi_van_chuyen == null) thieu.push("phí vận chuyển");
    if (!tk) thieu.push("tài khoản hãng (chưa gán)");
    const cap = (hang && hang.capabilities) || {};
    return {
      la_nhan_hang: false,
      nguon: "CSDL local qua GET /api/v2/don/<id>",
      che_do: che_do,
      hang_ho_tro_in_nhan: !!cap.getShippingLabel,
      thieu: thieu,
      o: {
        ma_don: don.ma_don || "", ma_van_don: don.ma_van_don || "",
        nguoi_gui: [don.nguoi_gui_ten, don.nguoi_gui_sdt, don.nguoi_gui_dia_chi],
        nguoi_nhan: [don.nguoi_nhan_ten, don.nguoi_nhan_sdt, don.nguoi_nhan_dia_chi],
        hang_hoa: don.hang_hoa || "", khoi_luong_gram: don.khoi_luong_gram || 0,
        cod: don.cod || 0, phi_van_chuyen: don.phi_van_chuyen,
        ghi_chu: don.ghi_chu || "", tao_luc: don.tao_luc || "",
      },
    };
  }

  /* ===== 11. Webhook monitor: gom nhóm, đếm thử lại, DLQ, trạng thái nhập nhằng ===== */
  function nhomWebhook(ds) {
    ds = ds || [];
    const theo_tt = {};
    let tong_thu_lai = 0;
    const dlq = [], cho_thu_lai = [], nhap_nhang = [], la = [];
    ds.forEach((s) => {
      const n = nhanWebhook(s.trang_thai);
      theo_tt[s.trang_thai] = (theo_tt[s.trang_thai] || 0) + 1;
      tong_thu_lai += +(s.so_lan_thu || 0);
      if (s.trang_thai === "dlq") dlq.push(s);
      if (s.trang_thai === "cho_thu_lai") cho_thu_lai.push(s);
      if (n.nhap_nhang) nhap_nhang.push(s);
      else if (n.la) la.push(s);
    });
    const co_thu_lai = ds.filter((s) => +(s.so_lan_thu || 0) > 0);
    return {
      tong: ds.length, theo_trang_thai: theo_tt,
      dlq: dlq, cho_thu_lai: cho_thu_lai,
      nhap_nhang: nhap_nhang, trang_thai_la: la,
      tong_lan_thu_lai: tong_thu_lai,
      so_su_kien_da_thu_lai: co_thu_lai.length,
      thu_lai_nhieu_nhat: co_thu_lai.reduce(
        (a, s) => (+(s.so_lan_thu || 0) > +(a ? a.so_lan_thu : -1) ? s : a), null),
      /* Replay do BACKEND kiểm quyền (tenant.webhook.replay). Giao diện chỉ ẩn nút cho gọn —
         danh sách này nói rõ trạng thái nào mời replay, để bộ thử canh được. */
      replay_duoc: ds.filter((s) => ["dlq", "khong_khop"].indexOf(s.trang_thai) >= 0).map((s) => s.id),
    };
  }

  /* ===== 12. Danh mục API CHƯA CÓ =====
     Một chỗ duy nhất khai những endpoint giao diện MONG ĐỢI mà backend chưa có. Giao diện
     đọc bảng này để hiện nhãn "CHỜ BACKEND"; bộ thử HTTP đọc đúng bảng này rồi bắn thật
     vào máy chủ — endpoint nào đã có mà vẫn còn trong bảng thì bộ thử HỎNG, buộc phải
     cập nhật. Như vậy nhãn "CHỜ BACKEND" không thể nói dối lâu. */
  const API_CHO_BACKEND = [
    {
      ten: "Từ chối đơn có lý do",
      duong: "/api/v2/don/<id>/tu-choi", method: "POST",
      man: "Đơn hàng → Chi tiết đơn → Từ chối",
      mong_doi_vao: { ly_do_ma: "sai_dia_chi|trung_don|khach_huy|qua_kho|khac", ghi_chu: "string" },
      mong_doi_ra: { don: "bản ghi đơn sau khi từ chối", ly_do_ma: "string", ly_do_ghi_chu: "string" },
      ghi_chu: "AG-02 đang mở rộng Order Service. Hiện giao diện chỉ có /huy (không nhận lý do).",
    },
    {
      ten: "Nhãn vận đơn của hãng",
      duong: "/api/v2/don/<id>/nhan", method: "GET",
      man: "Đơn hàng → Chi tiết đơn → In phiếu",
      mong_doi_vao: {},
      mong_doi_ra: { dinh_dang: "pdf|zpl|png", du_lieu_base64: "string", hang: "string", kho_giay: "A6|100x150" },
      ghi_chu: "CarrierAdapter có getShippingLabel nhưng chưa phơi ra HTTP. Phiếu in hiện là " +
               "PHIẾU NỘI BỘ dựng từ CSDL local, không phải nhãn hãng.",
    },
    {
      ten: "Tìm đơn nâng cao ở máy chủ",
      duong: "/api/v2/don", method: "GET",
      mong_doi_vao: {
        tu_ngay: "YYYY-MM-DD", den_ngay: "YYYY-MM-DD", trang_thai_giao: "string",
        hang: "mã hãng", carrier_account_id: "int", cod_tu: "int", cod_den: "int",
        can_doi_soat: "0|1", sap_xep: "tao_luc|cod|ma_don", trang: "int",
      },
      mong_doi_ra: { don: "[]", tong: "int (tổng khớp điều kiện, để phân trang đúng)" },
      man: "Đơn hàng → Bộ lọc nâng cao",
      ghi_chu: "Máy chủ hiện chỉ nhận q · trang_thai · gioi_han. Các điều kiện còn lại đang " +
               "lọc TẠI GIAO DIỆN trên tập đã tải — giao diện ghi rõ phạm vi này.",
      mot_phan: true,
    },
    {
      ten: "Chi tiết một sự kiện webhook",
      duong: "/api/v2/webhook/su-kien/<id>", method: "GET",
      man: "Webhook → Chi tiết sự kiện",
      mong_doi_vao: {},
      mong_doi_ra: {
        payload_tho: "string (đã che secret)", headers_json: "string",
        don_id: "int|null", ma_van_don: "string|null",
        anh_xa: { ma_goc_hang: "string", trang_thai_chuan: "string", ap_dung: "bool", ly_do: "string" },
        lan_thu: "[{luc, loi}]",
      },
      ghi_chu: "Danh sách hiện chỉ trả id · event_id · hang · nhan_luc · trang_thai · so_lan_thu · " +
               "loi_cuoi. Không có payload, không có đơn liên quan, không có lịch sử từng lần thử.",
    },
    {
      ten: "Ánh xạ cột khi import",
      duong: "/api/v2/import/<id>/anh-xa-cot", method: "GET + PUT",
      man: "Import file → Ánh xạ cột",
      mong_doi_vao: { anh_xa: "{ chỉ số cột: tên trường nội bộ }" },
      mong_doi_ra: { cot_file: "[]", anh_xa: "{}", truong_noi_bo: "[]", bat_buoc: "[]", mau_dong: "[]" },
      ghi_chu: "Màn ánh xạ cột đã viết sẵn, tự bật khi backend có endpoint này.",
    },
    {
      ten: "Tổng hợp số dòng import theo trạng thái",
      duong: "/api/v2/import/tong-hop", method: "GET",
      man: "Tổng quan → Thống kê import",
      mong_doi_vao: {},
      mong_doi_ra: { theo_trang_thai_dong: "{ VALID: n, INVALID: n, NEEDS_REVIEW: n, ... }" },
      ghi_chu: "GET /api/v2/import chỉ trả danh sách batch, không đếm dòng.",
    },
    {
      ten: "Kiểm kết nối hãng (ping)",
      duong: "/api/v2/tai-khoan-hang/<id>/kiem-ket-noi", method: "POST",
      man: "Hãng vận chuyển → Trạng thái kết nối",
      mong_doi_vao: {},
      mong_doi_ra: { ok: "bool", tre_ms: "int", loi: "string|null" },
      ghi_chu: "Trạng thái kết nối hiện SUY RA từ việc có tài khoản hãng hay không, " +
               "không phải phép thử gọi hãng.",
    },
  ];

  /* ===== 13. Danh mục endpoint giao diện ĐANG dùng =====
     Bộ thử HTTP bắn thật từng đường này để chắc giao diện không gọi vào hư không. */
  const API_DANG_DUNG = [
    ["GET", "/api/v2/auth/toi"],
    ["GET", "/api/v2/don"],
    ["GET", "/api/v2/don/xuat-csv"],
    ["GET", "/api/v2/khach-hang"],
    ["GET", "/api/v2/hang"],
    ["GET", "/api/v2/tai-khoan-hang"],
    ["GET", "/api/v2/import"],
    ["GET", "/api/v2/webhook/su-kien"],
    ["GET", "/api/v2/billing"],
    ["GET", "/api/v2/audit"],
    ["GET", "/api/v2/memberships"],
  ];

  /* ===== 14. Lý do từ chối đơn (dùng chung cho modal và cho bộ thử) ===== */
  const LY_DO_TU_CHOI = [
    ["sai_dia_chi", "Địa chỉ nhận sai hoặc không đủ"],
    ["trung_don", "Đơn trùng với đơn đã tạo"],
    ["khach_huy", "Khách hủy trước khi gửi"],
    ["qua_kho", "Hàng quá khổ / quá cân so với hãng nhận"],
    ["sai_cod", "COD sai so với thỏa thuận"],
    ["khac", "Lý do khác (ghi rõ ở ghi chú)"],
  ];
  function kiemTraTuChoi(d) {
    d = d || {};
    const loi = [];
    const ma = String(d.ly_do_ma || "");
    if (!ma) loi.push({ truong: "ly_do_ma", thong_diep: "Phải chọn lý do từ chối" });
    else if (!LY_DO_TU_CHOI.some(([m]) => m === ma)) {
      loi.push({ truong: "ly_do_ma", thong_diep: "Lý do không nằm trong danh mục" });
    }
    if (ma === "khac" && !String(d.ghi_chu || "").trim()) {
      loi.push({ truong: "ghi_chu", thong_diep: 'Chọn "Lý do khác" thì phải ghi rõ ở ghi chú' });
    }
    return loi;
  }

  dat({
    TT_DON: TT_DON, TT_GIAO: TT_GIAO, TT_BATCH: TT_BATCH, TT_DONG: TT_DONG, TT_WH: TT_WH,
    nhanTT: nhanTT, nhanBatch: nhanBatch, nhanDong: nhanDong, nhanGiao: nhanGiao,
    nhanWebhook: nhanWebhook, lopDongBang: lopDongBang,
    CHE_DO: CHE_DO, cheDoDon: cheDoDon, cheDoHeThong: cheDoHeThong,
    THAM_SO_MAY_CHU: THAM_SO_MAY_CHU, THAM_SO_LOC_TAI_GIAO_DIEN: THAM_SO_LOC_TAI_GIAO_DIEN,
    chiaDieuKien: chiaDieuKien, locDon: locDon,
    dienGiaiNguon: dienGiaiNguon, dungTimeline: dungTimeline,
    TRUONG_BAT_BUOC_DON: TRUONG_BAT_BUOC_DON, kiemTraDon: kiemTraDon,
    chonTaiKhoanGui: chonTaiKhoanGui, metaNhan: metaNhan, nhomWebhook: nhomWebhook,
    API_CHO_BACKEND: API_CHO_BACKEND, API_DANG_DUNG: API_DANG_DUNG,
    LY_DO_TU_CHOI: LY_DO_TU_CHOI, kiemTraTuChoi: kiemTraTuChoi,
  });
})(function (api) {
  if (typeof module !== "undefined" && module.exports) module.exports = api;       // Node — bộ thử
  if (typeof window !== "undefined") window.VIPLOGIC = api;                         // trình duyệt
});
