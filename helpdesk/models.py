from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """
    Bảng người dùng tùy chỉnh, kế thừa từ AbstractUser của Django.
    Tự động có sẵn các cột: username, password (đã băm), họ tên, email, is_active.
    """
    class Role(models.TextChoices):
        # Cú pháp: TÊN_HẰNG = 'giá_trị_lưu_trong_DB', 'Nhãn hiển thị tiếng Việt'
        EMPLOYEE = 'EMPLOYEE', 'Nhân viên'
        TECH = 'TECH', 'Kỹ thuật viên'
        MANAGER = 'MANAGER', 'Quản lý kỹ thuật'

    # Cột phân quyền chính để kiểm soát ai được xem/sửa yêu cầu nào
    role = models.CharField(
        max_length=20,
        choices=Role.choices,     # Khóa cứng chỉ cho phép chọn 1 trong 3 vai trò trên
        default=Role.EMPLOYEE,    # Tài khoản mới tạo mặc định là Nhân viên
        verbose_name='Vai trò',   # Tên hiển thị trên giao diện Admin/Form
    )
    