from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from notifications.models import Notification
from notifications.services import notify_user

from projects.models import Project, ProjectMember
from projects.permissions import ProjectObjectPermission, get_project_role
from projects.serializers import (
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
        return project_queryset_for(self.request.user)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated, ProjectObjectPermission]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return project_queryset_for(self.request.user)


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
        serializer.save()

    def perform_destroy(self, instance):
        self.check_owner(instance)
        if instance.role == ProjectMember.Role.OWNER:
            raise ValidationError('The owner membership cannot be removed.')
        instance.delete()


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        projects = project_queryset_for(request.user)
        tasks = Task.objects.filter(project__memberships__user=request.user).distinct()
        assigned_tasks = tasks.filter(assigned_to=request.user)
        today = timezone.localdate()

        return Response(
            {
                'total_projects': projects.count(),
                'owned_projects': projects.filter(owner=request.user).count(),
                'assigned_tasks': assigned_tasks.count(),
                'todo_tasks': assigned_tasks.filter(status=Task.Status.TODO).count(),
                'in_progress_tasks': assigned_tasks.filter(
                    status=Task.Status.IN_PROGRESS
                ).count(),
                'completed_tasks': assigned_tasks.filter(status=Task.Status.DONE).count(),
                'overdue_tasks': assigned_tasks.filter(due_date__lt=today).exclude(
                    status=Task.Status.DONE
                ).count(),
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
