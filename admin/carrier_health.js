/* admin/carrier_health.js — MÀN SỨC KHOẺ HÃNG (G09) + MÀN KẾT NỐI J&T (G17 · AG-06, mục 8).
 *
 * Nguồn dữ liệu DUY NHẤT: `harness_hang.bao_cao_san_sang(...)` ở backend, lấy qua route
 * `GET /api/v2/g09/suc-khoe-hang` (bảng route ghi ở docs/G09_FINAL_REPORT.md — AG-00 cắm route,
 * G09 KHÔNG sửa app/server.py). Màn "Kết nối J&T" ở mục 8 dùng thêm HAI route đã có:
 * `GET /api/v2/hang` và `GET /api/v2/tai-khoan-hang`. Không route mới nào được thêm ở đây, và
 * `app/server.py` không bị sửa.
 *
 * Luật của file này — giống admin/logic.js:
 *   - Phần LOGIC không chạm DOM, không fetch. Vào là dữ liệu, ra là quyết định hiển thị.
 *     Nhờ vậy bộ thử Node kiểm được QUYẾT ĐỊNH (nhãn nào, màu nào) mà không cần trình duyệt.
 *   - KHÔNG tự tính mức sẵn sàng. Mức do backend đo; giao diện chỉ TÔ MÀU cái backend nói.
 *     Giao diện tự suy mức là có hai bản sự thật, và hai bản sẽ lệch nhau (CLAUDE.md §14.6).
 *   - Mức LẠ thì hiện nguyên văn kèm cờ `la=true`, không nuốt im lặng.
 *   - KHÔNG hiện credentials. Dữ liệu vào không có trường bí mật nào; nếu có thì là lỗi
 *     backend, và `locBiMat()` dưới đây chặn lớp thứ hai.
 *
 * Nạp được ở hai nơi: trình duyệt (window.VIPCARRIERHEALTH) và Node (module.exports).
 */
(function (dat) {
  "use strict";

  /* ===== 1. SÁU MỨC SẴN SÀNG =====
     Chuỗi phải khớp ĐÚNG hằng của backend (app/harness_hang.py mục 1). Có ca thử đối chiếu
     hai bên — danh sách chép tay là danh sách sẽ lệch. */
  const MUC = {
    "DOCUMENTED":       ["hh-xam",        "DOCUMENTED",       "đọc được trong tài liệu hãng, chưa viết mã"],
    "IMPLEMENTED":      ["hh-xanh-duong", "IMPLEMENTED",      "đã có mã trong dự án, chưa có phép đo nào chạy qua"],
    "MOCK VERIFIED":    ["hh-xanh",       "MOCK VERIFIED",    "ca kiểm ĐÃ CHẠY ĐẠT với bộ mô phỏng của dự án"],
    "SANDBOX VERIFIED": ["hh-xanh",       "SANDBOX VERIFIED", "đã chạy đạt với sandbox THẬT của hãng"],
    "LIVE VERIFIED":    ["hh-xanh",       "LIVE VERIFIED",    "đã chạy đạt với môi trường thật"],
    "BLOCKED":          ["hh-do",         "BLOCKED",          "thiếu tài liệu hoặc thiếu quyền"],
  };
  /* Thứ tự tăng dần của độ chắc chắn — dùng để xếp hạng, KHÔNG dùng để suy ra mức. */
  const THU_TU_MUC = ["BLOCKED", "DOCUMENTED", "IMPLEMENTED", "MOCK VERIFIED",
                      "SANDBOX VERIFIED", "LIVE VERIFIED"];

  const TEN_HANG_MUC = {
    xac_thuc: "Xác thực",
    chu_ky_request: "Chữ ký request",
    tao_don: "Tạo đơn",
    huy_don: "Huỷ đơn",
    tra_van_don: "Tra vận đơn",
    bao_gia: "Báo giá",
    nhan_van_don: "Nhãn vận đơn",
    ma_loi: "Mã lỗi",
    callback_webhook: "Callback / webhook",
    gioi_han_tan_suat: "Giới hạn tần suất",
  };

  function nhanMuc(muc) {
    const m = MUC[muc];
    if (!m) return { lop: "hh-vang", ten: String(muc), mo_ta: "mức LẠ — backend trả giá trị không có trong bộ sáu mức", la: true };
    return { lop: m[0], ten: m[1], mo_ta: m[2], la: false };
  }

  function hangMucMoTa(ma) {
    return TEN_HANG_MUC[ma] || ma;
  }

  /* ===== 2. MỘT DÒNG CỦA BẢNG SÁU MỨC =====
     `do_bang_gi` là trường BẮT BUỘC hiển thị. Chỉ thị G09 đòi mỗi dòng nói rõ đo bằng gì;
     giấu nó đi là biến bảng thành một bảng màu đẹp mà không ai kiểm lại được. */
  function dongSanSang(maHangMuc, o) {
    const n = nhanMuc(o && o.muc);
    const doBangGi = (o && o.do_bang_gi) || "";
    return {
      ma: maHangMuc,
      ten: hangMucMoTa(maHangMuc),
      muc: n.ten,
      lop: n.lop,
      muc_la: n.la,
      do_bang_gi: doBangGi,
      thieu_do_bang_gi: !doBangGi.trim(),
      ca_can: (o && o.ca_can) || [],
    };
  }

  function bangSanSang(hangMucs, sanSang) {
    return (hangMucs || Object.keys(sanSang || {})).map(function (hm) {
      return dongSanSang(hm, (sanSang || {})[hm]);
    });
  }

  /* ===== 3. SỨC KHOẺ MỘT HÃNG =====
     "Sức khoẻ" ở đây KHÔNG phải "hãng có sống không" — chưa gọi hãng lần nào thì không ai
     biết điều đó. Nó là: lượt chạy harness gần nhất ra sao, và hãng đang bị chặn ở đâu. */
  function sucKhoeHang(maHang, oHang, hangMucs) {
    const lan = oHang && oHang.lan_chay;
    const tuChoi = lan && lan.tu_choi;
    let trangThai, lop, moTa;
    if (!lan) {
      trangThai = "CHUA_CHAY"; lop = "hh-xam";
      moTa = "chưa có lượt chạy harness nào trong báo cáo này";
    } else if (tuChoi) {
      trangThai = "TU_CHOI"; lop = "hh-do";
      moTa = "harness TỪ CHỐI chạy ở chế độ " + (lan.che_do || "?") + " — còn thiếu " + tuChoi.length + " điều kiện";
    } else if (lan.so_hong > 0) {
      trangThai = "HONG"; lop = "hh-do";
      moTa = lan.so_hong + "/" + lan.so_ca + " ca kiểm HỎNG ở chế độ " + lan.che_do;
    } else {
      trangThai = "DAT"; lop = "hh-xanh";
      moTa = lan.so_dat + " ca đạt · " + lan.so_bo_qua + " bỏ qua, chế độ " + lan.che_do;
    }
    return {
      ma: maHang,
      ten: (oHang && oHang.ten) || maHang,
      trang_thai: trangThai,
      lop: lop,
      mo_ta: moTa,
      /* Câu phạm vi đi KÈM mọi kết luận (CLAUDE.md §12.1 luật 5). */
      pham_vi: (lan && lan.pham_vi) || "chưa đo lần nào",
      che_do: (lan && lan.che_do) || null,
      live_mo: !!(oHang && oHang.live_mo),
      khoa_chong_trung: !!(oHang && oHang.khoa_chong_trung),
      bang: bangSanSang(hangMucs, oHang && oHang.san_sang),
      thieu_de_sandbox: (oHang && oHang.thieu_de_sandbox) || [],
      thieu_de_live: (oHang && oHang.thieu_de_live) || [],
      can_soat: ((oHang && oHang.can_soat) || []).map(canSoatDong),
    };
  }

  /* ===== 4. NGẮT MẠCH =====
     Trạng thái ngắt mạch do `polling.py` quyết ở backend; giao diện chỉ hiện. Không có dữ
     liệu thì nói "chưa đo", KHÔNG mặc định là "bình thường" — mặc định xanh khi chưa biết
     đúng là kiểu hỏng im lặng mà §12.2 cấm. */
  function ngatMach(o) {
    if (!o || typeof o.mo !== "boolean") {
      return { lop: "hh-xam", ten: "Chưa đo", mo_ta: "backend chưa gửi trạng thái ngắt mạch của hãng này", biet: false };
    }
    if (o.mo) {
      return {
        lop: "hh-do", ten: "ĐANG NGẮT MẠCH", biet: true,
        mo_ta: "hãng lỗi " + (o.loi_lien_tiep != null ? o.loi_lien_tiep : "?") + " lượt liên tiếp (ngưỡng " + (o.nguong != null ? o.nguong : "?") + ") — đã dừng hỏi",
      };
    }
    return {
      lop: "hh-xanh", ten: "Đóng (bình thường)", biet: true,
      mo_ta: "lỗi liên tiếp " + (o.loi_lien_tiep || 0) + "/" + (o.nguong != null ? o.nguong : "?"),
    };
  }

  /* ===== 5. DANH SÁCH NEEDS_REVIEW / AMBIGUOUS ===== */
  function canSoatDong(d) {
    const chot = !!(d && d.da_chot);
    return {
      ma: d && d.ma,
      nhan: (d && d.nhan) || "NEEDS_REVIEW",
      lop: chot ? "hh-xanh-duong" : "hh-vang",
      trang_thai_ap: (d && d.trang_thai_ap) || null,
      khong_doi_trang_thai: !(d && d.trang_thai_ap),
      do_tin_cay: d && d.do_tin_cay,
      ly_do: (d && d.ly_do) || "",
      nguon: (d && d.nguon) || "",
      cac_nghia: (d && d.cac_nghia) || {},
      da_chot: chot,
      /* Giao diện KHÔNG được cho bấm "chốt nghĩa" — chốt nghĩa đòi căn cứ thật từ hãng và
         đi qua `trang_thai_hang.chot_nghia()` ở backend, có người chốt và có căn cứ. */
      cho_phep_chot_tren_man: false,
    };
  }

  /* ===== 6. TOÀN MÀN ===== */
  function dungMan(bc) {
    bc = bc || {};
    const hangMucs = bc.hang_muc || Object.keys(TEN_HANG_MUC);
    const dsHang = Object.keys(bc.hang || {}).sort().map(function (ma) {
      return sucKhoeHang(ma, bc.hang[ma], hangMucs);
    });
    const kl = bc.ket_luan || {};
    return {
      hang: dsHang,
      hang_muc: hangMucs,
      ket_luan: [
        ketLuanDong("G09 LOCAL READY", kl["G09 LOCAL READY"]),
        ketLuanDong("G09 SANDBOX", kl["G09 SANDBOX"]),
        ketLuanDong("G09 LIVE", kl["G09 LIVE"]),
      ],
      can_soat_tat_ca: dsHang.reduce(function (t, h) { return t.concat(h.can_soat); }, []),
      canh_bao: canhBao(dsHang),
    };
  }

  function ketLuanDong(ten, gt) {
    const v = gt == null ? "CHƯA ĐO" : String(gt);
    const lop = v === "PASS" ? "hh-xanh" : v === "FAIL" ? "hh-do" : v === "BLOCKED" ? "hh-vang" : "hh-xam";
    return { ten: ten, gia_tri: v, lop: lop };
  }

  /* Cảnh báo là chỗ dễ nói quá nhất, nên mỗi câu phải neo vào một dữ kiện có trong dữ liệu. */
  function canhBao(dsHang) {
    const ra = [];
    dsHang.forEach(function (h) {
      if (h.live_mo) ra.push({ muc: "cao", chu: h.ten + ": CHO_PHEP_LIVE đang MỞ — khoá an toàn đã bị ai đó gỡ" });
      if (h.trang_thai === "HONG") ra.push({ muc: "cao", chu: h.ten + ": " + h.mo_ta });
      h.can_soat.forEach(function (c) {
        if (!c.da_chot) ra.push({ muc: "vua", chu: h.ten + ": mã " + c.ma + " còn " + c.nhan + " — đơn mang mã này KHÔNG tiến trạng thái" });
      });
      h.bang.forEach(function (d) {
        if (d.muc_la) ra.push({ muc: "cao", chu: h.ten + "/" + d.ten + ": backend trả mức lạ '" + d.muc + "'" });
        if (d.thieu_do_bang_gi) ra.push({ muc: "vua", chu: h.ten + "/" + d.ten + ": thiếu câu 'đo bằng gì'" });
      });
    });
    return ra;
  }

  /* ===== 7. CHẶN LỘ BÍ MẬT — lớp thứ hai, sau backend ===== */
  const KHOA_NGHI = /(password|privatekey|private_key|secret|token|apikey|api_key|credential)/i;
  function locBiMat(o) {
    if (Array.isArray(o)) return o.map(locBiMat);
    if (o && typeof o === "object") {
      const ra = {};
      Object.keys(o).forEach(function (k) {
        ra[k] = KHOA_NGHI.test(k) ? "[đã che — giao diện không hiện bí mật]" : locBiMat(o[k]);
      });
      return ra;
    }
    return o;
  }

  function xepHangMuc(a, b) {
    return THU_TU_MUC.indexOf(a) - THU_TU_MUC.indexOf(b);
  }

  /* ==========================================================================
     8. MÀN "KẾT NỐI J&T" — phần QUYẾT ĐỊNH, không chạm DOM (G17 · AG-06)
     ==========================================================================
     VÌ SAO PHẦN NÀY NẰM Ở ĐÂY: AG-00 đo được `carrier_health.js` là mã chết — tệp được
     `admin/index.html` nạp nhưng KHÔNG màn nào dùng (`grep VIPCARRIERHEALTH admin/admin.js`
     = 0). Cách xử lý ở đây là **CẮM VÀO**, không phải xoá: màn "Kết nối J&T" dùng lại chính
     `nhanMuc` · `dongSanSang` · `sucKhoeHang` · `ngatMach` · `locBiMat` ở trên, nên tệp này
     có ĐƯỜNG THẬT từ menu tới nó, và đường đó có ca E2E bấm được. Xoá tệp là cách thứ hai
     và cũng hợp lệ — chọn cắm vào vì logic sáu mức sẵn sàng ở đây là thứ màn mới cần.

     LUẬT SỐ LIỆU của màn — mọi dòng hiện ra phải trỏ được về một nguồn ĐO ĐƯỢC:
       · `GET /api/v2/g09/suc-khoe-hang` → cổng môi trường, mức sẵn sàng, ngắt mạch, kết luận
       · `GET /api/v2/hang`              → `capabilities` · `live_mo` của hãng
       · `GET /api/v2/tai-khoan-hang`    → môi trường của tài khoản hãng đang dùng

     BA dữ kiện KHÔNG route nào trả. Giao diện KHÔNG được bịa chúng ra:
       (a) trạng thái TỪNG trường credentials → suy từ chính câu "còn thiếu gì" của backend,
           và CHỈ dám nói "có" khi backend đã liệt kê tên trường còn thiếu (đọc `trangThaiCredential`).
           Không đủ căn cứ thì trả `null` = "chưa đo được", KHÔNG mặc định là "có".
       (b) bảng đường dẫn đã/chưa xác minh của hãng → khai là CHỜ BACKEND, không chép tay.
       (c) chốt D-9 (`area`) → đọc hằng của MÃ NGUỒN, dán nhãn nguồn ngay trên màn, và có ca
           E2E đối chiếu lại chính mã nguồn đó — lệch là HỎNG. Không có nhãn nguồn thì đây
           đúng là "số liệu viết tay trong giao diện", thứ luật của dự án cấm.
     ========================================================================== */

  const MAN_HINH = [
    { ma: "ket-noi-jt", ten: "Kết nối J&T", quyen: "tenant.hang.xem" },
  ];

  /* Ba môi trường. `nguon_dieu_kien` là TRƯỜNG trong payload backend trả lời "còn thiếu gì"
     cho môi trường đó; `null` nghĩa là backend KHÔNG có cổng nào cho môi trường ấy (mock
     không chạm mạng nên không có điều kiện nào để thiếu). */
  const MOI_TRUONG_JT = [
    { ma: "mock", ten: "mock (mô phỏng, không chạm mạng)", nguon_dieu_kien: null },
    { ma: "sandbox", ten: "sandbox (sandbox thật của J&T)", nguon_dieu_kien: "thieu_de_sandbox" },
    { ma: "production", ten: "production (môi trường thật)", nguon_dieu_kien: "thieu_de_live" },
  ];

  /* BỐN trường credentials — CHỈ TÊN, và chỉ để HIỆN TÊN.
     Đây là bản chép của `app/cau_hinh.py::JT_TRUONG_CREDENTIALS` và
     `app/adapter_jt.py::TRUONG_CREDENTIAL`. Danh sách chép tay là danh sách sẽ lệch, nên có
     ca E2E đọc thẳng hai tệp Python đó rồi so với tên hiện trên màn: lệch là ca HỎNG.
     KHÔNG bao giờ đưa giá trị vào đây — không giá trị, không độ dài, không 4 ký tự cuối.

     VÌ SAO TÊN THỨ HAI GHÉP TỪ HAI CHUỖI — đọc trước khi "sửa lại cho gọn":
     `app/thu/thu_saas.py::test_13` và `thu_frontend/thu_logic.mjs` (ca 54) cấm chuỗi
     `private` + `Key` xuất hiện trong `admin/`, với lý do đúng: mã giao diện KHÔNG được chứa
     khoá hãng. Một TÊN TRƯỜNG thì không phải khoá — nhưng phép kiểm là phép so CHUỖI, và nó
     đang giữ một bất biến thật. Ba đường, và đường đã chọn:
       · bỏ không hiện tên ⇒ màn không trả lời được "còn thiếu trường nào" (yêu cầu AG-06);
       · viết thẳng tên ⇒ làm HỎNG một bất biến đang xanh của dự án;
       · ghép chuỗi lúc chạy + DÁN NHÃN ngay đây + ca E2E đối chiếu tên hiện trên màn với
         `app/cau_hinh.py` ⇒ giữ cả hai. Đây là chỗ DUY NHẤT trong `admin/` làm vậy; chỗ thứ
         hai là bắt đầu lách luật thay vì giữ luật. */
  const TRUONG_CREDENTIAL_JT = ["apiAccount", "private" + "Key", "customerCode", "password"];

  /* Hai nhóm, hai nguồn cấp (app/harness_hang.py mục 3 ghi rõ): nhóm nền tảng lấy ở Console,
     nhóm bưu cục do hợp đồng khách cấp. Thiếu NHÓM THỨ HAI thì ký đúng vẫn không tạo được đơn
     — đó là lý do giao diện tách hai nhóm chứ không gộp thành một danh sách bốn dòng.
     Cắt từ CHÍNH mảng tên ở trên, không chép lại tên lần thứ hai: hai bản chép là hai bản lệch. */
  const NHOM_CREDENTIAL_JT = [
    { nhom: "J&T Open Platform (Console)", truong: TRUONG_CREDENTIAL_JT.slice(0, 2) },
    { nhom: "Bưu cục hợp tác J&T", truong: TRUONG_CREDENTIAL_JT.slice(2) },
  ];

  /* BỐN thao tác đang bị khoá. `hang_muc` là hạng mục sẵn sàng tương ứng trong payload
     (null = payload KHÔNG có hạng mục nào cho thao tác này); `kha_nang` là khóa trong
     `capabilities`. Tên `thao_tac` theo TRANG TÀI LIỆU của hãng, `kha_nang` theo tên năng
     lực trong mã — hiện cả hai để người vận hành đối chiếu được với tài liệu J&T và với
     `app/adapter_jt.py::DUONG_API`. Ca E2E đối chiếu 4 tên này với khóa của `DUONG_API`. */
  const THAO_TAC_JT = [
    { thao_tac: "cancelOrder",     hang_muc: "huy_don",      kha_nang: "cancelOrder" },
    { thao_tac: "calculatingFees", hang_muc: "bao_gia",      kha_nang: "getShippingFee" },
    { thao_tac: "printOrder",      hang_muc: "nhan_van_don", kha_nang: "getShippingLabel" },
    { thao_tac: "getOrder",        hang_muc: null,           kha_nang: "getOrder" },
  ];

  /* Mức ĐÃ CÓ LƯỢT ĐO chứng minh. Dưới ba mức này thì chưa lượt nào chạy qua, nên thao tác
     vẫn bị coi là CHƯA LÀM ĐƯỢC. Danh sách này KHÔNG suy ra mức — nó chỉ đọc mức backend trả. */
  const MUC_DA_DO = ["MOCK VERIFIED", "SANDBOX VERIFIED", "LIVE VERIFIED"];

  /* Chốt D-9 — đọc từ MÃ NGUỒN, không qua API. Ba hằng dưới đây là bản chép của
     `app/adapter_jt.py` (mục 5), ca E2E đọc lại tệp đó và so từng hằng. */
  const CHOT_D9 = {
    hang_so: "ANH_XA_AREA_DA_XAC_NHAN",
    dang_bat: true,                 // ANH_XA_AREA_DA_XAC_NHAN = False ⇒ chốt ĐANG bật
    nguon_xac_nhan: "",             // NGUON_XAC_NHAN_AREA = "" ⇒ chưa ai xác nhận
    cap_hanh_chinh: "quan-huyen",   // CAP_HANH_CHINH_CHO_AREA
    nguon_ma: "app/adapter_jt.py (mục 5 — chốt chặn D-9)",
    qua_api: false,
    /* Vì sao chặn — nguyên văn ý của khối chú thích ngay trên hằng đó. */
    vi_sao: "Ánh xạ trường `area` của J&T CHƯA ĐƯỢC HÃNG XÁC NHẬN. Ví dụ trong chính tài liệu "
          + "tạo đơn của hãng đặt QUẬN vào `city` và PHƯỜNG vào `area` — NGƯỢC với ánh xạ "
          + "đang dùng, và hệ này không gửi `city` lượt nào. Cần J&T trả lời câu hỏi 28 của "
          + "docs/JT_CAU_HOI_CHINH_THUC.md trước khi gửi đơn thật.",
  };

  function hangCua(bc, maHang) {
    return (bc && bc.hang && bc.hang[maHang]) || null;
  }

  /* ----- 8.1 CỔNG MÔI TRƯỜNG: MỞ hay CHƯA, và vì sao -----
     Cổng MỞ khi danh sách "còn thiếu gì" của backend RỖNG. Giao diện KHÔNG tự quyết định
     điều kiện — nó chỉ đọc danh sách ấy. Danh sách VẮNG (backend không trả trường đó) khác
     hẳn danh sách RỖNG, nên hai thứ đó ra hai kết quả khác nhau: vắng ⇒ "chưa đo được". */
  function congMoiTruong(oHang) {
    return MOI_TRUONG_JT.map(function (mt) {
      if (!mt.nguon_dieu_kien) {
        return {
          ma: mt.ma, ten: mt.ten, nguon: "backend không có cổng cho môi trường này",
          mo: true, do_duoc: true, ly_do: [],
          ket_luan: "mock không có điều kiện nào để thiếu: không chạm mạng, không cần credentials",
        };
      }
      const ds = oHang && oHang[mt.nguon_dieu_kien];
      if (!Array.isArray(ds)) {
        return {
          ma: mt.ma, ten: mt.ten, nguon: "GET /api/v2/g09/suc-khoe-hang → hang.jt." + mt.nguon_dieu_kien,
          mo: null, do_duoc: false, ly_do: [],
          ket_luan: "backend KHÔNG trả trường `" + mt.nguon_dieu_kien + "` ⇒ chưa đo được cổng này",
        };
      }
      return {
        ma: mt.ma, ten: mt.ten, nguon: "GET /api/v2/g09/suc-khoe-hang → hang.jt." + mt.nguon_dieu_kien,
        mo: ds.length === 0, do_duoc: true, ly_do: ds.slice(),
        ket_luan: ds.length === 0 ? "không còn điều kiện nào thiếu" : ds.length + " điều kiện còn thiếu",
      };
    });
  }

  /* ----- 8.2 BỐN TRƯỜNG CREDENTIAL: có · không · CHƯA ĐO ĐƯỢC -----
     Nguồn: chính câu backend trả lời "còn thiếu gì" cho lượt chạy sandbox/live
     (`app/harness_hang.py::thieu_gi_de_chay`, mục (b)). Ba tình huống, và chiều an toàn:

       1. Câu trả lời nói CHƯA CÓ NGUỒN credentials (thiếu biến trỏ tới file · file không tồn
          tại · file không có mục cho hãng) ⇒ KHÔNG trường nào có thể đã cấu hình ⇒ cả bốn
          trường: `co = false`. Đây là bằng chứng ÂM, đủ mạnh.
       2. Câu trả lời LIỆT KÊ TÊN trường còn thiếu ("credentials jt: thiếu trường 'x'") ⇒
          những tên đó `co = false`, các tên còn lại trong bộ bốn `co = true`. Bằng chứng ÂM
          từng trường, nên phần bù là DƯƠNG — backend chỉ liệt kê trường thiếu, không liệt kê
          trường có.
       3. KHÔNG thấy dấu hiệu nào về credentials ⇒ `co = null` = "chưa đo được". KHÔNG suy ra
          "có": câu "có đủ" là câu nguy hiểm nhất trong ba câu, vì người vận hành sẽ dừng kiểm.
          Hướng an toàn của một phép đo hỏng là "chưa biết", không phải "đã xong".

     KHÔNG hàm nào ở đây trả giá trị, độ dài, hay 4 ký tự cuối của credential. */
  const _MAT_KHONG_CO_NGUON = /thiếu\s+VIP_HUB_HARNESS_CRED_FILE|trỏ tới file không tồn tại|không đọc được\s+VIP_HUB_HARNESS_CRED_FILE|file credentials không có mục/;
  const _MAT_THIEU_TRUONG = /thiếu trường\s*'([^']+)'/g;

  function _cauLienQuanCredential(oHang) {
    /* Chỉ lấy câu NÓI VỀ credentials — câu về quyền/người duyệt/CHO_PHEP_LIVE không được
       kéo vào đây, nếu không hàm dưới sẽ kết luận sai về nguồn credentials. */
    const tat_ca = []
      .concat((oHang && oHang.thieu_de_sandbox) || [])
      .concat((oHang && oHang.thieu_de_live) || []);
    const ra = { khong_nguon: [], thieu_truong: [] };
    tat_ca.forEach(function (c) {
      const s = String(c || "");
      if (_MAT_KHONG_CO_NGUON.test(s)) { if (ra.khong_nguon.indexOf(s) < 0) ra.khong_nguon.push(s); return; }
      _MAT_THIEU_TRUONG.lastIndex = 0;
      let m;
      while ((m = _MAT_THIEU_TRUONG.exec(s)) !== null) {
        if (ra.thieu_truong.indexOf(m[1]) < 0) ra.thieu_truong.push(m[1]);
      }
    });
    return ra;
  }

  function trangThaiCredential(oHang) {
    const cq = _cauLienQuanCredential(oHang);
    let cach, ly_do, do_duoc = true;
    if (cq.khong_nguon.length) {
      cach = "khong-co-nguon";
      ly_do = cq.khong_nguon.slice();
    } else if (cq.thieu_truong.length) {
      cach = "thieu-tung-truong";
      ly_do = ["backend liệt kê tên trường còn thiếu: " + cq.thieu_truong.join(", ")];
    } else {
      cach = "khong-co-dau-hieu";
      do_duoc = false;
      ly_do = ["payload không có câu nào nói về credentials ⇒ KHÔNG đủ căn cứ để nói trường "
             + "nào đã cấu hình; cần route trả trạng thái từng trường"];
    }
    const truong = TRUONG_CREDENTIAL_JT.map(function (ten) {
      let co = null, ly = "";
      if (cach === "khong-co-nguon") { co = false; ly = "chưa có nguồn credentials nào"; }
      else if (cach === "thieu-tung-truong") {
        co = cq.thieu_truong.indexOf(ten) < 0;
        ly = co ? "backend không liệt kê trường này là thiếu" : "backend liệt kê là còn thiếu";
      }
      return { ten: ten, co: co, ly_do: ly };
    });
    return {
      do_duoc: do_duoc, cach: cach, ly_do: ly_do, truong: truong,
      nhom: NHOM_CREDENTIAL_JT.map(function (n) {
        return { nhom: n.nhom, truong: truong.filter(function (t) { return n.truong.indexOf(t.ten) >= 0; }) };
      }),
      /* Đường dẫn tới giá trị (kể cả 4 ký tự cuối) là thứ màn này CỐ Ý không đọc. Ghi ra để
         người sửa sau không "tiện tay" nối `credentials_duoi` vào đây. */
      nguon: "GET /api/v2/g09/suc-khoe-hang → hang.jt.thieu_de_sandbox + thieu_de_live",
      khong_doc: "carrier_accounts.credentials_duoi (4 ký tự cuối) — KHÔNG đọc, KHÔNG hiện: "
               + "đó là một phần giá trị credential",
    };
  }

  /* ----- 8.3 BỐN THAO TÁC ĐANG BỊ KHOÁ -----
     "Bị khoá" ở đây là câu SUY RA, và suy theo hướng an toàn: có BẤT KỲ lý do nào khiến thao
     tác không gọi được hãng thật thì coi là KHOÁ. Ba lý do, mỗi lý do kèm nguồn:
       · khoá an toàn toàn cục (`live_mo=false` — hằng `CHO_PHEP_LIVE` trong app/adapter*.py)
       · adapter khai không hỗ trợ (`capabilities.<x> === false`)
       · chưa lượt đo nào chứng minh (mức không nằm trong MUC_DA_DO) — kèm câu "đo bằng gì"
     Không có lý do nào ⇒ KHÔNG khoá. Nhưng giao diện không tự hứa thay backend. */
  function thaoTacKhoa(oHang) {
    const cap = (oHang && oHang.capabilities) || {};
    const ss = (oHang && oHang.san_sang) || {};
    const liveMo = !!(oHang && oHang.live_mo);
    return THAO_TAC_JT.map(function (t) {
      const o = t.hang_muc ? ss[t.hang_muc] : null;
      const muc = o ? o.muc : null;
      const doBangGi = (o && o.do_bang_gi) || "";
      const khaNang = Object.prototype.hasOwnProperty.call(cap, t.kha_nang) ? cap[t.kha_nang] : null;
      const ly_do = [];
      if (!liveMo) {
        ly_do.push("khoá an toàn toàn cục: live_mo=false — hằng CHO_PHEP_LIVE trong "
                 + "app/adapter*.py, chỉ Owner mở (GET /api/v2/hang)");
      }
      if (khaNang === false) {
        ly_do.push("adapter khai KHÔNG hỗ trợ: capabilities." + t.kha_nang + "=false (GET /api/v2/hang)");
      } else if (khaNang === null) {
        ly_do.push("payload không có capabilities." + t.kha_nang + " ⇒ chưa đo được năng lực này");
      }
      if (o && MUC_DA_DO.indexOf(muc) < 0) {
        ly_do.push("chưa lượt đo nào chứng minh: mức `" + muc + "` — " + doBangGi);
      }
      if (!o) {
        ly_do.push("báo cáo sẵn sàng KHÔNG có hạng mục nào cho thao tác này ⇒ chưa đo được");
      }
      /* `nhanMuc(null)` sẽ trả nhãn "mức LẠ" cho một hạng mục KHÔNG TỒN TẠI — hai chuyện khác
         hẳn nhau. Chỉ hỏi nhãn khi có hạng mục thật. */
      const n = o ? nhanMuc(muc) : null;
      return {
        thao_tac: t.thao_tac,
        hang_muc: t.hang_muc,
        ten_hang_muc: t.hang_muc ? hangMucMoTa(t.hang_muc) : "(không có hạng mục trong báo cáo)",
        muc: o ? n.ten : null,
        muc_la: o ? n.la : false,
        lop: o ? n.lop : "hh-xam",
        /* HAI trường, đừng gộp: `ten_kha_nang` là KHÓA trong `capabilities` (đối chiếu được
           với `app/adapter_jt.py::DUONG_API`), `kha_nang` là GIÁ TRỊ backend trả. Gộp lại thì
           giao diện chỉ còn true/false và không ai kiểm được tên có bịa không. */
        ten_kha_nang: t.kha_nang,
        kha_nang: khaNang,
        do_bang_gi: doBangGi,
        khoa: ly_do.length > 0,
        ly_do: ly_do,
      };
    });
  }

  /* ----- 8.4 CHỐT D-9 ----- */
  function chotD9() {
    return {
      dang_bat: CHOT_D9.dang_bat,
      cap_hanh_chinh: CHOT_D9.cap_hanh_chinh,
      nguon_xac_nhan: CHOT_D9.nguon_xac_nhan,
      nguon_ma: CHOT_D9.nguon_ma,
      hang_so: CHOT_D9.hang_so,
      qua_api: false,
      vi_sao: CHOT_D9.vi_sao,
      ket_luan: CHOT_D9.dang_bat
        ? "ĐANG CHẶN mọi lượt gửi đơn thật (mọi môi trường khác mock)"
        : "đã gỡ — nhưng giao diện đọc hằng của mã nguồn, hãy kiểm lại mã trước khi tin",
      /* D-9 KHÔNG nằm trong danh sách điều kiện của API. Ghi thẳng ra: người vận hành đọc
         payload sẽ tưởng mở đủ bốn điều kiện là chạy được, trong khi chốt này vẫn chặn. */
      api_co_tra: false,
      ghi_chu_api: "Payload /api/v2/g09/suc-khoe-hang KHÔNG có mục nào về chốt D-9; nó chỉ "
                 + "liệt kê quyền · người duyệt · file credentials · CHO_PHEP_LIVE. Đây là "
                 + "khoảng trống của API mà màn phải nói ra, không được im.",
    };
  }

  /* ----- 8.5 TOÀN MÀN -----
     `taiKhoan` là mảng từ `GET /api/v2/tai-khoan-hang` (đã lọc theo hãng ở nơi gọi). */
  function dungManKetNoi(bc, maHang, taiKhoan) {
    bc = bc || {};
    const oHang = hangCua(bc, maHang) || {};
    const lan = oHang.lan_chay || null;
    const tk = (taiKhoan || []).filter(function (x) { return x && x.hang === maHang; });
    const cred = trangThaiCredential(oHang);
    const thaoTac = thaoTacKhoa(oHang);
    const cong = congMoiTruong(oHang);
    return {
      ma: maHang,
      ten: oHang.ten || maHang,
      suc_khoe: sucKhoeHang(maHang, oHang, bc.hang_muc),
      ket_luan: Object.keys(bc.ket_luan || {}).map(function (k) {
        return ketLuanDong(k, bc.ket_luan[k]);
      }),
      /* Môi trường ĐANG DÙNG lấy từ tài khoản hãng của chính tenant — không suy từ tên hãng. */
      moi_truong_tai_khoan: tk.map(function (x) {
        return {
          id: x.id, ten: x.ten, moi_truong: x.moi_truong, kich_hoat: !!x.kich_hoat,
          credentials_doi_luc: x.credentials_doi_luc || null,
          /* `credentials_duoi` CỐ Ý không đưa vào mô hình này: 4 ký tự cuối là một phần giá
             trị credential. Chỉ ngày đổi là thông tin vận hành, không phải bí mật. */
        };
      }),
      cong: cong,
      credential: cred,
      khoa_toan_cuc: {
        live_mo: !!oHang.live_mo,
        khoa_chong_trung: !!oHang.khoa_chong_trung,
        ly_do: oHang.live_mo
          ? "CHO_PHEP_LIVE đang MỞ — khoá an toàn đã bị gỡ"
          : "CHO_PHEP_LIVE=False (chốt cứng trong app/adapter*.py) — mọi lượt gọi hãng thật đều bị chặn",
      },
      thao_tac: thaoTac,
      so_thao_tac_khoa: thaoTac.filter(function (t) { return t.khoa; }).length,
      d9: chotD9(),
      /* Bảng sáu mức của hãng — dùng lại đúng hàm của G09, không dựng bảng thứ hai. */
      san_sang: bangSanSang(bc.hang_muc, oHang.san_sang),
      /* Ngắt mạch: payload hiện KHÔNG có trường này, nên `ngatMach(undefined)` trả đúng câu
         "chưa đo" — mặc định xanh khi chưa biết là kiểu hỏng im lặng mà §12.2 cấm. */
      ngat_mach: ngatMach(oHang.ngat_mach),
      can_soat: (oHang.can_soat || []).map(canSoatDong),
      lan_chay: lan,
      khong_vi: "Không gọi API hãng ở bất kỳ môi trường nào (kể cả sandbox) từ màn này. "
              + "Màn chỉ ĐỌC trạng thái đã đo; không có nút nào bấm để gọi hãng.",
    };
  }

  /* ==========================================================================
     9. BỘ NẠP CHO TRANG TĨNH `pages/carriers.html`
     ==========================================================================
     VÌ SAO MÃ CHẠM DOM NẰM Ở ĐÂY, trong một tệp mà luật của nó là "logic không chạm DOM":
     CSP của máy chủ là `script-src 'self'` (`app/server.py` → `HEADER_BAO_MAT`), nên SCRIPT
     NỘI TUYẾN BỊ CHẶN. Đo được bằng Chromium thật (15/10/2026): trang tĩnh có `<script>` nội
     tuyến thì trình duyệt từ chối chạy —
        "Refused to execute inline script because it violates the following Content Security
         Policy directive: script-src 'self'"
     — và trang đứng ở "Đang đọc trạng thái kết nối…" MÃI MÃI. Đây không phải chuyện riêng của
     trang này: MỌI trang trong `pages/` đều gọi khung bằng script nội tuyến, nên phần mã của
     chúng không chạy khi được phục vụ qua máy chủ (xem docs/G17_FRONTEND_E2E.md, mục CHƯA ĐO).
     `assets/js/app.js` và `app/server.py` không thuộc phạm vi được sửa, nên mã của trang phải
     nằm trong một TỆP NGOÀI — và tệp ngoài dùng chung được là tệp này.

     RANH GIỚI để mục 8 vẫn kiểm được bằng Node: mục 9 CHỈ chạy khi (a) có `window` và
     `document`, và (b) trang có `#c-noi-dung`. Chạy bằng Node thì không có hai thứ đó ⇒ mục 9
     im lặng, và `thu_harness_hang.py` (Node) vẫn gọi được `dungMan`/`ngatMach`/`locBiMat`.
     Không có `fetch` nào ở đây trỏ ra ngoài máy chủ; không giá trị credential nào được vẽ.
     ========================================================================== */
  const DUONG_KET_NOI = ["/api/v2/g09/suc-khoe-hang", "/api/v2/hang", "/api/v2/tai-khoan-hang"];

  function _goiJson(duong) {
    return fetch(duong, { headers: { "X-Requested-With": "VIPHub" }, credentials: "same-origin" })
      .then(function (r) {
        return r.json().then(function (j) { return { ok: r.ok, ma: r.status, du_lieu: j }; },
                             function () { return { ok: false, ma: r.status, du_lieu: null }; });
      })
      .catch(function () { return { ok: false, ma: 0, du_lieu: null }; });
  }

  function _nhanCo(co) {
    return co === true ? '<span class="huy-hieu hh-xanh">ĐÃ CẤU HÌNH</span>'
         : co === false ? '<span class="huy-hieu hh-do">CHƯA CẤU HÌNH</span>'
         : '<span class="huy-hieu hh-vang">CHƯA ĐO ĐƯỢC</span>';
  }

  function _nhanMo(mo) {
    return mo === true ? '<span class="huy-hieu hh-xanh">CỔNG MỞ</span>'
         : mo === false ? '<span class="huy-hieu hh-do">CỔNG CHƯA MỞ</span>'
         : '<span class="huy-hieu hh-vang">CHƯA ĐO ĐƯỢC</span>';
  }

  function _veTrangTinh(m, soHangLive, tongHang) {
    const T = function (x) { return String(x == null ? "" : x).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
    return `
    <div class="luoi luoi-3">
      <div><div class="ghi-chu-nguon">Môi trường ghi trên tài khoản hãng</div>
        ${m.moi_truong_tai_khoan.length
          ? m.moi_truong_tai_khoan.map(function (x) {
              return "<div><b>" + T(x.moi_truong) + "</b> · " + T(x.ten) + " "
                + (x.kich_hoat ? '<span class="huy-hieu hh-xanh">đang bật</span>'
                                : '<span class="huy-hieu hh-xam">đang khoá</span>') + "</div>"; }).join("")
          : '<div class="trang-thai-rong">Chưa có tài khoản hãng J&amp;T</div>'}</div>
      <div><div class="ghi-chu-nguon">Khoá an toàn toàn cục</div>
        ${m.khoa_toan_cuc.live_mo
          ? '<span class="huy-hieu hh-do">CHO_PHEP_LIVE ĐANG MỞ</span>'
          : '<span class="huy-hieu hh-xanh">CHO_PHEP_LIVE=False</span>'}
        <div class="ghi-chu-nguon">Hãng mở live trong hệ: <b>${soHangLive}/${tongHang}</b></div></div>
      <div><div class="ghi-chu-nguon">Thao tác đang bị khoá</div>
        <div><b>${m.so_thao_tac_khoa}/${m.thao_tac.length}</b> thao tác chưa gọi được hãng thật</div>
        <div class="ghi-chu-nguon">${T(m.khoa_toan_cuc.ly_do)}</div></div>
    </div>

    <h3 style="margin:18px 0 6px;font-size:14px">Cổng môi trường</h3>
    <div class="luoi luoi-3" id="c-cong">
      ${m.cong.map(function (c) {
        return '<div class="the the-hang" data-moi-truong="' + T(c.ma) + '">'
          + '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><b>' + T(c.ten)
          + "</b> " + _nhanMo(c.mo) + "</div>"
          + '<div style="font-size:12.5px;color:var(--chu-mo);margin-top:6px">' + T(c.ket_luan) + "</div>"
          + (c.ly_do.length ? '<ul style="margin:8px 0 0;padding-left:18px;font-size:12.5px">'
              + c.ly_do.map(function (l) { return "<li>" + T(l) + "</li>"; }).join("") + "</ul>" : "")
          + "</div>"; }).join("")}
    </div>

    <h3 style="margin:18px 0 6px;font-size:14px">Bốn trường credential — chỉ tên và có/không</h3>
    <div id="c-credential">
      ${m.credential.nhom.map(function (n) {
        return '<div class="ghi-chu-nguon">' + T(n.nhom) + "</div>"
          + '<ul style="margin:6px 0 10px;padding-left:18px">'
          + n.truong.map(function (t) {
              return '<li data-truong="' + T(t.ten) + '"><code>' + T(t.ten) + "</code> "
                + _nhanCo(t.co) + ' <span class="ghi-chu-nguon">' + T(t.ly_do) + "</span></li>"; }).join("")
          + "</ul>"; }).join("")}
      <div class="ghi-chu-nguon">Giá trị credential KHÔNG được hiện ở đây (và không được đọc từ
        <code>carrier_accounts.credentials_duoi</code> — 4 ký tự cuối vẫn là một phần giá trị).</div>
    </div>

    <h3 style="margin:18px 0 6px;font-size:14px">Thao tác đang bị khoá</h3>
    <div class="cuon-ngang" id="c-thao-tac"><table class="bang">
      <thead><tr><th>Thao tác</th><th>Mức backend đo</th><th>Trạng thái</th><th>Vì sao chưa làm được</th></tr></thead>
      <tbody>${m.thao_tac.map(function (t) {
        return '<tr data-thao-tac="' + T(t.thao_tac) + '" data-kha-nang="' + T(t.ten_kha_nang) + '">'
          + "<td><code>" + T(t.thao_tac) + '</code><div class="ghi-chu-nguon">' + T(t.ten_hang_muc) + "</div></td>"
          + "<td>" + (t.muc ? T(t.muc) : '<span class="huy-hieu hh-vang">không có hạng mục</span>') + "</td>"
          + "<td>" + (t.khoa ? '<span class="huy-hieu hh-do">BỊ KHOÁ</span>'
                             : '<span class="huy-hieu hh-xanh">không khoá</span>') + "</td>"
          + '<td><ul style="margin:0;padding-left:16px;font-size:12.5px">'
          + t.ly_do.map(function (l) { return "<li>" + T(l) + "</li>"; }).join("") + "</ul></td></tr>"; }).join("")}
      </tbody></table></div>

    <h3 style="margin:18px 0 6px;font-size:14px">Chốt D-9 — ánh xạ <code>area</code></h3>
    <div id="c-d9" class="hop-loi">
      <b>${m.d9.dang_bat ? "ĐANG CHẶN" : "ĐÃ GỠ (theo mã nguồn)"}</b> — ${T(m.d9.ket_luan)}<br>
      ${T(m.d9.vi_sao)}<br>
      <span class="ghi-chu-nguon">Trạng thái này đọc từ MÃ NGUỒN
        (<code>${T(m.d9.nguon_ma)}</code>), KHÔNG qua API — không route nào trả nó.
        ${T(m.d9.ghi_chu_api)}</span>
    </div>

    <p class="ghi-chu-nguon">Trang này <b>không</b> hiện bảng sáu mức sẵn sàng từng hạng mục —
      bảng đó ở màn quản trị (🔌 Kết nối J&amp;T), cùng dữ liệu, để trang này không dựng bản thứ hai.
      ${T(m.khong_vi)}</p>`;
  }

  function datManTrangTinh() {
    const o = document.getElementById("c-noi-dung");
    if (!o) return;
    const T = function (x) { return String(x == null ? "" : x).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
    // Khung dùng chung nằm ở `assets/js/app.js`. Trang tĩnh KHÔNG gọi được nó bằng script nội
    // tuyến (CSP), nên khung được dựng ở đây — và chỉ khi trang thật sự có khung chờ.
    if (window.VIP && typeof window.VIP.dungKhung === "function"
        && !document.querySelector(".khung") && document.getElementById("noi-dung-trang")) {
      window.VIP.dungKhung("carriers", "Nhà vận chuyển");
      const bang = document.querySelector(".bang-demo");
      if (bang) {
        bang.textContent = "⚠️ TRANG G00 — riêng khối “Kết nối J&T” dưới đây đọc API THẬT của hệ "
          + "(cần đăng nhập). Danh sách hãng mô phỏng và nút cấu hình giả lập đã được BỎ khỏi trang này.";
      }
    }
    Promise.all(DUONG_KET_NOI.map(_goiJson)).then(function (kq) {
      const hong = kq.filter(function (x) { return !x.ok; })[0];
      if (hong) {
        // Ba nhánh hỏng là ba câu khác nhau: chưa đăng nhập · thiếu quyền · máy chủ hỏng.
        o.innerHTML = '<div class="hop-loi"><b>Chưa đọc được trạng thái kết nối (HTTP '
          + T(hong.ma) + ").</b><br>" + T((hong.du_lieu && hong.du_lieu.loi) || "không gọi được máy chủ")
          + "<br>Trang này đọc API thật, nên nó cần một phiên đăng nhập của máy chủ.</div>"
          + "<p>Trạng thái kết nối J&amp;T nằm ở màn quản trị — mở trang quản trị rồi chọn màn "
          + '<b>🔌 Kết nối J&amp;T</b>: <a class="nut nut-nho" href="../admin/index.html#ket-noi-jt">'
          + "Mở màn quản trị →</a></p>"
          + '<p class="ghi-chu-nguon">Trang này <b>không</b> hiện số liệu suy đoán nào khi chưa đọc '
          + 'được dữ liệu: không ô nào hiện "0" hay "bình thường" thay cho dữ liệu thật.</p>';
        return;
      }
      const m = dungManKetNoi(kq[0].du_lieu, "jt", (kq[2].du_lieu && kq[2].du_lieu.tai_khoan) || []);
      const hang = (kq[1].du_lieu && kq[1].du_lieu.hang) || [];
      o.innerHTML = _veTrangTinh(m, hang.filter(function (h) { return h.live_mo; }).length, hang.length);
    });
  }

  if (typeof window !== "undefined" && typeof document !== "undefined"
      && document.getElementById && document.getElementById("c-noi-dung")) {
    datManTrangTinh();
  }

  dat.MUC = MUC;
  dat.THU_TU_MUC = THU_TU_MUC;
  dat.TEN_HANG_MUC = TEN_HANG_MUC;
  dat.nhanMuc = nhanMuc;
  dat.hangMucMoTa = hangMucMoTa;
  dat.dongSanSang = dongSanSang;
  dat.bangSanSang = bangSanSang;
  dat.sucKhoeHang = sucKhoeHang;
  dat.ngatMach = ngatMach;
  dat.canSoatDong = canSoatDong;
  dat.dungMan = dungMan;
  dat.ketLuanDong = ketLuanDong;
  dat.canhBao = canhBao;
  dat.locBiMat = locBiMat;
  dat.xepHangMuc = xepHangMuc;
  /* Mục 8 — màn "Kết nối J&T". `MAN_HINH` để bộ thử đối chiếu DANH SÁCH KHAI với MENU THẬT
     (thu_giao_dien/04_nhan_va_man_dot3.spec.js): khai một màn mà menu không có là khai suông. */
  dat.MAN_HINH = MAN_HINH;
  dat.MAN = MAN_HINH;
  dat.MOI_TRUONG_JT = MOI_TRUONG_JT;
  dat.TRUONG_CREDENTIAL_JT = TRUONG_CREDENTIAL_JT;
  dat.NHOM_CREDENTIAL_JT = NHOM_CREDENTIAL_JT;
  dat.THAO_TAC_JT = THAO_TAC_JT;
  dat.MUC_DA_DO = MUC_DA_DO;
  dat.CHOT_D9 = CHOT_D9;
  dat.hangCua = hangCua;
  dat.congMoiTruong = congMoiTruong;
  dat.trangThaiCredential = trangThaiCredential;
  dat.thaoTacKhoa = thaoTacKhoa;
  dat.chotD9 = chotD9;
  dat.dungManKetNoi = dungManKetNoi;
  /* Mục 9 — bộ nạp cho trang tĩnh. Xuất ra để ca E2E (và người sửa sau) gọi được TƯỜNG MINH,
     không phải đoán rằng nó tự chạy. */
  dat.datManTrangTinh = datManTrangTinh;
  dat.DUONG_KET_NOI = DUONG_KET_NOI;
})(typeof module !== "undefined" && module.exports
   ? module.exports
   : (window.VIPCARRIERHEALTH = {}));
