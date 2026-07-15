from django.contrib import admin

from comments.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'created_at', 'updated_at']
    search_fields = ['message', 'task__title', 'user__username']
    list_filter = ['created_at']
    list_select_related = ['task', 'user']
