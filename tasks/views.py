from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from projects.models import Project
from projects.permissions import can_manage_tasks
from tasks.models import Task
from tasks.permissions import TaskObjectPermission
from tasks.serializers import (
    TaskAssignmentSerializer,
    TaskPositionSerializer,
    TaskSerializer,
    TaskStatusSerializer,
)


def task_queryset_for(user):
    return Task.objects.filter(project__memberships__user=user).select_related(
        'project', 'created_by', 'assigned_to'
    ).distinct()


class TaskListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskSerializer

    def get_project(self):
        return get_object_or_404(
            Project.objects.all(),
            pk=self.kwargs['project_id'],
            memberships__user=self.request.user,
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.get_project()
        return context

    def get_queryset(self):
        queryset = task_queryset_for(self.request.user).filter(project=self.get_project())
        status_value = self.request.query_params.get('status')
        priority = self.request.query_params.get('priority')
        assigned_to = self.request.query_params.get('assigned_to')
        overdue = self.request.query_params.get('overdue')

        if status_value:
            if status_value not in Task.Status.values:
                raise ValidationError({'status': 'Invalid task status.'})
            queryset = queryset.filter(status=status_value)
        if priority:
            if priority not in Task.Priority.values:
                raise ValidationError({'priority': 'Invalid task priority.'})
            queryset = queryset.filter(priority=priority)
        if assigned_to:
            try:
                queryset = queryset.filter(assigned_to_id=int(assigned_to))
            except ValueError as error:
                raise ValidationError({'assigned_to': 'A numeric user ID is required.'}) from error
        if overdue:
            if overdue not in {'true', 'false'}:
                raise ValidationError({'overdue': 'Use true or false.'})
            overdue_filter = Q(
                due_date__lt=timezone.localdate(),
            ) & ~Q(status=Task.Status.DONE)
            queryset = queryset.filter(overdue_filter if overdue == 'true' else ~overdue_filter)

        return queryset

    def perform_create(self, serializer):
        project = self.get_project()
        if not can_manage_tasks(project, self.request.user):
            raise PermissionDenied('Only project owners and managers can create tasks.')
        serializer.save()


class TaskDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, TaskObjectPermission]
    serializer_class = TaskSerializer

    def get_queryset(self):
        return task_queryset_for(self.request.user)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.request.method in {'PATCH', 'PUT'}:
            context['project'] = self.get_object().project
        return context


class TaskStatusView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskStatusSerializer
    http_method_names = ['patch', 'head', 'options']

    def get_queryset(self):
        return task_queryset_for(self.request.user)

    def perform_update(self, serializer):
        task = serializer.instance
        if not can_manage_tasks(task.project, self.request.user):
            if task.assigned_to_id != self.request.user.id:
                raise PermissionDenied(
                    'Only project managers or the assigned user can change status.'
                )
        serializer.save()


class TaskAssignmentView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskAssignmentSerializer
    http_method_names = ['patch', 'head', 'options']

    def get_queryset(self):
        return task_queryset_for(self.request.user)

    def perform_update(self, serializer):
        if not can_manage_tasks(serializer.instance.project, self.request.user):
            raise PermissionDenied('Only project owners and managers can assign tasks.')
        serializer.save()


class TaskPositionView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskPositionSerializer
    http_method_names = ['patch', 'head', 'options']

    def get_queryset(self):
        return task_queryset_for(self.request.user)

    def perform_update(self, serializer):
        if not can_manage_tasks(serializer.instance.project, self.request.user):
            raise PermissionDenied('Only project owners and managers can move tasks.')
        serializer.save()
