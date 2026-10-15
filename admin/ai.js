/* admin/ai.js — GIAO DIỆN TRỢ LÝ AI (G10). AG-04 sở hữu file này.
   Theo đúng khuôn `admin/logic.js` + `admin/admin.js`:
   - Phần LOGIC là thuần: vào là dữ liệu, ra là dữ liệu. KHÔNG chạm DOM, KHÔNG fetch,
     KHÔNG setTimeout. Nhờ vậy bộ thử chạy được bằng Node mà không cần trình duyệt.
   - Phần DỰNG MÀN chỉ trả về {lop, ten, dong, ...} để `admin.js` tự dựng thẻ — bộ thử kiểm
     QUYẾT ĐỊNH (nhãn nào, lớp nào, có cho bấm không), không phải so chuỗi HTML.
   - KHÔNG giữ secret nào. KHÔNG tự quyết định quyền — quyền do backend chốt.
   - Nạp được ở hai nơi: trình duyệt (window.VIPAI) và Node (module.exports).

   LUẬT RIÊNG CỦA MÀN AI, quan trọng nhất file này:
   **Mọi kết quả AI phải TỰ KHAI LÀ MÔ PHỎNG khi đang mock.** Người dùng không được phép
   tưởng đây là AI thật. Vì vậy `nhanKetQua` luôn trả về một dải nhãn, và khi `mock` THIẾU
   hoặc không đọc được thì nó coi như MOCK + gắn cờ `nghi_van` — chọn mặc định về phía AN
   TOÀN, vì nhãn sai theo hướng "tưởng là AI thật" là nhãn gây hại, còn nhãn sai theo hướng
   "tưởng là mô phỏng" chỉ làm người ta cẩn thận hơn.

   `admin/` KHÔNG có thư mục con — file này nằm phẳng cạnh `logic.js` và `admin.js`. */
(function (dat) {
  "use strict";

  /* ===== 1. Trạng thái công việc AI (SHARED_CONTRACTS §21) ===== */
  const TT_JOB = {
    moi:       ["hh-xam", "Mới", "đã tạo, chưa gọi trợ lý"],
    dang_chay: ["hh-xanh-duong", "Đang chạy", "đang chờ trợ lý trả lời"],
    cho_duyet: ["hh-vang", "Chờ người duyệt", "có kết quả, CHƯA được áp — cần người xem"],
    xong:      ["hh-xanh", "Xong", "đã có kết quả và đã được người xem"],
    loi:       ["hh-do", "Lỗi", "không có kết quả dùng được"],
    tu_choi:   ["hh-do", "Người từ chối", "người xem đã bỏ gợi ý này"],
  };

  /* ===== 2. Sáu loại việc AI ===== */
  const LOAI_VIEC = {
    trich_don_tu_file:    ["Trích dữ liệu đơn từ file", "tro-ly-import"],
    chuan_hoa_truong:     ["Chuẩn hoá trường", "goi-y"],
    goi_y_hang:           ["Gợi ý hãng vận chuyển", "goi-y"],
    phat_hien_bat_thuong: ["Phát hiện bất thường", "canh-bao"],
    giai_thich_loi_kiem:  ["Giải thích lỗi kiểm tra", "canh-bao"],
    tom_tat_lo_import:    ["Tóm tắt lô import", "tro-ly-import"],
  };

  /* ===== 3. Sự kiện dùng AI — nhãn cho màn lịch sử ===== */
  const SU_KIEN = {
    tao:               ["hh-xam", "Tạo việc"],
    goi_nha_cung_cap:  ["hh-xanh-duong", "Gọi trợ lý"],
    xong:              ["hh-xanh", "Xong"],
    cho_duyet:         ["hh-vang", "Chờ duyệt"],
    duyet:             ["hh-xanh", "Người duyệt"],
    tu_choi:           ["hh-do", "Người từ chối"],
    loi:               ["hh-do", "Lỗi"],
    timeout:           ["hh-do", "Hết hạn chờ — KHÔNG BIẾT kết quả"],
    chan_bi_mat:       ["hh-do", "CHẶN: prompt có thứ như bí mật"],
    chan_lenh:         ["hh-do", "CHẶN: kết quả chứa thứ như lệnh"],
  };

  function tra(bang, ma, moTaMacDinh) {
    const d = bang[String(ma)];
    if (d) return { ma: ma, lop: d[0], ten: d[1], mo_ta: d[2] || "", la: false };
    /* Trạng thái LẠ hiện NGUYÊN VĂN + cờ `la` — không nuốt im lặng, cùng nếp logic.js. */
    return { ma: ma, lop: "hh-xam", ten: String(ma == null ? "(trống)" : ma),
             mo_ta: moTaMacDinh || "giao diện chưa biết giá trị này", la: true };
  }

  const nhanJob = (ma) => tra(TT_JOB, ma, "trạng thái công việc AI chưa khai trong hợp đồng §21");
  const nhanSuKien = (ma) => tra(SU_KIEN, ma);

  function nhanLoai(ma) {
    const d = LOAI_VIEC[String(ma)];
    return d ? { ma: ma, ten: d[0], man: d[1], la: false }
             : { ma: ma, ten: String(ma), man: "trang-thai", la: true };
  }

  /* ===== 4. NHÃN MÔ PHỎNG — luật quan trọng nhất của màn này =====
     Trả một dải nhãn để `admin.js` dựng băng cảnh báo. `mock` không rõ ⇒ coi là MOCK. */
  function nhanKetQua(job) {
    job = job || {};
    const raw = job.mock;
    const chuaRo = raw === undefined || raw === null || raw === "";
    const laMock = chuaRo ? true : !(raw === false || raw === 0 || raw === "0" ||
                                     raw === "false");
    return {
      mock: laMock,
      nghi_van: chuaRo,
      lop: laMock ? "hh-vang" : "hh-xanh",
      nhan: laMock ? "MÔ PHỎNG — chưa nối AI thật" : "AI thật",
      chi_tiet: chuaRo
        ? "Backend không nói rõ kết quả này là mô phỏng hay thật. Giao diện mặc định coi là " +
          "MÔ PHỎNG cho an toàn — đừng dùng để quyết định việc thật."
        : (laMock
            ? "Kết quả do bộ mô phỏng nội bộ sinh ra (V-G10-01 chưa cấp quyền nối VIP AI " +
              "Brain). Dùng để thử luồng, KHÔNG dùng để quyết định việc thật."
            : "Kết quả do trợ lý AI thật sinh ra. Vẫn phải người xem trước khi áp."),
      /* Dù mock hay thật, câu này luôn hiện: kết quả AI là DỮ LIỆU, không phải LỆNH. */
      cau_an_toan: "Gợi ý của trợ lý KHÔNG tự áp vào đơn. Bạn phải tự xác nhận từng dòng.",
    };
  }

  /* ===== 5. Có cho bấm Duyệt / Từ chối không =====
     Hai điều kiện ĐỘC LẬP và cùng phải đúng: việc đang ở `cho_duyet`, và người dùng có
     quyền duyệt (quyền do backend trả về, giao diện KHÔNG tự suy). Che nút không phải là
     cưỡng chế — backend vẫn kiểm; che nút chỉ để người dùng không bấm vào chỗ sẽ bị từ chối. */
  function quyenBam(job, quyenCuaToi) {
    job = job || {};
    const ds = Array.isArray(quyenCuaToi) ? quyenCuaToi : [];
    const coQuyen = ds.indexOf("tenant.don.duyet") >= 0;
    const dungTrangThai = job.trang_thai === "cho_duyet";
    return {
      duyet: dungTrangThai && coQuyen,
      tu_choi: dungTrangThai && coQuyen,
      ly_do: !dungTrangThai
        ? "Chỉ duyệt được việc đang ở trạng thái Chờ người duyệt"
        : (coQuyen ? "" : "Bạn không có quyền tenant.don.duyet"),
    };
  }

  /* ===== 6. MÀN 1 — Trợ lý import AI ===== */
  function manTroLyImport(lo, job) {
    lo = lo || {};
    const dem = lo.dem_trang_thai || {};
    const tong = Object.keys(dem).reduce((s, k) => s + (dem[k] || 0), 0);
    const buoc = [
      { ma: "tai_file", ten: "Tải file", xong: !!lo.batch_id },
      { ma: "import_g05", ten: "Import engine kiểm dữ liệu", xong: tong > 0 },
      { ma: "chuan_hoa", ten: "Chuẩn hoá trường", xong: tong > 0 },
      { ma: "ai", ten: "Trợ lý AI đọc lô", xong: !!job && job.trang_thai !== "moi" },
      { ma: "kiem", ten: "Kiểm dữ liệu đơn", xong: !!job && !!job.ra_json },
      { ma: "nguoi_duyet", ten: "Người duyệt",
        xong: !!job && (job.trang_thai === "xong" || job.trang_thai === "tu_choi") },
      /* Bước cuối CỐ Ý ghi là chưa làm ở màn này: đơn nháp sinh ra ở màn duyệt lô import
         của G05, KHÔNG phải ở đây. Vẽ nó thành "xong" tại màn AI là nói sai việc. */
      { ma: "don_nhap", ten: "Đơn nháp (làm ở màn Duyệt lô import)", xong: false,
        ghi_chu: "Trợ lý AI không tạo đơn. Bạn sang màn Duyệt lô import để tạo bản nháp." },
    ];
    return {
      batch_id: lo.batch_id || null,
      ten_file: lo.ten_file || "",
      tong_dong: tong,
      dem: dem,
      buoc: buoc,
      ket_qua: nhanKetQua(job),
      cho_phep_goi_ai: tong > 0,
      ly_do_khong_goi: tong > 0 ? "" : "Lô chưa có dòng nào đọc được",
    };
  }

  /* ===== 7. MÀN 2 — Gợi ý AI (có ô so sánh gốc ↔ gợi ý) ===== */
  function manGoiY(deXuat) {
    deXuat = deXuat || {};
    const ds = Array.isArray(deXuat.de_xuat) ? deXuat.de_xuat : [];
    const dong = ds.map(function (x) {
      const t = x.truong || {};
      const tuAI = Array.isArray(x.truong_tu_ai) ? x.truong_tu_ai : [];
      const kiem = x.kiem || {};
      return {
        stt: x.stt,
        /* mỗi trường một dòng so sánh; `tu_ai` cho biết trường nào do trợ lý đổi */
        truong: Object.keys(t).sort().map(function (k) {
          return { ten: k, gia_tri: t[k], tu_ai: tuAI.indexOf(k) >= 0 };
        }),
        do_tin_cay: typeof x.do_tin_cay === "number" ? x.do_tin_cay : null,
        /* Độ tin cậy của bản mô phỏng là con số VÔ NGHĨA — nói thẳng ra, đừng để người
           dùng tưởng 35 % là một phép đo. */
        do_tin_cay_ghi_chu: deXuat.mock === false ? "" :
          "Số này do bộ mô phỏng gán, không phải phép đo thật",
        hop_le: kiem.hop_le === true,
        loi: Array.isArray(kiem.loi) ? kiem.loi : [],
        canh_bao: Array.isArray(kiem.canh_bao) ? kiem.canh_bao : [],
      };
    });
    return {
      ket_qua: nhanKetQua({ mock: deXuat.mock }),
      dong: dong,
      so_hop_le: dong.filter((d) => d.hop_le).length,
      so_sai: dong.filter((d) => !d.hop_le).length,
      thieu_nguoi_gui: deXuat.thieu_nguoi_gui === true,
      truong_da_gui: Array.isArray(deXuat.truong_da_gui) ? deXuat.truong_da_gui : [],
      truong_khong_gui: Array.isArray(deXuat.truong_khong_gui) ? deXuat.truong_khong_gui : [],
      canh_bao_tiem: (Array.isArray(deXuat.dau_hieu_tiem) ? deXuat.dau_hieu_tiem : []).length > 0
        ? "Dữ liệu trong lô có dòng chứa câu trông như chỉ thị cho máy. Hệ đã coi nó là văn " +
          "bản thường, nhưng bạn nên xem kỹ các dòng này."
        : "",
      ghi_chu_an_toan: deXuat.ghi_chu_an_toan || "",
    };
  }

  /* ===== 8. MÀN 3 — Cảnh báo kiểm tra =====
     CẢNH BÁO ≠ LỖI, và cảnh báo của AI ≠ cảnh báo của hệ. Ba thứ tách ba khối: trộn vào
     nhau thì người dùng bỏ qua cả ba (cùng lý do đã viết trong `don_hang.kiem_don`). */
  function manCanhBao(kiemHeThong, jobBatThuong) {
    kiemHeThong = kiemHeThong || {};
    const raAI = jobBatThuong && jobBatThuong.ra ? jobBatThuong.ra : {};
    const tuAI = Array.isArray(raAI.canh_bao) ? raAI.canh_bao : [];
    return {
      loi_he_thong: {
        tieu_de: "Lỗi chặn — phải sửa mới lưu được",
        lop: "hh-do",
        nguon: "hệ thống kiểm (don_hang.kiem_don)",
        muc: Array.isArray(kiemHeThong.loi) ? kiemHeThong.loi : [],
      },
      canh_bao_he_thong: {
        tieu_de: "Cảnh báo của hệ — không chặn lưu",
        lop: "hh-vang",
        nguon: "hệ thống kiểm (don_hang.kiem_don)",
        muc: Array.isArray(kiemHeThong.canh_bao) ? kiemHeThong.canh_bao : [],
      },
      canh_bao_ai: {
        tieu_de: "Trợ lý AI lưu ý",
        lop: "hh-xam",
        nguon: "trợ lý AI — chỉ gợi ý, không phải phép kiểm",
        ket_qua: nhanKetQua(jobBatThuong || {}),
        muc: tuAI,
      },
      /* Thứ hạng để `admin.js` biết khối nào đặt trên: lỗi chặn luôn trên cùng. */
      thu_tu: ["loi_he_thong", "canh_bao_he_thong", "canh_bao_ai"],
    };
  }

  /* ===== 9. MÀN 4 — Trạng thái công việc AI ===== */
  const BO_LOC_JOB = ["tat_ca"].concat(Object.keys(TT_JOB));

  function manTrangThai(dsJob, loc) {
    const ds = Array.isArray(dsJob) ? dsJob : [];
    const l = loc && loc !== "tat_ca" ? String(loc) : null;
    const hien = l ? ds.filter((j) => j.trang_thai === l) : ds;
    return {
      bo_loc: BO_LOC_JOB,
      dang_loc: l || "tat_ca",
      dem: Object.keys(TT_JOB).reduce(function (acc, k) {
        acc[k] = ds.filter((j) => j.trang_thai === k).length;
        return acc;
      }, {}),
      dong: hien.map(function (j) {
        return {
          id: j.id,
          loai: nhanLoai(j.loai),
          trang_thai: nhanJob(j.trang_thai),
          ket_qua: nhanKetQua(j),
          nha_cung_cap: j.nha_cung_cap || "(không rõ)",
          ms_chay: typeof j.ms_chay === "number" ? j.ms_chay : null,
          tao_luc: j.tao_luc || "",
          /* Lý do lỗi hiện NGUYÊN VĂN. Rút gọn "có lỗi" là xoá đúng thứ người ta cần. */
          loi: j.loi || "",
          can_nguoi_duyet: j.can_nguoi_duyet === 1 || j.can_nguoi_duyet === true,
        };
      }),
    };
  }

  /* ===== 10. MÀN 5 — Lịch sử phê duyệt ===== */
  function manLichSuDuyet(dsSuKien, dsJob) {
    const sk = Array.isArray(dsSuKien) ? dsSuKien : [];
    const theoJob = {};
    (Array.isArray(dsJob) ? dsJob : []).forEach(function (j) { theoJob[j.id] = j; });
    const chiDuyet = sk.filter((x) => x.loai_su_kien === "duyet" ||
                                      x.loai_su_kien === "tu_choi");
    return {
      tong_su_kien: sk.length,
      dong: chiDuyet.map(function (x) {
        const j = theoJob[x.job_id] || {};
        return {
          job_id: x.job_id,
          loai: nhanLoai(j.loai),
          su_kien: nhanSuKien(x.loai_su_kien),
          nguoi: x.user_id == null ? "(hệ thống)" : "user:" + x.user_id,
          luc: x.luc || "",
          chi_tiet: x.chi_tiet || "",
        };
      }),
      /* Dòng CHẶN cũng phải thấy được ở đây — đó là lúc hệ từ chối thay người, và ẩn nó đi
         là ẩn đúng thứ cần soát. */
      dong_chan: sk.filter((x) => x.loai_su_kien === "chan_bi_mat" ||
                                  x.loai_su_kien === "chan_lenh" ||
                                  x.loai_su_kien === "timeout")
        .map(function (x) {
          return { job_id: x.job_id, su_kien: nhanSuKien(x.loai_su_kien),
                   luc: x.luc || "", chi_tiet: x.chi_tiet || "" };
        }),
    };
  }

  /* ===== 11. MÀN 6 — Thống kê mức dùng AI ===== */
  function manThongKe(tk) {
    tk = tk || {};
    const dung = Number(tk.so_ai_da_dung || 0);
    const tran = tk.han_muc_ai_thang == null ? null : Number(tk.han_muc_ai_thang);
    /* Phần trăm tính bằng SỐ NGUYÊN (điểm phần trăm) — §16 cấm float cho con số đối chiếu,
       và một thanh tiến độ không cần phần thập phân. */
    const pt = tran && tran > 0 ? Math.min(100, Math.floor((dung * 100) / tran)) : null;
    return {
      thang: tk.thang || "",
      goi: tk.goi || "(không rõ)",
      da_dung: dung,
      tran: tran,
      phan_tram: pt,
      lop: pt == null ? "hh-xam" : (pt >= 90 ? "hh-do" : (pt >= 70 ? "hh-vang" : "hh-xanh")),
      con_lai: tran == null ? null : Math.max(0, tran - dung),
      job_theo_trang_thai: tk.job_theo_trang_thai || {},
      job_theo_loai: tk.job_theo_loai || {},
      ket_qua: nhanKetQua(tk),
      /* Chi phí: backend trả `null` kèm lý do. Giao diện hiện ĐÚNG lý do đó, KHÔNG hiện
         "0 đ" — "0 đ" là một con số, và một con số bịa thì tệ hơn một ô trống. */
      chi_phi: tk.chi_phi_dong == null
        ? { co_so_lieu: false, hien: "chưa đo được",
            ghi_chu: tk.chi_phi_ghi_chu || "chưa có đơn giá nhà cung cấp" }
        : { co_so_lieu: true, hien: String(tk.chi_phi_dong) + " đ", ghi_chu: "" },
      /* Hai số cố ý KHÔNG gộp (backend đã tách) — nếu lệch thì hiện cả hai và nói là lệch. */
      doi_chieu_luot: {
        tu_han_muc: dung,
        tu_su_kien: tk.luot_tinh_phi_tu_su_kien == null
          ? null : Number(tk.luot_tinh_phi_tu_su_kien),
        lech: tk.luot_tinh_phi_tu_su_kien == null
          ? null : Number(tk.luot_tinh_phi_tu_su_kien) !== dung,
        ghi_chu: "Hai bộ đếm đo hai thứ khác nhau: bộ đếm hạn mức là cái quyết định chặn; " +
                 "bộ đếm sự kiện là dấu vết từng lượt gọi. Lệch nhau là bình thường khi có " +
                 "lượt bị chặn trước khi gọi.",
      },
    };
  }

  /* ===== 12. Bảng API mà màn này cần — AG-00 cắm route theo đúng bảng này ===== */
  const API_CHO_BACKEND = [
    ["POST", "/api/v2/ai/job", "tạo công việc AI (body: loai, vao, idem_key?, batch_id?)"],
    ["POST", "/api/v2/ai/job/<id>/chay", "chạy công việc"],
    ["GET", "/api/v2/ai/job", "danh sách công việc (query: trang_thai?, loai?)"],
    ["GET", "/api/v2/ai/job/<id>", "một công việc + đề xuất cho người duyệt"],
    ["POST", "/api/v2/ai/job/<id>/duyet", "người duyệt đồng ý"],
    ["POST", "/api/v2/ai/job/<id>/tu-choi", "người từ chối (body: ly_do)"],
    ["GET", "/api/v2/ai/su-kien", "lịch sử sự kiện dùng AI"],
    ["GET", "/api/v2/ai/thong-ke", "thống kê mức dùng AI"],
    ["GET", "/api/v2/ai/lo/<batch_id>", "dựng đầu vào AI từ một lô import"],
  ];
  /* Ba đường AI đã có sẵn từ trước (AG-00 đã cắm) — màn này KHÔNG gọi lại chúng, vì tầng
     job đã bọc chúng và còn thêm kiểm schema + audit. Ghi ra để không ai nối hai đường. */
  const API_DA_CO_KHONG_DUNG_O_DAY = [
    "POST /api/v2/ai/chuan-hoa-dia-chi",
    "POST /api/v2/ai/phat-hien-bat-thuong",
    "POST /api/v2/ai/goi-y-hang",
  ];

  dat({
    TT_JOB: TT_JOB, LOAI_VIEC: LOAI_VIEC, SU_KIEN: SU_KIEN, BO_LOC_JOB: BO_LOC_JOB,
    nhanJob: nhanJob, nhanLoai: nhanLoai, nhanSuKien: nhanSuKien,
    nhanKetQua: nhanKetQua, quyenBam: quyenBam,
    manTroLyImport: manTroLyImport, manGoiY: manGoiY, manCanhBao: manCanhBao,
    manTrangThai: manTrangThai, manLichSuDuyet: manLichSuDuyet, manThongKe: manThongKe,
    API_CHO_BACKEND: API_CHO_BACKEND,
    API_DA_CO_KHONG_DUNG_O_DAY: API_DA_CO_KHONG_DUNG_O_DAY,
  });
})(function (api) {
  if (typeof module !== "undefined" && module.exports) module.exports = api;   // Node — bộ thử
  if (typeof window !== "undefined") window.VIPAI = api;                        // trình duyệt
});
