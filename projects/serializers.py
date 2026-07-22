from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import serializers

from projects.models import Project, ProjectActivity, ProjectLabel, ProjectMember
from projects.permissions import get_project_role

User = get_user_model()


class UserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'avatar']


class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    added_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'role', 'added_by', 'joined_at']
        read_only_fields = ['id', 'user', 'added_by', 'joined_at']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSummarySerializer(read_only=True)
    member_count = serializers.SerializerMethodField()
    current_user_role = serializers.SerializerMethodField()
    task_stats = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'name',
            'description',
            'owner',
            'member_count',
            'current_user_role',
            'task_stats',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'created_at', 'updated_at']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Project name cannot be blank.')
        return value

    def get_current_user_role(self, project):
        request = self.context.get('request')
        return get_project_role(project, request.user) if request else None

    def get_member_count(self, project):
        annotated_count = getattr(project, 'member_count', None)
        return annotated_count if annotated_count is not None else project.memberships.count()

    def get_task_stats(self, project):
        annotated = {
            'total': getattr(project, 'task_total', None),
            'todo': getattr(project, 'task_todo', None),
            'in_progress': getattr(project, 'task_in_progress', None),
            'done': getattr(project, 'task_done', None),
        }
        if all(value is not None for value in annotated.values()):
            return annotated

        counts = {'total': 0, 'todo': 0, 'in_progress': 0, 'done': 0}
        for item in project.tasks.values('status').annotate(count=Count('id')):
            counts[item['status']] = item['count']
            counts['total'] += item['count']
        return counts

    @transaction.atomic
    def create(self, validated_data):
        project = Project.objects.create(
            owner=self.context['request'].user,
            **validated_data,
        )
        return project


class ProjectMemberCreateSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    role = serializers.ChoiceField(
        choices=[ProjectMember.Role.MANAGER, ProjectMember.Role.MEMBER]
    )

    def validate_identifier(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Username or email is required.')
        return value

    def validate(self, attrs):
        identifier = attrs['identifier']
        user = User.objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        if not user:
            raise serializers.ValidationError({'identifier': 'User was not found.'})

        project = self.context['project']
        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise serializers.ValidationError({'identifier': 'User is already a member.'})

        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        validated_data.pop('identifier')
        return ProjectMember.objects.create(
            project=self.context['project'],
            added_by=self.context['request'].user,
            **validated_data,
        )


class ProjectMemberRoleSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        choices=[ProjectMember.Role.MANAGER, ProjectMember.Role.MEMBER]
    )

    class Meta:
        model = ProjectMember
        fields = ['role']

    def validate(self, attrs):
        if self.instance.role == ProjectMember.Role.OWNER:
            raise serializers.ValidationError('The owner role cannot be changed.')
        return attrs


class ProjectLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectLabel
        fields = ['id', 'name', 'color', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Label name cannot be blank.')
        project = self.context['project']
        queryset = ProjectLabel.objects.filter(project=project, name__iexact=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('This project already has that label.')
        return value

    def validate_color(self, value):
        import re

        if not re.fullmatch(r'#[0-9A-Fa-f]{6}', value):
            raise serializers.ValidationError('Use a six-digit hexadecimal color such as #175CD3.')
        return value.upper()

    def create(self, validated_data):
        return ProjectLabel.objects.create(
            project=self.context['project'],
            created_by=self.context['request'].user,
            **validated_data,
        )


class ProjectActivitySerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)
    target_user = UserSummarySerializer(read_only=True)
    task_id = serializers.IntegerField(read_only=True)
    message = serializers.SerializerMethodField()

    class Meta:
        model = ProjectActivity
        fields = [
            'id', 'action', 'message', 'actor', 'task_id', 'target_user',
            'metadata', 'created_at',
        ]

    def get_message(self, activity):
        actor = activity.actor.get_full_name() or activity.actor.username if activity.actor else 'System'
        detail = activity.metadata
        messages = {
            ProjectActivity.Action.PROJECT_CREATED: f'{actor} created the project.',
            ProjectActivity.Action.PROJECT_UPDATED: f'{actor} updated the project.',
            ProjectActivity.Action.MEMBER_ADDED: f'{actor} added {detail.get("member_name", "a member")}.',
            ProjectActivity.Action.MEMBER_REMOVED: f'{actor} removed {detail.get("member_name", "a member")}.',
            ProjectActivity.Action.MEMBER_ROLE_CHANGED: f'{actor} changed a member role to {detail.get("role", "a new role")}.',
            ProjectActivity.Action.TASK_CREATED: f'{actor} created task "{detail.get("task_title", "Task")}".',
            ProjectActivity.Action.TASK_ASSIGNED: f'{actor} assigned task "{detail.get("task_title", "Task")}".',
            ProjectActivity.Action.TASK_STATUS_CHANGED: f'{actor} moved a task to {detail.get("status", "a new status")}.',
            ProjectActivity.Action.TASK_UPDATED: f'{actor} updated task "{detail.get("task_title", "Task")}".',
            ProjectActivity.Action.TASK_DELETED: f'{actor} deleted task "{detail.get("task_title", "Task")}".',
            ProjectActivity.Action.COMMENT_ADDED: f'{actor} commented on "{detail.get("task_title", "a task")}".',
            ProjectActivity.Action.ATTACHMENT_ADDED: f'{actor} attached "{detail.get("filename", "a file")}".',
            ProjectActivity.Action.ATTACHMENT_DELETED: f'{actor} deleted attachment "{detail.get("filename", "a file")}".',
            ProjectActivity.Action.CHECKLIST_UPDATED: f'{actor} updated a checklist.',
        }
        return messages.get(activity.action, f'{actor} updated the project.')
