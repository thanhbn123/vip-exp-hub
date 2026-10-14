/* admin/health.js — màn SỨC KHOẺ HỆ (G11). AG-05 DEVOPS sở hữu file này.
   `admin/` KHÔNG có thư mục con — file nằm thẳng ở đây, theo đúng ràng buộc của dự án.

   Luật của file này, lấy theo đúng khuôn `admin/logic.js`:
   - LOGIC THUẦN tách khỏi DOM, để bộ thử chạy được bằng Node mà không cần trình duyệt.
     Vào là dữ liệu, ra là dữ liệu. Nạp được ở hai nơi: `window.VIPHEALTH` và `module.exports`.
   - KHÔNG tự quyết định quyền. Backend chốt; giao diện chỉ hiển thị cái nó nhận được.
   - KHÔNG giữ secret nào, và KHÔNG hiển thị trường nào mà backend không chủ động gửi.

   ====== HAI ĐIỀU QUAN TRỌNG VỀ CÁCH MÀN NÀY ĐỌC TRẠNG THÁI ======
   1. HEALTH và READINESS hiện RIÊNG, hai dòng, hai nhãn. Gộp lại thành một đèn xanh là đúng
      cái §12.1 cấm: một chữ "ok" cho hai câu hỏi khác nhau.
   2. Phép kiểm BỊ BỎ QUA hiện màu XÁM với chữ "bỏ qua", KHÔNG hiện màu xanh. `ok: null` từ
      backend nghĩa là "chưa đo", và "chưa đo" không phải "đạt". Đây là chỗ dễ hỏng nhất của
      một màn sức khoẻ: cho cái chưa đo mượn màu của cái đã đạt. */
(function (dat) {
  "use strict";

  /* Ba màu, dùng đúng lớp CSS sẵn có của dự án (hh-xanh / hh-vang / hh-do / hh-xam). */
  var XANH = "hh-xanh", VANG = "hh-vang", DO = "hh-do", XAM = "hh-xam";

  /* ===== 1. Nhãn cho từng phép kiểm readiness ===== */
  var NHAN_KIEM = {
    thu_muc_du_lieu: ["Thư mục dữ liệu ghi được", "CSDL và khóa mã hóa nằm ở đây"],
    csdl:            ["CSDL mở được", "đo bằng một truy vấn thật, không bằng việc file có mặt"],
    schema:          ["Phiên bản schema khớp mã", "CSDL cũ hơn mã thì máy chủ TỪ CHỐI chạy"],
    khoa:            ["Khóa mã hóa đọc được", "thiếu khóa thì credentials hãng thành rác"],
    worker:          ["Worker webhook còn sống", "worker chết thì sự kiện hãng đứng trong hàng đợi"]
  };

  /* ===== 2. Đọc kết quả HEALTH ===== */
  function docSucKhoe(d) {
    if (!d || typeof d !== "object") {
      return { lop: DO, ten: "Không gọi được", mo_ta: "máy chủ không trả lời", song_giay: null };
    }
    if (d.__chua_cam_route) {
      return { lop: XAM, ten: "Chưa cắm route /api/v2/suc-khoe", song_giay: null,
               chua_cam_route: true, pham_vi: "xem bản vá P-2" };
    }
    if (d.__loi) {
      return { lop: DO, ten: "Lỗi khi gọi: " + d.__loi, song_giay: null };
    }
    return {
      lop: d.ok ? XANH : DO,
      ten: d.ok ? "Tiến trình sống" : "Tiến trình KHÔNG phản hồi",
      song_giay: typeof d.song_giay === "number" ? d.song_giay : null,
      phien_ban: d.phien_ban_ma || null,
      pid: typeof d.pid === "number" ? d.pid : null,
      /* Phạm vi do BACKEND gửi kèm, hiện nguyên văn. Giao diện không tự viết lại phạm vi:
         viết lại là có ngày hai bên nói khác nhau mà không ai thấy. */
      pham_vi: d.pham_vi || null
    };
  }

  /* ===== 3. Đọc kết quả READINESS ===== */
  function docSanSang(d) {
    if (!d || typeof d !== "object") {
      return { lop: DO, ten: "Không gọi được", dong: [], so_hong: null, so_bo_qua: 0,
               pham_vi: null };
    }
    /* "Route chưa cắm" KHÁC "hệ hỏng". Gộp hai thứ này là bắt người vận hành đi chẩn đoán một
       hệ đang chạy tốt. Bản đầu của hàm này trả "CHƯA sẵn sàng" cho cả hai, trong khi lời bình
       ở dưới lại nói là có phân biệt — lời bình nói khác mã thì lời bình là thứ sẽ được tin.
       Sửa 15/10/2026. */
    if (d.__chua_cam_route) {
      return { lop: XAM, ten: "Chưa cắm route /api/v2/san-sang", dong: [], so_hong: null,
               so_bo_qua: 0, bo_qua: [], luc: null, chua_cam_route: true,
               pham_vi: "AG-00 giữ app/server.py — xem bản vá P-2 trong docs/G11_FINAL_REPORT.md" };
    }
    if (d.__loi) {
      return { lop: DO, ten: "Lỗi khi gọi: " + d.__loi, dong: [], so_hong: null, so_bo_qua: 0,
               bo_qua: [], luc: null, pham_vi: null };
    }
    var kiem = d.kiem && typeof d.kiem === "object" ? d.kiem : {};
    var dong = [], hong = 0, boQua = 0;
    for (var ma in kiem) {
      if (!Object.prototype.hasOwnProperty.call(kiem, ma)) continue;
      var k = kiem[ma] || {};
      var nhan = NHAN_KIEM[ma] || [ma, ""];
      var lop, trangThai;
      if (k.ok === null || typeof k.ok === "undefined") {
        /* CHƯA ĐO. Không cho nó mượn màu xanh. */
        lop = XAM; trangThai = "bỏ qua — CHƯA ĐO"; boQua++;
      } else if (k.ok) {
        lop = k.canh_bao ? VANG : XANH;
        trangThai = k.canh_bao ? "đạt, có cảnh báo" : "đạt";
      } else {
        lop = DO; trangThai = "HỎNG"; hong++;
      }
      dong.push({
        ma: ma, lop: lop, ten: nhan[0], ghi_chu_nhan: nhan[1], trang_thai: trangThai,
        /* `loi`/`canh_bao`/`ghi_chu` do backend sinh, hiện nguyên văn. Trạng thái LẠ cũng hiện
           nguyên văn thay vì nuốt im lặng — cùng luật với `admin/logic.js`. */
        loi: k.loi || null,
        canh_bao: k.canh_bao || null,
        ghi_chu: k.ghi_chu || null,
        chi_tiet: tomChiTiet(k)
      });
    }
    dong.sort(function (a, b) { return a.ma < b.ma ? -1 : (a.ma > b.ma ? 1 : 0); });
    return {
      lop: d.ok ? (boQua ? VANG : XANH) : DO,
      ten: d.ok ? (boQua ? "Sẵn sàng (có phép kiểm bị bỏ qua)" : "Sẵn sàng")
                : "CHƯA sẵn sàng",
      dong: dong, so_hong: hong, so_bo_qua: boQua,
      bo_qua: Array.isArray(d.bo_qua) ? d.bo_qua : [],
      luc: d.luc || null,
      pham_vi: d.pham_vi || null
    };
  }

  /* Gom các trường phụ thành chuỗi gọn. CHỈ lấy trường đã biết tên — danh sách trắng, để một
     trường mới mang dữ liệu nhạy cảm không tự nhảy lên màn hình. */
  var TRUONG_HIEN = ["phien_ban", "can", "key_id", "so_khoa", "so_bang", "qsize",
                     "dang_xu_ly", "song", "ten"];
  function tomChiTiet(k) {
    var ra = [];
    for (var i = 0; i < TRUONG_HIEN.length; i++) {
      var t = TRUONG_HIEN[i];
      if (k && typeof k[t] !== "undefined" && k[t] !== null) ra.push(t + "=" + k[t]);
    }
    return ra.join(" · ");
  }

  /* ===== 4. Đọc metric ===== */
  function docMetric(d) {
    if (!d || typeof d !== "object") {
      return { the: [], pham_vi: null, canh_bao: ["không gọi được metric"] };
    }
    var dem = d.dem && typeof d.dem === "object" ? d.dem : {};
    var w = d.worker_webhook || {};
    var the = [
      { ma: "song", ten: "Tiến trình sống", so: d.song_giay, don_vi: "giây", lop: XAM },
      { ma: "qsize", ten: "Hàng đợi webhook", so: so(w.qsize), don_vi: "sự kiện",
        lop: muc(so(w.qsize), 50, 200) },
      { ma: "dang_xu_ly", ten: "Đang xử lý", so: so(w.dang_xu_ly), don_vi: "sự kiện", lop: XAM },
      /* DLQ > 0 là VÀNG chứ không XANH: sự kiện vào DLQ là sự kiện KHÔNG tự xử lý được nữa,
         phải có người nhìn. Để nó xanh là để nó bị quên. */
      { ma: "wh_dlq", ten: "Webhook vào DLQ", so: so(d.wh_dlq), don_vi: "sự kiện",
        lop: muc(so(d.wh_dlq), 0, 10) },
      { ma: "wh_cho_thu_lai", ten: "Webhook chờ thử lại", so: so(d.wh_cho_thu_lai),
        don_vi: "sự kiện", lop: muc(so(d.wh_cho_thu_lai), 20, 100) },
      { ma: "worker", ten: "Worker webhook", so: w.ok ? "sống" : "CHẾT", don_vi: "",
        lop: w.ok ? XANH : DO }
    ];
    for (var k in dem) {
      if (!Object.prototype.hasOwnProperty.call(dem, k)) continue;
      the.push({ ma: "dem." + k, ten: k, so: dem[k], don_vi: "lượt",
                 lop: /loi|5xx|that_bai|dlq/.test(k) && dem[k] > 0 ? VANG : XAM });
    }
    return {
      the: the,
      /* Phạm vi của số đếm là thứ BẮT BUỘC hiện lên. Số đếm ở đây chỉ của MỘT tiến trình và
         MẤT khi khởi động lại — đúng kiểu quên phạm vi đã thành rủi ro R-a của dự án. */
      pham_vi: d.pham_vi || null,
      ghi_chu_bang: d.ghi_chu_bang || null
    };
  }

  function so(v) { return typeof v === "number" ? v : null; }
  /* Chưa đo (`null`) là XÁM, không phải XANH. */
  function muc(v, nguongVang, nguongDo) {
    if (v === null) return XAM;
    if (v > nguongDo) return DO;
    if (v > nguongVang) return VANG;
    return XANH;
  }

  /* ===== 5. Một dòng tổng kết — CỐ Ý nói hai câu, không gộp ===== */
  function tomTat(sk, ss) {
    return {
      health: sk.chua_cam_route ? "chưa cắm route"
              : (sk.lop === XANH ? "sống" : "không phản hồi"),
      readiness: ss.chua_cam_route ? "chưa cắm route"
                 : (ss.lop === XANH ? "sẵn sàng"
                    : (ss.lop === VANG ? "sẵn sàng, có phép kiểm bị bỏ qua" : "CHƯA sẵn sàng")),
      /* Không có trường "tong_quan" một màu. Người đọc phải thấy hai câu, vì đó là hai câu
         hỏi khác nhau và câu trả lời có thể ngược nhau: tiến trình sống mà CSDL ở schema cũ
         thì health xanh, readiness đỏ. */
      canh_bao: ss.so_bo_qua
        ? ss.so_bo_qua + " phép kiểm BỊ BỎ QUA — chưa đo, không phải đã đạt"
        : null
    };
  }

  var api = {
    docSucKhoe: docSucKhoe, docSanSang: docSanSang, docMetric: docMetric, tomTat: tomTat,
    NHAN_KIEM: NHAN_KIEM, TRUONG_HIEN: TRUONG_HIEN,
    /* Đường API. ROUTE NÀY CHƯA ĐƯỢC CẮM — AG-00 giữ `app/server.py`. Xem bảng route trong
       docs/G11_FINAL_REPORT.md (bản vá đề xuất P-2). Tới lúc đó `nap()` sẽ nhận 404 và màn
       hiện "chưa cắm route", chứ không hiện "hệ hỏng" — hai chuyện khác nhau. */
    DUONG: {
      suc_khoe: "/api/v2/suc-khoe",
      san_sang: "/api/v2/san-sang",
      metric: "/api/v2/platform/quan-sat/metric"
    }
  };

  /* ===== 6. Lớp mỏng chạm mạng — chỉ có trong trình duyệt ===== */
  if (typeof window !== "undefined" && typeof fetch === "function") {
    api.nap = function (duong) {
      return fetch(duong, { headers: { "X-Requested-With": "VIPHub" }, credentials: "same-origin" })
        .then(function (r) {
          if (r.status === 404) return { __chua_cam_route: true, __ma: 404 };
          return r.json().then(function (j) { return j; },
                               function () { return { __loi: "trả về không phải JSON", __ma: r.status }; });
        })
        .catch(function (e) { return { __loi: String(e && e.message || e) }; });
    };
  }

  dat(api);
}(function (api) {
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof window !== "undefined") window.VIPHEALTH = api;
}));
