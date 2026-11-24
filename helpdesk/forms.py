from django import forms
from .models import Ticket


class TicketCreateForm(forms.ModelForm):
    """Biểu mẫu tạo yêu cầu hỗ trợ mới dựa trên model Ticket."""

    class Meta:
        model = Ticket
        # Chỉ cho phép người dùng nhập 3 trường này; các trường khác do hệ thống tự gán
        fields = ['title', 'category', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'VD: Không kết nối được Wifi tầng 2',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Mô tả chi tiết lỗi và thời điểm phát sinh...',
            }),
        }