# G09 — AI Integration Gateway. VIP AI Brain là HỆ THỐNG ĐỘC LẬP — không xây lại ở đây.
# File này chỉ là interface + MOCK service. Mọi hàm đều:
#   - chạy sau auth + tenant isolation (server truyền tenant_id từ phiên, không từ client),
#   - tính usage AI qua billing (đo backend),
#   - CHỈ TRẢ GỢI Ý — không tự tạo đơn, không gọi carrier API; tạo đơn thật phải đi qua
#     Order Service + approval workflow như mọi người dùng khác.
import re

import billing

MOCK = True  # VIP AI Brain chưa nối — toàn bộ kết quả là mô phỏng và được gắn nhãn


def _goi(tenant_id):
    billing.kiem_va_tang_ai(tenant_id)


def chuan_hoa_dia_chi(tenant_id, dia_chi: str):
    _goi(tenant_id)
    # MOCK: chỉ dọn khoảng trắng + viết hoa chữ đầu; bản thật sẽ gọi VIP AI Brain qua service contract.
    sach = re.sub(r"\s+", " ", dia_chi or "").strip()
    return {"mock": True, "dia_chi_goc": dia_chi, "dia_chi_chuan": sach,
            "do_tin_cay": "mô phỏng — chưa phải AI thật"}


def phat_hien_bat_thuong(tenant_id, don: dict):
    _goi(tenant_id)
    canh_bao = []
    if int(don.get("cod") or 0) > 5_000_000:
        canh_bao.append("COD lớn hơn 5 triệu — nên xác nhận lại với khách")
    if int(don.get("khoi_luong_gram") or 0) > 20_000:
        canh_bao.append("kiện nặng hơn 20kg — kiểm tra hãng có nhận không")
    return {"mock": True, "canh_bao": canh_bao}


def goi_y_hang(tenant_id, don: dict):
    _goi(tenant_id)
    kl = int(don.get("khoi_luong_gram") or 0)
    goi_y = "vtp" if kl <= 2000 else "jt"
    return {"mock": True, "goi_y": goi_y,
            "ly_do": "mô phỏng theo cân nặng — bản thật sẽ dùng dữ liệu giá/chất lượng từng tuyến",
            "luu_y": "chỉ là gợi ý; việc chọn hãng và tạo đơn vẫn qua duyệt của người dùng"}
