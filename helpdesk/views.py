from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone
from .forms import TicketCreateForm, TicketUpdateForm
from .models import Notification, Ticket, TicketHistory, User, Category


def _is_manager(user):
    """Kiểm tra người dùng có quyền Quản lý (hoặc Superuser) không."""
    return user.is_superuser or user.role == User.Role.MANAGER


def _can_view_ticket(user, ticket):
    """Kiểm tra quyền xem chi tiết một yêu cầu cụ thể."""
    if _is_manager(user):
        return True
    if user.role == User.Role.TECH:
        return ticket.assigned_to == user or ticket.created_by == user
    return ticket.created_by == user


def _can_update_ticket(user, ticket):
    """Kiểm tra quyền phân công hoặc cập nhật trạng thái xử lý."""
    if _is_manager(user):
        return True
    return user.role == User.Role.TECH and ticket.assigned_to == user


@login_required
def ticket_list(request):
    """Hiển thị danh sách yêu cầu theo đúng phạm vi quyền của từng vai trò."""
    tickets = Ticket.objects.select_related(
        'category', 'created_by', 'assigned_to'
    ).order_by('-created_at')

    # Bước 1: Áp dụng bộ lọc phân quyền trước để không lộ phiếu ngoài phạm vi
    user = request.user
    if not _is_manager(user):
        if user.role == User.Role.TECH:
            tickets = tickets.filter(Q(assigned_to=user) | Q(created_by=user))
        else:
            tickets = tickets.filter(created_by=user)

    # Bước 2: Đọc các điều kiện tìm kiếm và lọc từ thanh địa chỉ URL (GET)
    q = request.GET.get('q', '').strip()
    selected_status = request.GET.get('status', '')
    category_param = request.GET.get('category', '')

    if q:
        # Tìm gần đúng theo Mã phiếu HOẶC Tiêu đề, không phân biệt hoa/thường
        tickets = tickets.filter(Q(code__icontains=q) | Q(title__icontains=q))

    if selected_status:
        tickets = tickets.filter(status=selected_status)

    # Kiểm tra isdigit() trước khi ép sang int để tránh lỗi nếu URL bị gõ sai
    selected_category = int(category_param) if category_param.isdigit() else None
    if selected_category:
        tickets = tickets.filter(category_id=selected_category)

    # Truyền lại giá trị đã chọn sang template để giữ nguyên trạng thái ô lọc
    context = {
        'tickets': tickets,
        'categories': Category.objects.all(),
        'statuses': Ticket.Status.choices,
        'q': q,
        'selected_status': selected_status,
        'selected_category': selected_category,
    }
    return render(request, 'helpdesk/ticket_list.html', context)

@login_required
def ticket_create(request):
    """Hiển thị form tạo yêu cầu (GET) và xử lý lưu yêu cầu mới (POST)."""
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()

            TicketHistory.objects.create(
                ticket=ticket,
                actor=request.user,
                action='Tạo yêu cầu mới',
                from_status='',
                to_status=ticket.status,
            )

            messages.success(request, f'Đã tạo yêu cầu {ticket.code} thành công!')
            return redirect('ticket_list')
    else:
        form = TicketCreateForm()

    return render(request, 'helpdesk/ticket_create.html', {'form': form})


@login_required
def ticket_detail(request, pk):
    """Xem chi tiết yêu cầu, kiểm tra phân quyền xem và cập nhật trạng thái."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('category', 'created_by', 'assigned_to'),
        pk=pk,
    )

    # Lớp bảo vệ 1: Chặn xem trộm phiếu không thuộc phạm vi quyền (trả về lỗi 403)
    if not _can_view_ticket(request.user, ticket):
        raise PermissionDenied('Bạn không có quyền xem yêu cầu này.')

    can_update = _can_update_ticket(request.user, ticket)
    histories = ticket.histories.select_related('actor').order_by('-created_at')

    if request.method == 'POST':
        # Lớp bảo vệ 2: Chặn gửi lệnh POST trái phép nếu không có quyền cập nhật
        if not can_update:
            raise PermissionDenied('Bạn không có quyền cập nhật yêu cầu này.')

        old_status = ticket.status
        old_assignee = ticket.assigned_to

        form = TicketUpdateForm(request.POST, instance=ticket, user=request.user)
        if form.is_valid():
            updated_ticket = form.save()

            if old_status != updated_ticket.status or old_assignee != updated_ticket.assigned_to:
                action_text = (
                    'Cập nhật trạng thái'
                    if old_status != updated_ticket.status
                    else 'Cập nhật phân công'
                )
                TicketHistory.objects.create(
                    ticket=updated_ticket,
                    actor=request.user,
                    action=action_text,
                    from_status=old_status,
                    to_status=updated_ticket.status,
                    note=updated_ticket.resolution_note,
                )

            if updated_ticket.assigned_to and old_assignee != updated_ticket.assigned_to:
                Notification.objects.create(
                    recipient=updated_ticket.assigned_to,
                    ticket=updated_ticket,
                    message=f'Bạn vừa được phân công xử lý yêu cầu {updated_ticket.code}',
                )

            # Thông báo cho người gửi phiếu biết khi trạng thái xử lý thay đổi
            if old_status != updated_ticket.status and updated_ticket.created_by != request.user:
                Notification.objects.create(
                    recipient=updated_ticket.created_by,
                    ticket=updated_ticket,
                    message=(
                        f'Yêu cầu {updated_ticket.code} đã chuyển sang trạng thái '
                        f'"{updated_ticket.get_status_display()}"'),
                )

            messages.success(request, f'Đã cập nhật yêu cầu {updated_ticket.code}!')
            return redirect('ticket_detail', pk=ticket.pk)
    else:
        form = TicketUpdateForm(instance=ticket, user=request.user) if can_update else None

    return render(
        request,
        'helpdesk/ticket_detail.html',
        {
            'ticket': ticket,
            'form': form,
            'histories': histories,
            'can_update': can_update,
        },
    )

@login_required
def notification_list(request):
    """Hiển thị danh sách thông báo của riêng tài khoản đang đăng nhập."""
    notifications = (
        Notification.objects.filter(recipient=request.user)
        .select_related('ticket')
        .order_by('-created_at')
    )
    return render(
        request,
        'helpdesk/notification_list.html',
        {'notifications': notifications},
    )


@login_required
def notification_read(request, pk):
    """Đánh dấu 1 thông báo là đã đọc rồi chuyển thẳng sang trang chi tiết yêu cầu."""
    # Ràng buộc recipient=request.user để ngăn đọc lén thông báo của người khác
    notification = get_object_or_404(
        Notification,
        pk=pk,
        recipient=request.user,
    )
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    return redirect('ticket_detail', pk=notification.ticket_id)


@login_required
@require_POST
def notification_mark_all_read(request):
    """Đánh dấu toàn bộ thông báo chưa đọc của người dùng hiện tại thành đã đọc."""
    # Dùng .update() để cập nhật hàng loạt trong 1 câu SQL duy nhất
    Notification.objects.filter(
        recipient=request.user,
        is_read=False,
    ).update(is_read=True)

    messages.success(request, 'Đã đánh dấu tất cả thông báo là đã đọc.')
    return redirect('notification_list')

@login_required
def dashboard(request):
    """Trang thống kê tổng quan hệ thống (chỉ dành cho Quản lý / Superuser)."""
    # Lớp bảo vệ Backend: chặn Nhân viên và Kỹ thuật viên gõ thẳng URL /dashboard/
    if not _is_manager(request.user):
        raise PermissionDenied('Chỉ Quản lý mới có quyền xem trang thống kê.')

    # 1. Tính 4 chỉ số tổng quan (KPI) trong đúng 1 câu truy vấn SQL
    stats = Ticket.objects.aggregate(
        total=Count('id'),
        new=Count('id', filter=Q(status=Ticket.Status.NEW)),
        in_progress=Count(
            'id',
            filter=Q(status__in=[Ticket.Status.ASSIGNED, Ticket.Status.IN_PROGRESS]),
        ),
        done=Count(
            'id',
            filter=Q(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]),
        ),
    )

    # 2. Đếm số lượng yêu cầu theo từng Danh mục (dùng related_name='tickets')
    by_category = Category.objects.annotate(
        ticket_count=Count('tickets')
    ).order_by('-ticket_count')

    # 3. Thống kê khối lượng công việc theo từng Kỹ thuật viên / Quản lý
    by_tech = (
        User.objects.filter(role__in=[User.Role.TECH, User.Role.MANAGER])
        .annotate(
            total_assigned=Count('assigned_tickets'),
            open_assigned=Count(
                'assigned_tickets',
                filter=Q(
                    assigned_tickets__status__in=[
                        Ticket.Status.ASSIGNED,
                        Ticket.Status.IN_PROGRESS,
                    ]
                ),
            ),
            done_assigned=Count(
                'assigned_tickets',
                filter=Q(
                    assigned_tickets__status__in=[
                        Ticket.Status.RESOLVED,
                        Ticket.Status.CLOSED,
                    ]
                ),
            ),
        )
        .order_by('-open_assigned', '-total_assigned')
    )

    # 4. Lọc các phiếu quá hạn (hạn xử lý < hôm nay và chưa Giải quyết / Đóng)
    today = timezone.localdate()
    overdue_tickets = (
        Ticket.objects.select_related('category', 'assigned_to')
        .filter(due_date__lt=today)
        .exclude(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
        .order_by('due_date')
    )

    context = {
        'stats': stats,
        'by_category': by_category,
        'by_tech': by_tech,
        'overdue_tickets': overdue_tickets,
        'today': today,
    }
    return render(request, 'helpdesk/dashboard.html', context)