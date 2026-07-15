from django.contrib.auth import get_user_model
from rest_framework import serializers

from projects.models import ProjectMember
from projects.serializers import UserSummarySerializer
from tasks.models import Task

User = get_user_model()


class TaskProjectSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)


class TaskSerializer(serializers.ModelSerializer):
    project = TaskProjectSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    assigned_to = UserSummarySerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source='assigned_to',
        queryset=User.objects.all(),
        allow_null=True,
        required=False,
        write_only=True,
    )
    comment_count = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            'id',
            'project',
            'title',
            'description',
            'created_by',
            'assigned_to',
            'assigned_to_id',
            'status',
            'priority',
            'due_date',
            'position',
            'comment_count',
            'is_overdue',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'project', 'created_by', 'created_at', 'updated_at']

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Task title cannot be blank.')
        return value

    def validate(self, attrs):
        project = self.context['project']
        assignee = attrs.get('assigned_to', getattr(self.instance, 'assigned_to', None))
        if assignee and not ProjectMember.objects.filter(
            project=project,
            user=assignee,
        ).exists():
            raise serializers.ValidationError(
                {'assigned_to_id': 'Assigned user must be a project member.'}
            )
        return attrs

    def create(self, validated_data):
        return Task.objects.create(
            project=self.context['project'],
            created_by=self.context['request'].user,
            **validated_data,
        )

    def get_comment_count(self, task):
        return getattr(task, 'comment_count', 0)

    def get_is_overdue(self, task):
        from django.utils import timezone

        return bool(
            task.due_date
            and task.due_date < timezone.localdate()
            and task.status != Task.Status.DONE
        )


class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['status']


class TaskAssignmentSerializer(serializers.ModelSerializer):
    assigned_to = UserSummarySerializer(read_only=True)
    assigned_to_id = serializers.PrimaryKeyRelatedField(
        source='assigned_to',
        queryset=User.objects.all(),
        allow_null=True,
        required=True,
        write_only=True,
    )

    class Meta:
        model = Task
        fields = ['assigned_to', 'assigned_to_id']

    def validate_assigned_to_id(self, user):
        if user and not ProjectMember.objects.filter(
            project=self.instance.project,
            user=user,
        ).exists():
            raise serializers.ValidationError('Assigned user must be a project member.')
        return user


class TaskPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['status', 'position']
