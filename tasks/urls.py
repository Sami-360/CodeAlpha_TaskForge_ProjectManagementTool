from django.urls import path

from tasks.views import (
    ChecklistItemCreateView,
    ChecklistItemDetailView,
    ChecklistItemToggleView,
    TaskAttachmentDestroyView,
    TaskAttachmentDownloadView,
    TaskAttachmentListCreateView,
    TaskAssignmentView,
    TaskChecklistDestroyView,
    TaskChecklistListCreateView,
    TaskCompletionView,
    TaskDetailView,
    TaskListCreateView,
    TaskPositionView,
    TaskLabelAssignmentView,
    TaskReopenView,
    TaskStatusView,
)


urlpatterns = [
    path(
        'projects/<int:project_id>/tasks/',
        TaskListCreateView.as_view(),
        name='task-list',
    ),
    path('tasks/<int:pk>/', TaskDetailView.as_view(), name='task-detail'),
    path('tasks/<int:pk>/status/', TaskStatusView.as_view(), name='task-status'),
    path('tasks/<int:pk>/assign/', TaskAssignmentView.as_view(), name='task-assign'),
    path('tasks/<int:pk>/position/', TaskPositionView.as_view(), name='task-position'),
    path('tasks/<int:task_id>/complete/', TaskCompletionView.as_view(), name='task-complete'),
    path('tasks/<int:task_id>/reopen/', TaskReopenView.as_view(), name='task-reopen'),
    path('tasks/<int:task_id>/labels/', TaskLabelAssignmentView.as_view(), name='task-labels'),
    path('tasks/<int:task_id>/attachments/', TaskAttachmentListCreateView.as_view(), name='task-attachment-list'),
    path('task-attachments/<int:pk>/', TaskAttachmentDestroyView.as_view(), name='task-attachment-detail'),
    path('task-attachments/<int:attachment_id>/download/', TaskAttachmentDownloadView.as_view(), name='task-attachment-download'),
    path('tasks/<int:task_id>/checklists/', TaskChecklistListCreateView.as_view(), name='task-checklist-list'),
    path('checklists/<int:pk>/', TaskChecklistDestroyView.as_view(), name='task-checklist-detail'),
    path('checklists/<int:checklist_id>/items/', ChecklistItemCreateView.as_view(), name='checklist-item-list'),
    path('checklist-items/<int:pk>/', ChecklistItemDetailView.as_view(), name='checklist-item-detail'),
    path('checklist-items/<int:item_id>/toggle/', ChecklistItemToggleView.as_view(), name='checklist-item-toggle'),
]
