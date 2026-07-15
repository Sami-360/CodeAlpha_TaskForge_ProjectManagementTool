from django.urls import path

from tasks.views import (
    TaskAssignmentView,
    TaskDetailView,
    TaskListCreateView,
    TaskPositionView,
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
]
