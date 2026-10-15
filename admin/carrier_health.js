/* admin/carrier_health.js — MÀN SỨC KHOẺ HÃNG (G09).
 *
 * Nguồn dữ liệu DUY NHẤT: `harness_hang.bao_cao_san_sang(...)` ở backend, lấy qua route
 * `GET /api/g09/suc-khoe-hang` (bảng route ghi ở docs/G09_FINAL_REPORT.md — AG-00 cắm route,
 * G09 KHÔNG sửa app/server.py).
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
})(typeof module !== "undefined" && module.exports
   ? module.exports
   : (window.VIPCARRIERHEALTH = {}));
