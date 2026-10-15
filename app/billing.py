# G10 — Billing: gói dịch vụ, hạn mức, usage. ĐO TỪ BACKEND — không tin số liệu frontend.
# Chưa nối thanh toán thật (chờ Owner duyệt); chỉ gói/hạn mức/usage/lịch sử.
import csdl


class VuotHanMuc(Exception):
    pass


_CO_BANG_PHIEN_BAN = None


def _co_bang_phien_ban():
    """Hai bảng của G08 đã có chưa (chỉ có sau migration v8). Nhớ kết quả để khỏi tra mãi."""
    global _CO_BANG_PHIEN_BAN
    if _CO_BANG_PHIEN_BAN is None:
        co = {r["name"] for r in csdl.nhieu(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name IN ('dang_ky','goi_phien_ban')")}
        _CO_BANG_PHIEN_BAN = {"dang_ky", "goi_phien_ban"} <= co
    return _CO_BANG_PHIEN_BAN


def quen_cache_phien_ban():
    """Gọi sau migration — nếu không, tiến trình đang chạy vẫn nhớ "chưa có bảng"."""
    global _CO_BANG_PHIEN_BAN
    _CO_BANG_PHIEN_BAN = None


def goi_cua_tenant(tenant_id):
    """Hạn mức ĐANG HIỆU LỰC của tenant. Ưu tiên PHIÊN BẢN GÓI ĐÃ GHIM trong `dang_ky`.

    AG-02 nêu ở đợt 3, AG-00 đo lại: bản cũ đọc hạn mức **hiện tại** từ `goi_dich_vu`, nên
    bốn chốt chặn thật (`kiem_va_tang_don` · `kiem_va_tang_ai` · `chen_membership_co_tran` ·
    `chen_tai_khoan_hang_co_tran`) **không tôn trọng phiên bản tenant đã ghim**.

    Đo được: tenant ghim `free` v1 (trần 50 đơn). Phát hành v2 rồi sửa `goi_dich_vu` lên
    9999 → `goi_dich_vu.han_muc_hieu_luc` vẫn nói **v1**, nhưng `goi_cua_tenant` trả **9999**.
    Nghĩa là tenant bị áp hạn mức của phiên bản nó KHÔNG đăng ký. Hướng nào cũng sai: nới ra
    thì hệ cho dùng quá thoả thuận, siết lại thì chặn đúng người đang trả tiền.

    Lùi về `goi_dich_vu` khi: chưa migrate v8 (hai bảng chưa có), hoặc tenant chưa có đăng ký
    đang hoạt động. Lượt lùi đó CỐ Ý im lặng — mọi tenant có trước G08 đều ở ca này, và báo
    động cho ca bình thường là cách nhanh nhất làm người ta bỏ qua báo động.
    """
    if _co_bang_phien_ban():
        r = csdl.mot(
            "SELECT pb.goi_id AS id, pb.ten, pb.gia_thang_dong AS gia_thang,"
            " pb.han_muc_don_thang, pb.han_muc_ai_thang, pb.so_nhan_vien,"
            " pb.so_tai_khoan_hang, pb.phien_ban AS goi_phien_ban"
            " FROM dang_ky dk"
            " JOIN goi_phien_ban pb ON pb.goi_id=dk.goi_id AND pb.phien_ban=dk.goi_phien_ban"
            " WHERE dk.tenant_id=? AND dk.trang_thai='dang_hoat_dong'", (tenant_id,))
        if r is not None:
            return r
    return csdl.mot(
        "SELECT g.* FROM tenants t JOIN goi_dich_vu g ON g.id=t.goi_id WHERE t.id=?", (tenant_id,))


def usage_hien_tai(tenant_id):
    thang = csdl.thang_nay()
    u = csdl.mot("SELECT * FROM usage_thang WHERE tenant_id=? AND thang=?", (tenant_id, thang))
    return {"thang": thang, "so_don": u["so_don"] if u else 0, "so_ai": u["so_ai"] if u else 0}


def _tang(tenant_id, cot):
    thang = csdl.thang_nay()
    with csdl.khoa_ghi:
        kn = csdl.mo()
        kn.execute("INSERT OR IGNORE INTO usage_thang (tenant_id, thang) VALUES (?,?)", (tenant_id, thang))
        kn.execute(f"UPDATE usage_thang SET {cot}={cot}+1 WHERE tenant_id=? AND thang=?", (tenant_id, thang))
        kn.commit()


def kiem_va_tang_don(tenant_id):
    """Gọi khi GỬI đơn sang hãng. Vượt hạn mức gói → chặn. NGUYÊN TỬ.

    r35: bản cũ đọc `usage_hien_tai` rồi mới `_tang` — giữa hai bước có khe hở, nên nhiều lượt
    gửi song song cùng đọc "còn 1 suất" rồi cùng tăng. Đo thật: còn 1 suất mà **5/8 luồng** lọt
    qua, `so_don` thành 10004/10000. Vá bằng cách đổi cấu trúc chứ không thêm một lượt đọc nữa:
    đưa trần vào `WHERE` của MỘT câu `UPDATE`, để chính CSDL so — khe hở không còn tồn tại.
    Cùng khuôn `gioi_han._cong_co_tran`.
    """
    goi = goi_cua_tenant(tenant_id)
    tran = goi["han_muc_don_thang"]
    # Dùng CHUNG helper với lượt AI — hai bản sao của một câu SQL là hai bản sẽ lệch nhau,
    # và lần lệch trước đã tốn một lỗ hổng.
    if not _cong_bo_dem_co_tran(tenant_id, "so_don", tran):
        # Đọc lại CHỈ để viết thông điệp — quyết định đã do câu UPDATE ở trên chốt.
        u = usage_hien_tai(tenant_id)
        raise VuotHanMuc(
            f"đã dùng {u['so_don']}/{tran} đơn của gói {goi['ten']} tháng này")


def hoan_don(tenant_id):
    """Hoàn một suất đơn đã trừ, khi lượt gửi KHÔNG tạo được vận đơn.

    G04-L3: `kiem_va_tang_don` trừ suất TRƯỚC khi gọi hãng. Lượt gửi trả kết quả
    "không rõ" (timeout) rồi được gửi lại sẽ trừ suất LẦN HAI cho cùng một đơn.
    Không cho `so_don` xuống âm — trừ nhiều hơn số đã cộng là dấu hiệu lỗi logic chỗ khác.
    """
    thang = csdl.thang_nay()
    with csdl.khoa_ghi:
        kn = csdl.mo()
        cur = kn.execute("UPDATE usage_thang SET so_don=so_don-1"
                         " WHERE tenant_id=? AND thang=? AND so_don >= 1", (tenant_id, thang))
        kn.commit()
    return cur.rowcount == 1


def _cong_bo_dem_co_tran(tenant_id, cot, tran):
    """Cộng 1 vào `cot` của `usage_thang` CHỈ KHI không vượt `tran`. Nguyên tử. True nếu cộng được.

    Trần nằm trong `WHERE` nên chính CSDL so — không có khe hở nào giữa lúc đọc và lúc ghi.
    MỘT chỗ duy nhất dựng câu này, để mọi bộ đếm dùng chung đúng một khuôn: trước đây mỗi chốt
    tự viết lại và chỉ MỘT chốt được vá, nên ba chốt còn lại hỏng y nguyên.
    """
    thang = csdl.thang_nay()
    with csdl.khoa_ghi:
        kn = csdl.mo()
        kn.execute("INSERT OR IGNORE INTO usage_thang (tenant_id, thang) VALUES (?,?)",
                   (tenant_id, thang))
        cur = kn.execute(
            f"UPDATE usage_thang SET {cot}={cot}+1"
            f" WHERE tenant_id=? AND thang=? AND {cot}+1 <= ?", (tenant_id, thang, tran))
        duoc = cur.rowcount == 1
        kn.commit()
    return duoc


def kiem_va_tang_ai(tenant_id):
    """Gọi khi dùng một lượt AI. Vượt hạn mức gói → chặn. NGUYÊN TỬ.

    AG-02 tìm ra ở đợt 3, AG-00 đo lại: bản cũ đọc `usage_hien_tai` rồi mới `_tang`, nên
    **28/40 lượt** (16 luồng tranh 1 suất cuối) vượt trần, `so_ai` cao nhất **30 trên trần 20**.

    Đây là CÙNG MỘT LỖI đã vá cho `kiem_va_tang_don` ở r35 (đợt 2) — và nó còn nguyên ở hàm
    ngay bên cạnh, vì lượt vá đó **bỏ bước 4 của §12.2**: *sửa xong hỏi cấu trúc này còn hỏng
    kiểu đó ở đâu nữa?* Bỏ một bước, sót ba chốt. Nay cả bốn chốt dùng chung khuôn, và
    `thu_han_muc_nguyen_tu.py` canh để chốt thứ năm không mọc theo khuôn cũ.
    """
    goi = goi_cua_tenant(tenant_id)
    tran = goi["han_muc_ai_thang"]
    if not _cong_bo_dem_co_tran(tenant_id, "so_ai", tran):
        u = usage_hien_tai(tenant_id)   # đọc lại CHỈ để viết thông điệp
        raise VuotHanMuc(
            f"đã dùng {u['so_ai']}/{tran} lượt AI của gói {goi['ten']} tháng này")


SQL_DEM_NHAN_VIEN = ("SELECT COUNT(*) FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                     " WHERE m.tenant_id=? AND m.trang_thai='hoat_dong'"
                     " AND u.trang_thai='hoat_dong'")
SQL_DEM_TAI_KHOAN_HANG = "SELECT COUNT(*) FROM carrier_accounts WHERE tenant_id=? AND kich_hoat=1"


def chen_membership_co_tran(tenant_id, user_id, role, moi_boi):
    """Thêm thành viên CHỈ KHI chưa đủ trần gói. Nguyên tử. Vượt trần → `VuotHanMuc`.

    Vì sao phải là CHÈN CÓ ĐIỀU KIỆN chứ không phải "kiểm rồi chèn": `kiem_han_muc_nhan_vien`
    chỉ ĐỌC rồi raise, còn câu `INSERT` nằm ở `server.py` — giữa hai bước có khe hở, nên hai
    yêu cầu song song cùng thấy "còn 1 suất" rồi cùng chèn. Phép đo ad-hoc của AG-00 KHÔNG tái
    hiện được chốt này (khoá ghi của SQLite tình cờ che), nhưng **không tái hiện KHÔNG PHẢI là
    an toàn** — cấu trúc vẫn hở, và chốt tài khoản hãng cùng khuôn thì hở thật 12/12 luồng.
    Đưa điều kiện vào chính câu chèn thì CSDL tự so, khe hở không còn tồn tại.
    """
    goi = goi_cua_tenant(tenant_id)
    tran = goi["so_nhan_vien"]
    with csdl.khoa_ghi:
        kn = csdl.mo()
        cur = kn.execute(
            "INSERT INTO tenant_memberships (user_id, tenant_id, role, moi_boi, tao_luc)"
            f" SELECT ?,?,?,?,? WHERE ({SQL_DEM_NHAN_VIEN}) < ?",
            (user_id, tenant_id, role, moi_boi, csdl.bay_gio(), tenant_id, tran))
        duoc, mid = cur.rowcount == 1, cur.lastrowid
        kn.commit()
    if not duoc:
        raise VuotHanMuc(f"gói {goi['ten']} chỉ cho {tran} tài khoản nhân viên")
    return mid


def chen_tai_khoan_hang_co_tran(tenant_id, hang, ten, moi_truong, cred_ma_hoa,
                                cred_duoi, webhook_ma, webhook_secret_ma_hoa):
    """Thêm tài khoản hãng CHỈ KHI chưa đủ trần gói. Nguyên tử. Vượt trần → `VuotHanMuc`.

    Chốt này hở THẬT và nặng nhất trong bốn chốt: AG-00 đo được **12/12 luồng qua, 12 tài khoản
    hãng trên trần 1** của gói Miễn phí. Hậu quả không chỉ là lách hạn mức — mỗi tài khoản hãng
    là một bộ credentials được mã hoá và một cửa webhook, nên lách ở đây là MỞ THÊM CỬA.
    """
    goi = goi_cua_tenant(tenant_id)
    tran = goi["so_tai_khoan_hang"]
    with csdl.khoa_ghi:
        kn = csdl.mo()
        cur = kn.execute(
            "INSERT INTO carrier_accounts (tenant_id, hang, ten, moi_truong, credentials_ma_hoa,"
            " credentials_duoi, webhook_ma, webhook_secret_ma_hoa, tao_luc)"
            f" SELECT ?,?,?,?,?,?,?,?,? WHERE ({SQL_DEM_TAI_KHOAN_HANG}) < ?",
            (tenant_id, hang, ten, moi_truong, cred_ma_hoa, cred_duoi, webhook_ma,
             webhook_secret_ma_hoa, csdl.bay_gio(), tenant_id, tran))
        duoc, id_moi = cur.rowcount == 1, cur.lastrowid
        kn.commit()
    if not duoc:
        raise VuotHanMuc(f"gói {goi['ten']} chỉ cho {tran} kết nối hãng")
    return id_moi


def hoan_ai(tenant_id):
    """Hoàn một lượt AI đã trừ, khi nhà cung cấp KHÔNG trả được kết quả.

    AG-04 đề xuất: `kiem_va_tang_ai` trừ suất TRƯỚC khi gọi nhà cung cấp. Nhà cung cấp lỗi
    thì suất đã mất. Ở chế độ mock không tốn tiền nên chưa đau; nối thật rồi thì **một chuỗi
    lỗi ăn hết hạn mức tháng của tenant** mà tenant không nhận được gì.

    Cùng khuôn `hoan_don`: không cho `so_ai` xuống âm — trừ nhiều hơn số đã cộng là dấu hiệu
    lỗi logic ở chỗ khác, và che nó bằng một số âm thì sau này không ai dựng lại được.

    CHỈ hoàn khi biết CHẮC nhà cung cấp không làm gì (lỗi mạng, từ chối rõ ràng). Lượt
    timeout **KHÔNG được hoàn**: lúc đó mình không biết nhà cung cấp đã tính phí chưa — cùng
    lý do `gui_don` không hoàn suất khi hãng timeout.
    """
    thang = csdl.thang_nay()
    with csdl.khoa_ghi:
        kn = csdl.mo()
        cur = kn.execute("UPDATE usage_thang SET so_ai=so_ai-1"
                         " WHERE tenant_id=? AND thang=? AND so_ai >= 1", (tenant_id, thang))
        kn.commit()
    return cur.rowcount == 1


def kiem_han_muc_nhan_vien(tenant_id):
    goi = goi_cua_tenant(tenant_id)
    so = csdl.mot("SELECT COUNT(*) c FROM tenant_memberships m JOIN users u ON u.id=m.user_id"
                  " WHERE m.tenant_id=? AND m.trang_thai='hoat_dong' AND u.trang_thai='hoat_dong'",
                  (tenant_id,))["c"]
    if so >= goi["so_nhan_vien"]:
        raise VuotHanMuc(f"gói {goi['ten']} chỉ cho {goi['so_nhan_vien']} tài khoản nhân viên")


def kiem_han_muc_tai_khoan_hang(tenant_id):
    goi = goi_cua_tenant(tenant_id)
    so = csdl.mot("SELECT COUNT(*) c FROM carrier_accounts WHERE tenant_id=? AND kich_hoat=1", (tenant_id,))["c"]
    if so >= goi["so_tai_khoan_hang"]:
        raise VuotHanMuc(f"gói {goi['ten']} chỉ cho {goi['so_tai_khoan_hang']} kết nối hãng")
