/* admin/ban_phim.js — DÙNG ĐƯỢC BẰNG BÀN PHÍM (V-13911). Mô-đun RIÊNG, nạp CUỐI cùng.
   ------------------------------------------------------------------------------------------
   VÌ SAO CÓ TỆP NÀY, VÀ VÌ SAO NÓ KHÔNG NẰM TRONG admin.js HAY logic.js:

   1. LỖI ĐO ĐƯỢC (BAN_GIAO.md §6.1 `V-13911`, §10 gọi là CHỖ YẾU NHẤT CỦA HỆ):
      `admin/admin.js::dungKhung()` dựng menu bằng `<a data-man="…">` — KHÔNG `href`, KHÔNG
      `tabindex`, KHÔNG `role`, và `#nut-thoat` (Đăng xuất) cũng vậy. Thẻ `<a>` không `href`
      KHÔNG vào được thứ tự Tab. Đo bằng Chromium thật (Playwright) ngày 15/10/2026, vai trò
      `shopa-owner`, bề rộng 1280:
        · 25/25 lượt Tab giữ nguyên `document.activeElement === body`;
        · cả tài liệu chỉ có ĐÚNG 1 phần tử focusable (`#nut-menu`) và nó `display:none` ở
          bề rộng ≥ 768 ⇒ thực tế không có gì để Tab tới;
        · màn "Đơn hàng" thì Tab đi được 24 điều khiển TRONG `#man` nhưng KHÔNG BAO GIỜ tới
          được menu ⇒ người dùng bàn phím KHÔNG ĐỔI ĐƯỢC MÀN NÀO.

   2. VÌ SAO KHÔNG VÁ THẲNG TRONG `admin/admin.js`: hàm `dungKhung()` là chỗ làn AG-05 đang sửa
      cho `V-13910` (cắm 15 màn chết vào menu). Hai làn cùng sửa một hàm là đúng thứ luật
      quyền sở hữu sinh ra để chặn. AG-00 đã chốt: vá bằng MỘT MÔ-ĐUN RIÊNG, gắn hành vi SAU
      khi menu đã render — nên tệp này KHÔNG sửa một dòng nào của `admin.js`.

   3. VÌ SAO KHÔNG NẰM TRONG `admin/logic.js`: tầng 1 ca 53 (`thu_frontend/thu_logic.mjs`)
      cấm chuỗi `document.` · `window.` · `innerHTML` · `setTimeout` trong tệp ấy, vì nó phải
      là LOGIC THUẦN để `require()` được bằng Node. Luật đó ĐÚNG và được giữ nguyên; tệp này
      là tệp MỚI nên không bị luật ấy ràng buộc.

   PHẠM VI: chỉ giao diện quản trị, chỉ bàn phím. KHÔNG đổi cách vẽ màn, KHÔNG gọi mạng,
   KHÔNG chạm quyền (quyền vẫn do backend chốt), KHÔNG chạm `carrier_health.js` (phần AG-06
   đã làm ở G17 — tệp này không đọc, không ghi, không bọc nó).

   G21 · AG-06 — HAI LỖ CÒN LẠI SAU G19, ĐO ĐƯỢC TRÊN `integration/g20` @ a3400a8:
     (a) MENU 30 MỤC THÀNH CÁI GIÁ. Bản vá `href` làm 30 mục menu vào được thứ tự Tab, nhưng
         người dùng bàn phím phải bấm 31 lượt Tab mới tới điều khiển đầu tiên TRONG màn, và
         giá ấy TĂNG THEO MENU. Nay có LỐI ĐI TẮT (WCAG 2.4.1) là điểm dừng Tab ĐẦU TIÊN.
     (b) BẢN VÁ TỰ SINH MỘT ĐIỂM DỪNG KHUẤT. Gỡ 30 mục menu khỏi thứ tự Tab lúc thanh bên
         đóng làm `<nav class="menu-quan-tri">` (vùng cuộn) TỰ vào thứ tự Tab tại `x=-260`
         — tiêu điểm có, nhìn không thấy. Nay vùng cuộn trong thanh bên cũng bị khoá theo
         đúng luật ấy. Chi tiết + số đo: `docs/G21_BANPHIM_E2E.md`. */
(function () {
  "use strict";

  var PHIEN_BAN = "G21-AG06";
  var so_lan_nang_cap = 0;

  /* Con trỏ bàn phím phải THẤY được. `assets/css/style.css` đã có `:focus-visible` cho
     `.sidebar nav a` và các `.nut`; luật dưới đây phủ NỐT phần còn lại của khung (đặc biệt
     `#nut-thoat` nằm trong `.chan`, không khớp luật nào của style.css) để dấu hiệu tiêu điểm
     không phụ thuộc vào kiểu mặc định của trình duyệt — bộ thử đo được nó bằng
     `getComputedStyle`, không đo bằng cảm nhận. Màu và độ dày lấy đúng token của style.css. */
  var CSS = ".khung a[href]:focus-visible,.khung button:focus-visible,.khung input:focus-visible," +
            ".khung select:focus-visible,.khung textarea:focus-visible,.khung [tabindex]:focus-visible" +
            "{outline:2px solid #7C9CF5;outline-offset:2px}" +
            /* LỐI ĐI TẮT phải NHÌN THẤY ĐƯỢC khi nó đang giữ tiêu điểm, nhưng KHÔNG được
               chiếm chỗ khi rảnh: `position:fixed` nằm NGOÀI luồng bố cục nên nó không thể
               đẩy `scrollWidth` của tài liệu — bố cục ba bề rộng của tầng 3 không đổi một
               pixel. `top:-3rem` khi rảnh (ở TRÊN khung nhìn ⇒ không sinh vùng cuộn), `top:0`
               khi có tiêu điểm. Không `transition`: phép đo của tầng 3 đọc toạ độ NGAY sau
               lượt Tab và không được phép bắt gặp khung hình giữa đường. */
            ".khung .bo-qua-menu{position:fixed;top:-3rem;left:8px;z-index:60;" +
            "background:#111827;color:#fff;padding:8px 14px;border-radius:0 0 8px 8px;" +
            "font:600 13px/1.25 system-ui,-apple-system,'Segoe UI',sans-serif;text-decoration:none}" +
            ".khung .bo-qua-menu:focus{top:0}";

  function ganCss() {
    if (document.getElementById("css-ban-phim")) return;
    var s = document.createElement("style");
    s.id = "css-ban-phim";
    s.textContent = CSS;                       // CSP: style-src 'self' 'unsafe-inline'
    document.head.appendChild(s);
  }

  /* LỐI ĐI TẮT QUA MENU (WCAG 2.4.1 "Bypass Blocks") — VÌ SAO CẦN, ĐO ĐƯỢC:
     menu của vai trò doanh nghiệp có 30 mục (G19 · AG-05 cắm thêm 20 màn vào menu). Bản vá
     `href` ở trên làm 30 mục ấy vào được thứ tự Tab — ĐÚNG, nhưng cái giá là người dùng bàn
     phím phải bấm 31 lượt Tab mới tới được điều khiển ĐẦU TIÊN trong màn, và cái giá ấy
     TĂNG THEO MENU. Đo ngày 16/10/2026, Chromium, `shopa-owner`, 1280px: 30 lượt Tab chỉ vào
     được 1 điều khiển trong màn (đặc tả `06_ban_phim.spec.js` ca 04).
     Lối đi tắt đưa cái giá ấy về một HẰNG SỐ (1 lượt Tab + Enter), không phụ thuộc menu.
     Nó KHÔNG thay menu, KHÔNG đổi thứ tự Tab của menu: chỉ THÊM một điểm dừng ĐẦU TIÊN.
     Chỉ tạo khi trong khung THẬT SỰ có `#man` để tới — một lối đi tắt dẫn vào chỗ trống là
     một lời hứa sai. */
  var CHON_BO_QUA = ".bo-qua-menu";
  function diToiMan() {
    var man = document.getElementById("man");
    if (!man) return false;
    /* Giữ nguyên màn đang xem trên thanh địa chỉ: `href="#man"` sẽ ghi `#man` vào hash, và
       SPA này dùng hash để nói MÀN ĐANG XEM. Một lối đi tắt làm địa chỉ nói sai màn thì nó
       vừa tiện vừa nói dối. */
    var dangXem = document.querySelector(".menu-quan-tri a.hien-tai");
    var hash = dangXem && dangXem.dataset.man ? "#" + dangXem.dataset.man : null;
    if (!man.hasAttribute("tabindex")) man.setAttribute("tabindex", "-1");
    man.focus();
    if (hash) { try { history.replaceState(null, "", hash); } catch (e) { /* file:// — bỏ qua */ } }
    return document.activeElement === man;
  }

  function ganLoiTat(g) {
    if (g.querySelector(CHON_BO_QUA)) return 0;              // idempotent
    var khung = g.querySelector(".khung");
    if (!khung || !g.querySelector("#man")) return 0;
    var a = document.createElement("a");
    a.className = "bo-qua-menu";
    a.setAttribute("href", "#man");                          // liên kết THẬT ⇒ Enter kích hoạt theo luật trình duyệt
    a.setAttribute("data-bo-qua", "man");
    a.textContent = "Bỏ qua menu — tới nội dung màn";
    a.addEventListener("click", function (ev) {
      /* `preventDefault` để trình duyệt KHÔNG ghi `#man` vào hash; việc chuyển tiêu điểm do
         `diToiMan()` làm, rồi trả hash về đúng màn đang xem. */
      ev.preventDefault();
      diToiMan();
    });
    khung.insertBefore(a, khung.firstChild);                 // ĐIỂM DỪNG TAB ĐẦU TIÊN của khung
    return 1;
  }

  /* Nâng cấp menu + lối ra. Idempotent: gọi lại bao nhiêu lần cũng không nhân đôi gì.
     `href="#<mã màn>"` KHÔNG chỉ để vào được thứ tự Tab: nó biến mục menu thành LIÊN KẾT
     thật — Enter kích hoạt theo đúng luật trình duyệt, con trỏ chuột đổi thành bàn tay,
     và địa chỉ trên thanh địa chỉ nói đúng màn đang xem (SPA này đã nghe `hashchange`).
     Trình xử lý `click` do `admin.js` gắn vẫn nguyên vẹn: tệp này không gỡ, không bọc nó. */
  function nangCap(goc) {
    var g = goc || document;
    var n = 0;

    var muc = g.querySelectorAll(".menu-quan-tri a[data-man]");
    for (var i = 0; i < muc.length; i++) {
      var a = muc[i];
      if (!a.getAttribute("href")) { a.setAttribute("href", "#" + a.dataset.man); n++; }
      // Trạng thái "đang xem" đã có trên màn (lớp `hien-tai`); nói lại bằng thuộc tính cho
      // trình đọc màn hình. Không suy diễn gì thêm: chỉ soi lại đúng lớp ấy.
      if (a.classList.contains("hien-tai")) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
    }

    var thoat = g.querySelector("#nut-thoat");
    if (thoat && !thoat.getAttribute("href")) {
      thoat.setAttribute("href", "#dang-xuat");   // hash lạ: `admin.js` bỏ qua, không mở màn nào
      n++;
    }

    /* Mở/đóng thanh bên là việc của `admin.js` (nó gắn trình xử lý cho nút ☰). Tệp này KHÔNG
       gỡ, KHÔNG bọc trình xử lý ấy — chỉ nghe THÊM cùng sự kiện để cập nhật thứ tự Tab NGAY
       trong cùng lượt bấm, thay vì chờ vòng theo dõi DOM chạy sau đó. */
    var nut = g.querySelector("#nut-menu");
    if (nut && !nut.__banPhimDaGan) {
      nut.__banPhimDaGan = true;
      nut.addEventListener("click", function () { dongBoTabindex(); });
    }

    if (n) so_lan_nang_cap++;
    return n;
  }

  /* VÙNG CUỘN CŨNG LÀ ĐIỂM DỪNG TAB — đo được, không suy đoán. Từ Chromium 127, một phần tử
     có `overflow:auto` mà nội dung cao hơn khung sẽ TỰ vào thứ tự Tab **khi bên trong nó
     không còn gì vào được**. Bản vá `href` ở trên gỡ 30 mục menu khỏi thứ tự Tab lúc thanh
     bên đóng — và đúng vì thế `<nav class="menu-quan-tri">` (vùng cuộn, `scrollHeight` 1368 >
     `clientHeight` 602) trở thành điểm dừng Tab ĐẦU TIÊN, tại `x=-260`: tiêu điểm có, nhìn
     không thấy gì. Bản vá tự sinh ra lỗ ấy, nên nó phải tự bịt.
     Nhận biết bằng chính thứ quyết định hành vi (`overflow` + có cuộn được thật), không bằng
     tên lớp: CSS đổi thì phép đo đổi theo. */
  function laVungCuon(n) {
    var s = getComputedStyle(n);
    if (!/(auto|scroll|overlay)/.test(s.overflowY + " " + s.overflowX)) return false;
    return n.scrollHeight - n.clientHeight > 1 || n.scrollWidth - n.clientWidth > 1;
  }

  /* Tên thuộc tính ĐÁNH DẤU do chính tệp này đặt, để lúc mở lại chỉ gỡ đúng thứ nó đã thêm —
     không đụng `tabindex` của người viết khác. */
  var DA_KHOA = "data-bp-khoa";

  /* Bố cục HẸP (≤768px): thanh bên là `position:fixed; left:-260px` — nằm NGOÀI khung nhìn
     chứ không `display:none`, nên các liên kết trong đó VẪN vào thứ tự Tab và người dùng bàn
     phím sẽ Tab vào một chỗ không nhìn thấy gì (đo được: 12 điểm dừng đầu ở `x=-252`). Bản vá
     `href` mà không có bước này thì mở lỗ này ra. Nên: thanh bên ĐANG Ở NGOÀI khung nhìn thì
     các mục của nó mang `tabindex="-1"` (ra khỏi thứ tự Tab); mở ra (`.mo`) thì trả lại.
     Nhận biết "bố cục hẹp" bằng chính thứ quyết định nó — nút ☰: ở bố cục rộng nút ấy
     `display:none`. Không chép lại số 768 vào đây: CSS đổi thì phép đo này đổi theo. */
  function dongBoTabindex() {
    var sb = document.getElementById("sidebar");
    if (!sb) return false;
    var nut = document.getElementById("nut-menu");
    var coNutMenu = !!(nut && getComputedStyle(nut).display !== "none");
    var dangMo = sb.classList.contains("mo");
    var ngoaiKhungNhin = coNutMenu && !dangMo;

    /* (1) Mọi thứ ĐANG giữ tiêu điểm được trong thanh bên: mục menu, lối ra, VÀ các vùng
       cuộn (xem `laVungCuon`). Duyệt theo bộ chọn cố định cộng một lượt quét con cháu — lượt
       quét chỉ để tìm vùng cuộn, và nó là thứ duy nhất bắt được `<nav>`. */
    var doiTuong = [];
    var coDinh = sb.querySelectorAll(".menu-quan-tri a[data-man], #nut-thoat");
    for (var i = 0; i < coDinh.length; i++) doiTuong.push(coDinh[i]);
    var con = sb.querySelectorAll("nav, div, ul, ol, aside, section");
    for (var j = 0; j < con.length; j++) if (laVungCuon(con[j])) doiTuong.push(con[j]);
    if (laVungCuon(sb)) doiTuong.push(sb);

    for (var k = 0; k < doiTuong.length; k++) {
      var n = doiTuong[k];
      if (ngoaiKhungNhin) {
        if (n.getAttribute("tabindex") === "-1") continue;   // đã ngoài thứ tự Tab — không đánh dấu
        n.setAttribute("tabindex", "-1");
        n.setAttribute(DA_KHOA, "1");
      } else if (n.getAttribute(DA_KHOA)) {
        n.removeAttribute("tabindex");
        n.removeAttribute(DA_KHOA);
      }
    }
    return ngoaiKhungNhin;
  }

  function chay() {
    ganCss();
    ganLoiTat(document);
    nangCap(document);
    dongBoTabindex();
  }

  /* Khung quản trị được DỰNG LẠI mỗi lần đăng nhập, đổi doanh nghiệp, hoặc phiên hết hạn —
     nên không thể chỉ chạy một lần lúc nạp. Theo dõi `childList` (khung mới) và `class`
     (mục đang xem đổi) rồi nâng cấp lại. Việc nâng cấp chỉ ĐẶT thuộc tính, không đổi
     `class`/`childList`, nên nó không tự kích hoạt chính mình. */
  var hen = null;
  function henNangCap() {
    if (hen) return;
    hen = setTimeout(function () { hen = null; chay(); }, 0);
  }

  function theoDoi() {
    if (!window.MutationObserver) return;
    new MutationObserver(henNangCap).observe(document.documentElement, {
      childList: true, subtree: true, attributes: true, attributeFilter: ["class"],
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { chay(); theoDoi(); });
  } else {
    chay(); theoDoi();
  }

  /* Bộ thử tầng 3 đọc những thứ này: nó phải đo được ĐÚNG cái đã được nâng cấp, và phải
     chứng minh được phép đo ĐỎ khi tệp này không chạy (xem `thu_giao_dien/06_ban_phim.spec.js`). */
  window.VIPBANPHIM = {
    phien_ban: PHIEN_BAN,
    nangCap: nangCap,
    dongBoTabindex: dongBoTabindex,
    diToiMan: diToiMan,
    laVungCuon: laVungCuon,
    so_lan_nang_cap: function () { return so_lan_nang_cap; },
    CHON_MENU: ".menu-quan-tri a[data-man]",   // để bộ thử không chép tay bộ chọn
    CHON_BO_QUA: CHON_BO_QUA,                  // lối đi tắt qua menu (WCAG 2.4.1)
  };
})();
