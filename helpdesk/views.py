from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import TicketCreateForm
from .models import Ticket, TicketHistory, User


def ticket_list(request):
    """Lấy danh sách yêu cầu mới nhất và hiển thị ra giao diện."""
    # JOIN sẵn các khóa ngoại để tránh lỗi N+1 query khi tải danh sách lớn
    tickets = Ticket.objects.select_related(
        'category', 'created_by', 'assigned_to'
    ).order_by('-created_at')

    return render(request, 'helpdesk/ticket_list.html', {'tickets': tickets})


def ticket_create(request):
    """Hiển thị form tạo yêu cầu (GET) và xử lý lưu yêu cầu mới (POST)."""
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            # Tạm chưa lưu DB để gán thêm thông tin người gửi
            ticket = form.save(commit=False)
            # TODO: Sau khi làm chức năng Đăng nhập sẽ bắt buộc dùng request.user
            ticket.created_by = (
                request.user if request.user.is_authenticated else User.objects.first()
            )
            ticket.save()

            # Tự động ghi nhận lịch sử tạo yêu cầu
            TicketHistory.objects.create(
                ticket=ticket,
                actor=ticket.created_by,
                action='Tạo yêu cầu mới',
                from_status='',
                to_status=ticket.status,
            )

            messages.success(request, f'Đã tạo yêu cầu {ticket.code} thành công!')
            return redirect('ticket_list')
    else:
        # Phương thức GET: khởi tạo form trống cho người dùng nhập
        form = TicketCreateForm()

    return render(request, 'helpdesk/ticket_create.html', {'form': form})