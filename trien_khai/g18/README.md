# `trien_khai/g18/` — MÁY CHỦ HTTP THẬT DƯỚI TẢI (G18, làn AG-04)

Đóng lỗ hổng **`V-13914(b)`** trong `docs/BAN_GIAO.md` §6.1: *"máy chủ HTTP thật **dưới tải**"*
— chưa ai đo, vì mọi bàn đo trước đây **gọi thẳng hàm nghiệp vụ**, không đi qua
`ThreadingHTTPServer`. Báo cáo đầy đủ: `docs/G18_HTTP_SERVER.md`.

| Tệp | Việc |
|---|---|
| `chot_an_toan.py` | **Mười hai chốt an toàn**, và harness TỪ CHỐI CHẠY nếu mất một chốt. Bảy chốt **mượn nguyên** của G17 (nạp theo đường dẫn, không chép lại — chép là tạo hai nguồn sự thật cho cùng một bất biến); năm chốt riêng của G18: số tiến trình · bind của **từng** tiến trình · không dính PostgreSQL · cấm `pkill`/`killall` · nền tách khỏi G17. Có `--tu-kiem` trên **14 cấu hình tổng hợp** |
| `harness_tai.py` | Kịch bản **G18-00 … G18-08** qua HTTP thật, **hai tiến trình** `server.py` trên cùng một CSDL tạm, cổng **0** trên `127.0.0.1`. Kèm **bộ đo tải** đóng vòng và **bộ phán quyết trần**. Phán quyết: `ĐẠT` · `ĐẠT (MOCK)` · `HỎNG` · `BLOCKED` · `BỎ QUA` |
| `tiem_loi.py` | **Chứng minh ngược**: tiêm lỗi vào chính bộ đo (làm nó mù với 5xx, với lỗi kết nối, và làm bộ phán quyết trần luôn trả ĐẠT) rồi đòi bộ tự kiểm phải **ĐỎ**. Không có tệp này thì dòng *"8/8 ca tự kiểm đạt"* không có giá trị |
| `chay_harness.sh` | Bộ chạy: bốn tầng tự kiểm → dựng nền riêng → chạy → tắt máy chủ theo **ĐÚNG PID** |

```bash
sh trien_khai/g18/chay_harness.sh              # chạy đầy đủ
sh trien_khai/g18/chay_harness.sh --giu-nen    # giữ nền để soi
python3 trien_khai/g18/chot_an_toan.py --tu-kiem     # 14 cấu hình chốt an toàn
python3 trien_khai/g18/harness_tai.py  --tu-kiem     # bộ đo + bộ phán quyết trần
python3 trien_khai/g18/tiem_loi.py                   # chứng minh ngược
python3 app/thu/thu_g18_maysrv.py                    # bộ hồi quy (17 ca, ~6 giây)
```

Báo cáo máy đọc được: `$VIP_HUB_DATA/bao-cao-g18.json`.

## Bốn tầng tự kiểm, và vì sao phải đủ bốn

Một bộ đo **không phân biệt được** máy chủ lành với máy chủ hỏng thì mọi con số nó in ra là số đo
của chính nó. Và một bộ tự kiểm **luôn in "đạt"** thì dòng "đạt" ấy không có nghĩa. Nên:

1. **chốt an toàn** — 14 cấu hình tổng hợp, mỗi cấu hình hỏng phải bị bắt bởi **đúng** chốt;
2. **bộ đo tải** — bắn vào máy chủ giả lành (phải 0 lỗi) và máy chủ giả hỏng (phải thấy 5xx, phải
   thấy lỗi kết nối, và **0 yêu cầu thì KHÔNG được coi là lành**);
3. **bộ phán quyết trần** — một chuỗi mã trạng thái ĐÚNG và ba dạng SAI (không chặn · chặn rồi cho
   qua lại · chặn sớm hơn khai báo);
4. **chứng minh ngược** (`tiem_loi.py`) — tầng duy nhất chứng minh ba tầng trên **ĐỎ ĐƯỢC**.

## Ba loại phán quyết, và loại thứ ba

`BLOCKED` **không bao giờ được tính là đạt** — nó mang theo chính xác cái còn thiếu. `BỎ QUA` cũng
vậy, và lượt này có **hai** ca `BỎ QUA` nói thẳng ra hai chỗ **không đo được** thay vì giấu chúng
vào một ô "đạt": CPU time (`ps` bị sandbox chặn) và một quan sát về tiến trình thứ hai chưa đủ
chặt để gọi là lỗi.

## Vì sao mọi phép đo đi qua stub / `mock`

`V-G09-01` (gọi API hãng, kể cả sandbox) và `V-13906-05` (credentials sandbox J&T) **CHƯA CẤP**.
Adapter là **MOCK**; không một lượt nào ra khỏi loopback. Hai tiến trình máy chủ bind
`127.0.0.1` **cổng 0** (hệ điều hành cấp) — không mở cổng, không tunnel, không deploy.

## Dọn dẹp

Máy chủ do harness spawn được tắt bằng `terminate()` → `kill()` theo **đúng PID**, và PID được ghi
ra `$NEN/hub.pid` (nhiều dòng — lượt này spawn hai tiến trình) để `trap` của `chay_harness.sh` hứng
được nếu harness chết giữa đường. **Không có `pkill`/`killall`**, và điều đó được **canh bằng máy**:
chốt `G18-11` quét chính mã của thư mục này. Trên máy nhiều làn, `pkill -f server.py` giết cả máy
chủ của làn khác — một lệnh dọn tay làm hỏng lượt của người khác, và không có gì báo.
