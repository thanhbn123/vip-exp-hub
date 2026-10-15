# `trien_khai/g16/` — HARNESS NGHIỆM THU SANDBOX (G16-A, làn AG-04)

| Tệp | Việc |
|---|---|
| `chot_an_toan.py` | **Sáu chốt an toàn**. Harness TỪ CHỐI CHẠY nếu mất một chốt. Có `--tu-kiem`: chạy bộ dò trên **10 cấu hình tổng hợp** (1 đủ chốt + 9 hỏng), mỗi ca hỏng phải bị bắt bởi **đúng chốt** |
| `harness_nghiem_thu.py` | Kịch bản **G01–G11** qua HTTP thật trên `127.0.0.1`, CSDL **tạm**, adapter **MOCK**. Phán quyết ba loại: `ĐẠT` · `ĐẠT (MOCK)` · `BLOCKED` |
| `chay_harness.sh` | Bộ chạy: tự kiểm chốt → dựng nền riêng → chạy → tắt máy chủ theo **ĐÚNG PID** |

```bash
sh trien_khai/g16/chay_harness.sh              # chạy đầy đủ
sh trien_khai/g16/chay_harness.sh --giu-nen    # giữ nền để soi
python3 trien_khai/g16/chot_an_toan.py --tu-kiem
```

Báo cáo máy đọc được: `$VIP_HUB_DATA/g16_harness/bao-cao-g16.json`.

**Không gọi hãng thật, kể cả sandbox** (`V-G09-01` + `V-13906-05` CHƯA CẤP) · **không mở cổng ra
Internet** (`V-G11-01` chưa cấp) · **không tạo đơn vận chuyển thật**.

Đọc kèm: `docs/G16_SANDBOX_HARNESS.md` (harness) và `docs/G16_WEBHOOK.md` (hợp đồng callback).
