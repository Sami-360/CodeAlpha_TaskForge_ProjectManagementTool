from pathlib import Path

from django.contrib import admin
from django.utils import timezone

from tasks.models import ChecklistItem, Task, TaskAttachment, TaskChecklist


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'project',
        'status',
        'priority',
        'assigned_to',
        'created_by',
        'due_date',
        'is_overdue',
        'position',
    ]
    search_fields = ['title', 'project__name', 'assigned_to__username']
    list_filter = ['status', 'priority', 'project', 'due_date']
    list_select_related = ['project', 'assigned_to', 'created_by']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(boolean=True, description='Overdue')
    def is_overdue(self, task):
        return bool(task.due_date and task.due_date < timezone.localdate() and task.status != Task.Status.DONE)


@admin.register(TaskAttachment)
class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ['original_name', 'task', 'uploaded_by', 'file_size', 'uploaded_at']
    search_fields = ['original_name', 'task__title', 'uploaded_by__username']
    list_filter = ['uploaded_at']
    readonly_fields = ['original_name', 'file_size', 'uploaded_at']

    def save_model(self, request, obj, form, change):
        upload = form.cleaned_data.get('file')
        if upload:
            obj.original_name = Path(upload.name).name
            obj.file_size = upload.size
        super().save_model(request, obj, form, change)


@admin.register(TaskChecklist)
class TaskChecklistAdmin(admin.ModelAdmin):
    list_display = ['title', 'task', 'created_by', 'created_at']
    search_fields = ['title', 'task__title']
    list_filter = ['created_at']
    readonly_fields = ['created_at']


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ['text', 'checklist', 'is_completed', 'position', 'completed_by', 'created_at']
    search_fields = ['text', 'checklist__title', 'checklist__task__title']
    list_filter = ['is_completed', 'created_at']
    readonly_fields = ['completed_at', 'created_at']
