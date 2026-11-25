from .models import Notification


def unread_notifications(request):
    """Tự động cung cấp số thông báo chưa đọc cho toàn bộ các template HTML."""
    if request.user.is_authenticated:
        # Tận dụng index (recipient, is_read) đã khai báo trong models.py để đếm nhanh
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
    else:
        count = 0

    return {'unread_notifications_count': count}