from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Category, Notification, Ticket, TicketHistory, User


class HelpdeskWorkflowTests(TestCase):
    """Bộ kiểm thử tự động cho toàn bộ luồng nghiệp vụ và phân quyền IT Helpdesk."""

    def setUp(self):
        """Khởi tạo dữ liệu mẫu sạch trước mỗi bài test."""
        self.employee = User.objects.create_user(
            username='nv1', password='Password@123', role=User.Role.EMPLOYEE
        )
        self.other_employee = User.objects.create_user(
            username='nv2', password='Password@123', role=User.Role.EMPLOYEE
        )
        self.tech = User.objects.create_user(
            username='ktv1', password='Password@123', role=User.Role.TECH
        )
        self.manager = User.objects.create_user(
            username='ql1', password='Password@123', role=User.Role.MANAGER
        )
        self.category = Category.objects.create(code='NET', name='Mạng nội bộ')

    def test_create_ticket_generates_code_and_history(self):
        """Tạo phiếu mới phải tự sinh mã HD-xxx, gán đúng người gửi và ghi lịch sử."""
        self.client.force_login(self.employee)

        response = self.client.post(
            reverse('ticket_create'),
            {
                'title': 'Mất kết nối Wifi phòng họp',
                'category': self.category.id,
                'description': 'Không vào được mạng từ 9h sáng.',
            },
        )

        # Lưu thành công phải chuyển hướng (302) về trang danh sách
        self.assertRedirects(response, reverse('ticket_list'))

        ticket = Ticket.objects.get(title='Mất kết nối Wifi phòng họp')
        self.assertEqual(ticket.code, f'HD-{ticket.id:03d}')
        self.assertEqual(ticket.created_by, self.employee)
        self.assertEqual(ticket.status, Ticket.Status.NEW)
        self.assertEqual(TicketHistory.objects.filter(ticket=ticket).count(), 1)

    def test_rbac_blocks_unauthorized_employee_access(self):
        """Nhân viên bị chặn (403) khi xem phiếu người khác, tự sửa phiếu hoặc vào Dashboard."""
        other_ticket = Ticket.objects.create(
            title='Lỗi máy in phòng kế toán',
            description='Kẹt giấy liên tục',
            category=self.category,
            created_by=self.other_employee,
        )
        own_ticket = Ticket.objects.create(
            title='Lỗi bàn phím',
            description='Liệt phím Space',
            category=self.category,
            created_by=self.employee,
        )

        self.client.force_login(self.employee)

        # 1. Cố xem phiếu của nhân viên khác -> 403 Forbidden
        res_other = self.client.get(reverse('ticket_detail', args=[other_ticket.pk]))
        self.assertEqual(res_other.status_code, 403)

        # 2. Cố gửi lệnh POST tự sửa trạng thái trên phiếu của chính mình -> 403 Forbidden
        res_post = self.client.post(
            reverse('ticket_detail', args=[own_ticket.pk]),
            {'status': Ticket.Status.ASSIGNED},
        )
        self.assertEqual(res_post.status_code, 403)

        # 3. Cố truy cập trang Dashboard của Quản lý -> 403 Forbidden
        res_dash = self.client.get(reverse('dashboard'))
        self.assertEqual(res_dash.status_code, 403)

    def test_manager_assign_creates_history_and_notifications(self):
        """Quản lý phân công phiếu phải ghi lịch sử và tạo thông báo cho cả KTV lẫn người gửi."""
        ticket = Ticket.objects.create(
            title='Lỗi phần mềm kế toán',
            description='Không mở được ứng dụng',
            category=self.category,
            created_by=self.employee,
        )

        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('ticket_detail', args=[ticket.pk]),
            {
                'assigned_to': self.tech.id,
                'status': Ticket.Status.ASSIGNED,
                'due_date': '2026-12-31',
                'resolution_note': 'Giao ktv1 kiểm tra trong ngày',
            },
        )

        self.assertRedirects(response, reverse('ticket_detail', args=[ticket.pk]))
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to, self.tech)
        self.assertEqual(ticket.status, Ticket.Status.ASSIGNED)

        # Kiểm tra đã ghi nhận lịch sử và gửi thông báo cho đúng 2 đối tượng
        self.assertTrue(
            TicketHistory.objects.filter(
                ticket=ticket, to_status=Ticket.Status.ASSIGNED
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.tech, ticket=ticket, is_read=False
            ).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                recipient=self.employee, ticket=ticket, is_read=False
            ).exists()
        )

    def test_invalid_status_transition_is_rejected(self):
        """Không cho phép nhảy cóc trạng thái từ Mới tạo (NEW) thẳng sang Đã đóng (CLOSED)."""
        ticket = Ticket.objects.create(
            title='Màn hình nhấp nháy',
            description='Cáp HDMI bị lỏng',
            category=self.category,
            created_by=self.employee,
        )

        self.client.force_login(self.manager)
        response = self.client.post(
            reverse('ticket_detail', args=[ticket.pk]),
            {
                'assigned_to': self.tech.id,
                'status': Ticket.Status.CLOSED,
                'resolution_note': 'Thử nhảy cóc trạng thái',
            },
        )

        # Form không hợp lệ sẽ render lại trang (200) và giữ nguyên trạng thái cũ
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.NEW)

    def test_tech_can_update_status_but_cannot_reassign(self):
        """KTV cập nhật được trạng thái nhưng bị chặn nếu cố gửi dữ liệu đổi người phụ trách."""
        ticket = Ticket.objects.create(
            title='Cài đặt máy in tầng 3',
            description='Cần cài driver',
            category=self.category,
            created_by=self.employee,
            assigned_to=self.tech,
            status=Ticket.Status.ASSIGNED,
        )

        self.client.force_login(self.tech)
        response = self.client.post(
            reverse('ticket_detail', args=[ticket.pk]),
            {
                'assigned_to': self.manager.id,  # Cố tình gửi thêm để kiểm tra lớp bảo vệ
                'status': Ticket.Status.IN_PROGRESS,
                'resolution_note': 'Đang tải và cài đặt driver',
            },
        )

        self.assertRedirects(response, reverse('ticket_detail', args=[ticket.pk]))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, Ticket.Status.IN_PROGRESS)
        # Người phụ trách phải giữ nguyên là ktv1 vì form đã pop trường assigned_to
        self.assertEqual(ticket.assigned_to, self.tech)

    def test_notification_read_and_privacy(self):
        """Bấm đọc thông báo phải đổi is_read=True và chặn người khác đọc hộ (404)."""
        ticket = Ticket.objects.create(
            title='Hỏng chuột không dây',
            description='Đã thay pin nhưng không lên',
            category=self.category,
            created_by=self.employee,
            assigned_to=self.tech,
        )
        notif = Notification.objects.create(
            recipient=self.tech,
            ticket=ticket,
            message=f'Bạn được giao phiếu {ticket.code}',
        )

        # Người khác cố bấm link đọc thông báo của ktv1 -> 404 Not Found
        self.client.force_login(self.employee)
        res_other = self.client.get(reverse('notification_read', args=[notif.pk]))
        self.assertEqual(res_other.status_code, 404)

        # Đúng người nhận bấm vào -> chuyển sang trang chi tiết và đánh dấu đã đọc
        self.client.force_login(self.tech)
        res_owner = self.client.get(reverse('notification_read', args=[notif.pk]))
        self.assertRedirects(res_owner, reverse('ticket_detail', args=[ticket.pk]))
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

    def test_dashboard_stats_and_overdue_tickets(self):
        """Dashboard tính đúng KPI và chỉ liệt kê phiếu quá hạn chưa hoàn thành."""
        yesterday = timezone.localdate() - timedelta(days=1)

        # Phiếu quá hạn nhưng vẫn đang xử lý -> phải xuất hiện trong danh sách cảnh báo
        Ticket.objects.create(
            title='Sự cố server nội bộ',
            description='Quá tải RAM',
            category=self.category,
            created_by=self.employee,
            assigned_to=self.tech,
            status=Ticket.Status.IN_PROGRESS,
            due_date=yesterday,
        )
        # Phiếu có hạn hôm qua nhưng đã giải quyết -> không bị tính là quá hạn
        Ticket.objects.create(
            title='Cấp lại mật khẩu email',
            description='Đã xử lý xong',
            category=self.category,
            created_by=self.employee,
            assigned_to=self.tech,
            status=Ticket.Status.RESOLVED,
            due_date=yesterday,
        )

        self.client.force_login(self.manager)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['stats']['total'], 2)
        self.assertEqual(response.context['stats']['in_progress'], 1)
        self.assertEqual(response.context['stats']['done'], 1)
        self.assertEqual(len(response.context['overdue_tickets']), 1)