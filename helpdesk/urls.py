from django.urls import path

from . import views

urlpatterns = [
    path('', views.ticket_list, name='ticket_list'),
    # Đường dẫn mở trang tạo yêu cầu mới
    path('tickets/new/', views.ticket_create, name='ticket_create'),
]