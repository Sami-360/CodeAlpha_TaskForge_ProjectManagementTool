from django.contrib import admin

from comments.models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['task', 'user', 'message_preview', 'created_at', 'updated_at']
    search_fields = ['message', 'task__title', 'user__username']
    list_filter = ['task', 'user', 'created_at']
    list_select_related = ['task', 'user']

    @admin.display(description='Message')
    def message_preview(self, comment):
        return comment.message[:80]
