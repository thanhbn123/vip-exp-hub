/* BỘ THỬ FRONTEND — TẦNG 1: LOGIC THUẦN (Node, KHÔNG trình duyệt).
   Chạy: node --test thu_frontend/thu_logic.mjs
   (hoặc sh thu_frontend/chay.sh để chạy cả ba tầng)

   PHẠM VI CỦA TẦNG NÀY — đọc kỹ trước khi tin kết quả (§12.1 luật 3):
   - Phủ: quyết định nhãn trạng thái, chế độ dữ liệu MOCK/LOCAL/LIVE, bộ lọc đơn,
     dựng dòng thời gian, kiểm dữ liệu form, chọn tài khoản hãng, metadata phiếu in,
     gom nhóm webhook, bảng API chờ backend.
   - KHÔNG phủ: DOM, CSS, bố cục, sự kiện chuột, fetch thật, quyền thật.
     Những thứ đó ở tầng 2 (HTTP, Python) và tầng 3 (trình duyệt thật) — xem
     docs/FRONTEND_AUTOMATION.md.
   - Mỗi ca ở đây là LOGIC, không có ca nào chạy trình duyệt. */
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const GOC = join(dirname(fileURLToPath(import.meta.url)), "..");
const require = createRequire(import.meta.url);
const L = require(join(GOC, "admin", "logic.js"));

/* ====================== 1. Nhãn trạng thái ====================== */

test("01 nhanTT — năm trạng thái nghiệp vụ của hợp đồng §10 đều có tên tiếng Việt", () => {
  for (const ma of ["nhap", "da_duyet", "dang_gui", "da_gui", "huy"]) {
    const d = L.nhanTT(ma);
    assert.equal(d.la, false, `${ma} phải được giao diện biết`);
    assert.ok(d.ten && d.ten !== ma, `${ma} phải có tên tiếng Việt`);
    assert.ok(d.lop.startsWith("hh-"));
  }
});

test("02 nhanTT — trạng thái LẠ hiện NGUYÊN VĂN và gắn cờ la (không nuốt im lặng)", () => {
  const d = L.nhanTT("PENDING_APPROVAL");
  assert.equal(d.la, true);
  assert.equal(d.ten, "PENDING_APPROVAL", "phải hiện nguyên văn, không đổi thành 'Khác'");
});

test("03 nhanTT — null/rỗng không bị coi là trạng thái lạ", () => {
  assert.equal(L.nhanTT(null).la, false);
  assert.equal(L.nhanTT("").la, false);
});

test("04 nhanGiao — sáu trạng thái giao vận §10 đủ tên + đúng rank chặn sự kiện muộn", () => {
  const rank = { cho_lay: 1, lay_hang: 2, dang_giao: 3, giao_that_bai: 4, giao_thanh_cong: 5, hoan_hang: 6 };
  for (const [ma, r] of Object.entries(rank)) {
    const d = L.nhanGiao(ma);
    assert.equal(d.la, false, ma);
    assert.equal(d.rank, r, `rank của ${ma}`);
  }
  const la = L.nhanGiao("IN_TRANSIT");
  assert.equal(la.la, true);
  assert.equal(la.rank, null, "trạng thái lạ KHÔNG được bịa rank");
  assert.equal(la.ten, "IN_TRANSIT");
});

test("05 nhanBatch — đỡ cả bộ cũ (moi/xong) và bộ mới §6", () => {
  assert.equal(L.nhanBatch("moi").la, false);
  assert.equal(L.nhanBatch("PARTIAL_FAILED").la, false);
  for (const ma of ["UPLOADED", "PARSING", "VALIDATING", "READY", "APPROVED",
                    "PROCESSING", "COMPLETED", "PARTIAL_FAILED", "FAILED"]) {
    assert.equal(L.nhanBatch(ma).la, false, `trạng thái batch bắt buộc §6: ${ma}`);
  }
  assert.equal(L.nhanBatch("QUARANTINED").ten, "QUARANTINED");
});

test("06 nhanDong — chín trạng thái dòng §6, kèm NEEDS_REVIEW và UNSUPPORTED", () => {
  for (const ma of ["VALID", "INVALID", "READY", "SUBMITTED", "SUCCESS",
                    "FAILED", "UNSUPPORTED", "NEEDS_REVIEW"]) {
    assert.equal(L.nhanDong(ma).la, false, ma);
  }
  assert.equal(L.nhanDong("NEEDS_REVIEW").lop, "hh-vang");
});

test("07 lopDongBang — tô dòng theo nhóm, NEEDS_REVIEW có lớp riêng", () => {
  assert.equal(L.lopDongBang("INVALID"), "dong-loi");
  assert.equal(L.lopDongBang("UNSUPPORTED"), "dong-loi");
  assert.equal(L.lopDongBang("NEEDS_REVIEW"), "dong-can-xem");
  assert.equal(L.lopDongBang("SUCCESS"), "dong-hop-le");
  assert.equal(L.lopDongBang("SUBMITTED"), "");
});

/* ====================== 2. Webhook: trạng thái nhập nhằng ====================== */

test("08 nhanWebhook — sáu trạng thái §12 đều biết", () => {
  for (const ma of ["moi", "dang_xu_ly", "xong", "cho_thu_lai", "dlq", "khong_khop"]) {
    const d = L.nhanWebhook(ma);
    assert.equal(d.la, false, ma);
    assert.equal(d.nhap_nhang, false, ma);
  }
});

test("09 nhanWebhook — NEEDS_REVIEW / AMBIGUOUS (AG-03, mã J&T 110) hiện NGUYÊN VĂN và được đánh dấu nhập nhằng", () => {
  for (const ma of ["NEEDS_REVIEW", "AMBIGUOUS", "needs_review", "ambiguous"]) {
    const d = L.nhanWebhook(ma);
    assert.equal(d.nhap_nhang, true, `${ma} phải được đánh dấu nhập nhằng`);
    assert.equal(d.ten, ma, `${ma} phải hiện nguyên văn — cấm đổi tên hay gộp vào 'lỗi'`);
    assert.equal(d.lop, "hh-vang");
  }
});

test("10 nhanWebhook — trạng thái lạ KHÁC cũng không bị nuốt", () => {
  const d = L.nhanWebhook("PARKED");
  assert.equal(d.la, true);
  assert.equal(d.nhap_nhang, false);
  assert.equal(d.ten, "PARKED");
});

/* ====================== 3. Chế độ dữ liệu MOCK / LOCAL / LIVE ====================== */

const HANG_MOCK = { ma: "jt", ten: "J&T Express", live_mo: false, capabilities: { createOrder: true } };
const HANG_LIVE = { ma: "vtp", ten: "Viettel Post", live_mo: true, capabilities: { createOrder: true } };

test("11 cheDoDon — đơn chưa gán tài khoản hãng là LOCAL REAL DATA", () => {
  const cd = L.cheDoDon({ ma_don: "D1" }, null, null);
  assert.equal(cd.ma, "LOCAL");
  assert.equal(cd.nhan, "LOCAL REAL DATA");
});

test("12 cheDoDon — đã qua tài khoản môi trường mock là MOCK DATA", () => {
  const cd = L.cheDoDon({ carrier_account_id: 7 }, { id: 7, hang: "jt", moi_truong: "mock" }, HANG_MOCK);
  assert.equal(cd.ma, "MOCK");
  assert.equal(cd.nhan, "MOCK DATA");
});

test("13 KHÓA AN TOÀN — môi trường 'production' mà hãng chưa mở live_mo thì VẪN LÀ MOCK, không được dán LIVE", () => {
  const cd = L.cheDoDon({ carrier_account_id: 7 },
    { id: 7, hang: "jt", moi_truong: "production" }, HANG_MOCK);
  assert.equal(cd.ma, "MOCK", "live_mo=false là khóa an toàn — một mình môi trường không mở được LIVE");
});

test("14 KHÓA AN TOÀN — hãng mở live_mo nhưng tài khoản vẫn môi trường mock thì KHÔNG phải LIVE", () => {
  const cd = L.cheDoDon({ carrier_account_id: 9 },
    { id: 9, hang: "vtp", moi_truong: "mock" }, HANG_LIVE);
  assert.equal(cd.ma, "MOCK", "phải đúng CẢ HAI điều kiện mới là LIVE");
});

test("15 cheDoDon — LIVE chỉ khi môi trường thật VÀ hãng mở live_mo", () => {
  const cd = L.cheDoDon({ carrier_account_id: 9 },
    { id: 9, hang: "vtp", moi_truong: "production" }, HANG_LIVE);
  assert.equal(cd.ma, "LIVE");
  assert.equal(cd.nhan, "LIVE CARRIER DATA");
});

test("16 cheDoDon — thiếu thông tin hãng/tài khoản thì lùi về MOCK, KHÔNG BAO GIỜ lùi về LIVE", () => {
  assert.equal(L.cheDoDon({ carrier_account_id: 3 }, null, null).ma, "MOCK");
  assert.equal(L.cheDoDon({ carrier_account_id: 3 }, { id: 3, moi_truong: "production" }, null).ma, "MOCK");
});

test("17 cheDoHeThong — không hãng nào mở live thì cả màn là MOCK", () => {
  assert.equal(L.cheDoHeThong([HANG_MOCK, { ma: "ghn", live_mo: false }]).ma, "MOCK");
  assert.equal(L.cheDoHeThong([]).ma, "MOCK");
  assert.equal(L.cheDoHeThong([HANG_MOCK, HANG_LIVE]).ma, "LIVE");
});

/* ====================== 4. Bộ lọc nâng cao ====================== */

const TK = { 7: { id: 7, hang: "jt", ten: "JT mock", moi_truong: "mock", kich_hoat: 1 },
             9: { id: 9, hang: "vtp", ten: "VTP mock", moi_truong: "mock", kich_hoat: 1 } };
const DON = [
  { id: 1, ma_don: "D-001", ma_van_don: "JT123", nguoi_nhan_ten: "An", nguoi_nhan_sdt: "0901",
    trang_thai: "da_gui", trang_thai_giao: "dang_giao", carrier_account_id: 7, cod: 100000,
    tao_luc: "2026-10-01 08:00:00", can_doi_soat_ket_qua: 0 },
  { id: 2, ma_don: "D-002", ma_van_don: null, nguoi_nhan_ten: "Bình", nguoi_nhan_sdt: "0902",
    trang_thai: "nhap", trang_thai_giao: null, carrier_account_id: null, cod: 0,
    tao_luc: "2026-10-05 09:00:00", can_doi_soat_ket_qua: 0 },
  { id: 3, ma_don: "D-003", ma_van_don: "VTP777", nguoi_nhan_ten: "Cường", nguoi_nhan_sdt: "0903",
    trang_thai: "dang_gui", trang_thai_giao: "cho_lay", carrier_account_id: 9, cod: 500000,
    tao_luc: "2026-10-10 10:00:00", can_doi_soat_ket_qua: 1 },
];

/* --- Chín ca dưới đây (18–26) VIẾT LẠI theo hợp đồng đã chốt (G22), KHÔNG phải sửa cho xanh.
   Bản cũ của chúng ghim HÀNH VI CŨ — "chỉ q/trang_thai/gioi_han đi lên máy chủ, phần còn lại
   lọc tại giao diện" — tức là ghim đúng khoản nợ mà G22 đóng (`app/server.py` thời ấy BỎ QUA
   IM LẶNG mọi tham số khác). Nay nguồn sự thật là `app/truy_van.py::BANG_DON` + §1 của
   `docs/G22_TRUYVAN.md`, và bốn bất biến của khối này:
     1. Mười ba tham số đi LÊN MÁY CHỦ, chép ĐÚNG tên máy chủ nhận; chỉ `co_van_don` ở lại trang.
     2. Một điều kiện chỉ được lọc ở MỘT chỗ — `locDon` nhận điều kiện của máy chủ thì NÉM.
     3. Tên lạ KHÔNG bị nuốt: vào túi `la` và màn hình phải nói ra; riêng `tenant_id` thì
        tuyệt đối không gửi (máy chủ lấy tenant từ PHIÊN, `tenant_id` trong query là 400).
     4. Dòng "phạm vi" đọc từ CHÍNH phản hồi máy chủ; thiếu số thì nói CHƯA ĐO ĐƯỢC, không suy ra.
   Mỗi ca ghi rõ nó từng ghim gì (CŨ) và bất biến đúng là gì (MỚI). */

test("18 chiaDieuKien — mười ba tham số của máy chủ đi LÊN MÁY CHỦ, chỉ `co_van_don` ở lại trang", () => {
  // CŨ: ca này chốt nguyên văn "chỉ q/trang_thai/gioi_han đi lên máy chủ" — đúng với máy chủ
  // chỉ biết ba tham số, và chính là ghim của khoản nợ G22.
  // MỚI: túi `may_chu` phải bằng ĐÚNG danh sách máy chủ nhận (14 trường lọc §1.1 mà giao diện
  // dùng, cộng ba tham số điều khiển `sap_xep`/`gioi_han`/`trang`), và `co_van_don` là điều kiện
  // DUY NHẤT lọc tại trang.
  const c = L.chiaDieuKien({ q: "abc", trang_thai: "nhap", trang_thai_giao: "cho_lay", hang: "jt",
                             carrier_account_id: "9", cod_tu: "1000", cod_den: "2000",
                             tu_ngay: "2026-10-01", den_ngay: "2026-10-31", can_doi_soat: "1",
                             gioi_han: "100", trang: "2", sap_xep: "cod_cao", co_van_don: "co" });
  assert.deepEqual(Object.keys(c.may_chu).sort(),
    ["can_doi_soat", "carrier_account_id", "cod_den", "cod_tu", "den_ngay", "gioi_han",
     "hang", "q", "sap_xep", "trang", "trang_thai", "trang_thai_giao", "tu_ngay"]);
  assert.deepEqual(Object.keys(c.giao_dien), ["co_van_don"],
    "chỉ `co_van_don` lọc tại trang — điều kiện đã gửi lên máy chủ thì KHÔNG lọc lại");
  assert.deepEqual(c.la, []);
});

test("19 chiaDieuKien — bỏ điều kiện rỗng/false, NHƯNG `0` là điều kiện THẬT; tên lạ phải NÓI RA", () => {
  // CŨ: ca này chốt luật bỏ-rỗng và coi `cod_tu='0'` là điều kiện lọc TẠI TRANG.
  // MỚI: luật bỏ-rỗng áp cho cả ba túi, và nó KHÔNG được nuốt hai giá trị `0` có nghĩa:
  // `cod_tu='0'` (đầu khoảng COD) và `can_doi_soat='0'` — theo §1.1, `can_doi_soat=0` nghĩa là
  // "chỉ đơn KHÔNG cần đối soát", tức bỏ nó đi là lọc SAI CHIỀU chứ không phải "bỏ điều kiện rỗng".
  const c = L.chiaDieuKien({ q: "", trang_thai: null, hang: "", can_doi_soat: false, cod_tu: "0" });
  assert.deepEqual(c.may_chu, { cod_tu: "0" }, "cod_tu='0' là điều kiện THẬT, không phải rỗng");
  assert.deepEqual(c.giao_dien, {});
  assert.deepEqual(c.la, [], "rỗng/false/null không phải 'tên lạ'");
  const c0 = L.chiaDieuKien({ can_doi_soat: "0" });
  assert.deepEqual(c0.may_chu, { can_doi_soat: "0" },
    'can_doi_soat="0" là điều kiện THẬT (chỉ đơn KHÔNG cần đối soát) — false mới là "không lọc"');
  const c2 = L.chiaDieuKien({ q: "a", ten_khong_co_that: "x" });
  assert.deepEqual(c2.la, ["ten_khong_co_that"], "tên lạ KHÔNG được nuốt im lặng");
  assert.deepEqual(Object.keys(c2.may_chu), ["q"], "tên lạ không được lọt vào túi gửi máy chủ");
});

test("20 locDon — điều kiện TẠI TRANG `co_van_don` lọc đúng cả hai chiều", () => {
  // CŨ: ca này chốt `locDon` tự tìm chữ (`q`) trên tập ĐÃ TẢI — phép tìm ấy nay ở máy chủ, và
  // ở đó nó tìm 5 cột (thêm `hang_hoa`), tức bản cũ còn ghim một phạm vi HẸP HƠN hợp đồng.
  // MỚI: `locDon` chỉ còn đúng một điều kiện, và cả hai chiều của nó đều phải đúng.
  assert.deepEqual(L.locDon(DON, { co_van_don: "co" }, TK).map(d => d.id), [1, 3]);
  assert.deepEqual(L.locDon(DON, { co_van_don: "khong" }, TK).map(d => d.id), [2]);
  assert.equal(L.locDon(DON, {}, TK).length, 3, "không điều kiện thì trả nguyên danh sách");
  assert.equal(L.locDon(null, {}, TK).length, 0);
});

test("21 locDon — NÉM khi nhận điều kiện CỦA MÁY CHỦ (không lọc hai chỗ)", () => {
  // CŨ: ca này chốt `locDon` tự lọc `trang_thai_giao` tại trang (trục giao vận riêng).
  // MỚI: điều kiện ấy nay đi lên máy chủ. Lọc lại tại trang là LỌC HAI CHỖ — đúng một cách
  // TÌNH CỜ, và sai ngay khi máy chủ đổi cách hiểu. Nên MỌI tên trong `THAM_SO_MAY_CHU` phải
  // làm `locDon` NÉM, và câu lỗi phải NÊU TÊN điều kiện vừa nhận.
  for (const ten of L.THAM_SO_MAY_CHU) {
    assert.throws(() => L.locDon(DON, { [ten]: "x" }, TK),
      new RegExp("điều kiện của máy chủ: " + ten),
      `lọc lại \`${ten}\` tại trang là LỌC HAI CHỖ — phải ném, không lặng lẽ lọc`);
  }
  assert.throws(() => L.locDon(DON, { q: "a", co_van_don: "co" }, TK), /q/,
    "trộn điều kiện máy chủ với điều kiện tại trang cũng phải ném");
});

test("22 phamViLoc — dựng dòng phạm vi từ CHÍNH phản hồi của máy chủ, kể cả giá trị ĐÃ KẸP", () => {
  // CŨ: ca này chốt `locDon` tự lọc theo hãng, đi qua bảng tài khoản hãng, TẠI TRANG.
  // MỚI: dòng phạm vi là DỮ LIỆU đọc từ phản hồi máy chủ, và hai con số phân trang phải là con
  // số máy chủ THẬT SỰ dùng: `gioi_han=99999` bị kẹp còn 500 thì dòng phạm vi nói 500 —
  // nói lại con số giao diện XIN là nói sai (§1.3: kẹp, và giá trị thật được TRẢ RA).
  const pv = L.phamViLoc({ dong: [{ id: 1 }, { id: 2 }], tong: 7, tong_chinh_xac: true,
                           trang: 2, gioi_han: 2, con_nua: true, sap_xep: "cod_cao",
                           loc_bo_qua: [] }, { co_van_don: "co" }, 1);
  assert.equal(pv.tong, 7);
  assert.equal(pv.tong_chinh_xac, true);
  assert.equal(pv.trang, 2);
  assert.equal(pv.gioi_han, 2);
  assert.equal(pv.con_nua, true);
  assert.equal(pv.so_dong_trang, 1);
  assert.deepEqual(pv.loc_tai_trang, ["co_van_don"]);
  assert.equal(pv.sap_xep, "cod_cao");
  assert.deepEqual(pv.loc_may_chu, L.THAM_SO_MAY_CHU.slice(),
    "dòng phạm vi phải nói ra ĐÚNG danh sách điều kiện đã gửi lên máy chủ");
  const kep = L.phamViLoc({ dong: [], tong: 0, tong_chinh_xac: true, trang: 1, gioi_han: 500,
                            con_nua: false, sap_xep: "moi_nhat" }, {}, 0);
  assert.equal(kep.gioi_han, 500, "máy chủ kẹp `gioi_han` thì dòng phạm vi nói giá trị ĐÃ KẸP");
  assert.equal(kep.sap_xep, "moi_nhat", "sắp xếp mặc định của máy chủ phải hiện ra được");
  assert.deepEqual(kep.loc_tai_trang, []);
});

test("23 phamViLoc — máy chủ KHÔNG trả `tong` thì nói CHƯA ĐO ĐƯỢC, không suy ra 0", () => {
  // CŨ: ca này chốt khoảng ngày lọc tại trang theo 10 ký tự đầu của `tao_luc`.
  // MỚI: hình dạng phản hồi là hợp đồng — thiếu `tong`/`trang`/`gioi_han` thì dòng phạm vi phải
  // nói CHƯA ĐO ĐƯỢC (null), tuyệt đối không hiện 0 như một con số chính xác: "0 đơn" và
  // "chưa đo được" là hai câu khác hẳn nhau với người đang tìm đơn.
  const pv = L.phamViLoc({ don: [{ id: 1 }] }, {}, 1);
  assert.equal(pv.tong, null, "thiếu `tong` ⇒ null (chưa đo được), KHÔNG phải 0");
  assert.equal(pv.tong_chinh_xac, null);
  assert.equal(pv.trang, null);
  assert.equal(pv.gioi_han, null);
  assert.equal(pv.so_dong_trang, 1);
  assert.equal(pv.con_nua, false, "thiếu `con_nua` thì KHÔNG được hứa là còn trang sau");
});

test("24 phamViLoc — chạm trần đếm thì nói TỐI THIỂU, và chuyển tiếp điều kiện máy chủ BỎ", () => {
  // CŨ: ca này chốt `locDon` tự lọc khoảng ngày tại trang.
  // MỚI: hai lời nói thật BẮT BUỘC của dòng phạm vi — (a) `tong_chinh_xac=false` nghĩa là `tong`
  // chỉ là TỐI THIỂU (đã chạm trần đếm), không được đọc như số chính xác; (b) điều kiện máy chủ
  // BỎ (cột chưa migrate) phải được chuyển tiếp lên màn, không nằm im trong log.
  const pv = L.phamViLoc({ dong: [], tong: 10000, tong_chinh_xac: false, trang: 1,
                           gioi_han: 100, con_nua: true,
                           loc_bo_qua: ["external_reference (CSDL chưa có cột)"] }, {}, 0);
  assert.equal(pv.tong_chinh_xac, false);
  assert.equal(pv.tong, 10000);
  assert.deepEqual(pv.loc_bo_qua, ["external_reference (CSDL chưa có cột)"],
    "máy chủ BỎ điều kiện thì phải chuyển tiếp lên màn hình");
  assert.equal(pv.so_dong_trang, 0);
});

test("25 THAM_SO_MAY_CHU — tên máy chủ nhận, hai danh sách RỜI NHAU, và KHÔNG bao giờ gửi `tenant_id`", () => {
  // CŨ: ca này chốt `can_doi_soat` lọc TẠI TRANG và giao diện gọi tên riêng `tai_khoan_id`.
  // MỚI, bốn bất biến:
  //  (a) hai danh sách RỜI NHAU — một điều kiện chỉ được lọc ở MỘT chỗ;
  //  (b) gửi ĐÚNG tên máy chủ (`carrier_account_id`), không gửi tên riêng của giao diện;
  //  (c) `co_van_don` không có trên máy chủ nên nó ở lại trang — và là điều kiện DUY NHẤT;
  //  (d) KHÔNG BAO GIỜ gửi `tenant_id`: máy chủ lấy tenant từ PHIÊN và coi `tenant_id` trong
  //      query là tham số lạ ⇒ 400 (§1.4). Gửi nó là tự làm hỏng MỌI lượt lọc.
  //      Cùng luật với `lech`: giao diện đánh số bằng `trang`, gửi cả `trang` lẫn `lech` ⇒ 400.
  for (const ten of L.THAM_SO_MAY_CHU) {
    assert.ok(L.THAM_SO_LOC_TAI_GIAO_DIEN.indexOf(ten) < 0,
      `${ten} vừa gửi lên máy chủ vừa lọc tại trang`);
  }
  assert.deepEqual(L.THAM_SO_LOC_TAI_GIAO_DIEN, ["co_van_don"],
    "`co_van_don` là điều kiện DUY NHẤT lọc tại trang");
  assert.ok(L.THAM_SO_MAY_CHU.indexOf("carrier_account_id") >= 0,
    "máy chủ nhận `carrier_account_id`; giao diện không được gửi tên riêng `tai_khoan_id`");
  assert.ok(L.THAM_SO_MAY_CHU.indexOf("tai_khoan_id") < 0);
  assert.ok(L.THAM_SO_MAY_CHU.indexOf("co_van_don") < 0,
    "`co_van_don` không có trong hợp đồng của máy chủ");
  assert.ok(L.THAM_SO_MAY_CHU.indexOf("trang") >= 0 && L.THAM_SO_MAY_CHU.indexOf("lech") < 0,
    "giao diện đánh số bằng `trang`; gửi thêm `lech` là 400");
  assert.ok(L.THAM_SO_MAY_CHU.indexOf("tenant_id") < 0,
    "`tenant_id` KHÔNG bao giờ đi từ giao diện: máy chủ lấy tenant từ phiên, gửi lên là 400");
  const c = L.chiaDieuKien({ tenant_id: "2", q: "x" });
  assert.deepEqual(c.la, ["tenant_id"],
    "`tenant_id` là tên lạ — phải bị NÓI RA ở dòng phạm vi, và KHÔNG được gửi đi");
  assert.deepEqual(Object.keys(c.may_chu), ["q"]);
});

test("26 SAP_XEP_DON — khoá sắp xếp chép đúng danh sách trắng của máy chủ", () => {
  // CŨ: ca này chốt nhiều điều kiện lọc tại trang là AND (nay ở ca 20) và `locDon` trả nguyên
  // danh sách khi không có điều kiện.
  // MỚI: `sap_xep` là DANH SÁCH TRẮNG — máy chủ TỪ CHỐI (400) khoá lạ, nên giao diện chép
  // thiếu / đủ / thừa một khoá là màn Đơn hàng TRẮNG BẢNG chứ không phải "sắp xếp hơi khác".
  // Tầng 2 (`test_40`) đối chiếu danh sách này với `GET /api/v2/don/loc-mo-ta`; ở đây ghim
  // đúng tám khoá của §1.2 và nhãn tiếng Việt của từng khoá.
  const khoa = L.SAP_XEP_DON.map(([k]) => k);
  assert.deepEqual(khoa.slice().sort(),
    ["cap_nhat_cu", "cap_nhat_moi", "cod_cao", "cod_thap", "cu_nhat", "ma_don", "moi_nhat", "nang_nhat"]);
  assert.equal(new Set(khoa).size, khoa.length, "khoá sắp xếp bị trùng");
  assert.ok(khoa.indexOf("moi_nhat") >= 0, "thiếu khoá MẶC ĐỊNH `moi_nhat` của máy chủ");
  const nhan = new Set();
  for (const [, ten] of L.SAP_XEP_DON) {
    assert.ok(ten && ten.length, `khoá ${ten} phải có nhãn tiếng Việt`);
    assert.ok(!nhan.has(ten), `nhãn sắp xếp bị trùng: ${ten}`);
    nhan.add(ten);
  }
});

/* ====================== 5. Dòng thời gian giao vận ====================== */

test("27 dienGiaiNguon — đọc được ba dạng nguồn của §11, nguồn lạ hiện nguyên văn", () => {
  assert.equal(L.dienGiaiNguon("user:42").loai, "user");
  assert.ok(L.dienGiaiNguon("user:42").ten.includes("42"));
  assert.equal(L.dienGiaiNguon("webhook:7").loai, "webhook");
  assert.equal(L.dienGiaiNguon("polling").loai, "polling");
  assert.equal(L.dienGiaiNguon("he_thong").loai, "he_thong");
  const la = L.dienGiaiNguon("cron:abc");
  assert.equal(la.loai, "la");
  assert.equal(la.ten, "cron:abc", "nguồn lạ phải hiện nguyên văn");
});

test("28 dungTimeline — sắp theo id tăng dần và KHÔNG bịa mốc giờ nào", () => {
  const tl = L.dungTimeline(
    { trang_thai_giao: "dang_giao", carrier_account_id: 7 },
    [{ id: 3, luc: "2026-10-02 10:00", nguon: "webhook:7", noi_dung: "trạng thái giao → dang_giao" },
     { id: 1, luc: "2026-10-01 08:00", nguon: "user:5", noi_dung: "tạo đơn" },
     { id: 2, luc: "2026-10-01 09:00", nguon: "user:5", noi_dung: "duyệt đơn" }]);
  assert.deepEqual(tl.nut.map(n => n.noi_dung),
    ["tạo đơn", "duyệt đơn", "trạng thái giao → dang_giao"]);
  assert.equal(tl.nut.filter(n => n.suy_ra).length, 0,
    "trạng thái giao đã có trong lịch sử ⇒ KHÔNG thêm nút suy ra");
  assert.ok(tl.nut.every(n => n.luc), "mọi nút đều phải có mốc thật từ lich_su");
});

test("29 dungTimeline — trạng thái giao KHÔNG có trong lịch sử thì nút cuối gắn cờ suy_ra và luc=null", () => {
  const tl = L.dungTimeline(
    { trang_thai_giao: "giao_thanh_cong", carrier_account_id: 7 },
    [{ id: 1, luc: "2026-10-01 08:00", nguon: "user:5", noi_dung: "tạo đơn" }]);
  const cuoi = tl.nut[tl.nut.length - 1];
  assert.equal(cuoi.suy_ra, true);
  assert.equal(cuoi.luc, null, "cấm bịa giờ cho nút suy ra — §12.1 luật 4");
  assert.ok(cuoi.noi_dung.includes("giao_thanh_cong"));
  assert.equal(tl.nhan_giao.ma, "giao_thanh_cong");
});

test("30 dungTimeline — đơn chưa gửi hãng: lịch sử trống, không nút suy ra, ghi chú phạm vi nói rõ", () => {
  const tl = L.dungTimeline({ trang_thai: "nhap" }, []);
  assert.equal(tl.nut.length, 0);
  assert.equal(tl.nhan_giao, null);
  assert.ok(tl.ghi_chu_pham_vi.includes("chưa gửi hãng"));
});

test("31 dungTimeline — mang theo cờ cần đối soát (hãng timeout = KHÔNG BIẾT, không phải thành công)", () => {
  const tl = L.dungTimeline({ can_doi_soat_ket_qua: 1, carrier_account_id: 7 }, []);
  assert.equal(tl.can_doi_soat, true);
  assert.ok(tl.ghi_chu_pham_vi.includes("webhook"));
});

/* ====================== 6. Kiểm dữ liệu form ====================== */

const DON_DU = {
  nguoi_gui_ten: "Shop A", nguoi_gui_sdt: "0901111111", nguoi_gui_dia_chi: "1 Đường A",
  nguoi_nhan_ten: "Khách B", nguoi_nhan_sdt: "0902222222", nguoi_nhan_dia_chi: "2 Phố B",
  hang_hoa: "Hộp", khoi_luong_gram: "500", cod: "0",
};

test("32 kiemTraDon — dữ liệu đủ thì không báo lỗi nào", () => {
  assert.deepEqual(L.kiemTraDon(DON_DU), []);
});

test("33 kiemTraDon — thiếu cả tám trường bắt buộc thì báo đủ tám, không báo gộp một dòng", () => {
  const loi = L.kiemTraDon({});
  assert.equal(loi.length, 8);
  assert.deepEqual(loi.map(x => x.truong).sort(), L.TRUONG_BAT_BUOC_DON.map(([k]) => k).sort());
});

test("34 kiemTraDon — khoảng trắng không tính là có dữ liệu", () => {
  const loi = L.kiemTraDon(Object.assign({}, DON_DU, { nguoi_nhan_ten: "   " }));
  assert.equal(loi.length, 1);
  assert.equal(loi[0].truong, "nguoi_nhan_ten");
});

test("35 kiemTraDon — cân nặng phải là số gram > 0", () => {
  for (const kl of ["0", "-5", "abc"]) {
    const loi = L.kiemTraDon(Object.assign({}, DON_DU, { khoi_luong_gram: kl }));
    assert.ok(loi.some(x => x.truong === "khoi_luong_gram"), `cân nặng ${kl} phải bị chặn`);
  }
});

test("36 kiemTraDon — COD âm bị chặn, COD 0 hợp lệ", () => {
  assert.ok(L.kiemTraDon(Object.assign({}, DON_DU, { cod: "-1" })).some(x => x.truong === "cod"));
  assert.deepEqual(L.kiemTraDon(Object.assign({}, DON_DU, { cod: "0" })), []);
});

test("37 kiemTraDon — SĐT sai định dạng bị chặn, dạng có dấu phân cách vẫn qua", () => {
  assert.ok(L.kiemTraDon(Object.assign({}, DON_DU, { nguoi_nhan_sdt: "abc-def" }))
    .some(x => x.truong === "nguoi_nhan_sdt"));
  assert.ok(L.kiemTraDon(Object.assign({}, DON_DU, { nguoi_nhan_sdt: "090" }))
    .some(x => x.truong === "nguoi_nhan_sdt"), "ngắn hơn 8 ký tự phải bị chặn");
  assert.deepEqual(L.kiemTraDon(Object.assign({}, DON_DU, { nguoi_nhan_sdt: "+84 90 222 2222" })), []);
});

/* ====================== 7. Chọn tài khoản hãng khi gửi ====================== */

test("38 chonTaiKhoanGui — tài khoản bị khóa KHÔNG được mời chọn, và nêu rõ lý do loại", () => {
  const r = L.chonTaiKhoanGui(
    [{ id: 1, hang: "jt", ten: "JT bật", moi_truong: "mock", kich_hoat: 1 },
     { id: 2, hang: "jt", ten: "JT khóa", moi_truong: "mock", kich_hoat: 0 }], [HANG_MOCK]);
  assert.deepEqual(r.dung_duoc.map(x => x.id), [1]);
  assert.deepEqual(r.loai_ra.map(x => x.id), [2]);
  assert.ok(r.loai_ra[0].ly_do_loai.includes("khóa"));
});

test("39 chonTaiKhoanGui — hãng không khai createOrder thì bị loại (không mời người dùng bấm vào chỗ chắc chắn lỗi)", () => {
  const r = L.chonTaiKhoanGui(
    [{ id: 5, hang: "x", ten: "X", moi_truong: "mock", kich_hoat: 1 }],
    [{ ma: "x", ten: "Hãng X", live_mo: false, capabilities: { createOrder: false, getShippingLabel: true } }]);
  assert.equal(r.dung_duoc.length, 0);
  assert.ok(r.loai_ra[0].ly_do_loai.includes("createOrder"));
});

test("40 chonTaiKhoanGui — mục dùng được mang theo chế độ dữ liệu và khả năng in nhãn/theo dõi", () => {
  const r = L.chonTaiKhoanGui(
    [{ id: 1, hang: "jt", ten: "JT", moi_truong: "mock", kich_hoat: 1 }],
    [{ ma: "jt", ten: "J&T", live_mo: false,
       capabilities: { createOrder: true, getShippingLabel: true, trackOrder: true } }]);
  const m = r.dung_duoc[0];
  assert.equal(m.che_do.ma, "MOCK");
  assert.equal(m.hang_ten, "J&T");
  assert.equal(m.in_nhan_duoc, true);
  assert.equal(m.theo_doi_duoc, true);
});

test("41 chonTaiKhoanGui — hãng thiếu hẳn capabilities thì vẫn cho tạo đơn (chỉ loại khi khai rõ false)", () => {
  const r = L.chonTaiKhoanGui([{ id: 1, hang: "z", ten: "Z", moi_truong: "mock", kich_hoat: 1 }], []);
  assert.equal(r.dung_duoc.length, 1);
  assert.equal(r.dung_duoc[0].in_nhan_duoc, false, "không khai thì coi như KHÔNG in nhãn được");
});

/* ====================== 8. Phiếu in ====================== */

test("42 metaNhan — BẤT BIẾN: la_nhan_hang luôn false khi chưa có API nhãn của hãng", () => {
  for (const hang of [null, HANG_MOCK, HANG_LIVE,
                      { ma: "q", live_mo: true, capabilities: { getShippingLabel: true } }]) {
    const meta = L.metaNhan({ ma_don: "D1", ma_van_don: "X1", phi_van_chuyen: 1000 },
      { id: 1, hang: "q", moi_truong: "production" }, hang);
    assert.equal(meta.la_nhan_hang, false,
      "phiếu in là PHIẾU NỘI BỘ — cấm tự khai là nhãn vận đơn của hãng khi chưa có API");
  }
});

test("43 metaNhan — nêu đúng những gì còn thiếu, không lấp bằng số tự nghĩ", () => {
  const meta = L.metaNhan({ ma_don: "D2" }, null, null);
  assert.equal(meta.thieu.length, 3);
  assert.ok(meta.thieu.some(x => x.includes("mã vận đơn")));
  assert.ok(meta.thieu.some(x => x.includes("phí")));
  assert.ok(meta.thieu.some(x => x.includes("tài khoản hãng")));
  assert.equal(meta.o.ma_van_don, "", "thiếu thì để trống, không sinh mã giả");
  assert.equal(meta.o.phi_van_chuyen, undefined);
});

test("44 metaNhan — đơn đủ dữ liệu thì không còn mục thiếu, và chế độ dữ liệu đi theo phiếu", () => {
  const meta = L.metaNhan(
    { ma_don: "D3", ma_van_don: "JT9", phi_van_chuyen: 25000, carrier_account_id: 7, cod: 100 },
    { id: 7, hang: "jt", moi_truong: "mock" }, HANG_MOCK);
  assert.deepEqual(meta.thieu, []);
  assert.equal(meta.che_do.ma, "MOCK");
  assert.equal(meta.hang_ho_tro_in_nhan, false, "J&T mock trong ca này không khai getShippingLabel");
});

/* ====================== 9. Webhook monitor: gom nhóm ====================== */

const SK = [
  { id: 1, event_id: "e1", hang: "jt", trang_thai: "xong", so_lan_thu: 0 },
  { id: 2, event_id: "e2", hang: "jt", trang_thai: "dlq", so_lan_thu: 5, loi_cuoi: "timeout" },
  { id: 3, event_id: "e3", hang: "vtp", trang_thai: "cho_thu_lai", so_lan_thu: 2 },
  { id: 4, event_id: "e4", hang: "jt", trang_thai: "khong_khop", so_lan_thu: 1 },
  { id: 5, event_id: "e5", hang: "jt", trang_thai: "NEEDS_REVIEW", so_lan_thu: 0 },
  { id: 6, event_id: "e6", hang: "jt", trang_thai: "PARKED", so_lan_thu: 0 },
];

test("45 nhomWebhook — đếm đúng DLQ, chờ thử lại, tổng lần thử lại và sự kiện thử nhiều nhất", () => {
  const n = L.nhomWebhook(SK);
  assert.equal(n.tong, 6);
  assert.deepEqual(n.dlq.map(s => s.id), [2]);
  assert.deepEqual(n.cho_thu_lai.map(s => s.id), [3]);
  assert.equal(n.tong_lan_thu_lai, 8);
  assert.equal(n.so_su_kien_da_thu_lai, 3);
  assert.equal(n.thu_lai_nhieu_nhat.id, 2);
});

test("46 nhomWebhook — tách riêng trạng thái NHẬP NHẰNG và trạng thái lạ khác", () => {
  const n = L.nhomWebhook(SK);
  assert.deepEqual(n.nhap_nhang.map(s => s.id), [5]);
  assert.deepEqual(n.trang_thai_la.map(s => s.id), [6]);
});

test("47 nhomWebhook — chỉ dlq và khong_khop được mời replay (quyền vẫn do backend kiểm)", () => {
  assert.deepEqual(L.nhomWebhook(SK).replay_duoc, [2, 4]);
});

test("48 nhomWebhook — danh sách rỗng không làm hỏng gì", () => {
  const n = L.nhomWebhook([]);
  assert.equal(n.tong, 0);
  assert.equal(n.thu_lai_nhieu_nhat, null);
  assert.deepEqual(n.replay_duoc, []);
});

/* ====================== 10. Từ chối đơn ====================== */

test("49 kiemTraTuChoi — phải chọn lý do, và lý do phải nằm trong danh mục", () => {
  assert.ok(L.kiemTraTuChoi({}).some(x => x.truong === "ly_do_ma"));
  assert.ok(L.kiemTraTuChoi({ ly_do_ma: "bay_ra" }).some(x => x.truong === "ly_do_ma"));
  assert.deepEqual(L.kiemTraTuChoi({ ly_do_ma: "sai_dia_chi" }), []);
});

test('50 kiemTraTuChoi — chọn "khác" thì bắt buộc ghi chú', () => {
  assert.ok(L.kiemTraTuChoi({ ly_do_ma: "khac" }).some(x => x.truong === "ghi_chu"));
  assert.ok(L.kiemTraTuChoi({ ly_do_ma: "khac", ghi_chu: "   " }).some(x => x.truong === "ghi_chu"));
  assert.deepEqual(L.kiemTraTuChoi({ ly_do_ma: "khac", ghi_chu: "hàng hỏng" }), []);
});

/* ====================== 11. Bảng API chờ backend ====================== */

test("51 API_CHO_BACKEND — mỗi mục phải khai đủ đường, method, màn, schema mong đợi và ghi chú", () => {
  assert.ok(L.API_CHO_BACKEND.length >= 5);
  for (const d of L.API_CHO_BACKEND) {
    assert.ok(d.ten && d.duong && d.method, `thiếu trường cơ bản: ${JSON.stringify(d)}`);
    assert.ok(d.duong.startsWith("/api/"), d.duong);
    assert.ok(d.man, `mục ${d.duong} phải nói rõ màn nào dùng`);
    assert.ok(d.mong_doi_ra && Object.keys(d.mong_doi_ra).length,
      `mục ${d.duong} phải khai schema mong đợi để AG-00 làm được`);
    assert.ok(d.ghi_chu && d.ghi_chu.length > 20, `mục ${d.duong} phải nói hiện đang thay thế bằng gì`);
  }
});

test("52 API_CHO_BACKEND — không trùng đường, và ba đường quan trọng phải được KHAI Ở ĐÂU ĐÓ", () => {
  const duong = L.API_CHO_BACKEND.map(d => d.duong);
  assert.equal(new Set(duong).size, duong.length, "khai trùng đường là có hai chỗ nói về một việc");
  // Bản đầu đòi ba đường này nằm TRONG API_CHO_BACKEND — đúng lúc viết, vì backend chưa có.
  // AG-00 cắm `/tu-choi` thật ngày 15/10, nên chốt như vậy biến ca thử thành cửa khoá chết:
  // backend làm xong là ca HỎNG, mà đó là chiều TIẾN BỘ. Ý định thật của ca là "không đường
  // nào được biến mất im lặng khỏi cả hai danh sách" — nên chốt đúng ý định đó.
  const dangDung = L.API_DANG_DUNG.map(([, d]) => d);
  const moiNoi = new Set([...duong, ...dangDung]);
  for (const d of ["/api/v2/don/<id>/tu-choi", "/api/v2/don/<id>/nhan",
                   "/api/v2/webhook/su-kien/<id>"]) {
    assert.ok(moiNoi.has(d),
      `${d} không còn được khai ở API_CHO_BACKEND lẫn API_DANG_DUNG — đường không ai canh`);
  }
  // Khai ở CẢ HAI danh sách chỉ hợp lệ khi mục đó mang cờ `mot_phan: true` — nghĩa là đường
  // ĐANG dùng được một phần và VẪN còn chờ phần còn lại (ví dụ `GET /api/v2/don`: lọc cơ bản
  // chạy rồi, tham số lọc nâng cao thì chưa). Không có cờ mà nằm ở cả hai thì là hai chỗ nói
  // về một việc, và hai chỗ như vậy sẽ lệch nhau.
  const motPhan = new Set(L.API_CHO_BACKEND.filter(d => d.mot_phan).map(d => d.duong));
  const caHai = duong.filter(d => dangDung.includes(d) && !motPhan.has(d));
  assert.deepEqual(caHai, [],
    `khai ở cả hai danh sách mà không có cờ mot_phan: ${caHai}`);
});

/* ====================== 12. Canh cấu trúc của chính logic.js ====================== */

test("53 logic.js KHÔNG được chạm DOM / fetch / timer — nếu chạm thì tầng Node không còn kiểm được nó", () => {
  const ma = readFileSync(join(GOC, "admin", "logic.js"), "utf8");
  // Quét MÃ, không quét lời bình: chính lời bình của logic.js có nhắc "KHÔNG setTimeout",
  // và lần chạy đầu ca này đã báo hỏng vì đúng câu đó — giữ lại ghi chú để lần sau không
  // ai gỡ bước bỏ lời bình. Cũng bỏ hai dòng cầu nối xuất module (chỗ duy nhất nhắc window).
  const than = ma
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "")
    .split("\n").filter(d => !/window\.VIPLOGIC|module\.exports/.test(d)).join("\n");
  for (const xau of ["document.", "window.", "fetch(", "localStorage", "setTimeout", "innerHTML", "XMLHttpRequest"]) {
    assert.ok(!than.includes(xau), `logic.js không được dùng ${xau} — nó phải là logic thuần`);
  }
});

test("54 logic.js KHÔNG được giữ secret hay tên miền hãng (cùng luật với thu_saas test_13)", () => {
  const ma = readFileSync(join(GOC, "admin", "logic.js"), "utf8");
  for (const xau of ["privateKey", "jtexpress.vn", "api_key:", "secret:", "BEGIN RSA", "Bearer "]) {
    assert.ok(!ma.includes(xau), `logic.js chứa dấu hiệu secret: ${xau}`);
  }
});

test("55 admin.js phải DÙNG logic.js, không giữ bản sao bảng trạng thái thứ hai", () => {
  const ma = readFileSync(join(GOC, "admin", "admin.js"), "utf8");
  assert.ok(ma.includes("window.VIPLOGIC"), "admin.js phải nạp logic.js");
  // Hai bản nội dung là hai bản sẽ lệch nhau: bảng trạng thái chỉ được khai ở logic.js.
  assert.ok(!/const\s+BATCH_TT\s*=/.test(ma), "BATCH_TT phải ở logic.js, không nhân bản sang admin.js");
  assert.ok(!/const\s+DONG_TT\s*=/.test(ma), "DONG_TT phải ở logic.js, không nhân bản sang admin.js");
});

test("56 admin/ KHÔNG có thư mục con (thu_saas test_13 dùng os.listdir + open ⇒ gặp thư mục là IsADirectoryError)", () => {
  const { readdirSync, statSync } = require("node:fs");
  for (const ten of readdirSync(join(GOC, "admin"))) {
    assert.ok(statSync(join(GOC, "admin", ten)).isFile(),
      `admin/${ten} là thư mục — sẽ làm hỏng bộ thử quét secret của AG-00`);
  }
});
