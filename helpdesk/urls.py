from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Dùng view xác thực có sẵn của Django; redirect_authenticated_user tránh đăng nhập lại
    path(
        'login/',
        auth_views.LoginView.as_view(
            template_name='helpdesk/login.html',
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', views.ticket_list, name='ticket_list'),
    path('tickets/new/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
]