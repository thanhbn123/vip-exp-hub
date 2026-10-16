# `trien_khai/g20-dahang/` — làn AG-06 (G20 · ĐÃ HÃNG)

Đo xem lớp HTTP thật `app/http_jt.py` (viết ở G16 cho **riêng** J&T) có **dùng lại được** cho hãng
chuyển phát thứ hai hay không. Kết luận + số đo đầy đủ: **`docs/G20_DA_HANG.md`**.

> ⚠️ **"HÃNG GIẢ MẪU" (`hang-gia-mau`) là hãng BỊA do AG-06 tự đặt ra. Nó KHÔNG tồn tại.**
> Mọi tên trường, đường dẫn, tên host và công thức chữ ký trong thư mục này là **BỊA có chủ ý** —
> không chép, không suy đoán từ API thật của bất kỳ hãng nào. Tên host dùng đuôi `.invalid`
> (RFC 6761 §6.4 — không bao giờ phân giải được) làm chốt chặn thứ hai, độc lập với danh sách trắng.
> **Không có credential thật nào ở đây**, và **không lượt gọi hãng nào** được thực hiện.

## Ba tệp

| tệp | là gì |
|---|---|
| `stub_hang_gia.py` | Máy chủ **HÃNG GIẢ MẪU** — chỉ bind `127.0.0.1` + cổng `0` (hệ điều hành cấp). Ghi lại **thân thô + header nguyên văn** của từng lượt nhận, nên bộ thử đo **đúng những byte đã gửi đi**, không đo bản mô tả của chúng |
| `phan_tich_gan_chat.py` | Bộ dò **ranh giới chung/đặc thù** bằng AST trên `app/http_jt.py`. In 5 bảng bằng chứng; `--json` ghi kết quả máy đọc được. Chỉ **ĐỌC** — không import `http_jt`, không mở socket |
| `bang_chung_ast.txt` · `bang_chung_ast.json` | Bằng chứng AST của lượt chạy gần nhất |

## Chạy lại mọi phép đo

Từ **gốc dự án**:

```sh
# 1. Bộ dò ranh giới (AST) — exit 0
python3 trien_khai/g20-dahang/phan_tich_gan_chat.py

# 2. Bộ đo AG-06 — 27 ca, exit 0
PYTHONPATH=app:app/thu:trien_khai/g20-dahang python3 app/thu/thu_g20_dahang.py

# 3. ĐỐI CHỨNG ĐƯỜNG: bộ thử J&T của G16 — phải vẫn 57 ca, exit 0
#    (đã chạy sẵn bên trong ca `CaDoiChungDuong.test_d2`)
PYTHONPATH=app:app/thu python3 app/thu/thu_http_jt.py

# 4. BẰNG CHỨNG TRUNG TÂM: `http_jt.py` không bị sửa — hai hash phải TRÙNG nhau
sha256sum app/http_jt.py
git hash-object app/http_jt.py && git rev-parse HEAD:app/http_jt.py
```

Môi trường git của phiên này có `GIT_CONFIG_COUNT` nhưng **thiếu** `GIT_CONFIG_KEY_*`, làm **mọi**
lệnh git thoát 128 (N-G18-00). Nếu gặp, gỡ gia đình biến đó trước:

```sh
unset GIT_CONFIG_COUNT GIT_CONFIG_VALUE_0 GIT_CONFIG_VALUE_1
```

## Ba chốt an toàn

1. **Chỉ loopback.** `app/thu/thu_g20_dahang.py` thay `socket.socket.connect` bằng chốt chặn chỉ cho
   `127.0.0.1`/`localhost`/`::1` đi qua, **cộng máy đếm**. Một URL gõ sai làm ca thử **NỔ NGAY**,
   chứ không lặng lẽ thành một lượt gọi ra Internet. Ca `e1` tự kiểm chính chốt chặn đó.
2. **Cổng 0.** Cả hai stub bind `127.0.0.1` + cổng do hệ điều hành cấp ⇒ nhiều làn chạy song song
   không đụng nhau, và **không mở cổng ra ngoài**.
3. **Không bí mật thật.** Ba "khoá" trong `stub_hang_gia.py` là chuỗi bịa sống trong tiến trình —
   chúng tồn tại **đúng để** phép đo rò rỉ biết chính xác chuỗi cần tìm.

## Hai luật phân loại ĐÃ THỬ và ĐÃ BỎ

Ghi lại để người sau không viết lại chúng — cả hai đều **báo sai**, và cả hai đều có ca tự kiểm
chặn không cho quay lại (`CaTuKiem`):

| luật đã bỏ | nó báo sai thế nào |
|---|---|
| "Hằng nào được cùng hàm đọc với một hằng đặc thù thì cũng là đặc thù" | Nuốt `DAI_TOI_THIEU_DE_CHE = 8` — một ngưỡng **hoàn toàn chung** — chỉ vì nó nằm cạnh `TRUONG_CREDENTIAL` trong `_dang_che`. Nay "chỗ dùng bị ràng buộc hãng" được ghi **riêng**, đo ở **chỗ dùng** |
| "Tham số nào có tên chứa `host`/`danh_sach`/`credential` là ĐIỂM TIÊM" | Gọi `host_duoc_phep(host)` là điểm tiêm — nhưng `host` chính là **GIÁ TRỊ ĐANG BỊ KIỂM**, không phải cái bảng. Một bảng dò theo **cái tên** là một bảng **đoán** |
| "Tên bảng xuất hiện ở đâu trong đối số của hàm nội bộ là bị TRAO đi" | Báo `HOST_HANG` "có điểm tiêm" ở dòng 731 — nơi nó chỉ được `', '.join(...)` để **in ra thông điệp**. Nay có **rào chắn** ở `Call`/`JoinedStr`: một lời gọi lồng trên đường đi nghĩa là bảng đã bị **tiêu thụ**, không được trao cho ai giữ |

Và một luật nữa ở tầng **đếm**, cùng khuôn: bản đầu tính **cả docstring** vào "nhãn hiệu hãng lộ
trong thông điệp" và báo **10 dòng** trong khi thực tế chỉ **4**. Docstring là literal trong cây cú
pháp nhưng **không bao giờ** được in ra cho ai — đúng bài học `thu_bien_driver.py` ca a4 ("grep đọc
cả chú thích") lặp lại ở tầng AST.

## Phạm vi

**Đo được:** lớp HTTP dùng lại được cho một hãng thứ hai **cùng khuôn giao thức**; ranh giới
chung/đặc thù; hai chỗ gắn chặt và hệ quả của chúng.

**KHÔNG đo được:** hành vi thật của J&T (V-G09-01/V-13906-05 **CHƯA CẤP** — chưa từng có lượt gọi
hãng nào); hành vi thật của bất kỳ hãng thứ hai **có thật** nào; ánh xạ mã lỗi/trạng thái của hãng
thứ hai (**D-4**: mã chưa xác minh ⇒ `NEEDS_REVIEW`, **không đoán**); tầng nghiệp vụ (đối soát, tính
phí, in nhãn).

**Bộ thử XANH ở đây KHÔNG phải lời cho phép gọi sandbox, và KHÔNG được đọc thành `LIVE VERIFIED`.**
