/* admin/billing.js — LOGIC THUẦN của màn gói dịch vụ / mức dùng / dự thảo hoá đơn (G08.5).
   Theo đúng khuôn `admin/logic.js`: vào là dữ liệu, ra là dữ liệu.

   Luật của file này:
   - KHÔNG chạm DOM, KHÔNG fetch, KHÔNG setTimeout. `admin.js` tự dựng thẻ từ thứ trả về.
   - KHÔNG sinh HTML. Trả `{lop, ten, ...}` để bộ thử kiểm được QUYẾT ĐỊNH, không so chuỗi HTML.
   - **KHÔNG TỰ QUYẾT HẠN MỨC.** Mọi trần, mọi "còn chỗ hay không", mọi số tiền đều do backend
     tính và trả về. Hàm `kiemTruocKhiGoi` ở đây CHỈ để hiện cảnh báo sớm cho người bấm; nó
     không phải chốt chặn, và `admin.js` không được dùng nó để bỏ qua lỗi backend trả về.
     Backend chặn bằng một câu `UPDATE` có trần trong `WHERE` (xem `app/usage.py`).
   - TIỀN là số nguyên ĐỒNG (SHARED_CONTRACTS §16). Gặp số thập phân thì BÁO LẠ, không tự
     làm tròn — làm tròn im lặng là cách một đồng lệch đi mà không ai thấy.
   - Tỷ lệ nhận từ backend theo ĐIỂM CƠ BẢN (1 = 0,01 %), không nhận số thực.

   Nạp được ở hai nơi: trình duyệt (window.VIPBILLING) và Node (module.exports). */
(function (dat) {
  "use strict";

  /* ===== 1. Màn hình của G08.5 ===== */
  const MAN = [
    ["goi", "Danh sách gói", "tenant.billing.xem"],
    ["dang-ky", "Chi tiết đăng ký", "tenant.billing.xem"],
    ["muc-dung", "Bảng mức dùng", "tenant.billing.xem"],
    ["canh-bao", "Cảnh báo sắp hết hạn mức", "tenant.billing.xem"],
    ["lich-su", "Lịch sử tính phí", "tenant.billing.xem"],
    ["du-thao", "Dự thảo hoá đơn (bản nháp nội bộ)", "tenant.billing.xem"],
    ["quan-tri-goi", "Quản trị gói (nền tảng)", "platform.goi.doi"],
  ];

  /* ===== 2. Trạng thái đăng ký (app/goi_dich_vu.py) ===== */
  const TT_DANG_KY = {
    dang_hoat_dong: ["hh-xanh", "Đang hoạt động"],
    tam_ngung: ["hh-vang", "Tạm ngưng"],
    da_huy: ["hh-do", "Đã huỷ"],
    chua_dang_ky: ["hh-xam", "Chưa có đăng ký (đang dùng gói của tenant)"],
  };

  /* ===== 3. Loại mục trong lịch sử đổi gói ===== */
  const LOAI_LICH_SU = {
    kich_hoat: ["hh-xanh-duong", "Kích hoạt"],
    nang_goi: ["hh-xanh", "Nâng gói"],
    ha_goi: ["hh-vang", "Hạ gói"],
    doi_phien_ban: ["hh-xanh-duong", "Đổi phiên bản gói"],
    tam_ngung: ["hh-vang", "Tạm ngưng"],
    mo_lai: ["hh-xanh", "Mở lại"],
    huy: ["hh-do", "Huỷ"],
  };

  function tra(bang, ma) {
    const d = bang[ma];
    if (d) return { ma: ma, lop: d[0], ten: d[1], la: false };
    // Trạng thái LẠ hiện NGUYÊN VĂN kèm cờ `la` — tuyệt đối không nuốt im lặng.
    return { ma: ma, lop: "hh-xam", ten: String(ma == null ? "(trống)" : ma), la: true };
  }
  function nhanDangKy(ma) { return tra(TT_DANG_KY, ma); }
  function nhanLichSu(ma) { return tra(LOAI_LICH_SU, ma); }

  /* ===== 4. TIỀN — số nguyên đồng, không thập phân (§16) ===== */
  function dinhDangDong(v) {
    if (v === null || v === undefined) return { ok: false, chu: "—", la: true, ly_do: "thiếu số" };
    if (typeof v !== "number" || !Number.isFinite(v)) {
      return { ok: false, chu: String(v), la: true, ly_do: "không phải số" };
    }
    if (!Number.isInteger(v)) {
      // KHÔNG tự làm tròn: số tiền thập phân là dấu hiệu backend chọn sai đơn vị.
      return { ok: false, chu: String(v), la: true, ly_do: "tiền phải là số nguyên đồng (§16)" };
    }
    const am = v < 0;
    const chu = Math.abs(v).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
    return { ok: true, la: false, chu: (am ? "-" : "") + chu + " đ", so: v };
  }

  /* ===== 5. Tỷ lệ theo ĐIỂM CƠ BẢN (1 = 0,01 %) ===== */
  function chuTyLe(diemCoBan) {
    if (typeof diemCoBan !== "number" || !Number.isFinite(diemCoBan)) return "—";
    const nguyen = Math.trunc(diemCoBan / 100);
    const le = Math.abs(diemCoBan % 100);
    return le === 0 ? nguyen + " %" : nguyen + "," + String(le).padStart(2, "0") + " %";
  }

  /* ===== 6. Mức cảnh báo hạn mức. Ngưỡng do backend trả về; đây chỉ là cách VẼ ===== */
  const NGUONG_SAP_HET = 8000;      // 80 % — khớp usage.NGUONG_CANH_BAO_DIEM_CO_BAN
  function mucCanhBao(dong) {
    dong = dong || {};
    const tran = dong.tran, ty = dong.ty_le_diem_co_ban;
    if (tran === null || tran === undefined) {
      // `tran=null` nghĩa là TRẦN DO MODULE KHÁC QUYẾT, KHÔNG phải "không giới hạn".
      return { muc: "khong_ro", lop: "hh-xam", ten: "Trần do nơi khác quyết", thanh: null };
    }
    if (tran === 0) return { muc: "khong_tran", lop: "hh-xam", ten: "Chưa áp trần", thanh: null };
    if (dong.con_lai === 0) return { muc: "het", lop: "hh-do", ten: "Đã hết hạn mức", thanh: 100 };
    if (typeof ty === "number" && ty >= NGUONG_SAP_HET) {
      return { muc: "sap_het", lop: "hh-vang", ten: "Sắp hết hạn mức", thanh: ty / 100 };
    }
    return { muc: "con_cho", lop: "hh-xanh", ten: "Còn hạn mức",
             thanh: typeof ty === "number" ? ty / 100 : null };
  }

  /* ===== 7. Bảng mức dùng — dựng từ ĐÚNG payload `usage.trang_thai_han_muc` ===== */
  function dungBangMucDung(tt) {
    tt = tt || {};
    const dong = tt.dong || {};
    const hang = Object.keys(dong).map(function (loai) {
      const d = dong[loai] || {};
      return {
        loai: loai, ten: d.ten || loai,
        tran: d.tran, da_dung: d.da_dung, con_lai: d.con_lai,
        ty_le: chuTyLe(d.ty_le_diem_co_ban),
        canh_bao: mucCanhBao(d),
        // Hai cột này hiện LÊN GIAO DIỆN, không chỉ nằm trong mã: người xem phải biết con số
        // đến từ bảng nào, nếu không thì hai số lệch nhau mà không ai biết tin bên nào.
        nguon_do: d.nguon_do || "?", nguon_tran: d.nguon_tran || "?",
      };
    });
    hang.sort(function (a, b) { return a.loai < b.loai ? -1 : 1; });
    return {
      ky: tt.ky || null, goi: tt.goi_ten || null, phien_ban: tt.phien_ban || null,
      trang_thai: nhanDangKy(tt.trang_thai_dang_ky),
      canh_bao_chua_ghim: tt.tu_dang_ky === false
        ? "Tenant chưa có đăng ký — hạn mức đang lấy từ gói hiện tại, CHƯA được ghim phiên bản"
        : null,
      hang: hang,
      sap_het: hang.filter(function (h) {
        return h.canh_bao.muc === "sap_het" || h.canh_bao.muc === "het";
      }),
    };
  }

  /* ===== 8. Dự thảo hoá đơn — BẮT BUỘC mang nhãn "không phải hoá đơn" ===== */
  const NHAN_BAT_BUOC = "KHÔNG PHẢI HOÁ ĐƠN";
  function tomTatDuThao(dt) {
    if (!dt) return { co: false, nhan: null, canh_bao: "Kỳ này chưa có dự thảo" };
    const thieuNhan = !(dt.nhan_phap_ly && String(dt.nhan_phap_ly).indexOf(NHAN_BAT_BUOC) >= 0);
    return {
      co: true, ky: dt.ky,
      tien_goi: dinhDangDong(dt.tien_goi_dong),
      tien_vuot: dinhDangDong(dt.tien_vuot_dong),
      tong: dinhDangDong(dt.tong_dong),
      phan_du_bo: dinhDangDong(dt.phan_du_bo_dong),
      la_du_thao: dt.la_du_thao === 1 || dt.la_du_thao === true,
      nhan: dt.nhan_phap_ly || null,
      // Thiếu nhãn thì KHÔNG hiện số tiền như một hoá đơn: báo lỗi ra ngoài.
      canh_bao: thieuNhan
        ? "Dự thảo thiếu nhãn pháp lý — không được hiển thị như hoá đơn, báo backend"
        : null,
      khoa_hanh_dong: ["Không có nút thanh toán: G08 không nối cổng thanh toán, không trừ tiền"],
    };
  }

  /* ===== 9. Đổi gói — xem TRƯỚC, backend vẫn là người quyết ===== */
  function kiemTruocKhiGoi(ss) {
    ss = ss || {};
    const vuot = ss.vuot || {};
    const ten = Object.keys(vuot);
    return {
      cho_bam: ten.length === 0,
      vuot: ten.map(function (k) {
        const v = vuot[k] || {};
        return { loai: k, ten: v.ten || k, dang_dung: v.dang_dung, tran_moi: v.tran_moi };
      }),
      thong_diep: ten.length === 0
        ? "Đổi được. Backend kiểm lại lần nữa khi bấm."
        : "Đang dùng vượt hạn mức gói mới. Dữ liệu sẽ KHÔNG bị xoá; cần tick "
          + '"cho phép vượt" hoặc giảm mức dùng trước.',
      ghi_chu: "chỉ để hiện cảnh báo sớm; chốt chặn ở backend (app/usage.py)",
    };
  }

  /* ===== 10. Route. Đường nào BACKEND CHƯA CẮM thì ghi CHỜ BACKEND, không tuyên bố làm được. =====
     AG-00 là người cắm route (SHARED_CONTRACTS §22). Bảng này khớp bảng route trong
     `docs/G08_FINAL_REPORT.md`.

     ✅ G20 · AG-02 — SỬA BẢNG 17/10/2026, ĐO BẰNG HTTP THẬT (không đọc mã rồi đoán).
     Bảng này TỪNG SAI ĐƯỜNG ở năm dòng, và AG-05 (G19) đã đo ra nhưng cố ý KHÔNG sửa, vì
     `billing.js` không nằm trong phạm vi được cấp của làn ấy — và vì sửa một bảng KHÔNG AI
     CANH chính là cách tạo ra một chỗ hỏng im lặng mới. G20 sửa bảng VÀ thêm ca canh.

     ĐO LẠI trên nền cô lập, cổng bind 127.0.0.1, KHÔNG gọi ra hãng (`/tmp/ag02/do_duong.py`):

       NĂM DÒNG SAI ĐƯỜNG (cả năm đều 404)          →  ĐƯỜNG THẬT (đều 200)
       GET /api/v2/billing/goi      → HTTP 404         GET /api/v2/goi
       GET /api/v2/billing/dang-ky  → HTTP 404         GET /api/v2/dang-ky
       GET /api/v2/billing/muc-dung → HTTP 404         GET /api/v2/usage
       GET /api/v2/billing/canh-bao → HTTP 404         GET /api/v2/usage/bao-cao
       GET /api/v2/billing/lich-su  → HTTP 404         GET /api/v2/usage/su-kien

       DÒNG THỨ SÁU cũng nói dối, theo chiều NGƯỢC LẠI — ca canh mới bắt được, AG-05 chưa nêu:
       GET /api/v2/billing/du-thao  → HTTP **200**     (ĐÃ cắm từ trước, mà vẫn khai CHỜ BACKEND)
       Màn `du-thao` của `admin.js` đã đọc chính đường ấy và ghi trên màn "Đường ĐỌC thì có".
       Một đường đã chạy nằm trong bảng CHỜ là nhãn nói dối — chuyển sang ĐANG DÙNG.

     SÁU đường còn lại GIỮ NGUYÊN trong bảng chờ, và đo lại vẫn đúng là CHƯA CẮM (đo bằng tài
     khoản NỀN TẢNG `platform-owner`: `/api/v2/platform/**` có cổng riêng ở `server.py:566`
     trả 403 cho người không phải nhân sự nền tảng TRƯỚC khi tới bảng route — đo bằng
     `shopa-owner` thì 403 ấy KHÔNG nói gì về việc đường có được cắm hay không, và dễ bị đọc
     nhầm thành "đã cắm"). Kết quả: `POST /api/v2/billing/du-thao` 404 · `POST /api/v2/billing/usage`
     404 · `POST /api/v2/platform/goi/phien-ban` 404 · `POST /api/v2/platform/tenants/{id}/doi-goi`
     404 · `POST /api/v2/platform/tenants/{id}/tam-ngung` 404.

     CA CANH: `thu_giao_dien/08_bang_duong_billing.spec.js` — đọc thẳng `app/server.py`, đối
     chiếu HAI CHIỀU (chờ-mà-đã-cắm, và dùng-mà-không-có), kèm ca TỰ KIỂM chứng minh bộ đo
     ấy ĐỎ ĐƯỢC. Đây là bản tương đương `app/thu/thu_tai_chinh.py::test_j4` đang canh
     `finance.js`; `finance.js` có ca ấy, `billing.js` trước G20 KHÔNG có. */
  const API_DANG_DUNG = [
    ["GET", "/api/v2/billing", "gói + usage hiện tại (đã có từ đợt trước)"],
    ["GET", "/api/v2/goi", "danh sách gói + phiên bản mới nhất — màn `goi` đọc đường này"],
    ["GET", "/api/v2/dang-ky", "đăng ký của tenant đang đăng nhập — màn `dang-ky`"],
    ["GET", "/api/v2/usage", "trang_thai_han_muc(tenant, ky) — màn `muc-dung` và `canh-bao`"],
    ["GET", "/api/v2/usage/bao-cao", "báo cáo mức dùng đầy đủ của một kỳ"],
    ["GET", "/api/v2/usage/su-kien", "sự kiện dùng trong kỳ — màn `lich-su`"],
    ["GET", "/api/v2/billing/du-thao", "dự thảo hoá đơn của một kỳ — màn `du-thao`"],
  ];
  const API_CHO_BACKEND = [
    ["POST", "/api/v2/billing/du-thao", "lập dự thảo (idempotent theo kỳ) — cần quyền tenant.billing.lap_du_thao (V-13909)", "CHỜ BACKEND"],
    ["POST", "/api/v2/billing/usage", "ghi sự kiện dùng (cần idem_key) — chưa có đường HTTP nào ghi sự kiện", "CHỜ BACKEND"],
    ["POST", "/api/v2/platform/goi/phien-ban", "phát hành phiên bản gói", "CHỜ BACKEND"],
    ["POST", "/api/v2/platform/tenants/{id}/doi-goi", "nâng/hạ gói", "CHỜ BACKEND"],
    ["POST", "/api/v2/platform/tenants/{id}/tam-ngung", "tạm ngưng / mở lại", "CHỜ BACKEND"],
  ];
  function trangThaiRoute() {
    return {
      dang_dung: API_DANG_DUNG.length, cho_backend: API_CHO_BACKEND.length,
      ghi_chu: "màn nào dựa trên route CHỜ BACKEND thì hiện ô 'chưa nối backend', "
             + "không hiện số 0 như thể đã đo được",
    };
  }

  dat({
    MAN: MAN, TT_DANG_KY: TT_DANG_KY, LOAI_LICH_SU: LOAI_LICH_SU,
    nhanDangKy: nhanDangKy, nhanLichSu: nhanLichSu,
    dinhDangDong: dinhDangDong, chuTyLe: chuTyLe,
    NGUONG_SAP_HET: NGUONG_SAP_HET, mucCanhBao: mucCanhBao,
    dungBangMucDung: dungBangMucDung,
    NHAN_BAT_BUOC: NHAN_BAT_BUOC, tomTatDuThao: tomTatDuThao,
    kiemTruocKhiGoi: kiemTruocKhiGoi,
    API_DANG_DUNG: API_DANG_DUNG, API_CHO_BACKEND: API_CHO_BACKEND,
    trangThaiRoute: trangThaiRoute,
  });
})(function (api) {
  if (typeof module !== "undefined" && module.exports) module.exports = api;       // Node — bộ thử
  if (typeof window !== "undefined") window.VIPBILLING = api;                       // trình duyệt
});
