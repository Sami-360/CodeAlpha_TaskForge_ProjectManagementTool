from rest_framework import serializers

from notifications.models import Notification
from projects.serializers import UserSummarySerializer


class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    project_id = serializers.IntegerField(read_only=True)
    task_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'sender',
            'notification_type',
            'message',
            'project_id',
            'task_id',
            'is_read',
            'created_at',
        ]
        read_only_fields = fields
