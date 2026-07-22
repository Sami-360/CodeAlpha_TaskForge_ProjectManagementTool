from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.realtime import broadcast_project_event
from notifications.services import notify_user, notify_users

from projects.models import Project, ProjectActivity
from projects.permissions import can_manage_tasks
from projects.services import record_activity
from tasks.models import ChecklistItem, Task, TaskAttachment, TaskChecklist
from tasks.permissions import TaskObjectPermission
from tasks.serializers import (
    TaskAssignmentSerializer,
    ChecklistItemSerializer,
    TaskAttachmentCreateSerializer,
    TaskAttachmentSerializer,
    TaskChecklistSerializer,
    TaskLabelAssignmentSerializer,
    TaskPositionSerializer,
    TaskSerializer,
    TaskStatusSerializer,
)


def task_event_data(task):
    return {
        'id': task.pk,
        'status': task.status,
        'position': task.position,
        'assigned_to_id': task.assigned_to_id,
        'updated_at': task.updated_at.isoformat(),
    }


def task_queryset_for(user):
    return (
        Task.objects.filter(project__memberships__user=user)
        .select_related('project', 'created_by', 'assigned_to')
        .prefetch_related('labels')
        .annotate(
            comment_count=Count('comments', distinct=True),
            attachment_count=Count('attachments', distinct=True),
            checklist_total=Count('checklists__items', distinct=True),
            checklist_completed=Count(
                'checklists__items',
                filter=Q(checklists__items__is_completed=True),
                distinct=True,
            ),
        )
        .distinct()
    )


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
        search = self.request.query_params.get('search')
        label = self.request.query_params.get('label')
        due_this_week = self.request.query_params.get('due_this_week')
        unassigned = self.request.query_params.get('unassigned')

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
        if search:
            queryset = queryset.filter(title__icontains=search.strip())
        if label:
            try:
                queryset = queryset.filter(labels__id=int(label))
            except ValueError as error:
                raise ValidationError({'label': 'A numeric label ID is required.'}) from error
        if due_this_week:
            if due_this_week != 'true':
                raise ValidationError({'due_this_week': 'Use true when applying this filter.'})
            today = timezone.localdate()
            queryset = queryset.filter(due_date__range=(today, today + timedelta(days=7)))
        if unassigned:
            if unassigned != 'true':
                raise ValidationError({'unassigned': 'Use true when applying this filter.'})
            queryset = queryset.filter(assigned_to__isnull=True)

        return queryset.distinct()

    def perform_create(self, serializer):
        project = self.get_project()
        if not can_manage_tasks(project, self.request.user):
            raise PermissionDenied('Only project owners and managers can create tasks.')
        task = serializer.save()
        notify_user(
            recipient=task.assigned_to,
            sender=self.request.user,
            notification_type=Notification.Type.TASK_ASSIGNED,
            message=f'You were assigned task "{task.title}".',
            project=task.project,
            task=task,
        )
        broadcast_project_event(
            task.project_id,
            'task_created',
            task_event_data(task),
        )
        record_activity(
            project=task.project,
            actor=self.request.user,
            action=ProjectActivity.Action.TASK_CREATED,
            task=task,
            metadata={'task_title': task.title},
        )


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

    def perform_update(self, serializer):
        previous_assignee_id = serializer.instance.assigned_to_id
        task = serializer.save()
        notify_users(
            recipients=[task.project.owner, task.created_by, task.assigned_to],
            sender=self.request.user,
            notification_type=Notification.Type.TASK_UPDATED,
            message=f'Task "{task.title}" was updated.',
            project=task.project,
            task=task,
        )
        broadcast_project_event(
            task.project_id,
            'task_updated',
            task_event_data(task),
        )
        action = (
            ProjectActivity.Action.TASK_ASSIGNED
            if previous_assignee_id != task.assigned_to_id
            else ProjectActivity.Action.TASK_UPDATED
        )
        record_activity(
            project=task.project,
            actor=self.request.user,
            action=action,
            task=task,
            target_user=task.assigned_to,
            metadata={'task_title': task.title},
        )

    def perform_destroy(self, instance):
        project_id = instance.project_id
        project = instance.project
        task_id = instance.pk
        task_title = instance.title
        instance.delete()
        broadcast_project_event(project_id, 'task_deleted', {'id': task_id})
        record_activity(
            project=project,
            actor=self.request.user,
            action=ProjectActivity.Action.TASK_DELETED,
            metadata={'task_title': task_title},
        )


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
        previous_status = task.status
        if serializer.validated_data.get('status') == Task.Status.DONE and previous_status != Task.Status.DONE:
            task.previous_status = previous_status
        task = serializer.save()
        if previous_status != task.status:
            notify_users(
                recipients=[task.project.owner, task.created_by, task.assigned_to],
                sender=self.request.user,
                notification_type=Notification.Type.TASK_STATUS_CHANGED,
                message=f'Task "{task.title}" moved to {task.get_status_display()}.',
                project=task.project,
                task=task,
            )
            broadcast_project_event(
                task.project_id,
                'task_status_changed',
                task_event_data(task),
            )
            record_activity(
                project=task.project,
                actor=self.request.user,
                action=ProjectActivity.Action.TASK_STATUS_CHANGED,
                task=task,
                metadata={'task_title': task.title, 'status': task.get_status_display()},
            )


class TaskAssignmentView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskAssignmentSerializer
    http_method_names = ['patch', 'head', 'options']

    def get_queryset(self):
        return task_queryset_for(self.request.user)

    def perform_update(self, serializer):
        if not can_manage_tasks(serializer.instance.project, self.request.user):
            raise PermissionDenied('Only project owners and managers can assign tasks.')
        task = serializer.save()
        notify_user(
            recipient=task.assigned_to,
            sender=self.request.user,
            notification_type=Notification.Type.TASK_ASSIGNED,
            message=f'You were assigned task "{task.title}".',
            project=task.project,
            task=task,
        )
        broadcast_project_event(
            task.project_id,
            'task_updated',
            task_event_data(task),
        )
        record_activity(
            project=task.project,
            actor=self.request.user,
            action=ProjectActivity.Action.TASK_ASSIGNED,
            task=task,
            target_user=task.assigned_to,
            metadata={'task_title': task.title},
        )


class TaskPositionView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskPositionSerializer
    http_method_names = ['patch', 'head', 'options']

    def get_queryset(self):
        return task_queryset_for(self.request.user)

    def perform_update(self, serializer):
        if not can_manage_tasks(serializer.instance.project, self.request.user):
            raise PermissionDenied('Only project owners and managers can move tasks.')
        task = serializer.save()
        broadcast_project_event(
            task.project_id,
            'task_status_changed',
            task_event_data(task),
        )
        record_activity(
            project=task.project,
            actor=self.request.user,
            action=ProjectActivity.Action.TASK_STATUS_CHANGED,
            task=task,
            metadata={'task_title': task.title, 'status': task.get_status_display()},
        )


def member_task(task_id, user):
    return get_object_or_404(
        Task.objects.select_related('project', 'assigned_to', 'created_by'),
        pk=task_id,
        project__memberships__user=user,
    )


def can_update_task_content(task, user):
    return can_manage_tasks(task.project, user) or task.assigned_to_id == user.id


class TaskAttachmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_task(self):
        return member_task(self.kwargs['task_id'], self.request.user)

    def get_queryset(self):
        return TaskAttachment.objects.filter(task=self.get_task()).select_related('uploaded_by')

    def get_serializer_class(self):
        return TaskAttachmentCreateSerializer if self.request.method == 'POST' else TaskAttachmentSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['task'] = self.get_task()
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attachment = serializer.save()
        task = attachment.task
        notify_users(
            recipients=[task.project.owner, task.created_by, task.assigned_to],
            sender=request.user,
            notification_type=Notification.Type.ATTACHMENT_ADDED,
            message=f'{request.user.username} added "{attachment.original_name}" to "{task.title}".',
            project=task.project,
            task=task,
        )
        record_activity(
            project=task.project,
            actor=request.user,
            action=ProjectActivity.Action.ATTACHMENT_ADDED,
            task=task,
            metadata={'filename': attachment.original_name, 'task_title': task.title},
        )
        broadcast_project_event(task.project_id, 'attachment_added', {'task_id': task.pk, 'id': attachment.pk})
        return Response(
            TaskAttachmentSerializer(attachment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class TaskAttachmentDestroyView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskAttachment.objects.filter(
            task__project__memberships__user=self.request.user
        ).select_related('task__project', 'uploaded_by')

    def perform_destroy(self, instance):
        if instance.uploaded_by_id != self.request.user.id and not can_manage_tasks(instance.task.project, self.request.user):
            raise PermissionDenied('Only the uploader or a project manager can delete this attachment.')
        task = instance.task
        attachment_id = instance.pk
        filename = instance.original_name
        instance.delete()
        record_activity(
            project=task.project,
            actor=self.request.user,
            action=ProjectActivity.Action.ATTACHMENT_DELETED,
            task=task,
            metadata={'filename': filename, 'task_title': task.title},
        )
        broadcast_project_event(
            task.project_id,
            'attachment_deleted',
            {'task_id': task.pk, 'id': attachment_id},
        )


class TaskAttachmentDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, attachment_id):
        attachment = get_object_or_404(
            TaskAttachment.objects.select_related('task__project'),
            pk=attachment_id,
            task__project__memberships__user=request.user,
        )
        try:
            file_handle = attachment.file.open('rb')
        except (FileNotFoundError, OSError) as error:
            raise Http404('Attachment file is missing.') from error
        return FileResponse(
            file_handle,
            as_attachment=True,
            filename=attachment.original_name,
        )


class TaskChecklistListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TaskChecklistSerializer

    def get_task(self):
        return member_task(self.kwargs['task_id'], self.request.user)

    def get_queryset(self):
        return TaskChecklist.objects.filter(task=self.get_task()).prefetch_related('items__completed_by')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['task'] = self.get_task()
        return context

    def perform_create(self, serializer):
        task = self.get_task()
        if not can_manage_tasks(task.project, self.request.user):
            raise PermissionDenied('Only project owners and managers can create checklists.')
        checklist = serializer.save()
        record_activity(project=task.project, actor=self.request.user, action=ProjectActivity.Action.CHECKLIST_UPDATED, task=task)
        broadcast_project_event(task.project_id, 'checklist_updated', {'task_id': task.pk, 'checklist_id': checklist.pk})


class TaskChecklistDestroyView(generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return TaskChecklist.objects.filter(task__project__memberships__user=self.request.user).select_related('task__project')

    def perform_destroy(self, instance):
        if not can_manage_tasks(instance.task.project, self.request.user):
            raise PermissionDenied('Only project owners and managers can delete checklists.')
        instance.delete()


class ChecklistItemCreateView(generics.CreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChecklistItemSerializer

    def get_checklist(self):
        return get_object_or_404(
            TaskChecklist.objects.select_related('task__project'),
            pk=self.kwargs['checklist_id'],
            task__project__memberships__user=self.request.user,
        )

    def perform_create(self, serializer):
        checklist = self.get_checklist()
        if not can_update_task_content(checklist.task, self.request.user):
            raise PermissionDenied('Only project managers or the task assignee can add checklist items.')
        item = serializer.save(checklist=checklist)
        record_activity(project=checklist.task.project, actor=self.request.user, action=ProjectActivity.Action.CHECKLIST_UPDATED, task=checklist.task)
        broadcast_project_event(checklist.task.project_id, 'checklist_updated', {'task_id': checklist.task_id, 'item_id': item.pk})


class ChecklistItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ChecklistItemSerializer
    http_method_names = ['patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return ChecklistItem.objects.filter(
            checklist__task__project__memberships__user=self.request.user
        ).select_related('checklist__task__project')

    def check_change_permission(self, item):
        if not can_update_task_content(item.checklist.task, self.request.user):
            raise PermissionDenied('Only project managers or the task assignee can update checklist items.')

    def perform_update(self, serializer):
        self.check_change_permission(serializer.instance)
        completion = serializer.validated_data.get('is_completed')
        extra = {}
        if completion is not None:
            extra = {
                'completed_by': self.request.user if completion else None,
                'completed_at': timezone.now() if completion else None,
            }
        item = serializer.save(**extra)
        task = item.checklist.task
        record_activity(project=task.project, actor=self.request.user, action=ProjectActivity.Action.CHECKLIST_UPDATED, task=task)
        broadcast_project_event(task.project_id, 'checklist_updated', {'task_id': task.pk, 'item_id': item.pk})

    def perform_destroy(self, instance):
        self.check_change_permission(instance)
        task = instance.checklist.task
        instance.delete()
        broadcast_project_event(task.project_id, 'checklist_updated', {'task_id': task.pk})


class ChecklistItemToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, item_id):
        item = get_object_or_404(
            ChecklistItem.objects.select_related('checklist__task__project'),
            pk=item_id,
            checklist__task__project__memberships__user=request.user,
        )
        task = item.checklist.task
        if not can_update_task_content(task, request.user):
            raise PermissionDenied('Only project managers or the task assignee can complete checklist items.')
        item.is_completed = not item.is_completed
        item.completed_by = request.user if item.is_completed else None
        item.completed_at = timezone.now() if item.is_completed else None
        item.save(update_fields=['is_completed', 'completed_by', 'completed_at'])
        notify_users(
            recipients=[task.project.owner, task.assigned_to],
            sender=request.user,
            notification_type=Notification.Type.CHECKLIST_UPDATED,
            message=f'Checklist item updated on "{task.title}".',
            project=task.project,
            task=task,
        )
        record_activity(project=task.project, actor=request.user, action=ProjectActivity.Action.CHECKLIST_UPDATED, task=task)
        broadcast_project_event(task.project_id, 'checklist_updated', {'task_id': task.pk, 'item_id': item.pk})
        return Response(ChecklistItemSerializer(item).data)


class TaskLabelAssignmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, task_id):
        task = member_task(task_id, request.user)
        if not can_manage_tasks(task.project, request.user):
            raise PermissionDenied('Only project owners and managers can assign labels.')
        serializer = TaskLabelAssignmentSerializer(data=request.data, context={'task': task})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        broadcast_project_event(task.project_id, 'task_updated', task_event_data(task))
        return Response(TaskSerializer(task, context={'request': request, 'project': task.project}).data)


class TaskCompletionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    target_status = Task.Status.DONE

    def patch(self, request, task_id):
        task = member_task(task_id, request.user)
        if not can_update_task_content(task, request.user):
            raise PermissionDenied('Only project managers or the task assignee can change completion.')
        if task.status != Task.Status.DONE:
            task.previous_status = task.status
        task.status = self.target_status
        task.save(update_fields=['status', 'previous_status', 'updated_at'])
        notify_users(
            recipients=[task.project.owner, task.created_by, task.assigned_to],
            sender=request.user,
            notification_type=Notification.Type.TASK_STATUS_CHANGED,
            message=f'Task "{task.title}" was completed.',
            project=task.project,
            task=task,
        )
        record_activity(project=task.project, actor=request.user, action=ProjectActivity.Action.TASK_STATUS_CHANGED, task=task, metadata={'task_title': task.title, 'status': 'Done'})
        broadcast_project_event(task.project_id, 'task_status_changed', task_event_data(task))
        return Response(TaskSerializer(task, context={'request': request, 'project': task.project}).data)


class TaskReopenView(TaskCompletionView):
    def patch(self, request, task_id):
        task = member_task(task_id, request.user)
        if not can_update_task_content(task, request.user):
            raise PermissionDenied('Only project managers or the task assignee can reopen this task.')
        task.status = task.previous_status if task.previous_status in {Task.Status.TODO, Task.Status.IN_PROGRESS} else Task.Status.TODO
        task.previous_status = ''
        task.save(update_fields=['status', 'previous_status', 'updated_at'])
        notify_users(
            recipients=[task.project.owner, task.created_by, task.assigned_to],
            sender=request.user,
            notification_type=Notification.Type.TASK_STATUS_CHANGED,
            message=f'Task "{task.title}" was reopened.',
            project=task.project,
            task=task,
        )
        record_activity(project=task.project, actor=request.user, action=ProjectActivity.Action.TASK_STATUS_CHANGED, task=task, metadata={'task_title': task.title, 'status': task.get_status_display()})
        broadcast_project_event(task.project_id, 'task_status_changed', task_event_data(task))
        return Response(TaskSerializer(task, context={'request': request, 'project': task.project}).data)
