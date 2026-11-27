# Hệ thống Quản lý Yêu cầu Hỗ trợ Kỹ thuật (IT Helpdesk)

Ứng dụng web quản lý tiếp nhận, phân công và theo dõi xử lý sự cố CNTT nội bộ, xây dựng bằng **Django**, **SQLite** và **Bootstrap 5**.

## Tính năng chính
- **Quản lý yêu cầu (Ticket):** Tạo phiếu tự động sinh mã (`HD-001`), xem chi tiết, kiểm soát luồng chuyển trạng thái hợp lệ (`Mới tạo → Đã phân công → Đang xử lý → Đã giải quyết → Đã đóng`).
- **Phân quyền 3 vai trò (RBAC):**
  - **Nhân viên (`EMPLOYEE`):** Gửi yêu cầu và theo dõi các phiếu của chính mình.
  - **Kỹ thuật viên (`TECH`):** Xem và cập nhật tiến độ xử lý các phiếu được giao.
  - **Quản lý (`MANAGER` / Superuser):** Xem toàn bộ phiếu, phân công kỹ thuật viên, đặt hạn xử lý và truy cập Dashboard thống kê.
- **Lưu vết & Thông báo:** Tự động ghi nhật ký (`TicketHistory`) mọi lần thay đổi trạng thái và gửi thông báo trong ứng dụng (`Notification`) kèm bộ đếm chưa đọc trên thanh điều hướng.
- **Tìm kiếm, Lọc & Dashboard:** Tìm kiếm theo mã/tiêu đề, lọc theo trạng thái/danh mục; trang thống kê KPI theo danh mục, khối lượng công việc kỹ thuật viên và cảnh báo phiếu quá hạn.

## Hướng dẫn cài đặt và chạy dự án

```powershell
# 1. Tạo và kích hoạt môi trường ảo (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Cài đặt thư viện cần thiết
pip install -r requirements.txt

# 3. Khởi tạo cơ sở dữ liệu
python manage.py migrate

# 4. Tạo tài khoản Quản trị viên (Superuser)
python manage.py createsuperuser

# 5. Chạy máy chủ phát triển
python manage.py runserver