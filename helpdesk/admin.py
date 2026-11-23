from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Category, Notification, Ticket, TicketHistory, User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'is_active')
    # hiển thi thêm trường role trong form sửa và tạo
    fieldsets = UserAdmin.fieldsets + (('Phân quyền', {'fields': ('role',)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (('Phân quyền', {'fields': ('role',)}),)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'category', 'created_by', 'assigned_to', 'status', 'created_at')
    list_filter = ('status', 'category')
    search_fields = ('code', 'title')


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'actor', 'action', 'from_status', 'to_status', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'ticket', 'message', 'is_read', 'created_at')
    list_filter = ('is_read',)