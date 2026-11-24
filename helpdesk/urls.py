from django.urls import path

from . import views

urlpatterns = [
    path('', views.ticket_list, name='ticket_list'),
    path('tickets/new/', views.ticket_create, name='ticket_create'),
    # Đường dẫn động trỏ tới chi tiết từng yêu cầu theo id (pk)
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
]