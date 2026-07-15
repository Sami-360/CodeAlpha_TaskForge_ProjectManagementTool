from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions

from comments.models import Comment
from comments.permissions import CommentObjectPermission
from comments.serializers import CommentSerializer
from notifications.models import Notification
from notifications.realtime import broadcast_project_event
from notifications.services import notify_users
from tasks.models import Task


class CommentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CommentSerializer

    def get_task(self):
        return get_object_or_404(
            Task.objects.select_related('project', 'created_by', 'assigned_to'),
            pk=self.kwargs['task_id'],
            project__memberships__user=self.request.user,
        )

    def get_queryset(self):
        return Comment.objects.filter(task=self.get_task()).select_related('user')

    def perform_create(self, serializer):
        task = self.get_task()
        comment = serializer.save(task=task, user=self.request.user)
        notify_users(
            recipients=[task.project.owner, task.created_by, task.assigned_to],
            sender=self.request.user,
            notification_type=Notification.Type.NEW_COMMENT,
            message=f'{self.request.user.username} commented on "{task.title}".',
            project=task.project,
            task=task,
        )
        broadcast_project_event(
            task.project_id,
            'comment_created',
            {
                'id': comment.pk,
                'task_id': task.pk,
                'user_id': comment.user_id,
                'message': comment.message,
                'created_at': comment.created_at.isoformat(),
            },
        )
        return comment


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, CommentObjectPermission]
    serializer_class = CommentSerializer
    http_method_names = ['patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return Comment.objects.filter(
            task__project__memberships__user=self.request.user
        ).select_related('task__project', 'user')
