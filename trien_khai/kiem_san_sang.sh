#!/bin/sh
# Cổng READINESS gọi TỪ NGOÀI tiến trình, qua HTTP thật. AG-05 DEVOPS sở hữu file này.
#
# ====== VÌ SAO PHẢI GỌI TỪ NGOÀI ======
# §12.1 luật 1: thứ dùng để kiểm chứng phải ĐỘC LẬP với thứ được kiểm chứng. Ca đã xảy ra thật
# trong vault chủ dự án: bước nghiệm thu của một bộ cài TỰ CHẠY HỘ bằng shell có sẵn quyền nên
# LUÔN báo đạt, che mất việc bộ lập lịch không chạy nổi.
# Áp vào đây: gọi `python3 app/quan_sat.py san-sang` trên máy chủ KHÔNG kiểm chứng được rằng
# *máy chủ web đang chạy đã sẵn sàng* — nó chỉ kiểm chứng rằng *một tiến trình Python mới dựng
# lên thì sẵn sàng*. Hai thứ khác nhau: tiến trình web có thể đang giữ một kết nối SQLite hỏng,
# đang bị treo thread, đang chạy mã của bản deploy TRƯỚC.
# Nên cổng này đi qua HTTP tới đúng tiến trình đang phục vụ.
#
# Dùng: sh trien_khai/kiem_san_sang.sh [URL_GOC] [SO_LAN_THU]
# Mã thoát: 0 = sẵn sàng · 1 = trả lời nhưng CHƯA sẵn sàng · 2 = không gọi được · 3 = sai cách dùng
set -eu

GOC_URL="${1:-http://127.0.0.1:8897}"
SO_LAN="${2:-10}"
case "$SO_LAN" in ''|*[!0-9]*) echo "SO_LAN_THU phai la so" >&2; exit 3;; esac

i=0
while [ "$i" -lt "$SO_LAN" ]; do
    i=$((i+1))
    # `-sS` im lặng nhưng vẫn hiện lỗi; `-w` lấy mã HTTP. Không `-f`: ta CẦN đọc body của 503
    # để biết phép kiểm nào hỏng — `-f` sẽ bỏ body đi và biến một chẩn đoán đầy đủ thành
    # "exit code 22", đúng kiểu mất thông tin mà §12.2 bước 1 nói (đừng tin thông báo lỗi).
    ra=$(curl -sS -m 10 -o /tmp/san-sang.$$ -w '%{http_code}' \
         -H 'X-Requested-With: VIPHub' "$GOC_URL/api/v2/san-sang" 2>/dev/null) || ra=000
    body=$(cat /tmp/san-sang.$$ 2>/dev/null || true)
    rm -f /tmp/san-sang.$$
    case "$ra" in
        200)
            echo "SAN SANG (HTTP 200) sau $i luot thu"
            echo "$body"
            exit 0 ;;
        503)
            echo "CHUA SAN SANG (HTTP 503) luot $i/$SO_LAN:"
            echo "$body"
            ;;
        404)
            # Nói thẳng chứ không thử lại 10 lần rồi báo "không sẵn sàng": nguyên nhân khác hẳn.
            echo "KHONG CO duong /api/v2/san-sang (HTTP 404)." >&2
            echo "Route nay CHUA DUOC CAM — AG-00 giu server.py. Xem bang route trong" >&2
            echo "docs/G11_FINAL_REPORT.md muc 'BAN VA DE XUAT P-2'." >&2
            exit 2 ;;
        000)
            echo "khong goi duoc $GOC_URL (luot $i/$SO_LAN)" ;;
        *)
            echo "HTTP $ra (luot $i/$SO_LAN): $body" ;;
    esac
    sleep 2
done
echo "HET $SO_LAN LUOT — van chua san sang" >&2
exit 1
