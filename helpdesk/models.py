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

class Category(models.Model):
    # Bảng danh mục sự cố

    code = models.CharField(max_length=20, unique=True, verbose_name='Mã danh mục')
    name = models.CharField(max_length=100, verbose_name='Tên danh mục')

    def __str__(self):
        # Quy định cách hiển thị đối tượng dang chữ trong trang Admin và Dropdown
        return f'{self.code} - {self.name}'

class Ticket(models.Model):
    # Bảng lưu toàn bộ yêu cầu hỗ trợ kỹ thuật

    class Status(models.TextChoices):
        # 5 trạng thái 
        NEW = 'NEW', 'Mới tạo'
        ASSIGNED = 'ASSIGNED', 'Đã phân công'
        IN_PROGRESS = 'IN_PROGRESS', 'Đang xử lý'
        RESOLVED = 'RESOLVED', 'Đã giải quyết'
        CLOSED = 'CLOSED', 'Đã đóng'

    # blank=True vì mã này do hệ thống tự sinh, người dùng không tự nhập 
    code = models.CharField(max_length=20, unique=True, blank=True, verbose_name='Mã yêu cầu')
    title = models.CharField(max_length=200, verbose_name='Tiêu đề')
    description = models.TextField(verbose_name='Mô tả sự cố')

    # khóa ngoài liên kết với danh mục và người dùng
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT, #chặn xóa danh mục nếu đang có yêu cầu sử dụng
        related_name='tickets',
        verbose_name='Danh mục',
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, # Giữ lại dữ liệu yêu cầu, không cho xóa người tạo 
        related_name='created_tickets',
        verbose_name='Người gửi',
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL, #Nếu xóa kỹ thuật viên thì để trống người phụ trách
        null=True, #cho phép giá trị NULL trong DB
        blank=True, # cho phép bỏ trống trên biểu mẫu nhập liệu 
        related_name='assigned_tickets',
        verbose_name='Kỹ thuật viên phụ trách',
    )

    # db_index=True giúp lọc danh sách và thống kê theo trang thái nhanh hơn
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
        verbose_name='Trạng Thái',
    )
    due_date = models.DateField(null=True, blank=True, verbose_name='Hạn xử lý')
    resolution_note = models.TextField(blank=True, verbose_name='Kết quả xử lý')
    # auto_now_add=True tự động lấy thời gian hiện tại lúc bản ghi được tạo lần đâu
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian tạo')

    def save(self, *args, **kwargs):
        # lưu lần 1 để Database cấp số id tự tăng
        super().save(*args, **kwargs)
        # dựa vào id vừa có để sinh mã duy nhất dạng HD-001
        if not self.code:
            self.code = f'HD-{self.id:03d}'
            super().save(update_fields=['code'])

    def __str__(self):
        return f'{self.code} - {self.title}'

class TicketHistory(models.Model):
    # Bảng nhật ký lưu vết

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE, # xóa yêu cầu thì xóa luôn lịch sử đi kèm
        related_name='histories',
        verbose_name='Yêu cầu',
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='actions',
        verbose_name='Người thực hiện',
    )
    action = models.CharField(max_length=100, verbose_name='Hành động')
    from_status = models.CharField(max_length=20, blank=True, verbose_name='Trạng thái trước')
    to_status = models.CharField(max_length=20, verbose_name='Trạng thái sau')
    note = models.TextField(blank=True, verbose_name='Ghi chú')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian')

    def __str__(self):
        return f'{self.ticket.code}: {self.action}'

class Notification(models.Model):
    #Bảng thông báo trong ứng dụng gửi tới người dùng liên quan

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Người nhận',
    )
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Yêu cầu liên quan',
    )
    message = models.CharField(max_length=255, verbose_name='Nội dung')
    is_read = models.BooleanField(default=False, verbose_name='Đã đọc')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Thời gian')

    class Meta:
        # Đánh index tổ hợp để đếm nhanh số thông báo chưa đọc của từng user
        indexes = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f'Gửi {self.recipient.username}: {self.message}'