# `trien_khai/g17/` — HARNESS WEBHOOK: REPLAY CÓ UỶ QUYỀN + CHỐNG TRÙNG Ở TẦNG CSDL (G17, làn AG-04)

| Tệp | Việc |
|---|---|
| `chot_an_toan.py` | **Bảy chốt an toàn**. Harness TỪ CHỐI CHẠY nếu mất một chốt. Có `--tu-kiem`: chạy bộ dò trên **12 cấu hình tổng hợp** (1 đủ chốt + 11 hỏng), mỗi ca hỏng phải bị bắt bởi **đúng chốt** |
| `harness_webhook.py` | Kịch bản **G17-00 … G17-16** qua HTTP thật trên `127.0.0.1` (máy chủ bind **cổng 0**), CSDL **tạm**, adapter **MOCK**, callback đi qua **stub cổng 0**. Phán quyết: `ĐẠT` · `ĐẠT (MOCK)` · `HỎNG` · `BLOCKED` |
| `chay_harness.sh` | Bộ chạy: tự kiểm chốt + tự kiểm bộ đếm → dựng nền riêng → chạy → tắt máy chủ theo **ĐÚNG PID** |

```bash
sh trien_khai/g17/chay_harness.sh              # chạy đầy đủ
sh trien_khai/g17/chay_harness.sh --giu-nen    # giữ nền để soi
python3 trien_khai/g17/chot_an_toan.py --tu-kiem
python3 trien_khai/g17/harness_webhook.py --tu-kiem   # chỉ tự kiểm, không dựng gì
```

Báo cáo máy đọc được: `$VIP_HUB_DATA/g17_harness/bao-cao-g17.json`.

## Ba loại phán quyết, và loại thứ ba

`BLOCKED` **không bao giờ được tính là đạt**. Nó mang theo **chính xác cái còn thiếu** — với lượt
này là `V-G09-01` (gọi API hãng, kể cả sandbox) + `V-13906-05` (credentials sandbox J&T), cộng
câu 24 và câu 6–7 gửi hãng (sandbox có đẩy callback không · khoá ký + chuỗi đem đi ký). Bộ đếm
`dem_phuong_an()` xếp `BLOCKED` một ô riêng, và `harness_webhook.py --tu-kiem` tự kiểm chính bộ
đếm đó — một bộ đếm gộp `BLOCKED` vào ô "đạt" thì bảng tổng kết vẫn xanh trong khi chặng chạm
hãng chưa từng chạy.

## Vì sao có stub riêng

Mọi phép đo lớp HTTP của lượt này đi qua `StubHang` — một máy chủ HTTP bind `127.0.0.1` **cổng 0**
đóng vai bên gửi của hãng. Stub giữ bí mật ký trong bộ nhớ tiến trình (bí mật không đi qua HTTP,
không vào log) và có **chốt loopback riêng**: đích không phải loopback thì nó từ chối chuyển tiếp,
kể cả khi ai đó đã sửa chốt của harness. Hai chốt độc lập cho cùng một bất biến.

## Dọn dẹp

Máy chủ do harness spawn được tắt bằng `sv.terminate()` → `sv.kill()` theo **đúng PID**, và PID
được ghi ra `$NEN/hub.pid` để `trap` của `chay_harness.sh` hứng được nếu harness chết giữa đường.
**Không có `pkill`/`killall` ở bất kỳ đâu** — trên máy nhiều làn, `pkill -f server.py` giết cả máy
chủ của làn khác.

Đọc kèm: `docs/G17_WEBHOOK.md` (báo cáo lượt chạy: lệnh, mã thoát, số ca, phạm vi).
