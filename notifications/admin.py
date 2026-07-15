from django.contrib import admin

from notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'recipient',
        'notification_type',
        'sender',
        'project',
        'task',
        'is_read',
        'created_at',
    ]
    search_fields = ['recipient__username', 'sender__username', 'message']
    list_filter = ['notification_type', 'is_read', 'created_at']
    list_select_related = ['recipient', 'sender', 'project', 'task']
