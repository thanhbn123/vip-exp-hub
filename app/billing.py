# G10 — Billing: gói dịch vụ, hạn mức, usage. ĐO TỪ BACKEND — không tin số liệu frontend.
# Chưa nối thanh toán thật (chờ Owner duyệt); chỉ gói/hạn mức/usage/lịch sử.
import csdl


class VuotHanMuc(Exception):
    pass


def goi_cua_tenant(tenant_id):
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
    """Gọi khi GỬI đơn sang hãng. Vượt hạn mức gói → chặn."""
    goi = goi_cua_tenant(tenant_id)
    u = usage_hien_tai(tenant_id)
    if u["so_don"] >= goi["han_muc_don_thang"]:
        raise VuotHanMuc(
            f"đã dùng {u['so_don']}/{goi['han_muc_don_thang']} đơn của gói {goi['ten']} tháng này")
    _tang(tenant_id, "so_don")


def kiem_va_tang_ai(tenant_id):
    goi = goi_cua_tenant(tenant_id)
    u = usage_hien_tai(tenant_id)
    if u["so_ai"] >= goi["han_muc_ai_thang"]:
        raise VuotHanMuc(
            f"đã dùng {u['so_ai']}/{goi['han_muc_ai_thang']} lượt AI của gói {goi['ten']} tháng này")
    _tang(tenant_id, "so_ai")


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
