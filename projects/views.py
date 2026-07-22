from datetime import timedelta

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.realtime import broadcast_project_event
from notifications.services import notify_user

from projects.models import Project, ProjectActivity, ProjectLabel, ProjectMember
from projects.permissions import ProjectObjectPermission, can_manage_tasks, get_project_role
from projects.services import record_activity
from projects.serializers import (
    ProjectActivitySerializer,
    ProjectLabelSerializer,
    ProjectMemberCreateSerializer,
    ProjectMemberRoleSerializer,
    ProjectMemberSerializer,
    ProjectSerializer,
)
from tasks.models import Task
from tasks.serializers import TaskSerializer


def project_queryset_for(user):
    return (
        Project.objects.filter(memberships__user=user)
        .select_related('owner')
        .annotate(
            member_count=Count('memberships', distinct=True),
            task_total=Count('tasks', distinct=True),
            task_todo=Count('tasks', filter=Q(tasks__status=Task.Status.TODO), distinct=True),
            task_in_progress=Count(
                'tasks',
                filter=Q(tasks__status=Task.Status.IN_PROGRESS),
                distinct=True,
            ),
            task_done=Count('tasks', filter=Q(tasks__status=Task.Status.DONE), distinct=True),
        )
        .distinct()
    )


class ProjectListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        queryset = project_queryset_for(self.request.user)
        search = self.request.query_params.get('search')
        role = self.request.query_params.get('role')
        sort = self.request.query_params.get('sort', 'updated')
        if search:
            queryset = queryset.filter(name__icontains=search.strip())
        if role:
            if role not in ProjectMember.Role.values:
                raise ValidationError({'role': 'Invalid project role.'})
            queryset = queryset.filter(
                memberships__user=self.request.user,
                memberships__role=role,
            )
        ordering = {
            'updated': '-updated_at',
            'created': '-created_at',
            'alphabetical': 'name',
        }
        if sort not in ordering:
            raise ValidationError({'sort': 'Use updated, created, or alphabetical.'})
        return queryset.order_by(ordering[sort])

    def perform_create(self, serializer):
        project = serializer.save()
        record_activity(
            project=project,
            actor=self.request.user,
            action=ProjectActivity.Action.PROJECT_CREATED,
            metadata={'project_name': project.name},
        )


class GlobalSearchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            raise ValidationError({'q': 'Enter at least 2 characters.'})

        projects = project_queryset_for(request.user).filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).order_by('-updated_at')[:6]
        tasks = (
            Task.objects.filter(project__memberships__user=request.user)
            .filter(Q(title__icontains=query) | Q(description__icontains=query))
            .select_related('project')
            .order_by('-updated_at')
            .distinct()[:6]
        )
        return Response(
            {
                'query': query,
                'projects': [
                    {
                        'id': project.pk,
                        'name': project.name,
                        'description': project.description,
                        'updated_at': project.updated_at,
                    }
                    for project in projects
                ],
                'tasks': [
                    {
                        'id': task.pk,
                        'title': task.title,
                        'project': {'id': task.project_id, 'name': task.project.name},
                        'status': task.status,
                        'priority': task.priority,
                        'due_date': task.due_date,
                    }
                    for task in tasks
                ],
            }
        )


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, ProjectObjectPermission]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return project_queryset_for(self.request.user)

    def perform_update(self, serializer):
        project = serializer.save()
        record_activity(
            project=project,
            actor=self.request.user,
            action=ProjectActivity.Action.PROJECT_UPDATED,
            metadata={'project_name': project.name},
        )


class ProjectMemberListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_project(self):
        return get_object_or_404(
            Project.objects.prefetch_related('memberships'),
            pk=self.kwargs['project_id'],
            memberships__user=self.request.user,
        )

    def get_queryset(self):
        return (
            ProjectMember.objects.filter(project=self.get_project())
            .select_related('user', 'added_by')
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProjectMemberCreateSerializer
        return ProjectMemberSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.get_project()
        return context

    def perform_create(self, serializer):
        project = self.get_project()
        if get_project_role(project, self.request.user) != ProjectMember.Role.OWNER:
            raise PermissionDenied('Only the project owner can add members.')
        membership = serializer.save()
        notify_user(
            recipient=membership.user,
            sender=self.request.user,
            notification_type=Notification.Type.MEMBER_ADDED,
            message=f'You were added to project "{project.name}" as {membership.role}.',
            project=project,
        )
        broadcast_project_event(
            project.pk,
            'member_added',
            {
                'membership_id': membership.pk,
                'user_id': membership.user_id,
                'role': membership.role,
            },
        )
        record_activity(
            project=project,
            actor=self.request.user,
            action=ProjectActivity.Action.MEMBER_ADDED,
            target_user=membership.user,
            metadata={'member_name': membership.user.get_full_name() or membership.user.username, 'role': membership.role},
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        membership = ProjectMember.objects.select_related('user', 'added_by').get(
            pk=serializer.instance.pk
        )
        return Response(
            ProjectMemberSerializer(
                membership,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectMemberDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectMemberRoleSerializer
    http_method_names = ['patch', 'delete', 'head', 'options']
    lookup_url_kwarg = 'member_id'

    def get_queryset(self):
        return ProjectMember.objects.filter(
            project_id=self.kwargs['project_id'],
            project__memberships__user=self.request.user,
        ).select_related('project', 'user')

    def check_owner(self, membership):
        if membership.project.owner_id != self.request.user.id:
            raise PermissionDenied('Only the project owner can manage members.')

    def perform_update(self, serializer):
        self.check_owner(serializer.instance)
        membership = serializer.save()
        notify_user(
            recipient=membership.user,
            sender=self.request.user,
            notification_type=Notification.Type.MEMBER_ROLE_CHANGED,
            message=f'Your role in "{membership.project.name}" changed to {membership.role}.',
            project=membership.project,
        )
        record_activity(
            project=membership.project,
            actor=self.request.user,
            action=ProjectActivity.Action.MEMBER_ROLE_CHANGED,
            target_user=membership.user,
            metadata={'member_name': membership.user.get_full_name() or membership.user.username, 'role': membership.role},
        )

    def perform_destroy(self, instance):
        self.check_owner(instance)
        if instance.role == ProjectMember.Role.OWNER:
            raise ValidationError('The owner membership cannot be removed.')
        project = instance.project
        member_name = instance.user.get_full_name() or instance.user.username
        target_user = instance.user
        instance.delete()
        record_activity(
            project=project,
            actor=self.request.user,
            action=ProjectActivity.Action.MEMBER_REMOVED,
            target_user=target_user,
            metadata={'member_name': member_name},
        )


class ProjectLabelListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectLabelSerializer

    def get_project(self):
        return get_object_or_404(
            Project,
            pk=self.kwargs['project_id'],
            memberships__user=self.request.user,
        )

    def get_queryset(self):
        return ProjectLabel.objects.filter(project=self.get_project())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.get_project()
        return context

    def perform_create(self, serializer):
        project = self.get_project()
        if not can_manage_tasks(project, self.request.user):
            raise PermissionDenied('Only project owners and managers can create labels.')
        serializer.save()


class ProjectLabelDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectLabelSerializer
    http_method_names = ['patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return ProjectLabel.objects.filter(
            project__memberships__user=self.request.user
        ).select_related('project')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['project'] = self.get_object().project
        return context

    def check_manager(self, label):
        if not can_manage_tasks(label.project, self.request.user):
            raise PermissionDenied('Only project owners and managers can manage labels.')

    def perform_update(self, serializer):
        self.check_manager(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self.check_manager(instance)
        instance.delete()


class ProjectActivityListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectActivitySerializer

    def get_project(self):
        return get_object_or_404(
            Project,
            pk=self.kwargs['project_id'],
            memberships__user=self.request.user,
        )

    def get_queryset(self):
        return ProjectActivity.objects.filter(
            project=self.get_project(),
        ).select_related('actor', 'target_user', 'task')[:100]


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        projects = project_queryset_for(request.user)
        tasks = Task.objects.filter(project__memberships__user=request.user).distinct()
        assigned_tasks = tasks.filter(assigned_to=request.user)
        today = timezone.localdate()
        due_week_end = today + timedelta(days=7)
        completed_count = assigned_tasks.filter(status=Task.Status.DONE).count()
        assigned_count = assigned_tasks.count()
        priority_distribution = {
            row['priority']: row['count']
            for row in assigned_tasks.values('priority').annotate(count=Count('id'))
        }
        workload = list(
            assigned_tasks.values('project_id', 'project__name')
            .annotate(total=Count('id'), completed=Count('id', filter=Q(status=Task.Status.DONE)))
            .order_by('-total')[:8]
        )
        recent_activity = ProjectActivity.objects.filter(
            project__memberships__user=request.user
        ).select_related('actor', 'target_user', 'task').distinct()[:8]

        return Response(
            {
                'total_projects': projects.count(),
                'owned_projects': projects.filter(owner=request.user).count(),
                'joined_projects': projects.exclude(owner=request.user).count(),
                'assigned_tasks': assigned_count,
                'total_assigned_tasks': assigned_count,
                'todo_tasks': assigned_tasks.filter(status=Task.Status.TODO).count(),
                'in_progress_tasks': assigned_tasks.filter(
                    status=Task.Status.IN_PROGRESS
                ).count(),
                'completed_tasks': completed_count,
                'overdue_tasks': assigned_tasks.filter(due_date__lt=today).exclude(
                    status=Task.Status.DONE
                ).count(),
                'completion_percentage': round(completed_count * 100 / assigned_count) if assigned_count else 0,
                'tasks_due_this_week': assigned_tasks.filter(
                    due_date__range=(today, due_week_end)
                ).exclude(status=Task.Status.DONE).count(),
                'priority_distribution': priority_distribution,
                'workload_by_project': workload,
                'upcoming_deadlines': TaskSerializer(
                    assigned_tasks.filter(due_date__gte=today).exclude(status=Task.Status.DONE).order_by('due_date')[:8],
                    many=True,
                    context={'request': request},
                ).data,
                'recent_activity': ProjectActivitySerializer(recent_activity, many=True).data,
                'unread_notifications': Notification.objects.filter(
                    recipient=request.user,
                    is_read=False,
                ).count(),
                'recent_projects': ProjectSerializer(
                    projects[:5],
                    many=True,
                    context={'request': request},
                ).data,
                'recent_assigned_tasks': TaskSerializer(
                    assigned_tasks.select_related(
                        'project', 'created_by', 'assigned_to'
                    ).order_by('-updated_at')[:5],
                    many=True,
                    context={'request': request},
                ).data,
            }
        )
