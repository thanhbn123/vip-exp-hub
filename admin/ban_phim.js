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
   đã làm ở G17 — tệp này không đọc, không ghi, không bọc nó). */
(function () {
  "use strict";

  var PHIEN_BAN = "G19-AG06";
  var so_lan_nang_cap = 0;

  /* Con trỏ bàn phím phải THẤY được. `assets/css/style.css` đã có `:focus-visible` cho
     `.sidebar nav a` và các `.nut`; luật dưới đây phủ NỐT phần còn lại của khung (đặc biệt
     `#nut-thoat` nằm trong `.chan`, không khớp luật nào của style.css) để dấu hiệu tiêu điểm
     không phụ thuộc vào kiểu mặc định của trình duyệt — bộ thử đo được nó bằng
     `getComputedStyle`, không đo bằng cảm nhận. Màu và độ dày lấy đúng token của style.css. */
  var CSS = ".khung a[href]:focus-visible,.khung button:focus-visible,.khung input:focus-visible," +
            ".khung select:focus-visible,.khung textarea:focus-visible,.khung [tabindex]:focus-visible" +
            "{outline:2px solid #7C9CF5;outline-offset:2px}";

  function ganCss() {
    if (document.getElementById("css-ban-phim")) return;
    var s = document.createElement("style");
    s.id = "css-ban-phim";
    s.textContent = CSS;                       // CSP: style-src 'self' 'unsafe-inline'
    document.head.appendChild(s);
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
    var muc = sb.querySelectorAll(".menu-quan-tri a[data-man], #nut-thoat");
    for (var i = 0; i < muc.length; i++) {
      if (ngoaiKhungNhin) muc[i].setAttribute("tabindex", "-1");
      else muc[i].removeAttribute("tabindex");
    }
    return ngoaiKhungNhin;
  }

  function chay() {
    ganCss();
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
    so_lan_nang_cap: function () { return so_lan_nang_cap; },
    CHON_MENU: ".menu-quan-tri a[data-man]",   // để bộ thử không chép tay bộ chọn
  };
})();
