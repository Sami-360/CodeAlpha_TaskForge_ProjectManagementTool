from django.contrib import admin

from tasks.models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'project',
        'status',
        'priority',
        'assigned_to',
        'due_date',
        'position',
    ]
    search_fields = ['title', 'project__name', 'assigned_to__username']
    list_filter = ['status', 'priority', 'due_date']
    list_select_related = ['project', 'assigned_to', 'created_by']
