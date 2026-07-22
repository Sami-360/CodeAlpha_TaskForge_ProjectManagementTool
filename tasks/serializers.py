from django.contrib.auth import get_user_model
from rest_framework import serializers

from projects.models import ProjectLabel, ProjectMember
from projects.serializers import ProjectLabelSerializer, UserSummarySerializer
from tasks.models import ChecklistItem, Task, TaskAttachment, TaskChecklist

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
    due_state = serializers.SerializerMethodField()
    labels = ProjectLabelSerializer(many=True, read_only=True)

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
            'due_state',
            'labels',
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

    def get_due_state(self, task):
        from datetime import timedelta
        from django.utils import timezone

        if task.status == Task.Status.DONE:
            return 'completed'
        if not task.due_date:
            return 'no_due_date'
        today = timezone.localdate()
        if task.due_date < today:
            return 'overdue'
        if task.due_date == today:
            return 'due_today'
        if task.due_date == today + timedelta(days=1):
            return 'due_tomorrow'
        if task.due_date <= today + timedelta(days=7):
            return 'due_soon'
        return 'scheduled'


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


class TaskAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSummarySerializer(read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = TaskAttachment
        fields = [
            'id', 'original_name', 'file_url', 'file_size', 'uploaded_by',
            'uploaded_at',
        ]
        read_only_fields = fields

    def get_file_url(self, attachment):
        request = self.context.get('request')
        url = f'/api/task-attachments/{attachment.pk}/download/'
        return request.build_absolute_uri(url) if request else url


class TaskAttachmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskAttachment
        fields = ['file']

    def validate_file(self, upload):
        from tasks.validators import validate_attachment

        validate_attachment(upload)
        return upload

    def create(self, validated_data):
        from pathlib import Path

        upload = validated_data['file']
        return TaskAttachment.objects.create(
            task=self.context['task'],
            uploaded_by=self.context['request'].user,
            original_name=Path(upload.name).name[:255],
            file_size=upload.size,
            **validated_data,
        )


class ChecklistItemSerializer(serializers.ModelSerializer):
    completed_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = ChecklistItem
        fields = [
            'id', 'text', 'is_completed', 'position', 'completed_by',
            'completed_at', 'created_at',
        ]
        read_only_fields = ['id', 'completed_by', 'completed_at', 'created_at']

    def validate_text(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Checklist item text cannot be blank.')
        return value


class TaskChecklistSerializer(serializers.ModelSerializer):
    items = ChecklistItemSerializer(many=True, read_only=True)
    completed_count = serializers.SerializerMethodField()
    total_count = serializers.SerializerMethodField()
    completed_percentage = serializers.SerializerMethodField()

    class Meta:
        model = TaskChecklist
        fields = [
            'id', 'title', 'items', 'completed_count', 'total_count',
            'completed_percentage', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Checklist title cannot be blank.')
        return value

    def create(self, validated_data):
        return TaskChecklist.objects.create(
            task=self.context['task'],
            created_by=self.context['request'].user,
            **validated_data,
        )

    def get_completed_count(self, checklist):
        return sum(1 for item in checklist.items.all() if item.is_completed)

    def get_total_count(self, checklist):
        return len(checklist.items.all())

    def get_completed_percentage(self, checklist):
        total = self.get_total_count(checklist)
        return round(self.get_completed_count(checklist) * 100 / total) if total else 0


class TaskLabelAssignmentSerializer(serializers.Serializer):
    label_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=True,
    )

    def validate_label_ids(self, values):
        unique_values = list(dict.fromkeys(values))
        labels = ProjectLabel.objects.filter(
            project=self.context['task'].project,
            pk__in=unique_values,
        )
        if labels.count() != len(unique_values):
            raise serializers.ValidationError('Every label must belong to this project.')
        self.context['labels'] = labels
        return unique_values

    def save(self):
        task = self.context['task']
        task.labels.set(self.context['labels'])
        return task
