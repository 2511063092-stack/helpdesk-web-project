from django import forms
from .models import Ticket

# Quy định luồng chuyển trạng thái hợp lệ của một yêu cầu
ALLOWED_TRANSITIONS = {
    Ticket.Status.NEW: [Ticket.Status.ASSIGNED],
    Ticket.Status.ASSIGNED: [Ticket.Status.IN_PROGRESS],
    Ticket.Status.IN_PROGRESS: [Ticket.Status.RESOLVED],
    Ticket.Status.RESOLVED: [Ticket.Status.CLOSED, Ticket.Status.IN_PROGRESS],
    Ticket.Status.CLOSED: [],
}


class TicketCreateForm(forms.ModelForm):
    """Biểu mẫu tạo yêu cầu hỗ trợ mới."""

    class Meta:
        model = Ticket
        fields = ['title', 'category', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'VD: Không kết nối được Wifi tầng 2',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Mô tả chi tiết lỗi và thời điểm phát sinh...',
            }),
        }


class TicketUpdateForm(forms.ModelForm):
    """Biểu mẫu phân công kỹ thuật viên và cập nhật trạng thái xử lý."""

    class Meta:
        model = Ticket
        fields = ['assigned_to', 'status', 'due_date', 'resolution_note']
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            # format='%Y-%m-%d' bắt buộc để input type="date" hiển thị đúng ngày đã lưu
            'due_date': forms.DateInput(
                format='%Y-%m-%d',
                attrs={'type': 'date', 'class': 'form-control'},
            ),
            'resolution_note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Ghi nhận cách xử lý hoặc kết quả kiểm tra...',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Giới hạn danh sách trạng thái trong dropdown theo đúng luồng hợp lệ
        if self.instance and self.instance.pk:
            current = self.instance.status
            valid_statuses = [current] + ALLOWED_TRANSITIONS.get(current, [])
            self.fields['status'].choices = [
                (val, label)
                for val, label in Ticket.Status.choices
                if val in valid_statuses
            ]