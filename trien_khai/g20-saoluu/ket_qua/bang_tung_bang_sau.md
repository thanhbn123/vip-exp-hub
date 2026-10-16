# BẢNG SỐ DÒNG + TỔNG TIỀN TỪNG BẢNG

Nguồn: `/Users/viporder/orca/workspaces/vip-express-hub/g21-ag02-backup/trien_khai/g20-saoluu/ket_qua/sau.json` · `app/` đang đo: `/var/folders/v1/443y_fys65vflj24_rjw9x_w0000gn/T/g21-chaydo-p_9v3dkt/app-ban-va`

Mỗi bảng dưới đây là một dòng của phép chụp ĐẦY ĐỦ (`khung_do.chup`), không phải bản
tóm tắt. Cột **Tiền** là tổng MỌI cột tiền của bảng đó (`khung_do.COT_TIEN`).

### S1 · 1. SAO LƯU BỊ CẮT GIỮA ĐƯỜNG (5 cách cắt)

`rc=0` · phán quyết **FAIL_CLOSED**

_Kịch bản này không giữ phép chụp đầy đủ (chỉ có bản tóm tắt: `{"ton_tai": false}`)._

### S2 · 2. TỆP SAO LƯU BỊ SỬA 1 BYTE (5 chỗ)

`rc=0` · phán quyết **FAIL_CLOSED**

_Kịch bản này không giữ phép chụp đầy đủ (chỉ có bản tóm tắt: `{"ton_tai": false}`)._

### S3 · 3. TỆP SAO LƯU RỖNG 0 BYTE

`rc=1` · phán quyết **FAIL_CLOSED**

| Bảng | Số dòng TRƯỚC | Số dòng SAU | Tiền TRƯỚC | Tiền SAU | Kết |
|---|---|---|---|---|---|
| `ai_job` | 0 | 0 | 0 | 0 | khớp |
| `ai_su_kien` | 0 | 0 | 0 | 0 | khớp |
| `audit` | 4 | 4 | 0 | 0 | khớp |
| `bo_dem_dung` | 0 | 0 | 0 | 0 | khớp |
| `carrier_accounts` | 5 | 5 | 0 | 0 | khớp |
| `carrier_providers` | 2 | 2 | 0 | 0 | khớp |
| `dang_ky` | 2 | 2 | 0 | 0 | khớp |
| `dang_ky_lich_su` | 2 | 2 | 0 | 0 | khớp |
| `don_hang` | 15 | 15 | 9870000 | 9870000 | khớp |
| `don_lich_su` | 30 | 30 | 0 | 0 | khớp |
| `don_mat_hang` | 0 | 0 | 0 | 0 | khớp |
| `ds_anh_xa_cot` | 0 | 0 | 0 | 0 | khớp |
| `ds_chenh_lech` | 0 | 0 | 0 | 0 | khớp |
| `ds_dong` | 15 | 15 | 330000 | 330000 | khớp |
| `ds_dot` | 3 | 3 | 0 | 0 | khớp |
| `du_thao_hoa_don` | 2 | 2 | 598000 | 598000 | khớp |
| `g09_harness_ca` | 0 | 0 | 0 | 0 | khớp |
| `g09_harness_lan_chay` | 0 | 0 | 0 | 0 | khớp |
| `gioi_han_chan` | 0 | 0 | 0 | 0 | khớp |
| `gioi_han_luot` | 0 | 0 | 0 | 0 | khớp |
| `goi_dich_vu` | 3 | 3 | 1298000 | 1298000 | khớp |
| `goi_phien_ban` | 4 | 4 | 2597000 | 2597000 | khớp |
| `han_muc_nhap_thang` | 0 | 0 | 0 | 0 | khớp |
| `han_muc_rieng` | 0 | 0 | 0 | 0 | khớp |
| `import_batch` | 1 | 1 | 0 | 0 | khớp |
| `import_dong` | 3 | 3 | 0 | 0 | khớp |
| `khach_hang` | 6 | 6 | 0 | 0 | khớp |
| `ky_tinh_phi` | 2 | 2 | 0 | 0 | khớp |
| `nhat_ky_tinh_phi` | 5 | 5 | 0 | 0 | khớp |
| `permissions` | 28 | 28 | 0 | 0 | khớp |
| `quan_sat_su_kien` | 0 | 0 | 0 | 0 | khớp |
| `reset_tokens` | 0 | 0 | 0 | 0 | khớp |
| `role_permissions` | 68 | 68 | 0 | 0 | khớp |
| `roles` | 6 | 6 | 0 | 0 | khớp |
| `schema_version` | 1 | 1 | 0 | 0 | khớp |
| `sessions` | 0 | 0 | 0 | 0 | khớp |
| `su_kien_dung` | 0 | 0 | 0 | 0 | khớp |
| `tc_but_toan` | 57 | 57 | 8177000 | 8177000 | khớp |
| `tc_cod` | 15 | 15 | 5936000 | 5936000 | khớp |
| `tc_cod_chuyen` | 12 | 12 | 0 | 0 | khớp |
| `tc_cong_no` | 10 | 10 | 4567000 | 4567000 | khớp |
| `tc_dieu_chinh` | 3 | 3 | -3000 | -3000 | khớp |
| `tc_dot_tt` | 3 | 3 | 424000 | 424000 | khớp |
| `tc_dot_tt_dong` | 3 | 3 | 212000 | 212000 | khớp |
| `tc_nhat_ky` | 24 | 24 | 0 | 0 | khớp |
| `tc_phi` | 15 | 15 | 330000 | 330000 | khớp |
| `tenant_memberships` | 3 | 3 | 0 | 0 | khớp |
| `tenants` | 3 | 3 | 0 | 0 | khớp |
| `usage_thang` | 3 | 3 | 0 | 0 | khớp |
| `users` | 4 | 4 | 0 | 0 | khớp |
| `wh_su_kien` | 10 | 10 | 0 | 0 | khớp |
| **TỔNG (toàn kho)** | 51 | 51 | **34336000** | **34336000** | khớp |

`integrity_check`: ok → ok · `bam_toan_kho`: `e4c124efdd4bb68a` → `e4c124efdd4bb68a` · số bảng LỆCH: **0**

### S4 · 4. KHÔI PHỤC ĐÈ LÊN CSDL ĐÃ CÓ DỮ LIỆU

`rc=0` · phán quyết **FAIL_CLOSED**

_Kịch bản này không giữ phép chụp đầy đủ (chỉ có bản tóm tắt: `{"ton_tai": false}`)._

### S5 · 5. KHÔI PHỤC BẢN SCHEMA THẤP HƠN (v6 đè lên v9)

`rc=1` · phán quyết **FAIL_CLOSED**

_Kịch bản này không giữ phép chụp đầy đủ (chỉ có bản tóm tắt: `{"ton_tai": false}`)._

### S6a · 6a. HẾT ĐĨA GIỮA ĐƯỜNG khi SAO LƯU

`rc=1` · phán quyết **FAIL_CLOSED**

| Bảng | Số dòng TRƯỚC | Số dòng SAU | Tiền TRƯỚC | Tiền SAU | Kết |
|---|---|---|---|---|---|
| `ai_job` | 0 | 0 | 0 | 0 | khớp |
| `ai_su_kien` | 0 | 0 | 0 | 0 | khớp |
| `audit` | 4 | 4 | 0 | 0 | khớp |
| `bo_dem_dung` | 0 | 0 | 0 | 0 | khớp |
| `carrier_accounts` | 5 | 5 | 0 | 0 | khớp |
| `carrier_providers` | 2 | 2 | 0 | 0 | khớp |
| `dang_ky` | 2 | 2 | 0 | 0 | khớp |
| `dang_ky_lich_su` | 2 | 2 | 0 | 0 | khớp |
| `don_hang` | 15 | 15 | 9870000 | 9870000 | khớp |
| `don_lich_su` | 30 | 30 | 0 | 0 | khớp |
| `don_mat_hang` | 0 | 0 | 0 | 0 | khớp |
| `ds_anh_xa_cot` | 0 | 0 | 0 | 0 | khớp |
| `ds_chenh_lech` | 0 | 0 | 0 | 0 | khớp |
| `ds_dong` | 15 | 15 | 330000 | 330000 | khớp |
| `ds_dot` | 3 | 3 | 0 | 0 | khớp |
| `du_thao_hoa_don` | 2 | 2 | 598000 | 598000 | khớp |
| `g09_harness_ca` | 0 | 0 | 0 | 0 | khớp |
| `g09_harness_lan_chay` | 0 | 0 | 0 | 0 | khớp |
| `gioi_han_chan` | 0 | 0 | 0 | 0 | khớp |
| `gioi_han_luot` | 0 | 0 | 0 | 0 | khớp |
| `goi_dich_vu` | 3 | 3 | 1298000 | 1298000 | khớp |
| `goi_phien_ban` | 4 | 4 | 2597000 | 2597000 | khớp |
| `han_muc_nhap_thang` | 0 | 0 | 0 | 0 | khớp |
| `han_muc_rieng` | 0 | 0 | 0 | 0 | khớp |
| `import_batch` | 1 | 1 | 0 | 0 | khớp |
| `import_dong` | 3 | 3 | 0 | 0 | khớp |
| `khach_hang` | 6 | 6 | 0 | 0 | khớp |
| `ky_tinh_phi` | 2 | 2 | 0 | 0 | khớp |
| `nhat_ky_tinh_phi` | 5 | 5 | 0 | 0 | khớp |
| `permissions` | 28 | 28 | 0 | 0 | khớp |
| `quan_sat_su_kien` | 0 | 0 | 0 | 0 | khớp |
| `reset_tokens` | 0 | 0 | 0 | 0 | khớp |
| `role_permissions` | 68 | 68 | 0 | 0 | khớp |
| `roles` | 6 | 6 | 0 | 0 | khớp |
| `schema_version` | 1 | 1 | 0 | 0 | khớp |
| `sessions` | 0 | 0 | 0 | 0 | khớp |
| `su_kien_dung` | 0 | 0 | 0 | 0 | khớp |
| `tc_but_toan` | 57 | 57 | 8177000 | 8177000 | khớp |
| `tc_cod` | 15 | 15 | 5936000 | 5936000 | khớp |
| `tc_cod_chuyen` | 12 | 12 | 0 | 0 | khớp |
| `tc_cong_no` | 10 | 10 | 4567000 | 4567000 | khớp |
| `tc_dieu_chinh` | 3 | 3 | -3000 | -3000 | khớp |
| `tc_dot_tt` | 3 | 3 | 424000 | 424000 | khớp |
| `tc_dot_tt_dong` | 3 | 3 | 212000 | 212000 | khớp |
| `tc_nhat_ky` | 24 | 24 | 0 | 0 | khớp |
| `tc_phi` | 15 | 15 | 330000 | 330000 | khớp |
| `tenant_memberships` | 3 | 3 | 0 | 0 | khớp |
| `tenants` | 3 | 3 | 0 | 0 | khớp |
| `usage_thang` | 3 | 3 | 0 | 0 | khớp |
| `users` | 4 | 4 | 0 | 0 | khớp |
| `wh_su_kien` | 10 | 10 | 0 | 0 | khớp |
| **TỔNG (toàn kho)** | 51 | 51 | **34336000** | **34336000** | khớp |

`integrity_check`: ok → ok · `bam_toan_kho`: `2d4c16cfa910ac1a` → `2d4c16cfa910ac1a` · số bảng LỆCH: **0**

### S6b · 6b. HẾT ĐĨA GIỮA ĐƯỜNG khi KHÔI PHỤC

`rc=1` · phán quyết **FAIL_CLOSED**

| Bảng | Số dòng TRƯỚC | Số dòng SAU | Tiền TRƯỚC | Tiền SAU | Kết |
|---|---|---|---|---|---|
| `audit` | 0 | 0 | 0 | 0 | khớp |
| `carrier_accounts` | 0 | 0 | 0 | 0 | khớp |
| `carrier_providers` | 0 | 0 | 0 | 0 | khớp |
| `don_hang` | 0 | 0 | 0 | 0 | khớp |
| `don_lich_su` | 0 | 0 | 0 | 0 | khớp |
| `goi_dich_vu` | 3 | 3 | 1298000 | 1298000 | khớp |
| `import_batch` | 0 | 0 | 0 | 0 | khớp |
| `import_dong` | 0 | 0 | 0 | 0 | khớp |
| `khach_hang` | 0 | 0 | 0 | 0 | khớp |
| `permissions` | 0 | 0 | 0 | 0 | khớp |
| `reset_tokens` | 0 | 0 | 0 | 0 | khớp |
| `role_permissions` | 0 | 0 | 0 | 0 | khớp |
| `roles` | 0 | 0 | 0 | 0 | khớp |
| `schema_version` | 0 | 0 | 0 | 0 | khớp |
| `sessions` | 0 | 0 | 0 | 0 | khớp |
| `tenant_memberships` | 0 | 0 | 0 | 0 | khớp |
| `tenants` | 0 | 0 | 0 | 0 | khớp |
| `usage_thang` | 0 | 0 | 0 | 0 | khớp |
| `users` | 0 | 0 | 0 | 0 | khớp |
| `wh_su_kien` | 0 | 0 | 0 | 0 | khớp |
| **TỔNG (toàn kho)** | 20 | 20 | **1298000** | **1298000** | khớp |

`integrity_check`: ok → ok · `bam_toan_kho`: `9ed8acc637acb9d4` → `9ed8acc637acb9d4` · số bảng LỆCH: **0**

### S7 · 7. KHÔI PHỤC NHẦM TỆP KHÔNG PHẢI SQLITE (bản dump PostgreSQL)

`rc=1` · phán quyết **FAIL_CLOSED**

_Kịch bản này không giữ phép chụp đầy đủ (chỉ có bản tóm tắt: `{"ton_tai": false}`)._

### S8 · 8. POSTGRESQL: `sao_luu()` có phải đường lùi THẬT không (P-G15-02)

`rc=1` · phán quyết **FAIL_CLOSED**

_Kịch bản này không giữ phép chụp đầy đủ (chỉ có bản tóm tắt: `{"ton_tai": false}`)._

### DC · ĐC. ĐỐI CHỨNG ĐƯỜNG — sao lưu rồi khôi phục lại chính CSDL gốc

`rc=0` · phán quyết **FAIL_CLOSED**

| Bảng | Số dòng TRƯỚC | Số dòng SAU | Tiền TRƯỚC | Tiền SAU | Kết |
|---|---|---|---|---|---|
| `ai_job` | 0 | 0 | 0 | 0 | khớp |
| `ai_su_kien` | 0 | 0 | 0 | 0 | khớp |
| `audit` | 4 | 4 | 0 | 0 | khớp |
| `bo_dem_dung` | 0 | 0 | 0 | 0 | khớp |
| `carrier_accounts` | 5 | 5 | 0 | 0 | khớp |
| `carrier_providers` | 2 | 2 | 0 | 0 | khớp |
| `dang_ky` | 2 | 2 | 0 | 0 | khớp |
| `dang_ky_lich_su` | 2 | 2 | 0 | 0 | khớp |
| `don_hang` | 15 | 15 | 9870000 | 9870000 | khớp |
| `don_lich_su` | 30 | 30 | 0 | 0 | khớp |
| `don_mat_hang` | 0 | 0 | 0 | 0 | khớp |
| `ds_anh_xa_cot` | 0 | 0 | 0 | 0 | khớp |
| `ds_chenh_lech` | 0 | 0 | 0 | 0 | khớp |
| `ds_dong` | 15 | 15 | 330000 | 330000 | khớp |
| `ds_dot` | 3 | 3 | 0 | 0 | khớp |
| `du_thao_hoa_don` | 2 | 2 | 598000 | 598000 | khớp |
| `g09_harness_ca` | 0 | 0 | 0 | 0 | khớp |
| `g09_harness_lan_chay` | 0 | 0 | 0 | 0 | khớp |
| `gioi_han_chan` | 0 | 0 | 0 | 0 | khớp |
| `gioi_han_luot` | 0 | 0 | 0 | 0 | khớp |
| `goi_dich_vu` | 3 | 3 | 1298000 | 1298000 | khớp |
| `goi_phien_ban` | 4 | 4 | 2597000 | 2597000 | khớp |
| `han_muc_nhap_thang` | 0 | 0 | 0 | 0 | khớp |
| `han_muc_rieng` | 0 | 0 | 0 | 0 | khớp |
| `import_batch` | 1 | 1 | 0 | 0 | khớp |
| `import_dong` | 3 | 3 | 0 | 0 | khớp |
| `khach_hang` | 6 | 6 | 0 | 0 | khớp |
| `ky_tinh_phi` | 2 | 2 | 0 | 0 | khớp |
| `nhat_ky_tinh_phi` | 5 | 5 | 0 | 0 | khớp |
| `permissions` | 28 | 28 | 0 | 0 | khớp |
| `quan_sat_su_kien` | 0 | 0 | 0 | 0 | khớp |
| `reset_tokens` | 0 | 0 | 0 | 0 | khớp |
| `role_permissions` | 68 | 68 | 0 | 0 | khớp |
| `roles` | 6 | 6 | 0 | 0 | khớp |
| `schema_version` | 1 | 1 | 0 | 0 | khớp |
| `sessions` | 0 | 0 | 0 | 0 | khớp |
| `su_kien_dung` | 0 | 0 | 0 | 0 | khớp |
| `tc_but_toan` | 57 | 57 | 8177000 | 8177000 | khớp |
| `tc_cod` | 15 | 15 | 5936000 | 5936000 | khớp |
| `tc_cod_chuyen` | 12 | 12 | 0 | 0 | khớp |
| `tc_cong_no` | 10 | 10 | 4567000 | 4567000 | khớp |
| `tc_dieu_chinh` | 3 | 3 | -3000 | -3000 | khớp |
| `tc_dot_tt` | 3 | 3 | 424000 | 424000 | khớp |
| `tc_dot_tt_dong` | 3 | 3 | 212000 | 212000 | khớp |
| `tc_nhat_ky` | 24 | 24 | 0 | 0 | khớp |
| `tc_phi` | 15 | 15 | 330000 | 330000 | khớp |
| `tenant_memberships` | 3 | 3 | 0 | 0 | khớp |
| `tenants` | 3 | 3 | 0 | 0 | khớp |
| `usage_thang` | 3 | 3 | 0 | 0 | khớp |
| `users` | 4 | 4 | 0 | 0 | khớp |
| `wh_su_kien` | 10 | 10 | 0 | 0 | khớp |
| **TỔNG (toàn kho)** | 51 | 51 | **34336000** | **34336000** | khớp |

`integrity_check`: ok → ok · `bam_toan_kho`: `8a5484bf72a604c0` → `8a5484bf72a604c0` · số bảng LỆCH: **0**

