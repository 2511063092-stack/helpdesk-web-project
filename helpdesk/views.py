from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import TicketCreateForm, TicketUpdateForm
from .models import Notification, Ticket, TicketHistory


@login_required
def ticket_list(request):
    """Lấy danh sách yêu cầu mới nhất và hiển thị ra giao diện."""
    tickets = Ticket.objects.select_related(
        'category', 'created_by', 'assigned_to'
    ).order_by('-created_at')

    return render(request, 'helpdesk/ticket_list.html', {'tickets': tickets})


@login_required
def ticket_create(request):
    """Hiển thị form tạo yêu cầu (GET) và xử lý lưu yêu cầu mới (POST)."""
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            # Gán trực tiếp người gửi là tài khoản đang đăng nhập
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
    """Xem chi tiết một yêu cầu, lịch sử xử lý và cập nhật trạng thái."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('category', 'created_by', 'assigned_to'),
        pk=pk,
    )
    histories = ticket.histories.select_related('actor').order_by('-created_at')

    if request.method == 'POST':
        old_status = ticket.status
        old_assignee = ticket.assigned_to

        form = TicketUpdateForm(request.POST, instance=ticket)
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
        form = TicketUpdateForm(instance=ticket)

    return render(
        request,
        'helpdesk/ticket_detail.html',
        {'ticket': ticket, 'form': form, 'histories': histories},
    )