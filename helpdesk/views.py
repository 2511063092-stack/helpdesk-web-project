from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

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